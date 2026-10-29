"""RESILIA — mini-rede solar resiliente e eficiente para Mabote (Inhambane).

Executar / Run:  streamlit run app.py
"""
from pathlib import Path

import streamlit as st

from ui import style
from ui.i18n import T

_LOGO = Path(__file__).with_name("logo.png")
st.set_page_config(page_title="RESILIA", page_icon=str(_LOGO) if _LOGO.exists() else ":material/solar_power:",
                   layout="wide", initial_sidebar_state="expanded")
style.inject()
style.lang_switch()


def pitch_page():
    from views import pitch
    style.hide_sidebar()
    pitch.render()


def solar_page():
    from views import panel, solar
    style.brand()
    solar.render(panel.build(show_system=True))
    style.footer()


def simulator_page():
    from views import panel, simulator
    style.brand()
    simulator.render(panel.build(show_system=True))
    style.footer()


def sizing_page():
    from views import panel, sizing
    style.brand()
    sizing.render(panel.build(show_system=False))
    style.footer()


def method_page():
    from views import method
    style.hide_sidebar()
    style.brand()
    method.render()
    style.footer()


st.navigation([
    st.Page(pitch_page, title=T("Apresentação", "Pitch"), icon=":material/co_present:", url_path="apresentacao", default=True),
    st.Page(solar_page, title=T("Energia solar", "Solar energy"), icon=":material/wb_sunny:", url_path="energia-solar"),
    st.Page(simulator_page, title=T("Simulador 24 h", "24-h simulator"), icon=":material/solar_power:", url_path="simulador"),
    st.Page(sizing_page, title=T("Dimensionamento", "System sizing"), icon=":material/tune:", url_path="dimensionamento"),
    st.Page(method_page, title=T("Metodologia", "Methodology"), icon=":material/functions:", url_path="metodologia"),
], position="top").run()
