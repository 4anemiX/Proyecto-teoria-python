from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    fred_api_key: str = "demo"
    var_confidence_level: float = 0.95
    sma_short: int = 20
    sma_long: int = 50
    rsi_period: int = 14
    default_tickers: list[str] = ["ACN", "MSFT", "NVDA", "KO", "JPM", "SPY"]
    benchmark: str = "SPY"
    risk_free_rate: float = 0.045

    model_config = {"env_file": ".env"}

@lru_cache
def get_settings() -> Settings:
    return Settings()