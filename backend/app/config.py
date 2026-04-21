from pydantic_settings import BaseSettings
import streamlit as st

class Settings(BaseSettings):
    alpha_vantage_key: str = "demo"
    fred_api_key: str = ""
    default_years: int = 3
    var_confidence: float = 0.95
    mc_simulations: int = 10000
    sma_period: int = 20
    ema_period: int = 21
    rsi_period: int = 14
    cache_ttl_seconds: int = 1800
    groq_api_key: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def get_groq_key(self) -> str:
        if self.groq_api_key:
            return self.groq_api_key
        try:
            return st.secrets["GROQ_API_KEY"]
        except Exception:
            return ""

settings = Settings()