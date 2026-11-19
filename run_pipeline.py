"""Cauvery Delta paddy yield project: modelling pipeline.

Two datasets, never mixed in one model:
  MAIN  Samba/Thaladi/Pishanam season yield, 6 districts, 2014-15 to 2024-25
  LONG  annual rice yield (all seasons), Thanjavur / Thiruvarur / Nagapattinam, 2005-06 to 2024-25
        (used to choose features and to test them over more droughts)

Target is the district anomaly: yield minus the district mean computed on the
training years only, so nothing leaks from the test year.

Validation (always reported together, never one number alone):
  LOYO        leave-one-year-out
  LOYO-calm   same, but scored without the extreme years
  L2YO        leave-two-years-out, all pairs
  ROLLING     train on earlier years only, test later years
  BOOT        90% interval (bootstrap over YEARS) for the RMSE change vs the baseline
  INTERVAL    80% prediction interval from LOYO residuals, with its coverage

Inputs (data/processed/):  main_samba_panel.csv, long_annual_rice_3districts_2005_2024.csv,
                           weather_features_nasa_by_fasli_year.csv, evi_modis_by_district_2005_2024.csv
Outputs:                   results/*.csv, figures/*.png
Run (from the repo root):  python src/run_pipeline.py
"""
import itertools
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "processed"
RES, FIG = ROOT / "results", ROOT / "figures"
RES.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)
RNG = np.random.default_rng(11)

MAIN_EXTREME = [2016, 2020]                 # drought year and cyclone year
LONG_EXTREME = [2008, 2012, 2016, 2020]     # low-yield years in the long series


# ----------------------------------------------------------------- data
def _weather():
    wf = pd.read_csv(DATA / "weather_features_nasa_by_fasli_year.csv")
    wf["District"] = wf["District"].replace({"Nagapattinam (incl. Mayiladuthurai)": "Nagapattinam"})
    wf = wf[["District", "Fasli_year", "Max3day_OctDec_mm", "Max3day_OctNov_mm"]]
    evi = pd.read_csv(DATA / "evi_modis_by_district_2005_2024.csv")
    evi["District"] = evi["District"].replace({"Nagapattinam (incl. Mayiladuthurai)": "Nagapattinam"})
    evi = evi[["District", "Fasli_year", "EVImax_SepNov", "EVImax_SepJan", "EVImean_SepNov", "EVImean_SepJan"]]
    return wf.merge(evi, on=["District", "Fasli_year"], how="left")


FEATURE_COLS = ["Max3day_OctDec_mm", "Max3day_OctNov_mm", "EVImax_SepNov", "EVImax_SepJan",
                "EVImean_SepNov", "EVImean_SepJan"]


def load_main():
    p = pd.read_csv(DATA / "main_samba_panel.csv")
    p["District"] = p["District"].replace({"Nagapattinam (incl. Mayiladuthurai)": "Nagapattinam"})
    p = p[p["Yield_t_per_ha"].notna()].copy()
    d = p.merge(_weather(), on=["District", "Fasli_year"], how="left")
    d = d.rename(columns={"Yield_t_per_ha": "Y", "Mettur_opening_storage_TMC": "Stor"})
    d["Yr"] = d["Fasli_year"].str[:4].astype(int)
    return d[["District", "Yr", "Y", "Stor"] + FEATURE_COLS]


def load_long():
    p = pd.read_csv(DATA / "long_annual_rice_3districts_2005_2024.csv")
    d = p.merge(_weather(), on=["District", "Fasli_year"], how="left")
    d = d.rename(columns={"Rice_yield_t_ha": "Y", "Mettur_opening_storage_TMC": "Stor"})
    d["Yr"] = d["Fasli_year"].str[:4].astype(int)
    return d[["District", "Yr", "Y", "Stor"] + FEATURE_COLS]


