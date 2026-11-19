"""MODIS EVI (crop greenness) by district and season window, from Google Earth Engine.

Run in Google Colab: paste this whole file into one cell and run it.
Before running: replace PROJECT below with your own Google Cloud project ID
(the one you choose when you register for Earth Engine, non-commercial use).

Output: evi_modis_by_district_2005_2024.csv (one row per district per season start year).

How it works
  * Satellite: MODIS Terra MOD13Q1, 250 m, 16-day composites, QA-filtered (cloudy pixels removed).
  * Mask: MODIS land cover (MCD12Q1, 500 m, year 2020). Classes 12 (cropland) and 14 (cropland mixed with
    natural vegetation) are kept. The same mask is used for every year (land use is assumed stable).
    It is a cropland mask, not a paddy-only mask, so in districts with little paddy (Tiruchirappalli,
    Ariyalur, Perambalur) the greenness is less specific to rice.
  * Districts: first boundary file in which all six districts are found with a plausible area
    (FAO GAUL 2025, then GAUL 2015, then geoBoundaries). Mayiladuthurai is merged into Nagapattinam.
  * Season start year Y means the Samba/Thaladi/Pishanam season of Fasli year Y to Y+1.
Windows (Mode B can use only windows that end by 30 November):
  SepNov  1 Sep to 30 Nov   (known by the December forecast)
  OctNov  1 Oct to 30 Nov   (known by the December forecast)
  SepJan  1 Sep to 31 Jan   (post-season model)
  DecJan  1 Dec to 31 Jan   (grain filling, post-season model)
For each window: EVImax = mean over crop pixels of each pixel's peak EVI, EVImean = mean EVI,
Nvalid = average number of clear composites per pixel (a quality indicator).
"""
import time

import ee
import pandas as pd

PROJECT = "YOUR-PROJECT-ID"      # <-- your Google Cloud project ID
START_YEAR, END_YEAR = 2005, 2024
CROP_FRACTION_MIN = 0.5

try:
    ee.Initialize(project=PROJECT)          # reuse the sign-in from earlier in this Colab session
except Exception:
    ee.Authenticate()                       # opens a link: sign in, copy the code back here
    ee.Initialize(project=PROJECT)

# ------------------------------------------------------------ districts
# We need six districts. Boundary files differ in age (an old file may not have Thiruvarur,
# which became a district in 1997, and a new one may list Mayiladuthurai separately).
# The script tries several boundary files, keeps the first one in which all six districts are
# found with a plausible area, and merges Mayiladuthurai into Nagapattinam when it is separate.
WANT = {
    "Thanjavur": ["thanjavur", "tanjore", "tanjavur"],
    "Thiruvarur": ["thiruvarur", "tiruvarur"],
    "Nagapattinam (incl. Mayiladuthurai)": ["nagapattinam", "nagappattinam", "nagapatnam"],
    "Tiruchirappalli": ["tiruchirappalli", "tiruchirapalli", "tiruchchirappalli", "trichy", "tiruchi"],
    "Ariyalur": ["ariyalur"],
    "Perambalur": ["perambalur"],
}
MAYILADUTHURAI_KEYS = ["mayiladuthurai", "mayiladuturai", "mayiladuthurai", "myladuthurai"]
# plausible district areas in square km (wide ranges, only to catch merged or wrong polygons)
AREA_RANGE = {
    "Thanjavur": (2500, 4800), "Thiruvarur": (1500, 3000),
    "Nagapattinam (incl. Mayiladuthurai)": (2000, 3600), "Tiruchirappalli": (3300, 5600),
    "Ariyalur": (1400, 2600), "Perambalur": (1200, 2400),
}
SOURCES = [("FAO/GAUL/2025/level2", "gaul"), ("FAO/GAUL/2015/level2", "gaul"),
           ("WM/geoLab/geoBoundaries/600/ADM2", "geob")]


def squash(text):
    return str(text).lower().replace(" ", "").replace("-", "")


def match_names(names):
    """Return {label: [matching names]} for the six districts."""
    return {label: [n for n in names if any(k in squash(n) for k in keys)] for label, keys in WANT.items()}


def load_source(asset, kind):
    fc = ee.FeatureCollection(asset)
    props = fc.first().propertyNames().getInfo()
    low = {p.lower(): p for p in props}
    if kind == "gaul":
        name_key = low.get("adm2_name") or low.get("gaul2_name")
        state_key = low.get("adm1_name") or low.get("gaul1_name")
        if not (name_key and state_key):
            raise ValueError(f"unexpected property names: {props}")
        fc = fc.filter(ee.Filter.stringContains(state_key, "Tamil"))
    else:
        name_key, group_key = low.get("shapename"), low.get("shapegroup")
        if not (name_key and group_key):
            raise ValueError(f"unexpected property names: {props}")
        fc = fc.filter(ee.Filter.eq(group_key, "IND"))
    return fc, name_key


