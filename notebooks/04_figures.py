# ---
# jupyter:
#   jupytext:
#     formats: py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.0
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # 04 — Figures (public data only)
#
# Four figures from the committed results. Figures from the national Land Use database are made
# locally by `pipeline/raba_report.py` and are not published.

# %%
import json
import tomllib
from pathlib import Path

import healpix_geo.nested as hn
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
from matplotlib.collections import PolyCollection
from matplotlib.colors import LinearSegmentedColormap

REPO = Path("..").resolve()
CFG = tomllib.loads((REPO / "config" / "study.toml").read_text())["study"]
SITE, DEPTH = CFG["site"], CFG["healpix_depth"]
FIG = REPO / "figures"
EU = REPO / "results" / "eu"
S = json.loads((REPO / "results" / "summary.json").read_text())

# Reference palette (dataviz skill, light mode): two categorical slots, text inks, surface.
BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "axes.edgecolor": GRID,
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 10})
DRAFT = "DRAFT: not reviewed by an ecologist or by the Slovenian Distributed Centre (ZRC SAZU)"


def save(fig, name):
    fig.text(0.01, -0.04, DRAFT, fontsize=7, color=INK2)
    fig.savefig(FIG / f"{name}.png", dpi=150, bbox_inches="tight")
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight")
    plt.show()


# %% [markdown]
# ## Main result: grassland change inside Kras, by source
#
# Each bar is the change in grassland area a source reports for its own period. The EU layers are
# measured inside SAC SI3000276; the national figure is the paper's, for its own study area (the
# Natura 2000 part of the Kras plateau, ~40,120 ha). Periods and areas differ, which is the point: the
# EU layers do not see a change of the size the national data show.

# %%
hrl = pd.DataFrame(S["hrl_grassland"])
hrl_net = float(hrl[(hrl.layer == "HRL_GrasslandChange_15_18") & (hrl.value == 11)].area_ha.iloc[0]
                - hrl[(hrl.layer == "HRL_GrasslandChange_15_18") & (hrl.value == 22)].area_ha.iloc[0])
clcp = S["clcplus_ha"]["Permanent herbaceous"]
paper = {r["land_use"]: r for r in S["paper_targets"]}["Grasslands"]
bars = [
    ("CORINE Land Cover change, 2000–2018\n(natural grasslands + pastures)", -S["corine_loss_from_grassland_classes_2000_2018_ha"]
     + S["corine_gain_to_grassland_classes_2000_2018_ha"], BLUE, "measured change"),
    ("HRL Grassland change, 2015–2018\n(gain − loss, both 'unverified')", hrl_net, BLUE, "measured change"),
    ("CLC+ Backbone, 2021 minus 2018\n(permanent herbaceous; two classifications)", clcp["2021"] - clcp["2018"], BLUE, "not change"),
    ("National Land Use database, 2002–2024\n(Davidović et al. 2026, Table 2)", paper["delta_2002_2024_ha"], ORANGE, "paper"),
]
fig, ax = plt.subplots(figsize=(8.5, 3.8))
y = np.arange(len(bars))[::-1]
for yi, (label, v, c, kind) in zip(y, bars):
    ax.barh(yi, v, color=c, height=0.55, alpha=0.55 if kind == "not change" else 1.0,
            hatch="//" if kind == "not change" else None, edgecolor=SURFACE, linewidth=2)
    ax.text(v + (60 if v >= 0 else -60), yi, f"{v:+,.0f} ha", va="center", ha="left" if v >= 0 else "right", color=INK)
ax.set_yticks(y, [b[0] for b in bars], fontsize=8.5)
ax.axvline(0, color=INK2, lw=0.8)
ax.set_xlim(-4200, 5800)
ax.set_xlabel("change in grassland area (ha)")
ax.grid(axis="x", color=GRID, lw=0.6)
ax.set_axisbelow(True)
ax.set_title("Grassland change inside Natura 2000 site Kras, as each source reports it", loc="left", fontsize=11)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=BLUE, label="open EU-wide data, inside SAC SI3000276"),
                   Patch(color=ORANGE, label="national data, paper's study area")],
          loc="lower right", frameon=False, fontsize=8)
save(fig, "main_result")

# %% [markdown]
# ## CORINE grassland classes 2000–2018
#
# Status-layer areas (lines) differ between years partly through mapping revisions; the change
# layers (annotation) are what CLMS advises using for change.

