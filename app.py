"""RESILIA 72H — energia que não apaga quando o clima aperta / power that stays on when the weather turns.

Executar / Run:  streamlit run app.py
"""
from pathlib import Path

import streamlit as st

from ui import style
from ui.i18n import T

_LOGO = Path(__file__).with_name("logo.png")
st.set_page_config(page_title="RESILIA 72H", page_icon=str(_LOGO) if _LOGO.exists() else ":material/bolt:",
                   layout="wide", initial_sidebar_state="expanded")
style.inject()
style.lang_switch()


def _explore(view):
    """Página de exploração: painel lateral + contexto partilhado."""
    def page():
        from views import controls
        style.brand()
        ctx = controls.build()
        view.render(ctx)
        style.footer()
    page.__name__ = f"page_{view.__name__.split('.')[-1]}"
    return page


def pitch_page():
    from views import pitch
    style.hide_sidebar()
    pitch.render()


def make_pages():
    from views import business, lab, method, optimizer, scale, simulator
    return [
        st.Page(pitch_page, title=T("Apresentação", "Pitch"), icon=":material/co_present:",
                url_path="apresentacao", default=True),
        st.Page(_explore(simulator), title=T("Simulador 72 h", "72-h Simulator"), icon=":material/thunderstorm:",
                url_path="simulador"),
        st.Page(_explore(lab), title=T("Laboratório do clima", "Climate lab"), icon=":material/science:",
                url_path="laboratorio"),
        st.Page(_explore(optimizer), title=T("Dimensionar", "System sizing"), icon=":material/tune:",
                url_path="dimensionar"),
        st.Page(_explore(scale), title=T("3 países", "3 countries"), icon=":material/public:", url_path="paises"),
        st.Page(_explore(business), title=T("Negócio", "Business"), icon=":material/payments:", url_path="negocio"),
        st.Page(_explore(method), title=T("Método e dados", "Method & data"), icon=":material/menu_book:",
                url_path="metodo"),
    ]


st.navigation(make_pages(), position="top").run()
