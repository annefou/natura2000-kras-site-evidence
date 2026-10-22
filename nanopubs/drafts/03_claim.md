# 03 — FORRT Claim

> Run the pre-flight checklist in `docs/forrt-form-fields.md` § Pre-flight checklist before drafting.

> **DRAFT — not published.** Not reviewed by an ecologist or by the Slovenian Distributed Centre of LifeWatch (ZRC SAZU). Do not publish before review.

**Form heading:** *"FORRT Claim — Declare an original claim according to FORRT, linking it to an AIDA sentence with a specific FORRT type."*

## Field-by-field draft

<!-- field: claim -->
### Short URI suffix as claim ID (text input, required)

Slug becomes part of the nanopub URI. Use kebab-case.

```
kras-natura2000-grassland-decline-2002-2024
```

<!-- field: label -->
### Label of the claim, to find it later (text input, required)

A descriptive title (not a sentence). Used for searches/discovery.

```
Grassland decline in Natura 2000 site Kras, 2002-2024, national Land Use database
```

<!-- field: aida -->
### Search for an AIDA sentence (search/select, required)

URI of the AIDA published in step 02. Pull from `nanopubs/PUBLISHED.md`.

> _If the AIDA was published via Nanodash (`w3id.org/np/...` namespace), the platform's search may not find it — paste the URI manually._

```
«URI of step 02 (AIDA sentence)»
```

<!-- field: forrtType -->
### Type of FORRT claim (dropdown, required)

Pick one. See `docs/claim-type-vocabulary.md` for the seven options and how to choose.

- [ ] computational performance (Computational & Performance)
- [ ] data governance (access control, licensing, FAIR compliance)
- [ ] data quality (preprocessing, validation, normalization)
- [x] descriptive pattern (distribution, trend, proportion)
- [ ] model performance (accuracy, F1 score, evaluation metrics)
- [ ] scalability (Computational & Performance)
- [ ] statistical significance (significant difference, relationship, or effect)

<!-- field: source -->
### Source URI (text input, optional)

Full URL form: `https://doi.org/...` (NOT bare DOI).

```
https://doi.org/10.3986/AGS.14021
```

## Publication note

After publishing, paste the resulting URI into `nanopubs/PUBLISHED.md` step 03.
