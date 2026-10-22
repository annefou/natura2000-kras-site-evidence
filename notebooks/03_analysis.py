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
# # 03 — What open EU-wide data detect inside Kras, against what the national data show
#
# **Question.** Can open EU-wide data tell whether grassland, and with it habitat 62A0 (Eastern
# sub-Mediterranean dry grasslands), is declining inside Natura 2000 site SI3000276 Kras?
#
# **Benchmark.** Davidović, Čuš & Ivajnšič (2026, [doi:10.3986/AGS.14021](https://doi.org/10.3986/AGS.14021),
# CC BY-SA 4.0) used the national Land Use database (MKGP) for 2002, 2012 and 2024 and report, for the
# part of the Kras plateau inside Natura 2000: grasslands −2,814.9 ha (−26.9 %), overgrown areas
# +1,645.9 ha (+47.3 %), forest +1,242.6 ha (+5.3 %) (their Table 2, `config/validation/`).
#
# This notebook uses only openly published inputs: Article 17 reports, CORINE Land Cover and its
# change layers, CLC+ Backbone, HRL Grassland and GBIF. The replication of the paper with the
# national data runs locally (`pixi run raba`, `pipeline/raba_report.py`); its results are not
# published until MKGP gives permission.
#
# Machine-generated; **not reviewed by an ecologist or by the Slovenian Distributed Centre
# (ZRC SAZU)**.

# %%
import json
import tomllib
from pathlib import Path

import pandas as pd

REPO = Path("..").resolve()
CFG = tomllib.loads((REPO / "config" / "study.toml").read_text())
SITE, HABITAT = CFG["study"]["site"], CFG["study"]["habitat"]
PROXY = CFG["study"]["proxy_classes"]
EU = REPO / "results" / "eu"
OUT = REPO / "results"

# %% [markdown]
# ## 1. National context: Article 17 (Slovenia, Continental region)
#
# Article 17 status is reported per member state and biogeographical region, not per site.

# %%
st = pd.read_csv(EU / f"article17-{SITE}" / "art17-status.csv", dtype=str)
pr = pd.read_csv(EU / f"article17-{SITE}" / "art17-pressures.csv", dtype=str)
a17 = st[st.habitat_code == HABITAT][["period", "overall", "overall_trend", "area_km2", "area_trend",
                                      "reason_area_change", "condition_good_km2", "condition_notgood_km2"]]
a17

# %%
high = pr[(pr.habitat_code == HABITAT) & (pr.type == "pressure") & (pr.ranking == "H")][["period", "pressure_code"]]
pressures = pr[(pr.habitat_code == HABITAT)].groupby(["period", "ranking"]).pressure_code.apply(lambda s: ", ".join(sorted(s)))
high, pressures

# %% [markdown]
# Pressure codes are kept as reported. Their official labels are not yet attached here (TODO): only
# PA05 is described in the text, as abandonment of grassland management such as grazing, and that
# wording needs checking against the 2019–2024 reference list.

# %% [markdown]
# ## 2. CORINE Land Cover inside the site, 2000–2018
#
# Proxy for 62A0: CORINE classes 321 *Natural grasslands* and 231 *Pastures*. Whether that is a fair
# proxy on Kras is one of the questions put to reviewers. Change is read from the CLC-Change layers,
# as the Copernicus Land Monitoring Service advises, not from differences between status layers
# (those mix real change with mapping revisions).

# %%
status = pd.read_csv(EU / f"landcover-{SITE}" / "clc-status-areas.csv", dtype={"clc_code": str})
change = pd.read_csv(EU / f"landcover-{SITE}" / "clc-changes.csv", dtype={"from_code": str, "to_code": str})
series = status[status.clc_code.isin(PROXY)].pivot(index="year", columns="clc_label", values="area_ha")
series

# %%
loss = change[change.from_code.isin(PROXY) & ~change.to_code.isin(PROXY) & (change.area_ha > 0)]
gain = change[change.to_code.isin(PROXY) & ~change.from_code.isin(PROXY) & (change.area_ha > 0)]
to_shrub = change[(change.to_code == "324") & change.from_code.isin(["311", "312", "313"])].groupby("period").area_ha.sum()
print(f"lost from the grassland classes 2000-2018: {loss.area_ha.sum():.1f} ha; gained: {gain.area_ha.sum():.1f} ha")
loss, to_shrub

# %% [markdown]
# ## 3. CLC+ Backbone (10 m), 2018 and 2021
#
# The two years are separate classifications: their difference mixes change with classification
# differences, so it is reported, not called change.

