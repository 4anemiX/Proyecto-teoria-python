# DataRisk · USTA

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
|------------|------------|---------|
| Backend API | FastAPI | 0.136.0 |
| Servidor ASGI | Uvicorn | 0.44.0 |
| Validación | Pydantic + pydantic-settings | 2.13.1 |
| Frontend | Streamlit | 1.43.2 |
| Visualización | Plotly | 5.22.0 |
| Datos de mercado | yfinance | 1.2.0 |
| Modelos ARCH/GARCH | arch | 7.0.0 |
| Optimización | PyPortfolioOpt | 1.5.6 |
| Estadística | scipy + statsmodels | 1.13.1 / 0.14.2 |
| IA Asistente | Groq API (llama-3.1-8b-instant) | — |
| Base de datos | SQLAlchemy + SQLite | — |
| Lenguaje | Python | 3.12.1 |

---

## Módulos del Frontend

| Módulo | Descripción |
|--------|-------------|
| Vista General | Resumen del portafolio, precios actuales y variación diaria |
| Análisis Técnico | SMA, EMA, Bollinger Bands, RSI, MACD, Oscilador Estocástico |
| Rendimientos | Estadísticas de retornos diarios por activo |
| ARCH/GARCH | Modelado de volatilidad condicional |
| CAPM & Beta | Beta de mercado y rendimiento esperado por CAPM |
| VaR & CVaR | Value at Risk paramétrico, histórico, Monte Carlo y CVaR |
| Markowitz | Frontera eficiente y optimización de portafolio |
| Señales & Alertas | Señales de compra/venta basadas en indicadores técnicos |
| Macro & Benchmark | Indicadores macroeconómicos y comparación con SPY |
| Asistente IA | Chat financiero con Groq (llama-3.1-8b-instant) |
| Renta Fija | Curva de rendimiento Nelson-Siegel, duración, convexidad |
| Opciones B-S | Valoración de opciones Black-Scholes y Greeks |
| Stress Testing | Escenarios de estrés sobre el portafolio |
| Predicción ML | Clasificación de régimen de mercado con Machine Learning |
| Portafolios | Gestión CRUD de portafolios personalizados |

---

## Endpoints del Backend

### Datos de mercado

| Endpoint | Método | Parámetros | Descripción |
|----------|--------|------------|-------------|
| `/` | GET | — | Health check |
| `/activos` | GET | — | Lista activos con precios actuales |
| `/precios/{ticker}` | GET | `start`, `end` (query, opcionales) | Precios históricos OHLCV |
| `/rendimientos/{ticker}` | GET | `start`, `end` (query, opcionales) | Retornos y estadísticas |
| `/indicadores/{ticker}` | GET | `start`, `end` (query, opcionales) | Indicadores técnicos |

### Análisis de riesgo

| Endpoint | Método | Parámetros | Descripción |
|----------|--------|------------|-------------|
| `/capm` | GET | `start`, `end` (query, opcionales) | Beta y rendimiento esperado CAPM |
| `/garch/{ticker}` | GET | `start`, `end` (query, opcionales) | Modelo ARCH/GARCH de volatilidad |
| `/var` | POST | `VaRRequest` body | VaR paramétrico, histórico, MC y CVaR |
| `/alertas` | GET | `start`, `end` (query, opcionales) | Señales de compra/venta |
| `/macro` | GET | — | Indicadores macroeconómicos |

### Portafolio

| Endpoint | Método | Parámetros | Descripción |
|----------|--------|------------|-------------|
| `/frontera-eficiente` | POST | `PortfolioRequest` body | Frontera eficiente de Markowitz |
| `/portafolios` | GET | — | Listar portafolios guardados |
| `/portafolios` | POST | `PortfolioCreate` body | Crear portafolio |
| `/portafolios/{id}` | DELETE | `portfolio_id` path | Eliminar portafolio |

### Renta Fija

| Endpoint | Método | Parámetros | Descripción |
|----------|--------|------------|-------------|
| `/curva-rendimiento` | GET | — | Curva Nelson-Siegel con datos FRED (caché 24h) |
| `/bono/duracion` | POST | `BondRequest` body | Duración Macaulay/Modificada y convexidad |

### Opciones

| Endpoint | Método | Parámetros | Descripción |
|----------|--------|------------|-------------|
| `/opcion/precio` | POST | `OptionRequest` body | Precio Black-Scholes, Greeks e IV implícita |
| `/opcion/curvas` | POST | `OptionRequest` body | Curvas de payoff y delta |

### Otros

| Endpoint | Método | Parámetros | Descripción |
|----------|--------|------------|-------------|
| `/stress` | POST | `StressRequest` body | Stress testing por escenarios |
| `/predict` | POST | `PredictRequest` body | Predicción de régimen de mercado (ML) |
| `/predict/history` | GET | `ticker`, `limit` (query) | Historial de predicciones |
| `/consulta-ia` | POST | `ConsultaIARequest` body | Asistente IA vía Groq |

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/4anemiX/Proyecto-teoria-python
cd Proyecto-teoria-python
```

### 2. Crear entorno virtual

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / Mac
source .venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
pip install -r backend/requirements.txt
```

### 4. Configurar variables de entorno

```bash
cp .env.example backend/.env
# Editar backend/.env y agregar:
# FRED_API_KEY=tu_clave_fred
# GROQ_API_KEY=tu_clave_groq
```

---

## Ejecución

Abrir **dos terminales** desde la raíz del proyecto:

### Terminal 1 — Backend FastAPI

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

El backend queda disponible en `http://localhost:8000`  
Documentación interactiva: `http://localhost:8000/docs`

### Terminal 2 — Frontend Streamlit

```bash
cd frontend
streamlit run app.py
```

El frontend se abre automáticamente en `http://localhost:8501`

---

## Variables de Entorno

| Variable | Descripción | Obligatoria |
|----------|-------------|-------------|
| `FRED_API_KEY` | Clave API de FRED (Federal Reserve Bank of St. Louis) | Sí (Renta Fija) |
| `GROQ_API_KEY` | Clave API de Groq para el Asistente IA | Sí (Asistente IA) |

Obtén tu clave FRED gratis en [fred.stlouisfed.org/docs/api/api_key.html](https://fred.stlouisfed.org/docs/api/api_key.html)  
Obtén tu clave Groq gratis en [console.groq.com](https://console.groq.com)

---

## Uso de IA

Este proyecto utilizó **Claude (Anthropic)** como asistente de desarrollo.

---

*DataRisk · Universidad Santo Tomás · Bogotá, Colombia · 2026*