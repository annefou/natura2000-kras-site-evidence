# 02 — AIDA Sentence

> Run the pre-flight checklist in `docs/forrt-form-fields.md` § Pre-flight checklist before drafting.

> **DRAFT — not published.** Not reviewed by an ecologist or by the Slovenian Distributed Centre of LifeWatch (ZRC SAZU). Do not publish before review.

**Form heading:** *"AIDA Sentence — Make structured scientific claims following the AIDA model"*

## Field-by-field draft

<!-- field: aida -->
### AIDA sentence (text input, required)

Atomic, Independent, Declarative, Absolute. One empirical finding. Must end with a full stop.

> _If your draft AIDA contains "and" linking two distinct findings, split into two AIDA nanopubs._

```
Between 2002 and 2024, the area of grassland in the Natura 2000 site Kras in Slovenia declined by about a quarter.
```

<!-- field: topic -->
### Select related topics/tags (search/select, optional)

Predefined topic vocabulary — list the labels you intend to pick from the dropdown.

```
grassland (Q1006733)
land use (Q1165944)
Natura 2000 site (Q15069452)
ecological succession (Q188230)
```

<!-- field: project -->
### Relates to this nanopublication (search/select, required)

URI of the nanopub the AIDA derives from.

- For paper-rooted chains: the Quote-with-comment URI (from step 01).
- For question-rooted chains: the PICO or PCC URI (from step 01).

Pull the URI from `nanopubs/PUBLISHED.md`.

```
«URI of step 01 (Quote-with-comment)»
```

<!-- field: dataset -->
### Supported by datasets (text input, optional)

DOIs/URLs of datasets that ground the AIDA claim.

- URL 1: https://rkg.gov.si/arhiv/RABA/?C=N;O=D (Land Use database archive, MKGP; no DOI)

<!-- field: publication -->
### Supported by other publications (text input, optional)

DOIs/URLs of publications that support the AIDA claim — e.g. peer-reviewed methods papers, or the original paper if not already cited via the Quote.

- DOI 1: https://doi.org/10.3986/AGS.14021 (Davidović, Čuš & Ivajnšič 2026)

> **Known platform bug (2026-04-26):** if both *Supported by datasets* AND *Supported by other publications* are populated and publishing fails, fall back to publishing this AIDA via Nanodash. The URI namespace becomes `https://w3id.org/np/...` (still valid and citable).

## Publication note

After publishing, paste the resulting URI into `nanopubs/PUBLISHED.md` step 02.
