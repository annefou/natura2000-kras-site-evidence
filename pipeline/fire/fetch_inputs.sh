#!/usr/bin/env bash
# Open inputs for the 2022 Kras fire test (pipeline/fire/). Run from the repository root.
#   Copernicus EMS EMSR604 burnt area (© European Union, Copernicus EMS terms)
#   EFFIS burnt area polygon 206388 (CC BY 4.0), sensitivity check
#   Copernicus DEM GLO-30 tiles N45 E013/E014 (confounder check)
# Outputs go to results/local/fire/input/ (gitignored), next to the RABA-derived results.
set -euo pipefail
IN=results/local/fire/input
mkdir -p "$IN"/{EMSR604,effis,dem}
EMS=https://cems-mapping-website.s3.eu-west-1.amazonaws.com/static/activations/EMSR604
for p in GRA_MONIT01_r1_RTP01_v2 DEL_MONIT01_r1_RTP01_v2 GRA_PRODUCT_r1_RTP01_v1 DEL_PRODUCT_r1_RTP01_v1; do
  curl -fsS -o "$IN/EMSR604/EMSR604_AOI01_${p}_vector.zip" "$EMS/EMSR604_AOI01_${p}_vector.zip"
  unzip -qo "$IN/EMSR604/EMSR604_AOI01_${p}_vector.zip" -d "$IN/EMSR604/EMSR604_AOI01_${p}"
done
curl -fsS -o "$IN/effis/effis_bbox.geojson" \
  "https://maps.effis.emergency.copernicus.eu/effis?service=WFS&version=1.1.0&request=GetFeature&typename=ms:modis.ba.poly&bbox=45.70,13.40,45.95,13.85,EPSG:4326&outputformat=geojson"
for e in 013 014; do
  t=Copernicus_DSM_COG_10_N45_00_E${e}_00_DEM
  curl -fsS -o "$IN/dem/$t.tif" "https://copernicus-dem-30m.s3.amazonaws.com/$t/$t.tif"
done
echo "inputs in $IN"
