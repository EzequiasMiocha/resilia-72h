"""Apresentação de 7 minutos ao júri — Moçambique (Mabote, ciclone Freddy). Bilingue PT/EN.

Diapositivos simples, um de cada vez, com cronómetro e notas do orador.
A simulação mostrada é a do motor RESILIA com dados meteorológicos reais.
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from resilia import __version__
from resilia.data import event_window, load_site, sim_slice, typical_window
from resilia.economics import capex, crf
from resilia.engine import CONVENTIONAL, RESILIA, metrics, simulate
from resilia.sites import COSTS, SITES
from ui import charts
from ui.i18n import T, date_long, event, month_short, num
from ui.icons import icon
from ui.style import C, legend

from .common import all_events_summary, community_for, default_systems

# (chave, título PT, título EN, segundos, notas PT, notas EN)
SLIDES = [
    ("abertura", "Abertura", "Opening", 40,
     "Comecem pela pergunta: «O que acontece a uma clínica rural quando chega um ciclone?» Digam o número grande "
     "(horas às escuras → zero) e que é com dados reais do Freddy em Mabote.",
     "Open with the question: “What happens to a rural clinic when a cyclone hits?” State the headline number "
     "(hours in the dark → zero) and that it uses real data from Cyclone Freddy in Mabote."),
    ("problema", "O problema", "The problem", 50,
     "Mostrem o gráfico: os dias normais têm sol que chega; nos dias do ciclone o sol cai a quase nada. Expliquem as 3 "
     "razões pelas quais as mini-redes de hoje apagam tudo, incluindo a clínica.",
     "Show the chart: normal days have enough sun; during the cyclone it drops to almost nothing. Explain the 3 reasons "
     "why today's mini-grids shut everything down, including the clinic."),
    ("solucao", "A solução", "The solution", 50,
     "Três ideias simples: saber antes, guardar para o que salva vidas, desligar por ordem. Sublinhem que o equipamento "
     "é o MESMO; o que muda é a inteligência e um reforço físico barato.",
     "Three simple ideas: know in advance, save energy for what saves lives, switch off in order. Stress that the "
     "equipment is the SAME; what changes is the intelligence plus low-cost physical hardening."),
    ("como", "Como simulamos", "How we simulate", 30,
     "Em 30 segundos: clima real hora a hora → energia dos painéis → consumo da aldeia → a bateria decide. Duas formas "
     "de gerir o mesmo equipamento, lado a lado.",
     "In 30 seconds: real hourly weather → panel output → village demand → the battery decides. Two ways of operating "
     "the same equipment, side by side."),
    ("simulacao", "A simulação", "The simulation", 100,
     "Cliquem nos momentos, da esquerda para a direita. Em cada um, leiam só a frase de baixo de cada lado. No fim, "
     "mostrem o mapa de luzes: preto = apagão. A linha do centro de saúde do RESILIA fica amarela do princípio ao fim.",
     "Click through the moments from left to right. For each one, read only the bottom sentence on each side. Finish "
     "with the lights map: black = blackout. RESILIA's health-centre row stays yellow from start to finish."),
    ("resultados", "Resultados", "Results", 50,
     "Leiam os 4 números. Depois: «não foi sorte»: os 3 ciclones reais de Inhambane dão o mesmo resultado. Com gerador, "
     "o sistema de hoje gasta mais gasóleo e ainda apaga; o RESILIA gasta menos e não apaga.",
     "Read the 4 numbers. Then: “it wasn't luck”: the 3 real Inhambane cyclones give the same result. With a generator, "
     "today's system burns more diesel and still goes dark; RESILIA burns less and never does."),
    ("viabilidade", "Viabilidade", "Feasibility", 40,
     "Custo por família, quem paga e com quem trabalhamos. A tecnologia já existe; o que é novo é a inteligência que a junta.",
     "Cost per household, who pays and who we work with. The technology already exists; what's new is the intelligence "
     "that brings it together."),
    ("futuro", "Escala e pedido", "Scale and ask", 40,
     "O mesmo motor funciona em Marrocos (neve) e no Mali (calor). Terminem com o pedido concreto: piloto em Mabote em "
     "2027. Última frase: «Energia que não apaga quando o clima aperta.»",
     "The same engine works in Morocco (snow) and Mali (heat). Close with the concrete ask: a pilot in Mabote in 2027. "
     "Last line: “Power that stays on when the weather turns.”"),
]
ENDS = list(np.cumsum([s[3] for s in SLIDES]))
ROWS = ["health", "water", "homes", "mill"]


def _title(k):
    return T(SLIDES[k][1], SLIDES[k][2])


# ───────────────────────────── dados ─────────────────────────────
@st.cache_data(show_spinner="A preparar a apresentação… / Preparing the pitch…")
def pitch_data(version):
    key = "MZ"
    s = SITES[key]
    df = load_site(key)
    comm = community_for(key)
    sc, sr = default_systems(key)
    start = event_window(df, "freddy")
    w = sim_slice(df, start)
    oc = simulate(w, s, sc, comm, CONVENTIONAL)
    orr = simulate(w, s, sr, comm, RESILIA)
    storm = (w["fase"] != "preparação").values          # 72 h de ciclone + 24 h de chuva que se seguiram
    evm = (w["fase"] == "evento").values
    mc, mr = metrics(oc, storm), metrics(orr, storm)

    g = dict(diesel_kw=15, fuel_l=200)
    mcg = metrics(simulate(w, s, sc.copy(**g), comm, CONVENTIONAL), storm)
    mrg = metrics(simulate(w, s, sr.copy(**g), comm, RESILIA), storm)

    ev = w[evm]
    nw = sim_slice(df, typical_window(df, start))
    nsol = nw[nw["fase"] == "evento"]["shortwave_radiation"].sum()
    stats = dict(sol_pct=100 * ev["shortwave_radiation"].sum() / max(nsol, 1),
                 gust_kmh=3.6 * ev["wind_gusts_10m"].max(), rain=w[storm]["precipitation"].sum(),
                 pmin=ev["pressure_msl"].min())

    blocks = []
    for i in range(len(orr) // 24):
        part = orr.iloc[24 * i: 24 * i + 24]
        d0 = part.index[0]
        blocks.append(dict(day=d0.day, month=d0.month, fase=part["fase"].value_counts().idxmax(),
                           sol=float(part["pv_av"].sum()), pede=float((part["dC"] + part["dE"] + part["dP"]).sum())))

    cyc = []
    for ek in ("freddy", "dineo", "filipo"):
        ww = sim_slice(df, event_window(df, ek))
        m = (ww["fase"] != "preparação").values
        a = metrics(simulate(ww, s, sc, comm, CONVENTIONAL), m)
        b = metrics(simulate(ww, s, sr, comm, RESILIA), m)
        cyc.append(dict(ev=ek, hoje=a["crit_out_h"], res=b["crit_out_h"]))

    items_r = capex(sr, comm.households, True)
    items_c = capex(sc, comm.households, False)
    extra = sum(items_r.values()) - sum(items_c.values())
    ann = extra * crf(COSTS["discount"], COSTS["project_life_y"])
    first_bo = int(np.flatnonzero(oc["blackout"].values)[0]) if oc["blackout"].any() else None
    return dict(w=w, oc=oc, orr=orr, mc=mc, mr=mr, mcg=mcg, mrg=mrg, stats=stats, blocks=blocks, cyc=cyc,
                extra=extra, per_fam=extra / comm.households, month=ann / comm.households / 12,
                base_capex=sum(items_c.values()), households=comm.households, people=comm.people,
                pv=sc.pv_kwp, bat=sc.bat_kwh, start=start, first_bo=first_bo,
                ev0=int(np.flatnonzero(evm)[0]), ev1=int(np.flatnonzero(evm)[-1]))


# ───────────────────────────── utilitários ─────────────────────────────
def _go(i):
    st.session_state["slide_nav"] = max(0, min(len(SLIDES) - 1, i))


def _on_moment():
    k = st.session_state.get("moment")
    if k is None:                                    # clique no momento já seleccionado
        k = st.session_state.get("_moment_last", 0)
        st.session_state["moment"] = k
    st.session_state["_moment_last"] = k
    st.session_state["hour"] = st.session_state["_mhours"][k]


def _timer(end_s):
    t0 = st.session_state.get("pitch_t0") or 0
    stopped, late = T("cronómetro parado", "timer stopped"), T("acelerar: tempo do diapositivo esgotado",
                                                                 "speed up: slide time is over")
    until = T("acabar este diapositivo até ", "finish this slide by ")
    html = f"""
