#!/usr/bin/env python3
# Vendored from annefou/bmd-sap-prototype (MIT, per its package.json), scripts/fixtures/build_corine_crate.py
# at commit 4f7404ae3b8025066e4c070a53d67762c2ea65b5: the BMD Single Access Point prototype
# (A. Fouilloux, FAIR2Adapt-funded), whose data builders are reused here.
# Changes for this study: crates are written to data/crates/ (via common.py); usage line. See pipeline/builders/README.md.
"""Build the land-cover crate: CORINE Land Cover inside the site, 2000-2018.

    python pipeline/builders/build_corine_crate.py --site SI3000276

  clc-status-areas.csv   area of every CLC class inside the site, 2000/2006/2012/2018
  clc-changes.csv        mapped change (from class -> to class) inside the site, per period
  clc-<year>.geojson     CLC polygons clipped to the site, EPSG:4326, for the map

Method, following the Copernicus Land Monitoring Service's own advice: status layers give the
extent in each year, but change between years is taken from the three CLC-Change layers
(2000-2006, 2006-2012, 2012-2018), not by subtracting status layers -- "instead of comparing
CLC 2000 and CLC 2018, it is proposed to derive gains and losses between 2000 and 2018 by
summing up the three CLC-Change layers" (CLMS FAQ). Areas are computed in EPSG:3035 (equal
area) after clipping to the site boundary from the EEA Natura 2000 release.

Limits, stated in the crate: 25 ha minimum mapping unit for status, 5 ha for change, 100 m
minimum width. Whether CLC 1990 covers the site is checked, not assumed.
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import defaultdict

import httpx
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

import natura_site
from common import CRATES, THIS_RO, add_file, crate_skeleton, write_crate
from sources import CC_BY_4, CLC_1990, CLC_CHANGE as CHANGE, CLC_SERVICE as CLC, CLC_STATUS as STATUS, CLC_VERSION as VERSION
from sources import CLMS_FAQ, NATURA2000


def esri_polygon(geom) -> str:
    parts = getattr(geom, "geoms", [geom])
    rings = [list(map(list, p.exterior.coords)) for p in parts]
    rings += [list(map(list, r.coords)) for p in parts for r in p.interiors]
    return json.dumps({"rings": rings})


TOO_LARGE = ("The EEA serves CORINE only as vector polygons, returned whole. Around this site they are too large "
             "for the service to return (it answers {status}). Land cover for this site needs a raster source "
             "(not available in this study); no crate is built rather than a partial one.")


class TooLarge(Exception):
    pass


def query(service: str, fields: list[str], site, srid: str) -> list[dict]:
    """All features of layer 0 intersecting the site, paged, geometry in `srid`."""
    out, offset = [], 0
    while True:
        try:
            resp = httpx.post(f"{CLC}/{service}/MapServer/0/query", timeout=180, data={
                "where": "1=1", "geometry": esri_polygon(site), "geometryType": "esriGeometryPolygon",
                "inSR": srid, "outSR": srid, "spatialRel": "esriSpatialRelIntersects",
                "outFields": ",".join(fields), "returnGeometry": "true", "f": "geojson",
                "resultOffset": str(offset), "resultRecordCount": "500"})
        except httpx.TimeoutException:
            raise TooLarge(TOO_LARGE.format(status="with a timeout"))
        if resp.status_code in (405, 500, 502, 504):
            raise TooLarge(TOO_LARGE.format(status=f"HTTP {resp.status_code}"))
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise SystemExit(f"{service}: {data['error']}")
        out += data["features"]
        if not data.get("properties", {}).get("exceededTransferLimit") and len(data["features"]) < 500:
            return out
        offset += len(data["features"])


def legend(service: str) -> dict[str, str]:
    """Class labels exactly as the EEA service renders them, e.g. '321' -> 'Natural grasslands'."""
    info = httpx.get(f"{CLC}/{service}/MapServer/0", params={"f": "json"}, timeout=60).json()
    labels = {}
    for v in info["drawingInfo"]["renderer"]["uniqueValueInfos"]:
        code, _, label = v["label"].partition(": ")
        labels[str(v["value"]).strip()] = label or code
    return labels


def covered_1990(site) -> bool:
    service, _ = CLC_1990
    resp = httpx.post(f"{CLC}/{service}/MapServer/0/query", timeout=120, data={
        "where": "1=1", "geometry": esri_polygon(site), "geometryType": "esriGeometryPolygon", "inSR": "3035",
        "spatialRel": "esriSpatialRelIntersects", "returnCountOnly": "true", "f": "json"})
    resp.raise_for_status()
    return resp.json().get("count", 0) > 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--site", required=True, help="Natura 2000 site code")
    info = natura_site.load(ap.parse_args().site)
    site_code = info.code
    folder = CRATES / f"landcover-{site_code}"
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)

    site_laea, site_wgs = info.polygon("3035"), info.polygon("4326")
    site_ha = site_laea.area / 1e4
    labels = legend(STATUS[2018][0])

    status_rows, sources = [], []
    for year, (service, field, doi) in STATUS.items():
        areas: dict[str, float] = defaultdict(float)
        for f in query(service, [field], site_laea, "3035"):
            areas[str(f["properties"][field]).strip()] += shape(f["geometry"]).intersection(site_laea).area / 1e4
        for code, ha in sorted(areas.items()):
            if ha > 0:
                status_rows.append([year, code, labels.get(code, ""), round(ha, 1), round(100 * ha / site_ha, 2)])
        clipped = [{"type": "Feature", "properties": {"clc_code": str(f["properties"][field]).strip(), "year": year},
                    "geometry": mapping(shape(f["geometry"]).intersection(site_wgs))}
                   for f in query(service, [field], site_wgs, "4326")]
        (folder / f"clc-{year}.geojson").write_text(json.dumps(
            {"type": "FeatureCollection", "features": [c for c in clipped if c["geometry"]["coordinates"]]}) + "\n")
        sources.append({"@id": doi, "@type": "Dataset", "name": f"CORINE Land Cover {year} (vector), Europe",
                        "version": VERSION, "publisher": "Copernicus Land Monitoring Service, European Environment Agency"})

    change_rows = []
    for period, (service, a, b, doi) in CHANGE.items():
        moved: dict[tuple[str, str], float] = defaultdict(float)
        for f in query(service, [a, b], site_laea, "3035"):
            p = f["properties"]
            moved[(str(p[a]).strip(), str(p[b]).strip())] += shape(f["geometry"]).intersection(site_laea).area / 1e4
        for (src, dst), ha in sorted(moved.items()):
            if ha > 0:
                change_rows.append([period, src, labels.get(src, ""), dst, labels.get(dst, ""), round(ha, 1)])
        sources.append({"@id": doi, "@type": "Dataset", "name": f"CORINE Land Cover Change {period} (vector), Europe",
                        "version": VERSION, "publisher": "Copernicus Land Monitoring Service, European Environment Agency"})

    with (folder / "clc-status-areas.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["year", "clc_code", "clc_label", "area_ha", "share_of_site_pct"])
        w.writerows(status_rows)
    with (folder / "clc-changes.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["period", "from_code", "from_label", "to_code", "to_label", "area_ha"])
        w.writerows(change_rows)

    before = ("CLC 1990 covers the site but is not used: CLMS publishes no consistent 1990 accounting layer."
              if covered_1990(site_laea) else "CLC 1990 does not cover the site: nothing before 2000.")
    limits = ("Minimum mapping unit 25 ha for status layers and 5 ha for change layers; minimum width of linear "
              f"elements 100 m (EEA service description). {before}")
    name = f"Land cover inside {info.name} ({site_code}), CORINE 2000-2018"
    crate = crate_skeleton(
        name,
        (f"Area of each CORINE Land Cover class inside the Natura 2000 site {site_code} in 2000, 2006, 2012 and 2018, "
         "and the mapped changes between inventories, clipped to the site boundary and measured in EPSG:3035. "
         "Change is taken from the CLC-Change layers, as the Copernicus Land Monitoring Service advises, not by "
         f"subtracting status layers. {limits} CORINE classes are land cover, not Annex I habitat types."),
        license_id=CC_BY_4,
        based_on=[*sources, {"@id": NATURA2000["@id"], "@type": "Dataset", "name": f"Site boundary, {NATURA2000['name']}"},
                  {"@id": CLMS_FAQ, "@type": "WebPage", "name": "CLMS FAQ: status or change products for 2000-2018"}],
    )
    root = crate["@graph"][1]
    root.update({
        "keywords": ["Natura 2000", site_code, "CORINE Land Cover", "land cover change"],
        "temporalCoverage": "2000/2018",
        "conditionsOfAccess": "Copernicus Land Monitoring Service data: free of charge, for any purpose (CLMS).",
        "about": {"@id": site_code},
    })
    add_file(crate, folder / "clc-status-areas.csv", name="Land cover inside the site, per year",
             description=f"{len(status_rows)} rows: year, CLC class, area (ha), share of the site. {limits}",
             encoding_format="text/csv", source=STATUS[2018][2])
    add_file(crate, folder / "clc-changes.csv", name="Mapped land-cover change inside the site",
             description=f"{len(change_rows)} rows: period, from class, to class, area (ha). 5 ha minimum mapping unit.",
             encoding_format="text/csv", source=CHANGE["2012-2018"][3])
    for year in STATUS:
        add_file(crate, folder / f"clc-{year}.geojson", name=f"Land cover {year}, clipped to the site",
                 description="CLC polygons clipped to the site boundary, EPSG:4326, for display.",
                 encoding_format="application/geo+json", source=STATUS[year][2])

    annotations = f"""@prefix schema: <https://schema.org/> .

