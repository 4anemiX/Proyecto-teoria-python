from pydantic import BaseModel, Field, field_validator
from typing import Optional

class PortfolioRequest(BaseModel):
    tickers: list[str] = Field(..., min_length=2, description="Lista de tickers")
    weights: list[float] = Field(..., description="Pesos del portafolio, deben sumar 1.0")
    confidence_level: float = Field(0.95, ge=0.90, le=0.99)

    @field_validator("weights")
    @classmethod
    def weights_must_sum_one(cls, v):
        if abs(sum(v) - 1.0) > 0.01:
            raise ValueError(f"Los pesos deben sumar 1.0, suman {sum(v):.4f}")
        return v

    @field_validator("tickers")
    @classmethod
    def tickers_format(cls, v):
        for t in v:
            if not t.isalpha() or len(t) > 5:
                raise ValueError(f"Ticker inválido: {t}")
        return [t.upper() for t in v]

class VaRResponse(BaseModel):
    ticker_or_portfolio: str
    var_historico: float
    var_parametrico: float
    var_montecarlo: float
    cvar: float
    confidence_level: float

class CAPMResponse(BaseModel):
    ticker: str
    beta: float
    alpha: float
    expected_return: float
    risk_free_rate: float
    market_return: float
    r_squared: float

class IndicadoresResponse(BaseModel):
    ticker: str
    sma_20: Optional[float]
    sma_50: Optional[float]
    ema_20: Optional[float]
    rsi: Optional[float]
    macd: Optional[float]
    macd_signal: Optional[float]
    bb_upper: Optional[float]
    bb_lower: Optional[float]
    last_price: float
    signal: str

class MacroResponse(BaseModel):
    risk_free_rate: float
    source: str
    inflation_us: Optional[float]
    fed_funds_rate: Optional[float]