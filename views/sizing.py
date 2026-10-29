"""Dimensionamento a longo prazo: o sistema mais barato que é resiliente (aguenta os dias maus) e eficiente."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from resilia import model as M
from ui import charts
from ui.i18n import T, cut_txt, day_label, num
from ui.style import C, card, explain, page_header

from .panel import get_long_term, get_year

LEVEL_TXT = {"basic": ("Básico", "Basic"), "recommended": ("Recomendado", "Recommended"), "maximum": ("Máximo", "Maximum")}
VCOL = {"ok": "#16A34A", "partial": "#B45309", "fragile": C["red"]}


def _use(r):
    st.session_state["sys_pv"], st.session_state["sys_bat"] = int(r["pv"]), int(r["bat"])
    st.session_state["sz_msg"] = True


def render(ctx):
    page_header(T("Dimensionamento", "System sizing"),
                T("Que sistema instalar para os próximos anos?", "Which system to install for the years ahead?"),
                T(f"Testamos {M.N_SYSTEMS} combinações de painéis solares e baterias em milhares de dias reais de Mabote, "
                  "com sol, nuvens, chuva e calor. «Só eficiência» é o mais barato para o dia médio. «Resiliente» é o mais barato que também "
                  "aguenta os dias maus.",
                  f"We test {M.N_SYSTEMS} combinations of solar panels and batteries on thousands of real Mabote days, "
                  "with sun, clouds, rain and heat. “Efficiency only” is the cheapest for the average day. “Resilient” is the cheapest that also "
                  "withstands the bad days."))

    st.session_state.setdefault("sz_level", "recommended")
    lv = st.segmented_control(T("Nível de protecção", "Protection level"), list(M.LEVELS), key="sz_level",
                              format_func=lambda k: T(*LEVEL_TXT[k]))
    lv = lv or "recommended"
    L = M.LEVELS[lv]
    st.caption(T(f"Exigência: no máximo {num(L['risk'], 1)} % de energia em falta (média), {num(L['bad'])} dias maus por ano "
                 f"(> 10 % em falta) e {num(L['autonomy'])} h de autonomia da bateria.",
                 f"Requirement: at most {num(L['risk'], 1)} % energy missing (average), {num(L['bad'])} bad days per year "
                 f"(> 10 % missing) and {num(L['autonomy'])} h of battery autonomy."))

    tab = get_long_term(ctx.village)

    def _imp(x):
        return get_year(ctx.village, float(x["pv"]), float(x["bat"]))[1]

    ch = M.choose(tab, L)
    e, r = ch["efficient"], ch["resilient"]
    if not ch["feasible"]:
        st.markdown(f'<div class="warnbox">{T("Nenhum sistema da grelha cumpre este nível. A mostrar o mais próximo.", "No system in the grid meets this level. Showing the closest one.")}</div>',
                    unsafe_allow_html=True)

    st.markdown(f"#### {T('O sistema recomendado', 'The recommended system')}")
    a, b, d = st.columns(3)
    with a:
        card(T("Painéis solares", "Solar panels"), f"{num(r['pv'])} kWp",
             T(f"≈ {round(r['pv'] * 1000 / 550)} painéis de 550 W", f"≈ {round(r['pv'] * 1000 / 550)} panels of 550 W"), C["solar"])
    with b:
        card(T("Baterias", "Batteries"), f"{num(r['bat'])} kWh",
             T(f"autonomia {num(r['autonomy'])} h sem sol", f"{num(r['autonomy'])} h autonomy without sun"), C["bat"])
    with d:
        card(T("Investimento", "Investment"), f"{num(r['cost'] / 1000)} {T('mil USD', 'k USD')}",
             T(f"+{num(100 * (r['cost'] / e['cost'] - 1))} % face ao «só eficiência»",
               f"+{num(100 * (r['cost'] / e['cost'] - 1))} % vs “efficiency only”"), C["red"])
    st.button(T("Usar este sistema no simulador", "Use this system in the simulator"), type="primary",
              icon=":material/check_circle:", on_click=_use, args=(r,))
    if st.session_state.pop("sz_msg", False):
        st.success(T("Sistema aplicado. Abra o «Simulador 24 h» no menu do topo.", "System applied. Open the “24-hour simulator” in the top menu."))

    st.markdown(f"#### {T('Só eficiência vs resiliente (média por ano)', 'Efficiency only vs resilient (yearly average)')}")
    rows = [
        (T("Painéis / baterias", "Panels / batteries"), lambda x: f"{num(x['pv'])} kWp · {num(x['bat'])} kWh"),
        (T("Investimento estimado", "Estimated investment"), lambda x: f"{num(x['cost'])} USD"),
        (T("Energia em falta (média)", "Energy missing (average)"), lambda x: f"{num(x['risk'], 2)} %"),
        (T("Dias maus por ano (> 10 % em falta)", "Bad days per year (> 10 % missing)"), lambda x: num(x["bad_days"], 1)),
        (T("Horas com interrupção por ano", "Hours with interruption per year"), lambda x: f"{num(x['hours'])} h"),
        (T("Autonomia da bateria", "Battery autonomy"), lambda x: f"{num(x['autonomy'])} h"),
        (T("Excedente solar (livre para novos usos)", "Solar surplus (free for new uses)"), lambda x: f"{num(x['waste'])} %"),
        (T("Custo da energia em 20 anos", "Energy cost over 20 years"), lambda x: f"{num(_imp(x)['lcoe'], 2)} USD/kWh"),
        (T("CO₂ evitado face ao gasóleo", "CO₂ avoided vs diesel"), lambda x: f"{num(_imp(x)['co2_t'])} t/{T('ano', 'yr')}"),
    ]
    st.table(pd.DataFrame({T("Só eficiência", "Efficiency only"): [f(e) for _, f in rows],
                           T("Resiliente (recomendado)", "Resilient (recommended)"): [f(r) for _, f in rows]},
                          index=[n for n, _ in rows]))
    explain(T("Conclusão:", "Conclusion:"),
            T(f"o sistema «só eficiência» é o mais barato, mas tem <b>{num(e['bad_days'])} dias maus por ano</b> e "
              f"<b>{num(e['hours'])} horas sem energia</b>. O sistema resiliente custa mais "
              f"{num(100 * (r['cost'] / e['cost'] - 1))} % e reduz para <b>{num(r['bad_days'], 1)} dias maus</b> e "
              f"<b>{num(r['hours'])} horas</b> por ano. É o mais barato que cumpre o nível de protecção, por isso é também eficiente.",
              f"the “efficiency only” system is the cheapest, but it has <b>{num(e['bad_days'])} bad days per year</b> and "
              f"<b>{num(e['hours'])} hours without power</b>. The resilient system costs {num(100 * (r['cost'] / e['cost'] - 1))} % "
              f"more and brings this down to <b>{num(r['bad_days'], 1)} bad days</b> and <b>{num(r['hours'])} hours</b> a year. "
              "It is the cheapest system that meets the protection level, so it is also efficient."))

    l, rr = st.columns([3, 2])
    with l:
        st.plotly_chart(charts.sizing_map(tab, e, r, T("Investimento × dias maus por ano (cada ponto é um sistema)",
                                                       "Investment × bad days per year (each dot is a system)")), width="stretch")
    with rr:
        # teste de 24 h para os dois sistemas
        res, D = ctx.res, ctx.dem["total"].values
        st.markdown(f"**{T('Teste de 24 horas nos 5 tipos de dia', '24-hour test on the 5 day types')}**")
        rows2 = []
        for k in M.DAY_TYPES:
            vals = []
            for sysrow in (e, r):
                s = M.System(pv=sysrow["pv"], bat=sysrow["bat"])
                mm = M.day_metrics(M.simulate_day(res, D, s, ctx.days[k]), s)
                vals.append(cut_txt(mm["hours"]))
            rows2.append((day_label(k), *vals))
        st.table(pd.DataFrame(rows2, columns=[T("Tipo de dia", "Day type"), T("Só eficiência", "Efficiency only"),
                                              T("Resiliente", "Resilient")]).set_index(T("Tipo de dia", "Day type")))
        st.caption(T("«Sem cortes» = a aldeia teve luz nas 24 horas desse dia.",
                     "“No cuts” = the village had power for all 24 hours of that day."))

    with st.expander(T("Pressupostos e dados", "Assumptions and data"), icon=":material/info:"):
        st.markdown(T(f"""
- **Dados:** sol e temperatura reais de Mabote, hora a hora (reanálise ERA5, Copernicus/ECMWF).
- **Procura:** calculada a partir do número de famílias e dos serviços (painel à esquerda), com variação diária.
- **Bateria:** lítio (LFP), eficiência 95 %, nunca abaixo de 20 % de carga.
- **Custos indicativos:** solar {num(M.COST['pv'])} USD/kWp, baterias {num(M.COST['bat'])} USD/kWh (valores típicos de mini-redes em África).
- **Dia mau:** um dia em que falta mais de 10 % da energia pedida.
""", f"""
- **Data:** real Mabote sun and temperature, hourly (ERA5 reanalysis, Copernicus/ECMWF).
- **Demand:** calculated from the number of households and services (left panel), with daily variation.
- **Battery:** lithium (LFP), 95 % efficiency, never below 20 % charge.
- **Indicative costs:** solar {num(M.COST['pv'])} USD/kWp, batteries {num(M.COST['bat'])} USD/kWh (typical African mini-grid values).
- **Bad day:** a day on which more than 10 % of the requested energy is missing.
"""))
