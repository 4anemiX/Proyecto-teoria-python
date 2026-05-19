import streamlit as st
from utils.styles import GLOBAL_CSS
from utils.theme import COLORS, ticker_color
from datetime import date, timedelta
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
    "Vista General":     "pages.overview",
    "Análisis Técnico":  "pages.m1_technical",
    "Rendimientos":      "pages.m2_returns",
    "ARCH/GARCH":        "pages.m3_garch",
    "CAPM & Beta":       "pages.m4_capm",
    "VaR & CVaR":        "pages.m5_var",
    "Markowitz":         "pages.m6_markowitz",
    "Señales & Alertas": "pages.m7_signals",
    "Macro & Benchmark": "pages.m8_macro",
    "Asistente IA":      "pages.m9_ia",
    "Renta Fija":        "pages.m_rf",
    "Opciones B-S":      "pages.m_opt",
    "Stress Testing":    "pages.m_stress",
    "Predicción ML":     "pages.m_ml",
    "Portafolios":       "pages.portafolios",
}

PORTFOLIO = {
    "ACN":  "Accenture",
    "MSFT": "Microsoft",
    "NVDA": "NVIDIA",
    "KO":   "Coca-Cola",
    "JPM":  "JPMorgan",
    "SPY":  "Benchmark",
}

# ── Inicializar fechas SOLO si no existen ─────────────────────────────────────
if "global_start" not in st.session_state:
    st.session_state["global_start"] = date.today() - timedelta(days=365 * 3)
if "global_end" not in st.session_state:
    st.session_state["global_end"] = date.today()


def _apply_dates(new_start: date, new_end: date):
    """
    Centraliza el cambio de fechas: actualiza session_state, limpia el
    caché y dispara el rerun. Llamar SIEMPRE que las fechas cambien para
    garantizar consistencia.
    """
    st.session_state["global_start"] = new_start
    st.session_state["global_end"]   = new_end
    st.cache_data.clear()
    st.rerun()


# ── Sidebar ───────────────────────────────────────────────────────────────────
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

    st.markdown(
        '<div style="font-size:0.68rem; font-weight:600; letter-spacing:0.1em; '
        'text-transform:uppercase; color:#2E3550; margin-bottom:8px;">Módulos</div>',
        unsafe_allow_html=True,
    )
    selection = st.radio("nav", list(PAGES.keys()), label_visibility="collapsed")

    st.markdown('<hr style="border:none;border-top:1px solid #141824;margin:20px 0;">', unsafe_allow_html=True)

    # ── Selector de fechas global ─────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:0.68rem; font-weight:600; letter-spacing:0.1em; '
        'text-transform:uppercase; color:#2E3550; margin-bottom:10px;">Período de análisis</div>',
        unsafe_allow_html=True,
    )

    picked_start = st.date_input(
        "Fecha inicio",
        value=st.session_state["global_start"],
        min_value=date(2000, 1, 1),
        max_value=date.today() - timedelta(days=1),
        format="YYYY-MM-DD",
        key="_picker_start",
    )
    picked_end = st.date_input(
        "Fecha fin",
        value=st.session_state["global_end"],
        min_value=date(2000, 1, 2),
        max_value=date.today(),
        format="YYYY-MM-DD",
        key="_picker_end",
    )

    # ── Detectar cambio y aplicar ─────────────────────────────────────────────
    # Se compara contra session_state (no contra _prev_*) para evitar
    # doble rerun y que el picker quede desincronizado visualmente.
    dates_changed = (
        picked_start != st.session_state["global_start"] or
        picked_end   != st.session_state["global_end"]
    )
    dates_valid = picked_start < picked_end

    if dates_valid and dates_changed:
        _apply_dates(picked_start, picked_end)   # limpia caché + rerun

    # ── Presets rápidos ───────────────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:0.65rem; color:#3B4460; margin:8px 0 6px;">Presets rápidos</div>',
        unsafe_allow_html=True,
    )
    p1, p2, p3 = st.columns(3)
    if p1.button("1A", use_container_width=True, key="preset_1y"):
        _apply_dates(date.today() - timedelta(days=365), date.today())
    if p2.button("3A", use_container_width=True, key="preset_3y"):
        _apply_dates(date.today() - timedelta(days=365 * 3), date.today())
    if p3.button("5A", use_container_width=True, key="preset_5y"):
        _apply_dates(date.today() - timedelta(days=365 * 5), date.today())

    # ── Feedback visual ───────────────────────────────────────────────────────
    if not dates_valid:
        st.error("La fecha inicio debe ser anterior a la fecha fin.")
    else:
        delta_days = (st.session_state["global_end"] - st.session_state["global_start"]).days
        st.markdown(
            f'<div style="font-size:0.68rem; color:#3B4460; margin-top:6px; text-align:center;">'
            f'{delta_days:,} días seleccionados</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<hr style="border:none;border-top:1px solid #141824;margin:20px 0;">', unsafe_allow_html=True)

    st.markdown(
        '<div style="font-size:0.68rem; font-weight:600; letter-spacing:0.1em; '
        'text-transform:uppercase; color:#2E3550; margin-bottom:10px;">Portafolio</div>',
        unsafe_allow_html=True,
    )
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
    st.markdown(
        '<div style="font-size:0.68rem; color:#2A3048; line-height:1.6;">'
        'Prof. Javier Mauricio Sierra<br>USTA · 2026</div>',
        unsafe_allow_html=True,
    )

# ── Renderizar página seleccionada ────────────────────────────────────────────
module = importlib.import_module(PAGES[selection])
module.render()