"""Negócio: modelo de negócio, sustentabilidade e visão de futuro (bilingue)."""
import plotly.graph_objects as go
import streamlit as st

from resilia.economics import capex, crf, lcoe, voll_cost
from resilia.engine import CONVENTIONAL, metrics, simulate
from resilia.physics import System
from resilia.sites import COSTS, VOLL
from ui import charts
from ui.i18n import T, num
from ui.style import C, card, chain, explain, page_header

CAPEX_EN = {"Solar fotovoltaico": "Solar PV", "Baterias LFP": "LFP batteries", "Inversor/carregador": "Inverter/charger",
            "Aerogerador": "Wind turbine", "Gerador de reserva": "Backup generator",
            "Contentor climatizado": "Climate-controlled enclosure",
            "Controlo inteligente RESILIA": "RESILIA smart control", "Engenharia e logística": "Engineering and logistics"}


@st.cache_data(show_spinner="A simular um ano inteiro (8 760 horas)… / Simulating a full year (8,760 hours)…")
def annual(site_key, hw: tuple, flags: tuple, comm_t: tuple, lead, year=2025):
    from resilia.data import load_site
    from resilia.engine import Strategy
    from resilia.loads import Community
    from resilia.sites import SITES
    df = load_site(site_key)
    w = df[df.index.year == year].copy()
    s = SITES[site_key]
    keys = ["pv_kwp", "bat_kwh", "inv_kw", "wind_kw", "diesel_kw", "fuel_l"]
    hwd = dict(zip(keys, hw))
    comm = Community(*comm_t)
    sc = System(**hwd)
    sr = System(**hwd, pv_hardened=flags[0], bat_climate=flags[1])
    oc = simulate(w, s, sc, comm, CONVENTIONAL, fuel_resupply=True)
    orr = simulate(w, s, sr, comm, Strategy(True, lead, flags[2], "RESILIA"), fuel_resupply=True)
    return metrics(oc), metrics(orr)


