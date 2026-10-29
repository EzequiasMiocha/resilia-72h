"""Apresentação ao júri: directa, 6 diapositivos (contexto, desafio e objectivo, como respondemos, 24 h,
resiliente e eficiente, conclusão)."""
from __future__ import annotations

import time

import numpy as np
import streamlit as st
import streamlit.components.v1 as components

from resilia import model as M
from ui import charts
from ui.i18n import T, cut_txt, day_label, num, verdict_txt
from ui.icons import icon
from ui.style import C

from .panel import get_demand, get_resource, get_year, presets

VILLAGE = (200, True, True, True, True, 0.0)       # aldeia de referência da apresentação
VCOL = {"ok": "#16A34A", "partial": "#B45309", "fragile": C["red"]}

SLIDES = [
    ("contexto", "Contexto", "Context", 45,
     "Onde estamos (Mabote, sem rede), qual é o problema (o sol muda todos os dias) e o que acontece se o sistema for "
     "pensado só para o dia médio (a aldeia fica às escuras). Mostrem os números.",
     "Where we are (Mabote, no grid), the problem (the sun changes every day) and what happens if the system is designed "
     "only for the average day (the village goes dark). Show the numbers."),
    ("objectivo", "Desafio e objectivo", "Challenge and objective", 55,
     "À esquerda, o desafio do EMERGE em três linhas. À direita, o nosso objectivo numa frase. Expliquem porque o "
     "sistema é só solar: o vento de Mabote é fraco para gerar energia.",
     "Left: the EMERGE challenge in three lines. Right: our objective in one sentence. Explain why the system is solar "
     "only: Mabote's wind is too weak to generate power."),
    ("metodo", "Metodologia", "Methodology", 55,
     "Os 5 passos, da esquerda para a direita: sol real → produção dos painéis → procura → bateria e balanço de cada "
     "hora → dimensionamento resiliente. Uma frase por passo.",
     "The 5 steps, left to right: real sun → panel output → demand → battery and hourly balance → resilient sizing. "
     "One sentence per step."),
    ("balanco", "Dias seguidos", "Days in a row", 90,
     "Quatro dias reais seguidos. Sigam a linha da bateria: os dias 1 e 2 enchem-na; no dia 3 o sistema pequeno já não "
     "enche; no dia 4 fica às escuras e o resiliente aguenta com a reserva.",
     "Four real days in a row. Follow the battery line: days 1 and 2 fill it; on day 3 the small system no longer fills "
     "it; on day 4 it goes dark while the resilient one holds on with its reserve."),
    ("resiliente", "Resiliente e eficiente", "Resilient and efficient", 75,
     "Digam a frase do título: resiliente em 98,6 % dos dias. Depois os números por ano e o teste nos 5 tipos de dia.",
     "Say the title sentence: resilient on 98.6 % of days. Then the yearly numbers and the 5 day-type test."),    ("conclusao", "Conclusão", "Conclusion", 40,
     "O que entregamos, o resultado, como se mantém e se replica, e o próximo passo. Frase final.",
     "What we deliver, the result, how it is sustained and replicated, and the next step. Closing line."),
]
ENDS = list(np.cumsum([s[3] for s in SLIDES]))


def _title(k):
    return T(SLIDES[k][1], SLIDES[k][2])


