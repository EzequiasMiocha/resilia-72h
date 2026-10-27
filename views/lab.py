"""Laboratório do clima: a física explicada de forma interactiva (bilingue)."""
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from resilia.physics import GAMMA, NOCT, PR_PV, pv_damage
from ui import charts
from ui.i18n import T
from ui.style import C, card, chain, page_header

# Cada condição: valores iniciais e cadeia de impacto [(título PT, título EN, texto PT, texto EN)]
PRESETS = {
    "normal": dict(pt="Dia normal", en="Normal day", G=900, T=28, v=4, gust=8, aod=0.0, snow=0, soil=3, chain=None),
    "cyclone": dict(pt="Ciclone tropical", en="Tropical cyclone", G=120, T=24, v=18, gust=35, aod=0.0, snow=0, soil=0, chain=[
        ("Ameaça", "Hazard", "Ciclone: nuvens densas durante dias, rajadas de 30–60 m/s, chuva torrencial, estradas cortadas.",
         "Cyclone: thick clouds for days, 30–60 m/s gusts, torrential rain, roads cut."),
        ("Física", "Physics", "A irradiância cai 80–95 %; a turbina pára por segurança acima de ~20 m/s; estruturas comuns "
         "cedem a partir de ~40 m/s.", "Irradiance drops 80–95 %; the turbine shuts down above ~20 m/s; standard structures "
         "fail from ~40 m/s."),
        ("Energia", "Energy", "Quase sem produção durante 2–4 dias; a bateria é a única fonte; não chega gasóleo.",
         "Almost no generation for 2–4 days; the battery is the only source; no diesel gets through."),
        ("Serviços", "Services", "Clínica com feridos, abrigo na escola, rádio de alerta, água limpa (risco de cólera).",
         "Clinic with injured people, shelter at the school, warning radio, clean water (cholera risk)."),
        ("Resposta RESILIA", "RESILIA response", "Alerta 48 h antes → bateria e depósito de água cheios; estrutura "
         "anti-ciclone; reserva dinâmica para a clínica; moagem pausada; casas em modo essencial.",
         "48-hour warning → battery and water tank full; cyclone-rated structure; dynamic clinic reserve; mill paused; "
         "homes in essentials mode."),
    ]),
    "heat": dict(pt="Onda de calor", en="Heatwave", G=950, T=45, v=2, gust=6, aod=0.3, snow=0, soil=8, chain=[
        ("Ameaça", "Hazard", "Calor de 42–48 °C e noites acima de 30 °C (Sahel, Abril a Junho).",
         "Heat of 42–48 °C and nights above 30 °C (Sahel, April to June)."),
        ("Física", "Physics", "Painel a 70 °C perde ~15 % (−0,35 %/°C); inversor acima de 45 °C reduz potência; bateria "
         "acima de 45 °C limita a carga e envelhece mais depressa.", "A panel at 70 °C loses ~15 % (−0.35 %/°C); the inverter "
         "derates above 45 °C; above 45 °C the battery limits charging and ages faster."),
        ("Energia", "Energy", "Há sol, mas a cadeia painel → inversor → bateria perde 20–35 % da capacidade útil.",
         "There is sun, but the panel → inverter → battery chain loses 20–35 % of usable capacity."),
        ("Serviços", "Services", "A procura dispara: ventilação na clínica, frio das vacinas, mais água (+40 %).",
         "Demand soars: clinic ventilation, vaccine cooling, more water (+40 %)."),
        ("Resposta RESILIA", "RESILIA response", "Contentor climatizado e sombreado; bombagem ao meio-dia; reserva nocturna "
         "para a clínica; lavagem dos painéis.", "Shaded, ventilated enclosure; pumping at midday; night-time reserve for the "
         "clinic; panel washing."),
    ]),
    "snow": dict(pt="Neve e frio", en="Snow and cold", G=500, T=-6, v=5, gust=14, aod=0.0, snow=80, soil=0, chain=[
        ("Ameaça", "Hazard", "Tempestade de neve no Alto Atlas: −10 °C, 30 cm de neve, aldeias isoladas.",
         "Snowstorm in the High Atlas: −10 °C, 30 cm of snow, villages cut off."),
        ("Física", "Physics", "1 cm de neve cobre o painel; as baterias de lítio (LFP) NÃO podem carregar abaixo de 0 °C; "
         "o frio reduz a capacidade útil.", "1 cm of snow covers the panel; lithium (LFP) batteries CANNOT charge below "
         "0 °C; cold reduces usable capacity."),
        ("Energia", "Energy", "Mesmo com o céu limpo após a tempestade, a bateria gelada não aceita a energia do sol.",
         "Even with clear skies after the storm, the frozen battery cannot take in solar energy."),
        ("Serviços", "Services", "Aquecimento e iluminação na clínica, comunicações com o exterior, água.",
         "Heating and lighting at the clinic, communications with the outside world, water."),
        ("Resposta RESILIA", "RESILIA response", "Contentor isolado e aquecido (pouca energia, desbloqueia a carga); "
         "painéis mais inclinados; técnico local limpa a neve duas vezes por dia.", "Insulated, heated enclosure (little "
         "energy, unblocks charging); steeper panel tilt; local technician clears snow twice a day."),
    ]),
    "dust": dict(pt="Tempestade de poeira", en="Dust storm", G=600, T=38, v=12, gust=20, aod=1.5, snow=0, soil=15, chain=[
        ("Ameaça", "Hazard", "Harmatão e tempestades de poeira (haboob) no Sahel.", "Harmattan and dust storms (haboob) in the Sahel."),
        ("Física", "Physics", "A poeira no ar bloqueia a luz directa; a poeira depositada suja os painéis (até 3–5 %/dia).",
         "Airborne dust blocks direct light; settled dust soils the panels (up to 3–5 %/day)."),
        ("Energia", "Energy", "Perdas que se acumulam até à próxima chuva: 10–30 % em poucos dias.",
         "Losses accumulate until the next rain: 10–30 % within a few days."),
        ("Serviços", "Services", "Doenças respiratórias (procura na clínica), equipamentos a aquecer.",
         "Respiratory illness (clinic demand), overheating equipment."),
        ("Resposta RESILIA", "RESILIA response", "Dados reais de poeira (CAMS) e lavagem planeada dos painéis pelo técnico local.",
         "Real dust data (CAMS) and scheduled panel washing by the local technician."),
    ]),
    "flood": dict(pt="Chuva e cheia", en="Rain and flood", G=200, T=25, v=6, gust=12, aod=0.0, snow=0, soil=0, chain=[
        ("Ameaça", "Hazard", "Chuvas torrenciais de 100+ mm em 72 h; cheias repentinas.", "Torrential rain of 100+ mm in 72 h; flash floods."),
        ("Física", "Physics", "Céu coberto dias seguidos; estradas de terra intransitáveis.", "Overcast for days on end; dirt roads impassable."),
        ("Energia", "Energy", "Produção solar a 20–40 % do normal; sem reabastecimento de gasóleo.",
         "Solar output at 20–40 % of normal; no diesel resupply."),
        ("Serviços", "Services", "Água contaminada (cólera), feridos, desalojados no abrigo.",
         "Contaminated water (cholera), injuries, displaced people in the shelter."),
        ("Resposta RESILIA", "RESILIA response", "Bateria e depósito de água cheios antes; bombagem e cloração como carga "
         "crítica; equipamento elevado acima da cota de cheia.", "Battery and water tank full beforehand; pumping and "
         "chlorination as critical loads; equipment raised above flood level."),
    ]),
}


