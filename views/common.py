"""Cálculos partilhados entre separadores (com cache)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from resilia.data import event_window, load_site, sim_slice
from resilia.engine import CONVENTIONAL, RESILIA, metrics, simulate
from resilia.loads import Community
from resilia.physics import System
from resilia.sites import EVENTS, SITES


def community_for(key: str) -> Community:
    s = SITES[key]
    return Community(households=s["households"], people=s["people"], water_head_m=s["water_head_m"],
                     heat_sens=s["heat_sens"], cold_sens=s["cold_sens"])


def default_systems(key: str):
    d = SITES[key]["default_sys"]
    hw = dict(pv_kwp=d["pv"], bat_kwh=d["bat"], inv_kw=d["inv"])
    return System(**hw), System(**hw, pv_hardened=True, bat_climate=True)


@st.cache_data(show_spinner="A simular os 9 eventos extremos dos 3 países…")
def all_events_summary() -> pd.DataFrame:
    rows = []
    for key, s in SITES.items():
        df = load_site(key)
        comm = community_for(key)
        sc, sr = default_systems(key)
        for ek, e in EVENTS.items():
            if e["site"] != key:
                continue
            w = sim_slice(df, event_window(df, ek))
            oc = simulate(w, s, sc, comm, CONVENTIONAL)
            orr = simulate(w, s, sr, comm, RESILIA)
            m = (oc["fase"] == "evento").values
            a, b = metrics(oc, m), metrics(orr, m)
            rows.append(dict(
                site=key, ev=ek, país=s["country"], local=s["name"], evento=e["name"], tipo=e["kind"],
                conv_crit=a["crit_pct"], res_crit=b["crit_pct"],
                conv_out=a["crit_out_h"], res_out=b["crit_out_h"],
                conv_black=a["blackout_h"], res_black=b["blackout_h"],
                conv_essmin=a["essmin_pct"], res_essmin=b["essmin_pct"],
                conv_water=a["water_pct"], res_water=b["water_pct"],
                conv_idx=a["index"], res_idx=b["index"],
                conv_dark=a["house_dark_h"], res_dark=b["house_dark_h"],
            ))
    return pd.DataFrame(rows)


def pct(x):
    return f"{x:.0f}%"


def hours(x):
    return f"{int(round(x))} h"
