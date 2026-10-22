# 04 — FORRT Replication Study

> Run the pre-flight checklist in `docs/forrt-form-fields.md` § Pre-flight checklist before drafting.
>
> **Verify code first:** read the actual reproduction script in `notebooks/03_analysis.py` before writing the methodology field. See `docs/verify-before-drafting.md`.

> **DRAFT — not published.** Not reviewed by an ecologist or by the Slovenian Distributed Centre of LifeWatch (ZRC SAZU). Do not publish before review.

## Field-by-field draft

<!-- field: study -->
### Short URI suffix for study ID (text input, required)

Slug. Use kebab-case.

```
kras-grassland-decline-replication-open-code
```

<!-- field: label -->
### Label/name of replication study (text input, required)

Human-readable title.

```
Replication with open code and public archive snapshots: grassland and overgrowth change in Natura 2000 site Kras, 2002-2024
```

<!-- field: type -->
### Choose the study type (dropdown, required)

- [x] Replication Study - replication with different methodology or conditions
- [ ] Reproduction/Replication Study - study that is both, reproduction and replication
- [ ] Reproduction Study - direct reproduction: same methodology, same tools

<!-- field: claim -->
### Choose FORRT claim (search/select, required)

URI of the Claim published in step 03. Pull from `nanopubs/PUBLISHED.md`.

```
«URI of step 03 (FORRT Claim)»
```

<!-- field: scope -->
### Describe what part of the claim is reproduced/replicated. (textarea, required)

The **scope** of the claim being tested. Which aspect, what's in/out of scope. NOT methodology. NOT results. See `docs/pico-study-outcome-levels.md`.

```
The direction and relative size of change 2002-2024 in three land-use classes of the paper's Table 2 (grasslands, overgrown areas, forest) in the Natura 2000 site Kras, and their shares of the site in 2002, 2012 and 2024. Out of scope: the socioeconomic models (GLMs), the TerrSet change-process and spatial-trend analyses, and absolute hectares, which depend on a study-area polygon that is not published.
```

<!-- field: methodology -->
### Describe how the claim is reproduced/replicated. (textarea, required)

The **method** in plain prose. Read `notebooks/03_analysis.py` and any config files first. NOT exact numerical results.

```
Public snapshots of the Slovenian Land Use database (MKGP RABA) from https://rkg.gov.si/arhiv/RABA/ (2002: RABA_2002_SHP.ZIP; 2012: RABA_2012_12_04.RAR; 2024: RABA_2024_06_30.zip) are read with open Python code (pipeline/raba.py), reprojected from D48/GK (EPSG:3912, up to 2018) to D96/TM (EPSG:3794), clipped to the Natura 2000 boundary from the EEA end-2024 release, and reclassified into the paper's classes following its Table 1 (config/validation/reclass.csv). Areas are exact vector areas. Shares and relative change 2002-2024 are compared with the paper's Table 2. The same code reports the latest month-end snapshot as a monitoring service.
```

<!-- field: deviation -->
### Describe any deviations from original methodology. (textarea, optional)

What's different from the original method. Verify against the actual code, don't guess.

```
1) Study area: SAC SI3000276 Kras from the EEA (48,042 ha) instead of the authors' ZRSVN polygon of the Natura 2000 part of the Kras plateau (~40,120 ha, unpublished); the SAC's northern part (22,280 ha) is also reported. 2) Exact vector areas instead of 5 m rasterisation. 3) The paper does not say which version of each year it used; we use the versions named above. 4) The 2002 meadow codes 1310 and 1322, absent from the paper's Table 1, are mapped to grasslands. 5) Python instead of QGIS / TerrSet / Excel.
```

<!-- field: keyword -->
### Search keywords (Wikidata) (search/select, optional)

Provide labels (not QIDs) — the Wikidata search picks up labels.

```
grassland (Q1006733)
land use (Q1165944)
Natura 2000 site (Q15069452)
ecological succession (Q188230)
```

<!-- field: discipline -->
### Search discipline (Wikidata) (search/select, optional)

Provide labels.

```
landscape ecology (Q738011)
```

## Publication note

After publishing, paste the resulting URI into `nanopubs/PUBLISHED.md` step 04.
