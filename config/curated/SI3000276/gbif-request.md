# GBIF download request — Kras (SI3000276)

Generated 2026-10-22 by `pixi run gbif-request --site SI3000276`. Regenerate rather than edit.

## Open this link while logged in to gbif.org

[Open the search on GBIF](https://www.gbif.org/occurrence/search?geometry=POLYGON+%28%2813.56526230878951+45.84730619257539%2C13.591505047173458+45.7991207264173%2C13.622787045040141+45.786123452504505%2C13.66352226291595+45.79007812652207%2C13.80088339062217+45.72170908727634%2C13.843872155325085+45.717739900366404%2C13.858470944209566+45.7358918461543%2C13.846198834355334+45.748774592715556%2C13.876438208374635+45.75196879879141%2C13.913162612604195+45.7478244060671%2C13.939758425892663+45.728935108051566%2C13.948619583565458+45.69940962963531%2C13.924651558485055+45.70828064351386%2C13.88604630327948+45.6969599907502%2C13.86715821374459+45.70833791689289%2C13.82139044263043+45.694650582377385%2C13.851307680962668+45.65812478351008%2C13.899827799557986+45.632818880704235%2C13.863008531369571+45.61730582957842%2C13.840497911311969+45.58862386764113%2C13.877709880437282+45.53269709406475%2C13.85650340723246+45.52323485638459%2C13.889548837294033+45.45211505308755%2C13.975112470540655+45.4386114880152%2C14.006622528209673+45.47033788252454%2C13.987519798062628+45.499453030373154%2C14.01190679021912+45.50766752773668%2C14.070360421167223+45.474973482076784%2C14.107409910390679+45.482248450511136%2C14.104922334726647+45.49837078735011%2C14.07859806275636+45.50627835727421%2C14.109819874599877+45.53062878186565%2C14.103575964774786+45.54958671517042%2C13.939302900310599+45.60843287636692%2C13.963273119073085+45.610355087687736%2C13.986465590838026+45.63583218244298%2C14.050871508392076+45.66819777339522%2C14.082158740415128+45.67121794918399%2C14.083556269824202+45.69145686501164%2C14.041277826189873+45.71033949520604%2C14.036227709948387+45.737470509480936%2C14.00388972915941+45.748541193410425%2C13.99107701124236+45.73308283434711%2C13.97317796296841+45.73756206243898%2C13.83935031687484+45.84088760780765%2C13.81173614194584+45.84735953895934%2C13.801480022924181+45.82940327179673%2C13.731464096294143+45.85658948155268%2C13.741642359608523+45.87336135710019%2C13.734166756203173+45.88485344762176%2C13.588444006670521+45.89735056130592%2C13.56526230878951+45.84730619257539%29%29&has_coordinate=true&has_geospatial_issue=false&taxon_key=7RCB7&taxon_key=5WNNK&taxon_key=SH4Q&taxon_key=5ZJCR&taxon_key=6FYZY&taxon_key=3B4GS&taxon_key=NW8JT&taxon_key=BFQCJ&taxon_key=3LXXH&taxon_key=3R94W&taxon_key=3TNTB&taxon_key=72P4Y&taxon_key=43JSW&taxon_key=6RN8X&taxon_key=BLDJ2&taxon_key=456DK&taxon_key=6RRRM&taxon_key=7443L&taxon_key=456G3&taxon_key=4N3XG&taxon_key=4S977&taxon_key=4S97C&taxon_key=4S97S&taxon_key=595F2&taxon_key=7FRLB)

## Before downloading, check

The page should show about **423 occurrences** (the GBIF API's count for the same filter on
2026-10-22). If it shows many more, the website has read the taxon keys in another taxonomy: do not
download, and say so.

## Then

1. **Download → Simple** (the format healpix-connector reads).
2. GBIF emails when it is ready, with a DOI (`10.15468/dl.…`).
3. Record the **download key** (e.g. `0012345-260924123456789`) in `fixtures/curated/SI3000276/gbif-download.txt`.

The download and its DOI belong to the person who submits it; the species crate cites it.

## What the link encodes

- **Area:** a simplified shape that covers the whole site boundary (buffered 0.01°); records
  outside the exact boundary are clipped when the species crate is built.
- **Quality:** records with coordinates and no geospatial issue.
- **Taxonomy:** Catalogue of Life XR, checklist `7ddf754f-d193-4cc9-b351-99906754a03b` (healpix-connector's default and
  GBIF.org's).
- **Taxa:** the 25 species and subspecies of the site's Standard Data Form.

| Standard Data Form name | Taxon key | Matched name | Match |
|---|---|---|---|
| Austropotamobius pallipes | `7RCB7` |  | EXACT |
| Bombina variegata | `5WNNK` |  | EXACT |
| Cerambyx cerdo | `SH4Q` |  | EXACT |
| Coenonympha oedippus | `5ZJCR` |  | EXACT |
| Erannis ankeraria | `6FYZY` |  | EXACT |
| Eriogaster catax | `3B4GS` |  | EXACT |
| Euphydryas aurinia | `NW8JT` |  | EXACT |
| Euplagia quadripunctaria | `BFQCJ` |  | EXACT |
| Himantoglossum adriaticum | `3LXXH` |  | EXACT |
| Klasea lycopifolia | `3R94W` |  | EXACT |
| Leptodirus hochenwartii | `3TNTB` |  | EXACT |
| Lucanus cervus | `72P4Y` |  | EXACT |
| Miniopterus schreibersii | `43JSW` |  | EXACT |
| Moehringia tommasinii | `6RN8X` |  | EXACT |
| Morimus asper funereus | `BLDJ2` |  | EXACT |
| Myotis blythii | `456DK` |  | EXACT |
| Myotis capaccinii | `6RRRM` |  | EXACT |
| Myotis emarginatus | `7443L` |  | EXACT |
| Myotis myotis | `456G3` |  | EXACT |
| Proteus anguinus | `4N3XG` |  | EXACT |
| Rhinolophus euryale | `4S977` |  | EXACT |
| Rhinolophus ferrumequinum | `4S97C` |  | EXACT |
| Rhinolophus hipposideros | `4S97S` |  | EXACT |
| Triturus carnifex | `595F2` |  | EXACT |
| Vertigo angustior | `7FRLB` |  | EXACT |
