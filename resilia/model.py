"""RESILIA — modelo de um sistema off-grid solar + eólico + bateria para Mabote (Inhambane).

O modelo é deliberadamente simples, para se compreender facilmente:
  1. Oferta  — painéis solares (com efeito da temperatura e do vento) e um pequeno aerogerador,
               ambos com dados horários reais (ERA5, 2015–2025): o sol e o vento variam hora a hora.
  2. Procura — calculada a partir do número de famílias e dos serviços da aldeia; varia ao longo
               do dia, entre dias da semana e de dia para dia.
  3. Balanço — em cada hora: renováveis → consumo; excedente → bateria; défice → bateria;
               o que a bateria não cobre é energia não servida (interrupção).
  4. Dimensionamento a longo prazo — cada sistema candidato é testado contra 11 anos de dias reais.
     «Eficiente» = o mais barato que serve o dia médio. «Resiliente» = o mais barato que também
     aguenta os piores dias com pouco ou nenhum corte.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"
SITE = dict(name="Mabote", region="Inhambane", lat=-22.05, lon=34.13, utc=2, tilt=22)

# parâmetros técnicos (valores típicos)
PR = 0.88            # perdas eléctricas do sistema solar (cablagem, inversor, sujidade)
GAMMA = -0.0035      # perda de potência do painel por °C acima de 25 °C
NOCT = 45.0          # temperatura nominal de operação da célula
ETA = 0.95           # eficiência de carga e de descarga da bateria
SOC_MIN = 0.20       # a bateria nunca desce abaixo de 20 % (protege a vida útil)
C_RATE = 0.5         # potência máxima da bateria = 0,5 × capacidade
HUB = 18.0           # altura do aerogerador (m)
COST = dict(pv=650.0, bat=320.0, wind=3500.0)   # USD por kWp / kWh / kW (indicativo, mini-redes em África)


# ───────────────────────────── dados ─────────────────────────────
def load_weather() -> pd.DataFrame:
    df = pd.read_csv(DATA / "MZ_era5.csv.gz", index_col=0, parse_dates=True)
    df.index = df.index + pd.Timedelta(hours=SITE["utc"])
    df = df[~df.index.duplicated()].sort_index().interpolate(limit=6).fillna(0.0)
    return df


def _sun(idx: pd.DatetimeIndex):
    """cos(zénite) e cos(incidência) num painel virado a norte com inclinação SITE['tilt']."""
    t = idx - pd.Timedelta(hours=SITE["utc"]) - pd.Timedelta(minutes=30)   # meio da hora, em UTC
    doy = t.dayofyear.values.astype(float)
    hr = t.hour.values + t.minute.values / 60.0
    g = 2 * np.pi / 365.0 * (doy - 1 + (hr - 12) / 24)
    eqt = 229.18 * (0.000075 + 0.001868 * np.cos(g) - 0.032077 * np.sin(g) - 0.014615 * np.cos(2 * g)
                    - 0.040849 * np.sin(2 * g))
    dec = (0.006918 - 0.399912 * np.cos(g) + 0.070257 * np.sin(g) - 0.006758 * np.cos(2 * g)
           + 0.000907 * np.sin(2 * g) - 0.002697 * np.cos(3 * g) + 0.00148 * np.sin(3 * g))
    ha = np.radians((hr * 60 + eqt + 4 * SITE["lon"]) / 4 - 180)
    phi = np.radians(SITE["lat"])
    cz = np.sin(phi) * np.sin(dec) + np.cos(phi) * np.cos(dec) * np.cos(ha)
    phi_a, dec_a, b = abs(phi), -dec, np.radians(SITE["tilt"])           # hemisfério sul → espelhar
    ci = np.sin(dec_a) * np.sin(phi_a - b) + np.cos(dec_a) * np.cos(ha) * np.cos(phi_a - b)
    return np.clip(cz, -1, 1), np.clip(ci, -1, 1)


def resource(df: pd.DataFrame) -> pd.DataFrame:
    """Produção por unidade instalada: kW por kWp solar e kW por kW eólico, hora a hora."""
    cz, ci = _sun(df.index)
    ghi = df["shortwave_radiation"].values.astype(float)
    dif = df["diffuse_radiation"].values.astype(float)
    dirh = df["direct_radiation"].values.astype(float)
    dni = np.where(cz > 0.087, dirh / np.maximum(cz, 0.087), 0.0).clip(0, 1100)
    b = np.radians(SITE["tilt"])
    poa = dni * np.clip(ci, 0, None) + dif * (1 + np.cos(b)) / 2 + ghi * 0.2 * (1 - np.cos(b)) / 2
    poa = np.where(ghi <= 0, 0.0, np.clip(poa, 0, 1300))
    ta = df["temperature_2m"].values.astype(float)
    v10 = df["wind_speed_10m"].values.astype(float)
    tc = ta + (NOCT - 20) * poa / 800.0 * 9.5 / (5.7 + 3.8 * np.clip(v10, 0, 30))   # o vento arrefece o painel
    pv1 = np.clip(poa / 1000.0 * (1 + GAMMA * (tc - 25)) * PR, 0, None)
    # vento à altura do aerogerador (perfil vertical a partir de 10 m e 100 m)
    if "wind_speed_100m" in df:
        alpha = np.clip(np.log(np.maximum(df["wind_speed_100m"].values, 0.1) / np.maximum(v10, 0.1)) / math.log(10), 0.05, 0.35)
    else:
        alpha = np.full(len(df), 0.14)
    vh = v10 * (HUB / 10.0) ** alpha
    vin, vr, vout = 2.5, 11.0, 25.0
    w1 = np.where(vh >= vout, 0.0, np.clip((vh ** 3 - vin ** 3) / (vr ** 3 - vin ** 3), 0, 1))
    return pd.DataFrame({"pv1": pv1, "w1": w1, "poa": poa, "ghi": ghi, "t": ta, "v": v10, "vh": vh,
                         "rain": df["precipitation"].values}, index=df.index)


# ───────────────────────────── procura ─────────────────────────────
HOUSE_W = np.array([6] * 6 + [12, 10] + [6] * 9 + [20] + [35] * 4 + [20, 10], float)   # W por família (~0,3 kWh/dia)
HEALTH = np.array([0.38] * 6 + [0.45, 0.6] + [0.9] * 5 + [0.8] * 4 + [0.7] * 5 + [0.45] * 2)  # kW (~15 kWh/dia)


@dataclass
class Village:
    households: int = 200
    health: bool = True
    school: bool = True
    water: bool = True
    mill: bool = True
    growth: float = 0.0        # crescimento da procura (%), para planear o futuro


def demand(idx: pd.DatetimeIndex, temp: np.ndarray, v: Village) -> pd.DataFrame:
    """Procura horária (kW) por serviço. Varia com a hora, o dia da semana, a temperatura e de dia para dia."""
    h = idx.hour.values
    dow = idx.dayofweek.values
    k = v.households / 200.0
    hot = np.clip(temp - 30, 0, 12)
    fans = np.where((h >= 11) | (h < 1), 1.5 * hot, 0.3 * hot)                  # ventoinhas nos dias quentes
    homes = v.households * (HOUSE_W[h] + fans) / 1000.0
    street = np.where((h >= 18) | (h < 5), 0.04 * max(5, v.households // 10), 0.0)
    health = HEALTH[h] * v.health
    school = np.where((dow < 5) & (h >= 8) & (h <= 15), 1.0 * k, 0.0) * v.school
    water = np.where(np.isin(h, [7, 8, 9, 15, 16, 17]), 2.5 * k, 0.0) * v.water
    mill = np.where((dow < 6) & np.isin(h, [8, 9, 15]), 5.5 * k, 0.0) * v.mill
    # variação natural de dia para dia (±8 %) e de hora para hora (±4 %), reprodutível
    day_no = ((idx - pd.Timestamp("2015-01-01")).days).values
    rng = np.random.default_rng(36)
    day_f = 1 + 0.08 * rng.standard_normal(day_no.max() + 2)
    hour_f = 1 + 0.04 * np.random.default_rng(7).standard_normal(len(idx))
    f = np.clip(day_f[np.clip(day_no, 0, None)] * hour_f, 0.75, 1.3) * (1 + v.growth / 100.0)
    parts = pd.DataFrame({"homes": homes, "street": street, "health": health, "school": school, "water": water,
                          "mill": mill}, index=idx).mul(f, axis=0)
    parts["total"] = parts.sum(axis=1)
    return parts


# ───────────────────────────── balanço horário ─────────────────────────────
@dataclass
class System:
    pv: float = 40.0      # kWp
    wind: float = 5.0     # kW
    bat: float = 120.0    # kWh


def simulate(res: pd.DataFrame, dem: np.ndarray, s: System, soc0: float = 0.6) -> pd.DataFrame:
    """Balanço hora a hora para um sistema."""
    n = len(res)
    pv = res["pv1"].values * s.pv
    wd = res["w1"].values * s.wind
    cap = max(s.bat, 1e-9)
    emin, pmax = SOC_MIN * s.bat, C_RATE * s.bat
    E = soc0 * s.bat
    out = np.zeros((n, 7))
    for t in range(n):
        d = float(dem[t])
        re = float(pv[t] + wd[t])
        direct = min(re, d)
        sur, dfc = re - direct, d - direct
        ch = min(sur, pmax, max(s.bat - E, 0) / ETA) if s.bat > 0 else 0.0
        E += ch * ETA
        dis = min(dfc, pmax, max(E - emin, 0) * ETA) if s.bat > 0 else 0.0
        E -= dis / ETA
        out[t] = (direct, ch, dis, dfc - dis, sur - ch, E / cap if s.bat > 0 else 0.0, d)
    o = pd.DataFrame(out, columns=["direct", "bat_ch", "bat_dis", "unmet", "curt", "soc", "demand"], index=res.index)
    o["pv"], o["wind"] = pv, wd
    # quanto do consumo directo veio do sol e quanto do vento (proporcional)
    share = np.where(pv + wd > 0, pv / np.maximum(pv + wd, 1e-9), 1.0)
    o["direct_pv"], o["direct_wind"] = o["direct"] * share, o["direct"] * (1 - share)
    return o


def day_metrics(o: pd.DataFrame, s: System) -> dict:
    dem, un = o["demand"].sum(), o["unmet"].sum()
    gen = (o["pv"] + o["wind"]).sum()
    return dict(
        risk=100 * un / max(dem, 1e-9), unmet=un, demand=dem, served=dem - un,
        hours=int((o["unmet"] > 0.01 * o["demand"]).sum()),
        waste=100 * o["curt"].sum() / max(gen, 1e-9), pv=o["pv"].sum(), wind=o["wind"].sum(),
        soc_end=100 * o["soc"].iloc[-1], soc_min=100 * o["soc"].min(),
        autonomy=(1 - SOC_MIN) * s.bat * ETA / max(o["demand"].mean(), 1e-9),
    )


def verdict(risk: float):
    if risk <= 2:
        return "ok"
    if risk <= 10:
        return "partial"
    return "fragile"


# ───────────────────────────── tipos de dia (dados reais) ─────────────────────────────
DAY_TYPES = ["sunny", "partly", "cloudy", "storm", "hot"]


def representative_days(df: pd.DataFrame) -> dict:
    """Escolhe dias reais típicos de cada condição a partir de 11 anos de dados."""
    d = df.resample("D").agg({"shortwave_radiation": "sum", "precipitation": "sum", "temperature_2m": "max",
                              "wind_gusts_10m": "max"})
    d = d[d.index.year >= 2016]
    sol = d["shortwave_radiation"]

    def closest(series, q, pool=None):
        s = series if pool is None else series[pool]
        target = s.quantile(q)
        return (s - target).abs().idxmin()

    rain_pool = d["precipitation"] >= 30          # dia típico de chuva forte (não o pior caso)
    return {
        "sunny": closest(sol, 0.90),
        "partly": closest(sol, 0.50),
        "cloudy": closest(sol, 0.08),
        "storm": closest(sol, 0.50, rain_pool) if rain_pool.any() else closest(sol, 0.05),
        "hot": d["temperature_2m"].idxmax(),
    }


# ───────────────────────────── dimensionamento a longo prazo ─────────────────────────────
GRID = dict(pv=[30, 40, 50, 60, 70, 80, 90], bat=[80, 120, 160, 200, 260, 320, 400, 500], wind=[0, 5, 10, 15])


def long_term(res: pd.DataFrame, dem: np.ndarray, grid: dict = GRID) -> pd.DataFrame:
    """Testa todos os sistemas da grelha contra a série completa (11 anos), em paralelo (vectorizado)."""
    P, B, W = np.meshgrid(grid["pv"], grid["bat"], grid["wind"], indexing="ij")
    P, B, W = P.ravel().astype(float), B.ravel().astype(float), W.ravel().astype(float)
    m = len(P)
    pv1, w1 = res["pv1"].values, res["w1"].values
    days = ((res.index.normalize() - res.index.normalize()[0]).days).values
    nd = days.max() + 1
    E = 0.6 * B
    emin, pmax = SOC_MIN * B, C_RATE * B
    un_day = np.zeros((nd, m))
    dem_day = np.bincount(days, weights=dem, minlength=nd)
    curt = np.zeros(m); gen = np.zeros(m); hours = np.zeros(m)
    for t in range(len(dem)):
        d = dem[t]
        re = pv1[t] * P + w1[t] * W
        direct = np.minimum(re, d)
        sur, dfc = re - direct, d - direct
        ch = np.minimum(np.minimum(sur, pmax), np.maximum(B - E, 0) / ETA)
        E += ch * ETA
        dis = np.minimum(np.minimum(dfc, pmax), np.maximum(E - emin, 0) * ETA)
        E -= dis / ETA
        un = dfc - dis
        un_day[days[t]] += un
        curt += sur - ch
        gen += re
        hours += un > 0.01 * d
    years = len(dem) / 8760.0
    day_risk = 100 * un_day / np.maximum(dem_day[:, None], 1e-9)
    out = pd.DataFrame(dict(
        pv=P, bat=B, wind=W,
        cost=P * COST["pv"] + B * COST["bat"] + W * COST["wind"],
        risk=100 * un_day.sum(0) / dem.sum(),                       # energia não servida, média de 11 anos
        worst_day=day_risk.max(0),                                   # pior dia em 11 anos
        bad_days=(day_risk > 10).sum(0) / years,                     # dias por ano com >10 % em falta
        hours=hours / years,                                         # horas por ano com interrupção
        waste=100 * curt / np.maximum(gen, 1e-9),                    # energia renovável desperdiçada
        autonomy=(1 - SOC_MIN) * B * ETA / dem.mean(),
    ))
    return out


# Níveis de protecção: energia em falta (média de 11 anos), dias maus por ano (> 10 % em falta) e autonomia
LEVELS = {
    "basic": dict(risk=2.0, bad=12.0, autonomy=8.0),
    "recommended": dict(risk=0.5, bad=3.0, autonomy=12.0),
    "maximum": dict(risk=0.1, bad=1.0, autonomy=24.0),
}


def choose(table: pd.DataFrame, level: dict) -> dict:
    """«Só eficiência»: o mais barato que serve o dia médio (≤ 5 % de energia em falta em média).
    «Resiliente»: o mais barato que cumpre o nível de protecção, ou seja, que também aguenta os dias maus."""
    eff_ok = table[table.risk <= 5.0]
    eff = eff_ok.sort_values("cost").iloc[0] if len(eff_ok) else table.sort_values("risk").iloc[0]
    ok = table[(table.risk <= level["risk"]) & (table.bad_days <= level["bad"]) & (table.autonomy >= level["autonomy"])]
    res = ok.sort_values(["cost", "waste"]).iloc[0] if len(ok) else table.sort_values(["bad_days", "cost"]).iloc[0]
    return dict(efficient=eff, resilient=res, feasible=len(ok) > 0)


def simulate_day(res: pd.DataFrame, dem: np.ndarray, s: System, day: pd.Timestamp, warmup_days: int = 7):
    """Simula o dia escolhido precedido dos 7 dias reais anteriores, para a bateria começar o dia
    no estado em que realmente estaria (e não num valor inventado)."""
    day = pd.Timestamp(day).normalize()
    a = day - pd.Timedelta(days=warmup_days)
    m = (res.index >= a) & (res.index < day + pd.Timedelta(days=1))
    o = simulate(res[m], dem[m], s, soc0=0.6)
    return o[o.index >= day]