@st.cache_data(show_spinner=False)
def pitch_data(version=5):
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
    imp = get_year(VILLAGE, float(r["pv"]), float(r["bat"]))[1]
    seq = {}
    for name, row in (("e", e), ("r", r)):
        s = M.System(pv=row["pv"], bat=row["bat"])
        seq[name] = M.simulate_period(res, D, s, M.SEQUENCE["start"], len(M.SEQUENCE["days"]))
    o0 = seq["e"]
    seq_sun = [res.loc[o0.index[24 * k:24 * (k + 1)], "ghi"].sum() / 1000 for k in range(len(M.SEQUENCE["days"]))]
    return dict(e=e, r=r, imp=imp, seq=seq, seq_sun=seq_sun, weak_per_year=weak.sum() / (len(daily) / 365.25), weak_run=best,
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


def hcol(m):
    """Verde = sem cortes; laranja = cortes curtos; vermelho = muitas horas sem luz."""
    return VCOL[M.verdict(m["risk"], m["hours"])]


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
  <div class="k"><div class="n">{num(d['weak_run'])} {T("dias", "days")}</div><div class="u">{T("seguidos com pouco sol: a bateria tem de aguentar isto",
   "in a row with little sun: the battery must withstand this")}</div></div>
  <div class="k"><div class="n">{num(d['sun_min'], 1)}–{num(d['sun_max'], 1)}</div><div class="u">{T("kWh/m² de sol por dia: do dia mais fraco ao mais forte",
   "kWh/m² of sun per day: from weakest to strongest day")}</div></div>
  <div class="k"><div class="n">{num(d['dem_min'])}–{num(d['dem_max'])}</div><div class="u">{T("kWh/dia: a procura de 200 famílias também varia",
   "kWh/day: demand from 200 households varies too")}</div></div>
</div>
<div class="lead" style="font-size:15px;margin-top:6px">{T("Fonte: dados horários reais de Mabote (ERA5, Copernicus).",
 "Source: real hourly Mabote data (ERA5, Copernicus).")}</div>""")


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
   <li>{T("Dados reais de Mabote, hora a hora: dias de sol, nuvens, chuva e calor.",
          "Real Mabote data, hour by hour: sunny, cloudy, rainy and hot days.")}</li>
   <li>{T("Procura calculada a partir do <b>número de famílias</b> e dos serviços.",
          "Demand calculated from the <b>number of households</b> and services.")}</li>
   <li>{T("<b>Resiliência obrigatória</b>; entre os sistemas resilientes, escolhe-se o mais barato (eficiência).",
          "<b>Resilience is required</b>; among resilient systems, the cheapest is chosen (efficiency).")}</li>
   <li>{T(f"Só solar: o vento médio em Mabote é de {num(d['wind_mean'], 1)} m/s, fraco para gerar energia. Entra apenas porque arrefece os painéis.",
          f"Solar only: mean wind in Mabote is {num(d['wind_mean'], 1)} m/s, too weak to generate power. It only counts because it cools the panels.")}</li>
  </ul>
 </div>
</div>""")


def _step_card(n, ic, title, text, formula):
    return (f'<div class="m"><div class="top"><span class="no">{n}</span>{icon(ic, 26, "#C8102E", 2)}</div>'
            f'<div class="h">{title}</div><div class="x">{text}</div><div class="f">{formula}</div></div>')


def s_metodo(d):
    cards = [
        _step_card(1, "sun", T("Recurso solar", "Solar resource"),
                   T("Sol real de Mabote, hora a hora (satélite ERA5). Convertido para painéis inclinados a 22°, virados a norte.",
                     "Real Mabote sun, hour by hour (ERA5 satellite data). Converted to panels tilted 22°, facing north."),
                   T("sol no painel = directo + difuso + reflectido", "sun on panel = direct + diffuse + reflected")),
        _step_card(2, "panel", T("Produção solar", "Solar output"),
                   T("Os painéis convertem o sol em electricidade. O calor reduz a produção; o vento arrefece os painéis.",
                     "Panels turn sunlight into electricity. Heat lowers output; wind cools the panels."),
                   T("kW = kWp × sol/1000 × 0,88 × (1 − 0,35 % por °C)", "kW = kWp × sun/1000 × 0.88 × (1 − 0.35 % per °C)")),
        _step_card(3, "house", T("Procura da aldeia", "Village demand"),
                   T("Número de famílias × consumo de cada hora + centro de saúde, escola, bomba de água e moagem.",
                     "Number of households × hourly use + health centre, school, water pump and mill."),
                   T("varia com a hora, o dia da semana e o calor", "varies with the hour, weekday and heat")),
        _step_card(4, "battery", T("Bateria e balanço", "Battery and balance"),
                   T("Em cada hora: o sol serve a aldeia; o que sobra vai para a bateria; o que falta sai da bateria.",
                     "Every hour: the sun serves the village; the surplus goes to the battery; shortfalls come from it."),
                   T("eficiência 95 % · nunca abaixo de 20 %", "95 % efficiency · never below 20 %")),
        _step_card(5, "shield", T("Dimensionamento resiliente", "Resilient sizing"),
                   T(f"{M.N_SYSTEMS} sistemas testados em milhares de dias reais seguidos. Escolhe o mais barato que não deixa a aldeia às escuras.",
                     f"{M.N_SYSTEMS} systems tested on thousands of real consecutive days. Picks the cheapest that keeps the lights on."),
                   T("resiliência obrigatória → depois o menor custo", "resilience required → then lowest cost")),
    ]
    maps = [(T("Entradas", "Inputs"), T("painel lateral", "side panel")), (T("Balanço 24 h", "24-h balance"), T("Simulador", "Simulator")),
            (T("Risco de interrupção", "Interruption risk"), T("horas sem luz", "hours without power")),
            (T("Resiliência", "Resilience"), T("Dimensionamento", "Sizing")), (T("Folha de cálculo", "Spreadsheet"), "Excel")]
    chips = "".join(f'<span class="chip">{a} → <b>{b}</b></span>' for a, b in maps)
    _slide(f"3 · {_title(2)}", f"""
<h2>{T("Como calculamos a energia renovável, em 5 passos", "How we calculate the renewable energy, in 5 steps")}</h2>
<div class="method">{"".join(cards)}</div>
<div style="margin-top:14px;font-size:14px;color:#6B7280;font-weight:700;letter-spacing:.06em;text-transform:uppercase">{T("Onde está cada pedido do desafio", "Where each challenge requirement is")}</div>
<div style="margin-top:6px">{chips}</div>""")