<div style="font-family:Inter,system-ui,sans-serif;display:flex;gap:10px;align-items:center;justify-content:flex-end;height:44px">
  <div id="t" style="font-size:28px;font-weight:800;color:#1F2933">0:00</div>
  <div style="font-size:14px;color:#6B7280">/ 7:00</div>
  <div id="h" style="font-size:12px;padding:5px 10px;border-radius:999px;background:#ECEEF2;color:#374151;font-weight:600"></div>
</div>
<script>
const t0={int(t0)}, end={int(end_s)};
function fmt(s){{s=Math.max(0,Math.floor(s));return Math.floor(s/60)+':'+String(s%60).padStart(2,'0');}}
function tick(){{
  const T=document.getElementById('t'), H=document.getElementById('h');
  if(!t0){{T.textContent='0:00'; H.textContent='{stopped}'; return;}}
  const s=(Date.now()-t0)/1000; T.textContent=fmt(s);
  T.style.color = s>420 ? '#C8102E' : (s>end ? '#B45309' : '#1F2933');
  H.textContent = s>end ? '{late}' : '{until}' + fmt(end);
  H.style.background = s>end ? '#FDECEF' : '#ECEEF2'; H.style.color = s>end ? '#8E0B21' : '#374151';
}}
tick(); setInterval(tick, 500);
</script>"""
    if hasattr(st, "iframe"):
        st.iframe(html, height=50)
    else:
        components.html(html, height=50)


def _slide(num_, inner, cls="slide"):
    st.markdown(f'<div class="{cls}"><div class="num">{num_}</div>{inner}</div>', unsafe_allow_html=True)


def _dot(color):
    return f'<span class="dt" style="background:{color}"></span>'


def _weather_words(w, t):
    r = w.iloc[t]
    h = w.index[t].hour
    if 6 <= h <= 17:
        g = r["shortwave_radiation"]
        sky = (icon("sun", 18) + T("sol", "sunny")) if g > 450 else (
            (icon("cloud", 18) + T("muito nublado", "very cloudy")) if g > 150 else
            (icon("cloud", 18) + T("céu escuro, quase sem sol", "dark sky, almost no sun")))
    else:
        sky = icon("moon", 18) + T("noite", "night")
    parts = [f"<span>{sky}</span>"]
    rain = r["precipitation"]
    if rain >= 0.5:
        parts.append(f"<span>{icon('rain', 18)}{T('chuva forte', 'heavy rain') if rain >= 5 else T('chuva', 'rain')}</span>")
    parts.append(f"<span>{icon('wind', 18)}{T('rajadas de', 'gusts of')} {num(3.6 * r['wind_gusts_10m'])} km/h</span>")
    return '<div class="wx">' + "".join(parts) + "</div>"


def _board(o, t, smart, met="INAM"):
    r = o.iloc[t]
    eps = 1e-9
    fc = r["sC"] / (r["dC"] + eps)
    fe = r["sE"] / (r["dE"] + eps)
    fw = r["w_srv"] / (r["w_need"] + eps)

    def box(ic, name, state, cls):
        return (f'<div class="b {cls}"><div class="i">{icon(ic, 26)}</div>'
                f'<div><div class="n">{name}</div><div class="s">{state}</div></div></div>')

    clinic = box("clinic", T("Centro de saúde", "Health centre"),
                 T("LIGADO", "ON") if fc >= 0.98 else (T("PARCIAL", "PARTIAL") if fc >= 0.3 else T("APAGADO", "OFF")),
                 "on" if fc >= 0.98 else ("part" if fc >= 0.3 else "offb"))
    water = box("water", T("Água potável", "Drinking water"),
                T(f"a correr · depósito {100 * r['tank']:.0f} %", f"flowing · tank {100 * r['tank']:.0f} %")
                if fw >= 0.98 else T("SEM ÁGUA", "NO WATER"), "on" if fw >= 0.98 else "offb")
    if fe >= 0.98:
        hs = box("house", T("Casas", "Homes"), T("luz normal", "normal power"), "on")
    elif r["sE"] >= 0.95 * r["dEmin"]:
        hs = box("house", T("Casas", "Homes"), T("luz + telemóvel", "lights + phone"), "part")
    else:
        hs = box("house", T("Casas", "Homes"), T("ÀS ESCURAS", "IN THE DARK"), "offb")
    if r["dP"] <= 0.05:
        mill = box("mill", T("Moagem", "Grain mill"), T("fechada (fora de horas)", "closed (off hours)"), "cut")
    elif r["sP"] >= 0.98 * r["dP"]:
        mill = box("mill", T("Moagem", "Grain mill"), T("a trabalhar", "running"), "on")
    elif smart and not r["blackout"]:
        mill = box("mill", T("Moagem", "Grain mill"), T("pausa planeada", "planned pause"), "cut")
    else:
        mill = box("mill", T("Moagem", "Grain mill"), T("PARADA", "STOPPED"), "offb")

    soc = 100 * r["soc"]
    col = C["red"] if soc < 20 else C["bat"]
    batt = (f'<div class="batt"><div class="f" style="width:{max(soc, 2):.0f}%;background:{col}"></div>'
            f'<div class="lbl">{T("bateria", "battery")} {soc:.0f} %</div></div>')

    if not smart:
        if r["blackout"]:
            say = T('<div class="say bad"><b>Apagão total.</b> A bateria chegou ao fim e o sistema desligou tudo, '
                    'incluindo o centro de saúde. Só volta quando a bateria recuperar 30 %.</div>',
                    '<div class="say bad"><b>Total blackout.</b> The battery ran out and the system switched everything '
                    'off, including the health centre. It only comes back when the battery recovers to 30 %.</div>')
        elif r["fase"] == "preparação":
            say = T('<div class="say">Tudo ligado como num dia normal. O sistema <b>não sabe</b> que o ciclone vem aí.</div>',
                    '<div class="say">Everything on, as on a normal day. The system <b>does not know</b> the cyclone is coming.</div>')
        else:
            say = T('<div class="say">Tudo ligado enquanto houver bateria. Não há forma de escolher o que desligar.</div>',
                    '<div class="say">Everything on while the battery lasts. There is no way to choose what to switch off.</div>')
    else:
        if r["mode"] == "alerta":
            say = T(f'<div class="say"><b>Alerta do {met} recebido.</b> O RESILIA enche a bateria e o depósito de água '
                    'e prepara a reserva da clínica.</div>',
                    f'<div class="say"><b>{met} warning received.</b> RESILIA fills the battery and the water tank and '
                    'sets aside the clinic reserve.</div>')
        elif r["mode"] == "evento" or r["fase"] == "recuperação":
            if fe >= 0.98:
                say = T('<div class="say"><b>Modo ciclone:</b> há energia para tudo, com a reserva da clínica guardada.</div>',
                        '<div class="say"><b>Storm mode:</b> enough energy for everything, with the clinic reserve kept aside.</div>')
            else:
                say = T('<div class="say"><b>Modo ciclone:</b> a clínica tem prioridade. As casas ficam com luz e telemóvel '
                        'quando há margem; a moagem espera.</div>',
                        '<div class="say"><b>Storm mode:</b> the clinic comes first. Homes keep lights and phone charging '
                        'when there is margin; the mill waits.</div>')
        else:
            say = T('<div class="say">Operação normal.</div>', '<div class="say">Normal operation.</div>')
    return f'<div class="svc">{clinic}{water}{hs}{mill}</div>{batt}{say}'


def _phase_marks(fig, o):
    ph = o["fase"].values
    labels = (("preparação", T("ANTES (aviso)", "BEFORE (warning)")), ("evento", T("CICLONE (72 h)", "CYCLONE (72 h)")),
              ("recuperação", T("DEPOIS", "AFTER")))
    for name, label in labels:
        idx = np.flatnonzero(ph == name)
        if len(idx):
            fig.add_annotation(x=o.index[idx[len(idx) // 2]], y=1.0, yref="paper", yanchor="bottom", showarrow=False,
                               text=f"<b>{label}</b>", font=dict(size=12, color=C["red"] if name == "evento" else "#6B7280"))


def _heat(o, smart, title, t_mark=None):
    fig = charts.services_heatmap(o, smart, title, rows=ROWS, height=250)
    _phase_marks(fig, o)
    if t_mark is not None:
        fig.add_vline(x=o.index[t_mark], line=dict(color="#2563EB", width=3))
    fig.update_layout(margin=dict(l=150, t=70, b=30, r=10))
    return fig


def _idea(ic, h, x, edge=None):
    style = f' style="border-top-color:{edge}"' if edge else ""
    return f'<div class="idea"{style}><div class="ic">{icon(ic, 30)}</div><div class="h">{h}</div><div class="x">{x}</div></div>'


# ───────────────────────────── diapositivos ─────────────────────────────
def s_abertura(d):
    mc, mr = d["mc"], d["mr"]
    _slide(f"1 · {_title(0)}", T(
        f"""<h1>Quando o ciclone chega,<br><span class="red">a clínica não pode apagar.</span></h1>
