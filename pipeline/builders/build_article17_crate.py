#!/usr/bin/env python3
# Vendored from annefou/bmd-sap-prototype (MIT, per its package.json), scripts/fixtures/build_article17_crate.py
# at commit 4f7404ae3b8025066e4c070a53d67762c2ea65b5: the BMD Single Access Point prototype
# (A. Fouilloux, FAIR2Adapt-funded), whose data builders are reused here.
# Changes for this study: crates are written to data/crates/ (via common.py); usage line. See pipeline/builders/README.md.
"""Build the conservation-status baseline crate: Article 17 reporting for the site's habitats.

    python pipeline/builders/build_article17_crate.py --site SI3000276

  art17-status.csv      overall status, trend, the four parameters, area and condition, per
                        habitat, region and reporting period, with the reported reason for any change
  art17-pressures.csv   pressures (and, for 2013-2018, threats) with their ranking

Article 17 status is reported per member state and biogeographical region, NOT per site. This
crate carries the member state's assessment, in every region the site's Standard Data Form
lists, for the habitats of that Standard Data Form. Nothing about the site is assumed: country,
regions and habitats are read from the EEA (natura_site.py).

Sources, both downloaded afresh:
  2013-2018  EEA tabular dataset (Article17_2020, edition 1.0, 2020-08-27), CC BY 4.0
  2019-2024  the member state's delivery to Reportnet 3 (dataflow 1525), found in the dataflow's
             public listing. While the EU dataflow is marked draft, values may still change.
"""
from __future__ import annotations

import argparse
import csv
import io
import shutil
import zipfile
from datetime import datetime, timezone
from urllib.parse import quote

import httpx

import natura_site
from common import COMPILATION_LICENCE, CRATES, THIS_RO, add_file, crate_skeleton, write_crate
from sources import CC_BY_4, ART17_2018, ART17_2018_DATA, ART17_2024_DATAFLOW, REPORTNET

STATUS_COLS = ["habitat_code", "region", "period", "overall", "overall_trend", "previous_overall",
               "reason_status_change", "range", "area", "structure_functions", "future_prospects",
               "area_km2", "area_km2_min", "area_km2_max", "area_trend", "area_trend_period", "reason_area_change",
               "condition_good_km2", "condition_notgood_km2", "condition_unknown_km2"]
PRESSURE_COLS = ["habitat_code", "region", "period", "pressure_code", "type", "ranking", "invasive_species_named"]


def get_csv(url: str) -> list[dict]:
    resp = httpx.get(url, timeout=300, follow_redirects=True)
    resp.raise_for_status()
    return list(csv.DictReader(io.StringIO(resp.content.decode("utf-8-sig"))))


def period_2013_2018(country: str, regions: set[str], habitats: set[str]) -> tuple[list[list], list[list]]:
    rows = [r for r in get_csv(ART17_2018_DATA.format("Article17_2020_data_habitats_regions.csv"))
            if r["country"] == country and r["region"] in regions and r["habitatcode"] in habitats]
    # One row per habitat, region and reported field (habitatstatus, habitatarea, ...), Yes/No per reason.
    change = {(r["featurecode"], r["region"], r["report_field"]): r
              for r in get_csv(ART17_2018_DATA.format("Article17_2020_data_change.csv"))
              if r["featuretype"] == "habitats" and r["country"] == country and r["region"] in regions}

    def reasons(code: str, region: str, field: str) -> str:
        c = change.get((code, region, field), {})
        return ";".join(k for k in ("genuine", "knowledge", "method", "no_info") if c.get(k) == "Yes") or \
            ("noChange" if c.get("no_change") == "Yes" else "")

    status = [[r["habitatcode"], r["region"], "2013-2018", r["conclusion_assessment"], r["conclusion_assessment_trend"],
               r["conclusion_assessment_prev"], reasons(r["habitatcode"], r["region"], "habitatstatus"),
               r["conclusion_range"], r["conclusion_area"], r["conclusion_structure"], r["conclusion_future"],
               r["coverage_surface_area"], r["coverage_surface_area_min"], r["coverage_surface_area_max"],
               r["coverage_trend"], r["coverage_trend_period"], reasons(r["habitatcode"], r["region"], "habitatarea"),
               r["hab_condition_good"], r["hab_condition_notgood"], r["hab_condition_unknown"]]
              for r in sorted(rows, key=lambda r: (r["habitatcode"], r["region"]))]
    pressures = [[r["featurecode"], r["region"], "2013-2018", r["pressurecode"],
                  {"p": "pressure", "t": "threat"}.get(r["type"], r["type"]), r["ranking"], ""]
                 for r in get_csv(ART17_2018_DATA.format("Article17_2020_data_pressures_threats.csv"))
                 if r["country"] == country and r["region"] in regions and r["featurecode"] in habitats]
    return status, pressures


