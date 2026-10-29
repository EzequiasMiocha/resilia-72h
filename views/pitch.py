"""Apresentação ao júri: directa, 6 diapositivos (contexto, desafio e objectivo, como respondemos, 24 h,
resiliente e eficiente, conclusão)."""
from __future__ import annotations

import time

import numpy as np
import streamlit as st
import streamlit.components.v1 as components

from resilia import model as M
from ui import charts
from ui.i18n import T, day_label, num, verdict_txt
from ui.icons import icon
from ui.style import C

from .panel import get_demand, get_resource, presets

VILLAGE = (200, True, True, True, True, 0.0)       # aldeia de referência da apresentação
VCOL = {"ok": "#16A34A", "partial": "#B45309", "fragile": C["red"]}

SLIDES = [
    ("contexto", "Contexto", "Context", 45,
     "Onde estamos (Mabote, sem rede), qual é o problema (o sol muda todos os dias) e o que acontece se o sistema for "
     "pensado só para o dia médio (a aldeia fica às escuras). Mostrem os números.",
     "Where we are (Mabote, no grid), the problem (the sun changes every day) and what happens if the system is designed "
     "only for the average day (the village goes dark). Show the numbers."),
    ("objectivo", "Desafio e objectivo", "Challenge and objective", 60,
     "À esquerda, o desafio do EMERGE em três linhas. À direita, o nosso objectivo numa frase. Expliquem porque o "
     "sistema é só solar: o vento de Mabote é fraco para gerar energia.",
     "Left: the EMERGE challenge in three lines. Right: our objective in one sentence. Explain why the system is solar "
     "only: Mabote's wind is too weak to generate power."),
    ("como", "Como respondemos", "How we answer", 45,
     "Cada exigência do desafio e onde está na plataforma. Terminem com a regra do balanço de cada hora.",
     "Each requirement of the challenge and where it is in the platform. End with the hourly balance rule."),
    ("balanco", "Balanço 24 h", "24-h balance", 90,
     "Mudem o tipo de dia. À esquerda o sistema só eficiente, à direita o resiliente. Mostrem a parte preta (energia em falta).",
     "Change the type of day. Left: efficiency-only system; right: resilient. Point to the black part (energy missing)."),
    ("resiliente", "Resiliente e eficiente", "Resilient and efficient", 80,
     "Os números de 11 anos: dias maus por ano e horas sem energia. Depois o teste nos 5 tipos de dia.",
     "The 11-year numbers: bad days per year and hours without power. Then the test on the 5 day types."),
    ("conclusao", "Conclusão", "Conclusion", 40,
     "O que entregamos, o resultado, como se mantém e se replica, e o próximo passo. Frase final.",
     "What we deliver, the result, how it is sustained and replicated, and the next step. Closing line."),
]
ENDS = list(np.cumsum([s[3] for s in SLIDES]))


def _title(k):
    return T(SLIDES[k][1], SLIDES[k][2])


@st.cache_data(show_spinner=False)
def pitch_data(version=2):
    res, days = get_resource()
    D = get_demand(VILLAGE)["total"].values
    ch = presets(VILLAGE)
    e, r = ch["efficient"], ch["resilient"]
    daily = res["ghi"].resample("D").sum()
    daily = daily[daily.index.year >= 2015]
    weak = daily < 0.5 * daily.mean()
    run = best = 0
    for x in weak.values:
        run = run + 1 if x else 0
        best = max(best, run)
    dd = get_demand(VILLAGE)["total"].resample("D").sum()
    test = {}
    for name, row in (("e", e), ("r", r)):
        s = M.System(pv=row["pv"], bat=row["bat"])
        test[name] = {k: M.day_metrics(M.simulate_day(res, D, s, days[k]), s) for k in M.DAY_TYPES}
    return dict(e=e, r=r, weak_per_year=weak.sum() / (len(daily) / 365.25), weak_run=best,
                dem_mean=dd.mean(), dem_min=dd.quantile(0.02), dem_max=dd.quantile(0.98), test=test,
                sun_min=daily.quantile(0.02) / 1000, sun_max=daily.quantile(0.98) / 1000, wind_mean=res["v"].mean())


