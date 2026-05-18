import sys
import os

# ── Apuntar al backend para importar sus módulos directamente ──────────────────
_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend"))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

# ── Cargar .env del backend ANTES de importar settings ────────────────────────
from dotenv import load_dotenv
_ENV_PATH = os.path.join(_BACKEND, ".env")
load_dotenv(dotenv_path=_ENV_PATH, override=True)

import httpx
import streamlit as st
from typing import Dict, List, Any, Optional

from app.services import (DataService, TechnicalIndicators, RiskCalculator,
                          PortfolioAnalyzer, AlertasService, MacroService)
from app.config import settings
from app.database import init_db

# Garantizar que las tablas existen aunque el backend FastAPI no haya arrancado
init_db()

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


def _get_dates() -> tuple:
    """Lee las fechas globales desde session_state y las devuelve como strings."""
    start = st.session_state.get("global_start")
    end   = st.session_state.get("global_end")
    return (str(start) if start else None, str(end) if end else None)


# ── Datos de mercado ───────────────────────────────────────────────────────────

@st.cache_data(ttl=1800)
def fetch_activos() -> Optional[List[Dict]]:
    try:
        return _data_svc.get_asset_info()
    except Exception as e:
        st.error(f"Error al obtener activos: {e}")
        return None


@st.cache_data(ttl=1800)
def fetch_precios(ticker: str, start: str = None, end: str = None) -> Optional[Dict]:
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


# ── IA / Groq ─────────────────────────────────────────────────────────────────