<{THIS_RO}> schema:about "{site_code}" ;
    schema:temporalCoverage "2000/2018" ;
    schema:isBasedOn {' , '.join(f'<{s["@id"]}>' for s in sources)} .
"""
    deposit = {
        "title": name, "description": root["description"],
        "ros_type": "Data-centric Research Object",
        "research_areas": ["Earth observation", "Ecology"],
        "license": "cc-by-4.0",
        "keywords": root["keywords"],
        "files": [{"path": "ro-crate-metadata.json", "res_type": "File", "title": "ro-crate-metadata.json",
                   "description": "RO-Crate 1.2 metadata."},
                  {"path": "clc-status-areas.csv", "res_type": "Dataset", "title": "Land cover inside the site, per year",
                   "description": "CLC class areas inside the site, 2000-2018."},
                  {"path": "clc-changes.csv", "res_type": "Dataset", "title": "Mapped land-cover change inside the site",
                   "description": "CLC-Change areas inside the site, per period."},
                  *[{"path": f"clc-{y}.geojson", "res_type": "Dataset", "title": f"Land cover {y}, clipped to the site",
                     "description": "EPSG:4326, for display."} for y in STATUS]],
        "links": [{"url": s["@id"], "res_type": "Dataset", "title": s["name"],
                   "description": f"Copernicus Land Monitoring Service, {VERSION}."} for s in sources],
    }
    write_crate(folder, crate, annotations, deposit)

    print(f"[landcover] {name}   site {site_ha:,.1f} ha (EPSG:3035)")
    for year in STATUS:
        top = sorted((r for r in status_rows if r[0] == year), key=lambda r: -r[3])[:3]
        print(f"[landcover]   {year}: " + "; ".join(f"{r[1]} {r[2]} {r[3]:,.0f} ha" for r in top))
    for period in CHANGE:
        total = sum(r[5] for r in change_rows if r[0] == period)
        print(f"[landcover]   change {period}: {total:,.1f} ha mapped")
    print(f"[landcover] {folder.relative_to(CRATES.parents[1])}/")


if __name__ == "__main__":
    try:
        main()
    except TooLarge as exc:
        for leftover in CRATES.glob("landcover-*"):
            if leftover.is_dir() and not any(leftover.iterdir()):
                leftover.rmdir()
        raise SystemExit(str(exc))
