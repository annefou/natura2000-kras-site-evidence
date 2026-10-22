#!/usr/bin/env python3
"""Site-level aggregates of one snapshot of the Slovenian Land Use database (MKGP "RABA").

    pixi run python pipeline/raba.py --snapshot RABA_2002_SHP.ZIP
    pixi run python pipeline/raba.py --latest            # newest month-end snapshot in the archive

Source: the public archive https://rkg.gov.si/arhiv/RABA/?C=N;O=D (monthly from March 2015,
several versions a year 2006-2014, one in 2002). Methodology: RABA_Read_me.pdf in the same folder.

What this writes, all under results/local/ (gitignored; NOTHING derived from RABA is committed or
published until MKGP gives written permission: the 2002 archive's Terms and Conditions restrict use
to internal / personal / non-commercial, with prior notification, and forbid non-internal
reproduction or display without written permission; the current readme states no licence):

  results/local/raba/<date>/areas.csv      area per area of interest and RABA_ID class (ha), exact vector areas
  results/local/raba/<date>/currency.csv   per area of interest: how recently its polygons were last changed or
                                     reviewed (D_OD), area-weighted
  results/local/raba/<date>/cells.parquet  per HEALPix cell (WGS84, NESTED, depth from config) and service class:
                                     area estimated from a regular 25 m sample grid (each point 625 m2)
  results/local/raba/<date>/snapshot.json  which file, its URL, size, CRS, retrieval time, polygon count

Areas of interest (from config/study.toml [raba]): the Natura 2000 site(s), each also split into its
separate parts, plus any extra site listed for comparison. Boundaries: EEA Natura 2000 end-2024
release, requested in EPSG:3794 (D96/TM). Data up to 2018 are in D48/GK (EPSG:3912) and are
reprojected (RABA_Read_me.pdf: "Data up to and including 2018 are in the D48/GK coordinate system.
Data since January 2019 are in the D96/TM coordinate system.").

The downloaded archive and its unpacked shapefile are deleted afterwards (disk), unless --keep.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tomllib
from datetime import date, datetime, timezone
from pathlib import Path

import geopandas as gpd
import httpx
import numpy as np
import pandas as pd
import pyogrio
import shapely
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import unary_union

REPO = Path(__file__).resolve().parents[1]
CONFIG = tomllib.loads((REPO / "config" / "study.toml").read_text())
ARCHIVE = "https://rkg.gov.si/arhiv/RABA/"
EEA_SITES = "https://bio.discomap.eea.europa.eu/arcgis/rest/services/ProtectedSites/Natura2000Sites/MapServer/2/query"
WORK = REPO / "data" / "raba"
OUT = REPO / "results" / "local" / "raba"  # gitignored: RABA-derived results are not published (MKGP permission pending)
SAMPLE_M = 25

# RABA_ID code list, copied from RABA_Read_me.pdf (MA Farm register service, August 2026).
LABELS = {
    1100: "Arable land", 1160: "Hop field", 1180: "Permanent crops on arable land", 1190: "Greenhouse",
    1211: "Vineyard", 1212: "Nursery", 1221: "Intensive orchard", 1222: "Extensive orchard", 1230: "Olive grove",
    1240: "Other permanent crop", 1300: "Permanent grassland", 1321: "Swampy meadow",
    1410: "Overgrown agricultural area", 1420: "Forest plantation", 1500: "Trees and shrubs",
    1600: "Uncultivated agricultural land", 1800: "Forest trees on agricultural land", 2000: "Forest",
    3000: "Built-up area and related surface", 4100: "Swamp", 4210: "Reed", 4220: "Other marshy area",
    5000: "Dried open area with special vegetation", 6000: "Open area with little or no vegetation", 7000: "Water",
}
# The 2002 version uses an older code list (its legend, slo_legenda_new.avl, inside RABA_2002_SHP.ZIP;
# Slovenian labels as written there, English in brackets is ours). Two meadow codes replace 1300, and
# 1500 means mixed agricultural land and forest, not trees and shrubs.
LABELS_2002 = {
    1100: "Njive in vrtovi (arable land and gardens)", 1160: "Hmeljišča (hop fields)", 1211: "Vinogradi (vineyards)",
    1221: "Intenzivni sadovnjaki (intensive orchards)", 1222: "Ekstenzivni sadovnjaki (extensive orchards)",
    1230: "Oljčni nasadi (olive groves)", 1240: "Ostali trajni nasadi (other permanent crops)",
    1310: "Intenzivni travniki (intensive meadows)", 1321: "Barjanski travniki (bog meadows)",
    1322: "Ekstenzivni travniki (extensive meadows)", 1410: "Zemljišča v zaraščanju (land being overgrown)",
    1420: "Plantaže gozdnega drevja (forest tree plantations)",
    1500: "Mešana raba zemljišč - kmetijska zemljišča in gozd (mixed use: agricultural land and forest)",
    2000: "Gozd in ostale poraščene površine (forest and other wooded areas)",
    3000: "Pozidana in sorodna zemljišča (built-up and related land)", 4100: "Barje (bog)", 4210: "Trstičje (reed)",
    4220: "Ostala zamočvirjena zemljišča (other marshy land)",
    5000: "Suha, odprta zemljišča s posebnim rastlinskim pokrovom (dry open land with special plant cover)",
    6000: "Odprta zemljišča brez ali z nepomembnim rastlinskim pokrovom (open land with little or no plant cover)",
    7000: "Vode (water)",
}
# Service classes (what a site manager asked for): defined here, once. 1310/1322 are the 2002 meadow codes.
SERVICE = {"permanent_grassland": {1300, 1310, 1321, 1322}, "overgrown_agricultural": {1410, 1600, 1800},
           "trees_and_shrubs": {1500}, "forest": {2000}}


def service_class(code: int) -> str:
    return next((k for k, v in SERVICE.items() if code in v), "other")


def listing() -> list[str]:
    html = httpx.get(ARCHIVE, params={"C": "N", "O": "D"}, timeout=60).text
    return sorted(set(re.findall(r'href="(RABA_[0-9_A-Z]+\.(?:zip|ZIP|rar|RAR))"', html)))


def latest_month_end(names: list[str]) -> str:
    """Newest snapshot dated on the last day of a month (the regular monthly release)."""
    import calendar
    best = None
    for n in names:
        m = re.match(r"RABA_(\d{4})_(\d{2})_(\d{2})\.", n)
        if m:
            y, mo, d = map(int, m.groups())
            if d == calendar.monthrange(y, mo)[1] and (best is None or (y, mo, d) > best[0]):
                best = ((y, mo, d), n)
    if not best:
        raise SystemExit("no month-end snapshot found in the RABA archive listing")
    return best[1]


def snapshot_date(name: str) -> str:
    m = re.match(r"RABA_(\d{4})_(\d{2})_(\d{2})", name)
    if m:
        return "-".join(m.groups())
    m = re.match(r"RABA_(\d{4})_", name)
    return m.group(1)  # 2002: the archive gives the year only


def download(name: str) -> Path:
    WORK.mkdir(parents=True, exist_ok=True)
    path = WORK / name
    url = ARCHIVE + name
    head = httpx.head(url, timeout=60, follow_redirects=True)
    size = int(head.headers.get("content-length", 0))
    if path.exists() and path.stat().st_size == size:
        return path
    print(f"[raba] downloading {url} ({size / 1e6:,.0f} MB)", flush=True)
    with httpx.stream("GET", url, timeout=1800, follow_redirects=True) as r:
        r.raise_for_status()
        with path.open("wb") as fh:
            for chunk in r.iter_bytes(1 << 20):
                fh.write(chunk)
    if path.stat().st_size != size:
        raise SystemExit(f"{name}: got {path.stat().st_size} bytes, expected {size}")
    return path


def unpack(archive: Path) -> Path:
    """Unpack only the shapefile parts (bsdtar reads both ZIP and RAR)."""
    dest = WORK / archive.stem
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir()
    members = subprocess.run(["bsdtar", "-tf", str(archive)], check=True, capture_output=True, text=True).stdout.split("\n")
    keep = [m for m in members if re.search(r"\.(shp|shx|dbf|prj|cpg)$", m, re.I)]
    if not keep:
        raise SystemExit(f"{archive.name}: no shapefile inside ({members[:10]})")
    subprocess.run(["bsdtar", "-xf", str(archive), "-C", str(dest), *keep], check=True)
    shps = sorted(dest.rglob("*.shp"), key=lambda p: -p.stat().st_size)
    return shps[0]


def eea_site(code: str) -> shapely.Geometry:
    r = httpx.get(EEA_SITES, params={"where": f"SITECODE='{code}'", "returnGeometry": "true", "outSR": "3794",
                                     "f": "geojson"}, timeout=120)
    r.raise_for_status()
    feats = r.json()["features"]
    if not feats:
        raise SystemExit(f"{code} not in the EEA Natura 2000 release")
    return unary_union([shape(f["geometry"]) for f in feats])


def areas_of_interest() -> dict[str, shapely.Geometry]:
    """Each configured site, its separate parts (ordered north to south), and comparison sites."""
    cfg = CONFIG["raba"]
    aoi = {}
    for code in cfg["sites"]:
        g = eea_site(code)
        aoi[code] = g
        parts = sorted(getattr(g, "geoms", [g]), key=lambda p: -p.centroid.y)
        if len(parts) > 1:
            for i, p in enumerate(parts, 1):
                aoi[f"{code}#part{i}"] = p
    for code in cfg.get("comparison_sites", []):
        aoi[code] = eea_site(code)
    return aoi


def source_crs(shp: Path, year: int) -> str:
    prj = shp.with_suffix(".prj")
    if prj.exists() and prj.read_text().strip():
        info = pyogrio.read_info(shp)
        if info.get("crs"):
            return info["crs"]
    return "EPSG:3912" if year <= 2018 else "EPSG:3794"


def read_clip(shp: Path, aoi_union, crs: str) -> gpd.GeoDataFrame:
    bbox_src = Transformer.from_crs("EPSG:3794", crs, always_xy=True).transform_bounds(*aoi_union.bounds)
    # Field names differ between versions: 2002 has RABA (code) and no D_OD; later ones RABA_ID, D_OD.
    fields = list(pyogrio.read_info(shp)["fields"])
    rename = {c: ("RABA_ID" if c.upper() in ("RABA_ID", "RABA") else c.upper()) for c in fields
              if c.upper() in ("RABA_ID", "RABA", "D_OD", "RABA_PID")}
    if "RABA_ID" not in rename.values():
        raise SystemExit(f"{shp.name}: no land-use code field among {fields}")
    gdf = pyogrio.read_dataframe(shp, columns=list(rename), bbox=tuple(bbox_src)).rename(columns=rename)
    gdf = gdf.set_crs(crs, allow_override=True).to_crs("EPSG:3794")
    gdf["RABA_ID"] = pd.to_numeric(gdf["RABA_ID"], errors="coerce").astype("Int64")
    gdf["geometry"] = shapely.make_valid(gdf.geometry.values)
    return gdf[gdf.intersects(aoi_union)].reset_index(drop=True)


def parse_dod(values: pd.Series) -> pd.Series:
    return pd.to_datetime(values.astype(str).str.slice(0, 10), errors="coerce", format="mixed")


def aggregate(gdf: gpd.GeoDataFrame, aoi: dict, snap_date: date) -> tuple[pd.DataFrame, pd.DataFrame]:
    area_rows, cur_rows = [], []
    labels = LABELS_2002 if snap_date.year == 2002 else LABELS
    has_dod = "D_OD" in gdf.columns
    if has_dod:
        gdf["dod"] = parse_dod(gdf["D_OD"])
    sindex = gdf.sindex
    for name, geom in aoi.items():
        idx = sindex.query(geom, predicate="intersects")
        sub = gdf.iloc[idx]
        inter = shapely.intersection(sub.geometry.values, geom)
        a = shapely.area(inter) / 1e4
        df = pd.DataFrame({"raba_id": sub["RABA_ID"].values, "area_ha": a})
        if has_dod:
            df["dod"] = sub["dod"].values
        total = geom.area / 1e4
        for code, ha in df.groupby("raba_id")["area_ha"].sum().items():
            area_rows.append({"area_of_interest": name, "raba_id": int(code), "label": labels.get(int(code), ""),
                              "service_class": service_class(int(code)), "area_ha": round(float(ha), 2),
                              "share_pct": round(100 * float(ha) / total, 3)})
        row = {"area_of_interest": name, "aoi_area_ha": round(total, 2), "mapped_ha": round(float(df.area_ha.sum()), 2)}
        if has_dod and df["dod"].notna().any():
            d = df.dropna(subset=["dod"]).sort_values("dod")
            age = (pd.Timestamp(snap_date) - d["dod"]).dt.days / 365.25
            w = d["area_ha"].values
            cum = np.cumsum(w) / w.sum()
            row.update({
                "dod_median": d["dod"].iloc[int(np.searchsorted(cum, 0.5))].date().isoformat(),
                "dod_oldest": d["dod"].min().date().isoformat(), "dod_newest": d["dod"].max().date().isoformat(),
                "share_reviewed_last_12_months_pct": round(100 * w[age.values <= 1].sum() / w.sum(), 2),
                "share_reviewed_last_36_months_pct": round(100 * w[age.values <= 3].sum() / w.sum(), 2),
                "share_older_than_5_years_pct": round(100 * w[age.values > 5].sum() / w.sum(), 2),
                "area_with_dod_ha": round(float(w.sum()), 2)})
        cur_rows.append(row)
    return pd.DataFrame(area_rows), pd.DataFrame(cur_rows)


def cells(gdf: gpd.GeoDataFrame, geom, depth: int) -> pd.DataFrame:
    """Service-class area per HEALPix cell, from a 25 m sample grid inside `geom` (EPSG:3794)."""
    import healpix_geo.nested as hn
    minx, miny, maxx, maxy = geom.bounds
    xs = np.arange(minx + SAMPLE_M / 2, maxx, SAMPLE_M)
    ys = np.arange(miny + SAMPLE_M / 2, maxy, SAMPLE_M)
    X, Y = np.meshgrid(xs, ys)
    pts = shapely.points(X.ravel(), Y.ravel())
    inside = shapely.contains_xy(geom, X.ravel(), Y.ravel())
    pts = pts[inside]
    hit_pt, hit_poly = gdf.sindex.query(pts, predicate="within")
    code = np.full(len(pts), -1, dtype=np.int64)
    code[hit_pt] = gdf["RABA_ID"].values.astype("int64")[hit_poly]
    lon, lat = Transformer.from_crs("EPSG:3794", "EPSG:4326", always_xy=True).transform(
        shapely.get_x(pts), shapely.get_y(pts))
    cell = hn.lonlat_to_healpix(np.asarray(lon), np.asarray(lat), np.uint8(depth), ellipsoid="WGS84")
    cls = np.array([service_class(int(c)) if c >= 0 else "unmapped" for c in code])
    df = pd.DataFrame({"cell_ids": cell.astype("uint64"), "service_class": cls})
    if "dod" in gdf.columns:  # date of last change/review of the polygon each sample point falls in
        dod = np.full(len(pts), np.datetime64("NaT"), dtype="datetime64[ns]")
        dod[hit_pt] = gdf["dod"].values.astype("datetime64[ns]")[hit_poly]
        df["dod"] = dod
    out = df.groupby(["cell_ids", "service_class"]).size().rename("points").reset_index()
    out["area_ha"] = out["points"] * SAMPLE_M ** 2 / 1e4
    if "dod" in df.columns:
        med = df.groupby("cell_ids")["dod"].median().rename("cell_dod_median")
        out = out.merge(med, left_on="cell_ids", right_index=True, how="left")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--snapshot", help="archive file name, e.g. RABA_2024_06_30.zip")
    g.add_argument("--latest", action="store_true", help="newest month-end snapshot in the archive")
    ap.add_argument("--keep", action="store_true", help="keep the downloaded archive and shapefile")
    args = ap.parse_args()

    names = listing()
    name = latest_month_end(names) if args.latest else args.snapshot
    if name not in names:
        raise SystemExit(f"{name} is not in {ARCHIVE}")
    sdate = snapshot_date(name)
    out = OUT / sdate
    out.mkdir(parents=True, exist_ok=True)
    year = int(sdate[:4])
    snap_day = date.fromisoformat(sdate) if len(sdate) == 10 else date(year, 12, 31)

    aoi = areas_of_interest()
    union = unary_union(list(aoi.values()))
    archive = download(name)
    shp = unpack(archive)
    crs = source_crs(shp, year)
    gdf = read_clip(shp, union, crs)
    print(f"[raba] {name}: {len(gdf):,} polygons intersect the areas of interest (source CRS {crs})", flush=True)

    areas, currency = aggregate(gdf, aoi, snap_day)
    areas.to_csv(out / "areas.csv", index=False)
    currency.to_csv(out / "currency.csv", index=False)
    site = CONFIG["study"]["site"]
    cells(gdf, aoi[site], CONFIG["raba"]["healpix_depth"]).to_parquet(out / "cells.parquet", index=False)
    meta = {"file": name, "url": ARCHIVE + name, "snapshot_date": sdate, "bytes": archive.stat().st_size,
            "source_crs": crs, "polygons_in_areas_of_interest": len(gdf), "has_D_OD": "D_OD" in gdf.columns,
            "retrieved": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "methodology": ARCHIVE + "RABA_Read_me.pdf",
            "licence": "not stated in RABA_Read_me.pdf; the 2002 archive's Terms and Conditions restrict use (internal / non-commercial, prior notification, no non-internal display without written permission). Local use only; ask raba.mkgp@gov.si",
            "boundaries": "EEA Natura 2000 end-2024 release, EPSG:3794",
            "cell_grid": {"depth": CONFIG["raba"]["healpix_depth"], "ellipsoid": "WGS84", "indexing": "nested",
                          "sample_spacing_m": SAMPLE_M}}
    (out / "snapshot.json").write_text(json.dumps(meta, indent=2) + "\n")
    top = areas[areas.area_of_interest == site].groupby("service_class")["area_ha"].sum()
    print(f"[raba] {site} {sdate}: " + ", ".join(f"{k} {v:,.0f} ha" for k, v in top.items()))
    print(currency.to_string(index=False))
    if not args.keep:
        archive.unlink()
        shutil.rmtree(WORK / archive.stem, ignore_errors=True)
    print(f"[raba] {out.relative_to(REPO)}/")


if __name__ == "__main__":
    sys.exit(main())
