# 05 — FORRT Replication Outcome

> Run the pre-flight checklist in `docs/forrt-form-fields.md` § Pre-flight checklist before drafting.
>
> **Verify the actual numerical results first** by reading `results/` and `notebooks/03_analysis.py`. Don't quote numbers from memory. See `docs/verify-before-drafting.md`.

> **DRAFT — not published.** Not reviewed by an ecologist or by the Slovenian Distributed Centre of LifeWatch (ZRC SAZU). Do not publish before review.

## Field-by-field draft

<!-- field: outcome -->
### Short URI suffix for outcome ID (text input, required)

Slug. Use kebab-case.

```
kras-grassland-decline-replication-outcome
```

<!-- field: label -->
### Plain-text label for the outcome (text input, required)

Descriptive title.

```
Grassland decline in Natura 2000 site Kras 2002-2024: replication with public Land Use database snapshots (pending)
```

<!-- field: study -->
### Choose study (search/select, required)

URI of the Replication Study published in step 04. Pull from `nanopubs/PUBLISHED.md`.

```
«URI of step 04 (FORRT Replication Study)»
```

<!-- field: repo -->
### Repository URL (text input, required)

Use the Zenodo **version DOI** URL for the release the results came from — not a
bare branch URL, and not the concept DOI.

> **Why not the bare repo URL.** `https://github.com/ORG/REPO` names a *moving
> branch*. This Outcome asserts "this code produced this number", in a signed,
> immutable record. A branch URL means that assertion points at whatever `main`
> happens to be years from now — code that may never have produced the number
> above. A concept DOI has the same flaw: it resolves to the latest version.
> The version DOI pins the exact release. `docs/chain-decision-tree.md` § Anchor
> ranks the options: SWHID > Zenodo DOI > repo URL > Wayback.
>
> Both DOIs and the SWHID are in `CITATION.cff` under `identifiers:`, recorded
> automatically at release by `.github/workflows/release-identifiers.yml`. Take
> the one described as *"Version DOI"*.

```
https://doi.org/{{ZENODO_VERSION_DOI}}
```

<!-- field: date -->
### Choose completion date (text input, required)

```
«completion date: set when the outcome can be published»
```

<!-- field: validationStatus -->
### Choose validation status (dropdown, required)


This dropdown maps to the CiTO intention in step 06: Validated → `confirms`, PartiallySupported → `qualifies`, Contradicted → `disputes`.

- [ ] contradicted
- [ ] inconclusive
- [ ] not tested
- [ ] partially supported
- [ ] validated

<!-- field: confidenceLevel -->
### Choose confidence level (dropdown, required)

_Vocabulary not yet captured._

```

```

- [ ] high - Strong evidence, mostly agrees with original
- [ ] low - Limited evidence, significant disagreement
- [ ] moderate - Adequate evidence, partial agreement
- [ ] very high - Extensive evidence, high agreement with original
- [ ] very low - Minimal evidence, major disagreement

<!-- field: conclusion -->
### Describe the overall conclusion about the original claim (textarea, required)

Substantive interpretation. Headline comparison: replication's number vs the paper's number, sign + significance.

```
«PENDING: the replication numbers come from the national Land Use database (MKGP RABA). They are computed locally (results/local/validation.csv) and are NOT written here, because RABA-derived results are not published until MKGP gives written permission (raba.mkgp@gov.si). Fill in from the local run once permission is granted.»
```

<!-- field: evidence -->
### Describe the evidence that supports your conclusion (textarea, required)

Numerical results, test statistics, model coefficients. Read directly from `results/`.

```
«PENDING: the replication numbers come from the national Land Use database (MKGP RABA). They are computed locally (results/local/validation.csv) and are NOT written here, because RABA-derived results are not published until MKGP gives written permission (raba.mkgp@gov.si). Fill in from the local run once permission is granted.»

Public part (may be published): open EU-wide layers inside SAC SI3000276 detect far less change: CORINE change layers 7.4 ha lost from natural grasslands and pastures 2000-2018 (all pastures to mineral extraction, 2000-2006); HRL Grassland 2015-2018 gain and loss classes are labelled unverified by the product; CLC+ Backbone 2018 and 2021 are separate classifications (permanent herbaceous 11,203.1 and 11,273.4 ha). Source: results/summary.json.
```

<!-- field: limitations -->
### Describe what limits the conclusions of the study (textarea, optional)

Honest caveats. If the result is partial or contradicted, say so plainly. Don't overclaim.

```
Different study area from the paper (its ZRSVN polygon is not published), so absolute hectares are not comparable; shares and relative change are. RABA is updated from orthophoto interpretation on roughly a three-year cycle and its methodology changed over time (classes, minimum mapping unit, interpretation rules; RABA_Read_me.pdf), so part of any change between versions may be methodological; the paper says the same of its extreme values. The date of last change or review (D_OD) appears bulk-updated in recent versions and cannot show how current each area is. Not reviewed by an ecologist.
```

## Publication note

After publishing, paste the resulting URI into `nanopubs/PUBLISHED.md` step 05.
