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
# # 01 — Inputs: what is monitored, from which data
#
# The study has three layers, each with its own inputs:
#
# | Layer | Data | Access | In this repository |
# |---|---|---|---|
# | **Service** (core): grassland, overgrowth, trees and shrubs, forest per Natura 2000 site | Slovenian Land Use database, MKGP "RABA", monthly national snapshots | Public archive <https://rkg.gov.si/arhiv/RABA/?C=N;O=D>, no account | **Code only.** Results stay local (`results/local/`, gitignored) until MKGP gives written permission to publish |
# | **EU comparison** | EEA Natura 2000 + Standard Data Form; Article 17 (EEA, Reportnet 3); CORINE Land Cover 2000–2018 and change; CLC+ Backbone 2018, 2021; HRL Grassland 2018 and change 2015–2018 | Open web services, no account | Small tables in `results/eu/` |
# | **Species** (supporting) | GBIF occurrence download [doi:10.15468/dl.5epzsz](https://doi.org/10.15468/dl.5epzsz) | Public download, CC BY-NC 4.0 | Counts per HEALPix cell, species, year in `results/species/`; raw records never committed |
#
# The Snakefile builds every input from its source (`pixi run rebuild` for the EU and species
# layers, `pixi run raba` for the Land Use database). This notebook reads what the pipeline left in
# `results/` and records the source registry; it downloads nothing, so the Jupyter Book can run it
# without network access to the national archive.

# %%
import json
import tomllib
from pathlib import Path

import pandas as pd

REPO = Path("..").resolve()
CFG = tomllib.loads((REPO / "config" / "study.toml").read_text())
SITE, HABITAT = CFG["study"]["site"], CFG["study"]["habitat"]
EU = REPO / "results" / "eu"

# %% [markdown]
# ## The site and the habitat (Standard Data Form, EEA end-2024 release)

# %%
hab = pd.read_csv(EU / f"site-{SITE}" / "sdf-habitats.csv", dtype={"habitat_code": str})
hab

# %%
row = hab[hab.habitat_code == HABITAT].iloc[0]
print(f"{HABITAT} {row.habitat_name}: cover {row.cover_ha:,.1f} ha in {SITE}; "
      f"representativity {row.representativity}, conservation {row.conservation}, data quality {row.data_quality}")

# %% [markdown]
# ## Source registry
#
# Every input, with identifier, licence and where its provenance is recorded. Written to
# `results/sources.json`.

# %%
def crate_root(name: str) -> dict:
    g = json.loads((EU / name / "ro-crate-metadata.json").read_text())["@graph"]
    return next(e for e in g if e.get("@id") == "./")


SOURCES = []
for crate in [f"site-{SITE}", f"article17-{SITE}", f"landcover-{SITE}", f"landcover10m-{SITE}", f"species-{SITE}"]:
    root = crate_root(crate)
    SOURCES.append({"input": root["name"], "based_on": [b["@id"] for b in root["isBasedOn"]],
                    "licence": (root.get("license") or {}).get("@id"), "retrieved": root["datePublished"],
                    "provenance": f"results/eu/{crate}/ro-crate-metadata.json"})
hrl = json.loads((EU / "hrl-grassland" / "source.json").read_text())
SOURCES.append({"input": "Copernicus HRL Grassland 2018 and Grassland Change 2015-2018, inside the site",
                "based_on": [v["url"] for v in hrl["layers"].values()], "licence": "CLMS: free of charge, any purpose",
                "retrieved": hrl["retrieved"][:10], "provenance": "results/eu/hrl-grassland/source.json"})
SOURCES.append({"input": "Slovenian Land Use database (MKGP RABA), snapshots " + ", ".join(
                    [CFG["raba"]["baseline"], *CFG["raba"]["reference"], "latest month-end"]),
                "based_on": ["https://rkg.gov.si/arhiv/RABA/?C=N;O=D", "https://rkg.gov.si/arhiv/RABA/RABA_Read_me.pdf"],
                "licence": "Not stated in RABA_Read_me.pdf; the 2002 archive's Terms and Conditions restrict use. "
                           "Used locally only; results not published (permission to be requested from raba.mkgp@gov.si)",
                "retrieved": None, "provenance": "results/local/raba/<date>/snapshot.json (local only)"})
(REPO / "results" / "sources.json").write_text(json.dumps(SOURCES, indent=2, ensure_ascii=False) + "\n")
pd.DataFrame(SOURCES)[["input", "licence", "retrieved"]]

# %% [markdown]
# ## Is a local Land Use database run present?
#
# Only on a machine where `pixi run raba` has been run. Nothing from it is shown here.

# %%
local = sorted(p.name for p in (REPO / "results" / "local" / "raba").glob("*") if p.is_dir())
print(f"local RABA snapshots aggregated: {len(local)}" + (" (results/local/, not published)" if local else ""))
