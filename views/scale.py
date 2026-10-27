"""3 países, qualquer local do planeta e previsão em tempo real (bilingue)."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from resilia.data import fetch_forecast, fetch_location, sim_slice, worst_window
from resilia.engine import CONVENTIONAL, Strategy, metrics, simulate
from resilia.sites import SITES
from ui import charts
from ui.i18n import T, event, num, site as site_txt
from ui.style import C, card, explain, page_header, versus

from .common import all_events_summary


@st.cache_data(show_spinner=False, ttl=3600)
def _forecast(key):
    s = SITES[key]
    return fetch_forecast(s["lat"], s["lon"], s["utc"])


@st.cache_data(show_spinner=False)
def _location(lat, lon, utc):
    return fetch_location(lat, lon, utc, years=(2019, 2025))


def render(ctx):
    page_header(T("3 países", "3 countries"),
                T("Um motor, três climas, qualquer aldeia", "One engine, three climates, any village"),
                T("O RESILIA não precisa de estações no terreno: usa dados climáticos globais disponíveis para qualquer "
                  "coordenada. Para um novo local bastam as coordenadas, um inventário da comunidade e o equipamento.",
                  "RESILIA needs no ground weather stations: it uses global climate data available for any coordinate. "
                  "A new site only needs its coordinates, a community inventory and the equipment list."))

    t = all_events_summary()
    fig = go.Figure()
    for k, s in SITES.items():
        sub = t[t.site == k]
        txt = (f"<b>{site_txt(k, 'name')}</b><br>{site_txt(k, 'hazard')}<br>"
               + T(f"Clínica no pior evento: {sub.conv_crit.min():.0f}% → {sub.res_crit.min():.0f}%",
                   f"Clinic in the worst event: {sub.conv_crit.min():.0f}% → {sub.res_crit.min():.0f}%"))
        fig.add_trace(go.Scattergeo(lat=[s["lat"]], lon=[s["lon"]], mode="markers+text", text=[site_txt(k, "name")],
                                    textposition="top center", hovertext=[txt], hoverinfo="text",
                                    marker=dict(size=20, color=C["red"], line=dict(color="#FFFFFF", width=2)),
                                    textfont=dict(color="#1F2933", size=14), name=site_txt(k, "country")))
    fig.update_geos(scope="africa", showcountries=True, countrycolor="#C3C8D0", landcolor="#ECEEF2",
                    showocean=True, oceancolor="#FFFFFF", bgcolor="rgba(0,0,0,0)", coastlinecolor="#C3C8D0")
    fig.update_layout(height=470, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)",
                      showlegend=False, font=dict(color="#1F2933"))
    l, r = st.columns([3, 2])
    with l:
        st.plotly_chart(fig, width="stretch")
    with r:
        for k in SITES:
            sub = t[t.site == k]
            versus(T(f"{site_txt(k, 'country')} — {site_txt(k, 'name')}: horas de clínica às escuras (3 eventos)",
                     f"{site_txt(k, 'country')} — {site_txt(k, 'name')}: clinic hours in the dark (3 events)"),
                   f"{sub.conv_out.sum()} h", f"{sub.res_out.sum()} h", site_txt(k, "hazard"))
            st.write("")

    st.markdown(f"#### {T('Matriz de resiliência: 9 eventos extremos reais', 'Resilience matrix: 9 real extreme events')}")
    m = pd.DataFrame({
        T("País", "Country"): [site_txt(k, "country") for k in t.site],
        T("Evento", "Event"): [event(e, "name") for e in t.ev],
        T("Críticas hoje (%)", "Critical, today (%)"): t.conv_crit.round(0),
        T("Críticas RESILIA (%)", "Critical, RESILIA (%)"): t.res_crit.round(0),
        T("Clínica s/ energia hoje (h)", "Clinic unpowered, today (h)"): t.conv_out,
        T("Clínica s/ energia RESILIA (h)", "Clinic unpowered, RESILIA (h)"): t.res_out,
        T("Apagão total hoje (h)", "Total blackout, today (h)"): t.conv_black,
        T("Apagão total RESILIA (h)", "Total blackout, RESILIA (h)"): t.res_black,
        T("Água hoje (%)", "Water, today (%)"): t.conv_water.round(0),
        T("Água RESILIA (%)", "Water, RESILIA (%)"): t.res_water.round(0),
    })
    st.dataframe(m, width="stretch", hide_index=True)

    st.markdown(f"#### {T('O que muda de país para país (e o que não muda)', 'What changes from country to country (and what does not)')}")
    rows = [
        (T("Ameaça dominante", "Dominant hazard"),
         T("Ciclones, chuva torrencial", "Cyclones, torrential rain"), T("Neve, frio extremo, isolamento", "Snow, extreme cold, isolation"),
         T("Calor > 45 °C, poeira, cheias", "Heat > 45 °C, dust, floods")),
        (T("Física crítica", "Critical physics"),
         T("Céu encoberto 3–4 dias, rajadas, estradas cortadas", "3–4 overcast days, gusts, roads cut"),
         T("Painéis cobertos, bateria < 0 °C não carrega", "Panels buried, battery < 0 °C cannot charge"),
         T("Inversor e bateria em derating, sujidade", "Inverter and battery derating, soiling")),
        (T("Reforço físico", "Physical hardening"),
         T("Estrutura anti-ciclone, equipamento elevado", "Cyclone-rated structure, raised equipment"),
         T("Contentor isolado e aquecido, painéis inclinados", "Insulated, heated enclosure, steeper panels"),
         T("Contentor ventilado e sombreado, lavagem", "Ventilated, shaded enclosure, washing")),
        (T("Alerta meteorológico", "Weather warnings"), SITES["MZ"]["met_service"], SITES["MA"]["met_service"],
         SITES["ML"]["met_service"]),
        (T("Protecção civil", "Civil protection"), SITES["MZ"]["disaster_agency"], SITES["MA"]["disaster_agency"],
         SITES["ML"]["disaster_agency"]),
        (T("Parceiros de energia", "Energy partners"), SITES["MZ"]["energy_agency"], SITES["MA"]["energy_agency"],
         SITES["ML"]["energy_agency"]),
    ]
    st.table(pd.DataFrame([r[1:] for r in rows], index=[r[0] for r in rows],
                          columns=[site_txt("MZ", "country"), site_txt("MA", "country"), site_txt("ML", "country")]))
    st.markdown(T("**Igual nos três:** o motor físico, o despacho inteligente, a reserva dinâmica, os cortes por prioridade "
                  "e os indicadores de impacto. Só os parâmetros mudam, não o código.",
                  "**The same in all three:** the physics engine, smart dispatch, dynamic reserve, priority-based load "
                  "shedding and impact indicators. Only the parameters change, not the code."))

    # ── qualquer local
    st.markdown(f"### {T('Teste qualquer aldeia do planeta (dados reais em directo)', 'Test any village on the planet (live real data)')}")
    explain(T("Como funciona:", "How it works:"),
            T("escreva as coordenadas. O RESILIA descarrega 7 anos de clima horário (2019–2025), <b>encontra sozinho as 72 h "
              "com menos sol</b> e simula a mini-rede configurada no painel lateral com as duas estratégias. Precisa de "
              "internet; a primeira análise de um local demora ~30 s.",
              "enter the coordinates. RESILIA downloads 7 years of hourly climate data (2019–2025), <b>finds the 72 h with "
              "the least sunshine on its own</b> and simulates the mini-grid configured in the side panel under both "
              "strategies. Requires internet; the first analysis of a site takes ~30 s."))
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        lat = st.number_input("Latitude", -60.0, 60.0, -19.83, 0.01, format="%.2f", key="loc_lat",
                              help=T("Exemplo: −19,83 = Beira (ciclone Idai)", "Example: −19.83 = Beira (Cyclone Idai)"))
    with c2:
        lon = st.number_input("Longitude", -180.0, 180.0, 34.84, 0.01, format="%.2f", key="loc_lon")
    with c3:
        utc = st.number_input(T("Fuso horário (UTC±h)", "Time zone (UTC±h)"), -12, 14, 2, 1, key="loc_utc")
    with c4:
        st.write("")
        go_btn = st.button(T("Analisar este local", "Analyse this site"), icon=":material/travel_explore:", width="stretch")
    if go_btn:
        st.session_state["loc"] = (round(lat, 2), round(lon, 2), int(utc))
    if st.session_state.get("loc"):
        la, lo, u = st.session_state["loc"]
        try:
            with st.spinner(T("A descarregar 7 anos de clima e a procurar o pior evento…",
                              "Downloading 7 years of climate data and searching for the worst event…")):
                dfl = _location(la, lo, u)
            site = dict(lat=la, lon=lo, utc=u)
            start = worst_window(dfl, "min_solar")
            w = sim_slice(dfl, start)
            oc = simulate(w, site, ctx.sys_c, ctx.comm, CONVENTIONAL)
            orr = simulate(w, site, ctx.sys_r, ctx.comm, ctx.strat_r)
            evm = (oc["fase"] == "evento").values
            a, b = metrics(oc, evm), metrics(orr, evm)
            ev = w[w.fase == "evento"]
            st.markdown(T(f"**Pior janela de 72 h encontrada:** {start:%d/%m/%Y %H:%M} · sol acumulado "
                          f"{num(ev['shortwave_radiation'].sum() / 1000, 1)} kWh/m² · rajada máx. {num(ev['wind_gusts_10m'].max())} m/s · "
                          f"chuva {num(ev['precipitation'].sum())} mm",
                          f"**Worst 72-hour window found:** {start:%d/%m/%Y %H:%M} · cumulative sun "
                          f"{num(ev['shortwave_radiation'].sum() / 1000, 1)} kWh/m² · max gust {num(ev['wind_gusts_10m'].max())} m/s · "
                          f"rain {num(ev['precipitation'].sum())} mm"))
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                versus(T("Cargas críticas servidas", "Critical loads served"), f"{num(a['crit_pct'])}%", f"{num(b['crit_pct'])}%")
            with k2:
                versus(T("Clínica sem energia", "Clinic without power"), f"{a['crit_out_h']} h", f"{b['crit_out_h']} h")
            with k3:
                versus(T("Apagão total", "Total blackout"), f"{a['blackout_h']} h", f"{b['blackout_h']} h")
            with k4:
                versus(T("Índice RESILIA", "RESILIA index"), num(a["index"]), num(b["index"]))
            st.plotly_chart(charts.soc(oc, orr, T("Bateria no pior evento deste local", "Battery during this site's worst event")),
                            width="stretch")
        except Exception as ex:
            st.markdown(f'<div class="warnbox">{T("Não foi possível obter dados para este local", "Could not fetch data for this site")}: '
                        f'{ex}. {T("Verifique a ligação à internet.", "Check the internet connection.")}</div>', unsafe_allow_html=True)

    # ── previsão
    st.markdown(f"### {T('Modo operacional: o que fazer nas próximas 72 h', 'Operational mode: what to do in the next 72 h')}")
    k = ctx.site_key
    explain(T("Do protótipo ao produto:", "From prototype to product:"),
            T(f"aqui o RESILIA lê a <b>previsão meteorológica real</b> dos próximos 4 dias para {site_txt(k, 'name')} "
              "(modelos globais ECMWF/GFS via Open-Meteo), detecta condições severas e simula o plano de operação. É isto "
              "que o controlador instalado na mini-rede faria todos os dias, automaticamente.",
              f"here RESILIA reads the <b>real weather forecast</b> for the next 4 days for {site_txt(k, 'name')} "
              "(ECMWF/GFS global models via Open-Meteo), detects severe conditions and simulates the operating plan. This is "
              "what the controller installed on the mini-grid would do every day, automatically."))
    if st.button(T(f"Ler a previsão real para {site_txt(k, 'name')}", f"Read the live forecast for {site_txt(k, 'name')}"),
                 icon=":material/satellite_alt:"):
        st.session_state["fc_site"] = k
    if st.session_state.get("fc_site") == k:
        try:
            with st.spinner(T("A ler a previsão…", "Reading the forecast…")):
                fc = _forecast(k)
            now = pd.Timestamp.utcnow().tz_localize(None) + pd.Timedelta(hours=ctx.site["utc"])
            fc = fc[fc.index >= now.floor("h")].iloc[:96]
            orr = simulate(fc, ctx.site, ctx.sys_r, ctx.comm, Strategy(True, 48, True, "RESILIA"))
            oc = simulate(fc, ctx.site, ctx.sys_c, ctx.comm, CONVENTIONAL)
            sev_h = int(orr["alert"].sum())
            a, b = metrics(oc), metrics(orr)
            k1, k2, k3 = st.columns(3)
            with k1:
                card(T("Horas severas previstas", "Forecast severe hours"), f"{int((orr['mode'] == 'evento').sum())} h",
                     T("rajadas ≥ 20 m/s, chuva ≥ 50 mm/24 h, neve, calor ≥ 42 °C ou poeira",
                       "gusts ≥ 20 m/s, rain ≥ 50 mm/24 h, snow, heat ≥ 42 °C or dust"), C["unmet"])
            with k2:
                card(T("Sol previsto (96 h)", "Forecast sun (96 h)"), f"{num(fc['shortwave_radiation'].sum() / 1000, 1)} kWh/m²",
                     f"{fc.index[0]:%d/%m %H:00} → {fc.index[-1]:%d/%m %H:00}", C["solar"])
            with k3:
                card(T("Plano RESILIA", "RESILIA plan"), T("MODO TEMPESTADE", "STORM MODE") if sev_h else T("operação normal", "normal operation"),
                     T("pré-carga e reserva activadas", "pre-charge and reserve activated") if sev_h
                     else T("sem ameaças no horizonte", "no threats on the horizon"), C["diesel"] if sev_h else C["res"])
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Scatter(x=fc.index, y=fc["shortwave_radiation"], name=T("Sol previsto (W/m²)", "Forecast sun (W/m²)"),
                                     fill="tozeroy", line=dict(color=C["solar"])))
            fig.add_trace(go.Scatter(x=orr.index, y=100 * orr["soc"], name=T("Bateria RESILIA (%)", "RESILIA battery (%)"),
                                     line=dict(color=C["res"], width=3)), secondary_y=True)
            fig.add_trace(go.Scatter(x=oc.index, y=100 * oc["soc"], name=T("Bateria hoje (%)", "Today's battery (%)"),
                                     line=dict(color=C["conv"], width=2, dash="dot")), secondary_y=True)
            fig.update_yaxes(title_text="W/m²", secondary_y=False)
            fig.update_yaxes(title_text=T("Bateria (%)", "Battery (%)"), range=[0, 105], secondary_y=True, showgrid=False)
            charts.pt_dates(fig, fc.index)
            st.plotly_chart(charts.base(fig, T("Previsão real e plano da bateria", "Live forecast and battery plan"), height=340),
                            width="stretch")
            st.markdown(T(f"Rajada máxima prevista: **{num(fc['wind_gusts_10m'].max())} m/s** · chuva prevista: "
                          f"**{num(fc['precipitation'].sum())} mm** · temperatura: **{num(fc['temperature_2m'].min())} a "
                          f"{num(fc['temperature_2m'].max())} °C** · clínica servida no plano: **{num(a['crit_pct'])}% → {num(b['crit_pct'])}%**",
                          f"Max forecast gust: **{num(fc['wind_gusts_10m'].max())} m/s** · forecast rain: "
                          f"**{num(fc['precipitation'].sum())} mm** · temperature: **{num(fc['temperature_2m'].min())} to "
                          f"{num(fc['temperature_2m'].max())} °C** · clinic served in the plan: **{num(a['crit_pct'])}% → {num(b['crit_pct'])}%**"))
            st.plotly_chart(charts.services_heatmap(orr, True, T("Plano de serviço previsto (RESILIA)", "Forecast service plan (RESILIA)")),
                            width="stretch")
        except Exception as ex:
            st.markdown(f'<div class="warnbox">{T("Previsão indisponível", "Forecast unavailable")} ({ex}). '
                        f'{T("O resto da aplicação funciona offline.", "The rest of the app works offline.")}</div>',
                        unsafe_allow_html=True)

    st.markdown(f"### {T('Caminho de replicação', 'Replication path')}")
    c1, c2, c3 = st.columns(3)
    with c1:
        card(T("Fase 1 · 2027", "Phase 1 · 2027"), T("1 piloto por país", "1 pilot per country"),
             T("Mabote, Alto Atlas e Kayes com controlador RESILIA, contadores inteligentes e alerta integrado com o serviço "
               "meteorológico nacional.", "Mabote, High Atlas and Kayes with the RESILIA controller, smart meters and warnings "
               "integrated with the national weather service."), C["solar"])
    with c2:
        card(T("Fase 2 · 2028", "Phase 2 · 2028"), T("50 mini-redes", "50 mini-grids"),
             T("Software como serviço para operadores de mini-redes já existentes: o mesmo motor, sem novo hardware de geração.",
               "Software as a service for existing mini-grid operators: the same engine, no new generation hardware."), C["bat"])
    with c3:
        card(T("Fase 3 · 2030", "Phase 3 · 2030"), T("SADC + Sahel + Magrebe", "SADC + Sahel + Maghreb"),
             T("Plataforma regional de resiliência energética, ligada a sistemas de alerta precoce e a seguros paramétricos.",
               "Regional energy-resilience platform linked to early-warning systems and parametric insurance."), C["wind"])