def _go(i):
    st.session_state["slide_nav"] = max(0, min(len(SLIDES) - 1, i))


def _timer(end_s, total=sum(s[3] for s in SLIDES)):
    t0 = st.session_state.get("pitch_t0") or 0
    stopped, late = T("cronómetro parado", "timer stopped"), T("acelerar", "speed up")
    until = T("acabar até ", "finish by ")
    tot = f"{total // 60}:{total % 60:02d}"
    html = f"""
<div style="font-family:Inter,system-ui,sans-serif;display:flex;gap:10px;align-items:center;justify-content:flex-end;height:44px">
  <div id="t" style="font-size:28px;font-weight:800;color:#1F2933">0:00</div>
  <div style="font-size:14px;color:#6B7280">/ {tot}</div>
  <div id="h" style="font-size:12px;padding:5px 10px;border-radius:999px;background:#ECEEF2;color:#374151;font-weight:600"></div>
</div>
<script>
const t0={int(t0)}, end={int(end_s)}, tot={total};
function fmt(s){{s=Math.max(0,Math.floor(s));return Math.floor(s/60)+':'+String(s%60).padStart(2,'0');}}
function tick(){{
  const T=document.getElementById('t'), H=document.getElementById('h');
  if(!t0){{T.textContent='0:00'; H.textContent='{stopped}'; return;}}
  const s=(Date.now()-t0)/1000; T.textContent=fmt(s);
  T.style.color = s>tot ? '#C8102E' : (s>end ? '#B45309' : '#1F2933');
  H.textContent = s>end ? '{late}' : '{until}' + fmt(end);
  H.style.background = s>end ? '#FDECEF' : '#ECEEF2';
}}
tick(); setInterval(tick, 500);
</script>"""
    if hasattr(st, "iframe"):
        st.iframe(html, height=50)
    else:
        components.html(html, height=50)


def _slide(n, inner, cls="slide"):
    st.markdown(f'<div class="{cls}"><div class="num">{n}</div>{inner}</div>', unsafe_allow_html=True)


def _idea(ic, h, x):
    return f'<div class="idea"><div class="ic">{icon(ic, 30)}</div><div class="h">{h}</div><div class="x">{x}</div></div>'


def _sys(row):
    return f"{num(row['pv'])} kWp · {num(row['bat'])} kWh"


# ───────────────────────────── diapositivos ─────────────────────────────
def s_contexto(d):
    _slide(f"1 · {_title(0)}", f"""
<h1>{T("Energia solar numa aldeia sem rede:", "Solar power in a village without the grid:")}<br>
<span class="red">{T("o sol não é igual todos os dias.", "the sun is not the same every day.")}</span></h1>
<div class="ideas" style="margin-top:8px">
 {_idea("globe", T("Onde", "Where"), T(
   "<b>Mabote, Inhambane.</b> A rede eléctrica nacional não chega à maioria das aldeias. A solução é uma <b>mini-rede solar com baterias</b>.",
   "<b>Mabote, Inhambane.</b> The national grid does not reach most villages. The answer is a <b>solar mini-grid with batteries</b>."))}
 {_idea("cloud", T("O problema", "The problem"), T(
   "Dias nublados, de chuva ou de calor reduzem a energia do sol. E a procura da aldeia também muda de hora para hora e de dia para dia.",
   "Cloudy, rainy or hot days cut solar energy. And village demand also changes hour by hour and day by day."))}
 {_idea("alert", T("A consequência", "The consequence"), T(
   "Um sistema pensado só para o <b>dia médio</b> é barato, mas nos <b>dias maus</b> a aldeia, o centro de saúde e a bomba de água ficam sem energia.",
   "A system designed only for the <b>average day</b> is cheap, but on <b>bad days</b> the village, the health centre and the water pump lose power."))}
</div>
<div class="big">
  <div class="k"><div class="n red">{num(d['weak_per_year'])}</div><div class="u">{T("dias por ano com menos de metade do sol normal",
   "days per year with less than half the normal sunshine")}</div></div>
  <div class="k"><div class="n">{num(d['weak_run'])} {T("dias", "days")}</div><div class="u">{T("a maior sequência de dias fracos seguidos (11 anos)",
   "longest run of weak days in a row (11 years)")}</div></div>
  <div class="k"><div class="n">{num(d['sun_min'], 1)}–{num(d['sun_max'], 1)}</div><div class="u">{T("kWh/m² de sol por dia: do dia mais fraco ao mais forte",
   "kWh/m² of sun per day: from weakest to strongest day")}</div></div>
  <div class="k"><div class="n">{num(d['dem_min'])}–{num(d['dem_max'])}</div><div class="u">{T("kWh/dia: a procura de 200 famílias também varia",
   "kWh/day: demand from 200 households varies too")}</div></div>
</div>
<div class="lead" style="font-size:15px;margin-top:6px">{T("Fonte: dados horários reais de Mabote, 2015–2025 (ERA5, Copernicus).",
 "Source: real hourly Mabote data, 2015–2025 (ERA5, Copernicus).")}</div>""")


