# Predicting Rice Yield in the Cauvery Delta: What Mettur Water Can and Cannot Explain

**Author:** Hari Gugan  |  **Status:** first complete analysis, November 2026

How much of the year-to-year change in paddy yield in Tamil Nadu's Cauvery Delta can be explained, and forecast by December, from Mettur reservoir water and weather? This project builds a documented district-year dataset from official reports, tests simple models with strict year-by-year validation, and reports honestly where the data helps and where it does not.

## Key findings

1. **Mettur opening storage has a measurable effect on delta rice yield.** In a 20-year series for three eastern districts, each extra 10 TMC of opening storage goes with about **+0.32 t/ha** of yield (90% interval +0.18 to +0.44). The result holds when the unusual 2013-14 year is removed or rescaled (+0.28 to +0.38).
2. **No model beats the district average in the main Samba-season dataset** (6 districts, 11 seasons). The direction of the storage effect is the same (+0.25 t/ha per 10 TMC), but 11 seasons are too few to prove it.
3. **Everything else I tested did not help:** heaviest 3-day rainfall, October to December rainfall, a district trend, a random forest, and MODIS satellite greenness (EVI).
4. **Most of the yield variation is not explained by water storage.** Some low-yield seasons (for example 2020-21, a cyclone season) look normal in the Mettur data. Predictions carry about +/- 1 t/ha of uncertainty.

This is a modest result with strong checks, not a forecasting tool for field decisions.

**Interactive demo:** `docs/index.html` is a small page that applies the simple model (district average + storage adjustment). To open it in a browser, turn on GitHub Pages for this repository (Settings, Pages, branch `main`, folder `/docs`).

## Question and scope

- **Target (main dataset):** yield (tonnes per hectare, in rice terms as published) of the combined **Samba/Thaladi/Pishanam season** (sown August to November). Thaladi alone is not reported separately in official statistics.
- **Districts:** Thanjavur, Thiruvarur, Nagapattinam (merged with Mayiladuthurai in all years), Tiruchirappalli, Ariyalur, Perambalur.
- **Years:** 2014-15 to 2024-25 (66 district-years, no gaps).
- **Second dataset:** annual rice yield (all seasons) for Thanjavur, Thiruvarur and Nagapattinam, 2005-06 to 2024-25 (60 district-years). It is used to choose and test features over more drought years. The two datasets are never mixed in one model.

## Data

| Data | Source | Notes |
|---|---|---|
| Area, production, yield by district and season | Season and Crop Report, Dept. of Economics and Statistics, Tamil Nadu | Tables IV-A, V-A, V-B. 2019-20 from the district-wise rice table V.5 |
| Annual rice 2005-06 to 2013-14 | Ministry of Agriculture, Area Production Yield portal | Used only for the three districts where it matches the Season and Crop Report within 1.5% |
| Mettur opening and closing details | Tamil Nadu Statistical Handbook (to 2020-21), Water Resources Department bulletins (2021-22 to 2024-25) | Opening storage, opening date, release days |
| Rainfall, temperature, humidity, sunshine | NASA POWER | One point per district; coarse grid |
| Crop greenness | MODIS MOD13Q1 through Google Earth Engine | Tested, did not help |

Full details: [`docs/sources.md`](docs/sources.md), [`docs/data_dictionary.md`](docs/data_dictionary.md) and [`docs/data_quality_log.md`](docs/data_quality_log.md). Every extraction was checked (seasons add up to the rice total; production divided by area matches the published yield). Raw files are not included.

## Method

- **Prediction target:** the district anomaly, meaning yield minus that district's average computed on the **training years only**. Nothing from the test year leaks into the model.
- **Baselines:** district average and district trend.
- **Models:** ridge regression (storage; storage + heaviest 3-day rain; EVI; storage + EVI) and a shallow random forest.
- **Validation is always by year, never random.** Because districts move together in a year, 66 rows behave like about 11 independent test points, so several views are reported together:
  - leave-one-year-out (also scored without the extreme years)
  - leave-two-years-out over all pairs
  - a rolling forecast that trains on earlier years only
  - a bootstrap over **years** for the size of any improvement
  - 80% prediction intervals and how often they cover the actual value
- **Two versions:** Mode A (post-season, uses data to January) and Mode B (December forecast, uses data to 30 November). Mode B results are in `results/model_comparison.csv` and tell the same story.

## Results

### 1. Opening storage and yield

![Storage and yield](figures/fig1_storage_vs_yield_long.png)

Lower opening storage goes with lower yield in the 20-year series. The scatter is wide. The drought years 2012-13 and 2016-17 sit on the low-storage side, as expected, but 2008-09 is a low-yield year with normal storage, and 2020-21 (a cyclone season) has normal storage and low yield.

Effect of +10 TMC of opening storage on yield (`results/storage_effect.csv`):

| Dataset | Change in yield (t/ha) | 90% interval |
|---|---|---|
| Long: annual rice, 3 districts, 20 years | +0.32 | +0.18 to +0.44 |
| Main: Samba season, 6 districts, 11 years | +0.25 | -0.10 to +0.54 |

Robustness (`results/sensitivity_long.csv`): the long-series effect stays between +0.28 and +0.38 t/ha when 2013-14 or 2005-06 are dropped, when 2013-14 is rescaled (the source may use a different unit), or when only 2008-09 onward is used.

### 2. Model comparison, Main dataset (Samba yield, 6 districts, 11 years), Mode A