def fetch_consulta_ia(mensaje: str, historial: list,
                      contexto_ticker: str = None) -> Optional[Dict]:
    """Llama a Groq directamente sin pasar por el backend HTTP."""
    api_key = settings.get_groq_key()
    if not api_key:
        st.error("GROQ_API_KEY no configurada en backend/.env")
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
        body   = response.json()
        texto  = body["choices"][0]["message"]["content"]
        tokens = body.get("usage", {}).get("completion_tokens")

        tickers_portfolio = ["ACN", "MSFT", "NVDA", "KO", "JPM", "SPY"]
        ticker_encontrado = next(
            (t for t in tickers_portfolio if t in mensaje.upper()), None
        )
        return {
            "respuesta":         texto,
            "ticker_mencionado": ticker_encontrado,
            "tokens_usados":     tokens,
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


# ── Renta fija ─────────────────────────────────────────────────────────────────

@st.cache_data(ttl=86400)
def fetch_curva_rendimiento() -> Optional[Dict]:
    try:
        from app.services.fixed_income import YieldCurve
        from app.database import SessionLocal
        from app.models.db_models import MacroCache
        import requests as req_lib
        from datetime import datetime, timedelta

        # Leer clave desde el .env del backend con ruta absoluta
        fred_key = os.getenv("FRED_API_KEY", "")
        if not fred_key or fred_key in ("demo", '""', "''"):
            st.error("FRED_API_KEY vacía o inválida — revisa backend/.env")
            return None

        SERIES = {
            "DGS3MO": 0.25, "DGS6MO": 0.5,
            "DGS1":   1.0,  "DGS2":   2.0,
            "DGS5":   5.0,  "DGS10":  10.0,
            "DGS30":  30.0,
        }
        TTL_HOURS  = 24
        maturities = []
        yields_pct = []

        db = SessionLocal()
        try:
            for series_id, maturity in SERIES.items():
                cached = db.query(MacroCache).filter(
                    MacroCache.series_id == series_id
                ).first()

                # Usar caché si está vigente
                if (cached and
                        datetime.utcnow() - cached.fetched_at < timedelta(hours=TTL_HOURS)):
                    maturities.append(maturity)
                    yields_pct.append(cached.value)
                    continue

                # Descargar desde FRED
                try:
                    url = (
                        f"https://api.stlouisfed.org/fred/series/observations"
                        f"?series_id={series_id}&api_key={fred_key}"
                        f"&file_type=json&sort_order=desc&limit=1"
                    )
                    resp = req_lib.get(url, timeout=10)
                    resp.raise_for_status()
                    val_str = resp.json()["observations"][0]["value"]
                    if val_str == ".":
                        continue
                    val = float(val_str)

                    # Guardar / actualizar caché
                    if cached:
                        cached.value      = val
                        cached.fetched_at = datetime.utcnow()
                    else:
                        db.add(MacroCache(series_id=series_id, value=val, source="FRED"))
                    db.commit()
                    maturities.append(maturity)
                    yields_pct.append(val)

                except Exception as e:
                    st.warning(f"No se pudo descargar {series_id}: {e}")
                    if cached:   # usar caché vieja si existe
                        maturities.append(maturity)
                        yields_pct.append(cached.value)
        finally:
            db.close()

        if len(maturities) < 4:
            st.error(
                f"Solo se obtuvieron {len(maturities)} series de FRED "
                f"(mínimo 4). Revisa la conexión o la FRED_API_KEY."
            )
            return None

        yc        = YieldCurve()
        ns_params = yc.fit_nelson_siegel(maturities, yields_pct)
        curve_pts = yc.curve_points(n=100)
        shape     = yc.curve_shape()

        return {
            "maturities_obs":     maturities,
            "yields_obs_pct":     yields_pct,
            "nelson_siegel":      ns_params,
            "curve_points":       curve_pts,
            "shape":              shape,
            "shape_interpretation": {
                "normal":   "La curva tiene pendiente positiva: el mercado espera crecimiento.",
                "invertida":"La curva está invertida: señal histórica de recesión.",
                "plana":    "La curva plana refleja incertidumbre sobre el ciclo económico.",
            }.get(shape, ""),
        }

    except Exception as e:
        st.error(f"Error inesperado en curva de rendimiento: {e}")
        return None


@st.cache_data(ttl=3600)
def fetch_bono(face_value: float, coupon_rate: float, maturity_years: int,
               frequency: int, ytm: float) -> Optional[Dict]:
    try:
        from app.services.fixed_income import Bond
        bond = Bond(
            face_value=face_value, coupon_rate=coupon_rate,
            maturity_years=maturity_years, frequency=frequency,
        )
        return bond.full_metrics(ytm=ytm)
    except Exception as e:
        st.error(f"Error al calcular bono: {e}")
        return None


# ── Opciones ───────────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def fetch_opcion(S: float, K: float, T: float, r: float, sigma: float,
                 tipo: str, market_price: float = None) -> Optional[Dict]:
    try:
        from app.services.options import OptionPricer
        pricer = OptionPricer(S=S, K=K, T=T, r=r, sigma=sigma, tipo=tipo)
        result = pricer.full_result()
        if market_price is not None:
            result["implied_vol"] = pricer.implied_volatility(market_price)
        return result
    except Exception as e:
        st.error(f"Error al valorar opción: {e}")
        return None


@st.cache_data(ttl=60)
def fetch_opcion_curvas(S: float, K: float, T: float, r: float,
                        sigma: float, tipo: str) -> Optional[Dict]:
    try:
        from app.services.options import OptionPricer
        pricer = OptionPricer(S=S, K=K, T=T, r=r, sigma=sigma, tipo=tipo)
        return {
            "payoff_curve": pricer.payoff_curve(),
            "delta_curve":  pricer.delta_curve(),
        }
    except Exception as e:
        st.error(f"Error al obtener curvas de opción: {e}")
        return None


# ── Stress Testing ─────────────────────────────────────────────────────────────