def s_objectivo(d):
    rows = [
        (T("Tarefa", "Task"), T("Simular como um sistema off-grid equilibra a oferta e a procura ao longo de <b>24 horas</b>.",
                                "Simulate how an off-grid system balances supply and demand over <b>24 hours</b>.")),
        (T("Entregável", "Deliverable"), T("Ferramenta simples. <b>Entradas:</b> sol, vento, bateria e perfil de procura. "
                                           "<b>Saídas:</b> balanço energético e risco de interrupção.",
                                           "A simple tool. <b>Inputs:</b> solar, wind, battery and demand profile. "
                                           "<b>Outputs:</b> energy balance and interruption risk.")),
        (T("Diferencial", "Twist"), T("Optimizar para a <b>resiliência</b>, não apenas para a eficiência.",
                                      "Optimise for <b>resilience</b>, not just efficiency.")),
    ]
    left = "".join(f'<div class="row"><div class="l">{a}</div><div>{b}</div></div>' for a, b in rows)
    _slide(f"2 · {_title(1)}", f"""
<h2>{T("O que nos pediram e o que fazemos.", "What we were asked and what we do.")}</h2>
<div class="two">
 <div class="box"><div class="tt">{T("O desafio · EMERGE", "The challenge · EMERGE")}</div>{left}</div>
 <div class="box goal"><div class="tt">{T("O nosso objectivo", "Our objective")}</div>
  <div class="say">{T(
   "Dimensionar a mini-rede <b>solar + bateria</b> de uma aldeia de Mabote para que <b>não fique às escuras nos dias maus</b>, "
   "gastando apenas o necessário.",
   "Size the <b>solar + battery</b> mini-grid of a Mabote village so that it <b>does not go dark on bad days</b>, "
   "spending only what is needed.")}</div>
  <ul>
   <li>{T("Dados reais de Mabote, hora a hora, durante 11 anos (2015–2025).",
          "Real Mabote data, hour by hour, over 11 years (2015–2025).")}</li>
   <li>{T("Procura calculada a partir do <b>número de famílias</b> e dos serviços.",
          "Demand calculated from the <b>number of households</b> and services.")}</li>
   <li>{T("<b>Resiliência obrigatória</b>; entre os sistemas resilientes, escolhe-se o mais barato (eficiência).",
          "<b>Resilience is required</b>; among resilient systems, the cheapest is chosen (efficiency).")}</li>
   <li>{T(f"Só solar: o vento médio em Mabote é de {num(d['wind_mean'], 1)} m/s, fraco para gerar energia. Entra apenas porque arrefece os painéis.",
          f"Solar only: mean wind in Mabote is {num(d['wind_mean'], 1)} m/s, too weak to generate power. It only counts because it cools the panels.")}</li>
  </ul>
 </div>
</div>""")


