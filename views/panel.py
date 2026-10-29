"""Dados em cache e painel lateral (a aldeia e o sistema), partilhados pelas páginas."""
from types import SimpleNamespace

import streamlit as st

from resilia import model as M
from ui.i18n import T, num


@st.cache_data(show_spinner="A carregar 11 anos de dados reais de Mabote… / Loading 11 years of real Mabote data…")
def get_resource():
    df = M.load_weather()
    return M.resource(df), M.representative_days(df)


@st.cache_data(show_spinner=False)
def get_demand(village: tuple):
    res, _ = get_resource()
    return M.demand(res.index, res["t"].values, M.Village(*village))


@st.cache_data(show_spinner=f"A testar {M.N_SYSTEMS} sistemas contra 11 anos de dias reais… / "
                            f"Testing {M.N_SYSTEMS} systems against 11 years of real days…",
               persist="disk")
def get_long_term(village: tuple, version: int = 3):
    res, _ = get_resource()
    return M.long_term(res, get_demand(village)["total"].values)


def presets(village: tuple):
    tab = get_long_term(village)
    return M.choose(tab, M.LEVELS["recommended"])


def _set_system(pv, bat):
    st.session_state["sys_pv"], st.session_state["sys_bat"] = int(pv), int(bat)


def build(show_system: bool = True):
    """Desenha o painel lateral e devolve o contexto (dados, procura, sistema)."""
    res, days = get_resource()
    with st.sidebar:
        st.markdown(f"### {T('A aldeia', 'The village')}")
        hh = st.slider(T("Número de famílias", "Number of households"), 50, 500, 200, 10, key="v_hh")
        health = st.checkbox(T("Centro de saúde", "Health centre"), True, key="v_health")
        water = st.checkbox(T("Bomba de água", "Water pump"), True, key="v_water")
        school = st.checkbox(T("Escola", "School"), True, key="v_school")
        mill = st.checkbox(T("Moagem", "Grain mill"), True, key="v_mill")
        growth = st.slider(T("Crescimento futuro da procura (%)", "Future demand growth (%)"), 0, 50, 0, 5, key="v_growth",
                           help=T("Para planear: quanto vai crescer o consumo nos próximos anos.",
                                  "For planning: how much consumption will grow in the coming years."))
        village = (hh, health, school, water, mill, float(growth))
        dem = get_demand(village)
        st.caption(T(f"Procura média: **{num(dem['total'].sum() / (len(dem) / 24))} kWh/dia** "
                     f"(varia de hora para hora e de dia para dia).",
                     f"Average demand: **{num(dem['total'].sum() / (len(dem) / 24))} kWh/day** "
                     f"(varies hour by hour and day by day)."))

        sysd = None
        if show_system:
            st.markdown(f"### {T('O sistema', 'The system')}")
            choice = presets(village)
            e, r = choice["efficient"], choice["resilient"]
            st.session_state.setdefault("sys_pv", int(r["pv"]))
            st.session_state.setdefault("sys_bat", int(r["bat"]))
            b1, b2 = st.columns(2)
            with b1:
                st.button(T("Só eficiência", "Efficiency only"), width="stretch", on_click=_set_system,
                          args=(e["pv"], e["bat"]), help=T("O mais barato para o dia médio.",
                                                           "The cheapest system for the average day."))
            with b2:
                st.button(T("Resiliente", "Resilient"), width="stretch", type="primary", on_click=_set_system,
                          args=(r["pv"], r["bat"]), help=T("O mais barato que aguenta os dias maus.",
                                                           "The cheapest system that withstands bad days."))
            pv = st.slider(T("Painéis solares (kWp)", "Solar panels (kWp)"), 0, 120, step=5, key="sys_pv")
            bat = st.slider(T("Baterias (kWh)", "Batteries (kWh)"), 0, 500, step=10, key="sys_bat")
            sysd = M.System(pv=pv, bat=bat)
            cost = (pv * M.COST["pv"] + bat * M.COST["bat"]) / 1000
            st.caption(T(f"Investimento estimado: **{num(cost)} mil USD**", f"Estimated investment: **{num(cost)}k USD**"))
    return SimpleNamespace(res=res, days=days, village=village, dem=dem, system=sysd)
