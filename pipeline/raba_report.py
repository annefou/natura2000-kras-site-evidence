#!/usr/bin/env python3
"""LOCAL report from the Land Use database aggregates: service status, validation, figures.

    pixi run python pipeline/raba_report.py

Reads results/local/raba/<date>/ (written by pipeline/raba.py) and writes, all under results/local/
(gitignored, never published until MKGP gives written permission):

  numbers.csv                  area and share per snapshot, area of interest and class (service + paper classes)
  validation.csv               shares and relative change vs Davidovic et al. 2026 Table 2
  eu_vs_raba.csv               grassland change per source over matched periods, inside SAC SI3000276
  service.json, latest.md      current status per site: latest values, change since the previous snapshot and
                               since 2002, and how current the data are (D_OD)
  figures/a_shares_vs_paper.png, a_service_areas.png, b_change_map.png, c_currency_map.png, d_eu_vs_raba.png
  run-crate/ro-crate-metadata.json   Process Run Crate of this run (version = latest snapshot date)
"""
from __future__ import annotations

import json
import tomllib
from datetime import date, datetime, timezone
from pathlib import Path

import healpix_geo.nested as hn
import matplotlib

matplotlib.use("Agg")  # a script, not a notebook
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import PolyCollection
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.patches import Patch

REPO = Path(__file__).resolve().parents[1]
CFG = tomllib.loads((REPO / "config" / "study.toml").read_text())
SITE = CFG["study"]["site"]
DEPTH = CFG["raba"]["healpix_depth"]
LOCAL = REPO / "results" / "local"
RABA = LOCAL / "raba"
FIG = LOCAL / "figures"
NORTH = f"{SITE}#part1"
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
NOTE = ("LOCAL / INTERNAL. Source: MKGP, Land Use database (RABA). Not for publication pending MKGP permission. "
        "Draft, not reviewed by an ecologist or by ZRC SAZU.")
plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "axes.edgecolor": GRID,
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 9})
SERVICE_CLASSES = ["permanent_grassland", "overgrown_agricultural", "trees_and_shrubs", "forest"]
PAPER_CLASSES = ["Grasslands", "Overgrown areas", "Forest"]


def save(fig, name: str) -> None:
    fig.text(0.01, -0.03, NOTE, fontsize=6.5, color=INK2)
    fig.savefig(FIG / f"{name}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def snapshots() -> list[str]:
    return sorted(p.name for p in RABA.iterdir() if (p / "areas.csv").exists())


def label(s: str) -> str:
    return s if len(s) == 4 else s[:7]


def load_numbers(snaps: list[str]) -> pd.DataFrame:
    reclass = pd.read_csv(REPO / "config" / "validation" / "reclass.csv").set_index("raba_id")["paper_class"]
    rows = []
    for s in snaps:
        a = pd.read_csv(RABA / s / "areas.csv")
        aoi_ha = pd.read_csv(RABA / s / "currency.csv").set_index("area_of_interest")["aoi_area_ha"]
        a["paper_class"] = a.raba_id.map(reclass).fillna("unclassified")
        for scheme, col in [("service", "service_class"), ("paper", "paper_class")]:
            g = a.groupby(["area_of_interest", col]).area_ha.sum().reset_index()
            for r in g.itertuples():
                rows.append({"snapshot": s, "area_of_interest": r.area_of_interest, "scheme": scheme,
                             "class": getattr(r, col), "area_ha": round(r.area_ha, 1),
                             "share_pct": round(100 * r.area_ha / aoi_ha[r.area_of_interest], 2)})
    return pd.DataFrame(rows)


def validation(num: pd.DataFrame, refs: dict[str, str]) -> pd.DataFrame:
    paper = pd.read_csv(REPO / "config" / "validation" / "davidovic2026_table2.csv").set_index("land_use")
    tot = paper[["area_2002_ha", "area_2012_ha", "area_2024_ha"]].sum()
    rows = []
    p = num[num.scheme == "paper"]
    for aoi in p.area_of_interest.unique():
        for cls in PAPER_CLASSES:
            r = {"area_of_interest": aoi, "class": cls}
            for y in ("2002", "2012", "2024"):
                v = p[(p.snapshot == refs[y]) & (p.area_of_interest == aoi) & (p["class"] == cls)]
                r[f"raba_{y}_ha"] = float(v.area_ha.iloc[0]) if len(v) else 0.0
                r[f"raba_{y}_share_pct"] = float(v.share_pct.iloc[0]) if len(v) else 0.0
                r[f"paper_{y}_ha"] = float(paper.loc[cls, f"area_{y}_ha"])
                r[f"paper_{y}_share_pct"] = round(100 * paper.loc[cls, f"area_{y}_ha"] / tot[f"area_{y}_ha"], 2)
            r["raba_rel_change_2002_2024_pct"] = round(100 * (r["raba_2024_ha"] / r["raba_2002_ha"] - 1), 1)
            r["paper_rel_change_2002_2024_pct"] = float(paper.loc[cls, "delta_2002_2024_pct"])
            r["raba_change_2002_2024_ha"] = round(r["raba_2024_ha"] - r["raba_2002_ha"], 1)
            r["paper_change_2002_2024_ha"] = float(paper.loc[cls, "delta_2002_2024_ha"])
            rows.append(r)
    return pd.DataFrame(rows)


def cell_polys(ids: np.ndarray) -> list[np.ndarray]:
    lon, lat = hn.vertices(ids.astype(np.uint64), np.uint8(DEPTH), ellipsoid="WGS84")
    return [np.column_stack([lo, la]) for lo, la in zip(lon, lat)]


def boundary(ax) -> None:
    gj = json.loads((REPO / "results" / "eu" / f"site-{SITE}" / "boundary-simplified.geojson").read_text())
    geom = gj["features"][0]["geometry"]
    for poly in (geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]):
        ring = np.array(poly[0])
        ax.plot(ring[:, 0], ring[:, 1], color=INK2, lw=0.6)
    ax.set_aspect(1 / np.cos(np.radians(45.7)))
    ax.set_xticks([])
    ax.set_yticks([])


