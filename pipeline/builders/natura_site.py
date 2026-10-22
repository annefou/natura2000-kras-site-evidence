# Vendored from annefou/bmd-sap-prototype (MIT, per its package.json), scripts/fixtures/natura_site.py
# at commit 4f7404ae3b8025066e4c070a53d67762c2ea65b5: the BMD Single Access Point prototype
# (A. Fouilloux, FAIR2Adapt-funded), whose data builders are reused here.
# Changes for this study: load() retries when the EEA service answers with no features. See pipeline/builders/README.md.
"""Everything a builder needs to know about a site, read from the EEA for any site code."""
from __future__ import annotations

import csv
import io
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import cache

import httpx
from shapely.geometry import shape
from shapely.ops import unary_union

from sources import ART17_2018_CODES, EEA_SITES, SDF_API


@dataclass
class Site:
    code: str
    name: str
    country: str                  # member-state code as used by the EEA, e.g. "SE"
    site_type: str                # A / B / C
    area_ha: float
    released: str                 # date of the Natura 2000 release the site comes from
    sdf_release: int
    sdf_url: str                  # Standard Data Form, as JSON, for that release
    regions: list[tuple[str, str]] = field(default_factory=list)   # [(code, name)], e.g. [("CON", "Continental")]
    habitats: list[tuple[str, str]] = field(default_factory=list)  # [(code, name)] from the SDF

    def polygon(self, srid: str = "4326"):
        resp = httpx.get(f"{EEA_SITES}/2/query", timeout=60, params={
            "where": f"SITECODE='{self.code}'", "returnGeometry": "true", "outSR": srid, "f": "geojson"})
        resp.raise_for_status()
        return unary_union([shape(f["geometry"]) for f in resp.json()["features"]])


@cache
def region_codes() -> dict[str, str]:
    """Biogeographical region name -> code, from the Article 17 reference code list."""
    text = httpx.get(ART17_2018_CODES.format("Article17_2020_ref_bioGeoReg.csv"), timeout=60).content.decode("utf-8-sig")
    return {r["label"]: r["code"] for r in csv.DictReader(io.StringIO(text))}


@cache
def load(code: str) -> Site:
    code = code.strip().upper()
    for attempt in range(4):  # the EEA service occasionally answers with no features; retry before giving up
        resp = httpx.get(f"{EEA_SITES}/2/query", timeout=60, params={
            "where": f"SITECODE='{code}'", "outFields": "SITENAME,MS,SITETYPE,Area_ha,RELEASE_DATE",
            "returnGeometry": "false", "f": "json"})
        resp.raise_for_status()
        features = resp.json().get("features")
        if features:
            break
        time.sleep(5 * (attempt + 1))
    if not features:
        raise SystemExit(f"{code} is not in the EEA Natura 2000 release")
    a = features[0]["attributes"]

    release = httpx.get(f"{SDF_API}/GetLastReleaseId", params={"SiteCode": code}, timeout=60).json()["Data"]
    sdf_url = f"{SDF_API}/GetReleaseDataLegacy?sdfPublic=true&siteCode={code}&releaseId={release}"
    sdf = httpx.get(sdf_url, timeout=60).json()["Data"]
    names = region_codes()
    regions = []
    for r in sdf["SiteLocation"]["BiogeographicalRegions"]:
        if r["Name"] not in names:
            raise SystemExit(f"{code}: region {r['Name']!r} is not in the Article 17 code list")
        regions.append((names[r["Name"]], r["Name"]))

    return Site(
        code=code, name=a["SITENAME"], country=a["MS"], site_type=a["SITETYPE"], area_ha=a["Area_ha"],
        released=datetime.fromtimestamp(a["RELEASE_DATE"] / 1000, tz=timezone.utc).date().isoformat(),
        sdf_release=release, sdf_url=sdf_url, regions=regions,
        habitats=sorted((h["Code"], h["HabitatName"]) for h in sdf["EcologicalInformation"]["HabitatTypes"]),
    )
