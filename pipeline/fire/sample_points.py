#!/usr/bin/env python3
"""LOCAL. Sample RABA_ID on a fixed 25 m point grid inside SAC SI3000276 for several snapshots.

    pixi run python pipeline/fire/sample_points.py RABA_2009_10_16.ZIP RABA_2012_12_04.RAR ...

Reuses pipeline/raba.py (download, unpack, CRS handling, clip). Same 25 m grid convention as
raba.cells() (EPSG:3794, point centres at bounds + 12.5 m), so each point stands for 625 m2.
Writes results/local/fire/points/grid.parquet once (x, y, lon, lat, HEALPix depth-15 cell, WGS84,
NESTED) and results/local/fire/points/<snapshot>.parquet (RABA_ID per point, -1 = unmapped).
Archives are deleted after sampling. Nothing here is published (MKGP permission pending).
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import shapely
from pyproj import Transformer

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "pipeline"))
import raba  # noqa: E402

OUT = REPO / "results" / "local" / "fire" / "points"
SITE = raba.CONFIG["study"]["site"]
DEPTH = raba.CONFIG["raba"]["healpix_depth"]
S = raba.SAMPLE_M


def grid(geom) -> pd.DataFrame:
    import healpix_geo.nested as hn
    minx, miny, maxx, maxy = geom.bounds
    X, Y = np.meshgrid(np.arange(minx + S / 2, maxx, S), np.arange(miny + S / 2, maxy, S))
    x, y = X.ravel(), Y.ravel()
    keep = shapely.contains_xy(geom, x, y)
    x, y = x[keep], y[keep]
    lon, lat = Transformer.from_crs("EPSG:3794", "EPSG:4326", always_xy=True).transform(x, y)
    cell = hn.lonlat_to_healpix(np.asarray(lon), np.asarray(lat), np.uint8(DEPTH), ellipsoid="WGS84")
    return pd.DataFrame({"x": x, "y": y, "lon": lon, "lat": lat, "cell15": cell.astype("uint64")})


def main(names: list[str]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    site = raba.eea_site(SITE)
    gpath = OUT / "grid.parquet"
    if not gpath.exists():
        grid(site).to_parquet(gpath, index=False)
    g = pd.read_parquet(gpath)
    pts = shapely.points(g.x.values, g.y.values)
    listing = raba.listing()
    for name in names:
        sdate = raba.snapshot_date(name)
        out = OUT / f"{sdate}.parquet"
        if out.exists():
            print(f"[fire] {sdate} already sampled", flush=True)
            continue
        if name not in listing:
            raise SystemExit(f"{name} not in archive")
        archive = raba.download(name)
        shp = raba.unpack(archive)
        crs = raba.source_crs(shp, int(sdate[:4]))
        gdf = raba.read_clip(shp, site, crs)
        hit_pt, hit_poly = gdf.sindex.query(pts, predicate="within")
        code = np.full(len(pts), -1, dtype=np.int32)
        # where repaired polygons overlap, keep the first hit; count overlaps for the record
        first = ~pd.Series(hit_pt).duplicated().values
        code[hit_pt[first]] = gdf["RABA_ID"].fillna(-1).values.astype("int32")[hit_poly[first]]
        pd.DataFrame({"raba_id": code}).to_parquet(out, index=False)
        meta = {"file": name, "url": raba.ARCHIVE + name, "snapshot_date": sdate, "source_crs": crs,
                "polygons": len(gdf), "points": len(pts), "unmapped_points": int((code < 0).sum()),
                "points_in_overlapping_polygons": int((~first).sum()),
                "retrieved": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        (OUT / f"{sdate}.json").write_text(json.dumps(meta, indent=2) + "\n")
        print(f"[fire] {name}: {meta}", flush=True)
        archive.unlink()
        shutil.rmtree(raba.WORK / archive.stem, ignore_errors=True)


if __name__ == "__main__":
    main(sys.argv[1:])
