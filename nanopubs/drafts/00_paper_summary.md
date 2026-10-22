# Paper summary

> This is a working scratchpad for the paper-analysis phase. The output of this file feeds the Quote / AIDA / Claim drafts. It is not itself a nanopub.

**Reference paper:** Land-use dynamics and grassland succession challenges in the Natura 2000 site Kras: The socioeconomic perspective

**DOI:** 10.3986/AGS.14021 (resolves; checked with `resolve_doi`)

**Authors:** Danijel Davidović, Jure Čuš, Danijel Ivajnšič

**Year:** 2026 — *Acta geographica Slovenica* 66(1), 61–80. Licence CC BY-SA 4.0. PDF in `paper/`.

## Headline claim

> Grasslands declined by 2,815 ha (27%) to 7,667 ha (19%), contracting by 128 ha/yr, especially near settlements and in the north. Overgrown areas rose by 1,646 ha (47%), reaching 5,125 ha (13%), with an average gain of 75 ha/yr, dispersed across the region.

(Section 3.1, page 7 of the PDF; verified with `verify_quote`.)

## Methodology summary

- **Data sources:** land-use vectors of the Ministry of Agriculture, Forestry and Food (the Land Use database, RABA) for 2002, 2012 and 2024; Natura 2000 site Kras boundary from ZRSVN (Institute of the Republic of Slovenia for Nature Conservation); subsidy-application data (GERK) for the socioeconomic part.
- **Processing:** original codes reclassified into ten classes (Table 1), rasterised at 5 × 5 m, EPSG:3794; QGIS, TerrSet (Land Change Modeler, Habitat and Biodiversity Modeler), Excel; GLMs in R.
- **Study area:** the part of the Kras Plateau (429 km²) inside Natura 2000, "Approximately 93% of the plateau (401 km²)"; the classes of Table 2 sum to ~40,120 ha.
- **Headline numbers (Table 2):** grasslands 10,481.85 → 8,692.2 → 7,666.9 ha (2002/2012/2024; −2,814.9 ha, −26.9 %); overgrown areas 3,478.91 → 3,629.4 → 5,124.8 ha (+1,645.9 ha, +47.3 %); forest 23,375.57 → 25,190.7 → 24,618.2 ha (+1,242.6 ha, +5.3 %).

## Replication design choice

- [ ] **Reproduction Study** — direct reproduction: same methodology, same tools.
- [x] **Replication Study** — replication with different methodology or conditions.
- [ ] **Reproduction/Replication Study** — both.

Same data source (the public archive of the same national database) but different conditions: the EEA boundary of SAC SI3000276 instead of the authors' unpublished polygon, exact vector areas instead of 5 m rasters, open Python instead of QGIS/TerrSet, and archive versions chosen by us because the paper does not name them.

## Notes for downstream drafts

- Compare **shares and relative change**, not absolute hectares (different study area). The boundary finding is in `notebooks/03_analysis.py` § 5.
- RABA-derived replication numbers are **not** written into any committed file until MKGP grants permission; the Outcome draft holds placeholders.
- The paper acknowledges the project "Development of Research Infrastructure for the International Competitiveness of the Slovenian RRI Space-RI-SI-LifeWatch".