def s_como(d):
    rows = [
        (T("Entradas", "Inputs"), T("sol, vento, bateria, procura", "solar, wind, battery, demand"),
         T("Painel lateral: painéis solares (kWp), baterias (kWh), número de famílias e serviços. O sol e o vento reais variam hora a hora.",
           "Side panel: solar panels (kWp), batteries (kWh), number of households and services. Real sun and wind vary hour by hour.")),
        (T("Balanço em 24 horas", "24-hour balance"), T("oferta × procura", "supply × demand"),
         T("<b>Simulador 24 h:</b> hora a hora (00–23 h), em dias reais de sol, nuvens, chuva e calor.",
           "<b>24-hour simulator:</b> hour by hour (00–23 h), on real sunny, cloudy, rainy and hot days.")),
        (T("Risco de interrupção", "Interruption risk"), T("saída", "output"),
         T("Energia em falta (%), horas sem energia e carga da bateria ao longo do dia.",
           "Energy missing (%), hours without power and battery charge through the day.")),
        (T("Resiliência, não só eficiência", "Resilience, not just efficiency"), T("diferencial", "twist"),
         T(f"<b>Dimensionamento:</b> {M.N_SYSTEMS} sistemas testados em 11 anos; o mais barato que aguenta os dias maus.",
           f"<b>Sizing:</b> {M.N_SYSTEMS} systems tested over 11 years; the cheapest that withstands bad days.")),
        (T("Modelo em folha de cálculo", "Spreadsheet model"), T("ferramenta simples", "simple tool"),
         T("A tabela hora a hora exporta para Excel.", "The hourly table exports to Excel.")),
    ]
    body = "".join(f"<tr><td>{a}<span class='w'>{w}</span></td><td>{b}</td></tr>" for a, w, b in rows)
    _slide(f"3 · {_title(2)}", f"""
<h2>{T("Como respondemos ao desafio", "How we answer the challenge")}</h2>
<table class="map"><tr><th>{T("O desafio pede", "The challenge asks for")}</th><th>{T("Na plataforma", "In the platform")}</th></tr>{body}</table>
<div class="lead" style="margin-top:16px;font-size:18px">{T(
 "<b>Em cada hora:</b> o sol serve a aldeia → o excedente carrega a bateria → o que falta sai da bateria → o resto é <b class='red'>energia em falta</b>.",
 "<b>Every hour:</b> the sun serves the village → surplus charges the battery → shortfalls come from the battery → the rest is <b class='red'>energy missing</b>.")}</div>""")


def s_balanco(d):
    res, days = get_resource()
    D = get_demand(VILLAGE)["total"].values
    _slide(f"4 · {_title(3)}", f'<h2>{T("O mesmo dia, dois sistemas: 24 horas de oferta e procura", "The same day, two systems: 24 hours of supply and demand")}</h2>',
           cls="slide compact")
    st.session_state.setdefault("p_day", "cloudy")
    k = st.segmented_control(T("Tipo de dia", "Type of day"), M.DAY_TYPES, key="p_day", format_func=day_label) or "cloudy"
    cols = st.columns(2)
    outs = []
    for (name, row), col in zip(((T("Só eficiência", "Efficiency only"), d["e"]), (T("Resiliente", "Resilient"), d["r"])), cols):
        s = M.System(pv=row["pv"], bat=row["bat"])
        o = M.simulate_day(res, D, s, days[k])
        outs.append((name, row, s, o, M.day_metrics(o, s)))
    peak = max(max(o["demand"].max(), o["bat_ch"].max() / 0.75) for _, _, _, o, _ in outs)
    for (name, row, s, o, m), col in zip(outs, cols):
        v = M.verdict(m["risk"])
        with col:
            st.markdown(f"<div style='font-size:15px;font-weight:800'>{name} · <span style='color:#6B7280;font-weight:600'>{_sys(row)}</span></div>"
                        f"<div style='font-size:22px;font-weight:800;color:{VCOL[v]}'>{num(m['risk'], 1)} % "
                        f"{T('em falta', 'missing')} · {m['hours']} h · {verdict_txt(v)}</div>", unsafe_allow_html=True)
            st.plotly_chart(charts.balance24(o, None, ymax=peak, height=340, legend=False), width="stretch")
    st.markdown(f'<div class="lead" style="font-size:15px">{T("Amarelo = sol · azul = bateria · <b>preto = energia em falta</b> · linha escura = procura · linha vermelha = bateria (%).", "Yellow = solar · blue = battery · <b>black = energy missing</b> · dark line = demand · red line = battery (%).")}</div>',
                unsafe_allow_html=True)


