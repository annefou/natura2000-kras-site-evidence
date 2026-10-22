#!/usr/bin/env python3
"""Feasibility check: read one national LiDAR tile (LSS 2011-2015, GKOT .laz) and place it on HEALPix.

    pixi run lidar-check                      # tile TM_402_75 (Komen, inside the 2022 fire), block b_11
    pixi run python pipeline/lidar/read_tile.py --block b_11 --tile 402_75

Source: ARSO LiDAR archive, http://gis.arso.gov.si/lidar/gkot/laz/<block>/D96TM/TM_<E>_<N>.laz
(1 x 1 km tiles named by D96/TM kilometre coordinates; licence GURS/ARSO, CC BY 4.0, attribution
"Geodetska uprava Republike Slovenije"). The header carries no CRS, so EPSG:3794 is set here.
Writes results/lidar/<tile>.json (summary only; the point cloud is cached in data/lidar/, gitignored).
The height range per cell is a crude woody proxy: terrain slope inflates it, so a canopy-height
model needs heights normalised to ground first.
"""
from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path

import healpix_geo.nested as hn
import laspy
import numpy as np
from pyproj import Transformer

REPO = Path(__file__).resolve().parents[2]
URL = "http://gis.arso.gov.si/lidar/gkot/laz/{block}/D96TM/TM_{tile}.laz"
CLASSES = {0: "never classified", 1: "unclassified", 2: "ground", 3: "low vegetation",
           4: "medium vegetation", 5: "high vegetation", 6: "building", 7: "noise", 9: "water"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--block", default="b_11")
    ap.add_argument("--tile", default="402_75")
    ap.add_argument("--depth", type=int, default=19)        # ~12 m cells
    a = ap.parse_args()

    laz = REPO / "data" / "lidar" / f"TM_{a.tile}.laz"
    if not laz.exists():
        laz.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(URL.format(block=a.block, tile=a.tile), laz)

    las = laspy.read(laz)
    h = las.header
    area = float((h.maxs[0] - h.mins[0]) * (h.maxs[1] - h.mins[1]))
    cls = np.asarray(las.classification)
    codes, counts = np.unique(cls, return_counts=True)
    ground = cls == 2

    x, y, z = np.asarray(las.x), np.asarray(las.y), np.asarray(las.z)
    lon, lat = Transformer.from_crs(3794, 4326, always_xy=True).transform(x, y)
    cell = hn.lonlat_to_healpix(lon, lat, np.uint8(a.depth), ellipsoid="WGS84")
    order = np.argsort(cell)
    cs, zs, gs = cell[order], z[order], ground[order]
    _, start = np.unique(cs, return_index=True)
    zmax = np.maximum.reduceat(zs, start)
    gmin = np.minimum.reduceat(np.where(gs, zs, np.inf), start)
    ok = np.isfinite(gmin)
    rng = zmax[ok] - gmin[ok]

    out = {
        "tile": f"TM_{a.tile}", "block": a.block, "url": URL.format(block=a.block, tile=a.tile),
        "las_version": str(h.version), "point_format": h.point_format.id, "points": int(h.point_count),
        "header_crs": str(h.parse_crs()), "crs_used": "EPSG:3794",
        "density_all_pts_m2": round(h.point_count / area, 2),
        "density_ground_pts_m2": round(float(ground.sum()) / area, 2),
        "classes": {CLASSES.get(int(c), str(int(c))): int(n) for c, n in zip(codes, counts)},
        "healpix": {"library": "healpix-geo", "ellipsoid": "WGS84", "indexing": "nested", "depth": a.depth,
                    "cells": int(len(start)), "cells_with_ground": int(ok.sum())},
        "height_range_gt_2m_share": round(float((rng > 2).mean()), 3),
        "height_range_gt_5m_share": round(float((rng > 5).mean()), 3),
    }
    dst = REPO / "results" / "lidar" / f"TM_{a.tile}.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
