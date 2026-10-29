"""Gráficos Plotly (tema claro, bilingue) para o simulador de 24 h e o dimensionamento."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .i18n import T
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


SERVICE_COLORS = dict(homes="#E8A33D", street="#94A3B8", health=C["red"], school="#2563EB", water="#0EA5E9", mill="#6B7280")


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