<div class="lead">Fevereiro de 2023: o ciclone <b>Freddy</b> passa por <b>Mabote, Inhambane</b>. Simulámos, com os dados
meteorológicos reais dessas horas, uma mini-rede solar de aldeia. Gerida como hoje, o centro de saúde fica
<b>{mc['crit_out_h']} horas às escuras</b>. Com o <b class="red">RESILIA</b>, com o <b>mesmo equipamento</b>:
<b class="red">{mr['crit_out_h']} horas</b>.</div>""",
        f"""<h1>When the cyclone hits,<br><span class="red">the clinic cannot go dark.</span></h1>
<div class="lead">February 2023: Cyclone <b>Freddy</b> sweeps through <b>Mabote, Inhambane</b>. Using the real weather data for
those hours, we simulated a village solar mini-grid. Operated the way it is today, the health centre spends
<b>{mc['crit_out_h']} hours in the dark</b>. With <b class="red">RESILIA</b> and the <b>same equipment</b>:
<b class="red">{mr['crit_out_h']} hours</b>.</div>""") + f"""
<div class="big">
  <div class="k"><div class="n red">{mc['crit_out_h']} h → {mr['crit_out_h']} h</div>
   <div class="u">{T("centro de saúde sem energia durante o ciclone", "health centre without power during the cyclone")}</div></div>
  <div class="k"><div class="n">{num(d['people'])}</div>
   <div class="u">{T(f"pessoas numa aldeia de {d['households']} famílias", f"people in a village of {d['households']} households")}</div></div>
  <div class="k"><div class="n">0</div><div class="u">{T("painéis ou baterias a mais", "extra panels or batteries")}</div></div>
  <div class="k"><div class="n">3</div><div class="u">{T("ciclones reais de Inhambane testados (Freddy, Dineo, Filipo)",
   "real Inhambane cyclones tested (Freddy, Dineo, Filipo)")}</div></div>
