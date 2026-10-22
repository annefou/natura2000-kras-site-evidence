# Input-crate builders (vendored)

These scripts build the EU-wide input crates of the study (Natura 2000 site + Standard Data Form,
Article 17, CORINE, CLC+ Backbone, GBIF species records). They are **vendored** (copied, then
adapted) from the BMD Single Access Point prototype (A. Fouilloux, FAIR2Adapt-funded), whose data
builders are reused here:

- Source: <https://github.com/annefou/bmd-sap-prototype>, `scripts/fixtures/`, commit
  `4f7404ae3b8025066e4c070a53d67762c2ea65b5`.
- Licence: MIT (as declared in that repository's `package.json`). This repository is also MIT.
- Funding of the original code: FAIR2Adapt, European Commission grant 101188256.

The repository does not import or call anything from the prototype at run time. Each file starts
with a header saying where it came from and what changed. The changes:

| File | Change |
|---|---|
| `common.py` | Author, funding and URLs from `config/study.toml` (no FAIR2Adapt-default constants); crates go to `data/crates/`, curated inputs come from `config/curated/`, the download cache is `data/cache/`. |
| `build_site_crate.py` | The ViewAction points at this study's pages, not the prototype. |
| `build_species_crate.py` | Records whose GBIF taxon key is a synonym or an infraspecific child of a Standard Data Form taxon (for example *Morimus funereus* → *Morimus asper funereus*) are mapped back through the GBIF v2 name match (accepted usage, then classification). In the prototype they were left without a Standard Data Form name. |
| `gbif_request.py` | The request is written to `config/curated/<site>/`. |
| `natura_site.py` | `load()` retries up to four times when the EEA service answers with no features (seen once during testing). |
| others | Header and usage line only. |

Run one with `pixi run python pipeline/builders/<script> --site SI3000276`, or let the Snakefile run
all of them (`pixi run rebuild`).