def delivery_2019_2024(country: str) -> dict:
    """The member state's public habitats file in the Reportnet 3 dataflow, found by its file name."""
    flow = httpx.get(f"{REPORTNET}/dataflow/getPublicDataflow/{ART17_2024_DATAFLOW}", timeout=60).json()
    for ds in flow["reportingDatasets"]:
        if ds["nameDatasetSchema"] == "Reporting data - Habitats" and (ds.get("publicFileName") or "").startswith(f"{country}-"):
            return {"flow": flow, "dataset": ds,
                    "url": (f"{REPORTNET}/dataset/exportPublicFile/dataflow/{ART17_2024_DATAFLOW}/dataProvider/"
                            f"{ds['dataProviderId']}?fileName={quote(ds['publicFileName'])}")}
    raise SystemExit(f"no public 2019-2024 habitats delivery for {country} in Reportnet dataflow {ART17_2024_DATAFLOW}")


def period_2019_2024(delivery: dict, regions: set[str], habitats: set[str]) -> tuple[list[list], list[list]]:
    resp = httpx.get(delivery["url"], timeout=300, follow_redirects=True)
    resp.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(resp.content))

    def table(name: str) -> list[dict]:
        member = next(n for n in z.namelist() if n.endswith(f"{name}.csv"))
        return [r for r in csv.DictReader(io.StringIO(z.read(member).decode("utf-8-sig")))
                if r["region_code"] in regions and r["habitat_code"] in habitats]

    key = lambda r: (r["habitat_code"], r["region_code"])  # noqa: E731
    area = {key(r): r for r in table("Regions_Area")}
    sf = {key(r): r for r in table("Regions_StructureAndFunctions")}
    status = []
    for c in sorted(table("Regions_Conclusions"), key=key):
        a, s = area.get(key(c), {}), sf.get(key(c), {})
        status.append([c["habitat_code"], c["region_code"], "2019-2024", c["H_10_5_conclusion_overall_assessment"],
                       c["H_10_6_conclusion_overall_trend"], "", c["H_10_7_a_conclusions_overall_assesment_change"],
                       c["H_10_1_conclusion_range"], c["H_10_2_conclusion_area"],
                       c["H_10_3_conclusion_structure_and_function"], c["H_10_4_conclusion_future_prospects"],
                       a.get("H_5_2_c_surface_area_best_single_value", ""), a.get("H_5_2_a_surface_area_min", ""),
                       a.get("H_5_2_b_surface_area_max", ""), a.get("H_5_7_short_term_trend_direction", ""),
                       a.get("H_5_6_short_term_trend_period", ""), a.get("H_5_5_a_reasons_for_change", ""),
                       s.get("H_6_1_a_condition_good_max", ""), s.get("H_6_1_b_condition_notgood_max", ""),
                       s.get("H_6_1_c_condition_unknown_max", "")])
    pressures = [[r["habitat_code"], r["region_code"], "2019-2024", r["H_7_1_a_pressure_code"], "pressure",
                  r["H_7_1_d_influence"], r["H_7_1_f_IAS_other"] or r["H_7_1_e_IAS_union_concern"]]
                 for r in table("Pressures_List")]
    return status, pressures


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--site", required=True, help="Natura 2000 site code")
    info = natura_site.load(ap.parse_args().site)

    folder = CRATES / f"article17-{info.code}"
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)

    regions = {code for code, _ in info.regions}
    habitats = {code for code, _ in info.habitats}
    s18, p18 = period_2013_2018(info.country, regions, habitats)
    delivery = delivery_2019_2024(info.country)
    s24, p24 = period_2019_2024(delivery, regions, habitats)

    # Absent rows are normal (a habitat need not occur in every region of a site); report, never fill.
    reported = {(r[0], r[1], r[2]) for r in s18 + s24}
    for period in ("2013-2018", "2019-2024"):
        absent = sorted(f"{h}/{g}" for h in habitats for g in regions if (h, g, period) not in reported)
        if absent:
            print(f"[article17] {period}: no {info.country} row for {', '.join(absent)}")

    with (folder / "art17-status.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(STATUS_COLS)
        w.writerows(s18 + s24)
    with (folder / "art17-pressures.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(PRESSURE_COLS)
        w.writerows(p18 + p24)

    ds = delivery["dataset"]
    art17_2024 = {
        "@id": f"{REPORTNET}/dataflow/getPublicDataflow/{ART17_2024_DATAFLOW}",
        "@type": "Dataset",
        "name": f"{delivery['flow']['name']}, {ds['dataSetName']}'s delivery (Reportnet 3)",
        "publisher": f"{ds['dataSetName']}, via Reportnet 3",
        "temporalCoverage": "2019/2024",
        "datePublished": (datetime.fromtimestamp(ds["dateReleased"] / 1000, tz=timezone.utc).date().isoformat()
                          if ds.get("dateReleased") else None),
        "creativeWorkStatus": f"Delivery {ds['status']}; EU dataflow {delivery['flow']['status']}",
    }
    region_names = ", ".join(name for _, name in info.regions)
    scope = (f"{ds['dataSetName']}, {region_names} biogeographical region(s) -- national/regional level, not site "
             f"level. Regions from the site's Standard Data Form (release {info.sdf_release}).")
    name = f"Conservation status of the habitats of {info.name} ({info.code}), Article 17, {info.country}"
    crate = crate_skeleton(
        name,
        (f"Article 17 conservation status (overall, trend, range, area, structure and functions, future "
         f"prospects), area, condition and pressures for the {len(habitats)} habitat types of the site's Standard "
         f"Data Form, for 2013-2018 and 2019-2024. {scope} Reported reasons for a change in status "
         "(genuine, knowledge, method) are kept: a change for knowledge or method is not a change on the ground. "
         f"2019-2024: {art17_2024['creativeWorkStatus']}."),
        license_id=CC_BY_4,
        based_on=[ART17_2018, art17_2024, {"@id": info.sdf_url, "@type": "Dataset",
                                           "name": f"Standard Data Form {info.code}, release {info.sdf_release}"}],
    )
    root = crate["@graph"][1]
    root["usageInfo"] = COMPILATION_LICENCE
    root.update({"keywords": ["Article 17", "conservation status", "Habitats Directive", info.code, *sorted(habitats)],
                 "spatialCoverage": f"{info.country} {region_names}", "temporalCoverage": "2013/2024",
                 "about": {"@id": info.code}})
    add_file(crate, folder / "art17-status.csv", name="Conservation status per habitat, region and period",
             description=f"{len(s18) + len(s24)} rows. {scope} Areas in km2.",
             encoding_format="text/csv", source=ART17_2018["@id"])
    add_file(crate, folder / "art17-pressures.csv", name="Pressures and threats per habitat, region and period",
             description=f"{len(p18) + len(p24)} rows, with ranking (H/M/L).",
             encoding_format="text/csv", source=ART17_2018["@id"])

    annotations = f"""@prefix schema: <https://schema.org/> .

<{THIS_RO}> schema:about "{info.code}" ;
    schema:spatialCoverage "{info.country} {region_names}" ;
    schema:temporalCoverage "2013/2024" ;
    schema:isBasedOn <{ART17_2018['@id']}> , <{art17_2024['@id']}> .
"""
    deposit = {
        "title": name, "description": root["description"],
        "ros_type": "Data-centric Research Object",
        "research_areas": ["Ecology", "Environmental research"],
        "license": "cc-by-4.0",
        "licence_note": COMPILATION_LICENCE,
        "keywords": root["keywords"],
        "files": [{"path": "ro-crate-metadata.json", "res_type": "File", "title": "ro-crate-metadata.json",
                   "description": "RO-Crate 1.2 metadata."},
                  {"path": "art17-status.csv", "res_type": "Dataset", "title": "Conservation status per habitat and period",
                   "description": scope},
                  {"path": "art17-pressures.csv", "res_type": "Dataset", "title": "Pressures and threats",
                   "description": "Per habitat, region and period, with ranking."}],
        "links": [{"url": ART17_2018["@id"], "res_type": "Dataset", "title": ART17_2018["name"],
                   "description": "EEA, edition 1.0, 2020-08-27, CC BY 4.0."},
                  {"url": art17_2024["@id"], "res_type": "Dataset", "title": art17_2024["name"],
                   "description": art17_2024["creativeWorkStatus"] + ". No licence stated."}],
    }
    write_crate(folder, crate, annotations, deposit)

    print(f"[article17] {name}   regions {sorted(regions)}")
    for r in s18 + s24:
        print(f"[article17]   {r[0]} {r[1]:<4} {r[2]}: {r[3]:<2} {r[4]:<3} (prev {r[5] or '-':<2}) "
              f"reason {r[6] or '-':<16} area {r[11] or '?'} km2 {r[14]} {r[15]}")
    print(f"[article17]   pressures: {len(p18)} (2013-2018), {len(p24)} (2019-2024)")
    print(f"[article17] {folder.relative_to(CRATES.parents[1])}/")


if __name__ == "__main__":
    main()
