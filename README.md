# DataRisk · USTA
### Tablero Interactivo de Análisis de Riesgo Financiero

**Universidad Santo Tomás · Teoría del Riesgo · Prof. Javier Mauricio Sierra · 2026**

> Proyecto integrador que implementa un tablero de análisis de riesgo financiero con nueve módulos cuantitativos y un asistente de IA conversacional. Desplegado en Streamlit Community Cloud con acceso público.

**Tablero en producción:** https://proyecto-teoria-python-aleja-xime.streamlit.app

---

## Portafolio Analizado

**Narrativa: Economía Digital y Servicios Globales** — empresas que transforman la economía global mediante tecnología, datos y servicios financieros.

| Ticker | Empresa | Sector |
|--------|---------|--------|
| ACN | Accenture | Consultoría Tecnológica |
| MSFT | Microsoft | Cloud / Inteligencia Artificial |
| NVDA | NVIDIA | Semiconductores / IA |
| KO | Coca-Cola | Consumo Defensivo |
| JPM | JPMorgan Chase | Finanzas Digitales |
| SPY | S&P 500 ETF | Benchmark del mercado |

**Horizonte por defecto:** 3 años de datos diarios · **Tasa libre de riesgo:** ^IRX (T-Bill 3M)

---

## Módulos de Análisis

| Módulo | Nombre | Contenido principal |
|--------|--------|-------------------|
| Overview | Vista General | Precios en tiempo real, rendimiento base 100, matriz de correlaciones |
| M1 | Análisis Técnico | SMA, EMA, Bollinger, RSI, MACD, Estocástico |
| M2 | Rendimientos | Estadísticas, pruebas de normalidad, histograma, Q-Q Plot, boxplot |
| M3 | ARCH/GARCH | ARCH(1), GARCH(1,1), GJR-GARCH, EGARCH — pronóstico 5 días comparativo |
| M4 | CAPM & Beta | Beta, alpha Jensen, R², Security Market Line |
| M5 | VaR & CVaR | VaR paramétrico/histórico/Montecarlo, CVaR, test de Kupiec |
| M6 | Markowitz | Frontera eficiente, mínima varianza, máximo Sharpe |
| M7 | Señales & Alertas | Heatmap de señales, score técnico, gauge por activo |
| M8 | Macro & Benchmark | VIX, tasas, divisas, Tracking Error, Information Ratio |
| M9 | Asistente IA | Chat con LLaMA 3.1 (Groq), accesos rápidos, contexto por ticker |

---

## Stack Tecnológico

| Componente | Tecnología | Versión |
|-----------|-----------|---------|
| Frontend | Streamlit | 1.43.2 |
| Visualización | Plotly | 5.22.0 |
| API (local) | FastAPI + Uvicorn | 0.136.0 / 0.44.0 |
| Validación | Pydantic + pydantic-settings | 2.13.1 |
| Datos de mercado | yfinance | 1.2.0 |
| Análisis cuantitativo | scipy / numpy / pandas | 1.15.3 / 2.2.5 / 2.2.3 |
| Modelos GARCH | arch | 7.0.0 |
| Optimización | PyPortfolioOpt | 1.5.6 |
| IA conversacional | Groq API (LLaMA 3.1) | llama-3.1-8b-instant |
| HTTP cliente | httpx | 0.27.0 |
| Runtime | Python | 3.12.9 |

---

## Estructura del Proyecto

```
DataRisk/
├── backend/
│   ├── app/
│   │   ├── main.py          # Endpoints FastAPI (uso local)
│   │   ├── services.py      # Motor de cálculo (DataService, RiskCalculator, etc.)
│   │   ├── models.py        # Modelos Pydantic request/response
│   │   ├── config.py        # Settings + fallback st.secrets
│   │   └── dependencies.py  # Inyección de dependencias
│   ├── requirements.txt
│   └── .python-version      # Python 3.12.9
├── frontend/
│   ├── app.py               # Punto de entrada, sidebar, fechas globales
│   ├── data/
│   │   └── client.py        # Capa de datos (llama servicios directamente)
│   ├── pages/
│   │   ├── overview.py
│   │   ├── m1_technical.py
│   │   ├── m2_returns.py
│   │   ├── m3_garch.py
│   │   ├── m4_capm.py
│   │   ├── m5_var.py
│   │   ├── m6_markowitz.py
│   │   ├── m7_signals.py
│   │   ├── m8_macro.py
│   │   └── m9_ia.py
│   ├── utils/
│   │   ├── styles.py        # CSS global
│   │   └── theme.py         # Paleta de colores y template Plotly
│   ├── requirements.txt
│   └── .python-version      # Python 3.12.9
└── requirements.txt         # Dependencias raíz
```

