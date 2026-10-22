#!/usr/bin/env python3
# Vendored from annefou/bmd-sap-prototype (MIT, per its package.json), scripts/fixtures/gbif_request.py
# at commit 4f7404ae3b8025066e4c070a53d67762c2ea65b5: the BMD Single Access Point prototype
# (A. Fouilloux, FAIR2Adapt-funded), whose data builders are reused here.
# Changes for this study: request written to config/curated/<site>/; usage line. See pipeline/builders/README.md.
"""Write the GBIF download request for a site, for a person to submit on gbif.org.

    python pipeline/builders/gbif_request.py --site SI3000276

Writes config/curated/<site>/gbif-request.md: the search link, the filter it encodes and the
record count the API gives for it today, so the person submitting can check the website shows
the same thing before downloading. A GBIF download needs an account; the person who submits it
owns the download and its DOI. No credentials are needed or stored here.

Filter: the site's Standard Data Form species (matched in the taxonomy healpix-connector uses,
stated below), records with coordinates and no geospatial issue, inside a simplified shape that
fully covers the site boundary. Records outside the exact boundary are clipped when the species
crate is built from the download.
"""
from __future__ import annotations

import argparse
import csv
from urllib.parse import urlencode

import httpx
from healpix_connector.connectors import gbif
from shapely.geometry.polygon import orient

import natura_site
from common import CRATES, CURATED, REPO, TODAY

GBIF_SEARCH = "https://www.gbif.org/occurrence/search"
GBIF_API_SEARCH = "https://api.gbif.org/v1/occurrence/search"
MAX_WKT = 3000  # longer shapes are refused by the search API


def query_shape(site):
    """Few vertices, and it must cover the whole site: widen until both hold."""
    for buf, tol in [(0.003, 0.003), (0.005, 0.005), (0.01, 0.008), (0.02, 0.015)]:
        q = site.buffer(buf).simplify(tol, preserve_topology=True)
        q = orient(q if q.geom_type == "Polygon" else q.convex_hull, 1.0)  # counter-clockwise, as GBIF expects
        wkt = q.wkt.replace(", ", ",")
        if q.covers(site) and len(wkt) <= MAX_WKT:
            return wkt, buf
    raise SystemExit("no covering shape short enough for GBIF; refusing to write a request that misses records")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--site", required=True, help="Natura 2000 site code")
    info = natura_site.load(ap.parse_args().site)
    species_csv = CRATES / f"site-{info.code}" / "sdf-species.csv"
    if not species_csv.exists():
        raise SystemExit(f"build the site crate first: python pipeline/builders/build_site_crate.py --site {info.code}")

    names = sorted({r["species_name"] for r in csv.DictReader(species_csv.open())})
    matches = [(n, gbif.match_name(n)) for n in names]
    unmatched = [n for n, m in matches if not m.get("taxon_key")]
    taxa = [(n, m) for n, m in matches if m.get("taxon_key")]
    wkt, buf = query_shape(info.polygon("4326"))

    filters = [("has_coordinate", "true"), ("has_geospatial_issue", "false")]
    api = [("checklistKey", gbif.COL_XR), ("geometry", wkt), ("limit", "0"),
           ("hasCoordinate", "true"), ("hasGeospatialIssue", "false")] + [("taxonKey", m["taxon_key"]) for _, m in taxa]
    count = httpx.get(GBIF_API_SEARCH, params=api, timeout=60).json()["count"]
    link = f"{GBIF_SEARCH}?" + urlencode([("geometry", wkt), *filters] + [("taxon_key", m["taxon_key"]) for _, m in taxa])

    rows = "\n".join(f"| {n} | `{m['taxon_key']}` | {m.get('scientific_name', '')} | {m.get('match_type', '')} |"
                     for n, m in taxa)
    missing = ("\n**Not matched, so not in the request:** " + ", ".join(unmatched) + "\n") if unmatched else ""
    out = CURATED / info.code / "gbif-request.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f"""# GBIF download request — {info.name} ({info.code})

Generated {TODAY} by `python pipeline/builders/gbif_request.py --site {info.code}`. Regenerate rather than edit.

## Open this link while logged in to gbif.org

[Open the search on GBIF]({link})

## Before downloading, check

The page should show about **{count:,} occurrences** (the GBIF API's count for the same filter on
{TODAY}). If it shows many more, the website has read the taxon keys in another taxonomy: do not
download, and say so.

## Then

1. **Download → Simple** (the format healpix-connector reads).
2. GBIF emails when it is ready, with a DOI (`10.15468/dl.…`).
3. Record the **download key** (e.g. `0012345-260924123456789`) in `config/curated/{info.code}/gbif-download.txt`.

The download and its DOI belong to the person who submits it; the species crate cites it.

## What the link encodes

- **Area:** a simplified shape that covers the whole site boundary (buffered {buf}°); records
  outside the exact boundary are clipped when the species crate is built.
- **Quality:** records with coordinates and no geospatial issue.
- **Taxonomy:** Catalogue of Life XR, checklist `{gbif.COL_XR}` (healpix-connector's default and
  GBIF.org's).
- **Taxa:** the {len(taxa)} species and subspecies of the site's Standard Data Form.

| Standard Data Form name | Taxon key | Matched name | Match |
|---|---|---|---|
{rows}
{missing}""")
    print(f"[gbif] {out.relative_to(REPO)}: {len(taxa)} taxa, {count:,} records expected"
          + (f", {len(unmatched)} not matched" if unmatched else ""))


if __name__ == "__main__":
    main()