# --------------------------------------------------------------- models
def _ridge(X, y, alpha):
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Z = (X - mu) / sd
    ym = y.mean()
    w = np.linalg.solve(Z.T @ Z + alpha * np.eye(Z.shape[1]), Z.T @ (y - ym))
    return lambda Xn: ((Xn - mu) / sd) @ w + ym


def make_models(rain_col, evi_col=None):
    """name -> (kind, features). rain_col / evi_col pick Mode A (post-season) or Mode B (forecast by 30 Nov).
    Primary EVI windows were fixed in advance: Mode B = Sep-Nov peak EVI, Mode A = Sep-Jan peak EVI."""
    models = {
        "District average": ("mean", []),
        "District trend": ("trend", []),
        "Ridge: storage": ("ridge", ["Stor"]),
        "Ridge: storage + 3-day rain": ("ridge", ["Stor", rain_col]),
        "Forest: storage + 3-day rain": ("forest", ["Stor", rain_col]),
    }
    if evi_col:
        models["Ridge: EVI"] = ("ridge", [evi_col])
        models["Ridge: storage + EVI"] = ("ridge", ["Stor", evi_col])
    return models


def predict(train, test, kind, feats):
    dm = train.groupby("District").Y.mean()
    base = test.District.map(dm).values
    if kind == "mean":
        return base
    if kind == "trend":
        out = []
        for dist, yr in zip(test.District, test.Yr):
            g = train[train.District == dist]
            out.append(np.polyval(np.polyfit(g.Yr, g.Y, 1), yr))
        return np.array(out)
    anomaly = (train.Y - train.District.map(dm)).values
    if kind == "ridge":
        f = _ridge(train[feats].values, anomaly, 2.0)
        return base + f(test[feats].values)
    if kind == "forest":
        rf = RandomForestRegressor(n_estimators=60, max_depth=3, min_samples_leaf=4, random_state=0)
        rf.fit(train[feats].values, anomaly)
        return base + rf.predict(test[feats].values)
    raise ValueError(kind)


def rmse(a, b):
    return float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2)))


# ----------------------------------------------------------- validation
def evaluate(data, models, extreme, roll_start, label, quick=False):
    years = sorted(data.Yr.unique())
    loyo = {}
    for name, (kind, feats) in models.items():
        parts = []
        for y in years:
            tr, te = data[data.Yr != y], data[data.Yr == y]
            parts.append(pd.DataFrame({"District": te.District.values, "Yr": y, "A": te.Y.values,
                                       "P": predict(tr, te, kind, feats)}))
        loyo[name] = pd.concat(parts, ignore_index=True)

    base = loyo["District average"]
    table = []
    for name, (kind, feats) in models.items():
        r = loyo[name]
        calm = r[~r.Yr.isin(extreme)]
        # leave-two-years-out
        l2 = [np.nan] if quick else [rmse(data[data.Yr.isin(p)].Y, predict(data[~data.Yr.isin(p)], data[data.Yr.isin(p)], kind, feats))
              for p in itertools.combinations(years, 2)]
        # rolling origin
        A, P = [], []
        for y in years:
            tr, te = data[data.Yr < y], data[data.Yr == y]
            if y < roll_start or tr.Yr.nunique() < 5:
                continue
            A += list(te.Y)
            P += list(predict(tr, te, kind, feats))
        # bootstrap over years vs baseline
        lo = hi = np.nan
        if name != "District average":
            diffs = []
            err_base = {y: (base[base.Yr == y].A - base[base.Yr == y].P).values for y in years}
            err_model = {y: (r[r.Yr == y].A - r[r.Yr == y].P).values for y in years}
            for _ in range(300 if quick else 1500):
                s = RNG.choice(years, len(years))
                e1 = np.concatenate([err_base[y] for y in s])
                e2 = np.concatenate([err_model[y] for y in s])
                diffs.append(np.sqrt(np.mean(e2 ** 2)) - np.sqrt(np.mean(e1 ** 2)))
            lo, hi = np.percentile(diffs, [5, 95])
        # 80% interval from LOYO residuals of the other years
        cover, width = [], []
        res = (r.A - r.P).abs()
        for y in years:
            q = np.quantile(res[r.Yr != y], 0.8)
            cover += list(res[r.Yr == y] <= q)
            width.append(2 * q)
        table.append({
            "Dataset": label, "Model": name,
            "LOYO_RMSE": rmse(r.A, r.P), "LOYO_calm_RMSE": rmse(calm.A, calm.P),
            "L2YO_RMSE": float(np.mean(l2)), "Rolling_RMSE": rmse(A, P),
            "Skill_vs_district_avg_%": 100 * (1 - rmse(r.A, r.P) / rmse(base.A, base.P)),
            "Boot90_low": lo, "Boot90_high": hi,
            "Interval80_coverage_%": 100 * float(np.mean(cover)), "Interval80_width_t_ha": float(np.mean(width)),
        })
    return pd.DataFrame(table), loyo


