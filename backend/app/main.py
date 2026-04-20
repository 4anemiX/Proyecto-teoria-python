from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx

from .config import settings
from .models import VaRRequest, PortfolioRequest, ConsultaIARequest, ConsultaIAResponse
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

@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "RiskLab API activa — Economía Digital y Servicios Globales"}

@app.get("/activos", tags=["Datos"])
async def get_activos(svc: DataService = Depends(get_data_service)):
    try:
        return svc.get_asset_info()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

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

@app.get("/capm", tags=["Análisis"])
async def get_capm(pa: PortfolioAnalyzer = Depends(get_portfolio_analyzer)):
    try:
        return pa.capm()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/macro", tags=["Macro"])
async def get_macro(ms: MacroService = Depends(get_macro_service)):
    try:
        return ms.get_macro()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

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

@app.post("/consulta-ia", response_model=ConsultaIAResponse, tags=["IA"])
async def consulta_ia(req: ConsultaIARequest):
    api_key = settings.groq_api_key
    if not api_key:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY no configurada")

    system_prompt = """Eres el asistente de análisis de riesgo financiero del proyecto DataRisk, \
desarrollado en la Universidad Santo Tomás (USTA Bogotá) para la materia Teoría del Riesgo \
con el profesor Javier Mauricio Sierra. \
El portafolio contiene: ACN, MSFT, NVDA, KO, JPM y SPY. \
Responde siempre en español, de forma pedagógica y concisa. \
Máximo 5 oraciones por respuesta. No uses listas ni markdown."""

    messages = [{"role": "system", "content": system_prompt}]
    for m in req.historial:
        messages.append({"role": m.role, "content": m.content})
    messages.append({"role": "user", "content": req.mensaje})

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
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
            )
        r.raise_for_status()
        body = r.json()
        texto = body["choices"][0]["message"]["content"]
        tokens = body.get("usage", {}).get("completion_tokens")

        tickers_portfolio = ["ACN", "MSFT", "NVDA", "KO", "JPM", "SPY"]
        ticker_encontrado = next(
            (t for t in tickers_portfolio if t in req.mensaje.upper()), None
        )

        return ConsultaIAResponse(
            respuesta=texto,
            ticker_mencionado=ticker_encontrado,
            tokens_usados=tokens,
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            raise HTTPException(status_code=503, detail="Límite de requests excedido. Espera un momento.")
        raise HTTPException(status_code=502, detail=f"Error API Groq: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))