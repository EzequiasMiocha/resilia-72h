"""Painel lateral (páginas de exploração) e cálculo partilhado."""
from types import SimpleNamespace

import pandas as pd
import streamlit as st

from resilia.data import EVENT_H, event_window, intensify, load_site, sim_slice, typical_window, worst_window
from resilia.engine import CONVENTIONAL, Strategy, metrics, recovery_hours, simulate
from resilia.loads import Community
from resilia.physics import System
from resilia.sites import EVENTS, SITES
from ui.i18n import T, event, site as site_txt


@st.cache_data(show_spinner="A carregar 11 anos de dados climáticos reais… / Loading 11 years of real climate data…")
def get_site(key):
    return load_site(key)


@st.cache_data(show_spinner=False)
def get_windows(key):
    df = get_site(key)
    out = {k: event_window(df, k) for k, e in EVENTS.items() if e["site"] == key}
    out["auto"] = worst_window(df, "min_solar")
    out["normal"] = typical_window(df, out[SITES[key]["default_event"]])
    return out


def event_label(k):
    if k == "auto":
        return T("Pior janela 2015–2025 (detecção automática)", "Worst window 2015–2025 (auto-detected)")
    if k == "normal":
        return T("72 h normais (para comparar)", "Normal 72 h (for comparison)")
    return event(k, "name")


