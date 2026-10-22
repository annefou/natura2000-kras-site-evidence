#!/usr/bin/env python3
"""LOCAL. Did former grassland that became overgrown / scrub burn more than its share in the 2022 Kras fire?

    pixi run python pipeline/fire/fire_analysis.py

Inputs (all local, gitignored):
  results/local/fire/points/*.parquet   RABA_ID per 25 m point (sample_points.py)
  results/local/fire/input/EMSR604/     Copernicus EMS Rapid Mapping EMSR604, grading monit01 (27 Jul 2022),
                                        "Burnt area" polygon
  results/local/fire/input/dem/         Copernicus DEM GLO-30 tile N45 E013 (confounder check only)
Outputs: results/local/fire/tables/*.csv, results/local/fire/figures/*.png, results/local/fire/numbers.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import healpix_geo.nested as hn  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import shapely  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
from matplotlib.colors import BoundaryNorm, ListedColormap, LinearSegmentedColormap, TwoSlopeNorm  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from PIL import Image  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "pipeline"))
import raba  # noqa: E402

FIRE = REPO / "results" / "local" / "fire"
PTS = FIRE / "points"
PERIM_SRC = "effis" if "--perimeter=effis" in sys.argv else "ems"   # ems = main; effis = sensitivity
SUFFIX = "" if PERIM_SRC == "ems" else "_effis"
TAB = FIRE / f"tables{SUFFIX}"
FIG = FIRE / f"figures{SUFFIX}"
EFFIS = FIRE / "input" / "effis" / "effis_bbox.geojson"   # EFFIS WFS ms:modis.ba.poly, polygon id 206388
SITE = raba.CONFIG["study"]["site"]
DEPTH = raba.CONFIG["raba"]["healpix_depth"]  # 15
PT_HA = raba.SAMPLE_M ** 2 / 1e4
PERIM = (FIRE / "input" / "EMSR604" / "EMSR604_AOI01_GRA_MONIT01_r1_RTP01_v2" /
         "EMSR604_AOI01_GRA_MONIT01_observedEventA_r1_v2.shp")
DEM = [FIRE / "input" / "dem" / f"Copernicus_DSM_COG_10_N45_00_E01{e}_00_DEM.tif" for e in (3, 4)]
PRE = ["2009-10-16", "2012-12-04", "2015-06-30", "2018-06-30", "2021-07-06", "2022-06-30"]
POST = ["2024-06-30", "2026-09-30"]
EDGE_M, RING_M = 250, 3000          # exclusion band outside the perimeter; outer radius of the ring control
BOOT, SEED = 5000, 20220717
BLOCK_DEPTHS = [12, 11, 13]         # first = main (~1.6 km blocks); others = sensitivity

G = {1300, 1321}                    # grassland
W = {1410, 1500, 2000}              # overgrown / scrub / forest (the hypothesis' target classes)
GROUPS = [("Grassland (1300, 1321)", {1300, 1321}), ("Overgrown agricultural land (1410)", {1410}),
          ("Trees and shrubs (1500)", {1500}), ("Forest (2000)", {2000}),
          ("Other woody on agricultural land (1420, 1600, 1800)", {1420, 1600, 1800})]
OTHER = "Other (crops, built-up, open, water, unmapped)"
NOTE = ("LOCAL / INTERNAL. Land use: MKGP Land Use database (RABA), not for publication pending MKGP permission. "
        "Burnt area: Copernicus EMS EMSR604 (© European Union). Draft, not reviewed.")
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
C_GRASS, C_OVER, C_FOREST, C_OTHER = "#eda100", "#6250d6", "#1baf7a", "#d9d8d3"
BLUE, ORANGE = "#2a78d6", "#eb6834"
plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "text.color": INK, "axes.spines.top": False,
                     "axes.spines.right": False, "font.size": 9})


def group_of(codes: np.ndarray) -> np.ndarray:
    out = np.full(len(codes), OTHER, dtype=object)
    for name, s in GROUPS:
        out[np.isin(codes, list(s))] = name
    return out


def load() -> tuple[pd.DataFrame, dict]:
    g = pd.read_parquet(PTS / "grid.parquet")
    for s in PRE + POST:
        g[s] = pd.read_parquet(PTS / f"{s}.parquet")["raba_id"].values
    site = raba.eea_site(SITE)
    if PERIM_SRC == "ems":
        fire = gpd.read_file(PERIM).to_crs(3794).union_all()
    else:
        e = gpd.read_file(EFFIS)
        fire = e[e["id"].astype(str) == "206388"].to_crs(3794).union_all()
    g["burned"] = shapely.contains_xy(fire, g.x.values, g.y.values)
    pts = shapely.points(g.x.values, g.y.values)
    g["dist_m"] = shapely.distance(fire, pts)  # 0 inside
    parts = sorted(getattr(site, "geoms", [site]), key=lambda p: -p.centroid.y)
    fpart = max(range(len(parts)), key=lambda i: parts[i].intersection(fire).area)
    g["part"] = 0
    for i, p in enumerate(parts):
        g.loc[shapely.contains_xy(p, g.x.values, g.y.values), "part"] = i + 1
    g["zone_A"] = g.burned | ((g.part == fpart + 1) & (g.dist_m > EDGE_M))
    g["zone_B"] = g.burned | ((g.dist_m > EDGE_M) & (g.dist_m <= RING_M))
    geo = {"site": site, "fire": fire, "fire_part": fpart + 1, "parts": parts}
    return g, geo


def dem_sample(g: pd.DataFrame) -> None:
    # Copernicus DEM GLO-30 tiles N45 E013 and E014 (both 3600 x 3600 at 1 arcsec here), side by side;
    # (PixelIsPoint, column 0 of each tile at its west edge, so they abut without overlap)
    a0, a1 = (np.array(Image.open(p)).astype("float64") for p in DEM)
    a = np.hstack([a0, a1])
    d = 1 / 3600  # PixelIsPoint: pixel (0,0) centre at (13.0 E, 46.0 N)
    col = np.rint((g.lon.values - 13.0) / d).astype(int)
    row = np.rint((46.0 - g.lat.values) / d).astype(int)
    lat0 = np.radians(45.8)
    dy, dx = 6371008.8 * np.radians(d), 6371008.8 * np.radians(d) * np.cos(lat0)
    gy, gx = np.gradient(a, dy, dx)
    g["elev_m"] = a[row, col]
    g["slope_deg"] = np.degrees(np.arctan(np.hypot(gx, gy)))[row, col]
    # aspect: direction the slope faces, degrees clockwise from north (rows go south)
    g["aspect_deg"] = (np.degrees(np.arctan2(-gx, gy)) % 360)[row, col]


# ---------------------------------------------------------------------------------------------
def counts_by_block(blocks: np.ndarray, cls: np.ndarray, burned: np.ndarray, labels: list[str]):
    ub, bi = np.unique(blocks, return_inverse=True)
    ci = pd.Categorical(cls, categories=labels).codes
    T = np.zeros((len(ub), len(labels), 2))
    np.add.at(T, (bi, ci, burned.astype(int)), 1)
    return T  # blocks x classes x [unburned, burned] point counts


def stats_from(T: np.ndarray) -> dict[str, np.ndarray]:
    """T: ... x classes x 2 -> per class burn rate, share in fire, share in control, OR vs rest, RBR."""
    u, b = T[..., 0], T[..., 1]
    U, B = u.sum(-1, keepdims=True), b.sum(-1, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        rate = b / (b + u)
        rate_all = B / (B + U)
        orr = (b / u) / ((B - b) / (U - u))
        return {"burn_rate": rate, "share_fire": b / B, "share_ctrl": u / U, "odds_ratio": orr,
                "rbr": rate / rate_all}


def boot(T: np.ndarray, n=BOOT, seed=SEED) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    nb = T.shape[0]
    flat = T.reshape(nb, -1)
    w = np.stack([np.bincount(rng.integers(0, nb, nb), minlength=nb) for _ in range(n)])
    Tb = (w @ flat).reshape(n, *T.shape[1:])
    return stats_from(Tb)


def class_table(g: pd.DataFrame, zone: str, cls_col: str, labels: list[str], depth: int, ref: str | None = None):
    sub = g[g[zone] & g[cls_col].isin(labels)]
    blocks = sub.cell15.values >> np.uint64(2 * (DEPTH - depth))
    T = counts_by_block(blocks, sub[cls_col].values, sub.burned.values, labels)
    est, bs = stats_from(T.sum(0)), boot(T)
    rows = []
    for i, lab in enumerate(labels):
        r = {"zone": zone, "block_depth": depth, "n_blocks": T.shape[0], "class": lab,
             "area_burned_ha": T[:, i, 1].sum() * PT_HA, "area_unburned_ha": T[:, i, 0].sum() * PT_HA}
        for k in ("share_fire", "share_ctrl", "burn_rate", "rbr", "odds_ratio"):
            v = bs[k][:, i]
            v = v[np.isfinite(v)]
            r[k] = float(est[k][i])
            r[k + "_lo"], r[k + "_hi"] = (np.percentile(v, [2.5, 97.5]) if len(v) else (np.nan, np.nan))
        if ref is not None:  # rate ratio and OR of each class vs the reference class
            j = labels.index(ref)
            rr = bs["burn_rate"][:, i] / bs["burn_rate"][:, j]
            u, b = T.sum(0)[:, 0], T.sum(0)[:, 1]
            r["rate_ratio_vs_ref"] = float((b[i] / (b[i] + u[i])) / (b[j] / (b[j] + u[j])))
            r["rate_ratio_lo"], r["rate_ratio_hi"] = np.nanpercentile(rr[np.isfinite(rr)], [2.5, 97.5])
            Tb_or = (bs["burn_rate"][:, i] / (1 - bs["burn_rate"][:, i])) / (bs["burn_rate"][:, j] / (1 - bs["burn_rate"][:, j]))
            r["or_vs_ref"] = float((b[i] / u[i]) / (b[j] / u[j]))
            r["or_vs_ref_lo"], r["or_vs_ref_hi"] = np.nanpercentile(Tb_or[np.isfinite(Tb_or)], [2.5, 97.5])
            r["p_boot_rate_ratio_le_1"] = float(np.mean(rr[np.isfinite(rr)] <= 1))
        rows.append(r)
    return pd.DataFrame(rows)


def mantel_haenszel(sub: pd.DataFrame, expo: str, ref: str, strata: pd.Series) -> float:
    num = den = 0.0
    for _, s in sub.groupby(strata.loc[sub.index]):
        e, r = s[s.traj == expo], s[s.traj == ref]
        a, b = e.burned.sum(), (~e.burned).sum()
        c, d = r.burned.sum(), (~r.burned).sum()
        n = a + b + c + d
        if n:
            num += a * d / n
            den += b * c / n
    return num / den if den else np.nan


# ---------------------------------------------------------------------------------------------
def trajectories(g: pd.DataFrame) -> None:
    C = g[PRE].values
    inG, inW = np.isin(C, list(G)), np.isin(C, list(W))
    start = inG[:, 0]
    persistent = np.zeros(len(g), bool)
    first_k = np.full(len(g), -1)
    for k in (1, 2, 3):  # 2012, 2015, 2018: at least two later pre-fire snapshots confirm the change
        hit = start & inW[:, k:].all(1) & ~persistent
        first_k[hit] = k
        persistent |= hit
    recent = start & ~persistent & inW[:, 4:].all(1)  # first seen 2021, confirmed only by 2022-06
    retained = start & inG[:, -1]
    strict = start & inG.all(1)
    t = np.full(len(g), "not grassland in 2009", dtype=object)
    t[start] = "grassland 2009 -> other"
    t[retained] = "grassland retained (2009 and 2022-06)"
    t[recent] = "grassland -> overgrowth, recent (2021, 1 confirmation)"
    t[persistent] = "grassland -> overgrowth, persistent (2012-2018, >=2 confirmations)"
    g["traj"] = t
    g["traj_strict"] = np.where(strict, "grassland in all six pre-fire snapshots", t)
    g["traj_first"] = np.where(first_k >= 0, np.array(PRE)[np.clip(first_k, 0, None)], "")
    g["traj_target_2022"] = np.where(persistent | recent, C[:, -1], -1)


def fuel(g: pd.DataFrame) -> pd.DataFrame:
    snaps = PRE + POST
    C = g[snaps].values
    F = {1410, 1500, 1600, 1800, 1420, 2000}
    O = {1410, 1500, 1600, 1800}
    inF = np.isin(C, list(F))
    gain = np.zeros(len(g), bool)
    for k in range(1, len(snaps) - 2):  # at least two later snapshots confirm
        gain |= ~inF[:, 0] & inF[:, k:].all(1)
    loss = np.zeros(len(g), bool)
    for k in range(1, len(snaps) - 2):
        loss |= inF[:, 0] & ~inF[:, k:].any(1)
    df = pd.DataFrame({"cell15": g.cell15.values, "gain": gain, "loss": loss})
    for s in snaps:
        df[f"over_{s}"] = np.isin(g[s].values, list(O))
    df["burned"] = g.burned.values
    agg = df.groupby("cell15").sum() * PT_HA
    agg["burned_share"] = df.groupby("cell15").burned.mean()
    ov = agg[[f"over_{s}" for s in snaps]].values
    agg["over_net_ha"] = ov[:, -1] - ov[:, 0]
    agg["over_never_decreasing"] = (np.diff(ov, axis=1) >= -1e-9).all(1) & (agg["over_net_ha"] > 0)
    agg["persistent_net_fuel_gain_ha"] = agg["gain"] - agg["loss"]
    return agg.drop(columns="burned").reset_index()


# ---------------------------------------------------------------------------------------------
def cell_polys(ids):
    lon, lat = hn.vertices(np.asarray(ids, dtype=np.uint64), np.uint8(DEPTH), ellipsoid="WGS84")
    return [np.column_stack([lo, la]) for lo, la in zip(lon, lat)]


def to_lonlat(geom):
    return gpd.GeoSeries([geom], crs=3794).to_crs(4326).iloc[0]


def plot_outline(ax, geom, **kw):
    for p in getattr(geom, "geoms", [geom]):
        x, y = p.exterior.xy
        ax.plot(x, y, **kw)
        kw.pop("label", None)


def footer(fig, y=-0.02):
    fig.text(0.01, y, NOTE, fontsize=6.5, color=INK2, va="top")


def fig_map(g, geo, path):
    box = shapely.box(*geo["fire"].bounds).buffer(RING_M + 800)
    sub = g[shapely.contains_xy(box, g.x.values, g.y.values)]
    x0, y1 = sub.x.min(), sub.y.max()
    ix = np.rint((sub.x.values - x0) / raba.SAMPLE_M).astype(int)
    iy = np.rint((y1 - sub.y.values) / raba.SAMPLE_M).astype(int)
    lab = group_of(sub["2022-06-30"].values)
    code = np.select([lab == GROUPS[0][0], np.isin(lab, [GROUPS[1][0], GROUPS[2][0]]), lab == GROUPS[3][0]], [1, 2, 3], 4)
    img = np.zeros((iy.max() + 1, ix.max() + 1))
    img[iy, ix] = code
    img = np.ma.masked_equal(img, 0)
    cmap = ListedColormap([C_GRASS, C_OVER, C_FOREST, C_OTHER])
    fig, ax = plt.subplots(figsize=(8.2, 7.4))
    ext = [x0 - 12.5, x0 + (ix.max() + 0.5) * 25, y1 - (iy.max() + 0.5) * 25, y1 + 12.5]
    ax.imshow(img, cmap=cmap, norm=BoundaryNorm([0.5, 1.5, 2.5, 3.5, 4.5], 4), extent=ext, interpolation="nearest")
    plot_outline(ax, geo["fire"], color=INK, lw=1.6)
    plot_outline(ax, geo["fire"].buffer(RING_M), color=INK, lw=0.9, ls=(0, (4, 3)))
    site_clip = geo["site"].intersection(box)
    for p in getattr(site_clip.boundary, "geoms", [site_clip.boundary]):
        x, y = p.xy
        ax.plot(x, y, color=INK2, lw=0.6)
    ax.set_xlim(ext[0], ext[1])
    ax.set_ylim(ext[2], ext[3])
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    sb_x, sb_y = ext[0] + 600, ext[2] + 600
    ax.plot([sb_x, sb_x + 2000], [sb_y, sb_y], color=INK, lw=2.5, solid_capstyle="butt")
    ax.text(sb_x + 1000, sb_y + 180, "2 km", ha="center", fontsize=8)
    u = g[g.burned]
    shares = pd.Series(group_of(u["2022-06-30"].values)).value_counts(normalize=True) * 100
    over = shares.get(GROUPS[1][0], 0) + shares.get(GROUPS[2][0], 0)
    handles = [Patch(color=C_GRASS, label=f"Grassland 1300/1321 ({shares.get(GROUPS[0][0], 0):.1f} % of burnt area)"),
               Patch(color=C_OVER, label=f"Overgrown 1410 + trees and shrubs 1500 ({over:.1f} %)"),
               Patch(color=C_FOREST, label=f"Forest 2000 ({shares.get(GROUPS[3][0], 0):.1f} %)"),
               Patch(color=C_OTHER, label="Other classes"),
               Line2D([], [], color=INK, lw=1.6, label=("Burnt area, Copernicus EMS EMSR604 (SPOT 24 Jul 2022)" if PERIM_SRC == "ems" else "Burnt area, EFFIS id 206388")),
               Line2D([], [], color=INK, lw=0.9, ls=(0, (4, 3)), label=f"{RING_M / 1000:.0f} km ring (control B)"),
               Line2D([], [], color=INK2, lw=0.6, label=f"SAC {SITE} boundary (land use shown only inside)")]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=2, frameon=False, fontsize=7.5)
    ax.set_title("2022 Kras fire over pre-fire land use (RABA 30 June 2022, 25 m sample)", loc="left", fontsize=11)
    footer(fig, -0.06)
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def fig_rates(cls_tab, trj_tab, path):
    fig, axes = plt.subplots(2, 1, figsize=(8.6, 7.6), gridspec_kw={"height_ratios": [5, 2.6], "hspace": 0.55})
    zones = [("zone_A", "Control A: rest of the SAC part with the fire", BLUE, 0.17),
             ("zone_B", f"Control B: {EDGE_M}-{RING_M} m ring around the fire", ORANGE, -0.17)]
    labs = [n for n, _ in GROUPS] + [OTHER]
    ax = axes[0]
    for z, zl, col, off in zones:
        t = cls_tab[(cls_tab.zone == z) & (cls_tab.block_depth == BLOCK_DEPTHS[0])].set_index("class").reindex(labs)
        y = np.arange(len(labs))[::-1] + off
        ax.errorbar(t.odds_ratio, y, xerr=[t.odds_ratio - t.odds_ratio_lo, t.odds_ratio_hi - t.odds_ratio],
                    fmt="o", ms=7, color=col, ecolor=col, elinewidth=2, capsize=0, label=zl,
                    markeredgecolor=SURF, markeredgewidth=1.5)
    ax.axvline(1, color=INK2, lw=0.8)
    ax.set_xscale("log")
    ax.set_yticks(np.arange(len(labs))[::-1], [l.replace(" (", "\n(") for l in labs], fontsize=8)
    ax.set_xticks([0.1, 0.2, 0.5, 1, 2, 5], ["0.1", "0.2", "0.5", "1", "2", "5"])
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xlabel("odds ratio of burning vs all other land (log scale; 95 % block-bootstrap CI)")
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_title("A. Pre-fire land-use class (RABA 2022-06-30): did it burn more than its share?", loc="left", fontsize=10)
    ax.legend(frameon=False, fontsize=7.5, loc="upper center", bbox_to_anchor=(0.45, -0.17), ncol=2)
    ax = axes[1]
    expo = ["grassland -> overgrowth, persistent (2012-2018, >=2 confirmations)",
            "grassland -> overgrowth, recent (2021, 1 confirmation)"]
    for z, zl, col, off in zones:
        t = trj_tab[(trj_tab.zone == z) & (trj_tab.block_depth == BLOCK_DEPTHS[0])].set_index("class").reindex(expo)
        y = np.arange(len(expo))[::-1] + off
        ax.errorbar(t.rate_ratio_vs_ref, y, xerr=[t.rate_ratio_vs_ref - t.rate_ratio_lo, t.rate_ratio_hi - t.rate_ratio_vs_ref],
                    fmt="o", ms=7, color=col, ecolor=col, elinewidth=2, capsize=0, markeredgecolor=SURF, markeredgewidth=1.5)
    ax.axvline(1, color=INK2, lw=0.8)
    ax.set_xscale("log")
    ax.set_yticks(np.arange(len(expo))[::-1], ["Grassland 2009 -> overgrowth,\npersistent (first seen 2012-2018)",
                                                "Grassland 2009 -> overgrowth,\nrecent (first seen 2021)"], fontsize=8)
    ax.set_xticks([0.8, 1, 1.25, 1.5, 2, 2.5], ["0.8", "1", "1.25", "1.5", "2", "2.5"])
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xlabel("burn rate ratio vs grassland retained 2009 -> 2022 (log scale; 95 % block-bootstrap CI)")
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_title("B. Former grassland that became overgrown, vs grassland that stayed", loc="left", fontsize=10)
    footer(fig, 0.0)
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def fig_fuel(agg, geo, path):
    polys = cell_polys(agg.cell15.values)
    fire_ll = to_lonlat(geo["fire"])
    site_ll = to_lonlat(geo["site"])
    fig, axes = plt.subplots(1, 2, figsize=(13, 6.8), gridspec_kw={"wspace": 0.25})
    seq = LinearSegmentedColormap.from_list("seq", ["#cde2fb", "#5598e7", "#0d366b"])
    v = agg["gain"].values
    m = v > 0
    pc = PolyCollection([p for p, k in zip(polys, m) if k], array=v[m], cmap=seq, edgecolor="none",
                        norm=matplotlib.colors.Normalize(0, 4))
    axes[0].add_collection(pc)
    fig.colorbar(pc, ax=axes[0], shrink=0.55, label="ha per cell (cell ≈ 3.9 ha)", extend="max")
    axes[0].set_title("A. Persistent conversion to woody / overgrown classes\n(1410, 1420, 1500, 1600, 1800, 2000), 2009 -> 2026-09,\n"
                      "confirmed by >= 2 later snapshots", loc="left", fontsize=9.5)
    d = agg["over_net_ha"].values
    div = LinearSegmentedColormap.from_list("div", [BLUE, "#e9e8e4", ORANGE])
    mk = np.abs(d) > 0
    pc2 = PolyCollection([p for p, k in zip(polys, mk) if k], array=d[mk], cmap=div, norm=TwoSlopeNorm(0, -3, 3),
                         edgecolor="none")
    axes[1].add_collection(pc2)
    fig.colorbar(pc2, ax=axes[1], shrink=0.55, label="net change, ha per cell (orange = more overgrowth)", extend="both")
    axes[1].set_title("B. Net change in overgrowth area\n(1410, 1500, 1600, 1800), 2009-10 -> 2026-09\n ", loc="left", fontsize=9.5)
    for ax in axes:
        plot_outline(ax, site_ll, color=INK2, lw=0.6)
        plot_outline(ax, fire_ll, color=INK, lw=1.3)
        ax.set_aspect(1 / np.cos(np.radians(45.7)))
        ax.autoscale_view()
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
    axes[0].legend(handles=[Line2D([], [], color=INK, lw=1.3, label="2022 burnt area (EMSR604)"),
                            Line2D([], [], color=INK2, lw=0.6, label=f"SAC {SITE}")],
                   loc="lower left", frameon=False, fontsize=7.5)
    fig.suptitle(f"Fuel build-up on HEALPix depth-{DEPTH} cells (WGS84, NESTED), SAC {SITE}\n"
                 "Inside the 2022 burnt area, post-2022 changes include fire effects", x=0.01, ha="left", fontsize=10)
    footer(fig, 0.04)
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------------------------
def main():
    for d in (TAB, FIG):
        d.mkdir(parents=True, exist_ok=True)
    g, geo = load()
    dem_sample(g)
    g["grp"] = group_of(g["2022-06-30"].values)
    trajectories(g)
    labs = [n for n, _ in GROUPS] + [OTHER]
    num = {"fire_area_in_site_ha": float(g.burned.sum() * PT_HA),
           "fire_polygon_ha_D96TM": geo["fire"].area / 1e4, "fire_part_of_site": geo["fire_part"],
           "zone_A_ha": float(g.zone_A.sum() * PT_HA), "zone_B_ha": float(g.zone_B.sum() * PT_HA),
           "points": len(g)}

    # per-code composition, pre-fire
    rows = []
    for z in ("zone_A", "zone_B"):
        s = g[g[z]]
        ct = s.groupby(["2022-06-30", "burned"]).size().unstack(fill_value=0) * PT_HA
        for code, r in ct.iterrows():
            rows.append({"zone": z, "raba_id": int(code), "label": raba.LABELS.get(int(code), "unmapped" if code < 0 else ""),
                         "burned_ha": r.get(True, 0), "unburned_ha": r.get(False, 0)})
    comp = pd.DataFrame(rows)
    comp["share_fire_pct"] = 100 * comp.burned_ha / comp.groupby("zone").burned_ha.transform("sum")
    comp["share_ctrl_pct"] = 100 * comp.unburned_ha / comp.groupby("zone").unburned_ha.transform("sum")
    comp.round(3).to_csv(TAB / "composition_by_code_2022-06-30.csv", index=False)

    cls = pd.concat([class_table(g, z, "grp", labs, d) for z in ("zone_A", "zone_B") for d in BLOCK_DEPTHS])
    cls.round(4).to_csv(TAB / "burn_by_class_2022-06-30.csv", index=False)

    tlabs = ["grassland retained (2009 and 2022-06)",
             "grassland -> overgrowth, persistent (2012-2018, >=2 confirmations)",
             "grassland -> overgrowth, recent (2021, 1 confirmation)", "grassland 2009 -> other"]
    trj = pd.concat([class_table(g, z, "traj", tlabs, d, ref=tlabs[0]) for z in ("zone_A", "zone_B") for d in BLOCK_DEPTHS])
    g["traj_s"] = np.where(g.traj_strict == "grassland in all six pre-fire snapshots", g.traj_strict, g.traj)
    slabs = ["grassland in all six pre-fire snapshots", tlabs[1]]
    trj_s = pd.concat([class_table(g, z, "traj_s", slabs, BLOCK_DEPTHS[0], ref=slabs[0]) for z in ("zone_A", "zone_B")])
    trj = pd.concat([trj, trj_s.assign(variant="strict stable reference")])
    trj.round(4).to_csv(TAB / "burn_by_trajectory_2009-2022.csv", index=False)

    # which class did persistent transitions end in (2022-06)?
    pt = g[g.traj == tlabs[1]]
    tgt = pt.groupby(["traj_target_2022", "burned"]).size().unstack(fill_value=0) * PT_HA
    tgt.to_csv(TAB / "persistent_transition_target_class_2022.csv")
    first = pt.groupby(["traj_first", "burned"]).size().unstack(fill_value=0) * PT_HA
    first.to_csv(TAB / "persistent_transition_first_snapshot.csv")

    # confounders: terrain inside fire vs controls; MH OR stratified by elevation x slope tertiles
    conf = []
    for z in ("zone_A", "zone_B"):
        s = g[g[z]]
        for b, ss in s.groupby("burned"):
            conf.append({"zone": z, "burned": bool(b), "area_ha": len(ss) * PT_HA,
                         "elev_median_m": ss.elev_m.median(), "elev_iqr": f"{ss.elev_m.quantile(.25):.0f}-{ss.elev_m.quantile(.75):.0f}",
                         "slope_median_deg": ss.slope_deg.median(),
                         "share_SW_facing_pct": 100 * ss.aspect_deg.between(135, 315).mean(),
                         "x_median_D96": ss.x.median()})
    pd.DataFrame(conf).round(2).to_csv(TAB / "terrain_fire_vs_control.csv", index=False)
    mh = {}
    for z in ("zone_A", "zone_B"):
        s = g[g[z] & g.traj.isin(tlabs[:2])]
        strata = (pd.qcut(s.elev_m, 3, labels=False).astype(str) + "_" + pd.qcut(s.slope_deg, 3, labels=False).astype(str))
        mh[z] = mantel_haenszel(s, tlabs[1], tlabs[0], strata)
        # x (west-east) is a proxy for distance from the western edge where the fire started/spread
        strata2 = strata + "_" + pd.qcut(s.x, 4, labels=False).astype(str)
        mh[z + "_plus_westeast_quartile"] = mantel_haenszel(s, tlabs[1], tlabs[0], strata2)
    num["mantel_haenszel_OR_persistent_vs_retained"] = mh

    agg = fuel(g)
    agg.to_parquet(TAB / "fuel_cells_depth15.parquet", index=False)
    inside = agg.burned_share > 0.5
    num["fuel"] = {"cells": len(agg), "persistent_gain_ha": float(agg.gain.sum()), "persistent_loss_ha": float(agg.loss.sum()),
                   "cells_with_gain_ge_1ha": int((agg.gain >= 1).sum()),
                   "cells_overgrowth_never_decreasing_net_gain": int(agg.over_never_decreasing.sum()),
                   "overgrowth_net_ha_site": float(agg.over_net_ha.sum()),
                   "overgrowth_net_ha_outside_fire_cells": float(agg.loc[~inside, "over_net_ha"].sum()),
                   "persistent_gain_ha_outside_fire_cells": float(agg.loc[~inside, "gain"].sum())}
    # site-level areas per snapshot (service-like groups), for context
    area = {s: (pd.Series(group_of(g[s].values)).value_counts() * PT_HA).round(1).to_dict() for s in PRE + POST}
    pd.DataFrame(area).to_csv(TAB / "site_area_by_group_per_snapshot.csv")
    # what happened to land in the burnt area after the fire
    b = g[g.burned]
    post = pd.crosstab(group_of(b["2022-06-30"].values), group_of(b["2024-06-30"].values)) * PT_HA
    post.to_csv(TAB / "burnt_area_flows_2022-06_to_2024-06.csv")

    (FIRE / f"numbers{SUFFIX}.json").write_text(json.dumps(num, indent=2, default=float) + "\n")
    fig_map(g, geo, FIG / "1_fire_over_prefire_landuse.png")
    fig_rates(cls, trj[trj.get("variant").isna()] if "variant" in trj else trj, FIG / "2_burn_rate_by_class.png")
    fig_fuel(agg, geo, FIG / "3_fuel_buildup_healpix.png")
    pd.set_option("display.width", 250)
    print(json.dumps(num, indent=2, default=float))
    cols = ["zone", "block_depth", "n_blocks", "class", "area_burned_ha", "area_unburned_ha", "share_fire", "share_ctrl",
            "burn_rate", "odds_ratio", "odds_ratio_lo", "odds_ratio_hi"]
    print(cls[cols].round(3).to_string(index=False))
    print(trj[cols[:6] + ["burn_rate", "rate_ratio_vs_ref", "rate_ratio_lo", "rate_ratio_hi", "or_vs_ref", "or_vs_ref_lo",
                          "or_vs_ref_hi", "p_boot_rate_ratio_le_1"]].round(3).to_string(index=False))
    print(comp[comp.burned_ha > 5].sort_values(["zone", "burned_ha"], ascending=[True, False]).round(1).to_string(index=False))
    print(pd.read_csv(TAB / "terrain_fire_vs_control.csv").to_string(index=False))
    print(tgt, first, post.round(0), sep="\n\n")


if __name__ == "__main__":
    main()
