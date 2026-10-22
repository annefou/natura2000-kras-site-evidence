# Snakefile — Natura 2000 site evidence for Kras (SI3000276).
#
# Three entry points:
#
#   pixi run snakemake --cores 1
#       Default. Analysis, HEALPix store, figures and run crate from the inputs committed in results/
#       (EU tables, GBIF cell counts). No network needed. This is what CI runs.
#
#   pixi run rebuild      (= snakemake --cores 1 --config rebuild=1 --forcerun site_crate hrl_grassland)
#       Rebuilds every EU and species input from its source, in order:
#       site -> article17 -> corine / clcplus -> species (GBIF download key) -> HEALPix -> trend.
#       Needs network (EEA, CLMS, Reportnet, GBIF); about 3 minutes.
#
#   pixi run raba         (= snakemake --cores 1 --config raba=1)
#       The national Land Use database (MKGP RABA) layer: downloads each configured snapshot plus the
#       latest month-end one (~0.5-0.7 GB each, processed one at a time and deleted), then writes the
#       LOCAL report. Everything goes to results/local/ (gitignored): RABA-derived results are not
#       published until MKGP gives written permission (README.md § Data licensing).

import tomllib

CFG = tomllib.load(open("config/study.toml", "rb"))
SITE = CFG["study"]["site"]
DEPTH = CFG["study"]["healpix_depth"]
REBUILD = bool(int(config.get("rebuild", 0)))
RABA = bool(int(config.get("raba", 0)))
NB = "notebooks"
EU = "results/eu"
CRATES = "data/crates"
ZARR = f"results/healpix/gbif-{SITE}-d{DEPTH}.zarr"


def nb(name):
    return f"cd {NB} && jupytext --to notebook --execute {name}.py"


rule all:
    input:
        "figures/main_result.png",
        "results/summary.json",
        "results/run-crate/ro-crate-metadata.json",
        "blog/index.html",
        *(["results/local/service.json"] if RABA else []),


# ---------------------------------------------------------------------------------------------
# Input crates (only with --config rebuild=1). Each builder takes the site code; the order is the
# one the evidence is read in: site, then status (Article 17), then land cover, then species.
# ---------------------------------------------------------------------------------------------
if REBUILD:

    rule site_crate:
        output:
            f"{CRATES}/site-{SITE}/ro-crate-metadata.json",
        shell:
            f"python pipeline/builders/build_site_crate.py --site {SITE}"

    rule article17_crate:
        input:
            rules.site_crate.output,
        output:
            f"{CRATES}/article17-{SITE}/ro-crate-metadata.json",
        shell:
            f"python pipeline/builders/build_article17_crate.py --site {SITE}"

    rule corine_crate:
        input:
            rules.article17_crate.output,
        output:
            f"{CRATES}/landcover-{SITE}/ro-crate-metadata.json",
        shell:
            f"python pipeline/builders/build_corine_crate.py --site {SITE}"

    rule clcplus_crate:
        input:
            rules.article17_crate.output,
        output:
            f"{CRATES}/landcover10m-{SITE}/ro-crate-metadata.json",
        shell:
            f"python pipeline/builders/build_clcplus_crate.py --site {SITE}"

    rule species_crate:
        input:
            rules.site_crate.output,
            f"config/curated/{SITE}/gbif-download.txt",
        output:
            f"{CRATES}/species-{SITE}/ro-crate-metadata.json",
            f"{CRATES}/species-{SITE}/occurrences.csv",
        shell:
            f"python pipeline/builders/build_species_crate.py --site {SITE}"

    rule collect_eu:
        input:
            rules.site_crate.output,
            rules.article17_crate.output,
            rules.corine_crate.output,
            rules.clcplus_crate.output,
            rules.species_crate.output,
        output:
            f"{EU}/site-{SITE}/sdf-habitats.csv",
            f"{EU}/article17-{SITE}/art17-status.csv",
            f"{EU}/landcover-{SITE}/clc-changes.csv",
            f"{EU}/landcover10m-{SITE}/clcplus-areas.csv",
            f"{EU}/species-{SITE}/species-summary.csv",
        shell:
            "python pipeline/collect_eu.py"

    rule hrl_grassland:
        output:
            f"{EU}/hrl-grassland/areas.csv",
        shell:
            "python pipeline/hrl_grassland.py"

    rule species_cells:
        input:
            f"{CRATES}/species-{SITE}/occurrences.csv",
        output:
            "results/species/cells.csv",
        shell:
            "python pipeline/species_cells.py"


# ---------------------------------------------------------------------------------------------
# Analysis from the committed inputs (default).
# ---------------------------------------------------------------------------------------------
rule inputs:
    input:
        f"{EU}/site-{SITE}/sdf-habitats.csv",
        f"{EU}/species-{SITE}/species-summary.csv",
        f"{EU}/hrl-grassland/areas.csv",
    output:
        "results/sources.json",
    shell:
        nb("01_data_download")


rule healpix_species:
    input:
        "results/species/cells.csv",
    output:
        directory(ZARR),
    shell:
        nb("02_data_clean")


rule analysis:
    input:
        "results/sources.json",
        f"{EU}/article17-{SITE}/art17-status.csv",
        f"{EU}/landcover-{SITE}/clc-changes.csv",
        f"{EU}/landcover10m-{SITE}/clcplus-areas.csv",
        f"{EU}/hrl-grassland/areas.csv",
        "results/species/cells.csv",
        "config/validation/davidovic2026_table2.csv",
    output:
        "results/summary.json",
        "results/summary.csv",
        "results/validation/targets.csv",
    shell:
        nb("03_analysis")


rule figures:
    input:
        "results/summary.json",
        ZARR,
    output:
        "figures/main_result.png",
        "figures/corine_grassland.png",
        "figures/species_years.png",
        "figures/gbif_cells.png",
    shell:
        nb("04_figures")


rule run_crate:
    input:
        "results/summary.json",
        "figures/main_result.png",
    output:
        "results/run-crate/ro-crate-metadata.json",
    shell:
        "python pipeline/run_crate.py"


rule story_preview:
    input:
        "results/summary.json",
        "figures/main_result.png",
        "figures/gbif_cells.png",
    output:
        "blog/index.html",
    shell:
        "python pipeline/story_preview.py"


# ---------------------------------------------------------------------------------------------
# National Land Use database (only with --config raba=1). LOCAL results only.
# ---------------------------------------------------------------------------------------------
if RABA:
    SNAPSHOTS = {
        "2002": CFG["raba"]["baseline"],
        **{f"{n[5:9]}-{n[10:12]}-{n[13:15]}": n for n in CFG["raba"]["reference"] + CFG["raba"].get("comparison", [])},
    }

    rule raba_snapshot:
        output:
            "results/local/raba/{snap}/areas.csv",
        params:
            name=lambda w: SNAPSHOTS[w.snap],
        resources:
            disk=1,  # one at a time: each archive is 0.5-0.7 GB and is deleted after aggregation
        shell:
            "python pipeline/raba.py --snapshot {params.name}"

    rule raba_latest:
        output:
            touch("results/local/raba/.latest-checked"),
        shell:
            "python pipeline/raba.py --latest"

    rule raba_report:
        input:
            expand("results/local/raba/{snap}/areas.csv", snap=SNAPSHOTS),
            "results/local/raba/.latest-checked",
            "results/summary.json",
        output:
            "results/local/service.json",
            "results/local/numbers.csv",
            "results/local/validation.csv",
        shell:
            "python pipeline/raba_report.py"
