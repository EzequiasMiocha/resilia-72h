"""Custos, LCOE e valor económico da resiliência."""
from __future__ import annotations

from .physics import System
from .sites import COSTS, VOLL


def crf(i: float, n: int) -> float:
    return i * (1 + i) ** n / ((1 + i) ** n - 1)


def capex(sys: System, households: int, smart: bool, c: dict = COSTS) -> dict:
    items = {
        "Solar fotovoltaico": sys.pv_kwp * (c["pv_usd_kwp"] + (c["pv_hardening_usd_kwp"] if sys.pv_hardened else 0)),
        "Baterias LFP": sys.bat_kwh * c["bat_usd_kwh"],
        "Inversor/carregador": sys.inv_kw * c["inv_usd_kw"],
        "Aerogerador": sys.wind_kw * c["wind_usd_kw"],
        "Gerador de reserva": sys.diesel_kw * c["diesel_usd_kw"] + (sys.fuel_l * 1.5 if sys.diesel_kw else 0),
        "Contentor climatizado": (c["bat_climate_fixed"] + c["bat_climate_usd_kwh"] * sys.bat_kwh) if sys.bat_climate else 0.0,
        "Controlo inteligente RESILIA": (c["smart_fixed"] + c["smart_usd_household"] * households) if smart else 0.0,
    }
    base = sum(items.values())
    items["Engenharia e logística"] = base * c["soft_costs"]
    items = {k: v for k, v in items.items() if v > 0}
    return items


def lcoe(sys: System, capex_total: float, served_kwh_y: float, diesel_L_y: float, diesel_price: float,
         c: dict = COSTS) -> dict:
    i, n = c["discount"], c["project_life_y"]
    f = crf(i, n)
    om = c["om_frac"] * capex_total
    fuel = diesel_L_y * diesel_price
    repl = sys.bat_kwh * c["bat_usd_kwh"] * 0.6 / (1 + i) ** c["bat_life_y"] * f  # substituição a meio
    annual = capex_total * f + om + fuel + repl
    return dict(annual_cost=annual, om=om, fuel_cost=fuel, repl=repl,
                lcoe=annual / max(served_kwh_y, 1.0), npc=annual / f)


def voll_cost(m: dict, v: dict = VOLL) -> float:
    """Custo social da energia não servida (USD) segundo o valor por nível de prioridade."""
    return m["ens_crit"] * v["critica"] + m["ens_ess"] * v["essencial"] + m["ens_prod"] * v["produtiva"]
