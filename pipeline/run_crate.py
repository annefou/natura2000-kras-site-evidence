#!/usr/bin/env python3
"""Workflow Run Crate (Process Run Crate profile) of the public part of a run.

    pixi run python pipeline/run_crate.py

Writes results/run-crate/ro-crate-metadata.json describing one execution of the EU-data and species
layers: inputs (the input crates' sources, with their identifiers), the code that ran, and the
results with the draft answer. Each run is a new version (`version` = run date). DRAFT: nothing is
deposited; the crate is ready for a later deposit once reviewed.
"""
from __future__ import annotations

import json
import tomllib
from datetime import date, datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CFG = tomllib.loads((REPO / "config" / "study.toml").read_text())
SITE = CFG["study"]["site"]
OUT = REPO / "results" / "run-crate"

RESULTS = ["results/summary.json", "results/summary.csv", "results/sources.json", "results/validation/targets.csv",
           "results/species/cells.csv", f"results/healpix/gbif-{SITE}-d{CFG['study']['healpix_depth']}.zarr/",
           "figures/main_result.png", "figures/corine_grassland.png", "figures/species_years.png", "figures/gbif_cells.png"]
CODE = ["Snakefile", "pipeline/builders/", "pipeline/collect_eu.py", "pipeline/hrl_grassland.py",
        "pipeline/species_cells.py", "notebooks/01_data_download.py", "notebooks/02_data_clean.py",
        "notebooks/03_analysis.py", "notebooks/04_figures.py"]


def main() -> None:
    summary = json.loads((REPO / "results" / "summary.json").read_text())
    sources = json.loads((REPO / "results" / "sources.json").read_text())
    inputs = sorted({b for s in sources if not s["input"].startswith("Slovenian Land Use") for b in s["based_on"]})
    today = date.today().isoformat()
    a = CFG["authors"][0]
    graph = [
        {"@id": "ro-crate-metadata.json", "@type": "CreativeWork", "about": {"@id": "./"},
         "conformsTo": [{"@id": "https://w3id.org/ro/crate/1.2"}, {"@id": "https://w3id.org/ro/wfrun/process/0.5"}]},
        {"@id": "./", "@type": "Dataset",
         "name": f"Open EU-wide evidence on grassland (habitat {CFG['study']['habitat']}) in Natura 2000 site {SITE} Kras: run {today}",
         "description": ("Process Run Crate of one execution of the EU-data and species layers of the study. "
                         f"Verdict: {summary['verdict']}. DRAFT: not deposited; {summary['review_status']}."),
         "version": today, "datePublished": today, "license": {"@id": "https://creativecommons.org/licenses/by/4.0/"},
         "author": {"@id": a["orcid"]},
         "conformsTo": {"@id": "https://w3id.org/ro/wfrun/process/0.5"},
         "hasPart": [{"@id": f"../../{p}"} for p in RESULTS], "mentions": {"@id": "#run"},
         "spatialCoverage": {"@id": f"https://natura2000.eea.europa.eu/Natura2000/SDF.aspx?site={SITE}"},
         "abstract": summary["statement"],
         "usageInfo": ("Species counts (results/species, results/healpix) derive from GBIF download "
                       "doi:10.15468/dl.5epzsz and carry its licence, CC BY-NC 4.0.")},
        {"@id": a["orcid"], "@type": "Person", "name": a["name"], "affiliation": a["affiliation"]},
        {"@id": f"https://natura2000.eea.europa.eu/Natura2000/SDF.aspx?site={SITE}", "@type": "Place",
         "name": f"{SITE} Kras (Natura 2000 SAC)",
         "geo": {"@type": "GeoShape", "description": "results/eu/site-*/boundary-simplified.wkt (EEA, CC BY 4.0)"}},
        {"@id": "#run", "@type": "CreateAction", "name": f"Snakemake run of the EU-data and species layers, {today}",
         "endTime": datetime.now(timezone.utc).isoformat(timespec="seconds"),
         "instrument": {"@id": "../../Snakefile"},
         "object": [{"@id": i} for i in inputs], "result": [{"@id": f"../../{p}"} for p in RESULTS]},
        *[{"@id": f"../../{p}", "@type": ["File", "SoftwareSourceCode"] if p.endswith(".py") or p == "Snakefile"
           else "Dataset" if p.endswith("/") else "File"} for p in CODE + RESULTS],
        *[{"@id": i, "@type": "CreativeWork"} for i in inputs],
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "ro-crate-metadata.json").write_text(json.dumps({"@context": "https://w3id.org/ro/crate/1.2/context",
                                                            "@graph": graph}, indent=2, ensure_ascii=False) + "\n")
    print(f"[run-crate] {OUT.relative_to(REPO)}/ro-crate-metadata.json, version {today}, {len(inputs)} inputs")


if __name__ == "__main__":
    main()
