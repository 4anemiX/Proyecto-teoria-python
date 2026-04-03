# ============================================================
# app.py — Punto de entrada principal de RiskLab USTA
# Ejecutar: streamlit run app.py
# ============================================================

import os
from dotenv import load_dotenv

load_dotenv()  # Carga variables desde .env

import streamlit as st

# ---- Configuración de página (debe ser lo primero de Streamlit) ----
st.set_page_config(
    page_title="DataRisk Studio",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- Importaciones del proyecto ----
from config import TICKERS, BENCHMARK, ALL_TICKERS, MODULES, TICKER_INFO
from utils.data_loader import cargar_precios, calcular_rendimientos, obtener_tasa_libre_riesgo

# Módulos implementados
from modules.inicio import render as render_inicio

# ── Módulos implementados ──────────────────────────────────────────────────────
from modules.inicio       import render as render_inicio
from modules.tecnico      import render as render_tecnico
from modules.rendimientos import render as render_rendimientos
from modules.garch        import render as render_garch
from modules.capm         import render as render_capm
from modules.var          import render as render_var
from modules.markowitz    import render as render_markowitz
from modules.senales      import render as render_senales
from modules.macro        import render as render_macro


# ---- CSS personalizado ----
st.markdown("""
<style>
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #001A4D 0%, #002868 100%);
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    /* Botones de módulo activo */
    .stButton > button {
        width: 100%;
        text-align: left;
        background: transparent;
        border: none;
        color: rgba(255,255,255,0.7) !important;
        padding: 0.5rem 0.75rem;
        border-radius: 8px;
        font-size: 0.9rem;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        background: rgba(255,255,255,0.1) !important;
        color: white !important;
    }
    /* Métricas */
    [data-testid="metric-container"] {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    /* Header principal */
    .main-header {
        background: linear-gradient(140deg, #3D008D 0%, #ED1E79 100%);
        padding: 1rem 1.5rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)


# ---- Estado de sesión ----
if "modulo_activo" not in st.session_state:
    st.session_state.modulo_activo = "inicio"


# ---- Sidebar ----
with st.sidebar:
    st.markdown("""
    <div style="padding: 1rem 0 1.5rem 0; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 1rem;">
        <h2 style="margin:0; font-size:1.4rem;">
            <span style="color:#ED1E79;">Data</span>Risk
            <span style="color:#FDB913;">Studio</span>
        </h2>
        <p style="margin:0.25rem 0 0 0; font-size:0.75rem; opacity:0.5;">
            Teoría del Riesgo · Proyecto Integrador
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("**Navegación**")
    for mod in MODULES:
        if st.button(mod["label"], key=f"btn_{mod['id']}"):
            st.session_state.modulo_activo = mod["id"]

    st.markdown("---")
    st.markdown("**Portafolio**")
    for ticker in TICKERS:
        info = TICKER_INFO[ticker]
        st.markdown(
            f"<small style='opacity:0.7'>**{ticker}** — {info['sector']}</small>",
            unsafe_allow_html=True
        )

    st.markdown("---")
    fred_key = os.getenv("FRED_API_KEY", "")
    if fred_key and fred_key != "tu_key_aqui":
        st.success("✅ FRED conectado")
    else:
        st.warning("⚠️ FRED no configurado")
        st.caption("Agrega tu key en el archivo .env")


# ---- Carga de datos (una sola vez, en caché) ----
with st.spinner("📡 Descargando datos del mercado..."):
    precios      = cargar_precios()
    rendimientos = calcular_rendimientos(precios)
    rf           = obtener_tasa_libre_riesgo()


# ---- Enrutamiento de módulos ----
mod = st.session_state.modulo_activo

if mod == "inicio":
    render_inicio(precios, rendimientos)
elif mod == "tecnico":
    render_tecnico(precios, rendimientos)
elif mod == "rendimientos":
    render_rendimientos(precios, rendimientos)
elif mod == "garch":
    render_garch(precios, rendimientos)
elif mod == "capm":
    render_capm(precios, rendimientos)
elif mod == "var":
    render_var(precios, rendimientos)
elif mod == "markowitz":
    render_markowitz(precios, rendimientos)
elif mod == "senales":
    render_senales(precios, rendimientos)
elif mod == "macro":
    render_macro(precios, rendimientos)
