#!/usr/bin/env python3
"""GBIF presence records inside the site -> counts per HEALPix cell, species and year (committed).

    pixi run python pipeline/species_cells.py

Input: data/crates/species-<site>/occurrences.csv (raw records of doi:10.15468/dl.5epzsz, CC BY-NC 4.0,
never committed). Output: results/species/cells.csv with one row per (cell, species, year) and the
number of records. No coordinates, record identifiers or observer names leave data/. The cells are
those healpix-connector assigned in the species crate (WGS84 ellipsoid, NESTED, depth 13, ~800 m).
"""
from __future__ import annotations

import tomllib
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
CFG = tomllib.loads((REPO / "config" / "study.toml").read_text())["study"]
SITE, DEPTH = CFG["site"], CFG["healpix_depth"]


def main() -> None:
    occ = pd.read_csv(REPO / "data" / "crates" / f"species-{SITE}" / "occurrences.csv", dtype={"year": "Int64"})
    cell = f"cell_depth{DEPTH}"
    occ["sdf_name"] = occ["sdf_name"].fillna("(not matched to the Standard Data Form)")
    out = (occ.groupby([cell, "sdf_name", "year", "datasetKey"], dropna=False).size().rename("records").reset_index()
              .rename(columns={cell: "cell_ids", "sdf_name": "species", "datasetKey": "dataset_key"}))
    dest = REPO / "results" / "species"
    dest.mkdir(parents=True, exist_ok=True)
    out.to_csv(dest / "cells.csv", index=False)
    print(f"[species-cells] {len(occ)} records -> {out.cell_ids.nunique()} cells, {out.species.nunique()} species")


if __name__ == "__main__":
    main()