# %%
clcp = pd.read_csv(EU / f"landcover10m-{SITE}" / "clcplus-areas.csv")
herb = clcp[clcp.class_name.isin(["Permanent herbaceous", "Low-growing woody plants"])].pivot(
    index="class_name", columns="year", values="area_ha")
herb

# %% [markdown]
# ## 4. HRL Grassland (Copernicus)
#
# 2018 status at 10 m, and the 2015–2018 change layer at 20 m whose gain and loss classes the product
# itself labels *unverified*. Yearly 10 m layers for 2017–2023 exist on the Copernicus Data Space
# Ecosystem but need an account (not used, TODO).

# %%
hrl = pd.read_csv(EU / "hrl-grassland" / "areas.csv")
hrl

# %% [markdown]
# ## 5. What the paper reports with the national data (validation targets)

# %%
paper = pd.read_csv(REPO / "config" / "validation" / "davidovic2026_table2.csv")
targets = paper[paper.land_use.isin(["Grasslands", "Overgrown areas", "Forest"])].copy()
targets["total_2002_ha"] = paper.area_2002_ha.sum()
targets["share_2002_pct_computed"] = (100 * targets.area_2002_ha / paper.area_2002_ha.sum()).round(2)
targets["share_2024_pct_computed"] = (100 * targets.area_2024_ha / paper.area_2024_ha.sum()).round(2)
targets["rel_change_pct_computed"] = (100 * (targets.area_2024_ha / targets.area_2002_ha - 1)).round(1)
(OUT / "validation").mkdir(exist_ok=True)
targets.to_csv(OUT / "validation" / "targets.csv", index=False)
print(f"paper study area (sum of Table 2 classes): 2002 {paper.area_2002_ha.sum():,.1f} ha, "
      f"2024 {paper.area_2024_ha.sum():,.1f} ha; SAC {SITE}: 48,042 ha (EEA)")
targets[["land_use", "area_2002_ha", "area_2024_ha", "delta_2002_2024_ha", "delta_2002_2024_pct",
         "share_2002_pct_computed", "share_2024_pct_computed", "rel_change_pct_computed"]]

# %% [markdown]
# **Boundary.** The classes sum to about 40,120 ha, matching the paper's own statement that
# "Approximately 93% of the plateau (401 km²) lies within the Natura 2000 network" (Kras plateau,
# 429 km²). The paper's area is therefore neither SAC SI3000276 Kras (48,042 ha) nor SPA SI5000023 Kras
# (58,753 ha), and no public combination of the two matches it (SAC ∩ SPA 44,981 ha, SAC ∪ SPA
# 61,814 ha; the SAC's two parts are 22,280 and 25,763 ha). The authors used a ZRSVN vector that is
# not published. The local replication therefore compares **shares and relative change**, computed on
# SAC SI3000276 as a stated approximation. Absolute hectares are recorded but are not comparable
# without the authors' boundary, which has been requested from them (TODO).

# %% [markdown]
# ## 6. Species records (GBIF), supporting evidence

# %%
summ = pd.read_csv(EU / f"species-{SITE}" / "species-summary.csv")
cells = pd.read_csv(REPO / "results" / "species" / "cells.csv", dtype={"year": "Int64"})
INAT = "50c9509d-22c7-4a22-a47d-8c48425ef4a7"
BAT = "30ac77b7-9434-4eec-84c3-52b507ee9b8b"  # Dutch Mammal Society 2004 survey, Rakitovec
bats = summ[summ.sdf_name.str.match(r"^(Rhinolophus|Myotis|Miniopterus)")]
bat_cells = cells[cells.species.str.match(r"^(Rhinolophus|Myotis|Miniopterus)")]
species = {
    "records_in_download": 423, "records_inside_site": int(summ.records.sum()),
    "cells_occupied_depth13": int(cells.cell_ids.nunique()),
    "inaturalist_share_inside_site_pct": round(100 * cells[cells.dataset_key == INAT].records.sum() / cells.records.sum(), 1),
    "sdf_taxa": int(len(summ)), "sdf_taxa_without_records": summ[summ.records == 0].sdf_name.tolist(),
    "bat_records": int(bats.records.sum()),
    "bat_records_from_2004_survey": int(bat_cells[bat_cells.dataset_key == BAT].records.sum()),
    "bat_record_years": sorted(int(y) for y in bat_cells.year.dropna().unique()),
}
species

# %% [markdown]
# ## 7. Answer (draft)