def render(ctx):
    s = ctx.site
    page_header(T("Negócio", "Business"),
                T("Um projecto que se paga e que pode ser financiado", "A project that pays its way and can be financed"),
                T("Simulamos um ano inteiro real (2025, 8 760 horas) do sistema configurado no painel à esquerda e calculamos "
                  "investimento, custo da energia, receitas e o valor das falhas evitadas.",
                  "We simulate a full real year (2025, 8,760 hours) of the system configured in the left panel and calculate "
                  "investment, cost of energy, revenue and the value of avoided outages."))
    with st.expander(T("Pressupostos económicos (editáveis)", "Economic assumptions (editable)"), icon=":material/settings:"):
        c1, c2, c3, c4 = st.columns(4)
        costs = dict(COSTS)
        with c1:
            costs["pv_usd_kwp"] = st.number_input(T("Solar instalado (USD/kWp)", "Installed solar (USD/kWp)"), 300.0, 2000.0,
                                                  COSTS["pv_usd_kwp"], 50.0, key="b_pv")
            costs["bat_usd_kwh"] = st.number_input(T("Bateria LFP instalada (USD/kWh)", "Installed LFP battery (USD/kWh)"),
                                                   100.0, 1000.0, COSTS["bat_usd_kwh"], 10.0, key="b_bat")
        with c2:
            diesel = st.number_input(T("Gasóleo (USD/L)", "Diesel (USD/L)"), 0.5, 3.0, s["diesel_usd_l"], 0.05, key="b_dsl")
            tariff = st.number_input(T("Tarifa média (USD/kWh)", "Average tariff (USD/kWh)"), 0.05, 1.0, s["tariff_usd_kwh"],
                                     0.01, key="b_tar")
        with c3:
            costs["discount"] = st.number_input(T("Taxa de desconto", "Discount rate"), 0.02, 0.25, COSTS["discount"], 0.01,
                                                key="b_disc")
            costs["smart_usd_household"] = st.number_input(T("Contador inteligente (USD/família)", "Smart meter (USD/household)"),
                                                           10.0, 200.0, COSTS["smart_usd_household"], 5.0, key="b_meter")
        with c4:
            voll = dict(VOLL)
            voll["critica"] = st.number_input(T("Valor da energia crítica não servida (USD/kWh)", "Value of unserved critical energy (USD/kWh)"),
                                              1.0, 50.0, VOLL["critica"], 1.0, key="b_vc")
            voll["essencial"] = st.number_input(T("… essencial (USD/kWh)", "… essential (USD/kWh)"), 0.5, 20.0, VOLL["essencial"],
                                                0.5, key="b_ve")
        st.caption(T("Ordens de grandeza: ESMAP (2022) *Mini Grids for Half a Billion People*; IRENA (2024) *Renewable Power "
                     "Generation Costs*; BNEF (2024) *Battery Price Survey*. O valor da energia não servida é um pressuposto "
                     "explícito (custo social de uma hora sem clínica, água ou luz).",
                     "Orders of magnitude: ESMAP (2022) *Mini Grids for Half a Billion People*; IRENA (2024) *Renewable Power "
                     "Generation Costs*; BNEF (2024) *Battery Price Survey*. The value of unserved energy is an explicit "
                     "assumption (social cost of an hour without clinic, water or light)."))

    hw = tuple(ctx.hw[k] for k in ["pv_kwp", "bat_kwh", "inv_kw", "wind_kw", "diesel_kw", "fuel_l"])
    c = ctx.comm
    comm_t = (c.households, c.people, c.health, c.school, c.mill, c.commerce, c.water_head_m, c.heat_sens, c.cold_sens)
    flags = (ctx.flags["hard"], ctx.flags["clim"], ctx.flags["maint"])
    ac, ar = annual(ctx.site_key, hw, flags, comm_t, ctx.lead)

    items = capex(ctx.sys_r, c.households, True, costs)
    cx = sum(items.values())
    served = ar["dem_kwh"] - ar["ens_kwh"]
    ec = lcoe(ctx.sys_r, cx, served, ar["diesel_L"], diesel, costs)
    revenue = tariff * served
    opex = ec["om"] + ec["fuel_cost"]
    margin = revenue - opex
    payback = cx / margin if margin > 0 else float("inf")
    f = crf(costs["discount"], costs["project_life_y"])
    npv = margin / f - cx - ctx.sys_r.bat_kwh * costs["bat_usd_kwh"] * 0.6 / (1 + costs["discount"]) ** 12
    voll_c, voll_r = voll_cost(ac, voll), voll_cost(ar, voll)
    k_ = T("mil", "k")

    st.markdown(f"#### {T('Economia do sistema configurado', 'Economics of the configured system')} "
                f"({ctx.hw['pv_kwp']:.0f} kWp · {ctx.hw['bat_kwh']:.0f} kWh"
                + (f" · {T('gerador', 'generator')} {ctx.hw['diesel_kw']:.0f} kW" if ctx.hw["diesel_kw"] else "")
                + f", {T('ano real de 2025', 'real year 2025')})")
    k = st.columns(5)
    with k[0]:
        card(T("Investimento", "Investment"), f"{num(cx / 1000)} {k_} USD",
             T(f"{num(cx / c.households)} USD por família", f"{num(cx / c.households)} USD per household"), C["prod"])
    with k[1]:
        card(T("Energia servida / ano", "Energy served / year"), f"{num(served / 1000)} MWh",
             T(f"{num(ar['total_pct'], 1)} % da procura", f"{num(ar['total_pct'], 1)} % of demand"), C["solar"])
    with k[2]:
        card(T("Custo da energia", "Cost of energy"), f"{num(ec['lcoe'], 2)} USD", T("por kWh (LCOE, 20 anos)", "per kWh (LCOE, 20 years)"),
             C["accent"])
    with k[3]:
        card(T("Margem operacional", "Operating margin"), f"{num(margin / 1000, 1)} {k_} USD",
             T(f"por ano · receita {num(revenue / 1000, 1)} mil − manutenção e gasóleo {num(opex / 1000, 1)} mil",
               f"per year · revenue {num(revenue / 1000, 1)}k − maintenance and diesel {num(opex / 1000, 1)}k"), C["bat"])
    with k[4]:
        card(T("Retorno simples", "Simple payback"), (f"{num(payback, 1)} {T('anos', 'years')}" if payback < 50 else "> 50"),
             T(f"valor actual líquido a 20 anos: {num(npv / 1000)} mil USD", f"20-year net present value: {num(npv / 1000)}k USD"),
             C["wind"])

    l, r = st.columns(2)
    with l:
        fig = go.Figure(go.Bar(x=list(items.values()), y=[T(x, CAPEX_EN.get(x, x)) for x in items], orientation="h",
                               marker_color=[C["solar"], C["bat"], C["prod"], C["wind"], C["diesel"], C["soc"], C["res"],
                                             "#94A3B8"][:len(items)],
                               text=[f"{num(v / 1000, 1)} {k_}" for v in items.values()], textposition="outside", cliponaxis=False))
        fig.update_layout(xaxis_title="USD", xaxis_range=[0, max(items.values()) * 1.3])
        st.plotly_chart(charts.base(fig, T("Onde vai o investimento", "Where the investment goes"), height=380, legend=False),
                        width="stretch")
    with r:
        fig = go.Figure()
        cats = [T("Crítica (clínica, rádio)", "Critical (clinic, radio)"), T("Casas e escola", "Homes and school"),
                T("Moagem e comércio", "Mill and shops")]
        fig.add_trace(go.Bar(x=cats, y=[ac["ens_crit"], ac["ens_ess"], ac["ens_prod"]], name=T("Sistema de hoje", "Today's system"),
                             marker_color=C["conv"]))
        fig.add_trace(go.Bar(x=cats, y=[ar["ens_crit"], ar["ens_ess"], ar["ens_prod"]], name=T("Com RESILIA", "With RESILIA"),
                             marker_color=C["res"]))
        fig.update_layout(barmode="group", yaxis_title=T("kWh que faltaram em 2025", "kWh not supplied in 2025"))
        st.plotly_chart(charts.base(fig, T("Energia que faltou num ano real, por prioridade", "Energy not supplied in a real year, by priority"),
                                    height=380), width="stretch")
    explain(T("Valor da resiliência:", "Value of resilience:"),
            T(f"no ano real de 2025, com o mesmo equipamento, o centro de saúde ficaria <b>{ac['crit_out_h']} h</b> sem energia "
              f"com a gestão de hoje e <b>{ar['crit_out_h']} h</b> com o RESILIA. O RESILIA prefere pausar a moagem (de forma "
              "planeada e avisada) a apagar a clínica, por isso a barra da moagem sobe e a da clínica desaparece. Ao valor "
              f"social assumido, isso evita <b>{num((voll_c - voll_r) / 1000, 1)} mil USD/ano</b> de danos. A parte inteligente "
              f"custa <b>{num(items.get('Controlo inteligente RESILIA', 0) / 1000, 1)} mil USD</b>, uma única vez.",
              f"in the real year 2025, with the same equipment, the health centre would be without power for "
              f"<b>{ac['crit_out_h']} h</b> under today's operation and <b>{ar['crit_out_h']} h</b> with RESILIA. RESILIA "
              "would rather pause the mill (planned and announced) than switch off the clinic, so the mill bar rises and the "
              f"clinic bar disappears. At the assumed social value, this avoids <b>{num((voll_c - voll_r) / 1000, 1)}k USD/year</b> "
              f"of damage. The smart layer costs <b>{num(items.get('Controlo inteligente RESILIA', 0) / 1000, 1)}k USD</b>, one-off."))

    st.markdown(f"#### {T('Modelo de negócio: resiliência como serviço', 'Business model: resilience as a service')}")
    a, b, cc = st.columns(3)
    with a:
        card(T("Quem paga", "Who pays"), T("5 fontes de receita", "5 revenue streams"),
             T("1. Famílias em pré-pagamento · 2. contratos-âncora: centro de saúde, escola, telecomunicações · 3. uso "
               "produtivo: moagem, frio, carregamento · 4. financiamento climático por resultados (horas de clínica "
               "garantidas) · 5. créditos de carbono pelo gasóleo evitado.",
               "1. Pay-as-you-go households · 2. anchor contracts: health centre, school, telecoms · 3. productive use: "
               "milling, cold storage, charging · 4. results-based climate finance (guaranteed clinic hours) · 5. carbon "
               "credits for avoided diesel."), C["bat"])
    with b:
        card(T("Quem opera", "Who operates"), T("Operador local + RESILIA", "Local operator + RESILIA"),
             T("Uma empresa ou cooperativa local opera a mini-rede e emprega técnicos da aldeia (limpeza de neve e poeira, "
               "manutenção). O RESILIA é licenciado como software por mini-rede e por mês.",
               "A local company or cooperative operates the mini-grid and employs village technicians (snow and dust "
               "cleaning, maintenance). RESILIA is licensed as software per mini-grid per month."), C["solar"])
    with cc:
        card(T("Quem financia", "Who finances"), T("Capital misto", "Blended capital"),
             T("Subvenções (Horizon Europe/EMERGE, fundos de adaptação climática), financiamento por resultados, bancos de "
               "desenvolvimento e parceiros de saúde e água.",
               "Grants (Horizon Europe/EMERGE, climate-adaptation funds), results-based finance, development banks and "
               "health and water partners."), C["wind"])

    st.markdown(f"#### {T('Sustentabilidade em três dimensões', 'Sustainability in three dimensions')}")
    amb = (T("sem gerador nesta configuração: 100 % renovável, zero gasóleo e zero emissões de operação.",
             "no generator in this configuration: 100 % renewable, zero diesel and zero operating emissions.")
           if not ctx.hw["diesel_kw"] else
           T(f"{num(ar['diesel_L'])} L de gasóleo por ano com RESILIA, contra {num(ac['diesel_L'])} L com a gestão de hoje "
             f"(mesmo equipamento), ou seja, {num((ac['co2_kg'] - ar['co2_kg']) / 1000, 1)} t de CO₂ evitadas por ano.",
             f"{num(ar['diesel_L'])} L of diesel per year with RESILIA vs {num(ac['diesel_L'])} L under today's operation "
             f"(same equipment): {num((ac['co2_kg'] - ar['co2_kg']) / 1000, 1)} t of CO₂ avoided per year."))
    st.markdown(T(f"""
- **Económica:** tarifa de referência de {num(tariff, 2)} USD/kWh, alinhada com as mini-redes da África subsariana. O «prémio
  de resiliência» por família é menor do que o que as famílias gastam hoje em velas, pilhas e carregamento de telemóveis.
- **Ambiental:** {amb}
- **Social:** a prioridade não se decide no meio da crise. Fica acordada antes com a comunidade (comité de energia) e é
  executada automaticamente. Os cortes são planeados, comunicados por SMS e rádio, e a clínica é sempre a última.
""", f"""
- **Economic:** reference tariff of {num(tariff, 2)} USD/kWh, in line with sub-Saharan African mini-grids. The per-household
  “resilience premium” is lower than what families spend today on candles, batteries and phone charging.
- **Environmental:** {amb}
- **Social:** priorities are not decided in the middle of a crisis. They are agreed beforehand with the community (energy
  committee) and executed automatically. Cuts are planned, announced by SMS and radio, and the clinic always comes last.
"""))

    st.markdown(f"### {T('Visão de futuro: roteiro 2026–2030', 'Future vision: 2026–2030 roadmap')}")
    chain([
        (T("2026 · protótipo", "2026 · prototype"), T("Gémeo digital com dados reais (esta plataforma) · EMERGE Final Hackathon.",
                                                      "Digital twin with real data (this platform) · EMERGE Final Hackathon.")),
        (T("2027 · piloto Mabote", "2027 · Mabote pilot"), T("Controlador físico, contadores inteligentes e ligação aos alertas do INAM.",
                                                             "Physical controller, smart meters and connection to INAM warnings.")),
        (T("2027–28 · Marrocos e Mali", "2027–28 · Morocco and Mali"), T("Módulos de neve/frio e de calor/poeira validados no terreno.",
                                                                       "Snow/cold and heat/dust modules validated in the field.")),
        (T("2028–29 · software", "2028–29 · software"), T("Serviço para operadores: 50 mini-redes, previsão com IA, painel para financiadores.",
                                                          "Service for operators: 50 mini-grids, AI forecasting, funder dashboard.")),
        (T("2030 · plataforma regional", "2030 · regional platform"), T("Ligação a alertas precoces, a seguros paramétricos e ao planeamento nacional.",
                                                                       "Links to early warning, parametric insurance and national planning.")),
    ])
    st.markdown(T("""
**Para onde vai o RESILIA:**
- **Previsão por IA local:** combinar a previsão global com os sensores da própria mini-rede para corrigir o erro local.
- **Gémeo digital ao vivo:** o mesmo motor deste protótipo a correr no controlador, actualizado a cada hora.
- **Seguro paramétrico:** o Índice RESILIA mede a resiliência de forma objectiva, o que permite a uma seguradora pagar
  automaticamente quando um evento ultrapassa o limiar acordado.
- **Do kWh ao serviço:** contratos com o sector da saúde e da água pagos por «horas de serviço garantidas», não por kWh.
""", """
**Where RESILIA is heading:**
- **Local AI forecasting:** combine the global forecast with the mini-grid's own sensors to correct local errors.
- **Live digital twin:** the same engine as this prototype running on the controller, updated every hour.
- **Parametric insurance:** the RESILIA Index measures resilience objectively, allowing an insurer to pay out automatically
  when an event crosses the agreed threshold.
- **From kWh to services:** contracts with the health and water sectors paid per “guaranteed service hour”, not per kWh.
"""))
