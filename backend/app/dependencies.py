from fastapi import Depends
from .config import Settings, get_settings
from . import services

def get_data_service(settings: Settings = Depends(get_settings)):
    """Dependencia: servicio de datos financieros"""
    return services

def get_rf_rate(settings: Settings = Depends(get_settings)) -> float:
    """Dependencia: tasa libre de riesgo"""
    macro = services.get_macro(settings.fred_api_key)
    return macro["risk_free_rate"]