def s_balanco(d):
    e, r, seq = d["e"], d["r"], d["seq"]
    labels = [T("Sol forte", "Strong sun"), T("Algumas nuvens", "Some clouds"), T("Nublado e chuva", "Cloudy and rain"),
              T("Chuva forte", "Heavy rain")]
    _slide(f"4 · {_title(3)}", f'<h2>{T("Quatro dias reais seguidos: do sol forte à chuva forte", "Four real days in a row: from strong sun to heavy rain")}</h2>'
           f'<div class="lead" style="font-size:16px">{T("O mesmo tempo para os dois sistemas. A bateria passa de um dia para o outro: siga a linha da bateria em baixo.", "The same weather for both systems. The battery carries over from one day to the next: follow the battery line at the bottom.")}</div>',
           cls="slide compact")
    oe, orr = seq["e"], seq["r"]
    fig = charts.sequence([(f"{T('Só eficiência', 'Efficiency only')} · {_sys(e)}", oe),
                           (f"{T('Resiliente', 'Resilient')} · {_sys(r)}", orr)], labels, d["seq_sun"], height=660)
    st.plotly_chart(fig, width="stretch")

    def day(o, k):
        od = o.iloc[24 * k:24 * (k + 1)]
        return int((od["unmet"] > 0.01 * od["demand"]).sum()), 100 * od["soc"].max(), 100 * od["soc"].iloc[-1]
    h3e, max3e, _ = day(oe, 2)
    h4e, _, _ = day(oe, 3)
    h4r, _, end4r = day(orr, 3)
    st.markdown(f'<div class="plain" style="font-size:15.5px;margin-top:4px"><div class="h">{T("Como ler", "How to read it")}</div>' + T(
        f"<b>Dias 1 e 2 · sol:</b> os painéis enchem a bateria dos dois sistemas (a linha sobe até 100 %). "
        f"<b>Dia 3 · nuvens e chuva:</b> o sistema pequeno já não enche a bateria (só chega a {num(max3e)} %) e à noite fica "
        f"{h3e} h sem luz. <b>Dia 4 · chuva forte:</b> o sistema pequeno fica <b>{h4e} horas às escuras</b>. O resiliente usa a "
        f"reserva que guardou nos dias de sol e <b>não corta nenhuma hora</b> (a bateria acaba o dia em {num(end4r)} %).",
        f"<b>Days 1 and 2 · sun:</b> the panels fill both batteries (the line rises to 100 %). "
        f"<b>Day 3 · clouds and rain:</b> the small system no longer fills its battery (only {num(max3e)} %) and at night loses "
        f"power for {h3e} h. <b>Day 4 · heavy rain:</b> the small system is <b>dark for {h4e} hours</b>. The resilient one uses the "
        f"reserve it stored on the sunny days and <b>does not cut a single hour</b> (the battery ends the day at {num(end4r)} %).")
        + "</div>", unsafe_allow_html=True)


