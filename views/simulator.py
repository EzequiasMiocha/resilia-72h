"""Simulador 72 h — explorar qualquer evento, país e equipamento (bilingue)."""
import io

import numpy as np
import pandas as pd
import streamlit as st

from resilia.data import sim_slice
from ui import charts
from ui.i18n import T, date_long, event, month_short, num, phase, site as site_txt
from ui.style import chips, explain, legend, page_header, versus

from .pitch import _board, _dot, _weather_words


def _verdict(ctx):
    mc, mr = ctx.mc, ctx.mr
    if mr["crit_out_h"] == 0 and mc["crit_out_h"] > 0:
        return T(f"Com o mesmo equipamento, o centro de saúde ficaria <b>{mc['crit_out_h']} h às escuras</b> com a gestão "
                 f"de hoje. Com o RESILIA fica <b>sempre ligado</b>.",
                 f"With the same equipment, the health centre would be <b>dark for {mc['crit_out_h']} h</b> under today's "
                 f"operation. With RESILIA it stays <b>on the whole time</b>.")
    if mc["crit_out_h"] == 0 and mr["crit_out_h"] == 0:
        return T("Este evento não chega para apagar a clínica com este equipamento, em nenhuma das gestões. Experimente "
                 "agravar o evento ou reduzir o equipamento no painel à esquerda.",
                 "This event is not severe enough to switch off the clinic with this equipment under either strategy. "
                 "Try intensifying the event or reducing the equipment in the left panel.")
    return T(f"Clínica sem energia: <b>{mc['crit_out_h']} h</b> (hoje) contra <b>{mr['crit_out_h']} h</b> (RESILIA). "
             "O equipamento não chega para este evento: veja a página «Dimensionar».",
             f"Clinic without power: <b>{mc['crit_out_h']} h</b> (today) vs <b>{mr['crit_out_h']} h</b> (RESILIA). "
             "The equipment is not enough for this event: see the “System sizing” page.")