def s_resiliente(d):
    e, r = d["e"], d["r"]
    cells = ""
    for k in M.DAY_TYPES:
        a, b = d["test"]["e"][k], d["test"]["r"][k]
        va, vb = M.verdict(a["risk"]), M.verdict(b["risk"])
        cells += (f'<div class="k"><div class="u"><b>{day_label(k)}</b></div>'
                  f'<div class="u" style="color:{VCOL[va]};font-weight:700">{T("Só eficiência", "Efficiency")}: {num(a["risk"], 1)} %</div>'
                  f'<div class="u" style="color:{VCOL[vb]};font-weight:800">{T("Resiliente", "Resilient")}: {num(b["risk"], 1)} %</div></div>')
    _slide(f"5 · {_title(4)}", f"""
<h2>{T("Testado em 11 anos de dias reais: resiliente e eficiente.", "Tested on 11 years of real days: resilient and efficient.")}</h2>
<div class="big">
  <div class="k"><div class="n red">{num(e['bad_days'])} → {num(r['bad_days'], 1)}</div><div class="u">{T("dias maus por ano (mais de 10 % de energia em falta)",
   "bad days per year (more than 10 % energy missing)")}</div></div>
  <div class="k"><div class="n red">{num(e['hours'])} h → {num(r['hours'])} h</div><div class="u">{T("horas com interrupção por ano",
   "hours with interruption per year")}</div></div>
  <div class="k"><div class="n">{num(e['autonomy'])} h → {num(r['autonomy'])} h</div><div class="u">{T("autonomia da bateria sem sol",
   "battery autonomy without sun")}</div></div>
  <div class="k"><div class="n">+{num(100 * (r['cost'] / e['cost'] - 1))} %</div><div class="u">{T(
   f"de investimento ({num(e['cost'] / 1000)} → {num(r['cost'] / 1000)} mil USD): o mais barato que cumpre",
   f"investment ({num(e['cost'] / 1000)} → {num(r['cost'] / 1000)}k USD): the cheapest that meets the target")}</div></div>
</div>
<div class="lead" style="font-size:16px"><b>{T("Só eficiência", "Efficiency only")}:</b> {_sys(e)} &nbsp;·&nbsp;
<b class="red">{T("Resiliente", "Resilient")}:</b> {_sys(r)}</div>
<div style="font-size:18px;font-weight:800;margin:16px 0 4px 0">{T("Teste de 24 horas nos 5 tipos de dia (energia em falta)",
 "24-hour test on the 5 day types (energy missing)")}</div>
<div class="big" style="grid-template-columns:repeat(5,1fr);margin-top:6px">{cells}</div>""")


