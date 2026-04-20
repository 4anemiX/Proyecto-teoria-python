import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from data.client import fetch_indicadores, TICKERS, BENCHMARK
from utils.theme import ticker_color, COLORS


def _interpret_technical(data: dict, ticker: str) -> tuple[str, str]:
    """Devuelve (mensaje, clase_css) según los indicadores técnicos."""
    signals = []
    rsi_vals = [r for r in data.get("rsi", []) if r is not None]
    last_rsi = rsi_vals[-1] if rsi_vals else 50

    macd_vals = data.get("macd", [])
    signal_vals = data.get("macd_signal", [])
    last_macd = macd_vals[-1] if macd_vals else 0
    last_signal = signal_vals[-1] if signal_vals else 0

    close_vals = data.get("close", [])
    sma_vals = data.get("sma", [])
    last_close = close_vals[-1] if close_vals else 0
    last_sma = sma_vals[-1] if sma_vals else 0

    # RSI
    if last_rsi > 70:
        signals.append(("sobrecompra (RSI {:.0f})".format(last_rsi), "negative"))
    elif last_rsi < 30:
        signals.append(("sobreventa (RSI {:.0f})".format(last_rsi), "positive"))
    else:
        signals.append(("RSI neutral ({:.0f})".format(last_rsi), "neutral"))

    # MACD
    if last_macd > last_signal:
        signals.append(("MACD alcista", "positive"))
    else:
        signals.append(("MACD bajista", "negative"))

    # Precio vs SMA
    if last_close > last_sma:
        signals.append(("precio sobre SMA (tendencia alcista)", "positive"))
    else:
        signals.append(("precio bajo SMA (tendencia bajista)", "negative"))

    bullish = sum(1 for _, s in signals if s == "positive")
    bearish = sum(1 for _, s in signals if s == "negative")

    desc = " · ".join(m for m, _ in signals)
    if bullish >= 2:
        return f"<strong>Señal técnica predominantemente alcista.</strong> {desc}.", "positive"
    elif bearish >= 2:
        return f"<strong>Señal técnica predominantemente bajista.</strong> {desc}.", "negative"
    else:
        return f"<strong>Señal técnica mixta.</strong> {desc}. Esperar confirmación antes de tomar posición.", "warning"


