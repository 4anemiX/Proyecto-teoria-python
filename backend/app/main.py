from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import VaRRequest, PortfolioRequest
from .services import (DataService, TechnicalIndicators, RiskCalculator,
                        PortfolioAnalyzer, AlertasService, MacroService, PORTFOLIO, TICKERS_ALL)
from .dependencies import (get_data_service, get_tech_indicators, get_risk_calculator,
                            get_portfolio_analyzer, get_alertas_service, get_macro_service)

app = FastAPI(
    title="RiskLab API — Economía Digital y Servicios Globales",
    description="Motor de cálculo de riesgo financiero · USTA · Teoría del Riesgo",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Health check ────────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "RiskLab API activa — Economía Digital y Servicios Globales"}

# ── Activos ─────────────────────────────────────────────────────
@app.get("/activos", tags=["Datos"])
async def get_activos(svc: DataService = Depends(get_data_service)):
    try:
        return svc.get_asset_info()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

# ── Precios OHLCV ────────────────────────────────────────────────
@app.get("/precios/{ticker}", tags=["Datos"])
async def get_precios(ticker: str, svc: DataService = Depends(get_data_service)):
    ticker = ticker.upper()
    if ticker not in TICKERS_ALL:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker} no está en el portafolio")
    try:
        df = svc.get_prices(ticker)
        fechas = [str(d)[:10] for d in df.index]
        return {
            "ticker": ticker,
            "fechas": fechas,
            "open":   [round(float(v), 4) for v in df["Open"]],
            "high":   [round(float(v), 4) for v in df["High"]],
            "low":    [round(float(v), 4) for v in df["Low"]],
            "close":  [round(float(v), 4) for v in df["Close"]],
            "volume": [int(v) for v in df["Volume"]],
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

# ── Rendimientos ─────────────────────────────────────────────────
@app.get("/rendimientos/{ticker}", tags=["Análisis"])
async def get_rendimientos(ticker: str,
                           svc: DataService = Depends(get_data_service),
                           risk: RiskCalculator = Depends(get_risk_calculator)):
    ticker = ticker.upper()
    if ticker not in TICKERS_ALL:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker} no encontrado")
    try:
        df = svc.get_prices(ticker)
        stats = risk.returns_stats(df)
        return {"ticker": ticker, **stats}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

# ── Indicadores técnicos ─────────────────────────────────────────
@app.get("/indicadores/{ticker}", tags=["Análisis"])
async def get_indicadores(ticker: str,
                           svc: DataService = Depends(get_data_service),
                           tech: TechnicalIndicators = Depends(get_tech_indicators)):
    ticker = ticker.upper()
    if ticker not in TICKERS_ALL:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker} no encontrado")
    try:
        df = svc.get_prices(ticker)
        result = tech.compute(df)
        return {"ticker": ticker, **result}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

# ── CAPM ──────────────────────────────────────────────────────────
@app.get("/capm", tags=["Análisis"])
async def get_capm(pa: PortfolioAnalyzer = Depends(get_portfolio_analyzer)):
    try:
        return pa.capm()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

# ── Macro ─────────────────────────────────────────────────────────
@app.get("/macro", tags=["Macro"])
async def get_macro(ms: MacroService = Depends(get_macro_service)):
    try:
        return ms.get_macro()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

# ── Alertas ───────────────────────────────────────────────────────
@app.get("/alertas", tags=["Señales"])
async def get_alertas(svc: DataService = Depends(get_data_service),
                      alerta_svc: AlertasService = Depends(get_alertas_service)):
    try:
        results = []
        for ticker in PORTFOLIO:
            df = svc.get_prices(ticker)
            results.append(alerta_svc.generate(ticker, df))
        return results
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

# ── VaR ───────────────────────────────────────────────────────────
@app.post("/var", tags=["Riesgo"])
async def get_var(req: VaRRequest,
                  svc: DataService = Depends(get_data_service),
                  risk: RiskCalculator = Depends(get_risk_calculator)):
    ticker = req.ticker.upper()
    if ticker not in TICKERS_ALL:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker} no encontrado")
    try:
        df = svc.get_prices(ticker)
        result = risk.compute_var(df, req.confidence, req.simulations)
        return {"ticker": ticker, **result}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

# ── Frontera eficiente ────────────────────────────────────────────
@app.post("/frontera-eficiente", tags=["Portafolio"])
async def get_frontera(req: PortfolioRequest,
                        pa: PortfolioAnalyzer = Depends(get_portfolio_analyzer)):
    for t in req.tickers:
        if t.upper() not in TICKERS_ALL:
            raise HTTPException(status_code=400, detail=f"Ticker {t} no válido")
    try:
        return pa.efficient_frontier([t.upper() for t in req.tickers], req.weights)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))