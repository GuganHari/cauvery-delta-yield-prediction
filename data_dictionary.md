# Data dictionary

All files are in `data/processed/`. "Fasli year" 2014-15 means the Samba/Thaladi/Pishanam season sown
from August to November 2014 and harvested by early 2015. Season start year = 2014.

## main_samba_panel.csv  (66 rows: 6 districts x 11 years, 2014-15 to 2024-25)
Target dataset. Season is the combined Samba/Thaladi/Pishanam season (Thaladi alone is not reported).

| Column | Meaning |
|---|---|
| District | Thanjavur, Thiruvarur, Nagapattinam (incl. Mayiladuthurai, merged in all years), Tiruchirappalli, Ariyalur, Perambalur |
| Fasli_year | Season label, for example 2014-15 |
| Area_ha | Area under the season, hectares (all irrigation sources) |
| Production_t | Production, tonnes, in rice terms as published |
| Yield_t_per_ha | Production divided by area. Stored as a formula value |
| Mettur_opening_storage_TMC | Mettur storage on the opening day for delta irrigation, TMC |
| Mettur_opening_date | Opening date |
| Mettur_opening_delay_days | Days after 12 June (negative = earlier) |
| Mettur_closing_date | Closing date (blank for 2016-17, source date looks like a typo) |
| Mettur_release_days | Closing date minus opening date |
| Mettur_total_inflow_TMC / Mettur_total_outflow_TMC | Opening-to-closing totals. Only available to 2020-21 |
| NEM_rain_mm_report | October to December district rainfall from the Season and Crop Report. Blank for 2015-16 (rows shifted in the source table) and 2019-20 (not available). Not used by the models |
| Source_edition | Which table or report the row came from |
| Notes | Checks, derivations and warnings |

## long_annual_rice_3districts_2005_2024.csv  (60 rows: 3 districts x 20 years)
Annual rice (all seasons) for Thanjavur, Thiruvarur and Nagapattinam. Used to choose and test features
over more droughts. Never mixed with the main dataset in one model.

| Column | Meaning |
|---|---|
| Rice_area_ha, Rice_production_t, Rice_yield_t_ha | Annual rice, all seasons |
| Source | Ministry of Agriculture APY (2005-06 to 2013-14), Season and Crop Report or Table V.5 (2014-15 onward) |
| Mettur_opening_storage_TMC, Mettur_opening_delay_days | As above |

## weather_features_nasa_by_fasli_year.csv  (120 rows: 6 districts x 20 years)
Computed from NASA POWER daily data at one point near each district centre (see `scripts/nasa_power_delta_download.py`).
NASA's grid is coarse, so several districts share identical series (Thanjavur, Thiruvarur and Ariyalur; Tiruchirappalli and Perambalur).

| Column pattern | Meaning |
|---|---|
| Rain_JunSep_mm, Rain_OctNov_mm, Rain_OctDec_mm | Rainfall totals for the window |
| ExtremeDays50_* | Days with at least 50 mm of rain |
| Max3day_OctNov_mm, Max3day_OctDec_mm | Largest 3-day rainfall total in the window |
| Tmean / RH / Solar columns | Mean temperature, relative humidity and solar radiation for the window |
Windows ending in Nov are known by 30 November (December forecast). Windows ending in Dec or Jan are post-season only.

## evi_modis_by_district_2005_2024.csv  (120 rows)
MODIS MOD13Q1 greenness (EVI) per district and window, from `scripts/earth_engine_evi_download.py`.
EVImax = mean over cropland pixels of each pixel's peak EVI. EVImean = mean EVI. Nvalid = average number of clear 16-day composites per pixel.
CropPixels500m = number of 500 m cropland pixels kept by the mask (almost the whole district, so this is district greenness, not paddy only).
