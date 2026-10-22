#!/usr/bin/env python3
# Vendored from annefou/bmd-sap-prototype (MIT, per its package.json), scripts/fixtures/build_site_crate.py
# at commit 4f7404ae3b8025066e4c070a53d67762c2ea65b5: the BMD Single Access Point prototype
# (A. Fouilloux, FAIR2Adapt-funded), whose data builders are reused here.
# Changes for this study: the ViewAction points at this study's pages (config/study.toml), not the BMD prototype; usage line. See pipeline/builders/README.md.
"""Build the site crate: the entry point for the site's evidence.

    python pipeline/builders/build_site_crate.py --site SI3000276

Everything comes from the EEA Natura 2000 end-2024 release, queried live:

  boundary.geojson     site polygon, EPSG:4326
  sdf-habitats.csv     Standard Data Form habitat rows (Annex I types, cover, A/B/C grades)
  sdf-species.csv      Standard Data Form species rows (one row per population type)

The crate links every input crate already listed in config/pids.json (hasPart), and carries
a ViewAction pointing at this study's pages, as FDO2map does. Deposit it last, after the inputs.
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path

import httpx

import natura_site
from common import CRATES, VIEW_URL, THIS_RO, TODAY, add_file, arcgis_query, crate_skeleton, load_pids, write_crate
from sources import CC_BY_4, EEA_SITES, EEA_SPECIES, NATURA2000

EEA_DATASET, EEA_DATASET_NAME = NATURA2000["@id"], NATURA2000["name"]

HABITAT_FIELDS = {
    "HABITATCODE": "habitat_code",
    "DESCRIPTION": "habitat_name",
    "HABITAT_PRIORITY": "priority",
    "COVER_HA": "cover_ha",
    "CAVES": "caves",
    "DATAQUALITY": "data_quality",
    "REPRESENTATIVITY": "representativity",
    "RELSURFACE": "relative_surface",
    "CONSERVATION": "conservation",
    "GLOBALASSESMENT": "global_assessment",
    "NON_PRESENCE_IN_SITE": "non_presence_in_site",
}

SPECIES_FIELDS = {
    "SpeciesNameClean": "species_name",
    "CONTAINSSPECIES_SPTYPE": "group",
    "POPULATION_TYPE": "population_type",
    "LOWERBOUND": "size_min",
    "UPPERBOUND": "size_max",
    "COUNTINGUNIT": "unit",
    "CONTAINSSPECIES_ABUNDANCECATEGORY": "abundance_category",
    "CONTAINSSPECIES_DATAQUALITY": "data_quality",
    "CONTAINSSPECIES_POPULATION": "population",
    "CONTAINSSPECIES_CONSERVATION": "conservation",
    "CONTAINSSPECIES_ISOLATIONFACTOR": "isolation",
    "CONTAINSSPECIES_GLOBALIMPORTANCE": "global_assessment",
    "CONTAINSSPECIES_SENSITIVE": "sensitive",
    "CONTAINSSPECIES_NONPRESENCEINSITE": "non_presence_in_site",
}


def write_csv(path: Path, rows: list[dict], fields: dict[str, str]) -> None:
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(fields.values()))
        w.writeheader()
        for row in rows:
            w.writerow({out: row.get(src) for src, out in fields.items()})


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--site", required=True, help="Natura 2000 site code, e.g. SI3000276")
    args = ap.parse_args()
    info = natura_site.load(args.site)
    code = info.code

    folder = CRATES / f"site-{code}"
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)

    # --- boundary ----------------------------------------------------------------------
    where = f"SITECODE='{code}'"
    resp = httpx.get(f"{EEA_SITES}/2/query", timeout=60, params={
        "where": where, "outFields": "SITECODE,SITENAME,MS,SITETYPE,Area_ha,RELEASE_DATE",
        "returnGeometry": "true", "outSR": "4326", "geometryPrecision": "6", "f": "geojson"})
    resp.raise_for_status()
    boundary_url = str(resp.url)
    (folder / "boundary.geojson").write_text(json.dumps(resp.json()) + "\n")
    released = info.released

    # --- Standard Data Form rows ------------------------------------------------------
    habitats, habitats_url = arcgis_query(f"{EEA_SITES}/3", where=where, outFields="*",
                                          orderByFields="HABITATCODE")
    habitat_rows = [f["attributes"] for f in habitats["features"]]
    write_csv(folder / "sdf-habitats.csv", habitat_rows, HABITAT_FIELDS)

    species, species_url = arcgis_query(f"{EEA_SPECIES}/0", where=f"SiteCode='{code}'", outFields="*",
                                        returnGeometry="false", orderByFields="SpeciesNameClean")
    species_rows = [f["attributes"] for f in species["features"]]
    write_csv(folder / "sdf-species.csv", species_rows, SPECIES_FIELDS)

    # --- crate --------------------------------------------------------------------------
    source = {**NATURA2000, "datePublished": released}
    name = f"{info.name} ({code}), Natura 2000 site"
    crate = crate_skeleton(
        name,
        (f"Site identity, boundary and Standard Data Form for the Natura 2000 site {info.name} "
         f"({code}, {info.country}), as reported by the member state in the EEA end-2024 release "
         f"(released {released}), retrieved {TODAY}. Entry point for the site's evidence: links every "
         "input used to describe the site's habitats and species."),
        license_id=CC_BY_4,
        based_on=[source],
    )
    root = crate["@graph"][1]
    root.update({"identifier": code, "keywords": ["Natura 2000", code, info.name],
                 "spatialCoverage": ", ".join(name for _, name in info.regions)})
    add_file(crate, folder / "boundary.geojson", name="Site boundary",
             description=f"Boundary of {code}, {info.area_ha:.1f} ha, EPSG:4326.",
             encoding_format="application/geo+json", source=EEA_DATASET, query_url=boundary_url)
    add_file(crate, folder / "sdf-habitats.csv", name="Qualifying habitats (Standard Data Form)",
             description=f"{len(habitat_rows)} Annex I habitat types with cover and A/B/C assessment grades.",
             encoding_format="text/csv", source=EEA_DATASET, query_url=habitats_url)
    add_file(crate, folder / "sdf-species.csv", name="Qualifying species (Standard Data Form)",
             description=(f"{len(species_rows)} rows, one per species and population type, "
                          "with population size and A/B/C assessment grades."),
             encoding_format="text/csv", source=EEA_DATASET, query_url=species_url)

    inputs = {k: v for k, v in load_pids().items() if not k.startswith("site-")}
    for pid in inputs.values():
        root["hasPart"].append({"@id": pid})

    # --- triples ROHub cannot infer ---------------------------------------------------
    links = "".join(f"<{THIS_RO}> schema:hasPart <{pid}> .\n" for pid in inputs.values())
    annotations = f"""@prefix schema: <https://schema.org/> .