# %%
a = {r.period: r for r in a17.itertuples()}
corine_loss = round(float(loss.area_ha.sum()), 1)
p = targets.set_index("land_use")
statement = (
    f"Open EU-wide data cannot tell whether grassland, and with it habitat {HABITAT}, is declining inside "
    f"Natura 2000 site {SITE} Kras. Slovenia's Article 17 reports for the Continental region assess {HABITAT} as "
    f"unfavourable-bad and declining in 2013-2018 ({a['2013-2018'].overall}, {a['2013-2018'].overall_trend}) and in "
    f"2019-2024 ({a['2019-2024'].overall}, {a['2019-2024'].overall_trend}), with the reported area falling from "
    f"{a['2013-2018'].area_km2} to {a['2019-2024'].area_km2} km2, a difference the 2019-2024 report attributes to a "
    f"change of method; that is national, not site-level. Inside the site, CORINE change layers detect "
    f"{corine_loss} ha lost from the grassland classes between 2000 and 2018, all of it pastures to mineral extraction "
    f"in 2000-2006, while the national Land Use database, as analysed by Davidovic et al. (2026), shows grasslands "
    f"falling by {abs(p.loc['Grasslands','delta_2002_2024_ha']):,.1f} ha ({p.loc['Grasslands','delta_2002_2024_pct']} %) and "
    f"overgrown areas rising by {p.loc['Overgrown areas','delta_2002_2024_ha']:,.1f} ha "
    f"(+{p.loc['Overgrown areas','delta_2002_2024_pct']} %) between 2002 and 2024. CORINE's 25 ha mapping unit (5 ha for "
    f"change) cannot see encroachment at the scale abandonment of grazing works. HRL Grassland's 2015-2018 change "
    f"classes are labelled unverified by the product, and CLC+ 2018 and 2021 are separate classifications. "
    f"GBIF records ({species['records_inside_site']} inside the site) are opportunistic and give no abundance trend."
)
summary = {
    "site": SITE, "habitat": HABITAT, "verdict": "EU-wide open data: inconclusive at site level",
    "article17": a17.to_dict(orient="records"),
    "article17_high_pressures": high.to_dict(orient="records"),
    "corine_proxy_ha": {str(k): v for k, v in series.to_dict().items()},
    "corine_loss_from_grassland_classes_2000_2018_ha": corine_loss,
    "corine_loss_detail": loss.to_dict(orient="records"),
    "corine_gain_to_grassland_classes_2000_2018_ha": round(float(gain.area_ha.sum()), 1),
    "corine_forest_to_transitional_shrub_ha": {k: round(v, 1) for k, v in to_shrub.items()},
    "clcplus_ha": {k: {str(y): v for y, v in d.items()} for k, d in herb.to_dict(orient="index").items()},
    "hrl_grassland": hrl.to_dict(orient="records"),
    "paper_targets": targets[["land_use", "area_2002_ha", "area_2024_ha", "delta_2002_2024_ha",
                              "delta_2002_2024_pct"]].to_dict(orient="records"),
    "paper_study_area_ha_2002": round(float(paper.area_2002_ha.sum()), 1),
    "species": species, "statement": statement,
    "review_status": "draft; not reviewed by an ecologist or by the Slovenian Distributed Centre (ZRC SAZU)",
}
(OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str) + "\n")
pd.DataFrame([
    ("corine_loss_from_grassland_classes_2000_2018_ha", corine_loss, "CORINE CLC-Change, inside SAC"),
    ("paper_grassland_change_2002_2024_ha", p.loc["Grasslands", "delta_2002_2024_ha"], "Davidovic et al. 2026, Table 2"),
    ("paper_overgrown_change_2002_2024_ha", p.loc["Overgrown areas", "delta_2002_2024_ha"], "Davidovic et al. 2026, Table 2"),
    ("hrl_grassland_2018_ha", float(hrl[(hrl.layer == "HRL_Grassland_2018") & (hrl.value == 1)].area_ha.iloc[0]), "HRL Grassland 2018, inside SAC"),
    ("clcplus_permanent_herbaceous_2018_ha", herb.loc["Permanent herbaceous", 2018], "CLC+ Backbone, inside SAC"),
    ("clcplus_permanent_herbaceous_2021_ha", herb.loc["Permanent herbaceous", 2021], "CLC+ Backbone, inside SAC"),
    ("gbif_records_inside_site", species["records_inside_site"], "doi:10.15468/dl.5epzsz"),
], columns=["quantity", "value", "source"]).to_csv(OUT / "summary.csv", index=False)
print(statement)
