"""Método e dados: fontes, validação, equações, lógica de decisão e referências (bilingue)."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from resilia.data import load_site
from ui import charts
from ui.i18n import T, en, num, site as site_txt
from ui.style import C, explain, page_header


@st.cache_data(show_spinner=False)
def _freddy():
    return load_site("MZ").loc["2023-02-20":"2023-03-02"]


def _tex(s):
    """Fórmulas: vírgula decimal em PT, ponto em EN."""
    return s.replace("{,}", ".") if en() else s


def _table(header, rows):
    st.table(pd.DataFrame(rows, columns=header).set_index(header[0]))


def render(ctx):
    page_header(T("Método e dados", "Method & data"),
                T("Como o RESILIA funciona por dentro", "How RESILIA works under the hood"),
                T("Fontes de dados, validação, equações, lógica de decisão, limitações e referências, para quem quer "
                  "verificar cada número.",
                  "Data sources, validation, equations, decision logic, limitations and references, for anyone who wants "
                  "to check every number."))

    st.markdown(f"#### 0. {T('Onde cada critério de avaliação é respondido', 'Where each evaluation criterion is addressed')}")
    _table([T("Critério (peso)", "Criterion (weight)"), T("Como o RESILIA responde", "How RESILIA addresses it"),
            T("Onde ver", "Where to see it")], [
        (T("Relevância (15 %)", "Relevance (15 %)"),
         T("Eventos reais dos 3 países-piloto do EMERGE; foco em saúde, água e alerta",
           "Real events in the 3 EMERGE pilot countries; focus on health, water and warnings"),
         T("Apresentação · Simulador", "Pitch · Simulator")),
        (T("Inovação (15 %)", "Innovation (15 %)"),
         T("Gestão guiada por alerta meteorológico, reserva dinâmica para a clínica, cortes por prioridade, detecção "
           "automática do pior evento, previsão em tempo real",
           "Warning-driven operation, dynamic clinic reserve, priority-based shedding, automatic worst-event detection, live forecasts"),
         T("Simulador · 3 países", "Simulator · 3 countries")),
        (T("Viabilidade técnica e protótipo (20 %)", "Technical feasibility & prototype (20 %)"),
         T("Protótipo funcional, física por componente, 11 anos de dados horários, validação com eventos históricos",
           "Working prototype, per-component physics, 11 years of hourly data, validation against historical events"),
         T("Simulador · Laboratório · Método", "Simulator · Lab · Method")),
        (T("Impacto local e inclusão (15 %)", "Local impact & inclusion (15 %)"),
         T("Horas de clínica, pessoas com água, casas com luz, cadeia de frio das vacinas",
           "Clinic hours, people with water, homes with light, vaccine cold chain"),
         T("Apresentação · Simulador", "Pitch · Simulator")),
        (T("Escalabilidade (15 %)", "Scalability (15 %)"),
         T("Mesmo motor em 3 climas diferentes e em qualquer coordenada do planeta",
           "Same engine in 3 different climates and at any coordinate on Earth"), T("3 países", "3 countries")),
        (T("Modelo de negócio (10 %)", "Business model (10 %)"),
         T("CAPEX, LCOE, valor da energia não servida, receitas e financiamento",
           "CAPEX, LCOE, value of unserved energy, revenue and financing"), T("Negócio · Dimensionar", "Business · Sizing")),
        (T("Pitch e equipa (10 %)", "Pitch & team (10 %)"),
         T("Apresentação de 7 min com simulação real; roteiro 2026–2030", "7-minute pitch with real simulation; 2026–2030 roadmap"),
         T("Apresentação", "Pitch")),
    ])

    st.markdown(f"#### 1. {T('Base de dados (real, aberta e reproduzível)', 'Database (real, open and reproducible)')}")
    df = ctx.df
    _table([T("Dado", "Data"), T("Fonte", "Source"), T("Resolução", "Resolution"), T("Período", "Period"), T("Usado para", "Used for")], [
        (T("Radiação global, directa e difusa", "Global, direct and diffuse radiation"), "ERA5 (ECMWF / Copernicus) via Open-Meteo",
         T("horária, ~25 km", "hourly, ~25 km"), "2015–2025", T("Produção solar no plano dos painéis", "Solar output on the panel plane")),
        (T("Temperatura, humidade", "Temperature, humidity"), "ERA5", T("horária", "hourly"), "2015–2025",
         T("Temperatura de célula, bateria, inversor, procura", "Cell, battery and inverter temperature, demand")),
        (T("Vento a 10 m e 100 m, rajadas", "Wind at 10 m and 100 m, gusts"), "ERA5", T("horária", "hourly"), "2015–2025",
         T("Aerogerador, arrefecimento dos painéis, danos estruturais", "Wind turbine, panel cooling, structural damage")),
        (T("Chuva, neve, neve acumulada, pressão", "Rain, snowfall, snow depth, pressure"), "ERA5 / ERA5-Land", T("horária", "hourly"),
         "2015–2025", T("Detecção de eventos, neve nos painéis, limpeza pela chuva", "Event detection, snow on panels, rain cleaning")),
        (T("Poeira e profundidade óptica de aerossóis", "Dust and aerosol optical depth"), "CAMS (Copernicus Atmosphere)",
         T("horária", "hourly"), "2023–2025", T("Atenuação solar e sujidade (Marrocos, Mali)", "Solar attenuation and soiling (Morocco, Mali)")),
        (T("Previsão meteorológica", "Weather forecast"), "ECMWF / GFS / ICON via Open-Meteo", T("horária, 4 dias", "hourly, 4 days"),
         T("em directo", "live"), T("Modo operacional", "Operational mode")),
    ])
    st.markdown(T(f"Para **{site_txt(ctx.site_key, 'name')}** a base tem **{num(len(df))} horas** ({df.index[0]:%Y}–{df.index[-1]:%Y}). "
                  "Os ficheiros estão em `data/` e a aplicação funciona **sem internet**. `scripts/fetch_data.py` reconstrói "
                  "tudo a partir das fontes.",
                  f"For **{site_txt(ctx.site_key, 'name')}** the database holds **{num(len(df))} hours** ({df.index[0]:%Y}–{df.index[-1]:%Y}). "
                  "Files live in `data/` and the app works **offline**. `scripts/fetch_data.py` rebuilds everything from the sources."))

    st.markdown(f"#### 2. {T('Validação: o motor «vê» os eventos documentados', 'Validation: the engine “sees” documented events')}")
    f = _freddy()
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=f.index, y=f["pressure_msl"], name=T("Pressão (hPa)", "Pressure (hPa)"),
                             line=dict(color=C["soc"], width=2.5)))
    fig.add_trace(go.Bar(x=f.index, y=f["shortwave_radiation"], name=T("Radiação solar (W/m²)", "Solar radiation (W/m²)"),
                         marker_color=C["solar"], opacity=0.6), secondary_y=True)
    fig.add_vline(x=pd.Timestamp("2023-02-24 18:00"), line=dict(color=C["red"], dash="dot"))
    fig.add_annotation(x=pd.Timestamp("2023-02-24 18:00"), y=1, yref="paper",
                       text=T("Freddy entra em Inhambane (24 Fev)", "Freddy makes landfall in Inhambane (24 Feb)"),
                       showarrow=False, font=dict(color=C["red"]), xanchor="left")
    fig.update_yaxes(title_text="hPa", secondary_y=False)
    fig.update_yaxes(title_text="W/m²", secondary_y=True, showgrid=False)
    charts.pt_dates(fig, f.index, every=24)
    st.plotly_chart(charts.base(fig, T("Mabote, Fevereiro de 2023: a passagem do ciclone Freddy nos dados ERA5",
                                       "Mabote, February 2023: Cyclone Freddy's passage in the ERA5 data"), height=360),
                    width="stretch")
    explain(T("Validação qualitativa:", "Qualitative validation:"),
            T("a queda de pressão (mínimo ~995 hPa), as rajadas de ~30 m/s e o colapso da radiação coincidem com a entrada "
              "documentada do Freddy em Inhambane a 24/02/2023. O mesmo acontece com o Dineo (15–16/02/2017), o Filipo "
              "(12/03/2024), a onda de calor de Abril de 2024 no Mali e a neve de Dezembro de 2025 no Alto Atlas. A reanálise "
              "a 25 km suaviza os picos locais (ex.: máximas de 48 °C medidas em Kayes aparecem como ~45 °C), por isso o "
              "painel lateral permite agravar o evento.",
              "the pressure drop (minimum ~995 hPa), ~30 m/s gusts and the collapse in radiation match Freddy's documented "
              "landfall in Inhambane on 24/02/2023. The same holds for Dineo (15–16/02/2017), Filipo (12/03/2024), the April "
              "2024 heatwave in Mali and the December 2025 snow in the High Atlas. The 25 km reanalysis smooths local peaks "
              "(e.g. 48 °C highs measured in Kayes appear as ~45 °C), which is why the side panel lets you intensify the event."))

    st.markdown(f"#### 3. {T('Modelos físicos (um por componente)', 'Physical models (one per component)')}")
    st.markdown(T("**Irradiância no plano dos painéis** (modelo isotrópico; painel virado ao equador, inclinação = |latitude|):",
                  "**Plane-of-array irradiance** (isotropic model; equator-facing panel, tilt = |latitude|):"))
    st.latex(_tex(r"G_{POA}=DNI\cdot\cos\theta_i+DHI\cdot\frac{1+\cos\beta}{2}+GHI\cdot\rho\cdot\frac{1-\cos\beta}{2}\qquad"
                  r"\times\ (1-0{,}2\cdot\Delta AOD)"))
    st.markdown(T("**Temperatura de célula com arrefecimento pelo vento** (Skoplaki & Palyvos, 2009) e **potência PV**:",
                  "**Cell temperature with wind cooling** (Skoplaki & Palyvos, 2009) and **PV power**:"))
    st.latex(_tex(r"T_c=T_a+(NOCT-20)\frac{G_{POA}}{800}\cdot\frac{9{,}5}{5{,}7+3{,}8\,v}\qquad "
                  r"P_{PV}=P_{nom}\frac{G_{POA}}{1000}\left[1-0{,}0035(T_c-25)\right]\cdot0{,}88\cdot(1-S_{snow})(1-S_{dust})(1-D)"))
    st.markdown(T("**Neve** (adaptado de Marion et al., 2013): 1 cm de neve cobre o painel; desliza a $0{,}25\\sin\\beta$/h com "
                  "sol e $T_a>-1$ °C. **Poeira:** deposição $1{,}5\\times10^{-6}$/h por µg/m³, lavada por chuva ≥ 5 mm/h. "
                  "**Danos estruturais:** curva de fragilidade lognormal na rajada, mediana 42 m/s (estrutura comum) ou 62 m/s "
                  "(anti-ciclone), β = 0,15.",
                  "**Snow** (adapted from Marion et al., 2013): 1 cm of snow covers the panel; it slides at $0.25\\sin\\beta$/h "
                  "with sun and $T_a>-1$ °C. **Dust:** deposition $1.5\\times10^{-6}$/h per µg/m³, washed off by rain ≥ 5 mm/h. "
                  "**Structural damage:** lognormal fragility curve on gust speed, median 42 m/s (standard structure) or 62 m/s "
                  "(cyclone-rated), β = 0.15."))
    st.markdown(T("**Aerogerador** (perfil vertical do vento a partir de 10 m e 100 m, eixo a 24 m):",
                  "**Wind turbine** (vertical wind profile from 10 m and 100 m, hub at 24 m):"))
    st.latex(_tex(r"P_{w}=P_{nom}\cdot\frac{v_h^3-v_{in}^3}{v_r^3-v_{in}^3},\ \ v_{in}=2{,}5,\ v_r=11\ \mathrm{m/s};"
                  + (r"\ \ \text{shutdown if }v_h\ge20\text{ or gust}\ge30\ \mathrm{m/s}" if en() else
                     r"\ \ \text{paragem se }v_h\ge20\text{ ou rajada}\ge30\ \mathrm{m/s}")))
    st.markdown(T("**Bateria LFP** (balanço, eficiências 96 %/96 %, C-rate 0,5, mínimo 10 %) e **limites térmicos do BMS**:",
                  "**LFP battery** (balance, 96 %/96 % efficiency, 0.5 C-rate, 10 % minimum) and **BMS thermal limits**:"))
    st.latex(_tex(r"E_{t+1}=E_t+0{,}96\,P_{ch}-\frac{P_{dis}}{0{,}96}\qquad "
                  r"f_{ch}(T_b)=\begin{cases}0 & T_b<0\\0{,}3 & 0\le T_b<10\\1 & 10\le T_b\le45\\0{,}5 & 45<T_b\le55\\0&T_b>55\end{cases}"))
    st.markdown(T("**Inversor:** potência × $\\max(0,\\min(1,1-(T_{inv}-45)/20))$. **Gerador** (curva HOMER): "
                  "$F=0{,}08415\\,P_{nom}+0{,}246\\,P$ (L/h), carga mínima 30 %.",
                  "**Inverter:** power × $\\max(0,\\min(1,1-(T_{inv}-45)/20))$. **Generator** (HOMER curve): "
                  "$F=0.08415\\,P_{nom}+0.246\\,P$ (L/h), 30 % minimum load."))

    st.markdown(f"#### 4. {T('Procura por prioridade, construída de baixo para cima', 'Priority-based demand, built bottom-up')}")
    _table([T("Nível", "Tier"), T("Serviços", "Services"), T("Reacção ao clima", "Weather response")], [
        (T("Crítica", "Critical"),
         T("Centro de saúde (~15 kWh/dia), comunicações e rádio de alerta, escola como abrigo de evacuação durante o evento, "
           "climatização da bateria", "Health centre (~15 kWh/day), communications and warning radio, school as an evacuation "
           "shelter during the event, battery climate control"),
         T("+30 % na clínica em tempestade; ventilação e frio de vacinas no calor; aquecimento no frio",
           "+30 % at the clinic in storms; ventilation and vaccine cooling in heat; heating in cold")),
        (T("Essencial", "Essential"),
         T("Casas (≈0,3 kWh/dia cada; modo essencial = 64 Wh/dia: 3 lâmpadas LED + telemóvel), iluminação pública, escola, "
           "bombagem de água (20 L/pessoa/dia, depósito de 1,5 dias)",
           "Homes (≈0.3 kWh/day each; essentials mode = 64 Wh/day: 3 LED lamps + phone), street lighting, school, water "
           "pumping (20 L/person/day, 1.5-day tank)"),
         T("ventoinhas acima de 32 °C, +25 % em tempestade, +40 % de água no calor extremo",
           "fans above 32 °C, +25 % in storms, +40 % water in extreme heat")),
        (T("Produtiva", "Productive"), T("Moagem (5,5 kW), comércio e frio", "Grain mill (5.5 kW), shops and cold storage"),
         T("parada a 70 % durante tempestades", "70 % idle during storms")),
    ])

    st.markdown(f"#### 5. {T('Lógica de decisão (despacho)', 'Decision logic (dispatch)')}")
    _table(["", T("Convencional", "Conventional"), "RESILIA"], [
        (T("Previsão", "Forecast"), T("nenhuma", "none"), T("alerta meteorológico com 0–72 h de antecedência", "weather warning 0–72 h ahead")),
        (T("Antes do evento", "Before the event"), T("nada muda", "nothing changes"),
         T("pré-carga (gerador só se a previsão mostrar défice) e depósito de água cheio",
           "pre-charge (generator only if the forecast shows a deficit) and full water tank")),
        (T("Bateria", "Battery"), T("descarrega até ao mínimo e desliga tudo (religa aos 30 %)",
                                    "discharges to the minimum and shuts everything down (restarts at 30 %)"),
         T("reserva dinâmica para a clínica, recalculada a cada hora com o sol previsto",
           "dynamic clinic reserve, recalculated every hour using the forecast sun")),
        (T("Quando falta energia", "When energy runs short"), T("apagão total (alimentador único)", "total blackout (single feeder)"),
         T("corta por ordem: produtiva → conforto das casas → essencial mínimo → crítica",
           "sheds in order: productive → home comfort → essential minimum → critical")),
        (T("Gasóleo", "Diesel"), T("arranca com bateria < 25 %", "starts when battery < 25 %"),
         T("racionado: guarda o necessário para as cargas críticas até ao fim do evento",
           "rationed: keeps what critical loads need until the event ends")),
        (T("Manutenção", "Maintenance"), T("nenhuma", "none"), T("limpeza de neve (9 h e 13 h) e lavagem de poeira",
                                                                 "snow clearing (9 am and 1 pm) and dust washing")),
    ])
    st.markdown(T("**Índice RESILIA (0–100)** = 50 % × cargas críticas servidas + 25 % × casas com luz essencial + 15 % × água "
                  "servida + 10 % × procura total servida. Mede **serviços que mantêm as pessoas seguras**, não kWh. A filosofia "
                  "segue o «triângulo de resiliência» (Bruneau et al., 2003): resistir, manter as funções críticas e recuperar depressa.",
                  "**RESILIA Index (0–100)** = 50 % × critical loads served + 25 % × homes with essential light + 15 % × water "
                  "served + 10 % × total demand served. It measures **services that keep people safe**, not kWh. The approach "
                  "follows the “resilience triangle” (Bruneau et al., 2003): resist, keep critical functions running and recover fast."))

    st.markdown(f"#### 6. {T('Pressupostos e limitações (transparência)', 'Assumptions and limitations (transparency)')}")
    st.markdown(T("""