def render(ctx):
    s, w, oc, orr, mc, mr = ctx.site, ctx.w, ctx.oc, ctx.orr, ctx.mc, ctx.mr
    k = ctx.site_key
    page_header(T("Simulador 72 h", "72-hour simulator"),
                f"{ctx.ev_label} · {site_txt(k, 'name')}, {site_txt(k, 'country')}",
                T(f"{ctx.start:%d/%m/%Y %H:%M} → {ctx.end:%d/%m/%Y %H:%M}. Clima real, hora a hora. Simulamos 48 h antes "
                  "(aviso), as 72 h do evento e 24 h depois. Mude o país, o evento ou o equipamento no painel à esquerda.",
                  f"{ctx.start:%d/%m/%Y %H:%M} → {ctx.end:%d/%m/%Y %H:%M}. Real weather, hour by hour. We simulate 48 h "
                  "before (warning), the 72-hour event and 24 h after. Change the country, event or equipment in the left panel."))

    # barra de resumo flutuante
    with st.container(key="simbar"):
        st.markdown(f"""<div class="simbar">
<span class="lbl">{T("Resumo do evento", "Event summary")}</span>
<span>{T("Clínica sem energia", "Clinic unpowered")}: <span class="g">{mc['crit_out_h']} h</span> → <span class="r">{mr['crit_out_h']} h</span></span>
<span>{T("Água", "Water")}: <span class="g">{num(mc['water_pct'])}%</span> → <span class="r">{num(mr['water_pct'])}%</span></span>
<span>{T("Casas com luz", "Homes with light")}: <span class="g">{num(mc['essmin_pct'])}%</span> → <span class="r">{num(mr['essmin_pct'])}%</span></span>
<span>{T("Apagão total", "Total blackout")}: <span class="g">{mc['blackout_h']} h</span> → <span class="r">{mr['blackout_h']} h</span></span>
<span style="margin-left:auto">{_dot("#9AA3AF")}{T("hoje", "today")} &nbsp; {_dot("#C8102E")}RESILIA</span>
</div>""", unsafe_allow_html=True)

    explain(T("Em resumo:", "In short:"), _verdict(ctx))

    ev = w[w["fase"] == "evento"]
    nw = sim_slice(ctx.df, ctx.wins["normal"])
    sol_norm = nw[nw["fase"] == "evento"]["shortwave_radiation"].sum()
    items = [(T(f"Sol: {num(100 * ev['shortwave_radiation'].sum() / max(sol_norm, 1))} % do normal",
                f"Sun: {num(100 * ev['shortwave_radiation'].sum() / max(sol_norm, 1))} % of normal"), "red"),
             (T(f"Rajadas até {num(3.6 * ev['wind_gusts_10m'].max())} km/h",
                f"Gusts up to {num(3.6 * ev['wind_gusts_10m'].max())} km/h"), ""),
             (T(f"{num(ev['precipitation'].sum())} mm de chuva", f"{num(ev['precipitation'].sum())} mm of rain"), ""),
             (f"{num(ev['temperature_2m'].min())} {T('a', 'to')} {num(ev['temperature_2m'].max())} °C", "")]
    if ev["snowfall"].sum() > 0.5:
        items.append((T(f"{num(ev['snowfall'].sum())} cm de neve", f"{num(ev['snowfall'].sum())} cm of snow"), "red"))
    if ev["dust"].max() > 300:
        items.append((T(f"Poeira até {num(ev['dust'].max())} µg/m³", f"Dust up to {num(ev['dust'].max())} µg/m³"), "red"))
    if ctx.stress:
        items.append((T(f"Agravado +{ctx.stress} %", f"Intensified +{ctx.stress} %"), "gold"))
    if ctx.future:
        items.append((T("Clima 2050", "2050 climate"), "gold"))
    chips(items)
    if ctx.event:
        with st.expander(T("O que aconteceu neste evento", "What happened in this event"), icon=":material/history_edu:"):
            st.markdown(event(ctx.ev_key, "story"))

    _balance24(ctx)
    st.markdown(f"### {T('O evento completo (72 h)', 'The full event (72 h)')}")

    c = st.columns(4)
    with c[0]:
        versus(T("Clínica sem energia", "Clinic without power"), f"{mc['crit_out_h']} h", f"{mr['crit_out_h']} h",
               T(f"vacinas: {'protegidas' if mr['cold_chain_ok'] else 'em risco'} com RESILIA",
                 f"vaccines: {'protected' if mr['cold_chain_ok'] else 'at risk'} with RESILIA"))
    with c[1]:
        versus(T("Água potável entregue", "Drinking water delivered"), f"{num(mc['water_pct'])}%", f"{num(mr['water_pct'])}%",
               T(f"≈ {num(mr['people_water'])} pessoas/dia (15 L)", f"≈ {num(mr['people_water'])} people/day (15 L)"))
    with c[2]:
        versus(T("Casas com luz e telemóvel", "Homes with lights and phone"), f"{num(mc['essmin_pct'])}%",
               f"{num(mr['essmin_pct'])}%", T("percentagem do tempo", "share of the time"))
    with c[3]:
        versus(T("Horas de apagão total", "Hours of total blackout"), f"{mc['blackout_h']} h", f"{mr['blackout_h']} h",
               T("o RESILIA desliga por ordem, nunca tudo", "RESILIA switches off in order, never everything"))
    with st.expander(T("Mais indicadores", "More indicators"), icon=":material/analytics:"):
        c = st.columns(4)
        with c[0]:
            versus(T("Cargas críticas servidas", "Critical loads served"), f"{num(mc['crit_pct'])}%", f"{num(mr['crit_pct'])}%")
        with c[1]:
            nr = T("não recupera", "no recovery")
            versus(T("Recuperação após o evento", "Recovery after the event"),
                   nr if ctx.rec_c is None else f"{ctx.rec_c} h", nr if ctx.rec_r is None else f"{ctx.rec_r} h",
                   T("até serviço completo e bateria ≥ 50 %", "until full service and battery ≥ 50 %"))
        with c[2]:
            versus(T("Gasóleo consumido", "Diesel used"), f"{num(mc['diesel_L'])} L", f"{num(mr['diesel_L'])} L",
                   T("sem gerador nesta configuração", "no generator in this configuration") if not ctx.hw["diesel_kw"]
                   else f"CO₂ {num(mr['co2_kg'])} kg")
        with c[3]:
            versus(T("Índice RESILIA (0–100)", "RESILIA index (0–100)"), num(mc["index"]), num(mr["index"]),
                   T("saúde 50 % · luz 25 % · água 15 % · total 10 %", "health 50 % · light 25 % · water 15 % · total 10 %"))

    st.markdown(f"### {T('Quem tem energia, hora a hora?', 'Who has power, hour by hour?')}")
    legend(charts.status_legend())
    st.plotly_chart(charts.services_heatmap(oc, False, T("SISTEMA DE HOJE", "TODAY'S SYSTEM")), width="stretch")
    st.plotly_chart(charts.services_heatmap(orr, True, T("COM RESILIA", "WITH RESILIA")), width="stretch")
    st.caption(T("Cada quadrado é uma hora; as linhas vermelhas pontilhadas marcam o início e o fim do evento.",
                 "Each square is one hour; the dotted red lines mark the start and end of the event."))

    st.markdown(f"### {T('Reviver uma hora do evento', 'Replay one hour of the event')}")
    n = len(orr)
    ev_idx = np.flatnonzero((orr["fase"] == "evento").values)
    t = st.slider(T("Hora", "Hour"), 0, n - 1, int(ev_idx[0] + 12) if len(ev_idx) else 0, key="sim_hour",
                  help=T("0 = 48 h antes do evento; o evento vai da hora 48 à 119.",
                         "0 = 48 h before the event; the event runs from hour 48 to 119."))
    st.markdown(f"<div style='font-size:19px;font-weight:800'>{date_long(orr.index[t])} · {phase(orr['fase'].iloc[t])}</div>"
                f"{_weather_words(w, t)}", unsafe_allow_html=True)
    met = s["met_service"].split(" ")[0]
    st.markdown(f"""<div class="duo">
<div class="side today"><div class="tt">{_dot("#9AA3AF")}{T("Sistema de hoje", "Today's system")}</div>{_board(oc, t, False, met)}</div>
<div class="side res"><div class="tt">{_dot("#C8102E")}{T("Com RESILIA", "With RESILIA")}</div>{_board(orr, t, True, met)}</div></div>""",
                unsafe_allow_html=True)
    notes = _physics_notes(orr, oc, t)
    if notes:
        st.markdown(f"**{T('Física nesta hora:', 'Physics at this hour:')}** " + "; ".join(notes) + ".", unsafe_allow_html=True)

    st.markdown(f"### {T('Detalhes técnicos', 'Technical details')}")
    tabs = st.tabs([T("Clima", "Weather"), T("Energia RESILIA", "RESILIA energy"), T("Energia hoje", "Today's energy"),
                    T("Bateria e gasóleo", "Battery and diesel"), T("O que aprendemos", "Lessons learned"),
                    T("Exportar", "Export")])
    with tabs[0]:
        st.plotly_chart(charts.weather(orr, w), width="stretch")
    with tabs[1]:
        st.plotly_chart(charts.supply(orr, T("Para onde vai a energia (RESILIA)", "Where the energy goes (RESILIA)")), width="stretch")
        st.plotly_chart(charts.sources(orr, T("De onde vem a energia (RESILIA)", "Where the energy comes from (RESILIA)")), width="stretch")
    with tabs[2]:
        st.plotly_chart(charts.supply(oc, T("Para onde vai a energia (sistema de hoje)", "Where the energy goes (today's system)")), width="stretch")
        st.plotly_chart(charts.sources(oc, T("De onde vem a energia (sistema de hoje)", "Where the energy comes from (today's system)")), width="stretch")
    with tabs[3]:
        st.plotly_chart(charts.soc(oc, orr), width="stretch")
        explain(T("A linha tracejada", "The dashed line"),
                T("é a reserva que o RESILIA guarda para a clínica até ao fim do evento. Abaixo dela, a bateria só alimenta cargas críticas.",
                  "is the reserve RESILIA keeps for the clinic until the end of the event. Below it, the battery only supplies critical loads."))
        if ctx.hw["diesel_kw"]:
            st.plotly_chart(charts.fuel(oc, orr, ctx.hw["fuel_l"]), width="stretch")
    with tabs[4]:
        for line in _lessons(ctx):
            st.markdown(f"- {line}", unsafe_allow_html=True)
    with tabs[5]:
        st.download_button(T("Descarregar a simulação completa (Excel)", "Download the full simulation (Excel)"),
                           _excel(ctx), f"resilia72h_{ctx.site_key}_{ctx.ev_key}.xlsx", type="primary",
                           icon=":material/download:",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.caption(T("Inclui os indicadores, os resultados hora a hora das duas gestões e o clima real usado.",
                     "Includes the indicators, hourly results for both strategies and the real weather used."))


def _day_stats(o):
    demand = o["dC"] + o["dE"] + o["dP"] + o["pump"]
    served = o["sC"] + o["sE"] + o["sP"] + o["pump"]
    unmet = (demand - served).clip(lower=0)
    # risco de interrupção = energia que faltou aos serviços essenciais (clínica, rádio, abrigo + luz e telemóvel das casas)
    ess_need = o["dC"] + o["dEmin"]
    ess_unmet = (o["dC"] - o["sC"]).clip(lower=0) + (o["dEmin"] - o["sE"]).clip(lower=0)
    return dict(
        demand=float(demand.sum()), served=float(served.sum()), unmet=float(unmet.sum()),
        ess_unmet=float(ess_unmet.sum()), other_unmet=float(unmet.sum() - ess_unmet.sum()),
        risk=100 * float(ess_unmet.sum()) / max(float(ess_need.sum()), 1e-9),
        # interrupção real: clínica sem energia ou casas às escuras (abaixo de luz + telemóvel);
        # o «modo essencial» é racionamento planeado, não conta como corte
        hours=int(((o["sC"] < 0.98 * o["dC"]) | (o["sE"] < 0.95 * o["dEmin"])).sum()),
        clinic=int((o["sC"] < 0.98 * o["dC"]).sum()),
        soc_end=100 * float(o["soc"].iloc[-1]), soc_min=100 * float(o["soc"].min()),
        pv=float(o["pv_av"].sum()), wind=float(o["wind"].sum()), diesel=float(o["diesel"].sum()),
        bat_out=float(o["bat_dis"].sum()), bat_in=float(o["bat_ch"].sum()), curt=float(o["curt"].sum()),
    )


def _balance24(ctx):
    """Resposta directa ao enunciado: equilíbrio oferta × procura ao longo de 24 horas."""
    oc, orr = ctx.oc, ctx.orr
    norm = orr.index.normalize()
    days = [d for d in sorted(set(norm)) if (norm == d).sum() == 24]
    if not days:
        return

    def main_phase(d):
        return orr.loc[norm == d, "fase"].value_counts().idxmax()

    st.markdown(f"### {T('Balanço de 24 horas', '24-hour energy balance')}")
    st.caption(T("Como a mini-rede equilibra a oferta (sol, vento, bateria, gerador) e a procura da aldeia, hora a hora, "
                 "durante um dia completo. Escolha o dia.",
                 "How the mini-grid balances supply (solar, wind, battery, generator) and village demand, hour by hour, "
                 "over one full day. Choose the day."))
    default = next((i for i, d in enumerate(days) if main_phase(d) == "evento"), 0)
    key = f"day24_{ctx.site_key}_{ctx.ev_key}"
    st.session_state.setdefault(key, default)
    sel = st.segmented_control(T("Dia", "Day"), list(range(len(days))), key=key, label_visibility="collapsed",
                               format_func=lambda i: f"{days[i].day} {month_short(days[i].month)} · {phase(main_phase(days[i]))}")
    sel = default if sel is None else sel
    day = days[sel]
    m = (norm == day)
    a, b = oc[m], orr[m]
    sa, sb = _day_stats(a), _day_stats(b)

    c = st.columns(4)
    with c[0]:
        versus(T("Risco de interrupção dos serviços essenciais", "Interruption risk for essential services"),
               f"{num(sa['risk'])}%", f"{num(sb['risk'])}%",
               T(f"energia essencial em falta: {num(sa['ess_unmet'])} → {num(sb['ess_unmet'])} kWh",
                 f"essential energy short: {num(sa['ess_unmet'])} → {num(sb['ess_unmet'])} kWh"))
    with c[1]:
        versus(T("Horas com interrupção", "Hours with interruption"), f"{sa['hours']} h", f"{sb['hours']} h",
               T("horas com a clínica sem energia ou as casas às escuras",
                 "hours with the clinic unpowered or homes in the dark"))
    with c[2]:
        versus(T("Clínica sem energia neste dia", "Clinic without power this day"), f"{sa['clinic']} h", f"{sb['clinic']} h")
    with c[3]:
        versus(T("Bateria no fim do dia", "Battery at end of day"), f"{num(sa['soc_end'])}%", f"{num(sb['soc_end'])}%",
               T(f"mínimo do dia: {num(sa['soc_min'])}% → {num(sb['soc_min'])}%",
                 f"day minimum: {num(sa['soc_min'])}% → {num(sb['soc_min'])}%"))

    peak = float(max((a["dC"] + a["dE"] + a["dP"] + a["pump"]).max(), (b["dC"] + b["dE"] + b["dP"] + b["pump"]).max(),
                     b["bat_ch"].max() / 0.6, a["bat_ch"].max() / 0.6, 1))
    l, r = st.columns(2)
    with l:
        st.plotly_chart(charts.balance24(a, T("Sistema de hoje", "Today's system"), ymax=peak), width="stretch")
    with r:
        st.plotly_chart(charts.balance24(b, T("Com RESILIA", "With RESILIA"), ymax=peak), width="stretch")

    with st.expander(T("Tabela do balanço energético do dia (kWh)", "Daily energy balance table (kWh)"),
                     icon=":material/table_chart:", expanded=False):
        rows = [
            (T("Energia produzida pelo sol", "Energy produced by the sun"), "pv"),
            (T("Energia produzida pelo vento", "Energy produced by the wind"), "wind"),
            (T("Energia do gerador", "Energy from the generator"), "diesel"),
            (T("Bateria entregou", "Battery delivered"), "bat_out"),
            (T("Bateria guardou", "Battery stored"), "bat_in"),
            (T("Sol desperdiçado (bateria cheia)", "Solar curtailed (battery full)"), "curt"),
            (T("Procura da aldeia", "Village demand"), "demand"),
            (T("Energia servida", "Energy served"), "served"),
            (T("Energia não servida (total)", "Energy not served (total)"), "unmet"),
            (T("… a serviços essenciais (interrupção)", "… to essential services (interruption)"), "ess_unmet"),
            (T("… conforto e moagem (hoje: apagão; RESILIA: racionamento planeado)",
               "… comfort and mill (today: blackout; RESILIA: planned rationing)"), "other_unmet"),
        ]
        st.table(pd.DataFrame({T("Sistema de hoje", "Today's system"): [num(sa[k], 1) for _, k in rows],
                               T("Com RESILIA", "With RESILIA"): [num(sb[k], 1) for _, k in rows]},
                              index=[n for n, _ in rows]))
    explain(T("Como ler:", "How to read:"),
            T("as barras acima de zero mostram de onde vem a energia entregue em cada hora (amarelo = sol, azul = bateria, "
              "castanho = gerador); a parte preta é energia que faltou. No sistema de hoje é um apagão; no RESILIA é sobretudo "
              "conforto e moagem adiados de propósito para proteger a clínica. As barras abaixo de zero são sol guardado na "
              "bateria. A linha escura é a procura da aldeia e a linha vermelha pontilhada é a carga da bateria.",
              "bars above zero show where each hour's delivered energy comes from (yellow = solar, blue = battery, brown = "
              "generator); the black part is energy that was missing. In today's system it is a blackout; with RESILIA it is "
              "mostly comfort and milling deliberately postponed to protect the clinic. Bars below zero are solar stored in the "
              "battery. The dark line is village demand and the dotted red line is the battery charge."))


def _physics_notes(orr, oc, t):
    r, q = orr.iloc[t], oc.iloc[t]
    notes = []
    if q["snow"] > 0.3:
        notes.append(T(f"neve cobre {100 * q['snow']:.0f} % dos painéis sem limpeza ({100 * r['snow']:.0f} % com limpeza)",
                       f"snow covers {100 * q['snow']:.0f} % of the panels without cleaning ({100 * r['snow']:.0f} % with cleaning)"))
    if q["soil"] > 0.06:
        notes.append(T(f"poeira tira {100 * q['soil']:.0f} % à produção", f"dust removes {100 * q['soil']:.0f} % of output"))
    if q["t_bat"] < 0:
        notes.append(T(f"bateria comum a {q['t_bat']:.0f} °C: <b>carga proibida</b> abaixo de 0 °C (contentor protegido: {r['t_bat']:.0f} °C)",
                       f"standard battery at {q['t_bat']:.0f} °C: <b>charging blocked</b> below 0 °C (protected enclosure: {r['t_bat']:.0f} °C)"))
    if q["inv_f"] < 0.98:
        notes.append(T(f"inversor comum sobreaquecido: só {100 * q['inv_f']:.0f} % da potência",
                       f"standard inverter overheating: only {100 * q['inv_f']:.0f} % of power"))
    if r["turb_stop"]:
        notes.append(T("aerogerador parado por segurança", "wind turbine stopped for safety"))
    if q["damage"] > 0.01:
        notes.append(T(f"{100 * q['damage']:.0f} % dos painéis danificados (estrutura comum)",
                       f"{100 * q['damage']:.0f} % of panels damaged (standard structure)"))
    return notes


def _lessons(ctx):
    oc, orr, mc = ctx.oc, ctx.orr, ctx.mc
    lines = []
    if (oc["t_bat"] < 0).any():
        h = int((oc["t_bat"] < 0).sum())
        lines.append(T(f"A bateria comum esteve <b>{h} h abaixo de 0 °C</b>: nessas horas não aceita carga.",
                       f"The standard battery spent <b>{h} h below 0 °C</b>: during those hours it cannot charge."))
    if oc["inv_f"].min() < 0.95:
        p = 100 * (1 - oc["inv_f"].min())
        lines.append(T(f"O calor tirou até <b>{p:.0f} %</b> da potência ao inversor comum.",
                       f"Heat took up to <b>{p:.0f} %</b> of the standard inverter's power."))
    if oc["snow"].max() > 0.5:
        a, b = int((oc["snow"] > 0.5).sum()), int((orr["snow"] > 0.5).sum())
        lines.append(T(f"Neve sobre os painéis: <b>{a} h</b> sem limpeza, <b>{b} h</b> com limpeza.",
                       f"Snow on the panels: <b>{a} h</b> without cleaning, <b>{b} h</b> with cleaning."))
    if oc["soil"].max() > 0.06:
        a, b = 100 * oc["soil"].max(), 100 * orr["soil"].max()
        lines.append(T(f"Poeira: até <b>{a:.0f} %</b> de perda; com lavagem, {b:.0f} %.",
                       f"Dust: up to <b>{a:.0f} %</b> loss; with washing, {b:.0f} %."))
    al = int((orr["mode"] == "alerta").sum())
    if al:
        e0 = orr["fase"] == "evento"
        a, b = 100 * orr["soc"][e0].iloc[0], 100 * oc["soc"][e0].iloc[0]
        lines.append(T(f"O alerta chegou <b>{al} h</b> antes: a bateria entrou no evento a <b>{a:.0f} %</b> (hoje: {b:.0f} %).",
                       f"The warning arrived <b>{al} h</b> ahead: the battery entered the event at <b>{a:.0f} %</b> (today: {b:.0f} %)."))
    if mc["crit_out_h"]:
        lines.append(T(f"Sem RESILIA, o maior corte seguido da clínica seria de <b>{mc['crit_longest_h']} h</b>.",
                       f"Without RESILIA, the clinic's longest continuous outage would be <b>{mc['crit_longest_h']} h</b>."))
    return lines or [T("Evento sem impactos físicos relevantes para este equipamento.",
                       "No significant physical impacts for this equipment in this event.")]


def _excel(ctx):
    buf = io.BytesIO()
    cols = ["fase", "mode", "pv_av", "pv", "wind", "bat_dis", "bat_ch", "diesel", "fuel", "soc", "reserve", "dC",
            "dE", "dEmin", "dP", "sC", "sE", "sP", "pump", "tank", "w_need", "w_srv", "blackout", "snow", "soil",
            "t_bat", "inv_f"]
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        pd.DataFrame({T("Indicador", "Indicator"): list(ctx.mc), T("Sistema de hoje", "Today's system"): list(ctx.mc.values()),
                      "RESILIA": list(ctx.mr.values())}).to_excel(xw, sheet_name=T("Indicadores", "Indicators"), index=False)
        ctx.orr[cols].to_excel(xw, sheet_name=T("RESILIA_horario", "RESILIA_hourly"))
        ctx.oc[cols].to_excel(xw, sheet_name=T("Hoje_horario", "Today_hourly"))
        ctx.w.drop(columns=["fase"]).to_excel(xw, sheet_name=T("Clima_real_ERA5", "Real_weather_ERA5"))
    return buf.getvalue()