---

## Ejecución Local

### Requisitos
- Python 3.12.x
- Git

### 1. Clonar el repositorio
```bash
git clone https://github.com/4anemiX/Proyecto-teoria-python.git
cd Proyecto-teoria-python
```

### 2. Instalar dependencias del backend
```bash
cd backend
pip install -r requirements.txt
```

### 3. Instalar dependencias del frontend
```bash
cd ../frontend
pip install -r requirements.txt
```

### 4. Configurar variables de entorno (opcional)
```bash
# backend/.env
cp backend/.env.example backend/.env
# Editar si se desea cambiar períodos, TTL de caché, etc.
```

### 5. Iniciar el backend (Terminal 1)
```bash
cd backend
uvicorn app.main:app --reload --port 8002
```

### 6. Iniciar el frontend (Terminal 2)
```bash
cd frontend
streamlit run app.py
```

El tablero estará disponible en `http://localhost:8501`

---

## Despliegue en Streamlit Cloud

El proyecto se despliega automáticamente en cada `git push` a la rama `main`.

### Configuración en Streamlit Cloud
- **Repository:** `4anemiX/Proyecto-teoria-python`
- **Branch:** `main`
- **Main file path:** `frontend/app.py`
- **Python version:** 3.12 (detectado desde `.python-version`)

### Secrets requeridos
En **Settings → Secrets** de la app en Streamlit Cloud:
```toml
GROQ_API_KEY = "tu_api_key_de_groq"
```

La API key de Groq se obtiene gratuitamente en https://console.groq.com

---

## Variables de Entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `GROQ_API_KEY` | — | API key para el asistente IA (requerida) |
| `DEFAULT_YEARS` | `3` | Horizonte de análisis por defecto en años |
| `SMA_PERIOD` | `20` | Período de la media móvil simple |
| `EMA_PERIOD` | `21` | Período de la media móvil exponencial |
| `RSI_PERIOD` | `14` | Período del RSI |
| `CACHE_TTL_SECONDS` | `1800` | Tiempo de vida del caché (30 min) |
| `VAR_CONFIDENCE` | `0.95` | Nivel de confianza VaR por defecto |
| `MC_SIMULATIONS` | `10000` | Simulaciones Montecarlo por defecto |

---

## Características Principales

- **Selector de fechas global** en el sidebar con presets de 1, 3 y 5 años — afecta todos los módulos simultáneamente con invalidación automática de caché.
- **Interpretaciones automáticas** en cada módulo: diagnóstico textual basado en los valores calculados (señales técnicas, normalidad, riesgo, consensus GARCH).
- **Score técnico por activo** en M7: gauge de -5 a +5 que sintetiza los cinco indicadores técnicos.
- **Pronóstico GARCH comparativo**: todos los modelos en el mismo gráfico con línea de referencia de volatilidad actual.
- **Matriz de correlaciones en tonos morado/lila** para mejor legibilidad visual.
- **Asistente IA pedagógico** con historial de conversación, accesos rápidos y contexto por ticker activo.
- **Arquitectura directa**: en producción el frontend importa las clases del backend sin HTTP, eliminando la dependencia de un servidor externo.

---

## Autores

| Nombre | Programa |
|--------|----------|
| Alejandra Gordillo / Ximena Arias | Estadística · USTA |

**Prof. Javier Mauricio Sierra · Universidad Santo Tomás · 2026**

## Uso de IA

Este proyecto utilizó **Claude (Anthropic)** como asistente de desarrollo.

*DataRisk · Universidad Santo Tomás · Bogotá, Colombia · 2026*