</div>""")


def s_problema(d):
    s = d["stats"]
    _slide(f"2 · {_title(1)}", f"""
<h2>{T("O Freddy roubou o sol durante dias, e a mini-rede apagou tudo.",
       "Freddy took the sun away for days, and the mini-grid shut everything down.")}</h2>
<div class="big">
  <div class="k"><div class="n red">{num(s['sol_pct'])} %</div><div class="u">{T("do sol normal nas 72 h do ciclone",
   "of normal sunshine during the 72-hour cyclone")}</div></div>
  <div class="k"><div class="n">{num(s['gust_kmh'])} km/h</div><div class="u">{T("rajadas de vento em Mabote", "wind gusts in Mabote")}</div></div>
  <div class="k"><div class="n">{num(s['rain'])} mm</div><div class="u">{T("de chuva em 4 dias: estradas cortadas, não chega gasóleo",
   "of rain in 4 days: roads cut, no diesel gets through")}</div></div>
  <div class="k"><div class="n">{num(s['pmin'])} hPa</div><div class="u">{T("pressão mínima: a passagem do ciclone nos dados",
   "minimum pressure: the cyclone's passage in the data")}</div></div>
</div>""")
    b = pd.DataFrame(d["blocks"])
    lab = {"preparação": T("antes", "before"), "evento": T("ciclone", "cyclone"), "recuperação": T("depois", "after")}
    xs = [f"{r.day} {month_short(r.month)}<br>({lab[r.fase]})" for r in b.itertuples()]
    colors = [C["red"] if f != "preparação" else C["solar"] for f in b["fase"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=xs, y=b["sol"], name=T("Energia que o sol deu", "Energy from the sun"), marker_color=colors,
                         text=[f"{v:.0f}" for v in b["sol"]], textposition="outside"))
    fig.add_trace(go.Scatter(x=xs, y=b["pede"], name=T("Energia que a aldeia precisa", "Energy the village needs"),
                             mode="lines+markers", line=dict(color="#1F2933", width=3), marker=dict(size=9)))
    fig.update_layout(yaxis_title=T("kWh por dia", "kWh per day"), bargap=0.35)
    charts.base(fig, T("Por dia: o sol que os painéis receberam (barras) e o que a aldeia precisa (linha). Vermelho = dias do ciclone",
                       "Per day: sun received by the panels (bars) vs what the village needs (line). Red = cyclone days"),
                height=380)
    fig.update_layout(margin=dict(b=70))
    st.plotly_chart(fig, width="stretch")
    st.markdown('<div class="ideas">' +
                _idea("ruler", T("Desenhadas para o dia médio", "Designed for the average day"),
                      T("As mini-redes são dimensionadas com médias anuais, não com os piores dias reais.",
                        "Mini-grids are sized on annual averages, not on the worst real days."), "#9AA3AF") +
                _idea("eyeoff", T("Não sabem o que vem aí", "Blind to what's coming"),
                      T("Gastam a bateria na primeira noite como se fosse um dia normal.",
                        "They drain the battery on the first night as if it were a normal day."), "#9AA3AF") +
                _idea("bulb", T("Um só interruptor", "A single switch"),
                      T("Quando falta energia, apaga tudo de uma vez: casas, água e o centro de saúde.",
                        "When energy runs short, everything goes off at once: homes, water and the health centre."),
                      "#9AA3AF") + "</div>", unsafe_allow_html=True)


def s_solucao(d):
    _slide(f"3 · {_title(2)}", f"""
