"""Carregamento da base de dados climática e selecção das janelas de 72 h."""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from .sites import EVENTS, SITES

DATA = Path(__file__).resolve().parents[1] / "data"
EVENT_H = 72      # duração do evento
PRE_H = 48        # horas simuladas antes do evento (preparação / alerta)
POST_H = 24       # horas simuladas depois do evento (recuperação)


def load_site(key: str) -> pd.DataFrame:
    """Série horária completa (hora local fixa do local)."""
    s = SITES[key]
    df = pd.read_csv(DATA / f"{key}_era5.csv.gz", index_col=0, parse_dates=True)
    df.index = df.index + pd.Timedelta(hours=s["utc"])
    df.index.name = "time"
    df.attrs["utc"] = s["utc"]
    return _clean(df)


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df[~df.index.duplicated()].sort_index()
    df = df.interpolate(limit=6).fillna(0.0)
    if "aerosol_optical_depth" in df:
        aod = df["aerosol_optical_depth"].replace(0, np.nan)
        has = aod.notna()
        clim = aod.groupby(aod.index.month).transform("mean")
        df["aod_excess"] = (aod - clim).clip(lower=0).where(has, 0.0).fillna(0.0)
    else:
        df["aod_excess"] = 0.0
    if "dust" not in df:
        df["dust"] = 0.0
    return df


def _rolling_score(sub: pd.DataFrame, rule: str) -> pd.Series:
    r = sub.rolling(EVENT_H)
    if rule == "min_solar":
        return -r["shortwave_radiation"].sum()
    if rule == "max_heat":
        return r["temperature_2m"].mean()
    if rule == "min_temp":
        return -r["temperature_2m"].mean()
    if rule == "max_snow":
        return r["snowfall"].sum() - 0.0005 * r["shortwave_radiation"].sum()
    if rule == "max_rain":
        return r["precipitation"].sum()
    raise ValueError(rule)


def event_window(df: pd.DataFrame, ev_key: str) -> pd.Timestamp:
    """Início (hora local) das 72 h mais severas dentro da janela de procura do evento."""
    ev = EVENTS[ev_key]
    if "start" in ev:
        return pd.Timestamp(ev["start"])
    a, b = ev["search"]
    sub = df.loc[a:pd.Timestamp(b) + pd.Timedelta(hours=23)]
    score = _rolling_score(sub, ev["rule"])
    end = score.idxmax()
    return end - pd.Timedelta(hours=EVENT_H - 1)


def worst_window(df: pd.DataFrame, rule: str = "min_solar") -> pd.Timestamp:
    score = _rolling_score(df, rule)
    end = score.idxmax()
    return end - pd.Timedelta(hours=EVENT_H - 1)


def typical_window(df: pd.DataFrame, near: pd.Timestamp) -> pd.Timestamp:
    """72 h com sol mediano no mesmo mês (referência «dias normais»)."""
    m = df[(df.index.month == near.month) & (df.index.year == near.year)]
    s = m["shortwave_radiation"].rolling(EVENT_H).sum().dropna()
    s = s.iloc[::24]  # começa à meia-noite
    end = (s - s.median()).abs().idxmin()
    return end - pd.Timedelta(hours=EVENT_H - 1)


def sim_slice(df: pd.DataFrame, start: pd.Timestamp) -> pd.DataFrame:
    """Janela simulada: 48 h antes + 72 h de evento + 24 h de recuperação."""
    a = start - pd.Timedelta(hours=PRE_H)
    b = start + pd.Timedelta(hours=EVENT_H + POST_H - 1)
    w = df.loc[a:b].copy()
    w["fase"] = "preparação"
    w.loc[start:start + pd.Timedelta(hours=EVENT_H - 1), "fase"] = "evento"
    w.loc[start + pd.Timedelta(hours=EVENT_H):, "fase"] = "recuperação"
    return w


