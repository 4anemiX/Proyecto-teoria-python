from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any

# ── Request models ──────────────────────────────────────────────

class VaRRequest(BaseModel):
    ticker: str = Field(..., description="Ticker del activo")
    confidence: float = Field(0.95, ge=0.80, le=0.99, description="Nivel de confianza")
    simulations: int = Field(10000, ge=1000, le=100000, description="Simulaciones Montecarlo")

class PortfolioRequest(BaseModel):
    tickers: List[str] = Field(..., description="Lista de tickers")
    weights: List[float] = Field(..., description="Pesos del portafolio (deben sumar 1.0)")

    @field_validator("weights")
    @classmethod
    def weights_must_sum_one(cls, v: List[float]) -> List[float]:
        if abs(sum(v) - 1.0) > 1e-4:
            raise ValueError(f"Los pesos deben sumar 1.0, suma actual: {sum(v):.4f}")
        return v

# ── Response models ─────────────────────────────────────────────

class AssetInfo(BaseModel):
    ticker: str
    empresa: str
    sector: str
    precio_actual: float
    variacion_diaria: float

class PriceData(BaseModel):
    ticker: str
    fechas: List[str]
    open: List[float]
    high: List[float]
    low: List[float]
    close: List[float]
    volume: List[float]

class ReturnsData(BaseModel):
    ticker: str
    fechas: List[str]
    simples: List[float]
    logaritmicos: List[float]
    media: float
    std: float
    skewness: float
    kurtosis: float
    jarque_bera_stat: float
    jarque_bera_pval: float
    shapiro_stat: float
    shapiro_pval: float

class IndicatorsData(BaseModel):
    ticker: str
    fechas: List[str]
    close: List[float]
    sma: List[Optional[float]]
    ema: List[Optional[float]]
    bb_upper: List[Optional[float]]
    bb_lower: List[Optional[float]]
    bb_mid: List[Optional[float]]
    rsi: List[Optional[float]]
    macd: List[Optional[float]]
    macd_signal: List[Optional[float]]
    stoch_k: List[Optional[float]]
    stoch_d: List[Optional[float]]

class CAPMData(BaseModel):
    ticker: str
    beta: float
    alpha: float
    r_squared: float
    expected_return: float
    risk_free_rate: float
    market_return: float

class MacroData(BaseModel):
    risk_free_rate: float
    sp500_return: float
    vix: float
    usdcop: float
    eurusd: float
    tnx: float

class AlertData(BaseModel):
    ticker: str
    rsi_signal: str
    macd_signal: str
    bb_signal: str
    sma_cross: str
    stoch_signal: str
    overall: str

class VaRData(BaseModel):
    ticker: str
    confidence: float
    var_parametric: float
    var_historical: float
    var_montecarlo: float
    cvar: float
    kupiec_stat: float
    kupiec_pval: float

class FrontierData(BaseModel):
    volatilities: List[float]
    returns: List[float]
    min_var_weights: Dict[str, float]
    min_var_return: float
    min_var_vol: float
    max_sharpe_weights: Dict[str, float]
    max_sharpe_return: float
    max_sharpe_vol: float
    max_sharpe_ratio: float

# ── Modelos para el Asistente IA ────────────────────────────────

class MensajeChat(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=4000)

class ConsultaIARequest(BaseModel):
    mensaje: str = Field(..., min_length=3, max_length=1000, description="Pregunta del usuario")
    historial: List[MensajeChat] = Field(default=[], max_length=20, description="Historial de la conversación")
    contexto_ticker: Optional[str] = Field(None, description="Ticker activo en pantalla, si aplica")

    @field_validator("mensaje")
    @classmethod
    def mensaje_no_vacio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El mensaje no puede estar vacío")
        return v.strip()

class ConsultaIAResponse(BaseModel):
    respuesta: str
    ticker_mencionado: Optional[str] = None
    tokens_usados: Optional[int] = None