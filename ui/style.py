"""Identidade visual RESILIA — branco, prata e vermelho — e componentes HTML reutilizáveis.

Metáfora visual usada em toda a plataforma (para ser lida sem explicação):
  • luz acesa  = amarelo-dourado   → o serviço tem energia
  • luz apagada = carvão escuro    → o serviço ficou sem energia
  • prata                          → sistema de hoje (convencional)
  • vermelho RESILIA               → a nossa solução
"""
from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

from .i18n import T
from .icons import icon

ROOT = Path(__file__).resolve().parents[1]

C = dict(
    red="#C8102E", red_dark="#8E0B21", red_soft="#FDECEF",
    ink="#1F2933", muted="#6B7280", silver="#C3C8D0", silver_soft="#ECEEF2",
    solar="#F2A900", wind="#0EA5E9", bat="#2563EB", diesel="#8B5E34", unmet="#2B2F36",
    demand="#1F2933", soc="#2563EB",
    crit="#C8102E", ess="#E8A33D", prod="#94A3B8", pump="#0EA5E9",
    ok="#F5B700", partial="#FBE3A0", planned="#D5D9E0", off="#2B2F36",
    conv="#9AA3AF", res="#C8102E", accent="#C8102E",
    bg="#F5F6F8", panel="#FFFFFF", grid="#E6E8EC", line="#DADDE3",
)

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stMarkdown, button, input, textarea, select {font-family:'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif;}
#MainMenu, footer {visibility:hidden;}
[data-testid="stHeader"]{background:#FFFFFF; border-bottom:3px solid #C8102E; box-shadow:0 2px 10px rgba(17,24,39,.06);}
[data-testid="stDecoration"]{display:none;}
.block-container{padding-top:4.2rem; padding-bottom:3rem; max-width:1320px;}
.stApp{background:#F5F6F8;}
h1,h2,h3,h4{color:#1F2933; font-weight:800; letter-spacing:-.01em;}
h3{margin-top:1.4rem;}
p, li{color:#1F2933;}
[data-testid="stCaptionContainer"]{color:#6B7280 !important;}

/* ── navegação no topo ── */
[data-testid="stNavSectionHeader"], [data-testid="stTopNavLink"] span{font-weight:600;}
[data-testid="stTopNavLink"][aria-current="page"], [data-testid="stTopNavLink"]:hover{color:#C8102E !important;}

/* ── faixa de marca ── */
.brand{display:flex; align-items:center; gap:16px; flex-wrap:wrap; background:#FFFFFF; border:1px solid #E6E8EC;
  border-radius:16px; padding:12px 18px; margin:0 0 18px 0; box-shadow:0 1px 3px rgba(17,24,39,.05);}
.brand img{height:44px; width:auto;}
.brand .name{font-size:22px; font-weight:800; color:#1F2933; letter-spacing:.02em;}
.brand .name span{color:#C8102E;}
.brand .sub{font-size:13px; color:#6B7280;}
.brand .right{margin-left:auto; display:flex; gap:8px; flex-wrap:wrap; align-items:center;}
.pill{display:inline-block; padding:5px 12px; border-radius:999px; font-size:12px; font-weight:600;
  background:#ECEEF2; color:#374151; border:1px solid #DADDE3;}
.pill.red{background:#C8102E; color:#FFFFFF; border-color:#C8102E;}

/* ── cabeçalho de página ── */
.page-h{margin:2px 0 14px 0;}
.page-h .kicker{font-size:12px; font-weight:700; color:#C8102E; letter-spacing:.12em; text-transform:uppercase;}
.page-h h2{margin:2px 0 6px 0; font-size:30px;}
.page-h p{font-size:16px; color:#4B5563; margin:0; max-width:900px;}

/* ── cartões ── */
.card{background:#FFFFFF; border:1px solid #E6E8EC; border-radius:14px; padding:16px 18px; height:100%;
  box-shadow:0 1px 3px rgba(17,24,39,.05);}
.card .t{color:#6B7280; font-size:12px; font-weight:700; letter-spacing:.06em; text-transform:uppercase;}
.card .v{color:#1F2933; font-size:28px; font-weight:800; line-height:1.15; margin-top:4px;}
.card .s{color:#4B5563; font-size:13px; margin-top:4px; line-height:1.4;}

.vs{background:#FFFFFF; border:1px solid #E6E8EC; border-radius:14px; padding:14px 16px; height:100%;
  box-shadow:0 1px 3px rgba(17,24,39,.05);}
.vs .t{color:#374151; font-size:13px; font-weight:700; margin-bottom:8px;}
.vs .row{display:flex; align-items:flex-end; justify-content:space-between; gap:10px;}
.vs .a{color:#9AA3AF; font-size:22px; font-weight:800;}
.vs .b{color:#C8102E; font-size:30px; font-weight:800;}
.vs .l{font-size:11px; color:#6B7280; text-transform:uppercase; letter-spacing:.06em; font-weight:600;}
.vs .d{font-size:12.5px; margin-top:8px; color:#4B5563; border-top:1px dashed #E6E8EC; padding-top:6px;}

.explain{background:#FFFFFF; border:1px solid #E6E8EC; border-left:5px solid #C8102E; border-radius:12px;
  padding:12px 16px; font-size:15px; color:#1F2933; margin:10px 0 16px 0;}
.explain b{color:#8E0B21;}
.warnbox{background:#FDECEF; border:1px solid #F5C2CB; border-left:5px solid #C8102E; border-radius:12px;
  padding:12px 16px; font-size:15px; color:#1F2933; margin:10px 0 14px 0;}
.goldbox{background:#FFF8E1; border:1px solid #F8DE8C; border-left:5px solid #F2A900; border-radius:12px;
  padding:12px 16px; font-size:15px; color:#1F2933; margin:10px 0 14px 0;}
.goldbox b{color:#8A5A00;}

.chain{display:flex; gap:8px; flex-wrap:wrap; align-items:stretch; margin:6px 0 14px 0;}
.chain .n{flex:1 1 160px; background:#FFFFFF; border:1px solid #E6E8EC; border-radius:12px; padding:12px 14px;
  box-shadow:0 1px 3px rgba(17,24,39,.05);}
.chain .n .h{font-size:12px; color:#C8102E; font-weight:800; text-transform:uppercase; letter-spacing:.06em;}
.chain .n .x{font-size:14px; color:#1F2933; margin-top:4px; line-height:1.4;}
.chain .arrow{align-self:center; color:#C3C8D0; font-size:22px;}

.status{display:grid; grid-template-columns:repeat(auto-fill,minmax(150px,1fr)); gap:8px;}
.st-item{border-radius:12px; padding:10px 12px; border:1px solid #E6E8EC; background:#FFFFFF;}
.st-item .h{font-size:11.5px; color:#6B7280; text-transform:uppercase; letter-spacing:.05em; font-weight:700;}
.st-item .x{font-size:16px; font-weight:800; color:#1F2933; margin-top:2px;}
.dot{display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:6px; vertical-align:middle;}

.chip{display:inline-block; padding:4px 11px; border-radius:999px; font-size:13px; margin:3px 5px 3px 0;
  border:1px solid #DADDE3; background:#FFFFFF; color:#1F2933; font-weight:500;}
.chip.red{border-color:#F5C2CB; background:#FDECEF; color:#8E0B21; font-weight:600;}
.chip.gold{border-color:#F8DE8C; background:#FFF8E1; color:#8A5A00;}

.legend{display:flex; gap:16px; flex-wrap:wrap; font-size:13.5px; color:#374151; margin:4px 0 6px 0;}
.legend span.sw{display:inline-block; width:14px; height:14px; border-radius:4px; margin-right:6px; vertical-align:-2px;
  border:1px solid rgba(0,0,0,.08);}

.foot{margin-top:30px; padding:14px; border-radius:12px; border-top:3px solid #C8102E; background:#FFFFFF;
  color:#6B7280; font-size:12.5px; text-align:center;}

/* ── painel lateral ── */
[data-testid="stSidebar"]{background:#FFFFFF !important; border-right:1px solid #E6E8EC;}
[data-testid="stSidebar"] h3{font-size:15px; margin:.6rem 0 .2rem 0;}
[data-testid="stExpander"]{border:1px solid #E6E8EC !important; border-radius:12px !important; background:#FFFFFF;}
[data-testid="stExpander"] summary p{font-weight:700;}
.stTabs [data-baseweb="tab-list"]{gap:6px; border-bottom:1px solid #E6E8EC;}
.stTabs [data-baseweb="tab"]{font-weight:600;}
.stButton>button, .stDownloadButton>button{border-radius:10px; font-weight:600;}
[data-testid="stBaseButton-primary"]{background:#C8102E !important; border-color:#C8102E !important;}
[data-testid="stBaseButton-primary"]:hover{background:#A50D26 !important; border-color:#A50D26 !important;}
[data-testid="stBaseButton-primary"] p, [data-testid="stBaseButton-primary"] *{color:#FFFFFF !important;}
[data-testid="stBaseButton-secondary"]:hover p{color:#C8102E !important;}

/* ════════════ APRESENTAÇÃO (7 min) ════════════ */
.slide{background:#FFFFFF; border:1px solid #E6E8EC; border-radius:22px; padding:30px 36px; margin:6px 0 14px 0;
  box-shadow:0 10px 30px rgba(17,24,39,.06); position:relative; overflow:hidden;}
.slide::before{content:""; position:absolute; left:0; top:0; bottom:0; width:8px; background:#C8102E;}
.slide .num{font-size:13px; font-weight:800; color:#C8102E; letter-spacing:.14em; text-transform:uppercase;}
.slide h1{font-size:44px; line-height:1.08; margin:6px 0 12px 0; color:#1F2933;}
.slide h2{font-size:34px; line-height:1.12; margin:6px 0 10px 0; color:#1F2933;}
.slide .lead{font-size:20px; color:#4B5563; line-height:1.5; max-width:1050px;}
.slide .lead b{color:#1F2933;}
.slide .red{color:#C8102E;}

.big{display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:14px; margin:18px 0 6px 0;}
.big .k{background:#F5F6F8; border:1px solid #E6E8EC; border-radius:16px; padding:18px 18px;}
.big .k .n{font-size:clamp(24px, 2.5vw, 38px); font-weight:800; color:#1F2933; line-height:1.1; white-space:nowrap;}
.big .k .n.red{color:#C8102E;}
.big .k .u{font-size:15px; color:#4B5563; margin-top:6px; line-height:1.35;}

.ideas{display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:16px; margin-top:18px;}
.idea{border:1px solid #E6E8EC; border-radius:18px; padding:20px; background:#FFFFFF; border-top:6px solid #C8102E;}
.idea .ic{font-size:34px;}
.idea .h{font-size:20px; font-weight:800; margin:8px 0 6px 0; color:#1F2933;}
.idea .x{font-size:15.5px; color:#4B5563; line-height:1.5;}

.duo{display:grid; grid-template-columns:1fr 1fr; gap:16px;}
@media (max-width:900px){.duo{grid-template-columns:1fr;}}
.side{border-radius:18px; padding:16px 18px; border:2px solid #E6E8EC; background:#FFFFFF;}
.side.today{border-color:#C3C8D0;}
.side.res{border-color:#C8102E;}
.side .tt{font-size:14px; font-weight:800; letter-spacing:.08em; text-transform:uppercase;}
.side.today .tt{color:#6B7280;}
.side.res .tt{color:#C8102E;}
.svc{display:grid; grid-template-columns:repeat(2,1fr); gap:8px; margin-top:10px;}
.svc .b{border-radius:12px; padding:10px 12px; display:flex; align-items:center; gap:10px;}
.svc .b .i{font-size:26px; line-height:1;}
.svc .b .n{font-size:11.5px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; opacity:.85;}
.svc .b .s{font-size:17px; font-weight:800; line-height:1.15;}
.dt{display:inline-block; width:12px; height:12px; border-radius:50%; margin-right:8px; vertical-align:0;}
.slide.compact{padding:18px 26px;}
.slide.compact h2{font-size:28px; margin:2px 0 0 0;}
.svc .on{background:#FFF4CC; border:1px solid #F5D46B; color:#5C4300;}
.svc .part{background:#FFF9E6; border:1px dashed #F2C94C; color:#6B5300;}
.svc .cut{background:#ECEEF2; border:1px solid #D5D9E0; color:#374151;}
.svc .offb{background:#2B2F36; border:1px solid #2B2F36; color:#F3F4F6;}
.batt{margin-top:12px; background:#ECEEF2; border-radius:10px; height:26px; position:relative; overflow:hidden;}
.batt .f{height:100%; border-radius:10px;}
.batt .lbl{position:absolute; inset:0; display:flex; align-items:center; justify-content:center;
  font-weight:800; font-size:13px; color:#1F2933;}
.say{margin-top:12px; font-size:15px; line-height:1.45; padding:10px 12px; border-radius:12px; background:#F5F6F8;}
.say.bad{background:#2B2F36; color:#F9FAFB;}

.timeline{display:flex; gap:6px; margin:6px 0 2px 0; flex-wrap:wrap;}
.timeline .s{flex:1 1 90px; text-align:center; font-size:12px; font-weight:700; padding:7px 4px; border-radius:8px;
  background:#ECEEF2; color:#6B7280; border:1px solid #E6E8EC;}
.timeline .s.done{background:#FDECEF; color:#8E0B21; border-color:#F5C2CB;}
.timeline .s.cur{background:#C8102E; color:#FFFFFF; border-color:#C8102E;}
[class*="st-key-nav_"] button{padding:6px 6px; min-height:42px; border-radius:10px;}
[class*="st-key-nav_"] button p{font-size:12.5px; font-weight:700; line-height:1.15;}
[class*="st-key-next_"] button, [class*="st-key-prev_"] button{min-height:46px;}
[class*="st-key-next_"] button p, [class*="st-key-prev_"] button p{font-size:16px; font-weight:800;}
/* ════════════ ELEMENTOS FLUTUANTES ════════════ */
.st-key-langbar{position:fixed !important; top:12px; right:22px; z-index:1000005; width:auto !important;
  background:#FFFFFF; border:1px solid #E6E8EC; border-radius:999px; padding:2px 4px;
  box-shadow:0 4px 16px rgba(17,24,39,.10);}
.st-key-langbar [data-testid="stButtonGroup"]{gap:0;}
.st-key-langbar button{min-height:30px !important; padding:2px 12px !important; border-radius:999px !important;}
.st-key-langbar button p{font-size:12.5px !important; font-weight:800 !important; letter-spacing:.06em;}
[data-testid="stLayoutWrapper"]:has(> .st-key-pitchbar), [data-testid="stLayoutWrapper"]:has(> .st-key-simbar),
.st-key-pitchbar, .st-key-simbar{position:sticky; top:3.75rem; z-index:990;}
.st-key-pitchbar, .st-key-simbar{background:rgba(245,246,248,.95); backdrop-filter:blur(10px);
  -webkit-backdrop-filter:blur(10px); padding:8px 0 6px 0; border-bottom:1px solid #E6E8EC;}
.simbar{display:flex; flex-wrap:wrap; gap:10px 22px; align-items:center; font-size:13.5px; color:#374151;
  background:#FFFFFF; border:1px solid #E6E8EC; border-radius:12px; padding:8px 14px; box-shadow:0 4px 14px rgba(17,24,39,.06);}
.simbar b{color:#1F2933;} .simbar .r{color:#C8102E; font-weight:800;} .simbar .g{color:#9AA3AF; font-weight:800;}
.simbar .lbl{font-size:11px; text-transform:uppercase; letter-spacing:.08em; color:#6B7280; font-weight:700;}
.totop{position:fixed; right:24px; bottom:24px; z-index:1000004; width:44px; height:44px; border-radius:50%;
  background:#C8102E; color:#FFFFFF !important; display:flex; align-items:center; justify-content:center;
  box-shadow:0 8px 22px rgba(200,16,46,.35); text-decoration:none !important; transition:transform .15s ease;}
.totop:hover{transform:translateY(-3px); background:#A50D26;}
.totop svg{stroke:#FFFFFF;}

/* ════════════ MICRO-INTERACÇÕES ════════════ */
@keyframes rise{from{opacity:0; transform:translateY(10px);} to{opacity:1; transform:none;}}
.slide, .card, .vs, .idea, .chain .n, .side, .big .k, .page-h{animation:rise .45s ease both;}
.card, .vs, .idea, .chain .n, .big .k{transition:transform .18s ease, box-shadow .18s ease;}
.card:hover, .vs:hover, .idea:hover, .chain .n:hover, .big .k:hover{transform:translateY(-3px);
  box-shadow:0 12px 28px rgba(17,24,39,.09);}
.ic{display:inline-block; vertical-align:-4px;}
.idea .ic, .card .t .ic{color:#C8102E;}
.svc .b .i{display:flex; align-items:center;}
.svc .offb .ic{stroke:#F3F4F6;}
.wx{display:flex; gap:16px; flex-wrap:wrap; font-size:15px; color:#4B5563; margin:2px 0 10px 0;}
.wx span{display:inline-flex; align-items:center; gap:6px;}
.legend{align-items:center;}
.speaker{font-size:13.5px; color:#6B7280; background:#F5F6F8; border:1px dashed #DADDE3; border-radius:10px;
  padding:8px 12px; margin-top:6px;}
</style>
"""


def inject():
    st.markdown(CSS, unsafe_allow_html=True)


def hide_sidebar():
    st.markdown("<style>[data-testid='stSidebar'], [data-testid='stSidebarCollapsedControl'],"
                "[data-testid='stExpandSidebarButton']{display:none !important;}</style>", unsafe_allow_html=True)


def img_b64(name: str):
    for cand in (name, name.lower(), name.upper()):
        p = ROOT / cand
        if p.exists():
            return base64.b64encode(p.read_bytes()).decode()
    return None


def brand():
    logo, emerge = img_b64("logo.png"), img_b64("EMERGE.PNG")
    lh = f'<img src="data:image/png;base64,{logo}">' if logo else ""
    eh = f'<img src="data:image/png;base64,{emerge}" style="border-radius:8px">' if emerge else ""
    st.markdown(f"""
<div id="top"></div>
<div class="brand">
  {lh}
  <div><div class="name">RESILIA <span>MZ</span></div>
  <div class="sub">{T("Mini-rede solar resiliente e eficiente", "Resilient and efficient solar mini-grid")}
  · Mabote, Inhambane</div></div>
  <div class="right"><span class="pill red">EMERGE Final Hackathon · Maputo</span>
  <span class="pill">{T("Dados reais 2015–2025", "Real data 2015–2025")}</span>
  <span class="pill">{T("Grupo 36 · UEM", "Team 36 · UEM")}</span>{eh}</div>
</div>""", unsafe_allow_html=True)


def to_top():
    """Botão flutuante «voltar ao topo»."""
    st.markdown(f'<a class="totop" href="#top" title="{T("Voltar ao topo", "Back to top")}">'
                f'{icon("up", 20, stroke=2.4)}</a>', unsafe_allow_html=True)


def lang_switch():
    """Selector de idioma flutuante (canto superior direito)."""
    if "lang" not in st.session_state:          # idioma também guardado no endereço (?lang=EN)
        q = str(st.query_params.get("lang", "PT")).upper()
        st.session_state["lang"] = q if q in ("PT", "EN") else "PT"

    def _keep():
        if st.session_state.get("lang") is None:
            st.session_state["lang"] = st.session_state.get("_lang_last", "PT")
        st.session_state["_lang_last"] = st.session_state["lang"]
        st.query_params["lang"] = st.session_state["lang"]

    with st.container(key="langbar"):
        st.segmented_control("Idioma / Language", ["PT", "EN"], key="lang", on_change=_keep,
                             label_visibility="collapsed")


def page_header(kicker, title, text):
    st.markdown(f'<div class="page-h"><div class="kicker">{kicker}</div><h2>{title}</h2><p>{text}</p></div>',
                unsafe_allow_html=True)


def card(t, v, s="", color=C["red"]):
    st.markdown(f'<div class="card" style="border-top:4px solid {color}"><div class="t">{t}</div>'
                f'<div class="v">{v}</div><div class="s">{s}</div></div>', unsafe_allow_html=True)


def versus(t, a, b, delta="", la=None, lb=None):
    la = la or T("Sistema de hoje", "Today's system")
    lb = lb or T("Com RESILIA", "With RESILIA")
    st.markdown(f'''<div class="vs"><div class="t">{t}</div>
      <div class="row"><div><div class="l">{la}</div><div class="a">{a}</div></div>
      <div style="text-align:right"><div class="l">{lb}</div><div class="b">{b}</div></div></div>
      {f'<div class="d">{delta}</div>' if delta else ''}</div>''', unsafe_allow_html=True)


def explain(title, text, kind="explain"):
    st.markdown(f'<div class="{kind}"><b>{title}</b> {text}</div>', unsafe_allow_html=True)


def chain(nodes):
    html = '<div class="chain">'
    for i, (h, x) in enumerate(nodes):
        if i:
            html += '<div class="arrow">→</div>'
        html += f'<div class="n"><div class="h">{h}</div><div class="x">{x}</div></div>'
    st.markdown(html + "</div>", unsafe_allow_html=True)


def chips(items):
    st.markdown("".join(f'<span class="chip {k}">{t}</span>' for t, k in items), unsafe_allow_html=True)


def legend(items):
    st.markdown('<div class="legend">' + "".join(
        f'<div><span class="sw" style="background:{c}"></span>{t}</div>' for t, c in items) + "</div>",
        unsafe_allow_html=True)


def footer():
    st.markdown(f'<div class="foot">RESILIA MZ · {T("Grupo 36", "Team 36")} — Ezequias Miocha, Laura Hele, '
                f'Suely Muando · Universidade Eduardo Mondlane · {T("Projecto", "Project")} EMERGE (Horizon Europe, '
                f'GA 101118278) · {T("Dados", "Data")}: ERA5 (ECMWF/Copernicus), Mabote 2015–2025</div>',
                unsafe_allow_html=True)
    to_top()
