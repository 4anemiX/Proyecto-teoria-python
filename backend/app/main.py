from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx

from .config import settings
from .models import VaRRequest, PortfolioRequest, ConsultaIARequest, ConsultaIAResponse
from .services import (DataService, TechnicalIndicators, RiskCalculator,
                        PortfolioAnalyzer, AlertasService, MacroService, PORTFOLIO, TICKERS_ALL)
from .dependencies import (get_data_service, get_tech_indicators, get_risk_calculator,
                            get_portfolio_analyzer, get_alertas_service, get_macro_service)

from sqlalchemy.orm import Session
import requests as req_lib
from datetime import datetime, timedelta
 
from .database import get_db, init_db
from .models.db_models import Asset, Price, Portfolio, PredictionLog, MacroCache, SignalLog
from .models.new_schemas import (
    YieldCurveRequest, BondRequest,
    OptionRequest, OptionResponse,
    StressRequest, StressScenario,
    PredictRequest, PredictResponse,
    PortfolioCreate, PortfolioResponse,
)
from .services.fixed_income import YieldCurve, Bond
from .services.options import OptionPricer
from .services.stress import StressTester
from .ml.predictor import get_predictor


app = FastAPI(
    title="DataRisk — Economía Digital y Servicios Globales",
    description="Motor de cálculo de riesgo financiero · USTA · Teoría del Riesgo · Python para APIs e IA",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    init_db()

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
                      alerta_svc: AlertasService = Depends(get_alertas_service),
                      db: Session = Depends(get_db)):
    try:
        results = []
        for ticker in PORTFOLIO:
            df = svc.get_prices(ticker)
            alerta = alerta_svc.generate(ticker, df)
            results.append(alerta)

            # Persistir en signals_log si hay señal activa
            señal = alerta.get("signal") or alerta.get("señal")
            if señal and señal not in ("Neutral", ""):
                asset = db.query(Asset).filter(Asset.ticker == ticker).first()
                if asset:
                    db.add(SignalLog(
                        asset_id=asset.id,
                        rule=str(alerta.get("rule", alerta.get("regla", "tecnica"))),
                        value=float(alerta.get("value", alerta.get("valor", 0.0)) or 0.0),
                        signal=señal,
                    ))
        db.commit()
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

# ── Portafolios (CRUD básico con SQLAlchemy) ──────────────────────────────
@app.post("/portafolios", tags=["Portafolios"])
async def crear_portafolio(req: PortfolioCreate, db: Session = Depends(get_db)):
    """Guarda un portafolio en SQLite."""
    portfolio = Portfolio(
        name=req.name,
        tickers=req.tickers,
        weights=req.weights,
        notes=req.notes,
    )
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return {
        "id": portfolio.id,
        "name": portfolio.name,
        "tickers": portfolio.tickers,
        "weights": portfolio.weights,
        "created_at": str(portfolio.created_at),
        "notes": portfolio.notes,
    }
 
 
@app.get("/portafolios", tags=["Portafolios"])
async def listar_portafolios(db: Session = Depends(get_db)):
    """Lista todos los portafolios guardados."""
    portfolios = db.query(Portfolio).order_by(Portfolio.created_at.desc()).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "tickers": p.tickers,
            "weights": p.weights,
            "created_at": str(p.created_at),
            "notes": p.notes,
        }
        for p in portfolios
    ]
 
 
@app.delete("/portafolios/{portfolio_id}", tags=["Portafolios"])
async def eliminar_portafolio(portfolio_id: int, db: Session = Depends(get_db)):
    """Elimina un portafolio por ID."""
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not p:
        raise HTTPException(status_code=404, detail=f"Portafolio {portfolio_id} no encontrado.")
    db.delete(p)
    db.commit()
    return {"message": f"Portafolio '{p.name}' eliminado."}

# ── Curva de rendimiento (FRED + Nelson-Siegel) ───────────────────────────────
@app.get("/curva-rendimiento", tags=["Renta Fija"])
async def get_curva_rendimiento(db: Session = Depends(get_db)):
    """
    Obtiene tasas de tesoros US desde FRED (con cache 24h en SQLite)
    y ajusta la curva Nelson-Siegel.
    """
    SERIES = {
        "DGS3MO": 0.25, "DGS6MO": 0.5,
        "DGS1": 1.0, "DGS2": 2.0, "DGS5": 5.0,
        "DGS10": 10.0, "DGS30": 30.0,
    }
    TTL_HOURS = 24
    maturities, yields_pct = [], []
 
    for series_id, maturity in SERIES.items():
        # Verificar caché
        cached = db.query(MacroCache).filter(MacroCache.series_id == series_id).first()
        if (cached and
                datetime.utcnow() - cached.fetched_at < timedelta(hours=TTL_HOURS)):
            maturities.append(maturity)
            yields_pct.append(cached.value)
            continue
 
        # Descargar desde FRED
        try:
            url = (
                f"https://api.stlouisfed.org/fred/series/observations"
                f"?series_id={series_id}&api_key={settings.fred_api_key}"
                f"&file_type=json&sort_order=desc&limit=1"
            )
            resp = req_lib.get(url, timeout=10)
            resp.raise_for_status()
            val_str = resp.json()["observations"][0]["value"]
            if val_str == ".":
                continue
            val = float(val_str)
 
            # Actualizar caché
            if cached:
                cached.value      = val
                cached.fetched_at = datetime.utcnow()
            else:
                db.add(MacroCache(series_id=series_id, value=val, source="FRED"))
            db.commit()
            maturities.append(maturity)
            yields_pct.append(val)
 
        except Exception as e:
            # Usar caché vieja si existe
            if cached:
                maturities.append(maturity)
                yields_pct.append(cached.value)
 
    if len(maturities) < 4:
        raise HTTPException(
            status_code=503,
            detail="Datos insuficientes de FRED. Verifica FRED_API_KEY."
        )
 
    yc = YieldCurve()
    ns_params = yc.fit_nelson_siegel(maturities, yields_pct)
    curve_pts  = yc.curve_points(n=100)
    shape      = yc.curve_shape()
 
    return {
        "maturities_obs": maturities,
        "yields_obs_pct": yields_pct,
        "nelson_siegel":  ns_params,
        "curve_points":   curve_pts,
        "shape":          shape,
        "shape_interpretation": {
            "normal":   "La curva tiene pendiente positiva: el mercado espera crecimiento.",
            "invertida":"La curva está invertida: señal histórica de recesión.",
            "plana":    "La curva plana refleja incertidumbre sobre el ciclo económico.",
        }.get(shape, ""),
    }
 
 
