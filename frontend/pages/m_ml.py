import streamlit as st
import plotly.graph_objects as go
from data.client import fetch_predict, fetch_predict_history, TICKERS
from utils.theme import COLORS, ticker_color

_REGIME_COLOR = {
    "alcista": COLORS["positive"],
    "bajista": COLORS["negative"],
    "lateral": COLORS["warning"],
}
_REGIME_ICON = {
    "alcista": "📈",
    "bajista": "📉",
    "lateral": "➡️",
}
_REGIME_DESC = {
    "alcista": "El modelo anticipa retornos positivos sostenidos. Momentum favorable.",
    "bajista": "El modelo anticipa retornos negativos. Señal de cautela o cobertura.",
    "lateral": "El modelo no detecta tendencia clara. Mercado en consolidación.",
}


# ── Gauge de confianza ─────────────────────────────────────────────────────────

def _gauge_confianza(confidence: float, regime: str):
    color = _REGIME_COLOR.get(regime, COLORS["muted"])
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(confidence * 100, 1),
        number=dict(suffix="%", font=dict(size=28, color=color, family="DM Mono, monospace")),
        gauge=dict(
            axis=dict(range=[0, 100], tickwidth=1, tickcolor=COLORS["muted"],
                      tickfont=dict(size=10, color=COLORS["muted"])),
            bar=dict(color=color, thickness=0.25),
            bgcolor=COLORS["surface"],
            borderwidth=0,
            steps=[
                dict(range=[0,  40], color="#0D1018"),
                dict(range=[40, 70], color="#111520"),
                dict(range=[70, 100], color="#141820"),
            ],
            threshold=dict(line=dict(color=color, width=3), thickness=0.75, value=confidence * 100),
        ),
        domain=dict(x=[0, 1], y=[0, 1]),
        title=dict(text="Confianza del modelo", font=dict(size=11, color=COLORS["muted"])),
    ))
    fig.update_layout(
        height=220,
        margin=dict(t=30, b=10, l=20, r=20),
        paper_bgcolor=COLORS["surface"],
        font=dict(color=COLORS["text"]),
    )
    return fig


# ── Probabilidades por régimen (barras horizontales) ──────────────────────────