- Passo horário. A previsão usada pelo RESILIA é a meteorologia real (previsão perfeita); a prudência fica embutida ao contar só com 50–85 % do sol previsto.
- A reanálise ERA5 (~25 km) suaviza extremos locais. O teste de stress permite agravar o evento até +50 %.
- ERA5 usa aerossóis climatológicos, por isso a poeira é acrescentada com o excesso de AOD do CAMS (só a partir de 2023).
- A procura é um modelo de engenharia com perfis típicos de aldeias rurais. Deve ser calibrada com medições no piloto.
- Os custos são indicativos (2024–2025) e editáveis. O valor da energia não servida é um pressuposto explícito.
- Validação de campo prevista para a fase piloto (2027): contadores inteligentes por alimentador e sensores de temperatura da bateria.
""", """
- Hourly time step. RESILIA uses the real weather as its forecast (perfect foresight); caution is built in by counting only 50–85 % of forecast sun.
- The ERA5 reanalysis (~25 km) smooths local extremes. The stress test lets you intensify the event by up to +50 %.
- ERA5 uses climatological aerosols, so dust is added from the CAMS AOD excess (from 2023 onwards only).
- Demand is an engineering model with typical rural-village profiles. It must be calibrated with measurements in the pilot.
- Costs are indicative (2024–2025) and editable. The value of unserved energy is an explicit assumption.
- Field validation is planned for the pilot phase (2027): smart meters per feeder and battery temperature sensors.
"""))

    st.markdown(f"#### 7. {T('Referências (APA 7)', 'References (APA 7)')}")
    st.markdown("""
