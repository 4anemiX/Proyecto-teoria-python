import os
import httpx
import streamlit as st
from typing import Dict, List, Any, Optional

# ── URL del backend ────────────────────────────────────────────────────────────
# Producción (Streamlit Cloud): lee BACKEND_URL desde secrets.toml
# Local: usa http://localhost:8000
try:
    BACKEND_URL = st.secrets.get("BACKEND_URL", "http://localhost:8000")
except Exception:
    BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

TICKERS = ["ACN", "MSFT", "NVDA", "KO", "JPM"]
BENCHMARK = "SPY"
PORTFOLIO_META = {
    "ACN":  {"empresa": "Accenture",      "sector": "Consultoría Tecnológica", "color": "#60A5FA"},
    "MSFT": {"empresa": "Microsoft",      "sector": "Cloud / IA",              "color": "#A78BFA"},
    "NVDA": {"empresa": "NVIDIA",         "sector": "Semiconductores / IA",    "color": "#34D399"},
    "KO":   {"empresa": "Coca-Cola",      "sector": "Consumo Defensivo",       "color": "#F87171"},
    "JPM":  {"empresa": "JPMorgan Chase", "sector": "Finanzas Digitales",      "color": "#FBBF24"},
    "SPY":  {"empresa": "S&P 500 ETF",    "sector": "Benchmark",               "color": "#64748B"},
}


def _get_dates() -> tuple:
    start = st.session_state.get("global_start")
    end   = st.session_state.get("global_end")
    return (str(start) if start else None, str(end) if end else None)