districts = None
for asset, kind in SOURCES:
    try:
        fc, name_key = load_source(asset, kind)
        names = fc.aggregate_array(name_key).getInfo()
    except Exception as exc:
        print(f"[{asset}] could not be used: {exc}")
        continue
    found = match_names(names)
    print(f"[{asset}] districts found: {sorted(names)}")
    missing = [label for label, hits in found.items() if len(hits) != 1]
    if missing:
        print(f"[{asset}] skipped, not found exactly once: {missing}")
        continue
    geoms, ok = {}, True
    for label, hits in found.items():
        geom = fc.filter(ee.Filter.eq(name_key, hits[0])).geometry()
        if label.startswith("Nagapattinam"):
            extra = [n for n in names if any(k in squash(n) for k in MAYILADUTHURAI_KEYS)]
            for n in extra:
                geom = geom.union(fc.filter(ee.Filter.eq(name_key, n)).geometry(), 100)
            if extra:
                print(f"[{asset}] merged {extra} into Nagapattinam")
        area = geom.area(100).divide(1e6).getInfo()
        lo, hi = AREA_RANGE[label]
        print(f"[{asset}] {label}: {area:,.0f} sq km (expected {lo:,} to {hi:,})")
        if not lo <= area <= hi:
            ok = False
        geoms[label] = geom
    if not ok:
        print(f"[{asset}] skipped, at least one area is not plausible")
        continue
    districts = ee.FeatureCollection([ee.Feature(g, {"District": label}) for label, g in geoms.items()])
    print("Using boundary file:", asset)
    break

if districts is None:
    raise SystemExit("No boundary file gave all six districts. Copy ALL the text printed above and send it to Claude.")

# ------------------------------------------------------- satellite data
modis = ee.ImageCollection("MODIS/061/MOD13Q1")
modis_proj = modis.first().select("EVI").projection()


def prep(img):
    evi = img.select("EVI").multiply(0.0001)
    good = img.select("SummaryQA").lte(1)        # 0 good, 1 marginal; 2 snow/ice and 3 cloudy are dropped
    return evi.updateMask(good).rename("EVI").set("system:time_start", img.get("system:time_start"))


# Crop mask from MODIS land cover (native MODIS grid, so no heavy resampling is needed)
landcover = (ee.ImageCollection("MODIS/061/MCD12Q1")
             .filter(ee.Filter.calendarRange(2020, 2020, "year")).first().select("LC_Type1"))
cropmask = landcover.eq(12).Or(landcover.eq(14)).rename("cropmask")
region = districts.geometry().bounds()          # limits every calculation to the six districts

# (start year offset, start month, end year offset, end month)
WINDOWS = {"SepNov": (0, 9, 0, 11), "OctNov": (0, 10, 0, 11), "SepJan": (0, 9, 1, 1), "DecJan": (0, 12, 1, 1)}

# number of 500 m cropland pixels per district (shows how much land the mask keeps)
crop_pixels = {}
try:
    counts = (cropmask.clip(region)
              .reduceRegions(collection=districts, reducer=ee.Reducer.sum(), scale=500, tileScale=4)
              .getInfo()["features"])
    crop_pixels = {f["properties"]["District"]: f["properties"].get("sum") for f in counts}
    print("Cropland pixels (500 m) kept per district:", crop_pixels)
except Exception as exc:
    print("Crop pixel count skipped:", exc)

rows = []
for year in range(START_YEAR, END_YEAR + 1):
    bands = []
    for wname, (so, sm, eo, em) in WINDOWS.items():
        start = ee.Date.fromYMD(year + so, sm, 1)
        end = ee.Date.fromYMD(year + eo, em, 1).advance(1, "month")
        col = modis.filterDate(start, end).map(prep)
        bands += [col.max().rename(f"EVImax_{wname}"),
                  col.mean().rename(f"EVImean_{wname}"),
                  col.count().rename(f"Nvalid_{wname}")]
    image = ee.Image.cat(bands).updateMask(cropmask).clip(region)
    stats = image.reduceRegions(collection=districts, reducer=ee.Reducer.mean(), scale=250, tileScale=4)
    for attempt in range(3):
        try:
            feats = stats.getInfo()["features"]
            break
        except Exception as exc:                  # temporary Earth Engine error: wait and retry
            print("retrying", year, exc)
            time.sleep(10)
    else:
        raise SystemExit(f"Failed for {year}")
    for f in feats:
        p = f["properties"]
        row = {"District": p["District"], "Fasli_year": f"{year}-{str(year + 1)[2:]}",
               "CropPixels500m": crop_pixels.get(p["District"])}
        row.update({k: v for k, v in p.items() if k.startswith(("EVI", "Nvalid"))})
        rows.append(row)
    print("done", year)

out = pd.DataFrame(rows).sort_values(["District", "Fasli_year"])
out.to_csv("evi_modis_by_district_2005_2024.csv", index=False)
print(out.shape)
print(out.head(8).round(3).to_string())

try:
    from google.colab import files
    files.download("evi_modis_by_district_2005_2024.csv")
except ImportError:
    pass
