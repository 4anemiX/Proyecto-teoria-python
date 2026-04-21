import streamlit as st
from data.client import fetch_consulta_ia, TICKERS
from utils.theme import ticker_color

_CATEGORIAS = {
    "Conceptos base": [
        ("¿Qué es el VaR?",         "¿Qué es el Value at Risk y para qué se usa en gestión de riesgo?"),
        ("VaR vs CVaR",             "¿Cuál es la diferencia entre VaR y CVaR (Expected Shortfall)?"),
        ("Test de Kupiec",          "¿Qué es el test de Kupiec y cómo se interpreta en backtesting?"),
        ("Distribución de colas",   "¿Qué son las colas gruesas en distribuciones de retornos financieros?"),
    ],
    "Modelos": [
        ("CAPM y Beta",             "Explica el modelo CAPM y cómo se interpreta el coeficiente Beta"),
        ("GARCH",                   "¿Cómo funciona el modelo GARCH y para qué sirve en series financieras?"),
        ("Sharpe Ratio",            "¿Cómo se interpreta el Sharpe Ratio en optimización de portafolios?"),
        ("Frontera de Markowitz",   "¿Qué es la frontera eficiente de Markowitz y cómo se construye?"),
    ],
    "Portafolio": [
        ("NVDA — riesgo",           "¿Qué riesgo aporta NVIDIA al portafolio dada su alta volatilidad y beta?"),
        ("KO — defensivo",          "¿Por qué incluir Coca-Cola (KO) en un portafolio de tecnología?"),
        ("JPM — finanzas",          "¿Qué rol cumple JPMorgan en el portafolio desde el punto de vista del riesgo?"),
        ("Correlación MSFT/NVDA",   "¿Cómo afecta la correlación entre MSFT y NVDA al riesgo del portafolio?"),
    ],
}

_TEMAS_VALIDOS = [
    "var", "cvar", "riesgo", "portafolio", "beta", "capm", "sharpe", "markowitz",
    "volatilidad", "retorno", "rendimiento", "correlación", "garch", "arch",
    "kupiec", "frontera", "activo", "ticker", "acción", "mercado", "financiero",
    "diversificación", "covarianza", "distribución", "normal", "cola", "percentil",
    "acn", "msft", "nvda", "ko", "jpm", "spy", "accenture", "microsoft", "nvidia",
    "coca", "jpmorgan", "benchmark", "alpha", "hedge", "drawdown", "expected shortfall",
    "montecarlo", "simulación", "histórico", "paramétrico", "backtesting",
]


def _init_session():
    if "ia_historial" not in st.session_state:
        st.session_state.ia_historial = []
    if "ia_input_key" not in st.session_state:
        st.session_state.ia_input_key = 0
    if "ia_total_preguntas" not in st.session_state:
        st.session_state.ia_total_preguntas = 0


def _es_tema_valido(mensaje: str) -> bool:
    msg_lower = mensaje.lower()
    return any(t in msg_lower for t in _TEMAS_VALIDOS)