def s_resiliente(d):
    e, r = d["e"], d["r"]
    cells = ""
    for k in M.DAY_TYPES:
        a, b = d["test"]["e"][k], d["test"]["r"][k]
        cells += (f'<div class="k"><div class="u"><b>{day_label(k)}</b></div>'
                  f'<div class="u" style="color:{hcol(a)};font-weight:700">{T("Só eficiência", "Efficiency")}: {cut_txt(a["hours"])}</div>'
                  f'<div class="u" style="color:{hcol(b)};font-weight:800">{T("Resiliente", "Resilient")}: {cut_txt(b["hours"])}</div></div>')
    _slide(f"5 · {_title(4)}", f"""
<h2>{T(f"O nosso sistema foi resiliente em <span class='red'>{num(r['ok_days'], 1)} % dos dias</span> reais.",
       f"Our system was resilient on <span class='red'>{num(r['ok_days'], 1)} % of the</span> real days.")}</h2>
<div class="lead" style="font-size:17px">{T(
 f"Em {num(r['ok_days'], 1)} % dos dias, a aldeia teve luz <b>o dia inteiro, sem nenhum corte</b>. O sistema «só eficiência» "
 f"conseguiu-o em {num(e['ok_days'], 1)} % dos dias.",
 f"On {num(r['ok_days'], 1)} % of days, the village had power <b>all day, with no cuts at all</b>. The efficiency-only system "
 f"managed it on {num(e['ok_days'], 1)} % of days.")}</div>
<div class="big">
  <div class="k"><div class="n red">{num(e['cut_days'])} → {num(r['cut_days'])}</div><div class="u">{T("dias por ano com algum corte",
   "days per year with any cut")}</div></div>
  <div class="k"><div class="n red">{num(e['hours'])} h → {num(r['hours'])} h</div><div class="u">{T("horas sem luz por ano",
   "hours without power per year")}</div></div>
  <div class="k"><div class="n">{num(e['autonomy'])} h → {num(r['autonomy'])} h</div><div class="u">{T("autonomia da bateria sem sol",
   "battery autonomy without sun")}</div></div>
  <div class="k"><div class="n">+{num(100 * (r['cost'] / e['cost'] - 1))} %</div><div class="u">{T(
   f"de investimento ({num(e['cost'] / 1000)} → {num(r['cost'] / 1000)} mil USD): o mais barato que cumpre",
   f"investment ({num(e['cost'] / 1000)} → {num(r['cost'] / 1000)}k USD): the cheapest that meets the target")}</div></div>
</div>
<div class="lead" style="font-size:16px"><b>{T("Só eficiência", "Efficiency only")}:</b> {_sys(e)} &nbsp;·&nbsp;
<b class="red">{T("Resiliente", "Resilient")}:</b> {_sys(r)}</div>
<div style="font-size:18px;font-weight:800;margin:16px 0 4px 0">{T("Teste de 24 horas: a aldeia ficou sem luz em algum momento do dia?",
 "24-hour test: did the village lose power at any point in the day?")}</div>
<div class="big" style="grid-template-columns:repeat(5,1fr);margin-top:6px">{cells}</div>""")


def s_conclusao(d):
    _slide(f"6 · {_title(5)}", f"""
<h2>{T("Uma ferramenta simples que diz que sistema instalar para a aldeia não ficar às escuras.",
       "A simple tool that tells you which system to install so the village does not go dark.")}</h2>
<div class="ideas" style="grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px">
 {_idea("check", T("O que entregamos", "What we deliver"), T(
   "Simulador de 24 h com dados reais, risco de interrupção, e dimensionamento testado em dias reais.",
   "24-hour simulator with real data, interruption risk, and sizing tested on real days."))}
 {_idea("shield", T("Resultado", "Result"), T(
   f"Com +{num(100 * (d['r']['cost'] / d['e']['cost'] - 1))} % de investimento, os dias maus passam de {num(d['e']['bad_days'])} para {num(d['r']['bad_days'], 1)} por ano.",
   f"With +{num(100 * (d['r']['cost'] / d['e']['cost'] - 1))} % investment, bad days fall from {num(d['e']['bad_days'])} to {num(d['r']['bad_days'], 1)} a year."))}
 {_idea("leaf", T("100 % renovável", "100 % renewable"), T(
   f"Evita {num(d['imp']['diesel_l'] / 1000, 1)} mil litros de gasóleo e {num(d['imp']['co2_t'])} t de CO₂ por ano. Energia a {num(d['imp']['lcoe'], 2)} USD/kWh.",
   f"Avoids {num(d['imp']['diesel_l'] / 1000, 1)}k litres of diesel and {num(d['imp']['co2_t'])} t of CO₂ a year. Energy at {num(d['imp']['lcoe'], 2)} USD/kWh."))}
 {_idea("users", T("Sustentabilidade e replicação", "Sustainability and replication"), T(
   "Gratuita e de código aberto. Serve qualquer aldeia: basta o sol hora a hora e o número de famílias.",
   "Free and open source. Works for any village: it only needs hourly sun and the number of households."))}
 {_idea("signal", T("Próximo passo", "Next step"), T(
   "Piloto numa aldeia de Mabote: medir a procura real e confirmar o dimensionamento no terreno.",
   "Pilot in a Mabote village: measure real demand and confirm the sizing in the field."))}
</div>
<div style="font-size:30px;font-weight:800;margin-top:22px;color:#1F2933">{T(
 'Energia solar que <span class="red">não falha nos dias maus.</span>', 'Solar power that <span class="red">does not fail on bad days.</span>')}</div>
<div class="lead" style="font-size:15px;margin-top:8px">{T("Grupo 36", "Team 36")} · Ezequias Miocha · Laura Hele · Suely Muando · Universidade Eduardo Mondlane</div>""")


RENDER = dict(contexto=s_contexto, objectivo=s_objectivo, metodo=s_metodo, balanco=s_balanco, resiliente=s_resiliente,
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
