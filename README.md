# Natura 2000 site evidence — Kras (SI3000276)

[![CI](https://github.com/annefou/natura2000-kras-site-evidence/actions/workflows/ci.yml/badge.svg)](https://github.com/annefou/natura2000-kras-site-evidence/actions/workflows/ci.yml)
[![Jupyter Book](https://github.com/annefou/natura2000-kras-site-evidence/actions/workflows/jupyter-book.yml/badge.svg)](https://annefou.github.io/natura2000-kras-site-evidence/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![FORRT](https://img.shields.io/badge/FORRT-replication%20(draft)-blue)](nanopubs/drafts/)
[![RO-Crate](https://img.shields.io/badge/RO--Crate-1.2-orange)](ro-crate-metadata.json)

> ## STATUS: draft
>
> This is a **draft study**. Its statements have **not yet been reviewed by an ecologist or by the
> Slovenian Distributed Centre of LifeWatch (ZRC SAZU)**. Nothing has been deposited (ROHub, Zenodo),
> no nanopublication has been published and no release has been made; those wait for review.
> Results computed from the Slovenian Land Use database are **not published** here (see
> [Data licensing](#data-licensing)). Comments and corrections are welcome: see
> [How to comment or correct](#how-to-comment-or-correct).

**What it is.** A workflow that gives Slovenia up-to-date, site-level information to act on in its
Natura 2000 sites, piloted on SAC **SI3000276 Kras**:

1. **Service (core).** Per Natura 2000 site: the current extent of permanent grassland, overgrown
   agricultural land, trees and shrubs, and forest; the change since the previous snapshot and since
   2002; *where* it changed (on HEALPix cells); and how current the underlying mapping is. Source: the
   national Land Use database of the Ministry of Agriculture, Forestry and Food (MKGP, "RABA"), whose
   monthly national snapshots are public at <https://rkg.gov.si/arhiv/RABA/?C=N;O=D> (methodology:
   [RABA_Read_me.pdf](https://rkg.gov.si/arhiv/RABA/RABA_Read_me.pdf)). *The code is public; the
   results are produced locally only, pending MKGP's permission.*
2. **Validation.** A FORRT replication (drafts) of Davidović, Čuš & Ivajnšič (2026), *Land-use
   dynamics and grassland succession challenges in the Natura 2000 site Kras*, Acta geographica
   Slovenica 66(1), [doi:10.3986/AGS.14021](https://doi.org/10.3986/AGS.14021) (CC BY-SA 4.0), which
   reports for 2002–2024 grasslands −2,814.9 ha (−26.9 %), overgrown areas +1,645.9 ha (+47.3 %),
   forest +1,242.6 ha (+5.3 %) (their Table 2).
3. **EU comparison.** What open EU-wide data detect for the same site and period: Article 17
   (national context), CORINE Land Cover and its change layers, CLC+ Backbone, HRL Grassland.
4. **Species (supporting).** GBIF records of the site's Standard Data Form species on HEALPix cells,
   written as a GRID4EARTH DGGS-Zarr v3 store.

## Background and source claim

> **PLACEHOLDER — to be finalised by the author.** The scientific paper this study rests on is being
> decided. The validation section currently replicates Davidović et al. (2026); the wider background
> (why grassland in Kras matters, habitat 62A0, the management context) will be written once the
> source claim is fixed.

## What the public data say so far (draft)

Inside SAC SI3000276 (48,042 ha), open EU-wide data **cannot tell** whether grassland, and with it
habitat 62A0 (Eastern sub-Mediterranean dry grasslands), is declining:

| Source | What it shows inside the site |
|---|---|
| Article 17, Slovenia, Continental region | 62A0 unfavourable-bad and declining (U2, D) in 2013–2018 and 2019–2024; reported area 194 → 172 km², a difference the 2019–2024 report attributes to a change of method. National, not site-level. |
| CORINE Land Cover change layers 2000–2018 | 7.4 ha lost from natural grasslands and pastures, all pastures → mineral extraction in 2000–2006; 0 ha gained. 25 ha mapping unit (5 ha for change). |
| CLC+ Backbone 2018, 2021 (10 m) | Permanent herbaceous 11,203.1 and 11,273.4 ha: two separate classifications, not a measure of change. |
| HRL Grassland 2018; change 2015–2018 | Grassland 8,219.9 ha in 2018 (17.1 %). Change layer: gain 6,143 ha and loss 1,775 ha, both classes labelled *unverified* by the product. |
| National Land Use database, per the paper | Grasslands −26.9 % and overgrown areas +47.3 % between 2002 and 2024. The paper's study area is a different polygon (see below). |
| GBIF, [doi:10.15468/dl.5epzsz](https://doi.org/10.15468/dl.5epzsz) | 290 of 423 records inside the site, in 87 HEALPix cells (depth 13); 37.9 % from iNaturalist; all 38 bat records from one 2004 survey; 6 of 25 Standard Data Form taxa without records (*Austropotamobius pallipes*, *Erannis ankeraria*, *Miniopterus schreibersii*, *Myotis capaccinii*, *Proteus anguinus*, *Vertigo angustior*). Opportunistic records: no abundance trend. |

![Grassland change by source](figures/main_result.png)

**Which boundary did the paper use?** Its Table 2 classes sum to about **40,120 ha**, which matches
its own sentence "Approximately 93% of the plateau (401 km²) lies within the Natura 2000 network"
(Kras plateau, 429 km²). That is neither SAC SI3000276 Kras (48,042 ha) nor SPA SI5000023 Kras
(58,753 ha), and no public combination of the two matches it (intersection 44,981 ha, union
61,814 ha; the SAC's two parts are 22,280 and 25,763 ha). The authors used a ZRSVN polygon that is
not published. The replication therefore compares **shares and relative change** on SAC SI3000276 (a
stated approximation), records absolute hectares as not comparable, and asks the authors for their
polygon (TODO).

## How to run

```bash
git clone https://github.com/annefou/natura2000-kras-site-evidence.git
cd natura2000-kras-site-evidence
pixi install
pixi run snakemake --cores 1     # analysis, HEALPix store, figures, run crate from the committed inputs (offline)
pixi run rebuild                 # rebuild every EU and GBIF input from its source (network, ~4 min)
pixi run raba                    # national Land Use database: LOCAL results only, in results/local/ (see below)
pixi run fire                    # 2022 Kras fire vs land-use change since 2009: LOCAL results only (see below)
pixi run lidar-check             # read one national LiDAR tile onto HEALPix (summary in results/lidar/)
pixi run -e tests test           # the template's test suite
```

`pixi run fire` tests whether grassland that became overgrown after 2009 burned more than its share in
the July 2022 Kras fire. It fetches the open inputs (Copernicus EMS EMSR604 burnt area, EFFIS polygon
206388, Copernicus DEM), samples eight Land Use snapshots (2009-10-16 to 2026-09-30, about 4.5 GB
downloaded one at a time, about 30 min) on a 25 m grid, counts a change only when two later snapshots
confirm it, and compares burn rates on HEALPix depth-15 cells (WGS84, NESTED) with a spatial block
bootstrap. Code is public; results stay in `results/local/fire/` because they derive from the Land Use
database.

`pixi run lidar-check` downloads tile TM_402_75 (Komen, 66 MB) from the ARSO LiDAR archive (LSS
2011–2015, CC BY 4.0, "Geodetska uprava Republike Slovenije"), sets EPSG:3794 (the header has no CRS)
and reports density, classes and HEALPix depth-19 cells.

`pixi run raba` downloads the configured snapshots of the Land Use database (2002, 2012-12-04,
2015-06-30, 2018-06-30, 2024-06-30) and the latest month-end one, 0.2–0.7 GB each, processes them one at
a time and deletes each archive after aggregation. It writes, all under the gitignored `results/local/`:
`numbers.csv`, `validation.csv`, `eu_vs_raba.csv`, `service.json`, `latest.md`, figures (shares vs the
paper, service-class areas, change map, currency map, EU vs national) and a local Workflow Run Crate.

Every input crate keeps its provenance (`results/eu/*/ro-crate-metadata.json`); each public run is
packaged as a Workflow Run Crate in `results/run-crate/` (version = run date; not deposited).

## Data licensing

| Data | Licence | In this repository |
|---|---|---|
| Natura 2000, Standard Data Form, Article 17 (EEA, Reportnet) | CC BY 4.0 (Reportnet 2019–2024 delivery states none; compilation note in its crate) | small tables in `results/eu/` |
| CORINE, CLC+ Backbone, HRL Grassland (Copernicus Land Monitoring Service) | free of charge for any purpose | small tables in `results/eu/` |
| GBIF download [doi:10.15468/dl.5epzsz](https://doi.org/10.15468/dl.5epzsz) | CC BY-NC 4.0 | **raw records not committed**; only counts per HEALPix cell, species, year (`results/species/`, `results/healpix/`), which carry CC BY-NC 4.0 |
| Davidović et al. 2026 | CC BY-SA 4.0 | PDF in `paper/`, Table 2 values in `config/validation/` |
| **Land Use database (MKGP RABA)** | **not stated** in RABA_Read_me.pdf; the 2002 archive contains *Terms and Conditions of use* restricting the data to internal, personal or non-commercial use, with prior notification to MKGP, and forbidding non-internal reproduction or display without MKGP's written permission | **nothing committed or published**: downloads in `data/raba/`, results in `results/local/`, both gitignored. Code only. |

The site's pages describe what is monitored, from which data and how to run it locally, but show no
result from the Land Use database until MKGP grants permission (request to `raba.mkgp@gov.si`: TODO).

## How to comment or correct

This study is meant to be checked and corrected by the people who know the site. Open an issue:

- **[Scientific review](../../issues/new?template=scientific-review.yml)** — a claim, figure or
  step that is wrong, missing or overstated, and your suggested correction.
- **[Data or site correction](../../issues/new?template=data-correction.yml)** — the Standard Data
  Form, Article 17 code labels, the boundary, or national data that could fill a gap.

Corrections are credited by name (and ORCID, if you give one) in the study and in any later release.
Expert input is especially wanted on:

1. the **62A0 trend statement** (`results/summary.json`, `notebooks/03_analysis.py` § 7);
2. the **official labels of the Article 17 pressure codes** beyond PA05 (only codes are shown now);
3. whether CORINE **natural grasslands (321) + pastures (231)** is a fair proxy for 62A0 on Kras;
4. **national datasets** that could replace the 2004 bat records and the missing records (e.g.
   *Proteus anguinus*);
5. the **study-area polygon** of Davidović et al. 2026, to compare absolute hectares.

## Repository structure

```
config/          study.toml (site, snapshots, authors, funding, repository URL), GBIF download key, validation targets
pipeline/        builders/ (EU input crates, vendored), raba.py + raba_report.py (local), hrl_grassland.py, run_crate.py, ...
notebooks/       01 inputs · 02 species -> HEALPix DGGS-Zarr · 03 analysis · 04 figures (public data only)
results/         eu/ · species/ · healpix/ · validation/targets.csv · summary.* · run-crate/   (local/ is gitignored)
figures/         public figures used in the book
nanopubs/        FORRT chain drafts (not published)
service/         the service pages of the site (what is monitored; no national-data results)
blog/            draft story page
paper/           Davidović et al. 2026 (CC BY-SA 4.0)
docs/            the template's reference material
```

## Built from a template

Created from [`sciencelivehub/forrt-replication-template`](https://github.com/sciencelivehub/forrt-replication-template),
which ships the operating manual ([`CLAUDE.md`](CLAUDE.md), [`AGENTS.md`](AGENTS.md)), domain
conventions ([`DOMAIN.md`](DOMAIN.md)), reference docs (`docs/`) and the FORRT chain tooling.

## Acknowledgements and funding

- Author: Anne Fouilloux ([ORCID 0000-0002-1784-2920](https://orcid.org/0000-0002-1784-2920)), LifeWatch ERIC.
- Funding: LifeWatch ERIC; GRID4EARTH2 (grant number: TODO).
- The EU input-crate builders are reused from the BMD Single Access Point prototype (A. Fouilloux,
  FAIR2Adapt-funded, European Commission grant 101188256), vendored in `pipeline/builders/` with their
  origin stated in each file.
- HEALPix tooling: [healpix-connector](https://doi.org/10.5281/zenodo.22904851) 0.1.0 and healpix-geo
  (GRID4EARTH).
- Source of the national land-use data: MKGP, Land Use database (RABA).

## TODO

- [ ] **Repository URL** after transfer to the GRID4EARTH organisation and then LifeWatch ERIC:
      update `config/study.toml` `[repository]`, then
      `grep -rl "annefou/natura2000-kras-site-evidence\|annefou.github.io/natura2000-kras-site-evidence" --exclude-dir=.git --exclude-dir=.pixi .`
      (README badges and clone line, CITATION.cff, codemeta.json, myst.yml, Dockerfile, index.md,
      service/, blog/, docs/fair4rs-checklist.md, docs/forrt-form-fields.md).
- [ ] **GRID4EARTH2 grant number and funder**: not found in local files (the ESA contract
      4000147951/25/I-NS found locally is GRID4EARTH phase 1). Fill in `config/study.toml`.
- [ ] **MKGP permission** to publish results derived from the Land Use database (`raba.mkgp@gov.si`);
      the 2002 Terms and Conditions also ask for prior notification of use.
- [ ] **Authors' study-area polygon** (University of Maribor) for the validation in absolute hectares.
- [ ] **Ecologist review** of the 62A0 statement and of the CORINE proxy; review by ZRC SAZU.
- [ ] **Official labels of the Article 17 pressure codes** beyond PA05.
- [ ] **HRL Grassland 2017–2023** (yearly, 10 m) from the Copernicus Data Space Ecosystem (needs an account).
- [ ] **DestinE climate inputs** (Climate DT, ERA5 on Earth Data Hub) are not included.
- [ ] Article 17 **species** status (the builder covers habitats only).
- [ ] Optionally extend the service to all Slovenian Natura 2000 sites (`config/study.toml` `[raba] sites`).

## Citation

See [`CITATION.cff`](CITATION.cff). Please also cite Davidović et al. (2026),
[doi:10.3986/AGS.14021](https://doi.org/10.3986/AGS.14021), and the GBIF download
[doi:10.15468/dl.5epzsz](https://doi.org/10.15468/dl.5epzsz).
