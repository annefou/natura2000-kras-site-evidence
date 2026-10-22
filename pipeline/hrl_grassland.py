#!/usr/bin/env python3
"""Copernicus HRL Grassland inside the site: 2018 status (10 m) and 2015-2018 change (20 m).

    pixi run python pipeline/hrl_grassland.py

Same method as pipeline/builders/build_clcplus_crate.py: the EEA image services compute a histogram
of pixel values inside a polygon on the server, so no raster is downloaded. Output (committed, CLMS
data are free for any purpose): results/eu/hrl-grassland/areas.csv and source.json.

The yearly HRL Grassland 2017-2023 (10 m) is distributed through the Copernicus Data Space
Ecosystem and needs an account: not used here (TODO).
"""
from __future__ import annotations

import csv
import json
import tomllib
from datetime import datetime, timezone
from pathlib import Path

import httpx
from shapely.geometry import box, shape
from shapely.ops import unary_union

REPO = Path(__file__).resolve().parents[1]
SITE = tomllib.loads((REPO / "config" / "study.toml").read_text())["study"]["site"]
SERVICE = "https://image.discomap.eea.europa.eu/arcgis/rest/services/GioLandPublic/{}/ImageServer"
LAYERS = {"HRL_Grassland_2018": 10, "HRL_GrasslandChange_15_18": 20}
EEA_SITES = "https://bio.discomap.eea.europa.eu/arcgis/rest/services/ProtectedSites/Natura2000Sites/MapServer/2/query"


def esri(geom) -> str:
    parts = getattr(geom, "geoms", [geom])
    rings = [list(map(list, p.exterior.coords)) for p in parts] + [list(map(list, r.coords)) for p in parts for r in p.interiors]
    return json.dumps({"rings": rings, "spatialReference": {"wkid": 3035}})


def main() -> None:
    r = httpx.get(EEA_SITES, params={"where": f"SITECODE='{SITE}'", "returnGeometry": "true", "outSR": "3035", "f": "geojson"}, timeout=120)
    site = unary_union([shape(f["geometry"]) for f in r.json()["features"]])
    rows, meta = [], {"retrieved": datetime.now(timezone.utc).isoformat(timespec="seconds"), "site": SITE, "layers": {}}
    for layer, px in LAYERS.items():
        url = SERVICE.format(layer)
        info = httpx.get(url, params={"f": "json"}, timeout=60).json()
        rat = httpx.get(f"{url}/rasterAttributeTable", params={"f": "json"}, timeout=60).json()
        names = {}
        for f in rat["features"]:
            a = {k.lower(): v for k, v in f["attributes"].items()}
            names[int(a["value"])] = a.get("classname") or a.get("class_name") or ""
        step = (info["maxImageWidth"] - 100) * px
        w, s, e, n = site.bounds
        counts: dict[int, int] = {}
        y = s
        while y < n:
            x = w
            while x < e:
                piece = site.intersection(box(x, y, min(x + step, e), min(y + step, n)))
                if not piece.is_empty and piece.area > 0:
                    h = httpx.post(f"{url}/computeHistograms", timeout=300, data={
                        "geometry": esri(piece), "geometryType": "esriGeometryPolygon",
                        "pixelSize": json.dumps({"x": px, "y": px, "spatialReference": {"wkid": 3035}}), "f": "json"}).json()
                    if "error" in h:
                        raise SystemExit(f"{layer}: {h['error']}")
                    hist = h["histograms"][0]
                    width = (hist["max"] - hist["min"]) / hist["size"]
                    if abs(width - 1) > 1e-9:
                        raise SystemExit(f"{layer}: histogram bins {width} wide; refusing to guess")
                    for i, c in enumerate(hist["counts"]):
                        if c:
                            v = round(hist["min"] + i + 0.5)
                            counts[v] = counts.get(v, 0) + c
                x += step
            y += step
        # Areas from pixel SHARES x site area: the change layer is stored in EPSG:3857 and the server
        # counts its native pixels (~14 m on the ground at 45.7 N) whatever pixelSize is requested, so
        # count x nominal pixel area would double the site. Shares are unaffected.
        total = sum(counts.values())
        site_ha = site.area / 1e4
        for v, c in sorted(counts.items()):
            rows.append([layer, px, v, names.get(v, ""), c, round(100 * c / total, 3), round(site_ha * c / total, 1)])
        meta["layers"][layer] = {"url": url, "pixel_m": px, "copyright": info.get("copyrightText"),
                                 "description": (info.get("description") or "")[:400]}
    out = REPO / "results" / "eu" / "hrl-grassland"
    out.mkdir(parents=True, exist_ok=True)
    with (out / "areas.csv").open("w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["layer", "pixel_m", "value", "class_name", "pixels", "share_pct", "area_ha"])
        wr.writerows(rows)
    (out / "source.json").write_text(json.dumps(meta, indent=2) + "\n")
    for r_ in rows:
        print("[hrl]", *r_)


if __name__ == "__main__":
    main()
