# Data quality log

Every extraction from the reports was checked: the three seasons add up to the rice total, and production divided by area matches the published yield.

| Item | What was found | What was done |
|---|---|---|
| 2020-21 paddy area | The report file used had no paddy area table | Area derived as production / yield x 1000, labelled "derived". Checked two ways (from the total and from the three seasons): agree within 0.03%. Tiruchirappalli's real area (44,171 ha) differs by 0.01% from the derived value |
| 2015-16 district rainfall | Rows in the extracted rainfall table are shifted by one district (normals belong to neighbouring districts) | Removed from the data. The yield tables for 2015-16 are not affected |
| 2019-20 | The Season and Crop Report is not available on the department site | Rice table V.5 for 2019-20 used for yield, area and production. District rainfall left blank |
| Three 2022-23 yields | Reported yield differs by 0.2% to 0.4% from production / area | Kept as published, flagged in Notes |
| Tiruchirappalli 2018-19 | Yield 5.4 t/ha is the highest in the data | Kept (internally consistent), flagged |
| Nagapattinam and Mayiladuthurai | Mayiladuthurai became a separate district in 2020 | Merged into one unit for all years |
| Ministry data, 2013-14 | Yields are unusually high and may use a different unit | Tested removing it and rescaling it: the storage effect stays between +0.28 and +0.38 t/ha per 10 TMC |
| Mettur table typos | A few old rows have typos (1987-88 outflow, 1964-65 date, 2016-17 closing date, swapped columns in 1991-93) | Only the years used were checked. 2016-17 closing date left blank |
| Mettur inflow and outflow | Not available after 2020-21 | Not used as model features |
| NASA grid | Several districts share one grid cell and the grid underestimates coastal heavy rain | Documented. Used only for heavy-rain features |