def fetch_stress(tickers: List[str], weights: List[float],
                 scenarios: List[Dict] = None) -> Optional[Any]:
    try:
        from app.services.stress import StressTester
        from app.services import DataService, PortfolioAnalyzer

        svc      = DataService()
        pa       = PortfolioAnalyzer(svc)
        capm_data = pa.capm()
        betas    = {d["ticker"]: d["beta"] for d in capm_data if "error" not in d}

        current_prices, base_vols = {}, {}
        for t in tickers:
            try:
                df    = svc.get_prices(t, years=1)
                close = df["Close"].dropna()
                current_prices[t] = float(close.iloc[-1])
                ret   = close.pct_change().dropna()
                base_vols[t]      = float(ret.std())
            except Exception:
                current_prices[t] = 100.0
                base_vols[t]      = 0.02

        tester = StressTester(
            tickers=tickers, weights=weights, betas=betas,
            current_prices=current_prices, base_vol=base_vols, rf=0.05,
        )
        if not scenarios:
            return tester.run_all_scenarios()
        return {"results": [tester.apply(s) for s in scenarios]}

    except Exception as e:
        st.error(f"Error en stress test: {e}")
        return None


# ── ML / Predicción ────────────────────────────────────────────────────────────

def fetch_predict(ticker: str) -> Optional[Dict]:
    try:
        from app.ml.predictor import get_predictor
        svc       = DataService()
        predictor = get_predictor()
        df        = svc.get_prices(ticker, years=1)
        close     = df["Close"].dropna()
        result    = predictor.predict(ticker, close)
        if "error" in result:
            st.error(result["error"])
            return None
        return result
    except Exception as e:
        st.error(f"Error en predicción ML: {e}")
        return None


def fetch_predict_history(ticker: str = None, limit: int = 20) -> Optional[List[Dict]]:
    try:
        from app.database import SessionLocal
        from app.models.db_models import PredictionLog
        db = SessionLocal()
        try:
            q = db.query(PredictionLog).order_by(PredictionLog.timestamp.desc())
            if ticker:
                q = q.filter(PredictionLog.ticker == ticker.upper())
            records = q.limit(limit).all()
            return [
                {
                    "id":            r.id,
                    "model_version": r.model_version,
                    "timestamp":     str(r.timestamp),
                    "ticker":        r.ticker,
                    "prediction":    r.prediction,
                    "label":         r.prediction_label,
                    "confidence":    r.confidence,
                }
                for r in records
            ]
        finally:
            db.close()
    except Exception as e:
        st.error(f"Error al obtener historial de predicciones: {e}")
        return None


# ── Portafolios CRUD ───────────────────────────────────────────────────────────

def fetch_portafolios() -> Optional[List[Dict]]:
    try:
        from app.database import SessionLocal
        from app.models.db_models import Portfolio
        db = SessionLocal()
        try:
            portfolios = db.query(Portfolio).order_by(Portfolio.created_at.desc()).all()
            return [
                {
                    "id":         p.id,
                    "name":       p.name,
                    "tickers":    p.tickers,
                    "weights":    p.weights,
                    "created_at": str(p.created_at),
                    "notes":      p.notes,
                }
                for p in portfolios
            ]
        finally:
            db.close()
    except Exception as e:
        st.error(f"Error al listar portafolios: {e}")
        return None


def crear_portafolio(name: str, tickers: List[str], weights: Dict,
                     notes: str = None) -> Optional[Dict]:
    try:
        from app.database import SessionLocal
        from app.models.db_models import Portfolio
        db = SessionLocal()
        try:
            p = Portfolio(name=name, tickers=tickers, weights=weights, notes=notes)
            db.add(p)
            db.commit()
            db.refresh(p)
            return {"id": p.id, "name": p.name}
        finally:
            db.close()
    except Exception as e:
        st.error(f"Error al crear portafolio: {e}")
        return None


def eliminar_portafolio(portfolio_id: int) -> bool:
    try:
        from app.database import SessionLocal
        from app.models.db_models import Portfolio
        db = SessionLocal()
        try:
            p = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
            if not p:
                return False
            db.delete(p)
            db.commit()
            return True
        finally:
            db.close()
    except Exception as e:
        st.error(f"Error al eliminar portafolio: {e}")
        return False