- Bruneau, M., Chang, S. E., Eguchi, R. T., Lee, G. C., O'Rourke, T. D., Reinhorn, A. M., Shinozuka, M., Tierney, K., Wallace, W. A., & von Winterfeldt, D. (2003). A framework to quantitatively assess and enhance the seismic resilience of communities. *Earthquake Spectra, 19*(4), 733–752. https://doi.org/10.1193/1.1623497
- Duffie, J. A., & Beckman, W. A. (2020). *Solar engineering of thermal processes, photovoltaics and wind* (5th ed.). Wiley.
- ESMAP. (2022). *Mini grids for half a billion people: Market outlook and handbook for decision makers*. World Bank.
- Hersbach, H., Bell, B., Berrisford, P., et al. (2020). The ERA5 global reanalysis. *Quarterly Journal of the Royal Meteorological Society, 146*(730), 1999–2049. https://doi.org/10.1002/qj.3803
- Inness, A., Ades, M., Agustí-Panareda, A., et al. (2019). The CAMS reanalysis of atmospheric composition. *Atmospheric Chemistry and Physics, 19*(6), 3515–3556. https://doi.org/10.5194/acp-19-3515-2019
- IPCC. (2021). *Climate change 2021: The physical science basis*. Cambridge University Press.
- IRENA. (2024). *Renewable power generation costs in 2023*. International Renewable Energy Agency.
- Lambert, T., Gilman, P., & Lilienthal, P. (2006). Micropower system modeling with HOMER. In F. A. Farret & M. G. Simões (Eds.), *Integration of alternative sources of energy* (pp. 379–418). Wiley.
- Marion, B., Schaefer, R., Caine, H., & Sanchez, G. (2013). Measured and modeled photovoltaic system energy losses from snow for Colorado and Wisconsin locations. *Solar Energy, 97*, 112–121. https://doi.org/10.1016/j.solener.2013.07.029
- Skoplaki, E., & Palyvos, J. A. (2009). On the temperature dependence of photovoltaic module electrical performance. *Solar Energy, 83*(5), 614–624. https://doi.org/10.1016/j.solener.2008.10.008
- Zippenfenig, P. (2023). *Open-Meteo.com Weather API* [Software]. Zenodo. https://doi.org/10.5281/zenodo.7970649
""")
