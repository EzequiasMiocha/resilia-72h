"""Metodologia: como a plataforma calcula a energia renovável, passo a passo."""
import pandas as pd
import streamlit as st

from resilia import model as M
from ui.i18n import T, num
from ui.icons import icon
from ui.style import page_header


def _step(n, ic, title, text):
    st.markdown(f'<div class="mstep"><span class="no">{n}</span>{icon(ic, 24, "#C8102E", 2)}<span class="t">{title}</span></div>'
                f'<div class="mtext">{text}</div>', unsafe_allow_html=True)


def _params(rows):
    st.table(pd.DataFrame(rows, columns=[T("Parâmetro", "Parameter"), T("Valor", "Value"), T("Porquê", "Why")])
             .set_index(T("Parâmetro", "Parameter")))


def render():
    page_header(T("Metodologia", "Methodology"),
                T("Como calculamos a energia renovável", "How we calculate the renewable energy"),
                T("O modelo segue a cadeia de uma mini-rede solar: o sol que chega, a electricidade que os painéis produzem, "
                  "o que a aldeia consome, o que a bateria guarda e, por fim, que sistema escolher. Tudo hora a hora, com "
                  "dados reais de Mabote.",
                  "The model follows the chain of a solar mini-grid: the sunlight that arrives, the electricity the panels "
                  "produce, what the village consumes, what the battery stores and, finally, which system to choose. All hour "
                  "by hour, with real Mabote data."))

    # 1 · recurso solar
    _step(1, "sun", T("Recurso solar", "Solar resource"), T(
        "Usamos a radiação solar real de Mabote (22,05° S; 34,13° E), hora a hora, da reanálise <b>ERA5</b> do programa "
        "europeu Copernicus (ECMWF): radiação global, directa e difusa, temperatura do ar e vento. Os painéis estão "
        "inclinados a 22° e virados a norte (no hemisfério sul, é a orientação que capta mais sol ao longo do ano). "
        "A radiação no plano do painel soma três partes: o sol directo, o céu difuso e o reflexo do chão.",
        "We use real hourly solar radiation for Mabote (22.05° S; 34.13° E) from the Copernicus <b>ERA5</b> reanalysis "
        "(ECMWF): global, direct and diffuse radiation, air temperature and wind. Panels are tilted 22° and face north "
        "(in the southern hemisphere this captures the most sun over the year). Radiation on the panel plane adds three "
        "parts: direct sun, diffuse sky and ground reflection."))
    st.latex(r"G_{painel} = DNI\cdot\cos\theta \;+\; DHI\cdot\frac{1+\cos\beta}{2} \;+\; GHI\cdot\rho\cdot\frac{1-\cos\beta}{2}")
    st.caption(T("θ = ângulo entre o sol e o painel · β = inclinação (22°) · ρ = reflexo do chão (0,2) · modelo de céu isotrópico.",
                 "θ = angle between sun and panel · β = tilt (22°) · ρ = ground reflectance (0.2) · isotropic sky model."))

    # 2 · produção fotovoltaica
    _step(2, "panel", T("Produção dos painéis solares", "Solar panel output"), T(
        "A potência produzida é proporcional ao sol no painel. Dois efeitos reduzem-na: as <b>perdas</b> do sistema "
        "(cabos, inversor, poeira) e o <b>calor</b>: cada grau acima de 25 °C na célula tira 0,35 % de produção. O vento "
        "arrefece os painéis, por isso entra na temperatura da célula.",
        "Output is proportional to the sun on the panel. Two effects reduce it: system <b>losses</b> (cables, inverter, "
        "dust) and <b>heat</b>: each degree above 25 °C in the cell removes 0.35 % of output. Wind cools the panels, so it "
        "enters the cell temperature."))
    st.latex(r"P_{FV} = P_{kWp}\cdot\frac{G_{painel}}{1000}\cdot PR\cdot\big[1+\gamma\,(T_c-25)\big]"
             r"\qquad T_c = T_a + \frac{NOCT-20}{800}\,G_{painel}\cdot\frac{9{,}5}{5{,}7+3{,}8\,v}")
    _params([
        (T("Perdas do sistema (PR)", "Performance ratio (PR)"), "0,88", T("cabos, inversor e sujidade", "cables, inverter and soiling")),
        (T("Efeito da temperatura (γ)", "Temperature coefficient (γ)"), "−0,35 %/°C", T("painéis de silício típicos", "typical silicon panels")),
        ("NOCT", "45 °C", T("temperatura nominal da célula", "nominal cell temperature")),
        (T("Inclinação e orientação", "Tilt and orientation"), T("22°, norte", "22°, north"), T("perto da latitude de Mabote", "close to Mabote's latitude")),
    ])

    # 3 · procura
    _step(3, "house", T("Procura da aldeia", "Village demand"), T(
        "A procura é construída a partir do <b>número de famílias</b> e dos serviços, como num levantamento de cargas. "
        "Cada família consome cerca de 0,3 kWh por dia (luz, telemóvel, rádio, ventoinha), com ponta ao fim da tarde. "
        "Os serviços têm horários próprios: o centro de saúde funciona 24 horas (cerca de 15 kWh/dia, com frio para "
        "vacinas), a escola nos dias úteis, a bomba de água de manhã e à tarde, e a moagem em três horas por dia. "
        "Nos dias de calor (acima de 30 °C) as ventoinhas aumentam o consumo. Uma variação natural de ±8 % de dia "
        "para dia e ±4 % de hora para hora torna a procura realista.",
        "Demand is built from the <b>number of households</b> and services, as in a load survey. Each household uses "
        "about 0.3 kWh per day (lights, phone, radio, fan), peaking in the evening. Services have their own hours: the "
        "health centre runs 24 hours (about 15 kWh/day, including vaccine cooling), the school on weekdays, the water pump "
        "in the morning and afternoon, and the mill three hours a day. On hot days (above 30 °C) fans increase use. A "
        "natural variation of ±8 % day to day and ±4 % hour to hour makes demand realistic."))

    # 4 · bateria e balanço
    _step(4, "battery", T("Bateria e balanço de cada hora", "Battery and hourly balance"), T(
        "Em cada hora, a energia segue sempre a mesma ordem: (1) o sol serve a aldeia directamente; (2) o que sobra "
        "carrega a bateria; (3) o que falta sai da bateria; (4) se a bateria chegar ao mínimo, o resto é <b>energia em "
        "falta</b>, ou seja, horas sem luz. A carga da bateria passa de uma hora para a seguinte e de um dia para o "
        "seguinte: é por isso que os dias de sol protegem os dias de chuva.",
        "Every hour, energy follows the same order: (1) the sun serves the village directly; (2) the surplus charges the "
        "battery; (3) shortfalls are drawn from the battery; (4) if the battery reaches its minimum, the rest is <b>energy "
        "missing</b>, i.e. hours without power. Battery charge carries over from hour to hour and from day to day: that is "
        "why sunny days protect rainy days."))
    st.latex(r"E_{t+1} = E_t + \eta\,P_{carga} - \frac{P_{descarga}}{\eta}\qquad 20\,\%\cdot C \le E_t \le C")
    _params([
        (T("Tipo de bateria", "Battery type"), T("lítio-ferro-fosfato (LFP)", "lithium iron phosphate (LFP)"), T("longa vida e segura", "long life and safe")),
        (T("Eficiência de carga e descarga (η)", "Charge and discharge efficiency (η)"), "95 %", T("valor típico de LFP", "typical LFP value")),
        (T("Carga mínima", "Minimum charge"), "20 %", T("protege a vida útil", "protects battery life")),
        (T("Potência máxima", "Maximum power"), T("0,5 × capacidade", "0.5 × capacity"), T("limite de carga/descarga (0,5C)", "charge/discharge limit (0.5C)")),
    ])

    # 5 · dimensionamento
    _step(5, "shield", T("Dimensionamento resiliente", "Resilient sizing"), T(
        f"Testamos <b>{M.N_SYSTEMS} combinações</b> de painéis (30 a 90 kWp) e baterias (80 a 500 kWh) em milhares de dias "
        "reais seguidos de Mabote, com a bateria a passar de um dia para o outro. A escolha é <b>hierárquica</b>: primeiro "
        "a resiliência é obrigatória (no máximo 0,5 % de energia em falta, 3 dias maus por ano e pelo menos 12 horas de "
        "autonomia); entre os sistemas que cumprem, escolhe-se o <b>mais barato</b>. O sistema «só eficiência» é o mais "
        "barato que serve o dia médio (até 5 % de energia em falta), sem exigência para os dias maus.",
        f"We test <b>{M.N_SYSTEMS} combinations</b> of panels (30 to 90 kWp) and batteries (80 to 500 kWh) on thousands of "
        "real consecutive Mabote days, with the battery carrying over from day to day. The choice is <b>hierarchical</b>: "
        "first resilience is required (at most 0.5 % energy missing, 3 bad days per year and at least 12 hours of "
        "autonomy); among the systems that comply, the <b>cheapest</b> is chosen. The efficiency-only system is the cheapest "
        "that serves the average day (up to 5 % energy missing), with no requirement for bad days."))

    # indicadores
    st.markdown(f"### {T('Indicadores: como medimos a resiliência e a eficiência', 'Indicators: how we measure resilience and efficiency')}")
    ind = [
        (T("Dias resilientes", "Resilient days"), T("% de dias em que a aldeia teve luz o dia inteiro, sem nenhum corte", "% of days with power all day, no cuts")),
        (T("Horas sem luz", "Hours without power"), T("horas em que faltou mais de 1 % da procura", "hours in which more than 1 % of demand was missing")),
        (T("Energia em falta", "Energy missing"), T("energia não servida ÷ procura total (LPSP)", "unserved energy ÷ total demand (LPSP)")),
        (T("Dias maus", "Bad days"), T("dias com mais de 10 % da energia em falta", "days with more than 10 % of energy missing")),
        (T("Autonomia", "Autonomy"), T("horas que a bateria aguenta a aldeia sozinha: 80 % × capacidade × 95 % ÷ procura média",
                                      "hours the battery alone can run the village: 80 % × capacity × 95 % ÷ average demand")),
        (T("Excedente solar", "Solar surplus"), T("energia solar que não cabe na bateria cheia ÷ produção total", "solar energy that does not fit in the full battery ÷ total output")),
        (T("Custo da energia", "Energy cost"), T(f"(investimento + troca de baterias + manutenção {num(100 * M.OM, 1)} %/ano) ÷ energia entregue em {M.LIFE} anos",
                                                f"(investment + battery replacement + {num(100 * M.OM, 1)} %/yr maintenance) ÷ energy delivered over {M.LIFE} years")),
        (T("CO₂ evitado", "CO₂ avoided"), T(f"energia entregue × {num(M.DIESEL_L_KWH, 2)} l de gasóleo/kWh × {num(M.CO2_KG_L, 2)} kg CO₂/l",
                                           f"energy delivered × {num(M.DIESEL_L_KWH, 2)} l diesel/kWh × {num(M.CO2_KG_L, 2)} kg CO₂/l")),
    ]
    st.table(pd.DataFrame(ind, columns=[T("Indicador", "Indicator"), T("Como se calcula", "How it is calculated")])
             .set_index(T("Indicador", "Indicator")))

    with st.expander(T("Limites do modelo (o que ainda queremos confirmar)", "Model limits (what we still want to confirm)"),
                     icon=":material/info:"):
        st.markdown(T(
            "- A radiação vem de uma reanálise (satélite e modelo), não de um medidor no local. Mede bem a variação de dia "
            "para dia, mas pode diferir alguns por cento de uma medição local.\n"
            "- A procura é uma estimativa típica de aldeias rurais. O piloto deve medi-la no terreno.\n"
            "- Não incluímos a perda lenta de rendimento dos painéis com a idade nem o envelhecimento da bateria "
            "(entram no custo como uma troca de baterias a meio da vida).\n"
            "- Os custos são valores indicativos de mini-redes em África e o custo da energia não inclui juros.",
            "- Radiation comes from a reanalysis (satellite and model), not an on-site meter. It captures day-to-day "
            "variation well but may differ by a few percent from a local measurement.\n"
            "- Demand is a typical estimate for rural villages. The pilot should measure it in the field.\n"
            "- We do not include the slow loss of panel output with age or battery ageing (the cost includes one battery "
            "replacement mid-life).\n"
            "- Costs are indicative African mini-grid values and the energy cost excludes interest."))
