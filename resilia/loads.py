"""Procura da comunidade construída de baixo para cima, com níveis de prioridade.

Níveis (tiers):
  crítica   — centro de saúde, comunicações/alerta, abrigo de evacuação, bombagem de emergência
  essencial — casas (luz, telemóveis, rádio), iluminação pública, escola, bombagem de água
  produtiva — moagem, comércio e frio (pode ser adiada ou cortada de forma planeada)

A procura reage ao clima: calor → ventoinhas, frio da cadeia de vacinas, mais água;
tempestade → abrigo na escola, carregamento de telemóveis, urgências; frio → iluminação e
aquecimento na clínica.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

# perfis horários base (kW) — 24 valores, hora local
HEALTH = [0.38] * 6 + [0.45, 0.6] + [0.9] * 5 + [0.8] * 4 + [0.7] + [0.7] * 4 + [0.45] * 2  # ≈15 kWh/d
HOUSE_W = [6] * 6 + [12, 10] + [6] * 9 + [20] + [35] * 4 + [20, 10]                          # ≈0,3 kWh/d
HOUSE_MIN_W = [1] * 18 + [9] * 5 + [1]      # modo essencial: 3 lâmpadas LED + telemóvel ≈ 64 Wh/d
SCHOOL = [0.1] * 8 + [1.0] * 8 + [0.1] * 8
MILL_H = {8, 9, 15}            # horas de moagem (motor)
WATER_PROFILE = np.array([0.5] * 5 + [1.5, 2.5, 2.0, 1.5, 1.2, 1.0, 1.0, 1.2, 1.0, 1.0, 1.2, 1.5, 2.0, 1.5, 0.8]
                         + [0.5] * 4)
WATER_PROFILE = WATER_PROFILE / WATER_PROFILE.sum()

PHONE_KWH = 0.012   # energia por carga de telemóvel (inclui perdas)
LITRES_PERSON = 20  # necessidade diária (L/pessoa); padrão Sphere de emergência = 15 L


@dataclass
class Community:
    households: int = 200
    people: int = 1400
    health: bool = True
    school: bool = True
    mill: bool = True
    commerce: bool = True
    water_head_m: float = 45.0
    heat_sens: float = 0.6
    cold_sens: float = 0.0


@dataclass
class Demand:
    crit: np.ndarray
    ess_full: np.ndarray
    ess_min: np.ndarray       # modo essencial (contadores inteligentes limitam a luz + telemóvel)
    prod: np.ndarray
    water_m3: np.ndarray      # água pedida pela população (m³/h)
    pump_kw: float
    kwh_m3: float
    tank_m3: float
    parts: pd.DataFrame       # decomposição por serviço (kW), para gráficos
    shelter: np.ndarray


def build_demand(w: pd.DataFrame, c: Community, severe: np.ndarray) -> Demand:
    n = len(w)
    h = w.index.hour.values
    wd = w.index.dayofweek.values
    ta = w["temperature_2m"].values
    hot = np.clip(ta - 32, 0, 15)          # °C acima de 32
    cold = np.clip(5 - ta, 0, 20)          # °C abaixo de 5
    sev = severe.astype(float)

    health = np.array(HEALTH)[h] * c.health
    # urgências na tempestade (+30 %); ventilação e frio de vacinas no calor; aquecedor no frio
    health = health * (1 + 0.30 * sev) + c.health * (0.03 * hot * c.heat_sens + 0.04 * cold * c.cold_sens)
    comms = np.full(n, 0.25) + 0.25 * sev                        # rádio, repetidor, carregamento
    shelter = sev > 0
    school_norm = np.where(wd < 5, np.array(SCHOOL)[h], 0.1) * c.school
    shelter_load = np.where((h >= 18) | (h < 6), 0.5, 0.3) * c.school   # abrigo de evacuação

    house_w = np.array(HOUSE_W)[h] * (1 + 0.25 * sev) * (1 + 0.12 * cold / 5 * c.cold_sens)
    fans = np.where((h >= 11) | (h < 6), 2.0 * hot * c.heat_sens, 0.6 * hot * c.heat_sens)
    houses = c.households * (house_w + fans) / 1000.0
    houses_min = c.households * np.array(HOUSE_MIN_W)[h] / 1000.0
    lamps = max(5, c.households // 10)
    street = np.where((h >= 18) | (h < 5), 0.04 * lamps, 0.0)

    scale = c.households / 200.0
    mill = np.where(np.isin(h, list(MILL_H)), 5.5 * scale, 0.0) * c.mill * (1 - 0.7 * sev)
    commerce = (np.where((h >= 7) & (h <= 20), 0.8, 0.5) * scale * (1 + 0.03 * hot * c.heat_sens)
                * c.commerce)

    # água: necessidade da população (m³/h); a bomba enche um depósito
    need_day = c.people * LITRES_PERSON / 1000.0
    water = need_day * WATER_PROFILE[h] * (1 + 0.025 * hot * c.heat_sens) * (1 + 0.10 * sev)
    kwh_m3 = 9.81 * c.water_head_m / 3600.0 / 0.45      # bomba submersível η≈45 %
    pump_kw = max(1.5, round(need_day * 2.0 / 6.0 * kwh_m3, 1))   # bombeia 2 dias de água em 6 h

    crit = health + comms + np.where(shelter, shelter_load, 0.0)
    ess_full = houses + street + np.where(shelter, 0.0, school_norm)
    ess_min = houses_min + 0.5 * street
    prod = mill + commerce

    parts = pd.DataFrame({
        "Centro de saúde": health, "Comunicações e alerta": comms,
        "Escola / abrigo": np.where(shelter, shelter_load, school_norm),
        "Casas": houses, "Iluminação pública": street,
        "Moagem": mill, "Comércio e frio": commerce,
    }, index=w.index)
    return Demand(crit, ess_full, ess_min, prod, water, pump_kw, kwh_m3, need_day * 1.5, parts, shelter)


def severe_flags(w: pd.DataFrame) -> np.ndarray:
    """Condições meteorológicas severas (critério genérico, válido para qualquer local)."""
    rain24 = w["precipitation"].rolling(24, min_periods=1).sum().values
    snow24 = (w["snowfall"].rolling(24, min_periods=1).sum().values if "snowfall" in w
              else np.zeros(len(w)))
    tmax24 = w["temperature_2m"].rolling(24, min_periods=1).max().values
    sev = ((w["wind_gusts_10m"].values >= 20) | (rain24 >= 50) | (snow24 >= 5)
           | (tmax24 >= 42) | (w["aod_excess"].values >= 0.5))
    return sev
