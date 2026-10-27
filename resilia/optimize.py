"""Dimensionamento robusto: o sistema mais barato que sobrevive a TODOS os eventos extremos do local.

Compara duas filosofias:
  • «Só eficiência» — mais barato que cumpre ≥95 % da procura em semanas normais (estratégia convencional);
  • «RESILIA robusto» — mais barato que, no PIOR dos eventos históricos, mantém ≥ X % das cargas críticas,
    ≥ Y % das essenciais e ≥ Z % da água (estratégia inteligente).
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from .data import EVENT_H, event_window, sim_slice, typical_window
from .economics import capex, lcoe
from .engine import CONVENTIONAL, RESILIA, Strategy, metrics, simulate
from .loads import Community, build_demand, severe_flags
from .physics import System, resource, scale_resource, snow_and_soiling
from .sites import EVENTS, SITES


def typical_weeks(df: pd.DataFrame, year: int) -> list[pd.DataFrame]:
    """Quatro semanas representativas (uma por trimestre, sol mediano) para estimar o ano."""
    out = []
    for q in (1, 4, 7, 10):
        m = df[(df.index.year == year) & (df.index.month >= q) & (df.index.month < q + 3)]
        s = m["shortwave_radiation"].rolling(168).sum().iloc[::24].dropna()
        end = (s - s.median()).abs().idxmin()
        out.append(df.loc[end - pd.Timedelta(hours=167):end].copy())
    return out


class Case:
    """Janela meteorológica pré-processada (recurso unitário, procura, neve/poeira)."""

    def __init__(self, w, site, comm, hardened, climate, smart_maint):
        self.w = w
        unit = System(pv_kwp=1, bat_kwh=1, wind_kw=1, pv_hardened=hardened, bat_climate=climate)
        self.unit = resource(w, site, unit)
        sev = severe_flags(w)
        ev = (w["fase"].values == "evento") if "fase" in w else sev
        self.dem = build_demand(w, comm, sev | ev)
        self.ss = snow_and_soiling(w, self.unit.poa, self.unit.extras["tilt"], smart_maint)
        self.event_mask = (w["fase"] == "evento").values if "fase" in w else None

    def run(self, site, sys, comm, strat, **kw):
        res = scale_resource(self.unit, sys)
        return simulate(self.w, site, sys, comm, strat, res=res, ss=self.ss, dem=self.dem, **kw)


def optimise(df: pd.DataFrame, site_key: str, comm: Community, targets: dict,
             grid: dict | None = None, lead_h: int = 48, progress=None) -> dict:
    site = SITES[site_key]
    evs = [k for k, e in EVENTS.items() if e["site"] == site_key]
    year = 2024
    grid = grid or dict(pv=[25, 35, 45, 60, 80, 100, 125], bat=[60, 100, 150, 200, 260, 330, 420],
                        diesel=[0, 15], wind=[0])
    smart = Strategy(True, lead_h, True, "RESILIA")

    ev_cases_h = [Case(sim_slice(df, event_window(df, k)), site, comm, True, True, True) for k in evs]
    wk = typical_weeks(df, year)
    wk_smart = [Case(x, site, comm, True, True, True) for x in wk]
    wk_conv = [Case(x, site, comm, False, False, False) for x in wk]
    ev_cases_c = [Case(sim_slice(df, event_window(df, k)), site, comm, False, False, False) for k in evs]

    rows = []
    combos = list(itertools.product(grid["pv"], grid["bat"], grid["diesel"], grid["wind"]))
    for i, (pv, bat, dg, wd) in enumerate(combos):
        if progress:
            progress((i + 1) / len(combos))
        inv = max(10.0, round(0.45 * pv, 0))
        for kind in ("robusto", "eficiente"):
            smart_k = kind == "robusto"
            sys = System(pv_kwp=pv, bat_kwh=bat, inv_kw=inv, wind_kw=wd, diesel_kw=dg,
                         fuel_l=200.0 if dg else 0.0, fuel_init=0.8,
                         pv_hardened=smart_k, bat_climate=smart_k)
            if kind == "eficiente" and dg:
                continue
            strat = smart if smart_k else CONVENTIONAL
            cases_ev = ev_cases_h if smart_k else ev_cases_c
            cases_wk = wk_smart if smart_k else wk_conv
            em = []
            for cs in cases_ev:
                o = cs.run(site, sys, comm, strat)
                em.append(metrics(o, cs.event_mask))
            served = dem = fuel = 0.0
            for cs in cases_wk:
                o = cs.run(site, sys, comm, strat, fuel_resupply=True)
                mm = metrics(o)
                served += mm["dem_kwh"] - mm["ens_kwh"]; dem += mm["dem_kwh"]; fuel += mm["diesel_L"]
            scale = 365 / 28
            cx = sum(capex(sys, comm.households, smart_k).values())
            ec = lcoe(sys, cx, served * scale, fuel * scale, site["diesel_usd_l"])
            row = dict(
                tipo=kind, pv=pv, bat=bat, diesel=dg, wind=wd, inv=inv, capex=cx,
                lcoe=ec["lcoe"], annual=ec["annual_cost"], served_y=served * scale, fuel_y=fuel * scale,
                normal_pct=100 * served / max(dem, 1e-9),
                worst_crit=min(m["crit_pct"] for m in em), worst_ess=min(m["essmin_pct"] for m in em),
                worst_water=min(m["water_pct"] for m in em), worst_index=min(m["index"] for m in em),
                worst_longest=max(m["crit_longest_h"] for m in em),
                total_out=sum(m["crit_out_h"] for m in em),
            )
            for k, m in zip(evs, em):
                row[f"crit_{k}"] = m["crit_pct"]
                row[f"out_{k}"] = m["crit_out_h"]
            rows.append(row)
    d = pd.DataFrame(rows)
    rob = d[d.tipo == "robusto"]
    ok = rob[(rob.worst_crit >= targets["crit"]) & (rob.worst_ess >= targets["ess"])
             & (rob.worst_water >= targets["water"]) & (rob.normal_pct >= 95)]
    best = (ok.sort_values("annual").iloc[0] if len(ok)
            else rob.sort_values(["worst_crit", "worst_ess", "annual"], ascending=[False, False, True]).iloc[0])
    ren = rob[rob.diesel == 0]
    ren_ok = ok[ok.diesel == 0]
    renewable = (ren_ok.sort_values("annual").iloc[0] if len(ren_ok)
                 else ren.sort_values(["worst_crit", "worst_ess", "annual"], ascending=[False, False, True]).iloc[0])
    eff = d[(d.tipo == "eficiente") & (d.normal_pct >= 95)]
    effb = eff.sort_values("annual").iloc[0] if len(eff) else d[d.tipo == "eficiente"].sort_values("normal_pct").iloc[-1]
    return dict(table=d, best=best, efficient=effb, renewable=renewable, renewable_ok=len(ren_ok) > 0,
                feasible=len(ok) > 0, events=evs)


def system_from_row(r, robust: bool) -> System:
    return System(pv_kwp=float(r["pv"]), bat_kwh=float(r["bat"]), inv_kw=float(r["inv"]),
                  wind_kw=float(r["wind"]), diesel_kw=float(r["diesel"]),
                  fuel_l=200.0 if r["diesel"] else 0.0, fuel_init=0.8,
                  pv_hardened=robust, bat_climate=robust,
                  label="RESILIA robusto" if robust else "Só eficiência")