<h2>{T("RESILIA: o mesmo sistema solar, agora com cérebro.", "RESILIA: the same solar system, now with a brain.")}</h2>
<div class="lead">{T("Um controlador instalado na mini-rede que usa a previsão meteorológica para decidir, hora a hora, para onde vai cada kWh.",
                     "A controller installed on the mini-grid that uses the weather forecast to decide, hour by hour, where every kWh goes.")}</div>
<div class="ideas">
 {_idea("signal", T("1. Saber antes", "1. Know in advance"),
        T("Recebe o alerta do <b>INAM</b> 48 h antes. Enche a bateria e o depósito de água <b>antes</b> do ciclone chegar.",
          "Receives the <b>INAM</b> warning 48 h ahead. Fills the battery and the water tank <b>before</b> the cyclone arrives."))}
 {_idea("shield", T("2. Guardar para o que salva vidas", "2. Save energy for what saves lives"),
        T("Calcula quanta energia a clínica vai precisar até ao fim da tempestade e <b>não deixa gastar essa reserva</b>.",
          "Calculates how much energy the clinic will need until the storm ends and <b>protects that reserve</b>."))}
 {_idea("split", T("3. Desligar por ordem, nunca tudo", "3. Switch off in order, never everything"),
        T("Primeiro pausa a moagem, depois limita as casas a luz e telemóvel. <b>A clínica é a última</b>.",
          "First the mill pauses, then homes are limited to lights and phone charging. <b>The clinic is last</b>."))}
</div>
<div class="lead" style="margin-top:18px;font-size:17px"><b>{T("O que se instala:", "What gets installed:")}</b>
{T("1 controlador · circuitos separados (clínica / água / casas / moagem) · contadores inteligentes nas casas · estrutura anti-ciclone · baterias em contentor protegido.",
   "1 controller · separate circuits (clinic / water / homes / mill) · smart meters in homes · cyclone-rated structure · batteries in a protected enclosure.")}</div>""")


def s_como(d):
    n_pan = round(d["pv"] * 1000 / 550)
    steps = [
        (T("1 · Clima real", "1 · Real weather"),
         T("O que aconteceu em Mabote, <b>hora a hora</b>, no Freddy: sol, vento, chuva, temperatura (dados ERA5 do Copernicus).",
           "What happened in Mabote, <b>hour by hour</b>, during Freddy: sun, wind, rain, temperature (Copernicus ERA5 data).")),
        (T("2 · Energia produzida", "2 · Energy produced"),
         T(f"Quanto os <b>{d['pv']:.0f} kWp de painéis</b> (≈ {n_pan} painéis) produzem em cada hora com aquele céu.",
           f"How much the <b>{d['pv']:.0f} kWp of panels</b> (≈ {n_pan} panels) produce each hour under that sky.")),
        (T("3 · Aldeia a consumir", "3 · Village demand"),
         T(f"<b>{d['households']} casas</b>, centro de saúde, bomba de água, escola e moagem, cada uma no seu horário.",
           f"<b>{d['households']} homes</b>, health centre, water pump, school and mill, each on its own schedule.")),
        (T("4 · A bateria decide", "4 · The battery decides"),
         T(f"Há sol? Usa. Falta? Tira da <b>bateria de {d['bat']:.0f} kWh</b>. Não chega? <b>Quem fica sem luz?</b>",
           f"Sun available? Use it. Short? Draw from the <b>{d['bat']:.0f} kWh battery</b>. Not enough? <b>Who goes dark?</b>")),
    ]
    chain = '<div class="chain">' + '<div class="arrow">→</div>'.join(
        f'<div class="n"><div class="h">{h}</div><div class="x">{x}</div></div>' for h, x in steps) + "</div>"
    _slide(f"4 · {_title(3)}", f"""
<h2>{T("Como funciona a simulação, em 30 segundos", "How the simulation works, in 30 seconds")}</h2>{chain}
<div class="duo" style="margin-top:8px">
 <div class="side today"><div class="tt">{_dot("#9AA3AF")}{T("Sistema de hoje", "Today's system")}</div>
 <div class="lead" style="font-size:16px;margin-top:6px">{T("Sem previsão. Um só circuito: quando a bateria acaba, <b>apaga tudo</b>.",
   "No forecast. A single circuit: when the battery runs out, <b>everything goes dark</b>.")}</div></div>
 <div class="side res"><div class="tt">{_dot(C["red"])}{T("Com RESILIA", "With RESILIA")}</div>
 <div class="lead" style="font-size:16px;margin-top:6px">{T("Alerta 48 h antes, reserva para a clínica, cortes por ordem de prioridade.",
   "48-hour warning, clinic reserve, cuts in order of priority.")}</div></div>
