"""Energia solar: como funciona o sistema renovável da aldeia, explicado de forma simples."""
import streamlit as st

from resilia import model as M
from ui import charts
from ui.i18n import T, num
from ui.icons import icon
from ui.style import C, page_header

from .panel import get_year

GREEN = "#16A34A"


def _step(ic, bg, fg, k, v, x):
    return (f'<div class="st"><div class="badge" style="background:{bg}">{icon(ic, 28, fg, 2)}</div>'
            f'<div class="k">{k}</div><div class="v">{v}</div><div class="x">{x}</div></div>')


def _eco(ic, t, v, s):
    return f'<div class="e"><div class="t">{icon(ic, 18, GREEN, 2.2)}{t}</div><div class="v">{v}</div><div class="s">{s}</div></div>'


def render(ctx):
    s, res, dem, vil = ctx.system, ctx.res, ctx.dem, ctx.village
    page_header(T("Energia renovável", "Renewable energy"),
                T("Como a aldeia vive da energia do sol", "How the village runs on solar energy"),
                T("Uma visão simples do sistema: de onde vem a energia, onde é guardada, para onde vai e o que se ganha "
                  "face a um gerador a gasóleo. Os números mudam com o painel à esquerda.",
                  "A simple view of the system: where the energy comes from, where it is stored, where it goes and what is "
                  "gained compared with a diesel generator. The numbers follow the left panel."))

    if s.pv <= 0:
        st.info(T("Escolha uma potência de painéis solares maior que zero no painel à esquerda.",
                  "Choose a solar panel size above zero in the left panel."))
        return

    n_days = len(res) / 24
    sun_day = res["ghi"].sum() / 1000 / n_days
    dem_day = dem["total"].sum() / n_days
    f, imp = get_year(vil, float(s.pv), float(s.bat))
    pv_day = f["pv"] / 365.25
    autonomy = (1 - M.SOC_MIN) * s.bat * M.ETA / max(dem["total"].mean(), 1e-9)

    # ── 1. o caminho da energia ──
    st.markdown(f"### {T('O caminho da energia, em 4 passos', 'The path of energy, in 4 steps')}")
    arrow = f'<div class="ar">{icon("up", 26, "#C3C8D0", 2.2).replace("<svg", "<svg style=transform:rotate(90deg)")}</div>'
    st.markdown('<div class="flow">' + arrow.join([
        _step("sun", "#FFF4CC", "#B07A00", T("1 · O sol", "1 · The sun"), f"{num(sun_day, 1)} kWh/m²",
              T("de luz solar por dia, em média, em Mabote. É energia limpa e gratuita, todos os dias.",
                "of sunlight per day, on average, in Mabote. Clean, free energy, every day.")),
        _step("panel", "#FFF4CC", "#B07A00", T("2 · Os painéis", "2 · The panels"), f"{num(imp['panels'])} {T('painéis', 'panels')}",
              T(f"de {M.PANEL_W} W ({num(s.pv)} kWp), cerca de {num(round(imp['area'], -1))} m². Produzem {num(pv_day)} kWh por dia.",
                f"of {M.PANEL_W} W ({num(s.pv)} kWp), about {num(round(imp['area'], -1))} m². They produce {num(pv_day)} kWh per day.")),
        _step("battery", "#E5EDFF", C["bat"], T("3 · A bateria", "3 · The battery"), f"{num(s.bat)} kWh",
              T(f"guarda a energia do dia para a noite. Sozinha, aguenta cerca de {num(autonomy)} horas sem sol.",
                f"stores the day's energy for the night. On its own, it lasts about {num(autonomy)} hours without sun.")),
        _step("house", "#FDECEF", C["red"], T("4 · A aldeia", "4 · The village"), f"{num(dem_day)} kWh/{T('dia', 'day')}",
              T(f"usadas por {vil[0]} famílias e pelos serviços: luz, telemóveis, frio para vacinas, água e moagem.",
                f"used by {vil[0]} households and services: lights, phones, vaccine cooling, water and milling.")),
    ]) + "</div>", unsafe_allow_html=True)

    # ── 2. energia limpa ──
    st.markdown(f"### {T('O que a energia solar traz', 'What solar energy brings')}")
    fuel_kwh = M.DIESEL_L_KWH * M.DIESEL_USD_L
    st.markdown('<div class="eco">' + "".join([
        _eco("leaf", T("Renovável", "Renewable"), "100 %",
             T("da energia vem do sol. Zero combustível, zero fumo, zero ruído.",
               "of the energy comes from the sun. Zero fuel, zero smoke, zero noise.")),
        _eco("sun", T("Energia limpa", "Clean energy"), f"{num(f['served'] / 1000)} MWh",
             T(f"entregues à aldeia por ano ({num(100 * f['served'] / f['demand'], 1)} % do que a aldeia pede).",
               f"delivered to the village per year ({num(100 * f['served'] / f['demand'], 1)} % of what it asks for).")),
        _eco("fuel", T("Gasóleo evitado", "Diesel avoided"), f"{num(imp['diesel_l'] / 1000, 1)} {T('mil litros', 'k litres')}",
             T(f"por ano, face a um gerador. São cerca de {num(imp['diesel_usd'] / 1000)} mil USD de combustível por ano.",
               f"per year, compared with a generator. About {num(imp['diesel_usd'] / 1000)}k USD of fuel per year.")),
        _eco("globe", T("CO₂ evitado", "CO₂ avoided"), f"{num(imp['co2_t'])} t/{T('ano', 'yr')}",
             T(f"{num(imp['co2_life_t'])} toneladas em {M.LIFE} anos de vida do sistema.",
               f"{num(imp['co2_life_t'])} tonnes over the system's {M.LIFE}-year life.")),
        _eco("coin", T("Custo da energia", "Energy cost"), f"{num(imp['lcoe'], 2)} USD/kWh",
             T(f"em {M.LIFE} anos, com manutenção e troca de baterias. Só o combustível de um gerador custa {num(fuel_kwh, 2)} USD/kWh.",
               f"over {M.LIFE} years, including maintenance and battery replacement. Generator fuel alone costs {num(fuel_kwh, 2)} USD/kWh.")),
    ]) + "</div>", unsafe_allow_html=True)

    # ── 3. para onde vai a energia ──
    st.markdown(f"### {T('Para onde vai a energia do sol, num ano', 'Where the solar energy goes, in a year')}")
    a, b = st.columns([3, 2], gap="large")
    with a:
        st.plotly_chart(charts.energy_flow(f), width="stretch")
    with b:
        pct = lambda x: 100 * x / max(f["pv"], 1e-9)
        rows = [
            (C["solar"], pct(f["direct"]), T("vai <b>directamente</b> para a aldeia, durante o dia.",
                                             "goes <b>straight</b> to the village, during the day.")),
            (C["bat"], pct(f["bat_in"]), T("é <b>guardada na bateria</b> e usada à noite e nas horas sem sol.",
                                           "is <b>stored in the battery</b> and used at night and when there is no sun.")),
            ("#C9A227", pct(f["curt"]), T("é <b>excedente livre</b>: a bateria já está cheia. Pode alimentar novos usos de dia "
                                          "(frio, moagem, rega, carregar telemóveis).",
                                          "is <b>free surplus</b>: the battery is already full. It can power new daytime uses "
                                          "(cooling, milling, irrigation, phone charging).")),
            ("#9CA3AF", pct(f["bat_loss"]), T("perde-se na carga e descarga da bateria.", "is lost charging and discharging the battery.")),
        ]
        st.markdown('<div class="shares">' + "".join(
            f'<div class="r"><div class="p" style="color:{c}">{num(p)} %</div><div class="x">{x}</div></div>' for c, p, x in rows)
            + "</div>", unsafe_allow_html=True)

    # ── 4. ao longo do ano ──
    st.markdown(f"### {T('O sol ao longo do ano', 'The sun through the year')}")
    m = f["monthly"]
    low = int(m["pv"].idxmin())
    months = T("Janeiro Fevereiro Março Abril Maio Junho Julho Agosto Setembro Outubro Novembro Dezembro",
               "January February March April May June July August September October November December").split()
    l, r = st.columns([3, 2], gap="large")
    with l:
        st.plotly_chart(charts.monthly(m, None), width="stretch")
    with r:
        st.markdown(f'<div class="plain"><div class="h">{T("Em palavras simples", "In plain words")}</div>' + T(
            f"Os painéis produzem mais do que a aldeia usa em todos os meses. O mês mais fraco é <b>{months[low - 1]}</b> "
            f"(inverno), com {num(m['pv'].min())} kWh por dia. Mas a média esconde os <b>dias maus</b>: nuvens e chuva "
            "podem cortar a produção para menos de metade. É por isso que o sistema é dimensionado para aguentar esses dias, "
            "e não só o dia médio.",
            f"The panels produce more than the village uses in every month. The weakest month is <b>{months[low - 1]}</b> "
            f"(winter), with {num(m['pv'].min())} kWh per day. But the average hides the <b>bad days</b>: clouds and rain "
            "can cut output to less than half. That is why the system is sized to withstand those days, not just the "
            "average day.") + "</div>", unsafe_allow_html=True)

    # ── 5. palavras simples ──
    st.markdown(f"### {T('Palavras-chave, sem complicações', 'Key words, made simple')}")
    words = [
        ("kWp", T("A potência dos painéis quando o sol está forte. 1 kWp ≈ 2 painéis de 550 W.",
                  "Panel power in full sun. 1 kWp ≈ 2 panels of 550 W.")),
        ("kWh", T("Uma quantidade de energia. Uma lâmpada LED de 10 W acesa 100 horas gasta 1 kWh.",
                  "An amount of energy. A 10 W LED bulb on for 100 hours uses 1 kWh.")),
        (T("Autonomia", "Autonomy"), T("Quantas horas a bateria aguenta a aldeia sozinha, sem sol.",
                                       "How many hours the battery can run the village alone, without sun.")),
        (T("Energia em falta", "Energy missing"), T("A energia que a aldeia pediu e o sistema não conseguiu dar: é a interrupção.",
                                                    "Energy the village asked for that the system could not deliver: the interruption.")),
        (T("Eficiente", "Efficient"), T("Não gasta mais dinheiro nem desperdiça mais energia do que o necessário.",
                                        "Does not spend more money or waste more energy than needed.")),
        (T("Resiliente", "Resilient"), T("Continua a dar energia nos dias maus: nublados, de chuva forte ou de muito calor.",
                                         "Keeps supplying power on bad days: cloudy, heavy rain or very hot.")),
    ]
    st.markdown('<div class="gloss">' + "".join(f'<div class="g"><div class="w">{w}</div><div class="d">{d}</div></div>'
                                                for w, d in words) + "</div>", unsafe_allow_html=True)

    st.markdown(f'<div class="goldbox" style="margin-top:18px"><b>{T("Porque só solar?", "Why solar only?")}</b> ' + T(
        f"Em Mabote o sol é forte quase todo o ano, enquanto o vento médio é de apenas {num(res['v'].mean(), 1)} m/s, "
        "fraco para um aerogerador. Por isso o sistema usa painéis solares e bateria. O vento conta apenas porque "
        "arrefece os painéis, o que ajuda a produzir um pouco mais.",
        f"In Mabote the sun is strong almost all year, while mean wind is only {num(res['v'].mean(), 1)} m/s, too weak "
        "for a wind turbine. So the system uses solar panels and a battery. Wind only counts because it cools the "
        "panels, which helps them produce a little more.") + "</div>", unsafe_allow_html=True)
    with st.expander(T("Pressupostos destes números", "Assumptions behind these numbers"), icon=":material/info:"):
        st.markdown(T(
            f"- Médias de 11 anos reais (2015–2025), hora a hora.\n"
            f"- Gerador a gasóleo: {num(M.DIESEL_L_KWH, 2)} l/kWh, {num(M.CO2_KG_L, 2)} kg de CO₂ por litro, gasóleo a {num(M.DIESEL_USD_L, 2)} USD/l.\n"
            f"- Custo da energia: investimento + uma troca de baterias + manutenção de {num(100 * M.OM, 1)} % por ano, a dividir pela energia entregue em {M.LIFE} anos (sem juros).\n"
            f"- Painel de {M.PANEL_W} W com cerca de {num(M.PANEL_M2, 1)} m².",
            f"- Averages over 11 real years (2015–2025), hour by hour.\n"
            f"- Diesel generator: {num(M.DIESEL_L_KWH, 2)} l/kWh, {num(M.CO2_KG_L, 2)} kg CO₂ per litre, diesel at {num(M.DIESEL_USD_L, 2)} USD/l.\n"
            f"- Energy cost: investment + one battery replacement + {num(100 * M.OM, 1)} % maintenance per year, divided by energy delivered over {M.LIFE} years (no interest).\n"
            f"- {M.PANEL_W} W panel of about {num(M.PANEL_M2, 1)} m²."))