def cell_table(s: str) -> pd.DataFrame:
    c = pd.read_parquet(RABA / s / "cells.parquet")
    c["group"] = c.service_class.replace({"overgrown_agricultural": "overgrowth", "trees_and_shrubs": "overgrowth"})
    return c.pivot_table(index="cell_ids", columns="group", values="area_ha", aggfunc="sum", fill_value=0)


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    snaps = snapshots()
    dated = [s for s in snaps if len(s) == 10]
    latest = max(dated)
    month_ends = [s for s in dated if s != latest and s >= "2015"]
    previous = max(month_ends) if month_ends else None
    base = "2002"
    refs = {"2002": "2002", "2012": next(s for s in snaps if s.startswith("2012")),
            "2024": next(s for s in snaps if s.startswith("2024"))}
    num = load_numbers(snaps)
    num.to_csv(LOCAL / "numbers.csv", index=False)
    val = validation(num, refs)
    val.to_csv(LOCAL / "validation.csv", index=False)

    # ---- (a1) shares vs paper ----------------------------------------------------------------
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.4), sharey=False)
    years = [2002, 2012, 2024]
    for ax, cls in zip(axes, PAPER_CLASSES):
        sub = val[val["class"] == cls].set_index("area_of_interest")
        ax.plot(years, [sub.loc[SITE, f"raba_{y}_share_pct"] for y in years], color=BLUE, lw=2, marker="o", ms=6,
                label=f"RABA, SAC {SITE} (48,042 ha)")
        ax.plot(years, [sub.loc[NORTH, f"raba_{y}_share_pct"] for y in years], color=AQUA, lw=2, marker="o", ms=6,
                label="RABA, SAC northern part (22,280 ha)")
        ax.plot(years, [sub.loc[SITE, f"paper_{y}_share_pct"] for y in years], color=ORANGE, lw=0, marker="D", ms=7,
                label="Davidović et al. 2026 (~40,120 ha)")
        lat = num[(num.snapshot == latest) & (num.area_of_interest == SITE) & (num.scheme == "paper") & (num["class"] == cls)]
        if len(lat):
            ax.plot([2026.75], [lat.share_pct.iloc[0]], color=BLUE, marker="s", ms=6, lw=0)
            ax.annotate(f"{label(latest)}", (2026.75, lat.share_pct.iloc[0]), textcoords="offset points", xytext=(0, 7),
                        ha="center", fontsize=7, color=INK2)
        ax.set_title(cls, loc="left", fontsize=10)
        ax.set_xticks([2002, 2012, 2024])
        ax.set_xlim(2000, 2028.5)
        ax.grid(axis="y", color=GRID, lw=0.6)
        ax.set_ylabel("share of area (%)")
    axes[0].legend(frameon=False, fontsize=7, loc="best")
    fig.suptitle("Land-use shares: national Land Use database on SAC SI3000276 vs the paper's study area", x=0.01,
                 ha="left", fontsize=11)
    save(fig, "a_shares_vs_paper")

    # ---- (a2) service classes, areas ---------------------------------------------------------
    s_num = num[(num.scheme == "service") & (num.area_of_interest == SITE)]
    order = [s for s in snaps]
    fig, axes = plt.subplots(1, 4, figsize=(12, 3.2))
    for ax, cls in zip(axes, SERVICE_CLASSES):
        v = s_num[s_num["class"] == cls].set_index("snapshot").reindex(order).area_ha.fillna(0)
        x = [int(s[:4]) + (int(s[5:7]) - 1) / 12 if len(s) == 10 else int(s) for s in order]
        ax.plot(x, v.values, color=BLUE, lw=2, marker="o", ms=5)
        ax.text(x[-1], v.values[-1], f" {v.values[-1]:,.0f} ha", fontsize=7.5, va="bottom", ha="right", color=INK)
        ax.text(x[0], v.values[0], f"{v.values[0]:,.0f} ha ", fontsize=7.5, va="bottom", ha="left", color=INK)
        ax.set_title(cls.replace("_", " "), loc="left", fontsize=10)
        ax.set_ylim(0, max(v.max() * 1.25, 1))
        ax.grid(axis="y", color=GRID, lw=0.6)
    axes[0].set_ylabel(f"area inside {SITE} (ha)")
    fig.suptitle("Service classes inside SAC SI3000276, every snapshot aggregated: " + ", ".join(label(s) for s in order),
                 x=0.01, ha="left", fontsize=10)
    save(fig, "a_service_areas")

    # ---- (b) change map 2002 -> latest on HEALPix cells ----------------------------------------
    c0, c1 = cell_table(base), cell_table(latest)
    ids = np.union1d(c0.index.values, c1.index.values)
    c0, c1 = c0.reindex(ids, fill_value=0), c1.reindex(ids, fill_value=0)
    polys = cell_polys(ids)
    div = LinearSegmentedColormap.from_list("div", [ORANGE, "#e9e8e4", BLUE])
    fig, axes = plt.subplots(1, 2, figsize=(11, 6))
    for ax, grp, title in [(axes[0], "permanent_grassland", "Permanent grassland"),
                           (axes[1], "overgrowth", "Overgrowth (overgrown agricultural land + trees and shrubs)")]:
        d = (c1.get(grp, 0) - c0.get(grp, 0)).values if grp in c1 or grp in c0 else np.zeros(len(ids))
        lim = max(np.nanpercentile(np.abs(d), 99), 0.5)
        pc = PolyCollection(polys, array=d, cmap=div if grp == "permanent_grassland" else div.reversed(),
                            norm=TwoSlopeNorm(0, -lim, lim), edgecolor="none")
        ax.add_collection(pc)
        boundary(ax)
        ax.autoscale_view()
        fig.colorbar(pc, ax=ax, shrink=0.55, label=f"change per cell, ha (cell ≈ 3.9 ha)")
        ax.set_title(f"{title}\n{base} → {label(latest)}", loc="left", fontsize=10)
    fig.suptitle(f"Where the change is: HEALPix depth {DEPTH} cells (WGS84, NESTED), from a 25 m sample of the "
                 "Land Use database", x=0.01, ha="left", fontsize=10)
    save(fig, "b_change_map")

    # ---- (c) currency map (D_OD) ---------------------------------------------------------------
    cl = pd.read_parquet(RABA / latest / "cells.parquet")
    snap_day = pd.Timestamp(latest)
    if "cell_dod_median" in cl:
        dod = cl.groupby("cell_ids").cell_dod_median.first()
        months = ((snap_day - pd.to_datetime(dod)).dt.days / 30.44).values
        seq = LinearSegmentedColormap.from_list("seq", ["#d6e6f8", BLUE, "#0d3a73"])
        fig, ax = plt.subplots(figsize=(6.5, 6.4))
        pc = PolyCollection(cell_polys(dod.index.values), array=months, cmap=seq, edgecolor="none")
        ax.add_collection(pc)
        boundary(ax)
        ax.autoscale_view()
        fig.colorbar(pc, ax=ax, shrink=0.6, label="months since last change or review (D_OD), cell median")
        cur = pd.read_csv(RABA / latest / "currency.csv").set_index("area_of_interest").loc[SITE]
        ax.set_title(f"How current is the snapshot of {latest}?\nmedian D_OD {cur.dod_median}; reviewed in the last "
                     f"12 months: {cur.share_reviewed_last_12_months_pct:.0f} % of the site, last 36 months: "
                     f"{cur.share_reviewed_last_36_months_pct:.0f} %", loc="left", fontsize=9.5)
        save(fig, "c_currency_map")

    # ---- (d) EU layers vs RABA over matched periods --------------------------------------------
    eu = json.loads((REPO / "results" / "summary.json").read_text())
    hrl = pd.DataFrame(eu["hrl_grassland"])
    hrl_net = float(hrl[(hrl.layer == "HRL_GrasslandChange_15_18") & (hrl.value == 11)].area_ha.iloc[0]
                    - hrl[(hrl.layer == "HRL_GrasslandChange_15_18") & (hrl.value == 22)].area_ha.iloc[0])
    g = num[(num.scheme == "service") & (num.area_of_interest == SITE) & (num["class"] == "permanent_grassland")]
    gs = g.set_index("snapshot").area_ha

    def first(prefix):
        m = [s for s in gs.index if s.startswith(prefix)]
        return m[0] if m else None
    pairs = []
    s18, s15 = first("2018"), first("2015")
    corine = -eu["corine_loss_from_grassland_classes_2000_2018_ha"] + eu["corine_gain_to_grassland_classes_2000_2018_ha"]
    if s18:
        pairs.append(("2000/2002–2018", "CORINE change layers", corine, f"RABA 2002 → {label(s18)}", gs[s18] - gs[base]))
    if s15 and s18:
        pairs.append(("2015–2018", "HRL Grassland change (unverified)", hrl_net, f"RABA {label(s15)} → {label(s18)}",
                      gs[s18] - gs[s15]))
    pairs.append((f"2002–{latest[:4]}", "(no EU layer)", np.nan, f"RABA 2002 → {label(latest)}", gs[latest] - gs[base]))
    rows = []
    for period, eu_name, eu_v, r_name, r_v in pairs:
        rows += [{"period": period, "source": eu_name, "grassland_change_ha": eu_v},
                 {"period": period, "source": r_name, "grassland_change_ha": round(float(r_v), 1)}]
    pd.DataFrame(rows).to_csv(LOCAL / "eu_vs_raba.csv", index=False)
    fig, ax = plt.subplots(figsize=(8, 3.6))
    yy = np.arange(len(pairs))[::-1]
    for y, (period, eu_name, eu_v, r_name, r_v) in zip(yy, pairs):
        if not np.isnan(eu_v):
            ax.barh(y + 0.18, eu_v, height=0.34, color=BLUE, edgecolor=SURFACE, lw=1.5)
            ax.text(eu_v, y + 0.18, f" {eu_v:+,.0f} ha  {eu_name}", va="center", fontsize=7.5,
                    ha="left" if eu_v >= 0 else "right", color=INK)
        ax.barh(y - 0.18, r_v, height=0.34, color=ORANGE, edgecolor=SURFACE, lw=1.5)
        ax.text(r_v, y - 0.18, f" {r_v:+,.0f} ha  {r_name}", va="center", fontsize=7.5,
                ha="left" if r_v >= 0 else "right", color=INK)
    ax.set_yticks(yy, [p[0] for p in pairs])
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_xlabel(f"change in grassland area inside {SITE} (ha)")
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.legend(handles=[Patch(color=BLUE, label="open EU-wide layer"), Patch(color=ORANGE, label="national Land Use database")],
              frameon=False, fontsize=7.5, loc="lower left")
    lo = min(0, *(p[4] for p in pairs), *(p[2] for p in pairs if not np.isnan(p[2])))
    hi = max(0, *(p[4] for p in pairs), *(p[2] for p in pairs if not np.isnan(p[2])))
    ax.set_xlim(lo * 1.9 - 200, hi * 1.9 + 200)
    ax.set_title("What EU layers detect vs the national Land Use database, same site, matched periods", loc="left", fontsize=10)
    save(fig, "d_eu_vs_raba")

    # ---- service status ------------------------------------------------------------------------
    def svc(s):
        return num[(num.snapshot == s) & (num.scheme == "service") & (num.area_of_interest == SITE)].set_index("class")
    L, B = svc(latest), svc(base)
    P = svc(previous) if previous else None
    cur = pd.read_csv(RABA / latest / "currency.csv").set_index("area_of_interest").loc[SITE].to_dict()
    service = {"site": SITE, "latest_snapshot": latest, "previous_snapshot": previous, "baseline_snapshot": base,
               "classes": {}, "currency": cur,
               "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "note": NOTE}
    for c in SERVICE_CLASSES:
        v = float(L.area_ha.get(c, 0))
        service["classes"][c] = {"area_ha": v, "share_pct": float(L.share_pct.get(c, 0)),
                                 "change_since_previous_ha": round(v - float(P.area_ha.get(c, 0)), 1) if P is not None else None,
                                 "change_since_2002_ha": round(v - float(B.area_ha.get(c, 0)), 1)}
    (LOCAL / "service.json").write_text(json.dumps(service, indent=2, default=str) + "\n")
    lines = [f"# Kras ({SITE}): current status from the Land Use database — LOCAL, NOT FOR PUBLICATION", "",
             f"> {NOTE}", "",
             f"Latest snapshot **{latest}**; previous **{previous}**; baseline **2002**.", "",
             "| Class | Area (ha) | Share | Since previous | Since 2002 |", "|---|---:|---:|---:|---:|"]
    for c, d in service["classes"].items():
        lines.append(f"| {c.replace('_', ' ')} | {d['area_ha']:,.1f} | {d['share_pct']:.1f} % | "
                     f"{d['change_since_previous_ha']:+,.1f} | {d['change_since_2002_ha']:+,.1f} |")
    lines += ["", f"**How current:** median date of last change or review (D_OD) {cur.get('dod_median')}; "
              f"{cur.get('share_reviewed_last_12_months_pct')} % of the site reviewed in the 12 months before the snapshot, "
              f"{cur.get('share_reviewed_last_36_months_pct')} % in the last 36 months. RABA_Read_me.pdf: on average about one "
              "third of Slovenia is updated each year, so a monthly snapshot is not a monthly observation.", ""]
    (LOCAL / "latest.md").write_text("\n".join(lines) + "\n")

    # ---- run crate (local) ---------------------------------------------------------------------
    metas = [json.loads((RABA / s / "snapshot.json").read_text()) for s in snaps]
    outs = ["numbers.csv", "validation.csv", "eu_vs_raba.csv", "service.json", "latest.md",
            *[f"figures/{p.name}" for p in sorted(FIG.glob("*.png"))]]
    crate = {"@context": "https://w3id.org/ro/crate/1.2/context", "@graph": [
        {"@id": "ro-crate-metadata.json", "@type": "CreativeWork", "about": {"@id": "./"},
         "conformsTo": [{"@id": "https://w3id.org/ro/crate/1.2"}, {"@id": "https://w3id.org/ro/wfrun/process/0.5"}]},
        {"@id": "./", "@type": "Dataset", "name": f"Land Use database status of Natura 2000 site {SITE}, run {latest}",
         "description": "LOCAL Workflow Run Crate (Process Run Crate profile). DRAFT: not deposited, not published, "
                        "not reviewed. " + NOTE, "version": latest, "datePublished": date.today().isoformat(),
         "conformsTo": {"@id": "https://w3id.org/ro/wfrun/process/0.5"},
         "hasPart": [{"@id": f"../{o}"} for o in outs], "mentions": {"@id": "#run"}},
        {"@id": "#run", "@type": "CreateAction", "name": f"raba.py + raba_report.py, snapshots {', '.join(snaps)}",
         "endTime": datetime.now(timezone.utc).isoformat(timespec="seconds"),
         "instrument": [{"@id": "pipeline/raba.py"}, {"@id": "pipeline/raba_report.py"}],
         "object": [{"@id": m["url"]} for m in metas], "result": [{"@id": f"../{o}"} for o in outs]},
        *[{"@id": m["url"], "@type": "Dataset", "name": m["file"], "dateCreated": m["snapshot_date"],
           "publisher": "Ministry of Agriculture, Forestry and Food (MKGP), Slovenia", "contentSize": str(m["bytes"]),
           "description": f"Retrieved {m['retrieved']}; source CRS {m['source_crs']}. {m['licence']}"} for m in metas],
        {"@id": "pipeline/raba.py", "@type": ["File", "SoftwareSourceCode"]},
        {"@id": "pipeline/raba_report.py", "@type": ["File", "SoftwareSourceCode"]},
    ]}
    (LOCAL / "run-crate").mkdir(exist_ok=True)
    (LOCAL / "run-crate" / "ro-crate-metadata.json").write_text(json.dumps(crate, indent=2) + "\n")
    print((LOCAL / "latest.md").read_text())
    print(val[val.area_of_interest.isin([SITE, NORTH])].to_string(index=False))


if __name__ == "__main__":
    main()