def build():
    """Desenha o painel lateral e devolve o contexto da simulação."""
    with st.sidebar:
        st.markdown(f"### {T('Onde e quando?', 'Where and when?')}")
        site_key = st.radio(T("País", "Country"), list(SITES), key="site_key",
                            format_func=lambda k: f"{site_txt(k, 'country')} · {site_txt(k, 'name')}")
        site = SITES[site_key]
        wins = get_windows(site_key)
        ev_keys = [k for k, e in EVENTS.items() if e["site"] == site_key] + ["auto", "normal"]
        ev_key = st.selectbox(T("Evento climático real (72 h)", "Real climate event (72 h)"), ev_keys,
                              index=ev_keys.index(site["default_event"]), format_func=event_label, key=f"ev_{site_key}")
        st.caption(T("Cinzento = sistema de hoje · Vermelho = com RESILIA. O equipamento é o mesmo nos dois.",
                     "Grey = today's system · Red = with RESILIA. Both use exactly the same equipment."))

        d = site["default_sys"]
        defaults = dict(pv=d["pv"], bat=d["bat"], inv=d["inv"], wind=0, dg=0, fuel=200)
        for k, v in defaults.items():
            st.session_state.setdefault(f"{k}_{site_key}", v)
        with st.expander(T("Equipamento da mini-rede", "Mini-grid equipment"), icon=":material/solar_power:"):
            pv = st.slider(T("Painéis solares (kWp)", "Solar panels (kWp)"), 0, 150, step=5, key=f"pv_{site_key}")
            bat = st.slider(T("Baterias (kWh)", "Batteries (kWh)"), 0, 500, step=10, key=f"bat_{site_key}")
            inv = st.slider(T("Inversor (kW)", "Inverter (kW)"), 5, 80, step=5, key=f"inv_{site_key}")
            wind = st.slider(T("Aerogerador (kW)", "Wind turbine (kW)"), 0, 30, step=5, key=f"wind_{site_key}")
            dg = st.slider(T("Gerador a gasóleo (kW)", "Diesel generator (kW)"), 0, 40, step=5, key=f"dg_{site_key}")
            fuel_l = st.slider(T("Depósito de gasóleo (L)", "Diesel tank (L)"), 0, 600, step=50, key=f"fuel_{site_key}",
                               disabled=dg == 0)
            if st.button(T("Repor equipamento padrão", "Reset to standard equipment"), icon=":material/restart_alt:",
                         width="stretch"):
                for k in defaults:
                    st.session_state.pop(f"{k}_{site_key}", None)
                st.rerun()
        with st.expander(T("Inteligência RESILIA", "RESILIA intelligence"), icon=":material/psychology:"):
            lead = st.slider(T("Aviso meteorológico com antecedência de (h)", "Weather warning lead time (h)"),
                             0, 72, 48, 6, key="lead", help=T("0 h = sem sistema de alerta.", "0 h = no warning system."))
            hard = st.toggle(T("Estrutura solar anti-ciclone", "Cyclone-rated solar structure"), value=True, key="hard")
            clim = st.toggle(T("Baterias em contentor protegido", "Batteries in protected enclosure"), value=True, key="clim")
            maint = st.toggle(T("Limpeza de neve e poeira", "Snow and dust cleaning"), value=True, key="maint")
        with st.expander(T("Teste de stress", "Stress test"), icon=":material/bolt:"):
            stress = st.slider(T("Agravar o evento (%)", "Intensify the event (%)"), 0, 50, 0, 5, key="stress",
                               help=T("Menos sol, mais vento e chuva, temperaturas mais extremas.",
                                      "Less sun, more wind and rain, more extreme temperatures."))
            future = st.toggle(T("Clima de 2050 (+1,5 °C)", "2050 climate (+1.5 °C)"), value=False, key="future")
        with st.expander(T("Comunidade", "Community"), icon=":material/groups:"):
            hh = st.slider(T("Famílias", "Households"), 50, 600, site["households"], 10, key=f"hh_{site_key}")
            people = int(hh * site["people"] / site["households"])
            st.caption(T(f"≈ {people} pessoas", f"≈ {people} people"))
            c_health = st.checkbox(T("Centro de saúde", "Health centre"), True, key=f"h_{site_key}")
            c_school = st.checkbox(T("Escola (abrigo de evacuação)", "School (evacuation shelter)"), True, key=f"s_{site_key}")
            c_mill = st.checkbox(T("Moagem", "Grain mill"), True, key=f"m_{site_key}")
            c_com = st.checkbox(T("Comércio e frio", "Shops and cold storage"), True, key=f"c_{site_key}")

    df = get_site(site_key)
    start = wins[ev_key]
    w = intensify(sim_slice(df, start), stress, 1.5 if future else 0.0)
    comm = Community(households=hh, people=people, health=c_health, school=c_school, mill=c_mill,
                     commerce=c_com, water_head_m=site["water_head_m"], heat_sens=site["heat_sens"],
                     cold_sens=site["cold_sens"])
    hw = dict(pv_kwp=pv, bat_kwh=bat, inv_kw=inv, wind_kw=wind, diesel_kw=dg, fuel_l=fuel_l if dg else 0.0)
    sys_c = System(**hw, label="Convencional")
    sys_r = System(**hw, pv_hardened=hard, bat_climate=clim, label="RESILIA")
    strat_r = Strategy(smart=True, lead_h=lead, maint=maint, name="RESILIA")
    intensity = 1 + stress / 100
    oc = simulate(w, site, sys_c, comm, CONVENTIONAL, intensity=intensity)
    orr = simulate(w, site, sys_r, comm, strat_r, intensity=intensity)
    evm = (oc["fase"] == "evento").values
    return SimpleNamespace(
        site_key=site_key, site=site, df=df, ev_key=ev_key, ev_label=event_label(ev_key),
        event=EVENTS.get(ev_key), start=start, end=start + pd.Timedelta(hours=EVENT_H - 1), w=w,
        comm=comm, sys_c=sys_c, sys_r=sys_r, strat_r=strat_r, oc=oc, orr=orr,
        mc=metrics(oc, evm), mr=metrics(orr, evm), rec_c=recovery_hours(oc), rec_r=recovery_hours(orr),
        stress=stress, future=future, intensity=intensity, lead=lead, wins=wins, hw=hw,
        flags=dict(hard=hard, clim=clim, maint=maint),
    )
