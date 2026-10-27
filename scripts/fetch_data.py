"""Descarrega a base de dados climática real (ERA5 via Open-Meteo) para os 3 locais piloto.

Uso:  python scripts/fetch_data.py
Os ficheiros ficam em data/ e a aplicação funciona offline a partir deles.

Fontes:
- Meteorologia horária: reanálise ERA5 / ERA5-Land (ECMWF, Copernicus) servida pela API
  histórica da Open-Meteo (https://open-meteo.com/en/docs/historical-weather-api).
- Poeira e profundidade óptica de aerossóis: CAMS (Copernicus Atmosphere Monitoring Service)
  servido pela API de qualidade do ar da Open-Meteo.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from resilia.sites import SITES  # noqa: E402

DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

WX_VARS = [
    "temperature_2m", "relative_humidity_2m", "precipitation", "snowfall", "snow_depth",
    "cloud_cover", "pressure_msl", "wind_speed_10m", "wind_speed_100m", "wind_gusts_10m",
    "shortwave_radiation", "direct_radiation", "diffuse_radiation",
]
AQ_VARS = ["dust", "aerosol_optical_depth"]


def _get(url: str, params: dict) -> dict:
    for attempt in range(8):
        try:
            r = requests.get(url, params=params, timeout=120)
            r.raise_for_status()
            return r.json()
        except Exception as ex:  # rede instável: tenta de novo
            print(f"   tentativa {attempt + 1} falhou ({ex.__class__.__name__}); a repetir…")
            time.sleep(3 + 2 * attempt)
    raise RuntimeError(f"Falha ao descarregar {url} {params}")


def fetch_weather(lat: float, lon: float, start: str, end: str) -> pd.DataFrame:
    j = _get("https://archive-api.open-meteo.com/v1/archive", dict(
        latitude=lat, longitude=lon, start_date=start, end_date=end,
        hourly=",".join(WX_VARS), wind_speed_unit="ms", timezone="GMT"))
    df = pd.DataFrame(j["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    return df


def fetch_aq(lat: float, lon: float, start: str, end: str) -> pd.DataFrame:
    j = _get("https://air-quality-api.open-meteo.com/v1/air-quality", dict(
        latitude=lat, longitude=lon, start_date=start, end_date=end,
        hourly=",".join(AQ_VARS), timezone="GMT"))
    df = pd.DataFrame(j["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    return df


def main(first_year: int = 2015, last_year: int = 2025) -> None:
    for key, s in SITES.items():
        out = DATA / f"{key}_era5.csv.gz"
        print(f"== {s['name']} ({s['country']}) {first_year}-{last_year}")
        parts = []
        for y in range(first_year, last_year + 1):
            print(f"   {y}")
            parts.append(fetch_weather(s["lat"], s["lon"], f"{y}-01-01", f"{y}-12-31"))
        wx = pd.concat(parts).drop_duplicates("time").set_index("time").sort_index()

        if s.get("dust"):
            aq_parts = []
            for y in range(max(first_year, 2023), last_year + 1):
                print(f"   poeira CAMS {y}")
                try:
                    aq_parts.append(fetch_aq(s["lat"], s["lon"], f"{y}-01-01", f"{y}-12-31"))
                except RuntimeError as ex:
                    print("   ", ex)
            if aq_parts:
                aq = pd.concat(aq_parts).drop_duplicates("time").set_index("time")
                wx = wx.join(aq, how="left")

        wx.round(2).to_csv(out, compression="gzip")
        print(f"   gravado {out.name}: {len(wx)} horas")


if __name__ == "__main__":
    main()