def render():
    st.markdown("""
    <div class="section-title">Análisis Técnico</div>
    <div class="section-subtitle">Indicadores de precio y momentum — SMA, EMA, Bandas de Bollinger, RSI, MACD, Estocástico</div>
    """, unsafe_allow_html=True)

    col_sel, col_info = st.columns([2, 5])
    with col_sel:
        ticker = st.selectbox("Activo", TICKERS + [BENCHMARK], label_visibility="visible")

    data = fetch_indicadores(ticker)
    if not data:
        st.warning("No se pudieron cargar los indicadores. Verifica el backend.")
        return

    fechas = data["fechas"]
    color = ticker_color(ticker)

    # ── Gráfico principal ──
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        row_heights=[0.55, 0.22, 0.23],
        vertical_spacing=0.04,
        subplot_titles=["Precio & Medias Móviles", "RSI (14)", "MACD"]
    )

    # Bandas de Bollinger (fondo)
    fig.add_trace(go.Scatter(
        x=fechas, y=data["bb_upper"], name="BB Superior",
        line=dict(color="#2E3850", width=1), showlegend=False
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=fechas, y=data["bb_lower"], name="BB Inferior",
        line=dict(color="#2E3850", width=1),
        fill="tonexty", fillcolor="rgba(59,130,246,0.05)",
        showlegend=False
    ), row=1, col=1)

    # Precio
    fig.add_trace(go.Scatter(
        x=fechas, y=data["close"], name="Precio",
        line=dict(color=color, width=2),
        hovertemplate="<b>%{x}</b><br>Precio: $%{y:,.2f}<extra></extra>"
    ), row=1, col=1)

    # SMA / EMA
    fig.add_trace(go.Scatter(
        x=fechas, y=data["sma"], name="SMA 20",
        line=dict(color=COLORS["warning"], width=1.2, dash="dot")
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=fechas, y=data["ema"], name="EMA 20",
        line=dict(color=COLORS["negative"], width=1.2, dash="dot")
    ), row=1, col=1)

    # RSI
    fig.add_trace(go.Scatter(
        x=fechas, y=data["rsi"], name="RSI",
        line=dict(color=COLORS["positive"], width=1.5),
        hovertemplate="RSI: %{y:.1f}<extra></extra>"
    ), row=2, col=1)
    fig.add_hrect(y0=70, y1=100, fillcolor="rgba(248,113,113,0.06)", line_width=0, row=2, col=1)
    fig.add_hrect(y0=0, y1=30, fillcolor="rgba(52,211,153,0.06)", line_width=0, row=2, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#F87171", line_width=1, row=2, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#34D399", line_width=1, row=2, col=1)

    # MACD
    macd_colors = [
        COLORS["positive"] if (m or 0) >= (s or 0) else COLORS["negative"]
        for m, s in zip(data["macd"], data["macd_signal"])
    ]
    fig.add_trace(go.Scatter(
        x=fechas, y=data["macd"], name="MACD",
        line=dict(color=COLORS["accent"], width=1.5),
        hovertemplate="MACD: %{y:.4f}<extra></extra>"
    ), row=3, col=1)
    fig.add_trace(go.Scatter(
        x=fechas, y=data["macd_signal"], name="Señal",
        line=dict(color=COLORS["warning"], width=1.2),
        hovertemplate="Señal: %{y:.4f}<extra></extra>"
    ), row=3, col=1)

    fig.update_layout(
        height=640,
        title=f"Análisis técnico — {ticker}",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1),
    )
    fig.update_yaxes(title_text="Precio (USD)", row=1, col=1, title_font=dict(size=10))
    fig.update_yaxes(title_text="RSI", row=2, col=1, title_font=dict(size=10), range=[0, 100])
    fig.update_yaxes(title_text="MACD", row=3, col=1, title_font=dict(size=10))

    st.plotly_chart(fig, use_container_width=True)

    # Interpretación técnica
    interp_msg, interp_class = _interpret_technical(data, ticker)
    st.markdown(f'<div class="interpretation-box {interp_class}">{interp_msg}</div>', unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Estocástico ──
    st.markdown('<div style="font-size:0.75rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#3B4460;margin-bottom:12px;">Oscilador Estocástico</div>', unsafe_allow_html=True)

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=fechas, y=data["stoch_k"], name="%K",
        line=dict(color=COLORS["accent"], width=1.5)
    ))
    fig2.add_trace(go.Scatter(
        x=fechas, y=data["stoch_d"], name="%D",
        line=dict(color=COLORS["warning"], width=1.2, dash="dot")
    ))
    fig2.add_hrect(y0=80, y1=100, fillcolor="rgba(248,113,113,0.05)", line_width=0)
    fig2.add_hrect(y0=0, y1=20, fillcolor="rgba(52,211,153,0.05)", line_width=0)
    fig2.add_hline(y=80, line_dash="dot", line_color="#F87171", line_width=1)
    fig2.add_hline(y=20, line_dash="dot", line_color="#34D399", line_width=1)
    fig2.update_layout(height=220, title="Oscilador Estocástico (%K, %D)", hovermode="x unified")
    st.plotly_chart(fig2, use_container_width=True)

    stoch_k_vals = [v for v in data.get("stoch_k", []) if v is not None]
    if stoch_k_vals:
        last_k = stoch_k_vals[-1]
        if last_k > 80:
            stoch_msg = f"El estocástico en <strong>{last_k:.0f}</strong> indica zona de sobrecompra. Posible corrección a corto plazo."
            stoch_class = "negative"
        elif last_k < 20:
            stoch_msg = f"El estocástico en <strong>{last_k:.0f}</strong> indica zona de sobreventa. Posible rebote técnico."
            stoch_class = "positive"
        else:
            stoch_msg = f"El estocástico en <strong>{last_k:.0f}</strong> se encuentra en zona neutral, sin señales extremas."
            stoch_class = ""
        st.markdown(f'<div class="interpretation-box {stoch_class}">{stoch_msg}</div>', unsafe_allow_html=True)