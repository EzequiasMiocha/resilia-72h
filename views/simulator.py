"""Simulador 24 h: como o sistema off-grid equilibra oferta e procura ao longo de um dia."""
import io

import pandas as pd
import streamlit as st

from resilia import model as M
from ui import charts
from ui.i18n import T, date_txt, day_label, num, verdict_txt
from ui.style import C, card, explain, page_header

VCOL = {"ok": "#16A34A", "partial": "#B45309", "fragile": C["red"]}


def _verdict_box(v, risk, hours):
    txt = {
        "ok": T("O sistema serve toda (ou quase toda) a procura neste dia.",
                "The system serves all (or almost all) demand on this day."),
        "partial": T(f"Faltaram {num(risk)} % da energia, em {hours} h. Cortes curtos.",
                     f"{num(risk)} % of the energy was missing, over {hours} h. Short cuts."),
        "fragile": T(f"Faltaram {num(risk)} % da energia, em {hours} h. A aldeia fica sem luz várias horas.",
                     f"{num(risk)} % of the energy was missing, over {hours} h. The village is without power for hours."),
    }[v]
    st.markdown(f'<div class="explain" style="border-left-color:{VCOL[v]}"><b style="color:{VCOL[v]}">'
                f'{verdict_txt(v)}</b> &nbsp;{txt}</div>', unsafe_allow_html=True)


def _plain(o, m):
    """O dia contado em palavras simples."""
    soc0, soc1 = 100 * o["soc"].iloc[0], m["soc_end"]
    txt = T(f"Os painéis solares produziram <b>{num(m['pv'])} kWh</b> e a aldeia pediu <b>{num(m['demand'])} kWh</b>. "
            f"A bateria começou o dia com {num(soc0)} % e terminou com {num(soc1)} %. ",
            f"The solar panels produced <b>{num(m['pv'])} kWh</b> and the village asked for <b>{num(m['demand'])} kWh</b>. "
            f"The battery started the day at {num(soc0)} % and ended at {num(soc1)} %. ")
    cut = o.index.hour[o["unmet"] > 0.01 * o["demand"]]
    if len(cut):
        txt += T(f"Faltaram <b>{num(m['unmet'])} kWh</b> em {len(cut)} horas, entre as {cut.min():02d}h e as {cut.max():02d}h, "
                 "quando a bateria chegou ao mínimo. Um sistema resiliente evita isto com mais bateria ou mais painéis.",
                 f"<b>{num(m['unmet'])} kWh</b> were missing over {len(cut)} hours, between {cut.min():02d}h and {cut.max():02d}h, "
                 "when the battery reached its minimum. A resilient system avoids this with more battery or more panels.")
    else:
        txt += T("A aldeia teve energia <b>em todas as horas</b>: de dia veio do sol, à noite veio da bateria.",
                 "The village had power <b>every hour</b>: from the sun by day and from the battery at night.")
    if m["waste"] > 1:
        txt += T(f" Sobrou {num(m['waste'])} % da energia solar, que pode servir novos usos durante o dia.",
                 f" {num(m['waste'])} % of the solar energy was left over and could serve new daytime uses.")
    st.markdown(f'<div class="plain"><div class="h">{T("O dia em palavras simples", "The day in plain words")}</div>{txt}</div>',
                unsafe_allow_html=True)


