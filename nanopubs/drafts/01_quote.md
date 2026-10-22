# 01 — Quote-with-comment (paper-rooted chains)

> Run the pre-flight checklist in `docs/forrt-form-fields.md` § Pre-flight checklist before drafting.
>
> If this is a question-rooted chain, use `01_pico.md` or `01_pcc.md` instead — see `docs/chain-decision-tree.md`.
>
> **After choosing the chain shape, delete the two step-1 alternates you aren't using.** Once you've decided this chain is paper-rooted and keep `01_quote.md`, run:
> ```bash
> rm nanopubs/drafts/01_pico.md nanopubs/drafts/01_pcc.md
> ```

> **DRAFT — not published.** Prepared for review; not reviewed by an ecologist or by the Slovenian Distributed Centre of LifeWatch (ZRC SAZU). Do not publish before review.

**Form heading:** *"Annotate a paper quotation — Annotating a paper quotation with personal interpretation"*

## Field-by-field draft

<!-- field: paper -->
### Cited DOI (text input, required)

Format: starts with `10.` — bare DOI, **NOT** `https://doi.org/...` form.

```
10.3986/AGS.14021
```

### Quote mode (radio button)

- [x] **Quote whole text (less than 500 characters)**
- [ ] Quote start/end *(use this if the quote exceeds 500 chars)*

<!-- field: quotation -->
### The exact quotation from the paper (max. 500 characters) (textarea, required)

Verbatim from the paper PDF in `paper/`. Character-for-character. ≤ 500 chars in whole-text mode.

> _Read the PDF first. Don't paraphrase from memory. See `docs/verify-before-drafting.md`._

```
Grasslands declined by 2,815 ha (27%) to 7,667 ha (19%), contracting by 128 ha/yr, especially near settlements and in the north. Overgrown areas rose by 1,646 ha (47%), reaching 5,125 ha (13%), with an average gain of 75 ha/yr, dispersed across the region.
```

Character count: 256 / 500. Verified against `paper/Davidovic_Cus_Ivajnsic_2026_AGS14021.pdf` with `verify_quote` (page 7; match after whitespace / line-break-hyphen repair: the PDF splits "espe-cially" across a line).

<!-- field: quotation-end -->
### End of quotation (optional - use when quoting beginning and end of a longer passage, max. 500 characters) (textarea, optional)

Only when quoting the beginning *and* end of a longer passage — set the mode above to
**Quote start/end**, put the opening phrase under the previous heading and the closing
phrase here. Leave empty for a single short quote.

```

```

<!-- field: comment -->
### Our interpretation and explanation of why this quotation is relevant (max. 800 characters) (textarea, required)

Why this quote matters and what the replication tests. Connect the paper's claim to the work this repo does. Don't repeat the quote.

```
This is the grassland and overgrowth change in the Natura 2000 site Kras from the national Land Use database (MKGP), 2002-2024. We re-derive it from the same database's public archive snapshots with open code, compare shares and relative change (the authors' study-area polygon is not published), and ask whether open EU-wide layers (CORINE, HRL Grassland, CLC+ Backbone) detect a change of this size. They do not: CORINE change layers show 7.4 ha lost from grassland classes 2000-2018 inside SAC SI3000276.
```

## Publication note

After publishing, paste the resulting URI into `nanopubs/PUBLISHED.md` step 01.