def s_conclusao(d):
    _slide(f"6 · {_title(5)}", f"""
<h2>{T("Uma ferramenta simples que diz que sistema instalar para a aldeia não ficar às escuras.",
       "A simple tool that tells you which system to install so the village does not go dark.")}</h2>
<div class="ideas" style="grid-template-columns:repeat(auto-fit,minmax(215px,1fr))">
 {_idea("check", T("O que entregamos", "What we deliver"), T(
   "Simulador de 24 h com dados reais, risco de interrupção, e dimensionamento testado em 11 anos.",
   "24-hour simulator with real data, interruption risk, and sizing tested over 11 years."))}
 {_idea("shield", T("Resultado", "Result"), T(
   f"Com +{num(100 * (d['r']['cost'] / d['e']['cost'] - 1))} % de investimento, os dias maus passam de {num(d['e']['bad_days'])} para {num(d['r']['bad_days'], 1)} por ano.",
   f"With +{num(100 * (d['r']['cost'] / d['e']['cost'] - 1))} % investment, bad days fall from {num(d['e']['bad_days'])} to {num(d['r']['bad_days'], 1)} a year."))}
 {_idea("users", T("Sustentabilidade e replicação", "Sustainability and replication"), T(
   "Gratuita e de código aberto, para comunidades, ONGs e o FUNAE. Para outra aldeia basta o sol e a temperatura hora a hora e o número de famílias.",
   "Free and open source, for communities, NGOs and FUNAE. For another village it only needs hourly sun and temperature and the number of households."))}
 {_idea("signal", T("Próximo passo", "Next step"), T(
   "Piloto numa aldeia de Mabote: medir a procura real e confirmar o dimensionamento no terreno.",
   "Pilot in a Mabote village: measure real demand and confirm the sizing in the field."))}
</div>
<div style="font-size:30px;font-weight:800;margin-top:22px;color:#1F2933">{T(
 'Energia solar que <span class="red">não falha nos dias maus.</span>', 'Solar power that <span class="red">does not fail on bad days.</span>')}</div>
<div class="lead" style="font-size:15px;margin-top:8px">{T("Grupo 36", "Team 36")} · Ezequias Miocha · Laura Hele · Suely Muando · Universidade Eduardo Mondlane</div>""")


RENDER = dict(contexto=s_contexto, objectivo=s_objectivo, como=s_como, balanco=s_balanco, resiliente=s_resiliente,
              conclusao=s_conclusao)


def render():
    d = pitch_data()
    st.session_state.setdefault("slide_nav", 0)
    i = min(int(st.session_state["slide_nav"]), len(SLIDES) - 1)
    st.markdown('<div id="top"></div>', unsafe_allow_html=True)
    with st.container(key="pitchbar"):
        head = st.columns([7, 3], vertical_alignment="center")
        with head[0]:
            st.markdown(f"<div style='font-size:15px;color:#6B7280;font-weight:600'><b style='color:#1F2933'>RESILIA · "
                        f"{T('apresentação', 'pitch')}</b> · {T('diapositivo', 'slide')} {i + 1} {T('de', 'of')} {len(SLIDES)}</div>",
                        unsafe_allow_html=True)
        with head[1]:
            _timer(ENDS[i])
        nav = st.columns(len(SLIDES), gap="small")
        for k in range(len(SLIDES)):
            with nav[k]:
                st.button(f"{k + 1} · {_title(k)}", key=f"nav_{k}", on_click=_go, args=(k,), width="stretch",
                          type="primary" if k == i else "secondary", help=f"{SLIDES[k][3]} s")

    RENDER[SLIDES[i][0]](d)

    bot = st.columns([1.2, 1.5, 1.5, 3.8, 1.2], vertical_alignment="center")
    with bot[0]:
        st.button(T("Anterior", "Previous"), icon=":material/arrow_back:", on_click=_go, args=(i - 1,),
                  disabled=i == 0, width="stretch", key="prev_bot")
    with bot[1]:
        running = bool(st.session_state.get("pitch_t0"))
        if st.button(T("Reiniciar cronómetro", "Restart timer") if running else T("Iniciar cronómetro", "Start timer"),
                     icon=":material/timer:", width="stretch"):
            st.session_state["pitch_t0"] = time.time() * 1000
            st.rerun()
    with bot[2]:
        notes_on = st.toggle(T("Notas do orador", "Speaker notes"), value=False, key="notes")
    with bot[4]:
        st.button(T("Seguinte", "Next"), icon=":material/arrow_forward:", icon_position="right", on_click=_go,
                  args=(i + 1,), disabled=i == len(SLIDES) - 1, width="stretch", type="primary", key="next_bot")
    if notes_on:
        _, tp, te, secs, np_, ne = SLIDES[i]
        st.markdown(f'<div class="speaker"><b>{T(tp, te)} ({secs} s):</b> {T(np_, ne)}</div>', unsafe_allow_html=True)
    st.markdown(f'<a class="totop" href="#top" title="{T("Voltar ao topo", "Back to top")}">{icon("up", 20, stroke=2.4)}</a>',
                unsafe_allow_html=True)