def render(ctx):
    s, res, D = ctx.system, ctx.res, ctx.dem["total"].values
    page_header(T("Simulador 24 h", "24-hour simulator"),
                T("Como o sistema equilibra a oferta e a procura num dia", "How the system balances supply and demand in a day"),
                T("Escolha o tipo de dia. O sistema solar (painel à esquerda) é testado hora a hora com o sol e o consumo "
                  "reais de Mabote. A bateria começa o dia no estado em que estaria depois dos 7 dias reais anteriores.",
                  "Choose the type of day. The solar system (left panel) is tested hour by hour with Mabote's real sun and "
                  "demand. The battery starts the day where it would be after the 7 real days before."))

    steps = [T("Escolha a aldeia e o sistema no painel à esquerda.", "Choose the village and the system in the left panel."),
             T("Escolha um tipo de dia (sol, nuvens, chuva, calor).", "Choose a type of day (sun, clouds, rain, heat)."),
             T("Leia o resumo e o gráfico: amarelo é sol, azul é bateria, preto é falta.",
               "Read the summary and the chart: yellow is sun, blue is battery, black is missing.")]
    st.markdown('<div class="steps">' + "".join(f'<div class="s"><div class="n">{i + 1}</div><div>{x}</div></div>'
                                                for i, x in enumerate(steps)) + "</div>", unsafe_allow_html=True)

    keys = M.DAY_TYPES
    st.session_state.setdefault("day_type", "cloudy")
    k = st.segmented_control(T("Tipo de dia", "Type of day"), keys, key="day_type", format_func=day_label)
    k = k or "cloudy"
    day = ctx.days[k]
    with st.expander(T("Ou escolha outra data real (2016–2025)", "Or choose another real date (2016–2025)"),
                     icon=":material/calendar_month:"):
        pick = st.date_input(T("Data", "Date"), value=None, min_value=pd.Timestamp("2016-01-08").date(),
                             max_value=pd.Timestamp("2025-12-31").date(), key="day_pick")
        if pick:
            day = pd.Timestamp(pick)
    o = M.simulate_day(res, D, s, day)
    m = M.day_metrics(o, s)
    v = M.verdict(m["risk"])
    m_ghi = res.loc[o.index, "ghi"].sum() / 1000
    st.caption(T(f"Dia real: **{date_txt(day)}** · sol: {num(m_ghi, 1)} kWh/m² · produção solar: {num(m['pv'])} kWh · "
                 f"procura: {num(m['demand'])} kWh",
                 f"Real day: **{date_txt(day)}** · sun: {num(m_ghi, 1)} kWh/m² · solar output: {num(m['pv'])} kWh · "
                 f"demand: {num(m['demand'])} kWh"))

    c = st.columns(4)
    with c[0]:
        card(T("Risco de interrupção", "Interruption risk"), f"{num(m['risk'], 1)} %",
             T(f"energia em falta: {num(m['unmet'])} kWh", f"energy missing: {num(m['unmet'])} kWh"), VCOL[v])
    with c[1]:
        card(T("Horas com interrupção", "Hours with interruption"), f"{m['hours']} h", T("em 24 horas", "in 24 hours"), C["unmet"])
    with c[2]:
        card(T("Bateria", "Battery"), f"{num(100 * o['soc'].iloc[0])} % → {num(m['soc_end'])} %",
             T(f"início → fim do dia · autonomia {num(m['autonomy'])} h", f"start → end of day · autonomy {num(m['autonomy'])} h"),
             C["bat"])
    with c[3]:
        card(T("Excedente solar", "Solar surplus"), f"{num(m['waste'])} %",
             T("bateria cheia: livre para novos usos de dia", "battery full: free for new daytime uses"), C["solar"])
    _verdict_box(v, m["risk"], m["hours"])
    _plain(o, m)

    st.plotly_chart(charts.balance24(o, T("Balanço de 24 horas: oferta × procura", "24-hour balance: supply × demand")),
                    width="stretch")
    explain(T("Como ler:", "How to read:"),
            T("as barras acima de zero mostram de onde vem a energia em cada hora (amarelo = sol, "
              "azul = bateria). A parte preta é energia que faltou (interrupção). As barras abaixo de zero são o excedente "
              "guardado na bateria. A linha escura é a procura e a linha vermelha pontilhada é a carga da bateria.",
              "bars above zero show where each hour's energy comes from (yellow = solar, blue = battery). "
              "The black part is energy that was missing (interruption). Bars below zero are surplus stored in the battery. "
              "The dark line is demand and the dotted red line is the battery charge."))

    # teste de resiliência: o mesmo sistema nos 5 tipos de dia
    st.markdown(f"### {T('Teste de resiliência em 24 horas', '24-hour resilience test')}")
    st.caption(T("O mesmo sistema, testado nos 5 tipos de dia reais. Um sistema resiliente passa em todos.",
                 "The same system, tested on the 5 real day types. A resilient system passes them all."))
    cells = ""
    for kk in keys:
        oo = M.simulate_day(res, D, s, ctx.days[kk])
        mm = M.day_metrics(oo, s)
        vv = M.verdict(mm["risk"])
        cells += (f'<div class="k" style="border-top:4px solid {VCOL[vv]}"><div class="u"><b>{day_label(kk)}</b></div>'
                  f'<div class="n" style="color:{VCOL[vv]};font-size:26px">{num(mm["risk"], 1)} %</div>'
                  f'<div class="u">{T("em falta", "missing")} · {mm["hours"]} h</div>'
                  f'<div class="u" style="color:{VCOL[vv]};font-weight:700">{verdict_txt(vv)}</div></div>')
    st.markdown(f'<div class="big" style="grid-template-columns:repeat(5,1fr)">{cells}</div>', unsafe_allow_html=True)

    st.plotly_chart(charts.demand_profile(ctx.dem.loc[o.index], T("A procura neste dia, por serviço",
                                                                    "Demand on this day, by service")), width="stretch")

    with st.expander(T("Tabela hora a hora e exportação", "Hourly table and export"), icon=":material/table_chart:"):
        tab = pd.DataFrame({
            T("Hora", "Hour"): [f"{h:02d}h" for h in o.index.hour],
            T("Procura (kW)", "Demand (kW)"): o["demand"].round(1),
            T("Sol (kW)", "Solar (kW)"): o["pv"].round(1),
            T("Bateria entrega (kW)", "Battery out (kW)"): o["bat_dis"].round(1),
            T("Bateria guarda (kW)", "Battery in (kW)"): o["bat_ch"].round(1),
            T("Em falta (kW)", "Missing (kW)"): o["unmet"].round(1),
            T("Bateria (%)", "Battery (%)"): (100 * o["soc"]).round(0),
        })
        st.dataframe(tab, hide_index=True, width="stretch")
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as xw:
            tab.to_excel(xw, sheet_name=T("Balanco_24h", "Balance_24h"), index=False)
        st.download_button(T("Descarregar em Excel", "Download as Excel"), buf.getvalue(), f"resilia_24h_{day:%Y%m%d}.xlsx",
                           icon=":material/download:",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with st.expander(T("Como é feito o cálculo", "How the calculation works"), icon=":material/functions:"):
        st.markdown(T("""
1. **Sol:** produção = potência dos painéis × sol no painel ÷ 1000 × perdas (0,88) × efeito da temperatura (−0,35 % por °C acima de 25 °C).
2. **Procura:** número de famílias × consumo típico de cada hora + centro de saúde, escola, bomba de água, moagem e iluminação pública. Varia com a hora, o dia da semana, o calor e de dia para dia.
3. **Balanço de cada hora:** o sol serve a procura; o excedente carrega a bateria; o que falta sai da bateria (até 20 % de carga mínima); o resto é **energia em falta**.
4. **Risco de interrupção** = energia em falta ÷ procura total do dia.

Dados: reanálise ERA5 (Copernicus/ECMWF), Mabote, 2015–2025, hora a hora.
""", """
1. **Solar:** output = panel power × sun on the panel ÷ 1000 × losses (0.88) × temperature effect (−0.35 % per °C above 25 °C).
2. **Demand:** number of households × typical hourly use + health centre, school, water pump, grain mill and street lighting. Varies with the hour, the weekday, heat and from day to day.
3. **Hourly balance:** the sun serves demand; surplus charges the battery; shortfalls are drawn from the battery (down to a 20 % minimum); the rest is **energy missing**.
4. **Interruption risk** = energy missing ÷ total demand of the day.

Data: ERA5 reanalysis (Copernicus/ECMWF), Mabote, 2015–2025, hourly.
"""))
