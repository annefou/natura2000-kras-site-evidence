#!/usr/bin/env python3
"""Copy the small, redistributable tables of the EU input crates into results/eu/ (committed).

    pixi run python pipeline/collect_eu.py

The crates themselves (data/crates/, gitignored) hold large GeoJSON and, for species, the raw GBIF
records, which are CC BY-NC 4.0 and are NOT committed. What is copied here:

  site boundary (simplified, WKT + GeoJSON), Standard Data Form rows      EEA Natura 2000, CC BY 4.0
  Article 17 status and pressures                                         EEA / Reportnet, CC BY 4.0 (compilation)
  CORINE status areas and change inside the site; CLC+ Backbone areas     CLMS, free for any purpose
  GBIF per-species summary, per-species-year counts, dataset list         derived from doi:10.15468/dl.5epzsz
                                                                          (CC BY-NC 4.0)
Each crate's ro-crate-metadata.json is copied alongside, so every table keeps its provenance.
"""
from __future__ import annotations

import json
import shutil
import tomllib
from pathlib import Path

from shapely.geometry import mapping, shape
from shapely.ops import unary_union

REPO = Path(__file__).resolve().parents[1]
SITE = tomllib.loads((REPO / "config" / "study.toml").read_text())["study"]["site"]
CRATES = REPO / "data" / "crates"
OUT = REPO / "results" / "eu"

TABLES = {
    f"site-{SITE}": ["sdf-habitats.csv", "sdf-species.csv"],
    f"article17-{SITE}": ["art17-status.csv", "art17-pressures.csv"],
    f"landcover-{SITE}": ["clc-status-areas.csv", "clc-changes.csv"],
    f"landcover10m-{SITE}": ["clcplus-areas.csv"],
    f"species-{SITE}": ["species-summary.csv", "species-years.csv", "datasets.csv"],
}


def main() -> None:
    for crate, files in TABLES.items():
        dest = OUT / crate
        dest.mkdir(parents=True, exist_ok=True)
        for f in [*files, "ro-crate-metadata.json"]:
            shutil.copy2(CRATES / crate / f, dest / f)
    # Boundary: simplified to ~10 m for display and for the geographical-coverage draft. The exact
    # boundary stays in data/crates/site-*/boundary.geojson and is re-fetched from the EEA.
    gj = json.loads((CRATES / f"site-{SITE}" / "boundary.geojson").read_text())
    geom = unary_union([shape(f["geometry"]) for f in gj["features"]]).simplify(0.0001, preserve_topology=True)
    (OUT / f"site-{SITE}" / "boundary-simplified.wkt").write_text(geom.wkt + "\n")
    (OUT / f"site-{SITE}" / "boundary-simplified.geojson").write_text(json.dumps(
        {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"sitecode": SITE,
         "source": "EEA Natura 2000 end-2024 release (CC BY 4.0), simplified to 0.0001 degree"},
         "geometry": mapping(geom)}]}) + "\n")
    print(f"[collect] {OUT.relative_to(REPO)}/: {sum(len(v) for v in TABLES.values())} tables + boundary")


if __name__ == "__main__":
    main()
