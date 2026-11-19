# Data sources

Raw files are not stored in this repository. Check each source's terms before reusing the tables.

| Data | Source | Used for |
|---|---|---|
| Samba/Thaladi/Pishanam area, production, yield by district (2014-15 to 2024-25) | Season and Crop Report, Department of Economics and Statistics, Government of Tamil Nadu (tn.gov.in/crop/stat.htm, des.tn.gov.in). Tables IV-A, V-A, V-B. 2019-20 from the district-wise rice table V.5 for that year | Main dataset |
| Annual rice area, production, yield by district (2005-06 to 2013-14) | Ministry of Agriculture and Farmers Welfare, Area Production Yield (APY) portal, district reports | Long dataset (Thanjavur, Thiruvarur, Nagapattinam only) |
| Mettur reservoir opening and closing details (1934-35 to 2020-21) | Tamil Nadu Statistical Handbook, table VII.10 | Opening storage, opening date, release days |
| Mettur reservoir opening and closing details (2021-22 to 2024-25) | Compiled from Tamil Nadu Water Resources Department bulletins. Storage for 2021-22 and 2022-23 is derived from the water level using the handbook's level and storage pairs | Same |
| Daily rainfall, temperature, humidity, solar radiation | NASA POWER (power.larc.nasa.gov), agroclimatology community | Weather features |
| Crop greenness (EVI) and land cover | MODIS MOD13Q1 and MCD12Q1 through Google Earth Engine; district boundaries from FAO GAUL or geoBoundaries | EVI features (tested, no gain) |
| District rainfall (October to December) | Season and Crop Report, Table I-A | Stored for reference, not used by the models |

## Why the Ministry data is used for three districts only
For Thanjavur, Thiruvarur and Nagapattinam the Ministry annual rice figures match the Season and Crop Report totals within 1.5% for 2014-15 to 2016-17. For Tiruchirappalli, Ariyalur and Perambalur they do not (area differs by 70% to 1,500%), so those districts are not used in the long dataset.
