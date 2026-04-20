# DataRisk· USTA
### Tablero Interactivo de Análisis de Riesgo Financiero
**Universidad Santo Tomás · Teoría del Riesgo · Prof. Javier Mauricio Sierra**

> Proyecto integrador que implementa un tablero de análisis de riesgo financiero con arquitectura backend/frontend separada. El backend FastAPI sirve como motor de cálculo y el frontend Streamlit consume los endpoints para visualizar los resultados.

---

## Autores

| Nombre | Programa |
|--------|----------|
| [Tu nombre aquí] | Estadística · USTA |

---

## Portafolio Analizado 📌

**Narrativa: Economía Digital y Servicios Globales** — empresas que transforman la economía global mediante tecnología, datos y servicios financieros.

| Ticker | Empresa | Sector |
|--------|---------|--------|
| ACN | Accenture | Consultoría Tecnológica |
| MSFT | Microsoft | Cloud / Inteligencia Artificial |
| NVDA | NVIDIA | Semiconductores / IA |
| KO | Coca-Cola | Consumo Defensivo |
| JPM | JPMorgan Chase | Finanzas Digitales |
| SPY | S&P 500 ETF | Benchmark del mercado |

**Horizonte:** 3 años de datos diarios · **Tasa libre de riesgo:** ^IRX (T-Bill 3M)

---

## Stack Tecnológico

| Componente | Tecnología | Versión |
|-----------|-----------|---------|
| Backend API | FastAPI | 0.136.0 |
| Servidor ASGI | Uvicorn | 0.44.0 |
| Validación | Pydantic + pydantic-settings | 2.13.1 |
| Frontend | Streamlit | 1.43.2 |
| Visualización | Plotly | 5.22.0 |
| Datos de mercado | yfinance | 1.2.0 |
| Modelos ARCH/GARCH | arch | 7.0.0 |
| Optimización | PyPortfolioOpt | 1.5.6 |
| Estadística | scipy + statsmodels | 1.13.1 / 0.14.2 |
| Lenguaje | Python | 3.12.1 |

---

## Instalación

### 1. Clonar el repositorio
```bash
git clone <tu-repo>
cd RiskLab-Digital
```

### 2. Crear entorno virtual
```bash
python -m venv .venv
source .venv/bin/activate        # Linux / Mac
# .venv\Scripts\activate         # Windows
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
pip install -r backend/requirements.txt
```

### 4. Configurar variables de entorno
```bash
cp .env.example backend/.env
```

---

## Ejecución

### Terminal 1 — Backend FastAPI
```bash
cd backend
uvicorn app.main:app --reload --port 8002
```

### Terminal 2 — Frontend Streamlit
```bash
cd frontend
streamlit run app.py
```

---

## Endpoints del Backend

| Endpoint | Método | Descripción |
|---------|--------|-------------|
| `/` | GET | Health check |
| `/activos` | GET | Lista activos con precios actuales |
| `/precios/{ticker}` | GET | Precios históricos OHLCV |
| `/rendimientos/{ticker}` | GET | Rendimientos con estadísticas |
| `/indicadores/{ticker}` | GET | SMA, EMA, Bollinger, RSI, MACD, Estocástico |
| `/capm` | GET | Beta y rendimiento esperado CAPM |
| `/macro` | GET | Indicadores macroeconómicos |
| `/alertas` | GET | Señales de compra/venta |
| `/var` | POST | VaR paramétrico, histórico, MC y CVaR |
| `/frontera-eficiente` | POST | Frontera eficiente de Markowitz |

---

## Uso de IA

Este proyecto utilizó **Claude (Anthropic)** como asistente de desarrollo.

*DataRisk · Universidad Santo Tomás · Bogotá, Colombia · 2026*