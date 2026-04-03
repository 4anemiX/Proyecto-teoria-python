# ============================================================
# modules/tecnico.py — Módulo 1: Análisis Técnico
# ============================================================
 
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
 
from config import TICKERS, TICKER_INFO
 
 
# ── Indicadores ───────────────────────────────────────────────────────────────
 
def _sma(s: pd.Series, w: int) -> pd.Series:
    return s.rolling(w).mean()
 
def _ema(s: pd.Series, span: int) -> pd.Series:
    return s.ewm(span=span, adjust=False).mean()
 
def _rsi(s: pd.Series, period: int = 14) -> pd.Series:
    delta = s.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)
 
def _macd(s: pd.Series, fast=12, slow=26, signal=9):
    ema_f   = _ema(s, fast)
    ema_s   = _ema(s, slow)
    line    = ema_f - ema_s
    sig     = _ema(line, signal)
    hist    = line - sig
    return line, sig, hist
 
def _bollinger(s: pd.Series, window=20, num_std=2):
    mid   = _sma(s, window)
    std   = s.rolling(window).std()
    return mid + num_std * std, mid, mid - num_std * std
 
 
# ── Render ────────────────────────────────────────────────────────────────────
 
def render(precios: pd.DataFrame, rendimientos: pd.DataFrame):
    st.markdown("## 📈 Módulo 1 — Análisis Técnico e Indicadores")
    st.caption("Indicadores técnicos calculados sobre precios ajustados de cierre.")
 
    # Selector de activo
    col1, col2 = st.columns([2, 1])
    with col1:
        ticker = st.selectbox("Activo", TICKERS,
                              format_func=lambda t: f"{t} — {TICKER_INFO[t]['sector']}")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        show_signals = st.toggle("Mostrar señales de cruce", value=True)
 
    price = precios[ticker].dropna()
 
    # Parámetros
    with st.expander("⚙️ Parámetros", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        sma_s = c1.number_input("SMA corta",  5,  50,  20)
        sma_l = c2.number_input("SMA larga",  20, 200, 50)
        rsi_p = c3.number_input("RSI período", 5, 30,  14)
        bb_w  = c4.number_input("BB ventana", 10, 50,  20)
 
    sma_short = _sma(price, sma_s)
    sma_long  = _sma(price, sma_l)
    ema20     = _ema(price, 20)
    rsi       = _rsi(price, rsi_p)
    macd_l, macd_sig, macd_hist = _macd(price)
    bb_up, bb_mid, bb_lo = _bollinger(price, bb_w)
 
    cross_up   = (sma_short > sma_long) & (sma_short.shift(1) <= sma_long.shift(1))
    cross_down = (sma_short < sma_long) & (sma_short.shift(1) >= sma_long.shift(1))
 
    # ── Gráfico principal ──────────────────────────────────────────────────────
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        row_heights=[0.55, 0.25, 0.20],
        vertical_spacing=0.03,
        subplot_titles=[
            f"{ticker} — Precio, Medias y Bollinger", "MACD", f"RSI ({rsi_p})"
        ],
    )
 
    # Precio + medias
    fig.add_trace(go.Scatter(x=price.index, y=price, name="Precio",
                             line=dict(color="#6C63FF", width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=sma_short.index, y=sma_short, name=f"SMA{sma_s}",
                             line=dict(color="orange", width=1.2, dash="dash")), row=1, col=1)
    fig.add_trace(go.Scatter(x=sma_long.index, y=sma_long, name=f"SMA{sma_l}",
                             line=dict(color="red", width=1.2, dash="dash")), row=1, col=1)
    fig.add_trace(go.Scatter(x=ema20.index, y=ema20, name="EMA20",
                             line=dict(color="purple", width=1, dash="dot")), row=1, col=1)
 
    # Bollinger
    fig.add_trace(go.Scatter(x=bb_up.index, y=bb_up, name="BB Sup",
                             line=dict(color="gray", width=0.8, dash="dot"),
                             showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=bb_lo.index, y=bb_lo, name="BB Inf",
                             line=dict(color="gray", width=0.8, dash="dot"),
                             fill="tonexty", fillcolor="rgba(128,128,128,0.08)"), row=1, col=1)
 
    # Señales de cruce
    if show_signals:
        up_dates   = price.index[cross_up]
        down_dates = price.index[cross_down]
        if len(up_dates):
            fig.add_trace(go.Scatter(x=up_dates, y=price[cross_up], mode="markers",
                                     marker=dict(symbol="triangle-up", size=10, color="green"),
                                     name="Cruce dorado ▲"), row=1, col=1)
        if len(down_dates):
            fig.add_trace(go.Scatter(x=down_dates, y=price[cross_down], mode="markers",
                                     marker=dict(symbol="triangle-down", size=10, color="red"),
                                     name="Cruce muerto ▼"), row=1, col=1)
 
    # MACD
    colors_hist = ["#4ECDC4" if v >= 0 else "#FF6B6B" for v in macd_hist.fillna(0)]
    fig.add_trace(go.Bar(x=macd_hist.index, y=macd_hist, name="Histograma",
                         marker_color=colors_hist, opacity=0.6), row=2, col=1)
    fig.add_trace(go.Scatter(x=macd_l.index, y=macd_l, name="MACD",
                             line=dict(color="#6C63FF", width=1.2)), row=2, col=1)
    fig.add_trace(go.Scatter(x=macd_sig.index, y=macd_sig, name="Señal",
                             line=dict(color="orange", width=1.2)), row=2, col=1)
 
    # RSI
    fig.add_trace(go.Scatter(x=rsi.index, y=rsi, name="RSI",
                             line=dict(color="#ED1E79", width=1.5)), row=3, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="red",   row=3, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="green", row=3, col=1)
 
    fig.update_layout(
        height=700, template="plotly_white",
        legend=dict(orientation="h", y=1.02),
        margin=dict(l=0, r=0, t=30, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)
 
    # ── Señales recientes ──────────────────────────────────────────────────────
    st.markdown("### 🔔 Señales de cruce recientes")
    signals = []
    for d in price.index[cross_up][-5:]:
        signals.append({"Fecha": d.date(), "Tipo": "🟢 Cruce dorado (compra)", "Precio": f"${price[d]:.2f}"})
    for d in price.index[cross_down][-5:]:
        signals.append({"Fecha": d.date(), "Tipo": "🔴 Cruce muerto (venta)",  "Precio": f"${price[d]:.2f}"})
 
    if signals:
        st.dataframe(pd.DataFrame(signals).sort_values("Fecha", ascending=False),
                     use_container_width=True, hide_index=True)
    else:
        st.info("No se detectaron cruces en el período seleccionado.")
 
    rsi_now = rsi.dropna().iloc[-1]
    zone = ("🔴 Sobrecompra (>70)" if rsi_now > 70
            else "🟢 Sobreventa (<30)" if rsi_now < 30
            else "⚪ Zona neutral")
    st.metric(f"RSI actual — {ticker}", f"{rsi_now:.1f}", zone)