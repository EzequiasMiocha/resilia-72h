"""Descarrega a base de dados climática real de Mabote (ERA5 via Open-Meteo), 2015–2025.

Uso:  python scripts/fetch_data.py
O ficheiro fica em data/MZ_era5.csv.gz e a aplicação funciona offline a partir dele.
Fonte: reanálise ERA5 / ERA5-Land (ECMWF, Copernicus) — https://open-meteo.com/en/docs/historical-weather-api
"""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import requests

DATA = Path(__file__).resolve().parents[1] / "data"
LAT, LON = -22.05, 34.13      # Mabote, Inhambane
VARS = ["temperature_2m", "relative_humidity_2m", "precipitation", "snowfall", "snow_depth", "cloud_cover",
        "pressure_msl", "wind_speed_10m", "wind_speed_100m", "wind_gusts_10m", "shortwave_radiation",
        "direct_radiation", "diffuse_radiation"]


def fetch(year: int) -> pd.DataFrame:
    params = dict(latitude=LAT, longitude=LON, start_date=f"{year}-01-01", end_date=f"{year}-12-31",
                  hourly=",".join(VARS), wind_speed_unit="ms", timezone="GMT")
    for attempt in range(8):
        try:
            r = requests.get("https://archive-api.open-meteo.com/v1/archive", params=params, timeout=120)
            r.raise_for_status()
            df = pd.DataFrame(r.json()["hourly"])
            df["time"] = pd.to_datetime(df["time"])
            return df
        except Exception as ex:
            print(f"   tentativa {attempt + 1} falhou ({ex.__class__.__name__}); a repetir…")
            time.sleep(3 + 2 * attempt)
    raise RuntimeError(f"Falha ao descarregar {year}")


def main(first: int = 2015, last: int = 2025) -> None:
    DATA.mkdir(exist_ok=True)
    parts = []
    for y in range(first, last + 1):
        print("Mabote", y)
        parts.append(fetch(y))
    df = pd.concat(parts).drop_duplicates("time").set_index("time").sort_index()
    df.round(2).to_csv(DATA / "MZ_era5.csv.gz", compression="gzip")
    print(f"gravado data/MZ_era5.csv.gz: {len(df)} horas")


if __name__ == "__main__":
    main()
