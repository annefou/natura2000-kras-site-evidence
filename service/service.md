# Service: what is monitored

```{note}
**No results from the national Land Use database are published here.** The data are public downloads,
but their terms of use are unclear (the current readme states no licence; the 2002 archive's terms
restrict use to internal, personal or non-commercial purposes, with prior notification to MKGP, and
forbid non-internal reproduction or display without written permission). Results are produced
**locally** until MKGP (raba.mkgp@gov.si) gives permission. Source of the data: MKGP, Land Use database (RABA).
```

## For each Natura 2000 site

| What | How |
|---|---|
| Current extent of **permanent grassland** (codes 1300, 1321; in 2002: 1310, 1321, 1322) | area and share, latest month-end snapshot |
| **Overgrown agricultural land** (1410 overgrown agricultural area, 1600 uncultivated agricultural land, 1800 forest trees on agricultural land) | idem |
| **Trees and shrubs** (1500) | idem (in 2002, 1500 meant *mixed use: agricultural land and forest*) |
| **Forest** (2000) | idem |
| **Change** since the previous snapshot and since 2002 | difference of exact vector areas inside the EEA site boundary |
| **Where** | 25 m sample grid aggregated to HEALPix cells (depth 15, ~3.9 ha, WGS84, NESTED) |
| **How current** | `D_OD`, the date of the last change or review of each polygon, area-weighted |

Codes and names: [RABA_Read_me.pdf](https://rkg.gov.si/arhiv/RABA/RABA_Read_me.pdf) (MKGP, August 2026).

## Data

- National snapshots, public archive: <https://rkg.gov.si/arhiv/RABA/?C=N;O=D> — monthly from March
  2015, several versions a year 2006–2014, one in 2002 (`RABA_2002_SHP.ZIP`).
- Coordinate systems: D48/GK (EPSG:3912) up to 2018, D96/TM (EPSG:3794) from 2019; everything is
  computed in EPSG:3794.
- Site boundaries: EEA Natura 2000 end-2024 release.

## How current is "monthly"?

The readme says that "On average, LU DB in about one third of the territory of the Republic of Slovenia
is updated annually", from orthophoto interpretation, and that the database "is updated within couple of
years since the change in field". A monthly snapshot is therefore not a monthly observation: the
effective refresh of any given area is about three years. The service reports `D_OD` so that users can
see this, but in recent snapshots `D_OD` appears to have been updated for whole areas at once, so it
cannot yet tell how recently each area was actually re-interpreted. To be clarified with MKGP.

## Run it locally

```bash
pixi install
pixi run raba        # downloads each configured snapshot + the latest month-end one, one at a time
```

Outputs (all in `results/local/`, gitignored): `service.json` and `latest.md` (current status),
`numbers.csv`, `validation.csv`, `eu_vs_raba.csv`, figures, and a Workflow Run Crate whose version is the
latest snapshot date.

## Scheduled update

`.github/workflows/service-update.yml` is the monthly job. It runs only the **EU-data** layers and
uploads them as a workflow artefact; the Land Use database step is present but disabled (see the
comment in the workflow) until MKGP gives permission. It commits nothing and publishes nothing.
