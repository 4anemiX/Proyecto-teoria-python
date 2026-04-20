from functools import lru_cache
from .services import DataService, TechnicalIndicators, RiskCalculator, PortfolioAnalyzer, AlertasService, MacroService
from .config import settings

@lru_cache()
def get_data_service() -> DataService:
    return DataService()

@lru_cache()
def get_tech_indicators() -> TechnicalIndicators:
    return TechnicalIndicators(
        sma=settings.sma_period,
        ema=settings.ema_period,
        rsi=settings.rsi_period,
    )

@lru_cache()
def get_risk_calculator() -> RiskCalculator:
    return RiskCalculator()

def get_portfolio_analyzer() -> PortfolioAnalyzer:
    return PortfolioAnalyzer(get_data_service())

def get_alertas_service() -> AlertasService:
    return AlertasService(get_tech_indicators())

@lru_cache()
def get_macro_service() -> MacroService:
    return MacroService()