#!/usr/bin/env python3
# Vendored from annefou/bmd-sap-prototype (MIT, per its package.json), scripts/fixtures/build_clcplus_crate.py
# at commit 4f7404ae3b8025066e4c070a53d67762c2ea65b5: the BMD Single Access Point prototype
# (A. Fouilloux, FAIR2Adapt-funded), whose data builders are reused here.
# Changes for this study: crates are written to data/crates/ (via common.py); usage line. See pipeline/builders/README.md.
"""Build the 10 m land-cover crate: CLC+ Backbone inside the site, 2018 and 2021.

    python pipeline/builders/build_clcplus_crate.py --site SI3000276

  clcplus-areas.csv    pixels, area and share of the site for every CLC+ class, per year

Works for any site: the EEA serves CLC+ Backbone as image services that compute a histogram of
pixel values inside a polygon on the server, so no geometry has to be downloaded. The site is
cut into strips no taller than the service's image limit, and the strip histograms are summed.
Class names come from the service's own raster attribute table.

The two years are separate classifications. Their difference mixes real change with differences
in classification, so this crate does not call it change; accuracy per year is in each year's
CLMS validation report, cited in the crate.
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import Counter

import httpx
from shapely.geometry import box

import natura_site
from common import CRATES, THIS_RO, add_file, crate_skeleton, write_crate
from sources import CC_BY_4, CLCPLUS, CLCPLUS_SERVICE, NATURA2000

PIXEL_M = 10
EXCLUDED = {254, 255}  # "Outside area", "No data": reported, never counted as land cover


def esri_polygon(geom) -> str:
    parts = getattr(geom, "geoms", [geom])
    rings = [list(map(list, p.exterior.coords)) for p in parts]
    rings += [list(map(list, r.coords)) for p in parts for r in p.interiors]
    return json.dumps({"rings": rings, "spatialReference": {"wkid": 3035}})


def strips(site, service_url: str) -> list:
    """Pieces of the site small enough for one computeHistograms request."""
    info = httpx.get(service_url, params={"f": "json"}, timeout=60).json()
    max_w = (info["maxImageWidth"] - 100) * PIXEL_M
    max_h = (info["maxImageHeight"] - 100) * PIXEL_M
    w, s, e, n = site.bounds
    pieces = []
    y = s
    while y < n:
        x = w
        while x < e:
            piece = site.intersection(box(x, y, min(x + max_w, e), min(y + max_h, n)))
            if not piece.is_empty and piece.area > 0:
                pieces.append(piece)
            x += max_w
        y += max_h
    return pieces


def histogram(service_url: str, pieces: list) -> Counter:
    total: Counter = Counter()
    for piece in pieces:
        resp = httpx.post(f"{service_url}/computeHistograms", timeout=300, data={
            "geometry": esri_polygon(piece), "geometryType": "esriGeometryPolygon",
            "pixelSize": json.dumps({"x": PIXEL_M, "y": PIXEL_M, "spatialReference": {"wkid": 3035}}), "f": "json"})
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise SystemExit(f"{service_url}: {data['error']}")
        h = data["histograms"][0]
        width = (h["max"] - h["min"]) / h["size"]
        if abs(width - 1) > 1e-9:
            raise SystemExit(f"{service_url}: histogram bins are {width} wide, not one per class value; refusing to guess")
        for i, count in enumerate(h["counts"]):
            if count:  # bins are centred on the class values: [min + i, min + i + 1) holds value min + i + 0.5
                total[round(h["min"] + i + 0.5)] += count
    return total


def classes(service_url: str) -> dict[int, str]:
    rat = httpx.get(f"{service_url}/rasterAttributeTable", params={"f": "json"}, timeout=60).json()
    return {int(f["attributes"]["Value"]): f["attributes"]["Class_name"] for f in rat["features"]}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--site", required=True, help="Natura 2000 site code")
    info = natura_site.load(ap.parse_args().site)
    site = info.polygon("3035")
    site_ha = site.area / 1e4

    folder = CRATES / f"landcover10m-{info.code}"
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)

    rows, sources, excluded = [], [], {}
    for year, (service, doi, validation) in CLCPLUS.items():
        url = f"{CLCPLUS_SERVICE}/{service}/ImageServer"
        names = classes(url)
        pieces = strips(site, url)
        counts = histogram(url, pieces)
        # Every pixel of the site must be accounted for, or a class fell outside the histogram.
        expected = sum(p.area for p in pieces) / (PIXEL_M * PIXEL_M)
        if abs(sum(counts.values()) - expected) > 0.01 * expected:
            raise SystemExit(f"{year}: {sum(counts.values()):,} pixels counted, about {expected:,.0f} expected; refusing")
        counted = sum(c for v, c in counts.items() if v not in EXCLUDED)
        excluded[year] = {names.get(v, str(v)): c for v, c in counts.items() if v in EXCLUDED}
        for value, count in sorted(counts.items()):
            if value in EXCLUDED:
                continue
            ha = count * PIXEL_M * PIXEL_M / 1e4
            rows.append([year, value, names.get(value, ""), count, round(ha, 1), round(100 * count / counted, 2)])
        sources.append({"@id": doi, "@type": "Dataset", "name": f"CLCplus Backbone {year} (raster 10 m), Europe",
                        "publisher": "Copernicus Land Monitoring Service, European Environment Agency",
                        "citation": {"@id": validation}})

    with (folder / "clcplus-areas.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["year", "class_value", "class_name", "pixels", "area_ha", "share_of_classified_pct"])
        w.writerows(rows)

    note = ("The two years are separate classifications: their difference mixes real change with differences "
            "in classification and is not presented as change. Accuracy per year: see each year's CLMS validation "
            "report (cited).")
    name = f"Land cover at 10 m inside {info.name} ({info.code}), CLC+ Backbone 2018 and 2021"
    crate = crate_skeleton(
        name,
        (f"Pixel counts and area of each CLC+ Backbone class inside the Natura 2000 site {info.code}, for 2018 "
         f"and 2021, computed by the EEA image services over the site boundary (EPSG:3035, 10 m pixels). "
         f"Site area {site_ha:,.1f} ha. {note} CLC+ classes are land cover, not Annex I habitat types."),
        license_id=CC_BY_4,
        based_on=[*sources, {"@id": NATURA2000["@id"], "@type": "Dataset", "name": f"Site boundary, {NATURA2000['name']}"}],
    )
    root = crate["@graph"][1]
    root.update({"keywords": ["Natura 2000", info.code, "CLC+ Backbone", "land cover"], "about": {"@id": info.code},
                 "temporalCoverage": "2018/2021",
                 "conditionsOfAccess": "Copernicus Land Monitoring Service data: free of charge, for any purpose (CLMS)."})
    add_file(crate, folder / "clcplus-areas.csv", name="Land cover at 10 m inside the site, 2018 and 2021",
             description=f"{len(rows)} rows: year, class, pixels, area (ha), share of classified pixels. {note}",
             encoding_format="text/csv", source=sources[-1]["@id"])

    annotations = f"""@prefix schema: <https://schema.org/> .

<{THIS_RO}> schema:about "{info.code}" ;
    schema:temporalCoverage "2018/2021" ;
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
                  {"path": "clcplus-areas.csv", "res_type": "Dataset", "title": "Land cover at 10 m inside the site",
                   "description": note}],
        "links": [{"url": s["@id"], "res_type": "Dataset", "title": s["name"],
                   "description": "Copernicus Land Monitoring Service."} for s in sources],
    }
    write_crate(folder, crate, annotations, deposit)

    print(f"[landcover10m] {name}   site {site_ha:,.1f} ha")
    for year in CLCPLUS:
        yr = [r for r in rows if r[0] == year]
        print(f"[landcover10m]   {year}: {sum(r[4] for r in yr):,.1f} ha classified; excluded {excluded[year] or 'none'}; "
              + "; ".join(f"{r[2]} {r[4]:,.0f} ha" for r in sorted(yr, key=lambda r: -r[4])[:4]))
    print(f"[landcover10m] {folder.relative_to(CRATES.parents[1])}/")


if __name__ == "__main__":
    main()