def _render_historial():
    if not st.session_state.ia_historial:
        st.markdown("""
        <div class="interpretation-box" style="text-align:center; padding:20px;">
            Selecciona un tema o escribe una pregunta sobre teoría del riesgo o el portafolio.
        </div>
        """, unsafe_allow_html=True)
        return

    for msg in st.session_state.ia_historial:
        if msg["role"] == "user":
            st.markdown(
                f'<div class="chat-msg-user">{msg["content"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            ticker = msg.get("ticker")
            badge = ""
            if ticker:
                color = ticker_color(ticker)
                badge = f'<span style="font-family:monospace;font-size:0.7rem;background:#0D1018;color:{color};border:1px solid {color};border-radius:4px;padding:1px 7px;margin-left:8px;">{ticker}</span>'
            st.markdown(
                f'<div class="chat-msg-assistant">{badge}{msg["content"]}</div>',
                unsafe_allow_html=True,
            )


def _enviar(mensaje: str, contexto_ticker: str = None):
    if not mensaje.strip():
        return

    if not _es_tema_valido(mensaje):
        st.session_state.ia_historial.append({
            "role": "user",
            "content": mensaje,
            "ticker": None,
        })
        st.session_state.ia_historial.append({
            "role": "assistant",
            "content": "Solo puedo responder preguntas relacionadas con teoría del riesgo financiero, los modelos del proyecto (VaR, CAPM, GARCH, Markowitz) o los activos del portafolio (ACN, MSFT, NVDA, KO, JPM, SPY).",
            "ticker": None,
        })
        st.session_state.ia_input_key += 1
        return

    st.session_state.ia_historial.append({
        "role": "user",
        "content": mensaje,
        "ticker": None,
    })
    st.session_state.ia_total_preguntas += 1

    with st.spinner("Consultando asistente..."):
        resultado = fetch_consulta_ia(mensaje, [], contexto_ticker)

    if resultado and resultado.get("respuesta"):
        st.session_state.ia_historial.append({
            "role": "assistant",
            "content": resultado["respuesta"],
            "ticker": resultado.get("ticker_mencionado"),
        })
    else:
        st.session_state.ia_historial.append({
            "role": "assistant",
            "content": "No se pudo obtener respuesta. Verifica que el backend esté corriendo.",
            "ticker": None,
        })

    st.session_state.ia_input_key += 1


def _categorias_filtradas(ticker: str) -> dict:
    if ticker and ticker in ["ACN", "MSFT", "NVDA", "KO", "JPM"]:
        ticker_preguntas = {
            "ACN":  [("ACN — Beta",     "¿Cuál es el Beta de Accenture y qué implica para el portafolio?"),
                     ("ACN — Sector",   "¿Qué riesgo sectorial representa Accenture en el portafolio?")],
            "MSFT": [("MSFT — Sharpe",  "¿Cómo contribuye Microsoft al Sharpe Ratio del portafolio?"),
                     ("MSFT — Corr.",   "¿Cómo se correlaciona Microsoft con el resto del portafolio?")],
            "NVDA": [("NVDA — VaR",     "¿Cuál sería el VaR esperado de NVIDIA dado su nivel de volatilidad?"),
                     ("NVDA — Beta",    "¿Qué implica el alto Beta de NVIDIA para el riesgo del portafolio?")],
            "KO":   [("KO — Cobertura", "¿Cómo actúa Coca-Cola como activo defensivo frente a shocks de mercado?"),
                     ("KO — Corr.",     "¿Cuál es la correlación de KO con los activos tech del portafolio?")],
            "JPM":  [("JPM — Beta",     "¿Qué significa el Beta de JPMorgan en el contexto del portafolio?"),
                     ("JPM — Riesgo",   "¿Qué riesgo sistémico representa JPMorgan Chase en el portafolio?")],
        }
        categorias = dict(_CATEGORIAS)
        categorias[f"Específico · {ticker}"] = ticker_preguntas[ticker]
        return categorias
    return _CATEGORIAS


def render():
    _init_session()

    st.markdown("""
    <div class="section-title">Asistente IA</div>
    <div class="section-subtitle">Consultas sobre teoría del riesgo, modelos financieros y el portafolio del proyecto</div>
    """, unsafe_allow_html=True)

    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b1:
        st.markdown('<div class="pydantic-tag">Pydantic · ConsultaIARequest validado</div>', unsafe_allow_html=True)
    with col_b2:
        st.markdown(f'<div class="pydantic-tag">Consultas en sesión: {st.session_state.ia_total_preguntas}</div>', unsafe_allow_html=True)
    with col_b3:
        st.markdown('<div class="pydantic-tag">Modelo · Claude Haiku</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_ctx, col_clear = st.columns([3, 1])
    with col_ctx:
        contexto = st.selectbox(
            "Contexto de activo (opcional)",
            ["Sin contexto"] + TICKERS,
            key="ia_contexto",
        )
    with col_clear:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Limpiar chat", use_container_width=True):
            st.session_state.ia_historial = []
            st.session_state.ia_total_preguntas = 0
            st.rerun()

    ctx_ticker = None if contexto == "Sin contexto" else contexto

    _render_historial()

    st.markdown("<br>", unsafe_allow_html=True)

    for categoria, preguntas in _categorias_filtradas(ctx_ticker).items():
        st.markdown(
            f'<div style="font-size:0.68rem;font-weight:600;letter-spacing:0.1em;'
            f'text-transform:uppercase;color:#2E3550;margin-bottom:8px;">{categoria}</div>',
            unsafe_allow_html=True,
        )
        cols = st.columns(4)
        for i, (label, pregunta) in enumerate(preguntas):
            with cols[i % 4]:
                if st.button(label, use_container_width=True, key=f"quick_{categoria}_{i}"):
                    _enviar(pregunta, ctx_ticker)
                    st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    col_input, col_send = st.columns([5, 1])
    with col_input:
        user_input = st.text_input(
            "Tu pregunta",
            placeholder="Ej: ¿Cómo se interpreta un VaR del 5% para NVDA?",
            label_visibility="collapsed",
            key=f"ia_input_{st.session_state.ia_input_key}",
        )
    with col_send:
        if st.button("Enviar", use_container_width=True, type="primary"):
            _enviar(user_input, ctx_ticker)
            st.rerun()

    if user_input:
        chars = len(user_input)
        valido = _es_tema_valido(user_input)
        if chars < 3:
            css, msg = "negative", "mínimo 3 caracteres"
        elif chars > 1000:
            css, msg = "negative", f"{chars}/1000 caracteres — límite excedido"
        elif not valido:
            css, msg = "warning", "tema fuera del alcance — solo teoría del riesgo y portafolio"
        else:
            css, msg = "positive", f"ConsultaIARequest válido — {chars}/1000 caracteres"
        st.markdown(
            f'<div class="interpretation-box {css}" style="margin-top:8px;">'
            f'Pydantic · <strong>{msg}</strong></div>',
            unsafe_allow_html=True,
        )