"""Shared presentation primitives and responsive console theme."""
import streamlit as st


def inject_theme():
    st.markdown('''
    <style>
    [data-testid="stMainBlockContainer"] {padding-top:2rem!important;max-width:1500px;}
    [data-testid="stSidebarUserContent"] {padding-top:1rem!important;}
    [data-testid="stSidebar"] label {min-height:38px;}
    .hero-copy {margin-bottom:16px;}

    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
    :root { --canvas:#111713; --surface:#1A211D; --raised:#222B25; --ink:#F4F2E9; --muted:#ADB7AD; --amber:#E6A15B; --amber-soft:#F1C27D; --teal:#71B6A1; --red:#D96A5F; --border:#39443C; }
    html, body, [class*="css"] { font-family:'DM Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; }
    .stApp { background:radial-gradient(ellipse at 78% -10%, rgba(230,161,91,.11), transparent 36%), var(--canvas); color:var(--ink); }
    [data-testid="stHeader"] { background:rgba(17,23,19,.84); }
    [data-testid="stSidebar"] { background:#151C17; border-right:1px solid var(--border); }
    [data-testid="stSidebar"] > div:first-child { padding-top:1.4rem; }
    h1,h2,h3 { color:var(--ink)!important; font-family:'Manrope','DM Sans',sans-serif!important; letter-spacing:-.035em!important; }
    h1 { font-size:2.15rem!important; font-weight:800!important; }
    h2 { font-size:1.45rem!important; font-weight:750!important; }
    h3 { font-size:1.08rem!important; font-weight:700!important; }
    p, label, li, [data-testid="stCaptionContainer"] { color:var(--muted); }
    [data-testid="stMetric"] { background:linear-gradient(145deg,#202821,#19211c); border:1px solid var(--border); border-radius:16px; padding:18px 20px; min-height:124px; box-shadow:0 8px 24px rgba(0,0,0,.14); }
    [data-testid="stMetricLabel"] { color:var(--muted)!important; font-size:.85rem!important; }
    [data-testid="stMetricValue"] { color:var(--ink)!important; font-family:'Manrope',sans-serif; font-size:1.8rem!important; font-weight:800!important; }
    [data-testid="stMetricDelta"] { font-size:.78rem!important; }
    [data-testid="stVerticalBlockBorderWrapper"] { border-color:var(--border)!important; border-radius:16px!important; background:rgba(26,33,29,.68); }
    .stButton > button, .stDownloadButton > button { border-radius:10px; min-height:42px; font-weight:650; transition:all .18s ease; }
    .stButton > button[kind="primary"] { background:var(--amber); border-color:var(--amber); color:#21180f; }
    .stButton > button:hover, .stDownloadButton > button:hover { border-color:var(--amber); color:var(--amber-soft); transform:translateY(-1px); }
    button:focus-visible, input:focus-visible, [tabindex="0"]:focus-visible { outline:3px solid var(--amber)!important; outline-offset:2px!important; }
    [data-testid="stDataFrame"], [data-testid="stTable"] { border:1px solid var(--border); border-radius:12px; overflow:hidden; }
    [data-testid="stAlert"] { border-radius:12px; }
    .console-kicker { text-transform:uppercase; letter-spacing:.15em; color:var(--amber); font-weight:700; font-size:.72rem; }
    .hero-title { font-family:'Manrope',sans-serif; font-size:2.45rem; line-height:1.1; letter-spacing:-.055em; font-weight:800; color:var(--ink); margin:.2rem 0 .55rem; }
    .hero-copy { max-width:760px; font-size:1rem; line-height:1.6; color:var(--muted); }
    .status-pill { display:inline-flex; align-items:center; gap:.45rem; padding:.4rem .75rem; border-radius:999px; border:1px solid rgba(230,161,91,.45); background:rgba(230,161,91,.1); color:var(--amber-soft); font-size:.78rem; font-weight:700; }
    .panel-card { background:linear-gradient(145deg,rgba(34,43,37,.94),rgba(26,33,29,.92)); border:1px solid var(--border); border-radius:16px; padding:18px 20px; }
    .panel-card h3 { margin:0 0 .55rem; }
    .muted-small { font-size:.82rem; color:var(--muted); line-height:1.5; }
    .severity-critical { color:#F18C80; }
    .severity-high { color:#F0B36F; }
    .severity-medium { color:#E8D17D; }
    @media(max-width:768px) { .hero-title {font-size:1.85rem;} [data-testid="stMetric"]{padding:13px;min-height:108px;} h1{font-size:1.7rem!important;} }
    @media(prefers-reduced-motion:reduce) { *,*::before,*::after {scroll-behavior:auto!important;transition:none!important;animation:none!important;} }
    </style>
    ''', unsafe_allow_html=True)


def hero(kicker: str, title: str, description: str, badge: str | None = None):
    badge_html = f'<span class="status-pill">{badge}</span>' if badge else ''
    st.markdown(f'<div class="console-kicker">{kicker}</div><div class="hero-title">{title}</div><div class="hero-copy">{description}</div>{badge_html}', unsafe_allow_html=True)


def card(title: str, body: str, footer: str = ''):
    st.markdown(f'<div class="panel-card"><h3>{title}</h3><div>{body}</div><div class="muted-small">{footer}</div></div>', unsafe_allow_html=True)