def storage_slope(data, reps=2000):
    """Pooled within-district slope of yield on opening storage, per +10 TMC, bootstrap CI over years."""
    d = data.copy()
    d["yc"] = d.Y - d.groupby("District").Y.transform("mean")
    d["sc"] = d.Stor - d.groupby("District").Stor.transform("mean")

    def slope(x):
        return float((x.sc * x.yc).sum() / (x.sc ** 2).sum() * 10)

    years = sorted(d.Yr.unique())
    by_year = {y: (d[d.Yr == y].sc.values, d[d.Yr == y].yc.values) for y in years}
    boots = []
    for _ in range(reps):
        ys = RNG.choice(years, len(years))
        sc = np.concatenate([by_year[y][0] for y in ys]); yc = np.concatenate([by_year[y][1] for y in ys])
        boots.append(float((sc * yc).sum() / (sc ** 2).sum() * 10))
    return slope(d), *np.percentile(boots, [5, 95])


# -------------------------------------------------------------- figures
def fig_scatter(long):
    d = long.copy()
    d["yc"] = d.Y - d.groupby("District").Y.transform("mean")
    d["sc"] = d.Stor - d.groupby("District").Stor.transform("mean")
    fig, ax = plt.subplots(figsize=(7, 5))
    for dist, g in d.groupby("District"):
        ax.scatter(g.sc, g.yc, label=dist, s=36)
    b = (d.sc * d.yc).sum() / (d.sc ** 2).sum()
    xs = np.array([d.sc.min(), d.sc.max()])
    ax.plot(xs, b * xs, color="black", lw=1)
    for _, r in d[d.Yr.isin(LONG_EXTREME)].iterrows():
        ax.annotate(str(r.Yr), (r.sc, r.yc), fontsize=7, xytext=(3, 3), textcoords="offset points")
    ax.axhline(0, color="grey", lw=0.5)
    ax.axvline(0, color="grey", lw=0.5)
    ax.set_xlabel("Opening storage of Mettur, difference from district average (TMC)")
    ax.set_ylabel("Annual rice yield, difference from district average (t/ha)")
    ax.set_title("Lower opening storage, lower yield (3 districts, 20 years)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "fig1_storage_vs_yield_long.png", dpi=150)
    plt.close(fig)


def fig_loyo(loyo, label, fname, extreme):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    a = loyo["District average"].groupby("Yr").mean(numeric_only=True)
    s = loyo["Ridge: storage"].groupby("Yr").mean(numeric_only=True)
    ax.plot(a.index, a.A, "o-", color="black", label="Actual (mean of districts)")
    ax.plot(a.index, a.P, "s--", color="tab:orange", label="District average")
    ax.plot(s.index, s.P, "^--", color="tab:blue", label="Ridge: storage")
    for y in extreme:
        ax.axvline(y, color="red", alpha=0.15, lw=6)
    ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    ax.set_xlabel("Season starting year")
    ax.set_ylabel("Yield (t/ha)")
    ax.set_title(f"{label}: leave-one-year-out predictions (shaded = extreme years)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / fname, dpi=150)
    plt.close(fig)


def sensitivity_long(long):
    """Is the storage effect driven by one odd year? 2013-14 looks unusually high; it may use a different unit."""
    variants = {
        "All 20 years": long,
        "Without 2013-14": long[long.Yr != 2013],
        "Without 2013-14 and 2005-06": long[~long.Yr.isin([2013, 2005])],
        "2013-14 scaled by 0.67 (if it were paddy units)": long.assign(Y=np.where(long.Yr == 2013, long.Y * 0.67, long.Y)),
        "2008-09 onward only": long[long.Yr >= 2008],
    }
    models = {k: v for k, v in make_models("Max3day_OctDec_mm").items() if k in ("District average", "Ridge: storage")}
    rows = []
    for name, d in variants.items():
        t, _ = evaluate(d, models, [y for y in LONG_EXTREME if y in set(d.Yr)], 2012, name, quick=True)
        s = t[t.Model == "Ridge: storage"].iloc[0]
        b, lo, hi = storage_slope(d)
        rows.append({"Variant": name, "Years": d.Yr.nunique(), "Skill_vs_district_avg_%": s["Skill_vs_district_avg_%"],
                     "Slope_per_+10_TMC": b, "Slope_boot90_low": lo, "Slope_boot90_high": hi})
    out = pd.DataFrame(rows)
    out.to_csv(RES / "sensitivity_long.csv", index=False)
    return out


# ----------------------------------------------------------------- main
def main():
    main_d, long_d = load_main(), load_long()
    print(f"MAIN: {len(main_d)} rows, {main_d.Yr.nunique()} years | LONG: {len(long_d)} rows, {long_d.Yr.nunique()} years")

    out = []
    for label, data, ext, roll in [("MAIN Samba yield (6 districts)", main_d, MAIN_EXTREME, 2019),
                                   ("LONG annual rice yield (3 districts)", long_d, LONG_EXTREME, 2012)]:
        for mode, col, evi in [("Mode A (post-season, Oct-Dec rain, Sep-Jan EVI)", "Max3day_OctDec_mm", "EVImax_SepJan"),
                               ("Mode B (December forecast, Oct-Nov rain, Sep-Nov EVI)", "Max3day_OctNov_mm", "EVImax_SepNov")]:
            t, loyo = evaluate(data.dropna(subset=[col, evi]), make_models(col, evi), ext, roll, label)
            t.insert(1, "Mode", mode)
            out.append(t)
            if mode.startswith("Mode A"):
                pd.concat(loyo, names=["Model"]).reset_index(level=0).to_csv(
                    RES / f"loyo_predictions_{'main' if label.startswith('MAIN') else 'long'}.csv", index=False)
                fig_loyo(loyo, label.split(" (")[0], f"fig_loyo_{'main' if label.startswith('MAIN') else 'long'}.png", ext)
    summary = pd.concat(out, ignore_index=True)
    summary.to_csv(RES / "model_comparison.csv", index=False)

    rows = []
    for label, data in [("MAIN Samba yield", main_d), ("LONG annual rice yield", long_d)]:
        b, lo, hi = storage_slope(data)
        rows.append({"Dataset": label, "Yield_change_per_+10_TMC_storage_t_ha": b, "Boot90_low": lo, "Boot90_high": hi})
    slopes = pd.DataFrame(rows)
    slopes.to_csv(RES / "storage_effect.csv", index=False)
    fig_scatter(long_d)
    sens = sensitivity_long(long_d)

    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    show = summary[summary.Mode.str.startswith("Mode A")].drop(columns=["Mode"]).round(2)
    print(show.to_string(index=False))
    print()
    print(summary[summary.Mode.str.startswith("Mode B")].drop(columns=["Mode"]).round(2)[
        ["Dataset", "Model", "LOYO_RMSE", "Rolling_RMSE", "Skill_vs_district_avg_%"]].to_string(index=False))
    print()
    print(slopes.round(2).to_string(index=False))
    print()
    print(sens.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