</div>
<div class="lead" style="margin-top:14px;font-size:16px">{T("Os dois lados têm <b>exactamente o mesmo equipamento</b> e o mesmo clima. A única diferença é a forma de gerir.",
   "Both sides have <b>exactly the same equipment</b> and the same weather. The only difference is how the system is operated.")}</div>""")


def s_simulacao(d):
    o, r, w = d["oc"], d["orr"], d["w"]
    ev0, ev1 = d["ev0"], d["ev1"]
    n = len(r)
    moments = [
        (T("1 · Aviso: faltam 24 h", "1 · Warning: 24 h to go"), ev0 - 24),
        (T("2 · O ciclone chega", "2 · The cyclone arrives"), ev0 + 6),
        (T("3 · 1.ª noite de ciclone", "3 · First night of the cyclone"), (d["first_bo"] or ev0 + 10) + 2),
        (T("4 · 2.º dia: o sol mal aparece", "4 · Day 2: barely any sun"), ev0 + 25),
        (T("5 · 3.ª noite", "5 · Third night"), ev0 + 62),
        (T("6 · Depois: ainda chove", "6 · After: still raining"), min(n - 1, ev1 + 16)),
    ]
    _slide(f"5 · {_title(4)}", f'<h2>{T("O ciclone Freddy, hora a hora: o mesmo equipamento, duas decisões", "Cyclone Freddy, hour by hour: same equipment, two decisions")}</h2>',
           cls="slide compact")
    st.session_state["_mhours"] = [m[1] for m in moments]
    st.session_state.setdefault("moment", 0)
    st.session_state.setdefault("hour", moments[0][1])
    st.segmented_control(T("Escolha um momento do ciclone", "Choose a moment of the cyclone"), list(range(len(moments))),
                         key="moment", on_change=_on_moment, format_func=lambda k: moments[k][0])
    with st.expander(T("Explorar qualquer hora (opcional)", "Explore any hour (optional)"), icon=":material/schedule:"):
        st.slider(T("Hora da simulação", "Simulation hour"), 0, n - 1, key="hour",
                  help=T("0 = dois dias antes do ciclone; o ciclone vai da hora 48 à 119.",
                         "0 = two days before the cyclone; the cyclone runs from hour 48 to 119."))
    t = int(st.session_state["hour"])
    ts = r.index[t]
    st.markdown(f"<div style='font-size:20px;font-weight:800;margin:6px 0 2px 0'>{date_long(ts)}</div>"
                f"{_weather_words(w, t)}", unsafe_allow_html=True)
    st.markdown(f"""<div class="duo">
<div class="side today"><div class="tt">{_dot("#9AA3AF")}{T("Sistema de hoje", "Today's system")}</div>{_board(o, t, False)}</div>
<div class="side res"><div class="tt">{_dot(C["red"])}{T("Com RESILIA", "With RESILIA")}</div>{_board(r, t, True)}</div></div>""",
                unsafe_allow_html=True)

    st.markdown(f"<div style='font-size:20px;font-weight:800;margin:22px 0 4px 0'>"
                f"{T('O mapa de luzes: cada quadrado é uma hora', 'The lights map: each square is one hour')}</div>",
                unsafe_allow_html=True)
    legend(charts.status_legend() + [(T("momento escolhido", "selected moment"), "#2563EB")])
    st.plotly_chart(_heat(o, False, T("SISTEMA DE HOJE · os quadrados pretos são apagões, que apanham tudo ao mesmo tempo",
                                      "TODAY'S SYSTEM · black squares are blackouts, hitting everything at once"), t),
                    width="stretch")
    st.plotly_chart(_heat(r, True, T("COM RESILIA · o centro de saúde fica aceso do princípio ao fim",
                                     "WITH RESILIA · the health centre stays on from start to finish"), t),
                    width="stretch")


def s_resultados(d):
    mc, mr, mcg, mrg = d["mc"], d["mr"], d["mcg"], d["mrg"]
    save = 100 * (1 - mrg["diesel_L"] / max(mcg["diesel_L"], 1))
    chk = icon("check", 34, "#16A34A", 2.6)
    crs = icon("x", 34, C["red"], 2.6)
    _slide(f"6 · {_title(5)}", f"""
<h2>{T("Resultado: a mesma energia, um destino diferente.", "Result: the same energy, a different destination.")}</h2>
<div class="lead">{T("Nas 96 horas de ciclone e chuva (24 a 28 de Fevereiro de 2023), com o mesmo equipamento:",
                     "Over the 96 hours of cyclone and rain (24–28 February 2023), with the same equipment:")}</div>
<div class="big">
  <div class="k"><div class="n red">{mc['crit_out_h']} h → {mr['crit_out_h']} h</div>
   <div class="u">{T("centro de saúde sem energia", "health centre without power")}</div></div>
  <div class="k"><div class="n red">{crs if not mc['cold_chain_ok'] else chk} → {chk if mr['cold_chain_ok'] else crs}</div>
   <div class="u">{T("cadeia de frio das vacinas: em risco hoje, protegida com RESILIA",
                     "vaccine cold chain: at risk today, protected with RESILIA")}</div></div>
  <div class="k"><div class="n red">{num(mc['water_pct'])}% → {num(mr['water_pct'])}%</div>
   <div class="u">{T("da água potável entregue à população", "of drinking water delivered to the population")}</div></div>
  <div class="k"><div class="n red">{num(mc['essmin_pct'])}% → {num(mr['essmin_pct'])}%</div>
   <div class="u">{T("do tempo com luz e telemóvel nas casas", "of the time homes have lights and phone charging")}</div></div>
