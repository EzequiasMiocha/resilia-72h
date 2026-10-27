"""Dimensionar: optimizar para resiliência, não só para eficiência (bilingue)."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from resilia import __version__
from resilia.data import load_site
from resilia.economics import capex
from resilia.loads import Community
from resilia.optimize import optimise, system_from_row
from resilia.sites import SITES
from ui import charts
from ui.i18n import T, event, num, site as site_txt
from ui.style import C, card, explain, page_header


@st.cache_data(show_spinner=False, persist="disk")
def run_opt(site_key, hh, people, crit, ess, water, lead, version):
    s = SITES[site_key]
    comm = Community(households=hh, people=people, water_head_m=s["water_head_m"],
                     heat_sens=s["heat_sens"], cold_sens=s["cold_sens"])
    return optimise(load_site(site_key), site_key, comm, dict(crit=crit, ess=ess, water=water), lead_h=lead)


def _apply(site_key, r):
    st.session_state[f"pv_{site_key}"] = int(r["pv"])
    st.session_state[f"bat_{site_key}"] = int(r["bat"])
    st.session_state[f"inv_{site_key}"] = int(max(5, round(r["inv"] / 5) * 5))
    st.session_state[f"dg_{site_key}"] = int(r["diesel"])
    st.session_state[f"wind_{site_key}"] = int(r["wind"])
    st.session_state["applied_msg"] = (int(r["pv"]), int(r["bat"]), int(r["diesel"]))


def render(ctx):
    k = ctx.site_key
    page_header(T("Dimensionar", "System sizing"),
                T(f"Que sistema comprar para {site_txt(k, 'name')}?", f"Which system should {site_txt(k, 'name')} buy?"),
                T("O habitual é escolher o sistema mais barato para o dia médio. O RESILIA escolhe o mais barato que "
                  "aguenta o PIOR evento real da década. Defina as metas abaixo; testamos 147 sistemas contra todos os "
                  "eventos extremos do local.",
                  "The usual approach picks the cheapest system for the average day. RESILIA picks the cheapest one that "
                  "survives the WORST real event of the decade. Set the targets below; we test 147 systems against every "
                  "extreme event at this site."))
    c1, c2, c3 = st.columns(3)
    with c1:
        crit = st.slider(T("Meta: cargas críticas servidas no pior evento (%)", "Target: critical loads served in the worst event (%)"),
                         90.0, 100.0, 99.5, 0.5, key="opt_crit")
    with c2:
        ess = st.slider(T("Meta: casas com luz e telemóvel (%)", "Target: homes with lights and phone (%)"), 50, 100, 95, 5,
                        key="opt_ess")
    with c3:
        water = st.slider(T("Meta: água potável servida (%)", "Target: drinking water served (%)"), 50, 100, 95, 5,
                          key="opt_water")

    with st.spinner(T("A testar 147 sistemas contra os eventos extremos reais… (só demora a primeira vez)",
                      "Testing 147 systems against the real extreme events… (only slow the first time)")):
        res = run_opt(k, ctx.comm.households, ctx.comm.people, crit, ess, water, ctx.lead, __version__)
    d, best, eff, ren = res["table"], res["best"], res["efficient"], res["renewable"]
    evs = res["events"]
    if not res["feasible"]:
        st.markdown(f'<div class="warnbox">{T("Nenhuma combinação testada cumpre todas as metas. A mostrar a mais próxima. Baixe ligeiramente as metas ou aumente a gama de equipamento.", "No tested combination meets every target. Showing the closest one. Relax the targets slightly or widen the equipment range.")}</div>',
                    unsafe_allow_html=True)

    st.markdown(f"#### {T('A recomendação RESILIA', 'The RESILIA recommendation')}")
    a, b, c, dd, e = st.columns(5)
    with a:
        card(T("Solar", "Solar"), f"{best['pv']:.0f} kWp",
             T(f"≈ {round(best['pv'] * 1000 / 550)} painéis de 550 W", f"≈ {round(best['pv'] * 1000 / 550)} panels of 550 W"), C["solar"])
    with b:
        card(T("Baterias LFP", "LFP batteries"), f"{best['bat']:.0f} kWh",
             T(f"≈ {round(best['bat'] / 5)} módulos de 5 kWh", f"≈ {round(best['bat'] / 5)} modules of 5 kWh"), C["bat"])
    with c:
        card(T("Gerador de reserva", "Backup generator"),
             f"{best['diesel']:.0f} kW" if best["diesel"] else T("não precisa", "not needed"),
             T(f"só para eventos; ~{num(best['fuel_y'])} L/ano", f"events only; ~{num(best['fuel_y'])} L/year")
             if best["diesel"] else T("100 % renovável", "100 % renewable"), C["diesel"])
    with dd:
        card(T("Investimento", "Investment"), f"{num(best['capex'] / 1000)} k USD",
             T(f"{num(best['capex'] / ctx.comm.households)} USD por família",
               f"{num(best['capex'] / ctx.comm.households)} USD per household"), C["prod"])
    with e:
        card(T("Custo da energia", "Cost of energy"), f"{num(best['lcoe'], 2)} USD",
             T("por kWh (LCOE, 20 anos, taxa 10 %)", "per kWh (LCOE, 20 years, 10 % rate)"), C["accent"])
    st.button(T("Usar este sistema no simulador", "Use this system in the simulator"), on_click=_apply, args=(k, best),
              type="primary", icon=":material/check_circle:")
    if st.session_state.get("applied_msg"):
        pv, bat, dg = st.session_state.pop("applied_msg")
        st.success(T(f"Configuração aplicada: {pv} kWp, {bat} kWh" + (f", gerador {dg} kW" if dg else "") +
                     ". Abra a página «Simulador 72 h» no menu do topo.",
                     f"Configuration applied: {pv} kWp, {bat} kWh" + (f", generator {dg} kW" if dg else "") +
                     ". Open the “72-h Simulator” page in the top menu."))

    st.markdown(f"#### {T('Três filosofias de projecto, frente a frente', 'Three design philosophies, side by side')}")
    cols = {T("Só eficiência (o habitual)", "Efficiency only (usual)"): eff,
            T("RESILIA 100 % renovável", "RESILIA 100 % renewable"): ren,
            T("RESILIA robusto (recomendado)", "RESILIA robust (recommended)"): best}
    rows = {
        T("Solar (kWp)", "Solar (kWp)"): lambda r: f"{r['pv']:.0f}",
        T("Baterias (kWh)", "Batteries (kWh)"): lambda r: f"{r['bat']:.0f}",
        T("Gerador (kW)", "Generator (kW)"): lambda r: f"{r['diesel']:.0f}",
        T("Controlo inteligente + reforço físico", "Smart control + physical hardening"):
            lambda r: T("não", "no") if r["tipo"] == "eficiente" else T("sim", "yes"),
        T("Investimento (USD)", "Investment (USD)"): lambda r: num(r["capex"]),
        T("Custo anual total (USD/ano)", "Total annual cost (USD/year)"): lambda r: num(r["annual"]),
        "LCOE (USD/kWh)": lambda r: num(r["lcoe"], 2),
        T("Procura servida em semanas normais", "Demand served in normal weeks"): lambda r: f"{num(r['normal_pct'])}%",
        T("Cargas críticas no PIOR evento", "Critical loads in the WORST event"): lambda r: f"{num(r['worst_crit'])}%",
        T("Casas com luz essencial no PIOR evento", "Homes with essential light in the WORST event"): lambda r: f"{num(r['worst_ess'])}%",
        T("Água no PIOR evento", "Water in the WORST event"): lambda r: f"{num(r['worst_water'])}%",
        T("Horas de clínica sem energia (soma dos eventos)", "Clinic hours without power (sum of events)"):
            lambda r: f"{r['total_out']:.0f} h",
    }
    tab = pd.DataFrame({name: [f(r) for f in rows.values()] for name, r in cols.items()}, index=list(rows))
    st.table(tab)
    prem = best["annual"] - eff["annual"]
    per_fam = prem / ctx.comm.households / 12
    explain(T("O prémio da resiliência:", "The resilience premium:"),
            T(f"o sistema robusto custa mais <b>{num(prem)} USD/ano</b> do que o «só eficiência», cerca de "
              f"<b>{num(per_fam, 1)} USD por família por mês</b>. Em troca, a clínica passa de <b>{eff['total_out']:.0f} h</b> "
              f"sem energia nos eventos extremos reais para <b>{best['total_out']:.0f} h</b>. É um valor que um financiador "
              "de adaptação climática, um seguro paramétrico ou o orçamento de saúde podem pagar.",
              f"the robust system costs <b>{num(prem)} USD/year</b> more than “efficiency only”, about "
              f"<b>{num(per_fam, 1)} USD per household per month</b>. In return, clinic outage across the real extreme events "
              f"falls from <b>{eff['total_out']:.0f} h</b> to <b>{best['total_out']:.0f} h</b>. That is a cost a climate-adaptation "
              "funder, a parametric insurer or the health budget can carry."))
    if not res["renewable_ok"]:
        explain(T("Sem gasóleo?", "No diesel?"),
                T("nenhuma configuração 100 % renovável da grelha cumpre todas as metas neste local: os eventos são longos "
                  "demais para baterias de custo razoável. O gerador fica como seguro, a funcionar poucas horas por ano.",
                  "no 100 % renewable configuration in the grid meets every target at this site: the events are too long for "
                  "reasonably priced batteries. The generator stays as insurance, running only a few hours a year."),
                kind="goldbox")

    l, r = st.columns(2)
    with l:
        fig = go.Figure()
        names = [event(e, "name").replace(" (", "<br>(") for e in evs]
        for row, name, col in [(eff, T("Só eficiência", "Efficiency only"), C["conv"]),
                               (ren, T("RESILIA 100 % renovável", "RESILIA 100 % renewable"), C["wind"]),
                               (best, T("RESILIA robusto", "RESILIA robust"), C["res"])]:
            fig.add_trace(go.Bar(x=names, y=[row[f"crit_{e}"] for e in evs], name=name, marker_color=col,
                                 text=[f"{row[f'crit_{e}']:.0f}%" for e in evs], textposition="outside"))
        fig.update_layout(barmode="group", yaxis=dict(title=T("Cargas críticas servidas (%)", "Critical loads served (%)"),
                                                      range=[0, 118]))
        charts.base(fig, T("Cada evento real, cada filosofia", "Each real event, each philosophy"), height=460)
        fig.update_layout(legend=dict(orientation="h", y=-0.22, yanchor="top", x=0), margin=dict(t=50, b=110),
                          xaxis=dict(tickangle=0))
        st.plotly_chart(fig, width="stretch")
    with r:
        rob = d[d.tipo == "robusto"]
        okm = ((rob.worst_crit >= crit) & (rob.worst_ess >= ess) & (rob.worst_water >= water) & (rob.normal_pct >= 95))
        fig = go.Figure()
        for mask, name, colr, size in [(~okm, T("Não cumpre as metas", "Misses the targets"), "#C3C8D0", 8),
                                       (okm, T("Cumpre as metas", "Meets the targets"), "#F2A0AE", 9)]:
            sub = rob[mask]
            fig.add_trace(go.Scatter(x=sub["annual"] / 1000, y=sub["worst_crit"], mode="markers", name=name,
                                     marker=dict(color=colr, size=size),
                                     text=[f"{p:.0f} kWp / {b:.0f} kWh / {g:.0f} kW" for p, b, g in zip(sub.pv, sub.bat, sub.diesel)],
                                     hovertemplate="%{text}"))
        for row, name, col in [(eff, T("Só eficiência", "Efficiency only"), "#6B7280"),
                               (best, T("RESILIA robusto", "RESILIA robust"), C["red"])]:
            fig.add_trace(go.Scatter(x=[row["annual"] / 1000], y=[row["worst_crit"]], mode="markers+text", name=name,
                                     marker=dict(symbol="star", size=20, color=col, line=dict(color="#000", width=1)),
                                     text=[name], textposition="top right"))
        fig.update_layout(xaxis_title=T("Custo anual total (mil USD/ano)", "Total annual cost (k USD/year)"),
                          yaxis_title=T("Cargas críticas no pior evento (%)", "Critical loads in the worst event (%)"))
        charts.base(fig, T("Mapa de soluções: custo vs resiliência", "Solution map: cost vs resilience"), height=460)
        fig.update_layout(legend=dict(orientation="h", y=-0.22, yanchor="top", x=0), margin=dict(t=50, b=110),
                          hovermode="closest")
        st.plotly_chart(fig, width="stretch")
    explain(T("Como ler o mapa:", "How to read the map:"),
            T("cada ponto é um sistema testado. Os rosa cumprem as metas em <b>todos</b> os eventos reais; a estrela "
              "vermelha é o mais barato entre eles. A estrela cinzenta é o projecto «só eficiência»: mais barato, mas deixa "
              "a clínica às escuras quando o clima aperta.",
              "each dot is a tested system. Pink dots meet the targets in <b>every</b> real event; the red star is the "
              "cheapest of them. The grey star is the “efficiency only” design: cheaper, but it leaves the clinic in the "
              "dark when the weather turns."))

    with st.expander(T("Detalhe do investimento recomendado", "Breakdown of the recommended investment"),
                     icon=":material/receipt_long:"):
        items = capex(system_from_row(best, True), ctx.comm.households, True)
        names = {"Solar fotovoltaico": "Solar PV", "Baterias LFP": "LFP batteries", "Inversor/carregador": "Inverter/charger",
                 "Aerogerador": "Wind turbine", "Gerador de reserva": "Backup generator",
                 "Contentor climatizado": "Climate-controlled enclosure", "Controlo inteligente RESILIA": "RESILIA smart control",
                 "Engenharia e logística": "Engineering and logistics"}
        st.table(pd.DataFrame({T("Componente", "Component"): [T(x, names.get(x, x)) for x in items],
                               "USD": [num(v) for v in items.values()]}))
        st.caption(T("Custos indicativos de mini-redes em África (2024–2025), editáveis na página «Negócio».",
                     "Indicative African mini-grid costs (2024–2025), editable on the “Business” page."))
