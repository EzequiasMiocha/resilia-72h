"""Gráficos Plotly (tema claro, bilingue) para o simulador de 24 h e o dimensionamento."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .i18n import T, num
from .style import C

FONT = dict(family="Inter, system-ui, sans-serif", color="#1F2933", size=13)


def base(fig, title=None, height=420, legend=True):
    fig.update_layout(
        template="plotly_white", plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=FONT,
        title=dict(text=title, font=dict(size=16, color="#1F2933"), x=0.0, xanchor="left") if title else None,
        height=height, margin=dict(t=60 if title else 20, l=55, r=20, b=40), hovermode="x unified",
        legend=dict(orientation="h", y=-0.2, yanchor="top", x=0.0, font=dict(size=12.5)) if legend else None,
        showlegend=legend, hoverlabel=dict(bgcolor="#FFFFFF", font=dict(color="#1F2933")),
    )
    fig.update_xaxes(gridcolor=C["grid"], zeroline=False, linecolor=C["line"])
    fig.update_yaxes(gridcolor=C["grid"], zeroline=False, linecolor=C["line"])
    return fig


def balance24(o: pd.DataFrame, title, ymax=None, height=440, legend=True):
    """Balanço de 24 h: de onde vem a energia, o que faltou, a carga da bateria e a procura."""
    h = o.index.hour
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=h, y=o["direct"], name=T("Sol", "Solar"), marker_color=C["solar"]))
    fig.add_trace(go.Bar(x=h, y=o["bat_dis"], name=T("Bateria", "Battery"), marker_color=C["bat"]))
    fig.add_trace(go.Bar(x=h, y=o["unmet"], name=T("Energia em falta (interrupção)", "Energy missing (interruption)"),
                         marker_color=C["unmet"]))
    fig.add_trace(go.Bar(x=h, y=-o["bat_ch"], name=T("Excedente guardado na bateria", "Surplus stored in battery"),
                         marker_color="rgba(242,169,0,.35)"))
    fig.add_trace(go.Scatter(x=h, y=o["demand"], name=T("Procura da aldeia", "Village demand"), mode="lines+markers",
                             line=dict(color="#1F2933", width=2.5), marker=dict(size=5)))
    fig.add_trace(go.Scatter(x=h, y=100 * o["soc"], name=T("Carga da bateria (%)", "Battery charge (%)"),
                             line=dict(color=C["red"], width=2.5, dash="dot")), secondary_y=True)
    fig.update_layout(barmode="relative", bargap=0.12)
    fig.update_xaxes(title_text=T("Hora do dia", "Hour of day"), tickmode="array", tickvals=list(range(0, 24, 2)),
                     ticktext=[f"{x:02d}h" for x in range(0, 24, 2)])
    if ymax:
        fig.update_yaxes(range=[-ymax * 0.75, ymax * 1.15], secondary_y=False)
    fig.update_yaxes(title_text="kW", secondary_y=False)
    fig.update_yaxes(title_text=T("Bateria (%)", "Battery (%)"), range=[0, 105], secondary_y=True, showgrid=False,
                     tickvals=[0, 50, 100], ticktext=["0", "50", "100"])
    base(fig, title, height=height, legend=legend)
    fig.update_layout(margin=dict(t=56 if title else 16, b=110 if legend else 40))
    return fig


def sequence(outs, labels, suns, height=None):
    """Vários dias seguidos no mesmo eixo do tempo.

    outs: lista de (nome, resultado da simulação). Uma faixa de barras por sistema (de onde veio a energia em cada
    hora) e, por baixo, uma faixa com a carga da bateria de todos os sistemas, para se ver quando enche e quando esgota.
    """
    n = len(outs)
    nd = len(labels)
    titles = [nm for nm, _ in outs] + [T("Carga da bateria (%)", "Battery charge (%)")]
    fig = make_subplots(rows=n + 1, cols=1, shared_xaxes=True, vertical_spacing=0.11, subplot_titles=titles,
                        row_heights=[1.0] * n + [0.8])
    lo = min(-o["bat_ch"].max() for _, o in outs) * 1.1
    hi = max(max(o["demand"].max(), (o["direct"] + o["bat_dis"] + o["unmet"]).max()) for _, o in outs) * 1.15
    bat_cols = ["#9AA3AF", C["red"]] if n == 2 else [C["red"]]
    for i, (nm, o) in enumerate(outs, start=1):
        x = np.arange(len(o))
        first = i == 1
        for col, y, name, color in [("direct", o["direct"], T("Sol", "Solar"), C["solar"]),
                                    ("bat_dis", o["bat_dis"], T("Bateria", "Battery"), C["bat"]),
                                    ("unmet", o["unmet"], T("Sem luz (energia em falta)", "No power (energy missing)"), C["unmet"]),
                                    ("bat_ch", -o["bat_ch"], T("Sol guardado na bateria", "Sun stored in battery"), "rgba(242,169,0,.38)")]:
            fig.add_trace(go.Bar(x=x, y=y, name=name, marker_color=color, showlegend=first, legendgroup=col,
                                 hovertemplate="%{y:.1f} kW<extra>" + name + "</extra>"), row=i, col=1)
        fig.add_trace(go.Scatter(x=x, y=o["demand"], name=T("Procura da aldeia", "Village demand"), mode="lines",
                                 line=dict(color="#1F2933", width=2), showlegend=first, legendgroup="dem",
                                 hovertemplate="%{y:.1f} kW<extra>" + T("Procura", "Demand") + "</extra>"), row=i, col=1)
        fig.update_yaxes(title_text="kW", range=[lo, hi], row=i, col=1)
        # resultado de cada dia, escrito por cima da faixa
        for k in range(nd):
            od = o.iloc[24 * k:24 * (k + 1)]
            h = int((od["unmet"] > 0.01 * od["demand"]).sum())
            txt = T("sem cortes", "no cuts") if h == 0 else T(f"{h} h sem luz", f"{h} h without power")
            fig.add_annotation(x=24 * k + 11.5, y=1.0, xref="x", yref=f"y{'' if i == 1 else i} domain", yanchor="bottom",
                               text=f"<b>{txt}</b>", showarrow=False,
                               font=dict(size=12.5, color="#16A34A" if h == 0 else C["red"]))
        fig.add_trace(go.Scatter(x=x, y=100 * o["soc"], name=f"{T('Bateria', 'Battery')} · {nm}", mode="lines",
                                 line=dict(color=bat_cols[i - 1], width=3), legendgroup=f"soc{i}",
                                 hovertemplate="%{y:.0f} %<extra>" + nm + "</extra>"), row=n + 1, col=1)
    fig.add_hline(y=100 * SOC_MIN_UI, line=dict(color="#6B7280", width=1, dash="dot"), row=n + 1, col=1,
                  annotation_text=T("mínimo 20 %", "minimum 20 %"), annotation_position="bottom right",
                  annotation_font=dict(size=11, color="#6B7280"))
    fig.update_yaxes(range=[0, 105], tickvals=[0, 20, 50, 100], title_text="%", row=n + 1, col=1)
    # faixas dos dias e nomes dos dias
    for k in range(nd):
        if k % 2 == 1:
            fig.add_vrect(x0=24 * k - 0.5, x1=24 * (k + 1) - 0.5, fillcolor="#F1F3F6", line_width=0, layer="below",
                          row="all", col=1)
        if k:
            fig.add_vline(x=24 * k - 0.5, line=dict(color="#C3C8D0", width=1.2), row="all", col=1)
        fig.add_annotation(x=24 * k + 11.5, y=1.0, xref="x", yref="paper", yanchor="bottom", yshift=44, showarrow=False,
                           text=f"<b>{T('Dia', 'Day')} {k + 1} · {labels[k]}</b><br>"
                                f"<span style='font-size:11.5px;color:#6B7280'>{T('sol', 'sun')}: {num(suns[k], 1)} kWh/m²</span>",
                           font=dict(size=13.5, color="#1F2933"))
    ticks = [24 * k + h for k in range(nd) for h in (0, 6, 12, 18)]
    fig.update_xaxes(tickmode="array", tickvals=ticks, ticktext=[f"{t % 24:02d}h" for t in ticks],
                     range=[-0.6, 24 * nd - 0.4], row=n + 1, col=1)
    fig.update_layout(barmode="relative", bargap=0.08)
    base(fig, None, height=height or (300 * n + 260))
    fig.update_layout(margin=dict(t=100, b=70, l=55, r=20), hovermode="x unified",
                      legend=dict(orientation="h", y=-0.07, yanchor="top", x=0, font=dict(size=12)))
    for a in fig.layout.annotations[:len(titles)]:            # títulos das faixas à esquerda, numa linha própria
        a.update(x=0, xanchor="left", yshift=20, font=dict(size=13.5, color="#1F2933"))
        a.update(text=f"<b>{a.text}</b>")
    return fig


SOC_MIN_UI = 0.20


SERVICE_COLORS =dict(homes="#E8A33D", street="#94A3B8", health=C["red"], school="#2563EB", water="#0EA5E9", mill="#6B7280")


def service_names():
    return dict(homes=T("Casas", "Homes"), street=T("Iluminação pública", "Street lighting"),
                health=T("Centro de saúde", "Health centre"), school=T("Escola", "School"),
                water=T("Bomba de água", "Water pump"), mill=T("Moagem", "Grain mill"))


def demand_profile(parts: pd.DataFrame, title):
    names = service_names()
    h = parts.index.hour
    fig = go.Figure()
    for k in ["health", "water", "homes", "street", "school", "mill"]:
        if parts[k].sum() > 0:
            fig.add_trace(go.Bar(x=h, y=parts[k], name=names[k], marker_color=SERVICE_COLORS[k]))
    fig.update_layout(barmode="stack", bargap=0.12, yaxis_title="kW")
    fig.update_xaxes(title_text=T("Hora do dia", "Hour of day"), tickmode="array", tickvals=list(range(0, 24, 2)),
                     ticktext=[f"{x:02d}h" for x in range(0, 24, 2)])
    base(fig, title, height=360)
    fig.update_layout(margin=dict(t=56, b=110), legend=dict(orientation="h", y=-0.32, yanchor="top", x=0))
    return fig


def energy_flow(f: dict, title=None, height=380):
    """Para onde vai a energia solar num ano (diagrama de fluxo, MWh/ano)."""
    nodes = [T("Energia do sol", "Solar energy"), T("Bateria", "Battery"), T("Aldeia servida", "Village served"),
             T("Excedente livre", "Free surplus"), T("Perdas da bateria", "Battery losses")]
    ncol = [C["solar"], C["bat"], C["red"], "#F7D774", "#C3C8D0"]
    src, dst, val, lc = [0, 0, 1, 1, 0], [2, 1, 2, 4, 3], [f["direct"], f["bat_in"], f["bat_out"], f["bat_loss"], f["curt"]], \
        ["rgba(242,169,0,.45)", "rgba(242,169,0,.35)", "rgba(37,99,235,.40)", "rgba(156,163,175,.45)", "rgba(247,215,116,.55)"]
    tot = [f["pv"], f["bat_in"], f["served"], f["curt"], f["bat_loss"]]
    unit = T("MWh/ano", "MWh/yr")
    fig = go.Figure(go.Sankey(
        arrangement="snap", valueformat=".0f", valuesuffix=" kWh",
        node=dict(label=nodes, customdata=[f"{num(t / 1000)} {unit}" for t in tot],
                  hovertemplate="%{label}: %{customdata}<extra></extra>",
                  color=ncol, pad=26, thickness=22, line=dict(color="#FFFFFF", width=2)),
        link=dict(source=src, target=dst, value=val, color=lc,
                  hovertemplate="%{source.label} → %{target.label}: %{value:,.0f} kWh<extra></extra>"),
    ))
    fig.update_layout(font=dict(family=FONT["family"], size=14, color="#1F2933"), height=height,
                      paper_bgcolor="rgba(0,0,0,0)", margin=dict(t=50 if title else 10, l=10, r=10, b=10),
                      title=dict(text=title, font=dict(size=16), x=0) if title else None)
    return fig


def monthly(m: pd.DataFrame, title):
    """Produção solar e procura, média por dia em cada mês (kWh/dia)."""
    lab = [T(x, y) for x, y in zip(["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"],
                                   ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=lab, y=m["pv"], name=T("Produção solar", "Solar output"), marker_color=C["solar"],
                         marker_line=dict(color="#FFFFFF", width=2),
                         hovertemplate="%{x}: %{y:.0f} kWh/" + T("dia", "day") + "<extra></extra>"))
    fig.add_trace(go.Bar(x=lab, y=m["demand"], name=T("Procura da aldeia", "Village demand"), marker_color="#4B5563",
                         marker_line=dict(color="#FFFFFF", width=2),
                         hovertemplate="%{x}: %{y:.0f} kWh/" + T("dia", "day") + "<extra></extra>"))
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.05, yaxis_title=T("kWh por dia", "kWh per day"),
                      hovermode="closest")
    base(fig, title, height=360)
    fig.update_layout(legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0), margin=dict(t=80, b=40))
    return fig


def sizing_map(tab: pd.DataFrame, eff, res, title):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=tab["cost"] / 1000, y=tab["bad_days"], mode="markers", name=T("Sistemas testados", "Systems tested"),
                             marker=dict(color="#C3C8D0", size=8),
                             text=[f"{p:.0f} kWp · {b:.0f} kWh" for p, b in zip(tab.pv, tab.bat)],
                             hovertemplate="%{text}<br>%{x:.0f}k USD · %{y:.1f}<extra></extra>"))
    for row, name, col in [(eff, T("Só eficiência", "Efficiency only"), "#6B7280"),
                           (res, T("Resiliente (recomendado)", "Resilient (recommended)"), C["red"])]:
        fig.add_trace(go.Scatter(x=[row["cost"] / 1000], y=[row["bad_days"]], mode="markers+text", name=name,
                                 marker=dict(symbol="star", size=22, color=col, line=dict(color="#FFFFFF", width=1.5)),
                                 text=[name], textposition="top right", textfont=dict(color=col, size=13)))
    fig.update_layout(xaxis_title=T("Investimento (mil USD)", "Investment (k USD)"),
                      yaxis_title=T("Dias maus por ano (> 10 % de energia em falta)", "Bad days per year (> 10 % energy missing)"),
                      hovermode="closest")
    fig.update_yaxes(type="log", range=[-1.3, 2.2], tickvals=[0.1, 0.3, 1, 3, 10, 30, 100],
                     ticktext=["0.1", "0.3", "1", "3", "10", "30", "100"])
    return base(fig, title, height=430)