</div>""")
    cyc = pd.DataFrame(d["cyc"])
    names = [event(k, "name") for k in cyc["ev"]]
    l, r = st.columns([3, 2])
    with l:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=names, y=cyc["hoje"], name=T("Sistema de hoje", "Today's system"), marker_color=C["conv"],
                             text=[f"{v} h" for v in cyc["hoje"]], textposition="outside"))
        fig.add_trace(go.Bar(x=names, y=cyc["res"], name=T("Com RESILIA", "With RESILIA"), marker_color=C["res"],
                             text=[f"{v} h" for v in cyc["res"]], textposition="outside"))
        fig.update_layout(barmode="group", yaxis_title=T("horas com a clínica sem energia", "hours with the clinic unpowered"),
                          yaxis_range=[0, max(cyc["hoje"].max(), 5) * 1.25])
        st.plotly_chart(charts.base(fig, T("Não foi sorte: 3 ciclones reais de Inhambane, o mesmo resultado",
                                           "Not luck: 3 real Inhambane cyclones, the same result"), height=340),
                        width="stretch")
    with r:
        st.markdown(f"""<div class="slide" style="padding:22px 24px">
<div class="num">{T("E se houver um gerador de reserva?", "What if there is a backup generator?")}</div>
<div class="lead" style="font-size:16px;margin-top:8px">{T("Com um gerador de 15 kW e 200 L de gasóleo (as estradas estão cortadas, não há reabastecimento):",
   "With a 15 kW generator and 200 L of diesel (roads are cut, no resupply):")}</div>
<div class="big" style="grid-template-columns:1fr 1fr">
 <div class="k"><div class="u">{_dot("#9AA3AF")}{T("Sistema de hoje", "Today's system")}</div><div class="n" style="font-size:30px">{num(mcg['diesel_L'])} L</div>
 <div class="u">{T(f"e a clínica ainda fica <b>{mcg['crit_out_h']} h</b> às escuras", f"and the clinic is still dark for <b>{mcg['crit_out_h']} h</b>")}</div></div>
 <div class="k"><div class="u">{_dot(C["red"])}{T("Com RESILIA", "With RESILIA")}</div><div class="n red" style="font-size:30px">{num(mrg['diesel_L'])} L</div>
 <div class="u">{T(f"e a clínica fica <b>{mrg['crit_out_h']} h</b> às escuras", f"and the clinic is dark for <b>{mrg['crit_out_h']} h</b>")}</div></div>
</div><div class="lead" style="font-size:15px">{T(f"−{num(save)} % de gasóleo, e o centro de saúde sempre ligado.",
   f"−{num(save)} % diesel, and the health centre always on.")}</div></div>""", unsafe_allow_html=True)


def s_viabilidade(d):
    _slide(f"7 · {_title(6)}", f"""
<h2>{T("Custa pouco, usa tecnologia que já existe e tem quem pague.", "Low cost, proven technology, and clear payers.")}</h2>
<div class="big">
  <div class="k"><div class="n red">≈ {num(d['extra'] / 1000)} {T("mil USD", "k USD")}</div><div class="u">{T(
    f"para acrescentar o RESILIA a uma mini-rede de {d['households']} famílias (+{num(100 * d['extra'] / d['base_capex'])} % sobre o sistema)",
    f"to add RESILIA to a {d['households']}-household mini-grid (+{num(100 * d['extra'] / d['base_capex'])} % on the system)")}</div></div>
  <div class="k"><div class="n">≈ {num(d['per_fam'])} USD</div><div class="u">{T("por família, uma única vez", "per household, one-off")}</div></div>
  <div class="k"><div class="n">≈ {num(d['month'], 1)} USD</div><div class="u">{T("por família e por mês, em 20 anos", "per household per month, over 20 years")}</div></div>
  <div class="k"><div class="n">0</div><div class="u">{T("tecnologias por inventar: controlador, contadores e alertas já existem",
    "technologies to invent: controllers, meters and warnings already exist")}</div></div>
</div>
<div class="ideas">
 {_idea("card", T("Quem paga", "Who pays"), T(
   "Famílias em pré-pagamento · contratos com o centro de saúde, a escola e as telecomunicações · moagem e frio · "
   "financiamento climático por resultados («horas de clínica garantidas») · créditos de carbono.",
   "Pay-as-you-go households · anchor contracts with the health centre, school and telecoms · milling and cold storage · "
   "results-based climate finance (“guaranteed clinic hours”) · carbon credits."))}
 {_idea("tool", T("Quem opera", "Who operates"), T(
   "Um operador ou cooperativa local, com técnicos da aldeia. O RESILIA é licenciado como software por mini-rede.",
   "A local operator or cooperative, with technicians from the village. RESILIA is licensed as software per mini-grid."))}
 {_idea("users", T("Com quem", "With whom"), T(
   "<b>INAM</b> (alertas) · <b>INGD</b> (gestão de desastres) · <b>FUNAE</b>, ALER e EDM (energia) · <b>UEM</b> · projecto <b>EMERGE</b>.",
   "<b>INAM</b> (warnings) · <b>INGD</b> (disaster management) · <b>FUNAE</b>, ALER and EDM (energy) · <b>UEM</b> · <b>EMERGE</b> project."))}