<{THIS_RO}> schema:identifier "{code}" ;
    schema:name "{info.name}" ;
    schema:isBasedOn <{EEA_DATASET}> .
{links}
<{THIS_RO}/action/view-site> a schema:ViewAction ;
    schema:name "Open this site's evidence study" ;
    schema:urlTemplate "{VIEW_URL}#{{identifier}}" ;
    schema:object <{THIS_RO}> .
"""

    deposit = {
        "title": name,
        "description": root["description"],
        "ros_type": "Data-centric Research Object",
        "research_areas": ["Environmental research", "Biology"],
        "license": "cc-by-4.0",
        "keywords": root["keywords"],
        "files": [
            {"path": "ro-crate-metadata.json", "res_type": "File", "title": "ro-crate-metadata.json",
             "description": "RO-Crate 1.2 metadata for this site."},
            {"path": "boundary.geojson", "res_type": "Dataset", "title": "Site boundary",
             "description": "Site polygon from the EEA Natura 2000 end-2024 release, EPSG:4326."},
            {"path": "sdf-habitats.csv", "res_type": "Dataset", "title": "Qualifying habitats",
             "description": "Standard Data Form habitat rows for this site."},
            {"path": "sdf-species.csv", "res_type": "Dataset", "title": "Qualifying species",
             "description": "Standard Data Form species rows for this site."},
        ],
        "links": [
            {"url": EEA_DATASET, "res_type": "Dataset", "title": EEA_DATASET_NAME,
             "description": "Source of the boundary and Standard Data Form rows (CC BY 4.0)."},
            {"url": VIEW_URL, "res_type": "Web Service", "title": "Natura 2000 site evidence study (this repository's pages)",
             "description": "Opens this site's evidence study."},
        ],
    }
    write_crate(folder, crate, annotations, deposit)

    print(f"[site] {name}")
    print(f"[site]   released {released}, retrieved {TODAY}, {info.area_ha:.1f} ha, regions {info.regions}")
    print(f"[site]   {len(habitat_rows)} habitat rows, {len(species_rows)} species rows")
    print(f"[site]   linked input crates: {len(inputs) or 'none yet (config/pids.json)'}")
    print(f"[site] {folder.relative_to(CRATES.parents[1])}/")


if __name__ == "__main__":
    main()
