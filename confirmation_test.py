"""Out-of-sample confirmation on the long dataset.

Fit on the first 12 seasons (2005-06 to 2016-17), the years in which the storage and heavy-rain
patterns were first noticed, then predict the 8 later seasons (2017-18 to 2024-25) that played no part in
choosing the features. A pattern that is real should help on these new years too.

Run (from the repo root): python src/confirmation_test.py
Output: results/confirmation_test_long.csv
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import run_pipeline as rp  # noqa: E402


def main():
    d = rp.load_long()
    train, test = d[d.Yr <= 2016], d[d.Yr >= 2017]
    models = rp.make_models("Max3day_OctDec_mm", "EVImax_SepJan")
    rows = []
    for name, (kind, feats) in models.items():
        pred = rp.predict(train, test, kind, feats)
        rows.append({"Model": name, "Test_years": "2017-18 to 2024-25", "RMSE_t_ha": rp.rmse(test.Y, pred)})
    out = pd.DataFrame(rows)
    base = out.loc[out.Model == "District average", "RMSE_t_ha"].iloc[0]
    out["Skill_vs_district_avg_%"] = 100 * (1 - out.RMSE_t_ha / base)
    out.to_csv(rp.RES / "confirmation_test_long.csv", index=False)
    print(out.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