</div>""")


def s_futuro(d):
    t = all_events_summary()
    ma, ml = t[t.site == "MA"], t[t.site == "ML"]
    road = [(T("2026 · hoje", "2026 · today"), T("Protótipo funcional com 11 anos de clima real e previsão em tempo real.",
                                                 "Working prototype with 11 years of real climate data and live forecasts.")),
            (T("2027 · piloto", "2027 · pilot"), T(f"<b>Mabote</b>: 1 mini-rede, {d['households']} famílias, ligação ao INAM.",
                                                   f"<b>Mabote</b>: 1 mini-grid, {d['households']} households, linked to INAM.")),
            ("2028", T("Inhambane e Gaza + pilotos em Marrocos e no Mali.", "Inhambane and Gaza + pilots in Morocco and Mali.")),
            ("2030", T("Plataforma regional ligada a alertas precoces e seguros climáticos.",
                       "Regional platform linked to early-warning systems and climate insurance."))]
    chain = '<div class="chain" style="margin-top:16px">' + '<div class="arrow">→</div>'.join(
        f'<div class="n"><div class="h">{h}</div><div class="x">{x}</div></div>' for h, x in road) + "</div>"
    _slide(f"8 · {_title(7)}", f"""
<h2>{T("De Mabote para Moçambique, e para os 3 países do EMERGE.", "From Mabote to Mozambique, and to the 3 EMERGE countries.")}</h2>
<div class="big">
  <div class="k"><div class="n">{T("3 países", "3 countries")}</div><div class="u">{T(
    "Moçambique, Marrocos e Mali: o mesmo motor, sem mudar o código, só muda o clima",
    "Mozambique, Morocco and Mali: the same engine, no code changes, only the climate changes")}</div></div>
  <div class="k"><div class="n red">{ma.conv_out.sum()} h → {ma.res_out.sum()} h</div><div class="u">{T(
    "<b>Marrocos</b>, Alto Atlas, neve e −10 °C: clínica sem energia em 3 eventos reais",
    "<b>Morocco</b>, High Atlas, snow and −10 °C: clinic without power across 3 real events")}</div></div>
  <div class="k"><div class="n red">{ml.conv_out.sum()} h → {ml.res_out.sum()} h</div><div class="u">{T(
    "<b>Mali</b>, Kayes, calor de 45 °C e cheias: clínica sem energia em 3 eventos reais",
    "<b>Mali</b>, Kayes, 45 °C heat and floods: clinic without power across 3 real events")}</div></div>
  <div class="k"><div class="n">{icon("globe", 38, "#1F2933", 1.6)}</div><div class="u">{T(
    "qualquer aldeia do planeta: basta escrever as coordenadas", "any village on the planet: just enter the coordinates")}</div></div>
</div>{chain}
<div class="lead" style="margin-top:14px">{T(
  "<b>O nosso pedido:</b> apoio para o <b class='red'>piloto em Mabote em 2027</b>: uma aldeia onde o centro de saúde nunca mais apaga quando chega o ciclone.",
  "<b>Our ask:</b> support for the <b class='red'>Mabote pilot in 2027</b>: a village where the health centre never goes dark again when a cyclone hits.")}</div>
<div style="font-size:30px;font-weight:800;margin-top:18px;color:#1F2933">{T(
  'Energia que não apaga <span class="red">quando o clima aperta.</span>',
  'Power that stays on <span class="red">when the weather turns.</span>')}</div>
<div class="lead" style="font-size:15px;margin-top:8px">{T("Grupo 36", "Team 36")} · Ezequias Miocha · Laura Hele · Suely Muando · Universidade Eduardo Mondlane</div>""")


RENDER = dict(abertura=s_abertura, problema=s_problema, solucao=s_solucao, como=s_como, simulacao=s_simulacao,
              resultados=s_resultados, viabilidade=s_viabilidade, futuro=s_futuro)


# ───────────────────────────── página ─────────────────────────────
def render():
    d = pitch_data(__version__)
    st.session_state.setdefault("slide_nav", 0)
    i = int(st.session_state["slide_nav"])
    st.markdown('<div id="top"></div>', unsafe_allow_html=True)

    # barra flutuante: título, cronómetro e navegação acompanham o scroll
    with st.container(key="pitchbar"):
        head = st.columns([7, 3], vertical_alignment="center")
        with head[0]:
            st.markdown(f"<div style='font-size:15px;color:#6B7280;font-weight:600'><b style='color:#1F2933'>"
                        f"RESILIA 72H · {T('apresentação ao júri', 'pitch to the jury')}</b> · "
                        f"{T('diapositivo', 'slide')} {i + 1} {T('de', 'of')} {len(SLIDES)} · "
                        f"{T('Moçambique', 'Mozambique')}</div>", unsafe_allow_html=True)
        with head[1]:
            _timer(ENDS[i])
        nav = st.columns(len(SLIDES), gap="small")
        for k in range(len(SLIDES)):
            with nav[k]:
                st.button(f"{k + 1} · {_title(k)}", key=f"nav_{k}", on_click=_go, args=(k,), width="stretch",
                          type="primary" if k == i else "secondary", help=f"{SLIDES[k][3]} s")

    key = SLIDES[i][0]
    RENDER[key](d)

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
    st.caption(T("Simulação real do motor RESILIA · dados meteorológicos ERA5 (Copernicus) para Mabote, 22–28 Fev 2023 · "
                 "mini-rede de 45 kWp + 120 kWh, sem gerador · para explorar tudo, use o menu no topo.",
                 "Real simulation by the RESILIA engine · ERA5 weather data (Copernicus) for Mabote, 22–28 Feb 2023 · "
                 "45 kWp + 120 kWh mini-grid, no generator · use the top menu to explore everything."))
    st.markdown(f'<a class="totop" href="#top" title="{T("Voltar ao topo", "Back to top")}">{icon("up", 20, stroke=2.4)}</a>',
                unsafe_allow_html=True)
