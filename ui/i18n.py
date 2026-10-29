"""Interface bilingue (Português / English).

Uso:  T("texto em português", "text in English")
O idioma activo fica em st.session_state["lang"] ("PT" ou "EN").
"""
from __future__ import annotations

import streamlit as st

MONTHS = {"PT": ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro",
                 "Outubro", "Novembro", "Dezembro"],
          "EN": ["January", "February", "March", "April", "May", "June", "July", "August", "September",
                 "October", "November", "December"]}


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


def date_txt(ts) -> str:
    m = MONTHS[lang()][ts.month - 1]
    return f"{ts.day} {m} {ts.year}" if en() else f"{ts.day} de {m} de {ts.year}"


DAY_LABELS = {
    "sunny": ("Dia de sol", "Sunny day"),
    "partly": ("Parcialmente nublado", "Partly cloudy"),
    "cloudy": ("Dia nublado", "Cloudy day"),
    "storm": ("Chuva forte", "Heavy rain"),
    "hot": ("Dia muito quente", "Very hot day"),
}


def day_label(k: str) -> str:
    return T(*DAY_LABELS[k])


def verdict_txt(v: str) -> str:
    return {"ok": T("RESILIENTE", "RESILIENT"), "partial": T("PARCIALMENTE RESILIENTE", "PARTIALLY RESILIENT"),
            "fragile": T("FRÁGIL", "FRAGILE")}[v]
