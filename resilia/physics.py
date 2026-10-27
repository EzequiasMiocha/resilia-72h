"""Modelos físicos dos componentes (vectorizados sobre a série horária).

Referências principais: Duffie & Beckman (2020) para geometria solar e plano inclinado;
Skoplaki & Palyvos (2009) para temperatura de célula com vento; Marion et al. (2013) para
deslizamento de neve; HOMER (Lambert et al., 2006) para curva de combustível do gerador;
fichas técnicas típicas de LFP e inversores para limites térmicos.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class System:
    pv_kwp: float = 40.0
    bat_kwh: float = 120.0
    inv_kw: float = 30.0
    wind_kw: float = 0.0
    diesel_kw: float = 0.0
    fuel_l: float = 0.0           # capacidade do depósito (L)
    fuel_init: float = 0.8        # fracção cheia no início
    tilt: float | None = None     # inclinação dos painéis (None = |latitude|)
    pv_hardened: bool = False     # estrutura anti-ciclone
    bat_climate: bool = False     # contentor de baterias isolado/climatizado
    label: str = ""

    def copy(self, **kw) -> "System":
        d = self.__dict__.copy(); d.update(kw)
        return System(**d)


# ───────────────────────────── geometria solar ─────────────────────────────
def solar_geometry(idx: pd.DatetimeIndex, utc: int, lat: float, lon: float, tilt: float):
    """cos(zénite) e cos(ângulo de incidência) num painel virado para o equador.
    A radiação horária é a média da hora anterior → usa-se o meio da hora."""
    t = idx - pd.Timedelta(hours=utc) - pd.Timedelta(minutes=30)
    doy = t.dayofyear.values.astype(float)
    hr = t.hour.values + t.minute.values / 60.0
    g = 2 * np.pi / 365.0 * (doy - 1 + (hr - 12) / 24)
    eqt = 229.18 * (0.000075 + 0.001868 * np.cos(g) - 0.032077 * np.sin(g)
                    - 0.014615 * np.cos(2 * g) - 0.040849 * np.sin(2 * g))
    dec = (0.006918 - 0.399912 * np.cos(g) + 0.070257 * np.sin(g) - 0.006758 * np.cos(2 * g)
           + 0.000907 * np.sin(2 * g) - 0.002697 * np.cos(3 * g) + 0.00148 * np.sin(3 * g))
    tst = hr * 60 + eqt + 4 * lon
    ha = np.radians(tst / 4 - 180)
    phi = np.radians(lat)
    cz = np.sin(phi) * np.sin(dec) + np.cos(phi) * np.cos(dec) * np.cos(ha)
    # painel orientado ao equador: trabalha-se com latitude/declinação “espelhadas”
    sgn = 1.0 if lat >= 0 else -1.0
    phi_a, dec_a, b = abs(phi), dec * sgn, np.radians(tilt)
    ci = np.sin(dec_a) * np.sin(phi_a - b) + np.cos(dec_a) * np.cos(ha) * np.cos(phi_a - b)
    return np.clip(cz, -1, 1), np.clip(ci, -1, 1)


def plane_of_array(w: pd.DataFrame, utc: int, lat: float, lon: float, tilt: float) -> np.ndarray:
    """Irradiância no plano dos painéis (W/m²), modelo isotrópico + atenuação por poeira."""
    cz, ci = solar_geometry(w.index, utc, lat, lon, tilt)
    ghi = w["shortwave_radiation"].values.astype(float)
    dif = w["diffuse_radiation"].values.astype(float) if "diffuse_radiation" in w else 0.35 * ghi
    dirh = w["direct_radiation"].values.astype(float) if "direct_radiation" in w else ghi - dif
    dni = np.where(cz > 0.087, dirh / np.maximum(cz, 0.087), 0.0).clip(0, 1100)
    b = np.radians(tilt)
    snow_ground = w["snow_depth"].values > 0.05 if "snow_depth" in w else np.zeros(len(w), bool)
    alb = np.where(snow_ground, 0.7, 0.2)
    poa = dni * np.clip(ci, 0, None) + dif * (1 + np.cos(b)) / 2 + ghi * alb * (1 - np.cos(b)) / 2
    poa = np.where(ghi <= 0, 0.0, poa)
    dust = np.clip(1 - 0.20 * w["aod_excess"].values, 0.6, 1.0)  # poeira acima do normal do mês
    return np.clip(poa * dust, 0, 1300)


# ───────────────────────────── componentes ─────────────────────────────
NOCT, GAMMA, PR_PV = 45.0, -0.0035, 0.88  # PR: cablagem, mismatch, inversor PV


def cell_temperature(poa, ta, v10):
    return ta + (NOCT - 20) * poa / 800.0 * 9.5 / (5.7 + 3.8 * np.clip(v10, 0, 30))


def _norm_cdf(x):
    return 0.5 * (1 + np.vectorize(math.erf)(x / math.sqrt(2)))


def pv_damage(gust, hardened: bool, intensity: float = 1.0):
    """Fracção da instalação PV danificada (curva de fragilidade lognormal, cumulativa).
    Mediana de colapso: estrutura comum ~42 m/s (150 km/h); anti-ciclone ~62 m/s (225 km/h)."""
    med = 62.0 if hardened else 42.0
    g = np.clip(np.asarray(gust, float) * intensity, 0.1, None)
    frac = _norm_cdf(np.log(g / med) / 0.15)
    frac = np.where(frac < 0.005, 0.0, frac)
    return np.maximum.accumulate(frac)


def snow_and_soiling(w: pd.DataFrame, poa, tilt: float, smart_maint: bool):
    """Cobertura de neve (0–1) e sujidade (0–1) hora a hora.
    smart_maint: técnico local limpa neve (9 h e 13 h) e lava painéis após poeira."""
    n = len(w)
    snowfall = w["snowfall"].values if "snowfall" in w else np.zeros(n)
    ta = w["temperature_2m"].values
    rain = w["precipitation"].values - snowfall * 0.7
    dust = w["dust"].values
    hours = w.index.hour.values
    sinb = math.sin(math.radians(tilt))
    S = np.zeros(n); D = np.zeros(n)
    s = 0.0; d = 0.02
    for t in range(n):
        # neve: 1 cm cobre o painel; desliza com sol/temperatura positiva (Marion et al., 2013)
        s = min(1.0, s + snowfall[t] / 1.0)
        if s > 0:
            if ta[t] > -1 and poa[t] > 120:
                s -= 0.25 * sinb
            elif ta[t] > 1:
                s -= 0.06
            s = max(0.0, s)
            if smart_maint and hours[t] in (9, 13) and snowfall[t] < 0.3:
                s = min(s, 0.05)
        # poeira: deposição proporcional à concentração; a chuva lava
        d += 0.002 / 24 + 1.5e-6 * dust[t]  # 0,2 %/dia de base; 1000 µg/m³ ≈ +3,6 %/dia
        if rain[t] >= 5:
            d = 0.0
        elif rain[t] >= 1:
            d *= 0.4
        if smart_maint and hours[t] == 7 and d > 0.04:
            d = 0.01
        d = min(d, 0.4)
        S[t] = s; D[t] = d
    return S, D


def wind_power(w: pd.DataFrame, kw: float, hub: float = 24.0):
    """Aerogerador pequeno: arranque 2,5 m/s, nominal 11 m/s, paragem de segurança a 20 m/s
    (média) ou 30 m/s (rajada), com religação apenas abaixo de 15 m/s."""
    n = len(w)
    v10 = w["wind_speed_10m"].values
    if "wind_speed_100m" in w:
        alpha = np.clip(np.log(np.maximum(w["wind_speed_100m"].values, 0.1) / np.maximum(v10, 0.1))
                        / math.log(10), 0.05, 0.35)
    else:
        alpha = np.full(n, 0.14)
    vh = v10 * (hub / 10.0) ** alpha
    gh = w["wind_gusts_10m"].values * (hub / 10.0) ** (alpha * 0.5)
    vin, vr = 2.5, 11.0
    curve = np.clip((vh ** 3 - vin ** 3) / (vr ** 3 - vin ** 3), 0, 1)
    stopped = np.zeros(n, bool); st = False
    for t in range(n):
        if not st and (vh[t] >= 20 or gh[t] >= 30):
            st = True
        elif st and vh[t] < 15 and gh[t] < 25:
            st = False
        stopped[t] = st
    p = np.where(stopped, 0.0, curve * kw)
    return p, vh, gh, stopped


def battery_thermal(ta, climate: bool, bat_kwh: float):
    """Temperatura da bateria e limites do BMS (LFP).
    - abaixo de 0 °C: carga proibida; 0–10 °C: carga a 30 %;
    - 45–55 °C: potência a 50 %; acima de 55 °C: BMS desliga.
    climate=True: contentor isolado com ventilação/aquecimento (consome energia auxiliar)."""
    n = len(ta); tb = np.zeros(n); aux = np.zeros(n)
    x = float(ta[0]) + 3
    for t in range(n):
        if climate:
            target = min(max(ta[t], 16.0), 30.0)
            x += (target - x) / 3.0
            aux[t] = bat_kwh * (0.0002 * max(ta[t] - 28, 0) + 0.00015 * max(12 - ta[t], 0))
        else:
            x += (ta[t] + 4.0 - x) / 6.0  # abrigo metálico simples, ganha calor
        tb[t] = x
    chg = np.select([tb < 0, tb < 10, tb <= 45, tb <= 55], [0.0, 0.3, 1.0, 0.5], 0.0)
    dis = np.select([tb < -20, tb < 0, tb <= 50, tb <= 60], [0.0, 0.6, 1.0, 0.5], 0.0)
    capf = np.clip(1 - 0.006 * np.clip(15 - tb, 0, None), 0.7, 1.0)
    return tb, chg, dis, capf, aux


def inverter_derate(ta, climate: bool):
    """Inversores reduzem potência acima de ~45 °C interno (perde ~5 %/°C até 65 °C)."""
    ti = (np.minimum(ta, 32) if climate else ta) + 6.0
    return np.clip(1 - (ti - 45) / 20.0, 0.0, 1.0), ti


def diesel_fuel(p_out, rated):
    """Consumo (L/h) — curva HOMER: 0,08415·P_nominal + 0,246·P_saída."""
    return 0.08415 * rated + 0.246 * p_out if p_out > 0 else 0.0


@dataclass
class Resource:
    poa: np.ndarray
    tcell: np.ndarray
    pv_base: np.ndarray       # kW disponíveis antes de neve/sujidade/danos
    damage: np.ndarray
    wind: np.ndarray
    v_hub: np.ndarray
    gust_hub: np.ndarray
    turb_stop: np.ndarray
    t_bat: np.ndarray
    chg_f: np.ndarray
    dis_f: np.ndarray
    cap_f: np.ndarray
    aux: np.ndarray
    inv_f: np.ndarray
    t_inv: np.ndarray
    extras: dict = field(default_factory=dict)


def scale_resource(unit: Resource, sys: System) -> Resource:
    """Reaproveita um recurso calculado para 1 kWp / 1 kW eólico / 1 kWh (optimização rápida)."""
    from dataclasses import replace
    return replace(unit, pv_base=unit.pv_base * sys.pv_kwp, wind=unit.wind * sys.wind_kw,
                   aux=unit.aux * sys.bat_kwh)


def resource(w: pd.DataFrame, site: dict, sys: System, intensity: float = 1.0) -> Resource:
    tilt = sys.tilt if sys.tilt is not None else round(abs(site["lat"]))
    tilt = max(tilt, 10)
    poa = plane_of_array(w, site["utc"], site["lat"], site["lon"], tilt)
    ta = w["temperature_2m"].values.astype(float)
    tc = cell_temperature(poa, ta, w["wind_speed_10m"].values)
    dmg = pv_damage(w["wind_gusts_10m"].values, sys.pv_hardened, intensity)
    pv = sys.pv_kwp * poa / 1000.0 * (1 + GAMMA * (tc - 25)) * PR_PV
    wp, vh, gh, stop = wind_power(w, sys.wind_kw)
    tb, chg, dis, capf, aux = battery_thermal(ta, sys.bat_climate, sys.bat_kwh)
    invf, ti = inverter_derate(ta, sys.bat_climate)
    return Resource(poa, tc, np.clip(pv, 0, None), dmg, wp, vh, gh, stop, tb, chg, dis, capf, aux, invf, ti,
                    extras=dict(tilt=tilt))
