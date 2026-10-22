#!/usr/bin/env python3
"""Draft story page (blog/index.html) from the committed public results, before any chain exists.

    pixi run python pipeline/story_preview.py

The template's `pixi run build-story` renders the story from a PUBLISHED nanopublication chain; none is
published yet. This preview is built the same way in spirit (deterministic, nothing invented): every
value comes from results/summary.json, config/validation/ or the figures, and the page says it is a
draft. Replace it with `pixi run build-story` once the chain is published.
Nothing from the national Land Use database appears on it.
"""
from __future__ import annotations

import base64
import html
import io
import json
import tomllib
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[1]
CFG = tomllib.loads((REPO / "config" / "study.toml").read_text())
REPO_URL = CFG["repository"]["url"]


def img(path: Path, width: int = 1400) -> str:
    im = Image.open(path)
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)))
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def main() -> None:
    s = json.loads((REPO / "results" / "summary.json").read_text())
    sp = s["species"]
    t = {r["land_use"]: r for r in s["paper_targets"]}
    a17 = {r["period"]: r for r in s["article17"]}
    e = html.escape
    rows = "".join(
        f"<tr><td>{e(k)}</td><td>{e(v)}</td></tr>" for k, v in [
            ("Article 17, Slovenia, Continental (national)",
             f"62A0 {a17['2013-2018']['overall']}/{a17['2013-2018']['overall_trend']} (2013–2018), "
             f"{a17['2019-2024']['overall']}/{a17['2019-2024']['overall_trend']} (2019–2024); area "
             f"{a17['2013-2018']['area_km2']} → {a17['2019-2024']['area_km2']} km², attributed to a change of method"),
            ("CORINE change layers 2000–2018, inside the site",
             f"{s['corine_loss_from_grassland_classes_2000_2018_ha']} ha lost from natural grasslands + pastures; "
             f"{s['corine_gain_to_grassland_classes_2000_2018_ha']} ha gained"),
            ("National Land Use database, 2002–2024 (Davidović et al. 2026)",
             f"grasslands {t['Grasslands']['delta_2002_2024_ha']:+,.1f} ha ({t['Grasslands']['delta_2002_2024_pct']:+} %), "
             f"overgrown {t['Overgrown areas']['delta_2002_2024_ha']:+,.1f} ha ({t['Overgrown areas']['delta_2002_2024_pct']:+} %)"),
            ("GBIF records inside the site",
             f"{sp['records_inside_site']} records in {sp['cells_occupied_depth13']} HEALPix cells; "
             f"{len(sp['sdf_taxa_without_records'])} of {sp['sdf_taxa']} Standard Data Form taxa without records"),
        ])
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kras grassland evidence</title>
<style>
:root {{ --navy:#1b2a4e; --magenta:#b5176b; --ink:#1d1d1f; --muted:#55555a; --rule:#e2e2e6; --bg:#fcfcfb; --warn:#fff4e5; --warnline:#e08a00; }}
@media (prefers-color-scheme: dark) {{ :root {{ --navy:#9db4e8; --magenta:#f06aa8; --ink:#ececee; --muted:#b4b4ba; --rule:#3a3a40; --bg:#17171a; --warn:#3a2a10; --warnline:#e0a040; }} }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:17px/1.6 Georgia, 'Times New Roman', serif; }}
main {{ max-width:760px; margin:0 auto; padding:24px 16px 64px; }}
h1 {{ font:700 2rem/1.2 system-ui, sans-serif; color:var(--navy); margin:.4em 0 .2em; }}
h2 {{ font:700 1.2rem/1.3 system-ui, sans-serif; color:var(--navy); margin:2em 0 .5em; }}
.kicker {{ font:600 .8rem system-ui, sans-serif; letter-spacing:.06em; text-transform:uppercase; color:var(--magenta); }}
.draft {{ background:var(--warn); border-left:4px solid var(--warnline); padding:12px 16px; font:15px/1.5 system-ui, sans-serif; }}
table {{ border-collapse:collapse; width:100%; font:14px/1.45 system-ui, sans-serif; }}
td {{ border-top:1px solid var(--rule); padding:8px 6px; vertical-align:top; }} td:first-child {{ color:var(--muted); width:40%; }}
img {{ max-width:100%; height:auto; border:1px solid var(--rule); background:#fcfcfb; }}
.small {{ font:14px/1.5 system-ui, sans-serif; color:var(--muted); }}
a {{ color:var(--magenta); }}
</style></head>
<body><main>
<p class="draft"><strong>Draft study.</strong> The statements below have not yet been reviewed by an ecologist or by the
Slovenian Distributed Centre of LifeWatch (ZRC SAZU). No nanopublication has been published; this page is a preview
built from the repository's public results, not the platform's story of a published chain. Results from the Slovenian
Land Use database (MKGP) are not shown until MKGP gives permission.</p>
<p class="kicker">Natura 2000 · Slovenia · Kras (SI3000276)</p>
<h1>Is grassland declining in Kras? What open EU-wide data can and cannot tell</h1>
<p>{e(s['statement'])}</p>
<img src="{img(REPO / 'figures' / 'main_result.png')}" alt="Grassland change inside Natura 2000 site Kras as reported by CORINE, HRL Grassland, CLC+ Backbone and the national Land Use database">
<h2>The evidence, source by source</h2>
<table>{rows}</table>
<h2>Where the species records are</h2>
<img src="{img(REPO / 'figures' / 'gbif_cells.png', 900)}" alt="GBIF records per HEALPix cell inside the site">
<p class="small">GBIF download <a href="https://doi.org/10.15468/dl.5epzsz">doi:10.15468/dl.5epzsz</a> (CC BY-NC 4.0), on
HEALPix depth 13 cells (WGS84, NESTED), written as a GRID4EARTH DGGS-Zarr store. Records are opportunistic:
{sp['inaturalist_share_inside_site_pct']} % from iNaturalist; all {sp['bat_records']} bat records from one survey in
{', '.join(map(str, sp['bat_record_years']))}.</p>
<h2>What comes next</h2>
<p>The core of this work is a monitoring service built on Slovenia's own Land Use database, which is updated monthly
and does see the change. It runs today, locally; its results will be published here once MKGP agrees. The validation
replicates <a href="https://doi.org/10.3986/AGS.14021">Davidović, Čuš &amp; Ivajnšič (2026)</a>.</p>
<h2>How to comment or correct</h2>
<p>Corrections are credited by name (and ORCID if you give one). Use the
<a href="{REPO_URL}/issues/new?template=scientific-review.yml">scientific review form</a> or the
<a href="{REPO_URL}/issues/new?template=data-correction.yml">data or site correction form</a>.
Expert input is especially wanted on the 62A0 trend statement, the official labels of the Article 17 pressure codes
beyond PA05, whether CORINE natural grasslands + pastures is a fair proxy for 62A0 on Kras, and national datasets that
could replace the 2004 bat records.</p>
<p class="small">Anne Fouilloux (LifeWatch ERIC) · Code: <a href="{REPO_URL}">{e(REPO_URL)}</a> ·
{e(s['review_status'])}</p>
</main></body></html>
"""
    out = REPO / "blog" / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(page)
    print(f"[story] {out.relative_to(REPO)} ({out.stat().st_size / 1e3:.0f} kB)")


if __name__ == "__main__":
    main()