# %%
series = pd.DataFrame(S["corine_proxy_ha"])
series.index = series.index.astype(int)
fig, ax = plt.subplots(figsize=(7, 3.6))
for col, c in zip(series.columns, [BLUE, ORANGE]):
    ax.plot(series.index, series[col], color=c, lw=2, marker="o", ms=6)
    ax.text(series.index[-1] + 0.4, series[col].iloc[-1], col, va="center", color=INK, fontsize=9)
ax.set_xticks(series.index)
ax.set_xlim(1999, 2023)
ax.set_ylim(0, series.values.max() * 1.15)
ax.set_ylabel("area inside the site (ha)")
ax.grid(axis="y", color=GRID, lw=0.6)
ax.set_title("CORINE classes 321 and 231 inside SI3000276", loc="left", fontsize=11)
ax.text(2000, 300, f"Change layers 2000–2018: {S['corine_loss_from_grassland_classes_2000_2018_ha']} ha lost "
        "(pastures → mineral extraction, 2000–2006); 0 ha gained", fontsize=8.5, color=INK2)
save(fig, "corine_grassland")

# %% [markdown]
# ## Species records per year
#
# Every bat record comes from one survey in 2004; most recent records are iNaturalist observations.

# %%
cells = pd.read_csv(REPO / "results" / "species" / "cells.csv", dtype={"year": "Int64"})
cells["group"] = np.where(cells.species.str.match(r"^(Rhinolophus|Myotis|Miniopterus)"), "bats", "other species")
yr = cells.dropna(subset=["year"]).pivot_table(index="year", columns="group", values="records", aggfunc="sum", fill_value=0)
yr = yr[yr.index >= 1990]
fig, ax = plt.subplots(figsize=(8, 3.4))
bottom = np.zeros(len(yr))
for g, c in [("other species", BLUE), ("bats", ORANGE)]:
    if g in yr:
        ax.bar(yr.index, yr[g], bottom=bottom, color=c, width=0.8, edgecolor=SURFACE, linewidth=1, label=g)
        bottom += yr[g].values
undated = int(cells[cells.year.isna()].records.sum())
old = int(cells[cells.year < 1990].records.sum())
ax.set_ylabel("GBIF records inside the site")
ax.grid(axis="y", color=GRID, lw=0.6)
ax.set_axisbelow(True)
ax.legend(frameon=False, fontsize=8, loc="upper left")
ax.set_title(f"Records of Standard Data Form species per year ({undated} undated, {old} before 1990 not shown)",
             loc="left", fontsize=10.5)
save(fig, "species_years")

# %% [markdown]
# ## Where the records are: HEALPix cells (depth 13, WGS84, NESTED)

# %%
ds = xr.open_zarr(REPO / "results" / "healpix" / f"gbif-{SITE}-d{DEPTH}.zarr", consolidated=False)
ids = ds.cell_ids.values.astype(np.uint64)
lon, lat = hn.vertices(ids, np.uint8(DEPTH), ellipsoid="WGS84")
polys = [np.column_stack([lo, la]) for lo, la in zip(lon, lat)]
rec = ds.records.values
blues = LinearSegmentedColormap.from_list("blues", ["#d6e6f8", "#2a78d6", "#0d3a73"])
fig, ax = plt.subplots(figsize=(6.5, 6.2))
pc = PolyCollection(polys, array=np.log10(rec), cmap=blues, edgecolor=SURFACE, linewidth=0.4)
ax.add_collection(pc)
gj = json.loads((EU / f"site-{SITE}" / "boundary-simplified.geojson").read_text())
geom = gj["features"][0]["geometry"]
for poly in (geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]):
    ring = np.array(poly[0])
    ax.plot(ring[:, 0], ring[:, 1], color=INK2, lw=0.8)
ax.set_aspect(1 / np.cos(np.radians(45.7)))
ax.autoscale_view()
cb = fig.colorbar(pc, ax=ax, shrink=0.6, label="records per cell")
ticks = [1, 3, 10, 30]
cb.set_ticks(np.log10(ticks), labels=[str(t) for t in ticks])
ax.set_xlabel("longitude")
ax.set_ylabel("latitude")
ax.set_title(f"{int(rec.sum())} GBIF records in {len(ids)} HEALPix cells (~800 m)\nsite boundary: EEA Natura 2000",
             loc="left", fontsize=10.5)
save(fig, "gbif_cells")
