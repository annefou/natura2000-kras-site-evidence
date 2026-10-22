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
# # 02 — Species evidence on HEALPix: a GRID4EARTH DGGS-Zarr store
#
# The GBIF records of the site's Standard Data Form species (download
# [doi:10.15468/dl.5epzsz](https://doi.org/10.15468/dl.5epzsz)) were clipped to the site boundary
# and placed on HEALPix cells by `healpix-connector` (WGS84 ellipsoid, NESTED, depth 13, about
# 800 m) when the species crate was built. `pipeline/species_cells.py` reduced them to counts per
# cell, species, year and source dataset (`results/species/cells.csv`); no coordinates or record
# identifiers leave `data/`.
#
# This notebook writes those counts as a Zarr v3 store with the GRID4EARTH DGGS conventions
# (`zarr-conventions/dggs` v1 group attributes, CF `healpix` grid mapping, `cell_ids` coordinate),
# using `healpix_connector.dggs_zarr` so that the metadata match what `healpix-convert` writes. Any
# DGGS-aware reader (xdggs, healpix-plot, the riomar dashboard) can then overlay it on other
# HEALPix layers. The Land Use database cells are written the same way, but only locally.
#
# The counts are derived from records licensed CC BY-NC 4.0 (GBIF applies the most restrictive
# licence among the download's datasets), so the store carries that licence too.

# %%
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from healpix_connector.dggs_zarr import cf_grid_mapping_attrs, dggs_attrs

REPO = Path("..").resolve()
CFG = tomllib.loads((REPO / "config" / "study.toml").read_text())["study"]
SITE, DEPTH = CFG["site"], CFG["healpix_depth"]
STORE = REPO / "results" / "healpix" / f"gbif-{SITE}-d{DEPTH}.zarr"
INAT = "50c9509d-22c7-4a22-a47d-8c48425ef4a7"  # iNaturalist Research-grade Observations (GBIF dataset key)

# %%
cells = pd.read_csv(REPO / "results" / "species" / "cells.csv", dtype={"year": "Int64"})
print(f"{cells.records.sum()} records, {cells.cell_ids.nunique()} cells, {cells.species.nunique()} species")

# %%
ids = np.array(sorted(cells.cell_ids.unique()), dtype=np.uint64)
species = sorted(cells.species.unique())
years = sorted(int(y) for y in cells.year.dropna().unique())
by_sp = cells.pivot_table(index="cell_ids", columns="species", values="records", aggfunc="sum", fill_value=0)
by_sp = by_sp.reindex(index=ids, columns=species, fill_value=0)
by_yr = cells.dropna(subset=["year"]).pivot_table(index="cell_ids", columns="year", values="records", aggfunc="sum",
                                                  fill_value=0).reindex(index=ids, columns=years, fill_value=0)
per_cell = cells.groupby("cell_ids")
inat = cells[cells.dataset_key == INAT].groupby("cell_ids")["records"].sum().reindex(ids, fill_value=0)
total = per_cell["records"].sum().reindex(ids)

ds = xr.Dataset(
    {
        "records": ("cells", total.values.astype(np.int32), {"long_name": "GBIF presence records in the cell"}),
        "records_by_species": (("cells", "species"), by_sp.values.astype(np.int32)),
        "records_by_year": (("cells", "year"), by_yr.values.astype(np.int32)),
        "records_inaturalist": ("cells", inat.values.astype(np.int32),
                                {"long_name": "records from iNaturalist Research-grade Observations"}),
        "last_year": ("cells", per_cell["year"].max().reindex(ids).astype("float").values,
                      {"long_name": "most recent record year in the cell (NaN: no dated record)"}),
        "crs": ((), 0, cf_grid_mapping_attrs(DEPTH)),
    },
    coords={"cell_ids": ("cells", ids, {"standard_name": "healpix_index", "grid_mapping": "crs"}),
            "species": species, "year": years},
    attrs={**dggs_attrs(DEPTH),
           "title": f"GBIF records of the Standard Data Form species inside Natura 2000 site {SITE}, per HEALPix cell",
           "source": "GBIF.org GBIF Occurrence Download https://doi.org/10.15468/dl.5epzsz, clipped to the EEA site boundary",
           "license": "CC BY-NC 4.0 (derived from the download; most restrictive licence among its datasets)",
           "comment": "Opportunistic records: counts reflect observer effort as much as occurrence; not abundance."},
)
STORE.parent.mkdir(parents=True, exist_ok=True)
ds.to_zarr(STORE, mode="w", zarr_format=3, consolidated=False)
xr.open_zarr(STORE, consolidated=False)

# %% [markdown]
# Check the store declares what GRID4EARTH readers expect: NESTED indexing, WGS84, depth 13.

# %%
back = xr.open_zarr(STORE, consolidated=False)
g = back.attrs["dggs"]
assert (g["name"], g["indexing_scheme"], g["refinement_level"], g["ellipsoid"]["name"]) == ("healpix", "nested", DEPTH, "wgs84")
print(g)