def _get(path: str, params: dict = None):
    try:
        r = httpx.get(f"{BACKEND_URL}{path}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        st.error(f"Error {e.response.status_code} en {path}: {e.response.text[:200]}")
        return None
    except Exception as e:
        st.error(f"Sin conexión al backend ({BACKEND_URL}): {e}")
        return None


def _post(path: str, body: dict):
    try:
        r = httpx.post(f"{BACKEND_URL}{path}", json=body, timeout=60)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        st.error(f"Error {e.response.status_code} en {path}: {e.response.text[:200]}")
        return None
    except Exception as e:
        st.error(f"Sin conexión al backend ({BACKEND_URL}): {e}")
        return None


def _delete(path: str):
    try:
        r = httpx.delete(f"{BACKEND_URL}{path}", timeout=15)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        st.error(f"Error {e.response.status_code} en {path}: {e.response.text[:200]}")
        return None
    except Exception as e:
        st.error(f"Sin conexión al backend ({BACKEND_URL}): {e}")
        return None


# ── Datos de mercado ───────────────────────────────────────────────────────────

@st.cache_data(ttl=1800)
def fetch_activos() -> Optional[List[Dict]]:
    return _get("/activos")


@st.cache_data(ttl=1800)
def fetch_precios(ticker: str, start: str = None, end: str = None) -> Optional[Dict]:
    if not start or not end:
        start, end = _get_dates()
    params = {}
    if start: params["start"] = start
    if end:   params["end"]   = end
    return _get(f"/precios/{ticker}", params=params)


@st.cache_data(ttl=1800)
def fetch_rendimientos(ticker: str, start: str = None, end: str = None) -> Optional[Dict]:
    if not start or not end:
        start, end = _get_dates()
    params = {}
    if start: params["start"] = start
    if end:   params["end"]   = end
    return _get(f"/rendimientos/{ticker}", params=params)


@st.cache_data(ttl=1800)
def fetch_indicadores(ticker: str, start: str = None, end: str = None) -> Optional[Dict]:
    if not start or not end:
        start, end = _get_dates()
    params = {}
    if start: params["start"] = start
    if end:   params["end"]   = end
    return _get(f"/indicadores/{ticker}", params=params)


@st.cache_data(ttl=1800)
def fetch_capm(start: str = None, end: str = None) -> Optional[List[Dict]]:
    return _get("/capm")


@st.cache_data(ttl=1800)
def fetch_macro() -> Optional[Dict]:
    return _get("/macro")


@st.cache_data(ttl=1800)
def fetch_alertas(start: str = None, end: str = None) -> Optional[List[Dict]]:
    return _get("/alertas")


@st.cache_data(ttl=1800)
def fetch_garch(ticker: str, start: str = None, end: str = None) -> Optional[Dict]:
    return _get(f"/garch/{ticker}")


def fetch_var(ticker: str, confidence: float = 0.95, simulations: int = 10000,
              start: str = None, end: str = None) -> Optional[Dict]:
    return _post("/var", {
        "ticker":      ticker,
        "confidence":  confidence,
        "simulations": simulations,
    })


@st.cache_data(ttl=1800)
def fetch_frontera(tickers: List[str], weights: List[float],
                   start: str = None, end: str = None) -> Optional[Dict]:
    return _post("/frontera-eficiente", {
        "tickers": tickers,
        "weights": weights,
    })


# ── IA / Groq ──────────────────────────────────────────────────────────────────

def fetch_consulta_ia(mensaje: str, historial: list,
                      contexto_ticker: str = None) -> Optional[Dict]:
    historial_clean = [
        {"role":    m.get("role")    if isinstance(m, dict) else m.role,
         "content": m.get("content") if isinstance(m, dict) else m.content}
        for m in historial
    ]
    return _post("/consulta-ia", {
        "mensaje":   mensaje,
        "historial": historial_clean,
    })


# ── Renta fija ─────────────────────────────────────────────────────────────────

@st.cache_data(ttl=86400)
def fetch_curva_rendimiento() -> Optional[Dict]:
    return _get("/curva-rendimiento")


def fetch_bono(face_value: float, coupon_rate: float, maturity_years: int,
               frequency: int, ytm: float) -> Optional[Dict]:
    return _post("/bono/duracion", {
        "face_value":     face_value,
        "coupon_rate":    coupon_rate,
        "maturity_years": maturity_years,
        "frequency":      frequency,
        "ytm":            ytm,
    })


# ── Opciones ───────────────────────────────────────────────────────────────────

def fetch_opcion(S: float, K: float, T: float, r: float, sigma: float,
                 tipo: str, market_price: float = None) -> Optional[Dict]:
    body = {"S": S, "K": K, "T": T, "r": r, "sigma": sigma, "tipo": tipo}
    if market_price is not None:
        body["market_price"] = market_price
    return _post("/opcion/precio", body)


def fetch_opcion_curvas(S: float, K: float, T: float, r: float,
                        sigma: float, tipo: str) -> Optional[Dict]:
    return _post("/opcion/curvas", {
        "S": S, "K": K, "T": T, "r": r, "sigma": sigma, "tipo": tipo,
    })


# ── Stress Testing ─────────────────────────────────────────────────────────────

def fetch_stress(tickers: List[str], weights: List[float],
                 scenarios: List[Dict] = None) -> Optional[Any]:
    return _post("/stress", {
        "tickers":   tickers,
        "weights":   weights,
        "scenarios": scenarios or [],
    })


# ── ML / Predicción ────────────────────────────────────────────────────────────

def fetch_predict(ticker: str) -> Optional[Dict]:
    return _post("/predict", {"ticker": ticker})


def fetch_predict_history(ticker: str = None, limit: int = 20) -> Optional[List[Dict]]:
    params = {"limit": limit}
    if ticker:
        params["ticker"] = ticker
    return _get("/predict/history", params=params)


# ── Portafolios CRUD ───────────────────────────────────────────────────────────

def fetch_portafolios() -> Optional[List[Dict]]:
    return _get("/portafolios")


def crear_portafolio(name: str, tickers: List[str], weights: Dict,
                     notes: str = None) -> Optional[Dict]:
    return _post("/portafolios", {
        "name":    name,
        "tickers": tickers,
        "weights": weights,
        "notes":   notes,
    })


def eliminar_portafolio(portfolio_id: int) -> bool:
    result = _delete(f"/portafolios/{portfolio_id}")
    return result is not None