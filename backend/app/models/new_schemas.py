from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any, Literal


# ── Renta fija ────────────────────────────────────────────────────────────────

class YieldCurveRequest(BaseModel):
    """Solicitud para ajuste de curva Nelson-Siegel."""
    maturities: List[float] = Field(
        default=[0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
        description="Vencimientos en años (mínimo 4 puntos)"
    )
    yields: List[float] = Field(
        ...,
        description="Tasas en % (ej: 5.20 para 5.20%)",
        min_length=4
    )

    @field_validator("yields")
    @classmethod
    def yields_positive(cls, v: List[float]) -> List[float]:
        if any(y < 0 for y in v):
            raise ValueError("Las tasas no pueden ser negativas.")
        return v

    @field_validator("maturities")
    @classmethod
    def maturities_positive(cls, v: List[float]) -> List[float]:
        if any(m <= 0 for m in v):
            raise ValueError("Los vencimientos deben ser positivos.")
        return v


class BondRequest(BaseModel):
    """Parámetros del bono sintético."""
    face_value:     float = Field(1000.0, gt=0,  description="Valor nominal")
    coupon_rate:    float = Field(0.05,   ge=0,  le=1.0, description="Tasa de cupón anual decimal")
    maturity_years: int   = Field(10,     ge=1,  le=50,  description="Vencimiento en años")
    frequency:      int   = Field(2,      ge=1,  le=12,  description="Pagos de cupón por año")
    ytm:            float = Field(0.05,   ge=0,  le=1.0, description="Rendimiento al vencimiento decimal")


# ── Opciones ──────────────────────────────────────────────────────────────────

class OptionRequest(BaseModel):
    """Parámetros para valoración Black-Scholes."""
    S:     float = Field(..., gt=0,   description="Precio actual del subyacente")
    K:     float = Field(..., gt=0,   description="Strike de la opción")
    T:     float = Field(..., gt=0,   description="Tiempo al vencimiento en años")
    r:     float = Field(..., ge=0,   description="Tasa libre de riesgo decimal")
    sigma: float = Field(..., gt=0,   le=5.0, description="Volatilidad anual decimal")
    tipo:  Literal["call", "put"] = Field("call", description="Tipo de opción")
    market_price: Optional[float] = Field(
        None, gt=0,
        description="Precio de mercado para calcular vol. implícita (opcional)"
    )

    @field_validator("T")
    @classmethod
    def T_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("T debe ser > 0.")
        return v

    @field_validator("sigma")
    @classmethod
    def sigma_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("sigma debe ser > 0.")
        return v


class GreeksResponse(BaseModel):
    delta: float
    gamma: float
    vega:  float
    theta: float
    rho:   float
    interpretation: Dict[str, str]


class OptionResponse(BaseModel):
    inputs:  Dict[str, Any]
    d1:      float
    d2:      float
    price:   float
    greeks:  GreeksResponse
    parity:  Dict[str, Any]
    implied_vol: Optional[Dict[str, Any]] = None


# ── Stress testing ────────────────────────────────────────────────────────────

class StressScenario(BaseModel):
    name:             str   = Field("Escenario",  description="Nombre descriptivo")
    rate_shock_bp:    int   = Field(0,    ge=-500, le=500,  description="Shock de tasa en pb")
    market_drop_pct:  float = Field(0.0,  ge=-1.0, le=0.5,  description="Caída del mercado (decimal, ej: -0.20)")
    vol_multiplier:   float = Field(1.0,  ge=0.5,  le=5.0,  description="Multiplicador de volatilidad")


class StressRequest(BaseModel):
    tickers:   List[str]   = Field(..., description="Tickers del portafolio")
    weights:   List[float] = Field(..., description="Pesos (deben sumar 1.0)")
    scenarios: List[StressScenario] = Field(
        default=[],
        description="Lista de escenarios. Si vacía, se usan los 6 obligatorios."
    )

    @field_validator("weights")
    @classmethod
    def weights_sum_one(cls, v: List[float]) -> List[float]:
        if abs(sum(v) - 1.0) > 1e-4:
            raise ValueError(f"Los pesos deben sumar 1.0 (suma actual: {sum(v):.4f})")
        return v


# ── ML / Predicción ───────────────────────────────────────────────────────────

class PredictRequest(BaseModel):
    ticker: str = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Ticker del activo a predecir"
    )

    @field_validator("ticker")
    @classmethod
    def ticker_upper(cls, v: str) -> str:
        return v.strip().upper()


class PredictResponse(BaseModel):
    ticker:          str
    model_version:   str
    regime:          str
    regime_code:     int
    confidence:      float
    probabilities:   Dict[str, float]
    features_used:   Dict[str, float]
    model_accuracy:  float
    interpretation:  str


# ── Portafolios guardados (CRUD) ──────────────────────────────────────────────

class PortfolioCreate(BaseModel):
    name:    str        = Field(..., min_length=2, max_length=120)
    tickers: List[str]  = Field(..., description="Lista de tickers del portafolio")
    weights: Dict[str, float] = Field(..., description="Dict ticker->peso")
    notes:   Optional[str]    = Field(None, max_length=500)

    @field_validator("weights")
    @classmethod
    def weights_sum_one(cls, v: Dict[str, float]) -> Dict[str, float]:
        total = sum(v.values())
        if abs(total - 1.0) > 1e-4:
            raise ValueError(f"Los pesos deben sumar 1.0 (suma actual: {total:.4f})")
        return v


class PortfolioResponse(BaseModel):
    id:         int
    name:       str
    tickers:    List[str]
    weights:    Dict[str, float]
    created_at: str
    notes:      Optional[str] = None


# ── Modelos faltantes usados en main.py ───────────────────────────────────────

class VaRRequest(BaseModel):
    """Solicitud para cálculo de Value at Risk."""
    ticker:      str   = Field(..., description="Ticker del activo")
    confidence:  float = Field(0.95, ge=0.90, le=0.99, description="Nivel de confianza")
    simulations: int   = Field(10000, ge=1000, le=100000, description="Simulaciones Monte Carlo")

    @field_validator("ticker")
    @classmethod
    def ticker_upper(cls, v: str) -> str:
        return v.strip().upper()


class PortfolioRequest(BaseModel):
    """Solicitud para análisis de portafolio / frontera eficiente."""
    tickers: List[str]   = Field(..., description="Lista de tickers")
    weights: List[float] = Field(..., description="Pesos (deben sumar 1.0)")

    @field_validator("weights")
    @classmethod
    def weights_sum_one(cls, v: List[float]) -> List[float]:
        if abs(sum(v) - 1.0) > 1e-4:
            raise ValueError(f"Los pesos deben sumar 1.0 (suma actual: {sum(v):.4f})")
        return v


class MensajeHistorial(BaseModel):
    """Un turno del historial de conversación con el asistente IA."""
    role:    str = Field(..., description="'user' o 'assistant'")
    content: str = Field(..., description="Contenido del mensaje")


class ConsultaIARequest(BaseModel):
    """Solicitud al asistente IA de riesgo financiero."""
    mensaje:   str                   = Field(..., min_length=1, description="Pregunta del usuario")
    historial: List[MensajeHistorial] = Field(default=[], description="Historial de conversación")


class ConsultaIAResponse(BaseModel):
    """Respuesta del asistente IA."""
    respuesta:          str
    ticker_mencionado:  Optional[str] = None
    tokens_usados:      Optional[int] = None