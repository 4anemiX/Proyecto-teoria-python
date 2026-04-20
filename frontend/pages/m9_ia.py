import streamlit as st
from data.client import fetch_consulta_ia, TICKERS
from utils.theme import ticker_color, COLORS


_PREGUNTAS_RAPIDAS = [
    ("¿Qué es el VaR?",            "¿Qué es el Value at Risk y para qué se usa en gestión de riesgo?"),
    ("VaR vs CVaR",                 "¿Cuál es la diferencia entre VaR y CVaR (Expected Shortfall)?"),
    ("Test de Kupiec",              "¿Qué es el test de Kupiec y cómo se interpreta en backtesting?"),
    ("CAPM y Beta",                 "Explica el modelo CAPM y cómo se interpreta el coeficiente Beta"),
    ("Sharpe Ratio",                "¿Cómo se interpreta el Sharpe Ratio en optimización de portafolios?"),
    ("Frontera de Markowitz",       "¿Qué es la frontera eficiente de Markowitz?"),
    ("NVDA en el portafolio",       "¿Qué riesgo aporta NVIDIA al portafolio dada su alta volatilidad y beta?"),
    ("KO como activo defensivo",    "¿Por qué incluir Coca-Cola (KO) en un portafolio de tecnología?"),
]


def _init_session():
    if "ia_historial" not in st.session_state:
        st.session_state.ia_historial = []
    if "ia_input_key" not in st.session_state:
        st.session_state.ia_input_key = 0


def _render_historial():
    if not st.session_state.ia_historial:
        st.markdown("""
        <div class="interpretation-box" style="text-align:center; padding:20px;">
            Haz una pregunta o usa uno de los accesos rápidos para comenzar.
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
            st.markdown(
                f'<div class="chat-msg-assistant">{msg["content"]}</div>',
                unsafe_allow_html=True,
            )


def _enviar(mensaje: str, contexto_ticker: str = None):
    if not mensaje.strip():
        return

    st.session_state.ia_historial.append({"role": "user", "content": mensaje})

    historial_api = st.session_state.ia_historial[:-1]

    with st.spinner("Consultando asistente..."):
        resultado = fetch_consulta_ia(mensaje, historial_api, contexto_ticker)

    if resultado and resultado.get("respuesta"):
        st.session_state.ia_historial.append(
            {"role": "assistant", "content": resultado["respuesta"]}
        )
    else:
        st.session_state.ia_historial.append(
            {"role": "assistant", "content": "No se pudo obtener respuesta. Verifica la conexión con el backend."}
        )

    st.session_state.ia_input_key += 1


def render():
    _init_session()

    st.markdown("""
    <div class="section-title">Asistente IA</div>
    <div class="section-subtitle">Consulta sobre los modelos de riesgo, los activos del portafolio y teoría financiera</div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="pydantic-tag">Pydantic · ConsultaIARequest validado</div>', unsafe_allow_html=True)

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
            st.rerun()

    ctx_ticker = None if contexto == "Sin contexto" else contexto

    _render_historial()

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        '<div style="font-size:0.68rem;font-weight:600;letter-spacing:0.1em;'
        'text-transform:uppercase;color:#2E3550;margin-bottom:8px;">Accesos rápidos</div>',
        unsafe_allow_html=True,
    )
    cols = st.columns(4)
    for i, (label, pregunta) in enumerate(_PREGUNTAS_RAPIDAS):
        with cols[i % 4]:
            if st.button(label, use_container_width=True, key=f"quick_{i}"):
                _enviar(pregunta, ctx_ticker)
                st.rerun()

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    col_input, col_send = st.columns([5, 1])
    with col_input:
        user_input = st.text_input(
            "Tu pregunta",
            placeholder="Ej: ¿Cómo afecta la correlación entre MSFT y NVDA al riesgo del portafolio?",
            label_visibility="collapsed",
            key=f"ia_input_{st.session_state.ia_input_key}",
        )
    with col_send:
        if st.button("Enviar", use_container_width=True, type="primary"):
            _enviar(user_input, ctx_ticker)
            st.rerun()

    if user_input:
        chars = len(user_input)
        if chars < 3:
            st.markdown(
                '<div class="interpretation-box negative" style="margin-top:8px;">'
                'Pydantic · <strong>mensaje</strong>: mínimo 3 caracteres</div>',
                unsafe_allow_html=True,
            )
        elif chars > 1000:
            st.markdown(
                '<div class="interpretation-box negative" style="margin-top:8px;">'
                f'Pydantic · <strong>mensaje</strong>: {chars}/1000 caracteres — límite excedido</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="interpretation-box positive" style="margin-top:8px;">'
                f'Pydantic · <strong>ConsultaIARequest</strong> válido — {chars}/1000 caracteres</div>',
                unsafe_allow_html=True,
            )