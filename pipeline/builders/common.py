# Vendored from annefou/bmd-sap-prototype (MIT, per its package.json), scripts/fixtures/common.py
# at commit 4f7404ae3b8025066e4c070a53d67762c2ea65b5: the BMD Single Access Point prototype
# (A. Fouilloux, FAIR2Adapt-funded), whose data builders are reused here.
# Changes for this study: author, funding and URLs come from config/study.toml instead of
# FAIR2Adapt-default constants; crates are written to data/crates/, curated inputs are read from
# config/curated/, the download cache is data/cache/. See pipeline/builders/README.md.
"""Shared helpers for building the input crates of this study.

Each crate is a folder under data/crates/<name>/ holding:

  ro-crate-metadata.json   RO-Crate 1.2, conformsTo the earth-science profile
  <data files>             exactly as retrieved, never edited by hand
  annotations.ttl          triples a repository cannot infer from the files (site code, view link,
                           links to other crates), written against THIS_RO
  deposit.json             the record a later deposit would create (nothing is deposited here)

Nothing here invents data: every value comes from a named source, with its retrieval date.
"""
from __future__ import annotations

import json
import sys
import tomllib
from datetime import date
from pathlib import Path

import httpx

from sources import EEA_SITES  # noqa: F401  (re-exported for builders)

REPO = Path(__file__).resolve().parents[2]
CONFIG = tomllib.loads((REPO / "config" / "study.toml").read_text())
CRATES = REPO / "data" / "crates"
CURATED = REPO / "config" / "curated"
CACHE = REPO / "data" / "cache"
PIDS = REPO / "config" / "pids.json"  # PIDs of deposited input crates; none yet

# Replaced by the real PID if a crate is ever deposited.
THIS_RO = "https://w3id.org/ro-id/THIS-RO"

RO_CRATE = "https://w3id.org/ro/crate/1.2"
EARTH_SCIENCE_PROFILE = "https://w3id.org/ro/terms/earth-science"
VIEW_URL = CONFIG["repository"]["pages_url"]

AUTHORS = CONFIG["authors"]
AUTHOR_ORCID = AUTHORS[0]["orcid"]
AUTHOR_NAME = AUTHORS[0]["name"]

TODAY = date.today().isoformat()


def _funding_entities() -> tuple[list[dict], list[dict]]:
    """Grant and organisation entities from config/study.toml, and the root's references to them."""
    entities, refs = [], []
    for i, f in enumerate(CONFIG.get("funding", [])):
        if f["kind"] == "Organization":
            oid = f.get("url") or f"#funder-{i}"
            entities.append({"@id": oid, "@type": "Organization", "name": f["name"]})
            refs.append({"@id": oid})
            continue
        gid = f"#grant-{f['name'].lower()}"
        grant = {"@id": gid, "@type": "Grant", "name": f["name"]}
        if f.get("identifier"):
            grant["identifier"] = f["identifier"]
        else:
            print(f"[common] WARNING: grant {f['name']} has no identifier in config/study.toml (TODO)", file=sys.stderr)
        if f.get("funder"):
            grant["funder"] = {"@id": f"#funder-{i}"}
            entities.append({"@id": f"#funder-{i}", "@type": "Organization", "name": f["funder"]})
        if f.get("url"):
            grant["url"] = f["url"]
        entities.append(grant)
        refs.append({"@id": gid})
    return entities, refs


FUNDING_ENTITIES, FUNDING_REFS = _funding_entities()

# Where a crate carries values or text whose source states no licence, CC BY 4.0 covers only the
# compilation. Said in the crate, so nobody reads the licence as ours to give.
COMPILATION_LICENCE = ("CC BY 4.0 applies to this compilation. Quoted source text, and values from sources "
                       "that state no licence, remain under their sources' terms.")


def arcgis_query(layer_url: str, **params: str) -> tuple[dict, str]:
    """Run an ArcGIS REST query; return the JSON and the exact URL, for provenance."""
    params = {"f": "json", **params}
    resp = httpx.get(f"{layer_url}/query", params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise SystemExit(f"EEA query failed: {data['error']}")
    return data, str(resp.url)


def load_pids() -> dict[str, str]:
    return json.loads(PIDS.read_text()) if PIDS.exists() else {}


def crate_skeleton(name: str, description: str, *, license_id: str | None, based_on: list[dict]) -> dict:
    """Root of an input crate. Sources go in `isBasedOn`, each with its query and date."""
    root = {
        "@id": "./",
        "@type": "Dataset",
        "name": name,
        "description": description,
        "datePublished": TODAY,
        "author": [{"@id": a["orcid"]} for a in AUTHORS],
        "isBasedOn": [{"@id": s["@id"]} for s in based_on],
        "hasPart": [],
        "funding": [r for r in FUNDING_REFS if r["@id"].startswith("#grant-")],
        "funder": [r for r in FUNDING_REFS if not r["@id"].startswith("#grant-")],
        "creditText": "; ".join(a["name"] for a in CONFIG.get("acknowledgement", [])),
    }
    if license_id:
        root["license"] = {"@id": license_id}
    return {
        "@context": "https://w3id.org/ro/crate/1.2/context",
        "@graph": [
            {
                "@id": "ro-crate-metadata.json",
                "@type": "CreativeWork",
                "conformsTo": [{"@id": RO_CRATE}, {"@id": EARTH_SCIENCE_PROFILE}],
                "about": {"@id": "./"},
            },
            root,
            *[{"@id": a["orcid"], "@type": "Person", "name": a["name"], "affiliation": a.get("affiliation", "")}
              for a in AUTHORS],
            *FUNDING_ENTITIES,
            *based_on,
        ],
    }


def add_file(crate: dict, path: Path, *, name: str, description: str, encoding_format: str,
             source: str, query_url: str | None = None) -> None:
    """Declare a data file with where it came from and when."""
    entry = {
        "@id": path.name,
        "@type": "File",
        "name": name,
        "description": description,
        "encodingFormat": encoding_format,
        "contentSize": str(path.stat().st_size),
        "isBasedOn": {"@id": source},
        "dateCreated": TODAY,
    }
    if query_url:
        entry["url"] = query_url
    crate["@graph"][1]["hasPart"].append({"@id": path.name})
    crate["@graph"].append(entry)


def write_crate(folder: Path, crate: dict, annotations: str, deposit: dict) -> None:
    (folder / "ro-crate-metadata.json").write_text(json.dumps(crate, indent=2, ensure_ascii=False) + "\n")
    (folder / "annotations.ttl").write_text(annotations)
    (folder / "deposit.json").write_text(json.dumps(deposit, indent=2, ensure_ascii=False) + "\n")
