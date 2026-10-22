# 06 — CiTO Citation

> Run the pre-flight checklist in `docs/forrt-form-fields.md` § Pre-flight checklist before drafting.

> **DRAFT — not published.** Not reviewed by an ecologist or by the Slovenian Distributed Centre of LifeWatch (ZRC SAZU). Do not publish before review.

**Description:** *"Declare citations between papers or other works, using Citation Typing Ontology"*

## Field-by-field draft

<!-- field: work -->
### Identifier for the citing creative work (text input, required)

URI of the Outcome published in step 05. Pull from `nanopubs/PUBLISHED.md`.

```
«URI of step 05 (FORRT Replication Outcome)»
```

### List citations (repeatable group, required ≥1)

#### Citation 1 — back to the original paper

##### Citation Type (dropdown)

Choose based on the Outcome's validation status:

- Validated → `confirms`
- PartiallySupported → `qualifies`
- Contradicted → `disputes`

For question-rooted chains where there is no original paper to confirm/dispute, use `usesMethodIn` or `citesAsAuthority` for the methodology paper(s).

Write the chosen type in the block below (a vocabulary label such as `cites as authority`, or `citesAsAuthority`). `build-chain-draft` uses it as written; leave the block empty to have the type derived from the Outcome's validation status, which is right for paper-rooted chains only.

> **Note:** `replicates` is NOT in the Science Live dropdown (despite existing in upstream CiTO). When citing a notebook/tutorial that was directly reused, use **`credits`** instead.

```

```

##### DOI or other URL of the cited work (text input)

Must be a DOI (`https://doi.org/...`): the first citation is the work the chain is about. Leave the placeholder to use the paper in `CITATION.cff`. Links to other works, such as another chain's nanopublication, go under *Additional citations* below.

```
https://doi.org/10.3986/AGS.14021
```

#### Additional citations (optional)

If the Outcome cites methods papers, related replications, or upstream tools, add them here.

One line per further citation, in this exact form (each becomes a pre-filled row):

- Type: uses data from → URL: https://doi.org/10.2909/3899a4a7-dd0b-4729-b24f-278844f1a686 (CORINE Land Cover Change 2000-2006)
- Type: uses data from → URL: https://doi.org/10.2909/fe3425ad-a71e-454c-97a9-586613af8191 (CORINE Land Cover Change 2006-2012)
- Type: uses data from → URL: https://doi.org/10.2909/f30f1000-7cf8-43bb-872c-5eb093911b24 (CORINE Land Cover Change 2012-2018)

## Publication note

After publishing, paste the resulting URI into `nanopubs/PUBLISHED.md` step 06.

This completes the six-step FORRT chain. Optional next layers:

- **Research Software** (`drafts/07_research_software.md`) — if the repo *produces* a reusable software artefact.
- **Research Synthesis** (`drafts/08_synthesis.md`) — if this chain is one of several testing facets of a shared property.
