from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Annotated

from .config import get_settings, Settings
from .models import PortfolioRequest, VaRResponse, CAPMResponse, IndicadoresResponse, MacroResponse
from .dependencies import get_data_service, get_rf_rate
from . import services

app = FastAPI(
    title="RiskLab API",
    description="Backend de análisis de riesgo financiero - Portafolio Economía Digital",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "RiskLab API v1.0 — Teoría del Riesgo USTA"}

@app.get("/activos")
def get_activos(settings: Annotated[Settings, Depends(get_settings)]):
    portfolio = [
        {"ticker": "ACN",  "empresa": "Accenture",      "sector": "Consultoría Tecnológica"},
        {"ticker": "MSFT", "empresa": "Microsoft",       "sector": "Cloud / IA"},
        {"ticker": "NVDA", "empresa": "NVIDIA",          "sector": "Semiconductores / IA"},
        {"ticker": "KO",   "empresa": "Coca-Cola",       "sector": "Consumo Defensivo"},
        {"ticker": "JPM",  "empresa": "JPMorgan Chase",  "sector": "Finanzas Digitales"},
        {"ticker": "SPY",  "empresa": "S&P 500 ETF",     "sector": "Benchmark"},
    ]
    return {"portafolio": portfolio, "benchmark": settings.benchmark}

@app.get("/precios/{ticker}")
def get_precios(ticker: str, period: str = "1y"):
    try:
        df = services.get_prices([ticker.upper()], period=period)
        col = ticker.upper()
        if col not in df.columns:
            col = df.columns[0]
        prices = df[col].dropna()
        return {
            "ticker": ticker.upper(),
            "fechas": [str(d.date()) for d in prices.index],
            "precios": [round(float(p), 2) for p in prices.values],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/rendimientos/{ticker}")
def get_rendimientos(ticker: str, period: str = "2y"):
    try:
        df = services.get_returns([ticker.upper()], period=period)
        col = ticker.upper()
        if col not in df.columns:
            col = df.columns[0]
        rets = df[col].dropna()
        return {
            "ticker": ticker.upper(),
            "fechas": [str(d.date()) for d in rets.index],
            "rendimientos": [round(float(r), 6) for r in rets.values],
            "media": round(float(rets.mean()), 6),
            "std": round(float(rets.std()), 6),
            "skewness": round(float(rets.skew()), 4),
            "kurtosis": round(float(rets.kurtosis()), 4),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/indicadores/{ticker}", response_model=IndicadoresResponse)
def get_indicadores(ticker: str):
    try:
        return services.compute_indicators(ticker.upper())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/var", response_model=VaRResponse)
def calc_var(req: PortfolioRequest, settings: Annotated[Settings, Depends(get_settings)]):
    try:
        return services.compute_var(req.tickers, req.weights, req.confidence_level)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/capm/{ticker}", response_model=CAPMResponse)
def calc_capm(ticker: str, rf: Annotated[float, Depends(get_rf_rate)]):
    try:
        return services.compute_capm(ticker.upper(), rf)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/frontera-eficiente")
def calc_frontera(req: PortfolioRequest):
    try:
        return services.compute_efficient_frontier(req.tickers, n_portfolios=2000)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/garch/{ticker}")
def calc_garch(ticker: str):
    try:
        return services.compute_garch(ticker.upper())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/alertas")
def get_alertas():
    try:
        tickers = ["ACN", "MSFT", "NVDA", "KO", "JPM"]
        alertas = [services.compute_indicators(t) for t in tickers]
        return {"alertas": alertas}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/macro", response_model=MacroResponse)
def get_macro_data(settings: Annotated[Settings, Depends(get_settings)]):
    return services.get_macro(settings.fred_api_key)