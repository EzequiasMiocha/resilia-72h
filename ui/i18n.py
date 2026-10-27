"""Interface bilingue (Português / English).

Uso:  T("texto em português", "text in English")
O idioma activo fica em st.session_state["lang"] ("PT" ou "EN").
"""
from __future__ import annotations

import streamlit as st

from resilia.sites import EVENTS, EVENTS_EN, SITES, SITES_EN

MONTHS = {"PT": ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro",
                 "Outubro", "Novembro", "Dezembro"],
          "EN": ["January", "February", "March", "April", "May", "June", "July", "August", "September",
                 "October", "November", "December"]}
WEEKDAYS = {"PT": ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"],
            "EN": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]}


def lang() -> str:
    return st.session_state.get("lang", "PT") or "PT"


def en() -> bool:
    return lang() == "EN"


def T(pt: str, en_: str) -> str:
    return en_ if en() else pt


def num(x, n=0) -> str:
    """Número no formato do idioma (PT: 1 234,5 · EN: 1,234.5)."""
    s = f"{x:,.{n}f}"
    return s if en() else s.replace(",", " ").replace(".", ",")


def month_short(m: int) -> str:
    return MONTHS[lang()][m - 1][:3]


def date_long(ts) -> str:
    L = lang()
    if L == "EN":
        return f"{WEEKDAYS[L][ts.dayofweek]}, {ts.day} {MONTHS[L][ts.month - 1]} · {ts.hour:02d}:00"
    return f"{WEEKDAYS[L][ts.dayofweek]}, {ts.day} de {MONTHS[L][ts.month - 1]} · {ts.hour:02d}:00"


def site(key: str, field: str) -> str:
    if en() and field in SITES_EN.get(key, {}):
        return SITES_EN[key][field]
    return SITES[key][field]


def event(key: str, field: str = "name") -> str:
    if en() and field in EVENTS_EN.get(key, {}):
        return EVENTS_EN[key][field]
    return EVENTS[key][field]


PHASE = {"preparação": ("antes (aviso)", "before (warning)"), "evento": ("evento", "event"),
         "recuperação": ("recuperação", "recovery"), "normal": ("normal", "normal"), "alerta": ("alerta", "alert")}


def phase(p: str) -> str:
    a, b = PHASE.get(p, (p, p))
    return T(a, b)
