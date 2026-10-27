"""Gráficos Plotly com a identidade RESILIA (tema claro, bilingue)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .i18n import T, month_short
from .style import C

FONT = dict(family="Inter, system-ui, sans-serif", color="#1F2933", size=13)


def base(fig, title=None, height=420, legend=True):
    fig.update_layout(
        template="plotly_white", plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=FONT,
        title=dict(text=title, font=dict(size=16, color="#1F2933"), x=0.0, xanchor="left") if title else None,
        height=height, margin=dict(t=78 if title else 30, l=55, r=20, b=40), hovermode="x unified",
        legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0.0, font=dict(size=12.5)) if legend else None,
        showlegend=legend, hoverlabel=dict(bgcolor="#FFFFFF", font=dict(color="#1F2933")),
    )
    fig.update_xaxes(gridcolor=C["grid"], zeroline=False, linecolor=C["line"])
    fig.update_yaxes(gridcolor=C["grid"], zeroline=False, linecolor=C["line"])
    return fig


def pt_dates(fig, idx, every=None, rows=None):
    """Eixo do tempo no idioma activo: uma marca por dia (00:00) e, se couber, ao meio-dia."""
    idx = pd.DatetimeIndex(idx)
    days = (idx[-1] - idx[0]).days + 1 if len(idx) else 1
    step = every or (12 if days <= 4 else 24)
    ticks = [t for t in idx if t.minute == 0 and t.hour % step == 0]
    text = [f"{t.day} {month_short(t.month)}" + (f"<br>{t.hour:02d}h" if step < 24 else "") for t in ticks]
    kw = dict(row="all", col=1) if rows else {}
    fig.update_xaxes(tickvals=ticks, ticktext=text, **kw)
    return fig


def _bounds(o: pd.DataFrame, col="fase", val="evento"):
    m = (o[col] == val).values if col in o else np.zeros(len(o), bool)
    if not m.any():
        return None
    idx = o.index[m]
    return idx[0] - pd.Timedelta(minutes=30), idx[-1] + pd.Timedelta(minutes=30)


def shade(fig, o, rows=None, alert=True, label=True):
    pt_dates(fig, o.index, rows=rows)
    b = _bounds(o)
    kw = dict(row="all", col=1) if rows else {}
    if alert and "alert" in o and o["alert"].any():
        a = o.index[o["alert"].values]
        if b is not None and a[0] < b[0]:
            fig.add_vrect(x0=a[0] - pd.Timedelta(minutes=30), x1=b[0], fillcolor=C["solar"], opacity=0.08,
                          line_width=0, **kw)
            if label:
                fig.add_annotation(x=a[0], y=1.0, yref="paper", xanchor="left", yanchor="bottom", showarrow=False,
                                   text=T("alerta meteorológico", "weather alert"), font=dict(color="#8A5A00", size=11.5))
    if b is not None:
        fig.add_vrect(x0=b[0], x1=b[1], fillcolor=C["red"], opacity=0.06, line_width=0, **kw)
        if label:
            fig.add_annotation(x=b[0], y=1.0, yref="paper", xanchor="left", yanchor="bottom", showarrow=False,
                               text=T("72 h de evento extremo", "72 h extreme event"), font=dict(color=C["red"], size=11.5))
    return fig


def weather(o: pd.DataFrame, w: pd.DataFrame, title=None):
    title = title or T("O que o clima fez — dados reais, hora a hora", "What the weather did — real data, hour by hour")
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.045,
                        subplot_titles=(T("Sol nos painéis (W/m²)", "Sun on the panels (W/m²)"),
                                        T("Vento e rajadas (m/s)", "Wind and gusts (m/s)"),
                                        T("Chuva (mm/h) e neve (cm/h)", "Rain (mm/h) and snow (cm/h)"),
                                        T("Temperatura do ar e da bateria (°C)", "Air and battery temperature (°C)")))
    x = o.index
    fig.add_trace(go.Scatter(x=x, y=o["poa"], name=T("Sol no painel", "Sun on panel"), fill="tozeroy",
                             line=dict(color=C["solar"], width=1.5), fillcolor="rgba(242,169,0,.25)"), 1, 1)
    fig.add_trace(go.Scatter(x=x, y=w["wind_speed_10m"], name=T("Vento médio", "Mean wind"),
                             line=dict(color=C["wind"], width=2)), 2, 1)
    fig.add_trace(go.Scatter(x=x, y=w["wind_gusts_10m"], name=T("Rajadas", "Gusts"),
                             line=dict(color="#64748B", width=1, dash="dot")), 2, 1)
    fig.add_trace(go.Bar(x=x, y=w["precipitation"], name=T("Chuva", "Rain"), marker_color="#3B82F6"), 3, 1)
    if "snowfall" in w and w["snowfall"].sum() > 0:
        fig.add_trace(go.Bar(x=x, y=w["snowfall"], name=T("Neve", "Snow"), marker_color="#94A3B8"), 3, 1)
    fig.add_trace(go.Scatter(x=x, y=w["temperature_2m"], name=T("Ar", "Air"), line=dict(color=C["red"], width=2)), 4, 1)
    fig.add_trace(go.Scatter(x=x, y=o["t_bat"], name=T("Bateria", "Battery"),
                             line=dict(color=C["bat"], width=1.5, dash="dash")), 4, 1)
    shade(fig, o, rows=True, label=False)
    base(fig, title + T("  ·  faixa amarela = aviso, faixa rosa = evento", "  ·  yellow band = warning, pink band = event"),
         height=680)
    fig.update_layout(barmode="stack", margin=dict(t=110),
                      legend=dict(orientation="h", y=1.06, yanchor="bottom", x=0))
    for a in fig.layout.annotations:
        if a.text and "(" in a.text:
            a.font = dict(size=12.5, color="#4B5563")
    return fig


def supply(o: pd.DataFrame, title):
    x = o.index
    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=o["sC"], name=T("Crítica (saúde, comunicações, abrigo)",
                                               "Critical (health, communications, shelter)"), marker_color=C["crit"]))
    fig.add_trace(go.Bar(x=x, y=o["sE"], name=T("Casas, iluminação, escola", "Homes, lighting, school"),
                         marker_color=C["ess"]))
    fig.add_trace(go.Bar(x=x, y=o["pump"], name=T("Bomba de água", "Water pump"), marker_color=C["pump"]))
    fig.add_trace(go.Bar(x=x, y=o["sP"], name=T("Moagem e comércio", "Mill and shops"), marker_color=C["prod"]))
    unmet = (o["dC"] + o["dE"] + o["dP"]) - (o["sC"] + o["sE"] + o["sP"])
    fig.add_trace(go.Bar(x=x, y=unmet.clip(lower=0), name=T("Ficou sem energia", "Left without power"),
                         marker_color=C["unmet"], opacity=0.9))
    fig.add_trace(go.Scatter(x=x, y=o["dC"] + o["dE"] + o["dP"], name=T("O que a aldeia pediu", "What the village asked for"),
                             line=dict(color="#1F2933", width=2, dash="dot")))
    fig.update_layout(barmode="stack", bargap=0.05, yaxis_title=T("kW (≈ kWh por hora)", "kW (≈ kWh per hour)"))
    shade(fig, o)
    return base(fig, title, height=420)


def sources(o: pd.DataFrame, title):
    x = o.index
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=o["pv_av"], name=T("Sol disponível", "Solar available"),
                             line=dict(color=C["solar"], width=1.2, dash="dot")))
    fig.add_trace(go.Bar(x=x, y=o["pv"], name=T("Sol usado", "Solar used"), marker_color=C["solar"]))
    if o["wind"].sum() > 0:
        fig.add_trace(go.Bar(x=x, y=o["wind"], name=T("Vento", "Wind"), marker_color=C["wind"]))
    fig.add_trace(go.Bar(x=x, y=o["bat_dis"], name=T("Bateria a entregar", "Battery discharging"), marker_color=C["bat"]))
    if o["diesel"].sum() > 0:
        fig.add_trace(go.Bar(x=x, y=o["diesel"], name=T("Gerador a gasóleo", "Diesel generator"), marker_color=C["diesel"]))
    fig.add_trace(go.Bar(x=x, y=-o["bat_ch"], name=T("Bateria a carregar", "Battery charging"),
                         marker_color="rgba(37,99,235,.35)"))
    fig.update_layout(barmode="relative", bargap=0.05, yaxis_title="kW")
    shade(fig, o, label=False)
    return base(fig, title, height=360)


def balance24(o: pd.DataFrame, title, ymax=None):
    """Balanço de um dia (00 h → 23 h): de onde vem a energia entregue, o que ficou por servir e a bateria."""
    h = o.index.hour
    served = o["sC"] + o["sE"] + o["sP"] + o["pump"]
    demand = o["dC"] + o["dE"] + o["dP"] + o["pump"]
    unmet = (demand - served).clip(lower=0)
    bat, dsl, wnd = o["bat_dis"], o["diesel"], o["wind"]
    sun = (served - bat - dsl - wnd).clip(lower=0)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=h, y=sun, name=T("Sol", "Solar"), marker_color=C["solar"]))
    if wnd.sum() > 0:
        fig.add_trace(go.Bar(x=h, y=wnd, name=T("Vento", "Wind"), marker_color=C["wind"]))
    fig.add_trace(go.Bar(x=h, y=bat, name=T("Bateria", "Battery"), marker_color=C["bat"]))
    if dsl.sum() > 0:
        fig.add_trace(go.Bar(x=h, y=dsl, name=T("Gerador", "Generator"), marker_color=C["diesel"]))
    fig.add_trace(go.Bar(x=h, y=unmet, name=T("Interrupção (não servida)", "Interruption (unserved)"),
                         marker_color=C["unmet"]))
    fig.add_trace(go.Bar(x=h, y=-o["bat_ch"], name=T("Sol a carregar a bateria", "Solar charging the battery"),
                         marker_color="rgba(242,169,0,.35)"))
    fig.add_trace(go.Scatter(x=h, y=demand, name=T("Procura da aldeia", "Village demand"), mode="lines+markers",
                             line=dict(color="#1F2933", width=2.5), marker=dict(size=5)))
    fig.add_trace(go.Scatter(x=h, y=100 * o["soc"], name=T("Bateria (%)", "Battery (%)"),
                             line=dict(color=C["red"], width=2.5, dash="dot")), secondary_y=True)
    fig.update_layout(barmode="relative", bargap=0.12)
    fig.update_xaxes(title_text=T("Hora do dia", "Hour of day"), tickmode="array", tickvals=list(range(0, 24, 3)),
                     ticktext=[f"{x:02d}h" for x in range(0, 24, 3)])
    fig.update_yaxes(title_text="kW", secondary_y=False, range=[-(ymax or 1) * 0.6, (ymax or 1) * 1.15] if ymax else None)
    fig.update_yaxes(title_text=T("Bateria (%)", "Battery (%)"), range=[0, 105], secondary_y=True, showgrid=False)
    base(fig, title, height=430)
    fig.update_layout(legend=dict(orientation="h", y=-0.22, yanchor="top", x=0), margin=dict(t=50, b=120))
    return fig


STATUS_COLORS = [[0.0, C["off"]], [0.25, C["off"]], [0.25, C["planned"]], [0.5, C["planned"]],
                 [0.5, C["partial"]], [0.75, C["partial"]], [0.75, C["ok"]], [1.0, C["ok"]]]


def status_txt():
    return {0: T("SEM ENERGIA", "NO POWER"), 1: T("pausa planeada", "planned pause"),
            2: T("só o essencial / parcial", "essentials only / partial"), 3: T("com energia", "powered")}


def status_legend():
    return [(T("com energia", "powered"), C["ok"]), (T("só o essencial", "essentials only"), C["partial"]),
            (T("pausa planeada", "planned pause"), C["planned"]), (T("sem energia (apagão)", "no power (blackout)"), C["off"])]


ROW_KEYS = ["health", "comms", "water", "homes", "mill"]


def row_names():
    return {"health": T("Centro de saúde", "Health centre"), "comms": T("Rádio e comunicações", "Radio and comms"),
            "water": T("Água potável", "Drinking water"), "homes": T("Casas", "Homes"),
            "mill": T("Moagem e comércio", "Mill and shops")}


def service_status(o: pd.DataFrame, smart: bool) -> pd.DataFrame:
    eps = 1e-9
    fc = (o["sC"] / (o["dC"] + eps)).values
    fe = (o["sE"] / (o["dE"] + eps)).values
    fp = (o["sP"] / (o["dP"] + eps)).values
    fw = (o["w_srv"] / (o["w_need"] + eps)).values

    def lvl(f, minfrac=None, planned=False):
        s = np.where(f >= 0.98, 3, np.where(f >= 0.30, 2, 0))
        if minfrac is not None:
            s = np.where((s < 3) & (f >= minfrac), 2, s)
        if planned:
            s = np.where((s == 0) & (~o["blackout"].values), 1, s)
        return s.astype(float)

    essmin = (o["dEmin"] / (o["dE"] + eps)).values * 0.95
    st = pd.DataFrame({"health": lvl(fc), "comms": lvl(fc), "water": lvl(fw), "homes": lvl(fe, essmin),
                       "mill": lvl(fp, planned=smart)}, index=o.index)
    st.loc[o["dP"].values < 0.05, "mill"] = np.nan
    return st


def services_heatmap(o: pd.DataFrame, smart: bool, title, rows=None, height=270):
    st = service_status(o, smart)
    if rows:
        st = st[rows]
    names = row_names()
    txtmap = status_txt()
    z = st.T.values
    txt = np.vectorize(lambda v: T("fechado", "closed") if np.isnan(v) else txtmap[int(v)])(z)
    fig = go.Figure(go.Heatmap(z=z, x=st.index, y=[names[c] for c in st.columns], zmin=0, zmax=3,
                               colorscale=STATUS_COLORS, showscale=False, xgap=0.6, ygap=4, text=txt,
                               hovertemplate="%{y}<br>%{x|%d/%m %H:00}<br><b>%{text}</b><extra></extra>"))
    b = _bounds(o)
    if b is not None:
        for xx in b:
            fig.add_vline(x=xx, line=dict(color=C["red"], width=2, dash="dot"))
    base(fig, title, height=height, legend=False)
    pt_dates(fig, o.index, every=24)
    fig.update_layout(margin=dict(l=160, t=56, b=30, r=10), hovermode="closest", plot_bgcolor="#FFFFFF")
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=13.5), showgrid=False)
    fig.update_xaxes(showgrid=False)
    return fig


def soc(oc: pd.DataFrame, orr: pd.DataFrame, title=None):
    title = title or T("Bateria: quanta energia resta guardada", "Battery: how much energy is left in store")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=oc.index, y=100 * oc["soc"], name=T("Sistema de hoje", "Today's system"),
                             line=dict(color=C["conv"], width=3)))
    fig.add_trace(go.Scatter(x=orr.index, y=100 * orr["soc"], name=T("Com RESILIA", "With RESILIA"),
                             line=dict(color=C["res"], width=3.5), fill="tozeroy", fillcolor="rgba(200,16,46,.07)"))
    fig.add_trace(go.Scatter(x=orr.index, y=100 * orr["reserve"].clip(upper=1),
                             name=T("Reserva guardada para a clínica", "Reserve kept for the clinic"),
                             line=dict(color=C["red_dark"], width=1.5, dash="dash")))
    fig.add_hline(y=10, line=dict(color="#6B7280", width=1, dash="dot"),
                  annotation_text=T("mínimo técnico 10 %", "technical minimum 10 %"),
                  annotation_font_color="#6B7280", annotation_position="bottom right")
    fig.update_layout(yaxis=dict(title=T("Carga da bateria (%)", "Battery charge (%)"), range=[0, 105]))
    shade(fig, orr)
    return base(fig, title, height=360)


def fuel(oc, orr, cap):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=oc.index, y=oc["fuel"], name=T("Sistema de hoje", "Today's system"),
                             line=dict(color=C["conv"], width=3)))
    fig.add_trace(go.Scatter(x=orr.index, y=orr["fuel"], name=T("Com RESILIA", "With RESILIA"),
                             line=dict(color=C["res"], width=3.5)))
    fig.update_layout(yaxis=dict(title=T("Gasóleo no depósito (L)", "Diesel in tank (L)"), range=[0, max(cap, 1) * 1.05]))
    shade(fig, orr, label=False)
    return base(fig, T("Gasóleo — sem reabastecimento (estradas cortadas)", "Diesel — no resupply (roads cut)"), height=300)


def wind_curve(v_now=None, gust_now=None, stopped=False):
    v = np.linspace(0, 32, 200)
    vin, vr = 2.5, 11.0
    p = np.clip((v ** 3 - vin ** 3) / (vr ** 3 - vin ** 3), 0, 1) * 100
    p[v >= 20] = 0
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=v, y=p, name=T("Potência (%)", "Power (%)"), line=dict(color=C["wind"], width=3),
                             fill="tozeroy", fillcolor="rgba(14,165,233,.12)"))
    fig.add_vrect(x0=20, x1=32, fillcolor=C["red"], opacity=0.08, line_width=0,
                  annotation_text=T("paragem de segurança", "safety shutdown"), annotation_font_color=C["red"])
    fig.add_vrect(x0=0, x1=2.5, fillcolor="#94A3B8", opacity=0.15, line_width=0,
                  annotation_text=T("vento fraco", "weak wind"), annotation_font_color="#475569")
    if v_now is not None:
        pn = 0 if stopped else float(np.interp(v_now, v, p))
        fig.add_trace(go.Scatter(x=[v_now], y=[pn], mode="markers+text", name=T("Agora", "Now"),
                                 marker=dict(size=16, color=C["red"], line=dict(color="#FFFFFF", width=2)),
                                 text=[f"{pn:.0f} %"], textposition="top center"))
    fig.update_layout(xaxis_title=T("Vento à altura da turbina (m/s)", "Wind at hub height (m/s)"),
                      yaxis_title=T("% da potência nominal", "% of rated power"))
    return base(fig, T("Curva de potência do aerogerador", "Wind turbine power curve"), height=320)


def waterfall(steps):
    names = [s[0] for s in steps]
    vals = [s[1] for s in steps]
    measure = ["absolute"] + ["relative"] * (len(steps) - 2) + ["total"]
    fig = go.Figure(go.Waterfall(x=names, y=vals, measure=measure,
                                 text=[f"{v:+.0f}%" if i not in (0, len(vals) - 1) else f"{v:.0f}%" for i, v in enumerate(vals)],
                                 textposition="outside",
                                 increasing=dict(marker=dict(color="#16A34A")),
                                 decreasing=dict(marker=dict(color=C["red"])),
                                 totals=dict(marker=dict(color=C["solar"])),
                                 connector=dict(line=dict(color="#CBD5E1"))))
    fig.update_layout(yaxis_title=T("% da potência nominal do painel", "% of panel rated power"))
    return base(fig, T("Do painel ideal à energia real: o que o clima tira", "From ideal panel to real energy: what the weather takes"),
                height=380, legend=False)
