#!/usr/bin/env python3
# Vendored from annefou/bmd-sap-prototype (MIT, per its package.json), scripts/fixtures/build_species_crate.py
# at commit 4f7404ae3b8025066e4c070a53d67762c2ea65b5: the BMD Single Access Point prototype
# (A. Fouilloux, FAIR2Adapt-funded), whose data builders are reused here.
# Changes for this study: curated key read from config/curated/, cache in data/cache/; records whose taxon key is a synonym or a child of an SDF taxon (e.g. Morimus funereus -> Morimus asper funereus) are mapped back through the GBIF v2 match (accepted usage and classification) instead of being left without a Standard Data Form name; usage line. See pipeline/builders/README.md.
"""Build the species crate: GBIF records of the site's qualifying species, inside the site.

    python pipeline/builders/build_species_crate.py --site SI3000276

Reads the GBIF download named in config/curated/<site>/gbif-download.txt (made by a person from
gbif-request.md), checks it is the download that request describes, clips it to the exact site
boundary, and places every record on HEALPix (WGS84, NESTED) with healpix-connector: its own cell
and the cells its stated positional uncertainty covers.

  occurrences.csv      presence records inside the site, with cell and uncertainty footprint
  species-years.csv    records and occupied cells per species and year
  species-summary.csv  per species: records, years covered, share with stated uncertainty
  datasets.csv         the source datasets of the download, for citation

Records are kept in the crate, not only linked: GBIF deletes the download file after a set date,
while the DOI remains. Observer names are left out. Opportunistic records measure observer effort
as much as occurrence, and the crate says so.
"""
from __future__ import annotations

import argparse
import csv
import io
import shutil
import statistics
import zipfile
from collections import Counter, defaultdict
from importlib.metadata import version

import httpx
import numpy as np
import shapely
from healpix_connector.cells import assign_cells, footprint_cells
from healpix_connector.connectors import gbif
from healpix_connector.conventions import cell_size_m

import natura_site
from common import CACHE, CRATES, CURATED, REPO, THIS_RO, TODAY, add_file, crate_skeleton, write_crate

DEPTH = 13  # ~800 m cells: finer than most stated uncertainties, coarse enough to count occupancy
GBIF_API = "https://api.gbif.org/v1"
CONNECTOR_DOI = "https://doi.org/10.5281/zenodo.22904851"  # healpix-connector v0.1.0
KEEP = ["gbifID", "datasetKey", "species", "scientificName", "taxonKey", "speciesKey", "occurrenceStatus",
        "individualCount", "eventDate", "year", "basisOfRecord", "decimalLatitude", "decimalLongitude",
        "coordinateUncertaintyInMeters", "license"]


def download(key: str) -> tuple[dict, dict, list[dict]]:
    meta = gbif.download_metadata(key)
    raw = httpx.get(f"{GBIF_API}/occurrence/download/{key}", timeout=60).json()
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"gbif-{key}.zip"
    if not path.exists():
        with httpx.stream("GET", meta["download_link"], timeout=600, follow_redirects=True) as r:
            r.raise_for_status()
            with path.open("wb") as fh:
                for chunk in r.iter_bytes(1 << 20):
                    fh.write(chunk)
    with zipfile.ZipFile(path) as z:
        name = next(n for n in z.namelist() if n.endswith(".csv"))
        text = io.TextIOWrapper(z.open(name), encoding="utf-8")
        rows = list(csv.DictReader(text, delimiter="\t", quoting=csv.QUOTE_NONE))
    return meta, raw, rows


def resolve_keys(keys: set[str], by_key: dict[str, str]) -> dict[str, str]:
    """taxonKey -> SDF name, for keys that are synonyms or children of an SDF taxon (COL XR)."""
    out = {}
    for k in sorted(keys):
        d = httpx.get(f"{GBIF_API.replace('/v1', '/v2')}/species/match",
                      params={"checklistKey": gbif.COL_XR, "usageKey": k}, timeout=60).json()
        chain = [(d.get("acceptedUsage") or {}).get("key"), *[c.get("key") for c in reversed(d.get("classification") or [])]]
        hit = next((by_key[c] for c in chain if c in by_key), None)
        if hit:
            out[k] = hit
            print(f"[species]   taxon key {k} ({(d.get('usage') or {}).get('name')}) -> {hit}")
    return out