def intensify(w: pd.DataFrame, pct: float, dT_future: float = 0.0) -> pd.DataFrame:
    """Teste de stress: agrava as anomalias do evento em `pct` % e soma `dT_future` °C (clima futuro).
    Durante o evento: menos sol, rajadas e chuva mais fortes, anomalia térmica ampliada."""
    if pct <= 0 and dT_future == 0:
        return w
    w = w.copy()
    k = pct / 100.0
    ev = (w["fase"] == "evento").values
    for col in ("shortwave_radiation", "direct_radiation", "diffuse_radiation"):
        if col in w:
            w.loc[ev, col] = w.loc[ev, col] * (1 - 0.6 * k)
    for col in ("wind_speed_10m", "wind_gusts_10m", "wind_speed_100m"):
        if col in w:
            w.loc[ev, col] = w.loc[ev, col] * (1 + k)
    for col in ("precipitation", "snowfall"):
        if col in w:
            w.loc[ev, col] = w.loc[ev, col] * (1 + k)
    t = w["temperature_2m"]
    ref = t[~ev].mean() if (~ev).any() else t.mean()
    w.loc[ev, "temperature_2m"] = ref + (t[ev] - ref) * (1 + k)
    w["temperature_2m"] = w["temperature_2m"] + dT_future
    if "aod_excess" in w:
        w.loc[ev, "aod_excess"] = w.loc[ev, "aod_excess"] * (1 + k)
        w.loc[ev, "dust"] = w.loc[ev, "dust"] * (1 + k)
    return w


# ───────────── dados em directo (opcionais; a app funciona sem internet) ─────────────
_WX = ("temperature_2m,relative_humidity_2m,precipitation,snowfall,snow_depth,cloud_cover,pressure_msl,"
       "wind_speed_10m,wind_gusts_10m,shortwave_radiation,direct_radiation,diffuse_radiation")


def _get(url: str, params: dict, tries: int = 4) -> dict:
    last = None
    for k in range(tries):
        try:
            r = requests.get(url, params=params, timeout=40)
            r.raise_for_status()
            return r.json()
        except Exception as ex:
            last = ex
            time.sleep(1.5 * (k + 1))
    raise RuntimeError(f"Sem ligação à fonte de dados ({last.__class__.__name__}).")


def fetch_forecast(lat: float, lon: float, utc: int) -> pd.DataFrame:
    """Previsão horária real (Open-Meteo, modelos ECMWF/GFS/ICON) para os próximos 4 dias,
    mais 2 dias passados para o estado inicial."""
    j = _get("https://api.open-meteo.com/v1/forecast", dict(
        latitude=lat, longitude=lon, hourly=_WX, wind_speed_unit="ms", timezone="GMT",
        past_days=2, forecast_days=4))
    df = pd.DataFrame(j["hourly"])
    df["time"] = pd.to_datetime(df["time"]) + pd.Timedelta(hours=utc)
    return _clean(df.set_index("time"))


def fetch_location(lat: float, lon: float, utc: int, years=(2019, 2025)) -> pd.DataFrame:
    """Série histórica ERA5 para qualquer ponto do planeta (usada no «qualquer local»)."""
    cache = DATA / f"custom_{lat:.2f}_{lon:.2f}.csv.gz"
    if cache.exists():
        df = pd.read_csv(cache, index_col=0, parse_dates=True)
        return _clean(df)
    parts = []
    for y in range(years[0], years[1] + 1):
        j = _get("https://archive-api.open-meteo.com/v1/archive", dict(
            latitude=lat, longitude=lon, start_date=f"{y}-01-01", end_date=f"{y}-12-31",
            hourly=_WX + ",wind_speed_100m", wind_speed_unit="ms", timezone="GMT"))
        p = pd.DataFrame(j["hourly"])
        p["time"] = pd.to_datetime(p["time"]) + pd.Timedelta(hours=utc)
        parts.append(p.set_index("time"))
    df = pd.concat(parts)
    df.round(2).to_csv(cache, compression="gzip")
    return _clean(df)
