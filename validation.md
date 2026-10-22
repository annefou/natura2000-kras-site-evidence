# Validation: replicating Davidović, Čuš & Ivajnšič (2026)

```{warning}
Draft FORRT chain (`nanopubs/drafts/`), not published. The replication numbers come from the national
Land Use database and are computed locally only (`results/local/validation.csv`) until MKGP gives
permission to publish them.
```

**Paper.** Land-use dynamics and grassland succession challenges in the Natura 2000 site Kras: The
socioeconomic perspective. *Acta geographica Slovenica* 66(1), 61–80,
[doi:10.3986/AGS.14021](https://doi.org/10.3986/AGS.14021), CC BY-SA 4.0.

**Claim under test** (Section 3.1, verified verbatim against the PDF):

> Grasslands declined by 2,815 ha (27%) to 7,667 ha (19%), contracting by 128 ha/yr, especially near
> settlements and in the north. Overgrown areas rose by 1,646 ha (47%), reaching 5,125 ha (13%), with an
> average gain of 75 ha/yr, dispersed across the region.

**Targets** (their Table 2; `config/validation/davidovic2026_table2.csv`, `results/validation/targets.csv`):

| Class | 2002 (ha) | 2012 (ha) | 2024 (ha) | Δ 2002–2024 |
|---|---:|---:|---:|---:|
| Forest | 23,375.57 | 25,190.7 | 24,618.2 | +1,242.6 ha (+5.3 %) |
| Grasslands | 10,481.85 | 8,692.2 | 7,666.9 | −2,814.9 ha (−26.9 %) |
| Overgrown areas | 3,478.91 | 3,629.4 | 5,124.8 | +1,645.9 ha (+47.3 %) |

**Method.** Same data source: the public archive snapshots of the same national database
(`RABA_2002_SHP.ZIP`, `RABA_2012_12_04.RAR`, `RABA_2024_06_30.zip`), reclassified with the paper's
Table 1 (`config/validation/reclass.csv`), clipped to the EEA boundary, exact vector areas, open Python.

**Boundary: what the paper used and what we use.** The classes of Table 2 sum to about 40,120 ha. The
paper says "Approximately 93% of the plateau (401 km²) lies within the Natura 2000 network" (Kras
plateau, 429 km²), and its boundary came from ZRSVN. So its area is the Natura 2000 part of the Kras
plateau, a polygon that is not published. It is not SAC SI3000276 Kras (48,042 ha), not SPA SI5000023
Kras (58,753 ha), and not their intersection (44,981 ha) or union (61,814 ha); the SAC's two parts
measure 22,280 ha (north) and 25,763 ha (south). **Decision:** compare **shares** and **relative change**
on SAC SI3000276 as a stated approximation (also reported for its northern part); record absolute
hectares but do not compare them; ask the authors for their polygon.

**Other deviations.** Exact vector areas instead of a 5 m raster; archive versions chosen by us (the
paper does not name them); the 2002 meadow codes 1310 and 1322 (absent from Table 1) counted as
grasslands; in 2002 code 1500 means mixed agricultural land and forest and is counted as overgrown, as
Table 1 does for 1500.