| Model | Leave-one-year-out error (t/ha) | Error reduction vs district average (negative = worse) | 90% interval of the error change (t/ha) | Rolling forecast error (t/ha) | 80% interval covers |
|---|---|---|---|---|---|
| District average | 0.81 | baseline |  | 0.52 | 77% |
| District trend | 0.87 | -8% | -0.03 to +0.13 | 0.65 | 79% |
| Ridge: storage | 0.85 | -6% | -0.03 to +0.16 | 0.69 | 77% |
| Ridge: storage + 3-day rain | 0.99 | -23% | +0.07 to +0.28 | 0.90 | 79% |
| Forest: storage + 3-day rain | 0.89 | -10% | -0.04 to +0.18 | 0.66 | 79% |
| Ridge: EVI | 0.84 | -4% | +0.01 to +0.06 | 0.53 | 77% |
| Ridge: storage + EVI | 0.88 | -10% | -0.00 to +0.16 | 0.70 | 77% |

The district average is already hard to beat. Every other model has a larger error, and the heavy-rain model is clearly worse.

![Main predictions](figures/fig_loyo_main.png)

### 3. Model comparison, Long dataset (annual rice, 3 districts, 20 years), Mode A

| Model | Leave-one-year-out error (t/ha) | Error reduction vs district average (negative = worse) | 90% interval of the error change (t/ha) | Rolling forecast error (t/ha) | 80% interval covers |
|---|---|---|---|---|---|
| District average | 0.91 | baseline |  | 0.89 | 80% |
| District trend | 0.88 | +3% | -0.12 to +0.07 | 0.97 | 78% |
| Ridge: storage | 0.81 | +11% | -0.21 to +0.00 | 0.79 | 77% |
| Ridge: storage + 3-day rain | 0.77 | +15% | -0.28 to +0.01 | 0.81 | 78% |
| Forest: storage + 3-day rain | 0.78 | +15% | -0.23 to -0.01 | 0.93 | 80% |
| Ridge: EVI | 0.94 | -4% | +0.01 to +0.06 | 0.89 | 78% |
| Ridge: storage + EVI | 0.85 | +7% | -0.18 to +0.05 | 0.78 | 80% |

Storage reduces the leave-one-year-out error by about 11% (borderline: the interval touches zero) and also helps in the rolling forecast. **The heavy-rain improvement did not confirm on later years** (next section), so it is not claimed.

![Long predictions](figures/fig_loyo_long.png)

### 4. Does the pattern hold on years that were not used to find it?

Fit on 2005-06 to 2016-17, predict 2017-18 to 2024-25 (`results/confirmation_test_long.csv`, from `src/confirmation_test.py`):

| Model | Error on the 8 new seasons (t/ha) |
|---|---|
| District average | 0.65 |
| Ridge: storage | 0.65 |
| Ridge: storage + 3-day rain | 0.70 |
| Ridge: EVI | 0.62 |

Those 8 seasons were mostly mild (only 2020-21 was extreme), so there was little to predict. Storage gave no gain there, heavy rain made it worse, and EVI was slightly better. With 8 seasons I do not read much into any of these differences.

### 5. Uncertainty

The 80% prediction intervals cover about 77% to 80% of the test years, as intended, but they are about 2 t/ha wide. Predictions are rough guides, not precise forecasts.

## What did not work, and why this is useful

- **Heaviest 3-day rain:** helped in the first 12 seasons, did not confirm on the later 8, and hurt in the main dataset.
- **MODIS EVI:** no gain in either dataset. The land-cover mask kept almost the whole district (so it is district greenness, not paddy only), monsoon clouds left about 2 clear observations in October and November, and the damage in bad years happens after the measurement window.
- **Total October to December rainfall, opening delay:** added nothing.
- **Random forest:** no better than simple ridge models, as expected with so few years.

## Limitations

- **About 11 independent seasons** in the main dataset. Results show association, not cause.
- **Extreme years dominate the error** (2016-17 drought, 2020-21 cyclones). When one of them is the test year, no similar year is left in the training data.
- **NASA weather is coarse:** Thanjavur, Thiruvarur and Ariyalur share one series, Tiruchirappalli and Perambalur another, and coastal heavy rain is underestimated.
- **Two Mettur storage values are derived** from the water level (2021-22 and 2022-23). Mettur inflow and outflow stop at 2020-21 and are not used.
- **2020-21 paddy area is derived** from production and yield, and labelled so.
- **The 2013-14 Ministry values look high** and may use a different unit. Conclusions do not depend on them.
- Results are district-level and historical, not field-level advice.

## Reproduce

```bash
python -m pip install -r requirements.txt
python src/run_pipeline.py          # models, validation, figures (about 2 minutes)
python src/confirmation_test.py     # out-of-sample check on the long dataset
```

Random forest results can differ in the second decimal depending on row order. The weather and EVI files were produced by `scripts/nasa_power_delta_download.py` and `scripts/earth_engine_evi_download.py`, which are designed for Google Colab (NASA and Earth Engine need internet access and, for Earth Engine, a free noncommercial account and your own project ID).

## Repository layout

```
data/processed/   cleaned tables used by the models
data/raw/         not published (see docs/sources.md)
src/              run_pipeline.py, confirmation_test.py
scripts/          data download scripts (NASA POWER, Earth Engine)
results/          model comparison, storage effect, sensitivity, predictions
figures/          charts used in this README
docs/             data dictionary, sources, data quality log, and index.html (the interactive demo)
```

## Future work

- Add the Samba-season reports for 2005-06 to 2013-14 to extend the main dataset beyond 11 seasons.
- Use block-level data or paddy-specific satellite maps (Sentinel-1 radar) for a sharper crop signal.
- Add cyclone and flood event indicators, since these explain what water storage cannot.
- Add nitrogen use once a recent district series is available.

## License and sources

Code: MIT (see `LICENSE`). The tables in `data/processed/` are compiled from public sources listed in `docs/sources.md` and remain subject to those sources' terms.
