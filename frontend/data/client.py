import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

import httpx
import streamlit as st
from typing import Dict, List, Any, Optional

from app.services import (DataService, TechnicalIndicators, RiskCalculator,
                          PortfolioAnalyzer, AlertasService, MacroService)
from app.config import settings

_data_svc  = DataService()
_tech      = TechnicalIndicators()
_risk      = RiskCalculator()
_portfolio = PortfolioAnalyzer(_data_svc)
_alertas   = AlertasService(_tech)
_macro     = MacroService()

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


def _get_dates() -> tuple[str | None, str | None]:
    """Lee las fechas globales desde session_state y las devuelve como strings."""
    start = st.session_state.get("global_start")
    end   = st.session_state.get("global_end")
    return (str(start) if start else None, str(end) if end else None)


@st.cache_data(ttl=1800)
def fetch_activos() -> Optional[List[Dict]]:
    try:
        return _data_svc.get_asset_info()
    except Exception as e:
        st.error(f"Error al obtener activos: {e}")
        return None


@st.cache_data(ttl=1800)
def fetch_precios(ticker: str, start: str = None, end: str = None) -> Optional[Dict]:
    # Si no se pasan fechas explícitas, leer del session_state global
    if not start or not end:
        start, end = _get_dates()
    try:
        df = _data_svc.get_prices(ticker, start=start, end=end)
        return {
            "ticker": ticker,
            "fechas": [str(d)[:10] for d in df.index],
            "open":   [round(float(v), 4) for v in df["Open"]],
            "high":   [round(float(v), 4) for v in df["High"]],
            "low":    [round(float(v), 4) for v in df["Low"]],
            "close":  [round(float(v), 4) for v in df["Close"]],
            "volume": [int(v) for v in df["Volume"]],
        }
    except Exception as e:
        st.error(f"Error al obtener precios de {ticker}: {e}")
        return None


@st.cache_data(ttl=1800)
def fetch_rendimientos(ticker: str, start: str = None, end: str = None) -> Optional[Dict]:
    if not start or not end:
        start, end = _get_dates()
    try:
        df = _data_svc.get_prices(ticker, start=start, end=end)
        return _risk.returns_stats(df)
    except Exception as e:
        st.error(f"Error al obtener rendimientos de {ticker}: {e}")
        return None


@st.cache_data(ttl=1800)
def fetch_indicadores(ticker: str, start: str = None, end: str = None) -> Optional[Dict]:
    if not start or not end:
        start, end = _get_dates()
    try:
        df = _data_svc.get_prices(ticker, start=start, end=end)
        return _tech.compute(df)
    except Exception as e:
        st.error(f"Error al obtener indicadores de {ticker}: {e}")
        return None


@st.cache_data(ttl=1800)
def fetch_capm(start: str = None, end: str = None) -> Optional[List[Dict]]:
    if not start or not end:
        start, end = _get_dates()
    try:
        return _portfolio.capm(start=start, end=end)
    except Exception as e:
        st.error(f"Error al obtener CAPM: {e}")
        return None


@st.cache_data(ttl=1800)
def fetch_macro() -> Optional[Dict]:
    try:
        return _macro.get_macro()
    except Exception as e:
        st.error(f"Error al obtener macro: {e}")
        return None


@st.cache_data(ttl=1800)
def fetch_alertas(start: str = None, end: str = None) -> Optional[List[Dict]]:
    if not start or not end:
        start, end = _get_dates()
    try:
        results = []
        for ticker in TICKERS:
            df = _data_svc.get_prices(ticker, start=start, end=end)
            results.append(_alertas.generate(ticker, df))
        return results
    except Exception as e:
        st.error(f"Error al obtener alertas: {e}")
        return None


@st.cache_data(ttl=1800)
def fetch_var(ticker: str, confidence: float = 0.95, simulations: int = 10000,
              start: str = None, end: str = None) -> Optional[Dict]:
    if not start or not end:
        start, end = _get_dates()
    try:
        df = _data_svc.get_prices(ticker, start=start, end=end)
        return _risk.compute_var(df, confidence, simulations)
    except Exception as e:
        st.error(f"Error al calcular VaR de {ticker}: {e}")
        return None


@st.cache_data(ttl=1800)
def fetch_garch(ticker: str, start: str = None, end: str = None) -> Optional[Dict]:
    if not start or not end:
        start, end = _get_dates()
    try:
        df = _data_svc.get_prices(ticker, start=start, end=end)
        return _risk.compute_garch(df)
    except Exception as e:
        st.error(f"Error al calcular GARCH de {ticker}: {e}")
        return None


@st.cache_data(ttl=1800)
def fetch_frontera(tickers: List[str], weights: List[float],
                   start: str = None, end: str = None) -> Optional[Dict]:
    if not start or not end:
        start, end = _get_dates()
    try:
        return _portfolio.efficient_frontier(tickers, weights)
    except Exception as e:
        st.error(f"Error al calcular frontera eficiente: {e}")
        return None


def fetch_consulta_ia(mensaje: str, historial: list,
                      contexto_ticker: str = None) -> Optional[Dict]:
    """Llama a Groq directamente sin pasar por el backend HTTP."""
    api_key = settings.get_groq_key()
    if not api_key:
        st.error("GROQ_API_KEY no configurada en los secrets de Streamlit.")
        return None

    system_prompt = (
        "Eres el asistente de análisis de riesgo financiero del proyecto DataRisk, "
        "desarrollado en la Universidad Santo Tomás (USTA Bogotá) para la materia Teoría del Riesgo "
        "con el profesor Javier Mauricio Sierra. "
        "El portafolio contiene: ACN, MSFT, NVDA, KO, JPM y SPY. "
        "Responde siempre en español, de forma pedagógica y concisa. "
        "Máximo 5 oraciones por respuesta. No uses listas ni markdown."
    )

    messages = [{"role": "system", "content": system_prompt}]
    for m in historial:
        role    = m.get("role")    if isinstance(m, dict) else m.role
        content = m.get("content") if isinstance(m, dict) else m.content
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": mensaje})

    try:
        response = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": messages,
                "max_tokens": 400,
                "temperature": 0.7,
            },
            timeout=30,
        )
        response.raise_for_status()
        body  = response.json()
        texto = body["choices"][0]["message"]["content"]
        tokens = body.get("usage", {}).get("completion_tokens")

        tickers_portfolio = ["ACN", "MSFT", "NVDA", "KO", "JPM", "SPY"]
        ticker_encontrado = next(
            (t for t in tickers_portfolio if t in mensaje.upper()), None
        )

        return {
            "respuesta":        texto,
            "ticker_mencionado": ticker_encontrado,
            "tokens_usados":    tokens,
        }

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            st.error("Límite de requests excedido. Espera un momento.")
        else:
            st.error(f"Error API Groq: {e.response.text}")
        return None
    except Exception as e:
        st.error(f"Error al consultar IA: {e}")
        return None