def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _bars_probabilidades(probs: dict, regime: str):
    orden  = sorted(probs.keys(), key=lambda k: -probs[k])
    values = [probs[k] * 100 for k in orden]

    bar_colors = []
    for k in orden:
        base = _REGIME_COLOR.get(k, COLORS["muted"])
        bar_colors.append(base if k == regime else _hex_to_rgba(base, 0.25))

    fig = go.Figure(go.Bar(
        x=values, y=[k.upper() for k in orden],
        orientation="h",
        marker_color=bar_colors,
        marker_line_width=0,
        text=[f"{v:.1f}%" for v in values],
        textposition="outside",
        textfont=dict(size=12, family="DM Mono, monospace", color=COLORS["text"]),
        hovertemplate="<b>%{y}</b>: %{x:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        height=180,
        xaxis=dict(range=[0, 120], showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(tickfont=dict(size=13, family="DM Mono, monospace", color=COLORS["text"])),
        margin=dict(t=10, b=10, l=10, r=60),
        paper_bgcolor=COLORS["surface"],
        plot_bgcolor=COLORS["surface"],
        font=dict(color=COLORS["text"]),
        showlegend=False,
        bargap=0.35,
    )
    return fig


# ── Features normalizadas ──────────────────────────────────────────────────────

def _bars_features(features: dict):
    """
    Normaliza cada feature a z-score aproximado para que sean comparables.
    Muestra valores absolutos con color según positivo/negativo.
    """
    if not features:
        return None

    # Separar en grupos con contexto financiero
    FEATURE_LABELS = {
        "ret_1d":   "Retorno 1d (%)",
        "ret_5d":   "Retorno 5d (%)",
        "ret_20d":  "Retorno 20d (%)",
        "vol_20d":  "Volatilidad 20d",
        "rsi_14":   "RSI 14",
        "macd":     "MACD",
        "bb_pct":   "Bollinger %B",
    }

    # Normalizar cada feature a su rango típico para que sean comparables visualmente
    NORM_RANGES = {
        "ret_1d":  (-5, 5),
        "ret_5d":  (-10, 10),
        "ret_20d": (-20, 20),
        "vol_20d": (0, 0.05),
        "rsi_14":  (0, 100),
        "macd":    (-5, 5),
        "bb_pct":  (0, 1),
    }

    names, norm_vals, raw_vals, bar_colors = [], [], [], []

    for key, val in features.items():
        label = FEATURE_LABELS.get(key, key)
        rng = NORM_RANGES.get(key, (-1, 1))
        lo, hi = rng
        span = hi - lo if hi != lo else 1
        # Normalizar a [-1, 1]
        norm = 2 * ((float(val) - lo) / span) - 1
        norm = max(-1.0, min(1.0, norm))

        names.append(label)
        norm_vals.append(norm)
        raw_vals.append(float(val))
        bar_colors.append(COLORS["positive"] if norm >= 0 else COLORS["negative"])

    fig = go.Figure(go.Bar(
        x=norm_vals,
        y=names,
        orientation="h",
        marker_color=bar_colors,
        marker_opacity=0.8,
        text=[
            f"{v:.4f}" if abs(v) < 0.01
            else f"{v:.2f}" if abs(v) < 10
            else f"{v:.1f}"
            for v in raw_vals
        ],
        textposition="outside",
        textfont=dict(size=10, family="DM Mono, monospace", color=COLORS["muted"]),
        hovertemplate="<b>%{y}</b><br>Valor real: %{text}<br>Posición relativa: %{x:.2f}<extra></extra>",
        customdata=raw_vals,
    ))
    fig.add_vline(x=0, line_width=1, line_dash="dot", line_color="#2E3550")
    fig.update_layout(
        height=max(200, len(names) * 38 + 50),
        xaxis=dict(
            range=[-1.4, 1.4],
            tickvals=[-1, -0.5, 0, 0.5, 1],
            ticktext=["Mínimo", "", "Neutro", "", "Máximo"],
            tickfont=dict(size=9, color=COLORS["muted"]),
            gridcolor="#111520",
        ),
        yaxis=dict(tickfont=dict(size=10, color=COLORS["text"])),
        margin=dict(t=10, b=20, l=10, r=80),
        paper_bgcolor=COLORS["surface"],
        plot_bgcolor=COLORS["surface"],
        font=dict(color=COLORS["text"]),
        showlegend=False,
        bargap=0.3,
    )
    return fig


# ── Interpretación automática ──────────────────────────────────────────────────

def _interpretar(result: dict) -> None:
    regime     = result.get("regime", "")
    confidence = result.get("confidence", 0.0)
    accuracy   = result.get("model_accuracy", 0.0)
    features   = result.get("features_used", {})

    color = _REGIME_COLOR.get(regime, COLORS["muted"])
    icon  = _REGIME_ICON.get(regime, "❓")

    # Nivel de confianza
    if confidence >= 0.70:
        conf_txt = f"alta confianza ({confidence*100:.0f}%)"
    elif confidence >= 0.50:
        conf_txt = f"confianza moderada ({confidence*100:.0f}%)"
    else:
        conf_txt = (
            f"baja confianza ({confidence*100:.0f}%) — "
            "las tres clases tienen probabilidades similares, lo que indica incertidumbre alta"
        )

    texto = (
        f"El modelo clasifica el régimen actual como "
        f"<strong style='color:{color}'>{regime.upper()}</strong> con {conf_txt}. "
    )

    # Contexto de accuracy
    if accuracy < 0.50:
        texto += (
            f"El accuracy histórico del modelo es {accuracy*100:.1f}%, apenas por encima del azar — "
            "interpretar con cautela y no usar como señal única de decisión. "
        )
    else:
        texto += (
            f"El modelo tiene un accuracy histórico del {accuracy*100:.1f}% sobre datos de prueba. "
        )

    # Señales de features si están disponibles
    rsi = features.get("rsi_14")
    ret_20 = features.get("ret_20d")
    vol = features.get("vol_20d")

    señales = []
    if rsi is not None:
        if float(rsi) > 70:
            señales.append(f"RSI en zona de sobrecompra ({rsi:.1f})")
        elif float(rsi) < 30:
            señales.append(f"RSI en zona de sobreventa ({rsi:.1f})")
    if ret_20 is not None:
        if float(ret_20) < -0.05:
            señales.append(f"retorno acumulado de 20d negativo ({float(ret_20)*100:.1f}%)")
        elif float(ret_20) > 0.05:
            señales.append(f"momentum positivo en 20d ({float(ret_20)*100:.1f}%)")
    if vol is not None and float(vol) > 0.03:
        señales.append(f"volatilidad elevada ({float(vol)*100:.2f}% diario)")

    if señales:
        texto += "Los indicadores que respaldan esta predicción incluyen: " + ", ".join(señales) + "."

    st.markdown(
        f'<div style="padding:14px 18px;background:#0D1018;border:1px solid #1C2030;'
        f'border-left:3px solid {color};border-radius:0 8px 8px 0;'
        f'font-size:0.83rem;color:#A0AABE;line-height:1.7;">'
        f'<span style="font-size:1rem;margin-right:8px;">{icon}</span>{texto}</div>',
        unsafe_allow_html=True,
    )


# ── Render principal ───────────────────────────────────────────────────────────

def render():
    st.markdown("""
    <div class="section-title">Predicción ML — Régimen de Mercado</div>
    <div class="section-subtitle">Clasificación alcista · bajista · lateral — pipeline scikit-learn + Singleton</div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🤖 Predicción", "🗂️ Historial"])

    # ── Tab 1: Predicción ──────────────────────────────────────────────────────
    with tab1:
        col_sel, col_btn, _ = st.columns([1, 1, 3])
        ticker = col_sel.selectbox("Activo", TICKERS + ["SPY"])

        if col_btn.button("▶ Predecir", type="primary"):
            with st.spinner(f"Ejecutando modelo ML para {ticker}..."):
                result = fetch_predict(ticker)
            if result:
                st.session_state["ml_result"] = result
                st.session_state["ml_ticker"] = ticker

        if "ml_result" not in st.session_state:
            st.markdown("""
            <div style="margin-top:16px;padding:14px 18px;background:#0D1018;border:1px solid #1C2030;
                        border-left:3px solid #3B82F6;border-radius:0 8px 8px 0;
                        font-size:0.83rem;color:#5A6480;line-height:1.6;">
                Selecciona un activo y haz clic en <strong style="color:#D4D8E2;">Predecir</strong>
                para clasificar el régimen de mercado actual usando el modelo entrenado.
            </div>""", unsafe_allow_html=True)
            return

        result  = st.session_state["ml_result"]
        ticker  = st.session_state.get("ml_ticker", ticker)
        regime  = result.get("regime", "desconocido")
        conf    = result.get("confidence", 0.0)
        probs   = result.get("probabilities", {})
        features= result.get("features_used", {})
        version = result.get("model_version", "v1")
        color   = _REGIME_COLOR.get(regime, COLORS["muted"])
        icon    = _REGIME_ICON.get(regime, "❓")

        # ── Cabecera del resultado ──
        st.markdown(
            f'<div style="margin:16px 0;padding:16px 20px;background:#0D1018;'
            f'border:1px solid #1C2030;border-top:2px solid {color};border-radius:8px;'
            f'display:flex;align-items:center;gap:16px;">'
            f'<span style="font-size:2rem;">{icon}</span>'
            f'<div>'
            f'<div style="font-size:1.2rem;font-weight:600;color:{color};'
            f'font-family:\'DM Mono\',monospace;">{regime.upper()}</div>'
            f'<div style="font-size:0.78rem;color:{COLORS["muted"]};margin-top:2px;">'
            f'{ticker} · {version} · {_REGIME_DESC.get(regime, "")}</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        # ── Interpretación ──
        _interpretar(result)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Gráficos: gauge + probabilidades + features ──
        col_g, col_p = st.columns([1, 1])

        with col_g:
            st.markdown(
                '<div style="font-size:0.65rem;font-weight:700;letter-spacing:0.1em;'
                'text-transform:uppercase;color:#3B4460;margin-bottom:4px;">Confianza</div>',
                unsafe_allow_html=True,
            )
            st.plotly_chart(_gauge_confianza(conf, regime),
                            use_container_width=True, config={"displayModeBar": False})

        with col_p:
            st.markdown(
                '<div style="font-size:0.65rem;font-weight:700;letter-spacing:0.1em;'
                'text-transform:uppercase;color:#3B4460;margin-bottom:4px;">Probabilidad por régimen</div>',
                unsafe_allow_html=True,
            )
            if probs:
                st.plotly_chart(_bars_probabilidades(probs, regime),
                                use_container_width=True, config={"displayModeBar": False})

        # ── Features normalizadas (ancho completo) ──
        if features:
            st.markdown(
                '<div style="font-size:0.65rem;font-weight:700;letter-spacing:0.1em;'
                'text-transform:uppercase;color:#3B4460;margin:16px 0 4px;">Features del modelo — posición relativa en su rango histórico</div>',
                unsafe_allow_html=True,
            )
            fig_f = _bars_features(features)
            if fig_f:
                st.plotly_chart(fig_f, use_container_width=True, config={"displayModeBar": False})
            st.caption(
                "Cada barra muestra dónde está el valor actual dentro del rango típico de esa feature. "
                "Verde = extremo superior · Rojo = extremo inferior · El valor real aparece a la derecha."
            )

    # ── Tab 2: Historial ───────────────────────────────────────────────────────
    with tab2:
        st.markdown(
            '<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;'
            'text-transform:uppercase;color:#3B4460;margin-bottom:12px;">Predicciones guardadas en SQLite</div>',
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns([1, 2])
        filter_ticker = col1.selectbox("Filtrar por ticker", ["Todos"] + TICKERS + ["SPY"])
        limit         = col2.slider("Máximo de registros", 5, 100, 20)
        ticker_param  = None if filter_ticker == "Todos" else filter_ticker

        with st.spinner("Cargando historial..."):
            history = fetch_predict_history(ticker_param, limit)

        if not history:
            st.info("No hay predicciones guardadas aún. Ejecuta una predicción primero.")
            return

        # Mini tabla visual
        for rec in history:
            regime = rec.get("label", "?")
            color  = _REGIME_COLOR.get(regime, COLORS["muted"])
            icon   = _REGIME_ICON.get(regime, "❓")
            conf   = (rec.get("confidence") or 0.0) * 100
            ts     = str(rec.get("timestamp", ""))[:16]
            tick   = rec.get("ticker", "")
            ver    = rec.get("model_version", "")

            # Barra de confianza inline
            bar_w  = int(conf)
            bar_color = color

            st.markdown(
                f'<div style="margin-bottom:6px;padding:10px 14px;background:#0D1018;'
                f'border:1px solid #1C2030;border-left:3px solid {color};border-radius:0 6px 6px 0;'
                f'display:flex;align-items:center;gap:14px;">'
                f'<span style="font-size:1.1rem;">{icon}</span>'
                f'<span style="font-family:\'DM Mono\',monospace;font-size:0.85rem;'
                f'font-weight:600;color:{color};min-width:70px;">{regime.upper()}</span>'
                f'<span style="font-family:\'DM Mono\',monospace;font-size:0.82rem;'
                f'color:{COLORS["muted"]};min-width:50px;">{tick}</span>'
                f'<div style="flex:1;background:#111520;border-radius:3px;height:4px;">'
                f'<div style="width:{bar_w}%;background:{bar_color};border-radius:3px;height:4px;"></div>'
                f'</div>'
                f'<span style="font-family:\'DM Mono\',monospace;font-size:0.8rem;'
                f'color:{COLORS["muted"]};min-width:50px;text-align:right;">{conf:.0f}%</span>'
                f'<span style="font-size:0.75rem;color:#3B4460;min-width:130px;text-align:right;">{ts}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )