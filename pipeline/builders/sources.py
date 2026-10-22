# Vendored from annefou/bmd-sap-prototype (MIT, per its package.json), scripts/fixtures/sources.py
# at commit 4f7404ae3b8025066e4c070a53d67762c2ea65b5: the BMD Single Access Point prototype
# (A. Fouilloux, FAIR2Adapt-funded), whose data builders are reused here.
# Changes for this study: none. See pipeline/builders/README.md.
"""European datasets the input crates are built from. The same for every site.

Site-specific facts (name, country, regions, habitats) are never written here: they are read
from the EEA for the site asked for (site.py). Site-specific curated evidence lives in
config/curated/<site code>/, as data, not code.
"""
from __future__ import annotations

CC_BY_4 = "https://creativecommons.org/licenses/by/4.0/"

# --- Natura 2000 (EEA) ---------------------------------------------------------------
EEA = "https://bio.discomap.eea.europa.eu/arcgis/rest/services/ProtectedSites"
EEA_SITES = f"{EEA}/Natura2000Sites/MapServer"          # layer 2: every site; layer 3: SDF habitats
EEA_SPECIES = f"{EEA}/Natura2000Species/MapServer"      # layer 0: SDF species
SDF_API = "https://n2kbackbone.eea.europa.eu/n2kbackbone_back/api/PublicData"
NATURA2000 = {
    "@id": "https://www.eea.europa.eu/en/datahub/datahubitem-view/6fc8ad2d-195d-40f4-bdec-576e7d1268e4",
    "@type": "Dataset",
    "name": "Natura 2000 end-2024 release, European Environment Agency",
    "publisher": "European Environment Agency",
    "license": {"@id": CC_BY_4},
    "creditText": "Natura 2000 data - the European network of protected sites, EEA, end-2024 release.",
}

# --- CORINE Land Cover (Copernicus Land Monitoring Service), vector, V2020_20u1 --------
CLC_SERVICE = "https://image.discomap.eea.europa.eu/arcgis/rest/services/Corine"
CLC_VERSION = "V2020_20u1"
CLC_STATUS = {  # year: (map service, class field, vector DOI)
    2000: ("CLC2000_WM", "code_00", "https://doi.org/10.2909/8b85b479-6afb-42c6-817c-11d1a5260b83"),
    2006: ("CLC2006_WM", "Code_06", "https://doi.org/10.2909/93eede6e-c196-40e3-9253-7f2237b49de1"),
    2012: ("CLC2012_WM", "Code_12", "https://doi.org/10.2909/916c0ee7-9711-4996-9876-95ea45ce1d27"),
    2018: ("CLC2018_WM", "Code_18", "https://doi.org/10.2909/71c95a07-e296-44fc-b22b-415f42acfdf0"),
}
CLC_CHANGE = {  # period: (map service, from field, to field, vector DOI)
    "2000-2006": ("CHA2000_2006_WM", "code_00", "code_06", "https://doi.org/10.2909/3899a4a7-dd0b-4729-b24f-278844f1a686"),
    "2006-2012": ("CHA2006_2012_WM", "code_06", "code_12", "https://doi.org/10.2909/fe3425ad-a71e-454c-97a9-586613af8191"),
    "2012-2018": ("CHA2012_2018_WM", "Code_12", "Code_18", "https://doi.org/10.2909/f30f1000-7cf8-43bb-872c-5eb093911b24"),
}
CLC_1990 = ("CLC1990_WM", "code_90")  # checked per site: several countries, Sweden among them, are not covered
CLMS_FAQ = ("https://land.copernicus.eu/en/faq/products/corine-land-cover/should-i-use-corine-land-cover-status-"
            "or-change-products-to-analyze-the-differences-between-2000-and-2018")

# --- Article 17 -----------------------------------------------------------------------
ART17_2018 = {
    "@id": "https://sdi.eea.europa.eu/data/7638812a-2063-40bc-b4cc-1b440e00e60e",
    "@type": "Dataset",
    "name": "Conservation status of habitat types and species: datasets from Article 17, Habitats Directive "
            "92/43/EEC reporting (2013-2018) 2020 Tabular Dataset",
    "publisher": "European Environment Agency",
    "version": "1.0", "datePublished": "2020-08-27", "license": {"@id": CC_BY_4},
    "temporalCoverage": "2013/2018",
}
ART17_2018_SHARE = "https://sdi.eea.europa.eu/datashare/s/YFeeg2obmNtLLZm/download"
ART17_2018_DATA = f"{ART17_2018_SHARE}?path=/Article17_2020_dataset_csv&files={{}}"
ART17_2018_CODES = f"{ART17_2018_SHARE}?path=/Article17_2020_ref_codelists_csv&files={{}}"
REPORTNET = "https://api.reportnet.europa.eu"
ART17_2024_DATAFLOW = 1525  # "Habitats Directive reporting (Art. 17) - 2019-2024"

# --- CLC+ Backbone (Copernicus Land Monitoring Service), raster 10 m -----------------
# Served by the EEA as ImageServers with server-side histograms: works for any site.
CLCPLUS_SERVICE = "https://image.discomap.eea.europa.eu/arcgis/rest/services/CLC_plus"
CLCPLUS = {  # year: (image service, DOI, validation report)
    2018: ("CLMS_CLCplus_RASTER_2018_010m_eu", "https://doi.org/10.2909/cd534ebf-f553-42f0-9ac1-62c1dc36d32c",
           "https://land.copernicus.eu/en/technical-library/validation-report-clcplus-backbone-2018"),
    2021: ("CLMS_CLCplus_RASTER_2021_010m_eu", "https://doi.org/10.2909/71fc9d1b-479f-4da1-aa66-662a2fff2cf7",
           "https://land.copernicus.eu/en/technical-library/validation-report-clcplus-backbone-2021"),
}
# 2023 exists (https://doi.org/10.2909/b0bd43c6-1fa1-4d88-9c45-98b13a95d0b2) but is not served by the EEA yet.
