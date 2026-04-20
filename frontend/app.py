import streamlit as st
from utils.styles import GLOBAL_CSS
from utils.theme import COLORS, ticker_color
import importlib
st.set_page_config(
    page_title="DataRisk · Economía Digital",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
st.markdown("""
<style>
[data-testid="stSidebarNav"] { display: none; }
</style>
""", unsafe_allow_html=True)
PAGES = {
    "Vista General":          "pages.overview",
    "Análisis Técnico":  "pages.m1_technical",
    "Rendimientos":      "pages.m2_returns",
    "ARCH/GARCH":        "pages.m3_garch",
    "CAPM & Beta":       "pages.m4_capm",
    "VaR & CVaR":        "pages.m5_var",
    "Markowitz":         "pages.m6_markowitz",
    "Señales & Alertas": "pages.m7_signals",
    "Macro & Benchmark": "pages.m8_macro",
    "Asistente IA":      "pages.m9_ia",
}
PORTFOLIO = {
    "ACN":  "Accenture",
    "MSFT": "Microsoft",
    "NVDA": "NVIDIA",
    "KO":   "Coca-Cola",
    "JPM":  "JPMorgan",
    "SPY":  "Benchmark",
}
with st.sidebar:
    st.markdown("""
    <div style="padding: 8px 0 20px 0;">
        <div style="font-family:'Playfair Display',serif; font-size:1.25rem;
                    font-weight:700; color:#E8EAF0; letter-spacing:-0.02em;">
            DataRisk
        </div>
        <div style="font-size:0.7rem; font-weight:500; letter-spacing:0.1em;
                    text-transform:uppercase; color:#3B4460; margin-top:2px;">
            Economía Digital & Servicios Globales
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.68rem; font-weight:600; letter-spacing:0.1em; text-transform:uppercase; color:#2E3550; margin-bottom:8px;">Módulos</div>', unsafe_allow_html=True)
    selection = st.radio("nav", list(PAGES.keys()), label_visibility="collapsed")
    st.markdown('<hr style="border:none;border-top:1px solid #141824;margin:20px 0;">', unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.68rem; font-weight:600; letter-spacing:0.1em; text-transform:uppercase; color:#2E3550; margin-bottom:10px;">Portafolio</div>', unsafe_allow_html=True)
    for ticker, name in PORTFOLIO.items():
        color = ticker_color(ticker)
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
            <div style="width:6px; height:6px; border-radius:50%;
                        background:{color}; flex-shrink:0; opacity:0.85;"></div>
            <span style="font-family:'DM Mono',monospace; font-size:0.75rem;
                         color:{color}; font-weight:500;">{ticker}</span>
            <span style="font-size:0.72rem; color:#3B4460;">{name}</span>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('<hr style="border:none;border-top:1px solid #141824;margin:20px 0;">', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:0.68rem; font-weight:600; letter-spacing:0.1em;
                text-transform:uppercase; color:#2E3550; margin-bottom:6px;">IA</div>
    <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
        <div style="width:6px; height:6px; border-radius:50%;
                    background:#34D399; flex-shrink:0; opacity:0.85;"></div>
        <span style="font-size:0.72rem; color:#3B4460;">Asistente · Claude Haiku</span>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<hr style="border:none;border-top:1px solid #141824;margin:20px 0;">', unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.68rem; color:#2A3048; line-height:1.6;">Prof. Javier Mauricio Sierra<br>USTA · 2026</div>', unsafe_allow_html=True)
module = importlib.import_module(PAGES[selection])
module.render()
