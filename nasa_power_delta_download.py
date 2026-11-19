# NASA POWER daily weather for the Cauvery Delta districts.
# Run in Google Colab: paste this whole file into one cell and run it.
# Output: nasa_power_delta_daily.csv (one row per district per day).
#
# Note: each district uses one point near its centre, so values describe
# that point, not the district average. State this in the README.

import time
import requests
import pandas as pd

DISTRICTS = {
    "Thanjavur": (10.787, 79.139),
    "Thiruvarur": (10.772, 79.636),
    "Nagapattinam (incl. Mayiladuthurai)": (10.850, 79.750),
    "Tiruchirappalli": (10.790, 78.705),
    "Ariyalur": (11.140, 79.076),
    "Perambalur": (11.234, 78.880),
}

PARAMS = "PRECTOTCORR,ALLSKY_SFC_SW_DWN,T2M,T2M_MAX,T2M_MIN,RH2M"
URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

frames = []
for name, (lat, lon) in DISTRICTS.items():
    print("Downloading", name)
    resp = requests.get(
        URL,
        params={
            "parameters": PARAMS,
            "community": "AG",
            "longitude": lon,
            "latitude": lat,
            "start": "20050101",
            "end": "20251231",
            "format": "JSON",
        },
        timeout=180,
    )
    resp.raise_for_status()
    values = resp.json()["properties"]["parameter"]
    df = pd.DataFrame(values)
    df.index.name = "date"
    df = df.reset_index()
    df.insert(0, "district", name)
    frames.append(df)
    time.sleep(2)

out = pd.concat(frames, ignore_index=True)
out = out.replace(-999, pd.NA)  # NASA POWER uses -999 for missing values
out.to_csv("nasa_power_delta_daily.csv", index=False)
print("Rows:", len(out), "| Districts:", out["district"].nunique())
print(out.head())

# Download the file to your computer (works in Colab only)
try:
    from google.colab import files
    files.download("nasa_power_delta_daily.csv")
except ImportError:
    pass