@app.post("/bono/duracion", tags=["Renta Fija"])
async def get_bond_metrics(req: BondRequest):
    """Calcula duración, convexidad y sensibilidad de precio de un bono sintético."""
    bond = Bond(
        face_value=req.face_value,
        coupon_rate=req.coupon_rate,
        maturity_years=req.maturity_years,
        frequency=req.frequency,
    )
    return bond.full_metrics(ytm=req.ytm)

# ── Opciones Black-Scholes ────────────────────────────────────────────────────
@app.post("/opcion/precio", tags=["Opciones"])
async def get_option_price(req: OptionRequest):
    """
    Valoración Black-Scholes de opción europea (call o put).
    Calcula precio, las 5 Greeks, verifica paridad put-call
    y opcionalmente la volatilidad implícita.
    """
    pricer = OptionPricer(
        S=req.S, K=req.K, T=req.T,
        r=req.r, sigma=req.sigma, tipo=req.tipo,
    )
    result = pricer.full_result()
 
    if req.market_price is not None:
        result["implied_vol"] = pricer.implied_volatility(req.market_price)
 
    return result
 
 
@app.post("/opcion/curvas", tags=["Opciones"])
async def get_option_curves(req: OptionRequest):
    """Curvas de payoff, precio y delta para visualización."""
    pricer = OptionPricer(
        S=req.S, K=req.K, T=req.T,
        r=req.r, sigma=req.sigma, tipo=req.tipo,
    )
    return {
        "payoff_curve": pricer.payoff_curve(),
        "delta_curve":  pricer.delta_curve(),
    }

# ── Stress Testing ────────────────────────────────────────────────────────────
@app.post("/stress", tags=["Stress Testing"])
async def get_stress(
    req: StressRequest,
    svc: DataService = Depends(get_data_service),
    pa:  PortfolioAnalyzer = Depends(get_portfolio_analyzer),
):
    """
    Aplica escenarios de estrés al portafolio.
    Si scenarios está vacío, ejecuta los 6 escenarios obligatorios.
    """
    tickers = [t.upper() for t in req.tickers]
    for t in tickers:
        if t not in TICKERS_ALL:
            raise HTTPException(status_code=400, detail=f"Ticker {t} no válido.")
 
    # Obtener betas y precios actuales
    capm_data = pa.capm()
    betas = {d["ticker"]: d["beta"] for d in capm_data if "error" not in d}
 
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
        tickers=tickers,
        weights=req.weights,
        betas=betas,
        current_prices=current_prices,
        base_vol=base_vols,
        rf=0.05,
    )
 
    if not req.scenarios:
        return tester.run_all_scenarios()
 
    results = [tester.apply(s.model_dump()) for s in req.scenarios]
    return {"results": results}

# ── Predicción ML ─────────────────────────────────────────────────────────────
@app.post("/predict", tags=["Machine Learning"])
async def predict_regime(
    req: PredictRequest,
    svc: DataService = Depends(get_data_service),
    db:  Session     = Depends(get_db),
):
    """
    Predice el régimen de mercado (alcista/bajista/lateral) para un ticker.
    Usa patrón Singleton para evitar recargar el modelo por request.
    Persiste cada predicción en SQLite.
    """
    predictor = get_predictor()
 
    try:
        df    = svc.get_prices(req.ticker, years=1)
        close = df["Close"].dropna()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Error al obtener precios: {e}")
 
    result = predictor.predict(req.ticker, close)
    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])
 
    # Persistir en BD
    log = PredictionLog(
        model_version=predictor.version,
        ticker=req.ticker,
        input_features=result["features_used"],
        prediction=float(result["regime_code"]),
        prediction_label=result["regime"],
        confidence=result["confidence"],
    )
    db.add(log)
    db.commit()
 
    return result
 
 
@app.get("/predict/history", tags=["Machine Learning"])
async def prediction_history(
    ticker: str | None = Query(None, description="Filtrar por ticker"),
    limit:  int        = Query(20, ge=1, le=100),
    db:     Session    = Depends(get_db),
):
    """Historial de predicciones guardadas en SQLite."""
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