def datasets(key: str) -> list[dict]:
    out, offset = [], 0
    while True:
        page = httpx.get(f"{GBIF_API}/occurrence/download/{key}/datasets",
                         params={"limit": 500, "offset": offset}, timeout=60).json()
        out += page["results"]
        if page.get("endOfRecords", True):
            return out
        offset += len(page["results"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--site", required=True, help="Natura 2000 site code")
    info = natura_site.load(ap.parse_args().site)
    curated = CURATED / info.code
    key_file = curated / "gbif-download.txt"
    if not key_file.exists():
        print(f"[species] no GBIF download recorded for {info.code}: run `python pipeline/builders/gbif_request.py --site {info.code}`, "
              f"submit it on gbif.org, and put the download key in {key_file.relative_to(REPO)}")
        raise SystemExit(3)  # nothing to build yet, not an error
    key = key_file.read_text().strip()

    # The requested taxa, matched as the request matched them.
    sdf_species = CRATES / f"site-{info.code}" / "sdf-species.csv"
    names = sorted({r["species_name"] for r in csv.DictReader(sdf_species.open())})
    by_key = {m["taxon_key"]: n for n in names if (m := gbif.match_name(n)).get("taxon_key")}

    meta, raw, rows = download(key)
    if meta["status"] != "SUCCEEDED" or meta["checklist_key"] != gbif.COL_XR:
        raise SystemExit(f"download {key}: status {meta['status']}, checklist {meta['checklist_key']}; refusing")
    requested = next((p for p in meta["predicate"].get("predicates", []) if p.get("key") == "TAXON_KEY"), {})
    if set(requested.get("values", [])) != set(by_key):
        raise SystemExit(f"download {key} was made for other taxa than the site's Standard Data Form; refusing")
    if len(rows) != meta["total_records"]:
        raise SystemExit(f"download {key}: {len(rows)} rows read, {meta['total_records']} declared; refusing")

    # Clip to the exact boundary; keep presences only.
    site = info.polygon("4326")
    lon = np.array([float(r["decimalLongitude"]) for r in rows])
    lat = np.array([float(r["decimalLatitude"]) for r in rows])
    inside = shapely.contains_xy(site, lon, lat)
    status = Counter(r["occurrenceStatus"] for r, keep in zip(rows, inside) if keep)
    recs = [r for r, keep in zip(rows, inside) if keep and r["occurrenceStatus"] == "PRESENT"]

    # A record's taxonKey can be a synonym, or a subspecies, of the requested SDF taxon (GBIF matched
    # it to that taxon when filtering). Resolve such keys once through the v2 match: accepted usage
    # first, then the classification (an infraspecific record belongs to its SDF species).
    resolved = resolve_keys({r["taxonKey"] for r in recs if r["taxonKey"] not in by_key and r["speciesKey"] not in by_key},
                            by_key)

    cells = assign_cells([float(r["decimalLongitude"]) for r in recs], [float(r["decimalLatitude"]) for r in recs], DEPTH)
    folder = CRATES / f"species-{info.code}"
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)

    occ_cols = ["sdf_name", *KEEP, f"cell_depth{DEPTH}", "footprint_cells", "uncertainty_stated"]
    per_year: dict[tuple[str, str], dict] = defaultdict(lambda: {"records": 0, "cells": set(), "stated": 0})
    per_species: dict[str, dict] = defaultdict(lambda: {"records": 0, "years": set(), "stated": 0, "unc": []})
    with (folder / "occurrences.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(occ_cols)
        for r, cell in zip(recs, cells):
            sdf = by_key.get(r["taxonKey"]) or by_key.get(r["speciesKey"]) or resolved.get(r["taxonKey"], "")
            unc = float(r["coordinateUncertaintyInMeters"]) if r["coordinateUncertaintyInMeters"] else None
            fp, stated = footprint_cells(float(r["decimalLongitude"]), float(r["decimalLatitude"]), unc, DEPTH)
            w.writerow([sdf, *(r[c] for c in KEEP), int(cell), len(fp), stated])
            y = per_year[(sdf, r["year"])]
            y["records"] += 1
            y["cells"].add(int(cell))
            y["stated"] += stated
            s = per_species[sdf]
            s["records"] += 1
            s["stated"] += stated
            if r["year"]:
                s["years"].add(int(r["year"]))
            if stated:
                s["unc"].append(unc)

    with (folder / "species-years.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["sdf_name", "year", "records", f"cells_occupied_depth{DEPTH}", "records_with_stated_uncertainty"])
        for (sdf, year), v in sorted(per_year.items()):
            w.writerow([sdf, year, v["records"], len(v["cells"]), v["stated"]])
    with (folder / "species-summary.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["sdf_name", "records", "first_year", "last_year", "share_uncertainty_stated", "median_uncertainty_m"])
        for sdf in names:
            s = per_species.get(sdf)
            if not s:
                w.writerow([sdf, 0, "", "", "", ""])
                continue
            w.writerow([sdf, s["records"], min(s["years"], default=""), max(s["years"], default=""),
                        round(s["stated"] / s["records"], 3), statistics.median(s["unc"]) if s["unc"] else ""])
    sources = datasets(key)
    with (folder / "datasets.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["dataset_key", "title", "records_in_download"])
        for d in sorted(sources, key=lambda d: -d["numberRecords"]):
            w.writerow([d["datasetKey"], d.get("datasetTitle", ""), d["numberRecords"]])

    licence = raw["license"].replace("/legalcode", "/")
    doi = f"https://doi.org/{meta['doi']}"
    effort = ("Records are opportunistic observations: their number per year reflects observer effort as much as "
              "occurrence, so counts are not abundance and a change in records is not a change in population.")
    top = max(sources, key=lambda d: d["numberRecords"])
    name = f"Records of the qualifying species inside {info.name} ({info.code}), GBIF"
    crate = crate_skeleton(
        name,
        (f"GBIF occurrence records of the {len(names)} species and subspecies of the site's Standard Data Form, "
         f"from download {doi} ({meta['total_records']:,} records in a shape covering the site), clipped to the exact "
         f"site boundary: {len(recs):,} presence records kept. Each record is placed on HEALPix depth {DEPTH} "
         f"(~{cell_size_m(DEPTH):.0f} m, WGS84, NESTED) with the cells its stated positional uncertainty covers, by "
         f"healpix-connector {version('healpix-connector')}. {effort} {top['numberRecords']:,} of the "
         f"{meta['total_records']:,} records come from {top.get('datasetTitle')}. Licence is GBIF's for the download "
         "(the most restrictive of its datasets). Observer names are not included."),
        license_id=licence,
        based_on=[
            {"@id": doi, "@type": "Dataset", "name": f"GBIF Occurrence Download {meta['doi']}", "publisher": "GBIF.org",
             "dateCreated": meta["created"][:10], "license": {"@id": licence},
             "creditText": f"GBIF.org ({meta['created'][:10]}) GBIF Occurrence Download {doi}"},
            {"@id": CONNECTOR_DOI, "@type": "SoftwareSourceCode", "name": "healpix-connector",
             "version": version("healpix-connector")},
            {"@id": f"https://www.checklistbank.org/dataset/{gbif.COL_XR}", "@type": "Dataset",
             "name": "Catalogue of Life XR (taxonomy used to match the Standard Data Form names)"},
        ],
    )
    root = crate["@graph"][1]
    root.update({"keywords": ["Natura 2000", info.code, "GBIF", "species occurrence", *names],
                 "about": {"@id": info.code}, "usageInfo": effort})
    add_file(crate, folder / "occurrences.csv", name="Presence records inside the site",
             description=f"{len(recs):,} records with cell and uncertainty footprint at depth {DEPTH}. "
                         f"Excluded inside the site: {dict((k, v) for k, v in status.items() if k != 'PRESENT') or 'none'}.",
             encoding_format="text/csv", source=doi)
    add_file(crate, folder / "species-years.csv", name="Records and occupied cells per species and year",
             description=effort, encoding_format="text/csv", source=doi)
    add_file(crate, folder / "species-summary.csv", name="Per species summary",
             description="Records, years covered, share and median of stated positional uncertainty.",
             encoding_format="text/csv", source=doi)
    add_file(crate, folder / "datasets.csv", name="Source datasets of the download",
             description=f"{len(sources)} datasets, for citation.", encoding_format="text/csv", source=doi)

    annotations = f"""@prefix schema: <https://schema.org/> .

<{THIS_RO}> schema:about "{info.code}" ;
    schema:isBasedOn <{doi}> ;
    schema:instrument <{CONNECTOR_DOI}> .
"""
    deposit = {
        "title": name, "description": root["description"],
        "ros_type": "Data-centric Research Object",
        "research_areas": ["Biology", "Ecology"],
        "license": "cc-by-nc-4.0" if "by-nc/4.0" in licence else "cc-by-4.0" if "by/4.0" in licence else "cc0-1.0",
        "keywords": root["keywords"],
        "files": [{"path": "ro-crate-metadata.json", "res_type": "File", "title": "ro-crate-metadata.json",
                   "description": "RO-Crate 1.2 metadata."},
                  *[{"path": f, "res_type": "Dataset", "title": t, "description": d} for f, t, d in [
                      ("occurrences.csv", "Presence records inside the site", "With HEALPix cell and footprint."),
                      ("species-years.csv", "Records per species and year", effort),
                      ("species-summary.csv", "Per species summary", "Records, years, positional uncertainty."),
                      ("datasets.csv", "Source datasets", "For citation.")]]],
        "links": [{"url": doi, "res_type": "Dataset", "title": f"GBIF Occurrence Download {meta['doi']}",
                   "description": f"{meta['total_records']:,} records, {len(sources)} datasets, {licence}."},
                  {"url": CONNECTOR_DOI, "res_type": "Software", "title": "healpix-connector",
                   "description": f"Version {version('healpix-connector')}: records to HEALPix cells with uncertainty footprints."}],
    }
    write_crate(folder, crate, annotations, deposit)

    print(f"[species] {name}")
    print(f"[species]   download {meta['doi']}: {meta['total_records']:,} records; inside the site {int(inside.sum()):,}; "
          f"presences kept {len(recs):,}; statuses inside {dict(status)}; licence {licence}")
    for sdf in names:
        s = per_species.get(sdf)
        print(f"[species]   {sdf:<38} {s['records'] if s else 0:>6} records"
              + (f"  {min(s['years'])}-{max(s['years'])}  uncertainty stated {s['stated'] / s['records']:.0%}" if s and s["years"] else ""))
    print(f"[species] {folder.relative_to(REPO)}/")


if __name__ == "__main__":
    main()
