import os
import requests
import streamlit as st
from typing import Dict, List, Any, Optional

# En local usa localhost, en Render usa la variable de entorno
BASE_URL = os.environ.get("BACKEND_URL", "http://localhost:8002")

def _get(endpoint: str) -> Any:
    try:
        r = requests.get(f"{BASE_URL}{endpoint}", timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Error al conectar con el backend: {e}")
        return None

def _post(endpoint: str, payload: Dict) -> Any:
    try:
        r = requests.post(f"{BASE_URL}{endpoint}", json=payload, timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Error al conectar con el backend: {e}")
        return None

@st.cache_data(ttl=1800)
def fetch_activos() -> Optional[List[Dict]]:
    return _get("/activos")

@st.cache_data(ttl=1800)
def fetch_precios(ticker: str) -> Optional[Dict]:
    return _get(f"/precios/{ticker}")

@st.cache_data(ttl=1800)
def fetch_rendimientos(ticker: str) -> Optional[Dict]:
    return _get(f"/rendimientos/{ticker}")

@st.cache_data(ttl=1800)
def fetch_indicadores(ticker: str) -> Optional[Dict]:
    return _get(f"/indicadores/{ticker}")

@st.cache_data(ttl=1800)
def fetch_capm() -> Optional[List[Dict]]:
    return _get("/capm")

@st.cache_data(ttl=1800)
def fetch_macro() -> Optional[Dict]:
    return _get("/macro")

@st.cache_data(ttl=1800)
def fetch_alertas() -> Optional[List[Dict]]:
    return _get("/alertas")

@st.cache_data(ttl=1800)
def fetch_var(ticker: str, confidence: float = 0.95, simulations: int = 10000) -> Optional[Dict]:
    return _post("/var", {"ticker": ticker, "confidence": confidence, "simulations": simulations})

@st.cache_data(ttl=1800)
def fetch_frontera(tickers: List[str], weights: List[float]) -> Optional[Dict]:
    return _post("/frontera-eficiente", {"tickers": tickers, "weights": weights})

PORTFOLIO_META = {
    "ACN":  {"empresa": "Accenture",     "sector": "Consultoría Tecnológica",        "color": "#00D4FF"},
    "MSFT": {"empresa": "Microsoft",      "sector": "Cloud / IA",                    "color": "#7B68EE"},
    "NVDA": {"empresa": "NVIDIA",         "sector": "Semiconductores / IA",          "color": "#76FF03"},
    "KO":   {"empresa": "Coca-Cola",      "sector": "Consumo Defensivo",             "color": "#FF4081"},
    "JPM":  {"empresa": "JPMorgan Chase", "sector": "Finanzas Digitales",            "color": "#FFD740"},
    "SPY":  {"empresa": "S&P 500 ETF",    "sector": "Benchmark",                     "color": "#B0BEC5"},
}
TICKERS = ["ACN", "MSFT", "NVDA", "KO", "JPM"]
BENCHMARK = "SPY"