def _chain(p):
    return [(T(a, b), T(c, d)) for a, b, c, d in p["chain"]]


def render(ctx):
    page_header(T("Laboratório do clima", "Climate lab"),
                T("O que cada tipo de clima faz a uma mini-rede", "What each type of weather does to a mini-grid"),
                T("Escolha uma condição e mexa nos valores. Vê, passo a passo, quanta energia chega realmente à "
                  "comunidade e porquê. São as mesmas equações do simulador de 72 h.",
                  "Pick a condition and adjust the values. See, step by step, how much energy actually reaches the "
                  "community and why. These are the same equations used by the 72-hour simulator."))
    pre = st.segmented_control(T("Condição", "Condition"), list(PRESETS), key="lab_preset", default="normal",
                               format_func=lambda k: T(PRESETS[k]["pt"], PRESETS[k]["en"]), label_visibility="collapsed")
    pre = pre or "normal"
    p = PRESETS[pre]
    k = pre
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        G = st.slider(T("Sol no painel (W/m²)", "Sun on panel (W/m²)"), 0, 1100, p["G"], 10, key=f"G{k}")
        Ta = st.slider(T("Temperatura do ar (°C)", "Air temperature (°C)"), -15, 50, p["T"], 1, key=f"T{k}")
    with c2:
        v = st.slider(T("Vento médio a 10 m (m/s)", "Mean wind at 10 m (m/s)"), 0, 40, p["v"], 1, key=f"v{k}")
        gust = st.slider(T("Rajada (m/s)", "Gust (m/s)"), 0, 70, p["gust"], 1, key=f"g{k}")
    with c3:
        aod = st.slider(T("Poeira no ar (AOD acima do normal)", "Airborne dust (AOD above normal)"), 0.0, 2.0,
                        float(p["aod"]), 0.1, key=f"a{k}")
        snow = st.slider(T("Neve sobre os painéis (%)", "Snow on panels (%)"), 0, 100, p["snow"], 5, key=f"s{k}")
    with c4:
        soil = st.slider(T("Sujidade nos painéis (%)", "Panel soiling (%)"), 0, 40, p["soil"], 1, key=f"d{k}")
        hardened = st.toggle(T("Estrutura anti-ciclone", "Cyclone-rated structure"), True, key=f"h{k}")
        climate = st.toggle(T("Contentor de baterias climatizado", "Climate-controlled battery enclosure"), True, key=f"c{k}")

    f_irr = G / 1000
    f_dust = max(0.6, 1 - 0.20 * aod)
    poa = G * f_dust
    tc = Ta + (NOCT - 20) * poa / 800 * 9.5 / (5.7 + 3.8 * v)
    f_temp = 1 + GAMMA * (tc - 25)
    dmg = float(pv_damage(np.array([gust]), hardened)[0])
    dmg_std = float(pv_damage(np.array([gust]), False)[0])
    cur = 100.0
    out = []
    for name, f in [(T("Nuvens / hora do dia", "Clouds / time of day"), f_irr), (T("Poeira no ar", "Airborne dust"), f_dust),
                    (T("Calor na célula", "Cell heat"), f_temp), (T("Perdas eléctricas", "Electrical losses"), PR_PV),
                    (T("Neve", "Snow"), 1 - snow / 100), (T("Sujidade", "Soiling"), 1 - soil / 100),
                    (T("Danos do vento", "Wind damage"), 1 - dmg)]:
        new = cur * f
        out.append((name, new - cur))
        cur = new
    wf = [(T("Painel ideal (1000 W/m², 25 °C)", "Ideal panel (1000 W/m², 25 °C)"), 100.0)] + out + \
         [(T("Energia real", "Real energy"), cur)]

    vh = v * (24 / 10) ** 0.14
    gh = gust * (24 / 10) ** 0.07
    stopped = vh >= 20 or gh >= 30
    vin, vr = 2.5, 11.0
    p_turb = 0 if stopped else 100 * float(np.clip((vh ** 3 - vin ** 3) / (vr ** 3 - vin ** 3), 0, 1))
    tb = min(max(Ta, 16), 30) if climate else Ta + 4
    chg = 0 if tb < 0 else 30 if tb < 10 else 100 if tb <= 45 else 50 if tb <= 55 else 0
    capf = 100 * min(1, max(0.7, 1 - 0.006 * max(15 - tb, 0)))
    ti = (min(Ta, 32) if climate else Ta) + 6
    invf = 100 * min(1, max(0, 1 - (ti - 45) / 20))

    a, b, c, d = st.columns(4)
    with a:
        card(T("Painéis solares", "Solar panels"), f"{cur:.0f} %",
             T(f"da potência nominal · célula a {tc:.0f} °C", f"of rated power · cell at {tc:.0f} °C"), C["solar"])
    with b:
        card(T("Aerogerador", "Wind turbine"), T("PARADO", "STOPPED") if stopped else f"{p_turb:.0f} %",
             T(f"vento à altura da turbina {vh:.0f} m/s", f"wind at hub height {vh:.0f} m/s")
             + (T(" — paragem de segurança", " — safety shutdown") if stopped else ""), C["wind"])
    with c:
        card(T("Bateria pode carregar", "Battery can charge"), f"{chg} %",
             T(f"bateria a {tb:.0f} °C · capacidade útil {capf:.0f} %", f"battery at {tb:.0f} °C · usable capacity {capf:.0f} %"),
             C["bat"] if chg == 100 else C["red"])
    with d:
        card(T("Inversor", "Inverter"), f"{invf:.0f} %", T(f"electrónica a {ti:.0f} °C", f"electronics at {ti:.0f} °C"),
             C["prod"] if invf >= 99 else C["red"])

    l, r = st.columns([3, 2])
    with l:
        st.plotly_chart(charts.waterfall(wf), width="stretch")
    with r:
        st.plotly_chart(charts.wind_curve(vh, gh, stopped), width="stretch")

    msgs = []
    if f_irr < 0.3:
        msgs.append(T(f"Com {G} W/m² o painel recebe {100 * f_irr:.0f} % do sol de referência: é por isso que um ciclone "
                      "ou uma frente de chuva derruba a produção, mesmo ao meio-dia.",
                      f"At {G} W/m² the panel receives {100 * f_irr:.0f} % of reference sunlight: this is why a cyclone or "
                      "a rain front collapses output, even at midday."))
    if tc > 50:
        msgs.append(T(f"A célula chega a <b>{tc:.0f} °C</b>; cada grau acima de 25 °C tira 0,35 % de potência "
                      f"(aqui −{100 * (1 - f_temp):.0f} %). O vento arrefece o painel: experimente subir o vento.",
                      f"The cell reaches <b>{tc:.0f} °C</b>; each degree above 25 °C costs 0.35 % of power "
                      f"(here −{100 * (1 - f_temp):.0f} %). Wind cools the panel: try raising the wind speed."))
    if Ta < 5 and v > 0:
        msgs.append(T("O frio <b>melhora</b> o rendimento do painel, mas é a bateria que trava o sistema.",
                      "Cold <b>improves</b> panel efficiency, but the battery is what holds the system back."))
    if chg == 0 and tb < 0:
        msgs.append(T(f"<b>Bateria a {tb:.0f} °C: carga proibida.</b> O lítio-ferro-fosfato forma depósitos metálicos se for "
                      "carregado abaixo de 0 °C, por isso o BMS bloqueia. Ligue o contentor climatizado.",
                      f"<b>Battery at {tb:.0f} °C: charging blocked.</b> Lithium iron phosphate forms metallic deposits if "
                      "charged below 0 °C, so the BMS blocks it. Switch on the climate-controlled enclosure."))
    if invf < 99:
        msgs.append(T(f"O inversor a {ti:.0f} °C só entrega {invf:.0f} % da potência. Num contentor ventilado e sombreado "
                      "fica abaixo de 45 °C.",
                      f"At {ti:.0f} °C the inverter delivers only {invf:.0f} % of its power. In a ventilated, shaded "
                      "enclosure it stays below 45 °C."))
    if stopped:
        msgs.append(T("Paradoxo da tempestade: <b>mais vento não dá mais energia</b>. Acima de ~20 m/s a turbina pára para não se destruir.",
                      "The storm paradox: <b>more wind does not mean more energy</b>. Above ~20 m/s the turbine shuts down to avoid destruction."))
    if dmg_std > 0.05:
        hard = 100 * float(pv_damage(np.array([gust]), True)[0])
        msgs.append(T(f"Com rajadas de {gust} m/s ({3.6 * gust:.0f} km/h), uma estrutura comum perde ~{100 * dmg_std:.0f} % "
                      f"dos painéis; a estrutura anti-ciclone perde {hard:.0f} %.",
                      f"With {gust} m/s gusts ({3.6 * gust:.0f} km/h), a standard structure loses ~{100 * dmg_std:.0f} % "
                      f"of its panels; the cyclone-rated structure loses {hard:.0f} %."))
    if aod > 0.5:
        msgs.append(T("A poeira no ar bloqueia sobretudo a luz directa. Depois de assentar, suja os painéis até à próxima chuva ou lavagem.",
                      "Airborne dust mainly blocks direct light. Once it settles, it soils the panels until the next rain or wash."))
    for m in msgs:
        st.markdown(f"- {m}", unsafe_allow_html=True)

    if p["chain"]:
        st.markdown(f"#### {T('Cadeia de impacto: do céu à clínica', 'Impact chain: from the sky to the clinic')}")
        chain(_chain(p))
    with st.expander(T("Ver as cadeias de impacto de todas as ameaças", "See the impact chains for every hazard"),
                     icon=":material/account_tree:"):
        for pp in PRESETS.values():
            if pp["chain"]:
                st.markdown(f"**{T(pp['pt'], pp['en'])}**")
                chain(_chain(pp))

    st.markdown(f"#### {T('Um dia inteiro nestas condições', 'A full day under these conditions')}")
    h = np.arange(24)
    shape = np.clip(np.sin(np.pi * (h - 6) / 12), 0, None)
    pv_h = shape * cur / 100 * ctx.hw["pv_kwp"]
    ref = shape * ctx.hw["pv_kwp"] * PR_PV
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=h, y=ref, name=T("Dia limpo de referência", "Clear reference day"),
                             line=dict(color="#94A3B8", dash="dot")))
    fig.add_trace(go.Scatter(x=h, y=pv_h, name=T("Nestas condições", "Under these conditions"), fill="tozeroy",
                             line=dict(color=C["solar"], width=3), fillcolor="rgba(242,169,0,.20)"))
    fig.update_layout(xaxis_title=T("Hora do dia", "Hour of day"),
                      yaxis_title=T(f"kW (sistema de {ctx.hw['pv_kwp']:.0f} kWp)", f"kW ({ctx.hw['pv_kwp']:.0f} kWp system)"))
    st.plotly_chart(charts.base(fig, T(f"Produção solar estimada: {pv_h.sum():.0f} kWh/dia (referência {ref.sum():.0f} kWh)",
                                       f"Estimated solar output: {pv_h.sum():.0f} kWh/day (reference {ref.sum():.0f} kWh)"),
                                height=320), width="stretch")
