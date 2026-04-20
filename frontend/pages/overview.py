import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from data.client import fetch_activos, fetch_precios, PORTFOLIO_META, TICKERS, BENCHMARK
from utils.theme import ticker_color, COLORS


def _interpret_correlation(corr_matrix: pd.DataFrame) -> str:
    """Genera interpretación automática de la matriz de correlaciones."""
    pairs = []
    tickers = corr_matrix.columns.tolist()
    for i in range(len(tickers)):
        for j in range(i + 1, len(tickers)):
            pairs.append((tickers[i], tickers[j], corr_matrix.iloc[i, j]))
    pairs.sort(key=lambda x: abs(x[2]), reverse=True)
    highest = pairs[0]
    lowest = pairs[-1]
    highly_correlated = [(a, b, c) for a, b, c in pairs if c > 0.7]

    msg = f"<strong>Par más correlacionado:</strong> {highest[0]}–{highest[1]} ({highest[2]:.2f}), "
    if len(highly_correlated) > 1:
        msg += f"junto con {len(highly_correlated) - 1} par(es) adicional(es) con correlación >0.70, lo que reduce la diversificación efectiva. "
    else:
        msg += "sin otros pares con correlación excesiva. "
    msg += f"<strong>Menor correlación:</strong> {lowest[0]}–{lowest[1]} ({lowest[2]:.2f}), lo que favorece la cobertura de riesgo entre estos activos."
    return msg


def render():
    st.markdown("""
    <div class="section-title">Vista General del Portafolio</div>
    <div class="section-subtitle">Economía Digital y Servicios Globales — empresas que transforman la economía global mediante tecnología, datos y servicios financieros.</div>
    """, unsafe_allow_html=True)

    activos = fetch_activos()
    if not activos:
        st.warning("No se pudo conectar con el backend. Verifica que esté corriendo en el puerto 8002.")
        return

    # ── Tarjetas de precios ──
    cols = st.columns(len(activos))
    bullish = sum(1 for a in activos if a["variacion_diaria"] >= 0)
    bearish = len(activos) - bullish

    for i, a in enumerate(activos):
        is_pos = a["variacion_diaria"] >= 0
        sign = "+" if is_pos else ""
        signal_class = "signal-positive" if is_pos else "signal-negative"
        color = ticker_color(a["ticker"])
        with cols[i]:
            st.markdown(f"""
            <div class="metric-card" style="--card-accent:{color};">
                <div class="metric-value" style="color:{color};">${a['precio_actual']:,.2f}</div>
                <div class="metric-label">{a['ticker']}</div>
                <div class="metric-label" style="color:#3B4460;">{a['empresa']}</div>
                <div class="metric-change {signal_class}">{sign}{a['variacion_diaria']:.2f}%</div>
            </div>
            """, unsafe_allow_html=True)

    # Interpretación del mercado
    sentiment = "predominantemente alcista" if bullish > bearish else ("mixto" if bullish == bearish else "predominantemente bajista")
    sentiment_class = "positive" if bullish > bearish else ("warning" if bullish == bearish else "negative")
    st.markdown(f"""
    <div class="interpretation-box {sentiment_class}" style="margin-top:16px;">
        <strong>Lectura de mercado:</strong> El portafolio muestra un cierre {sentiment} hoy,
        con {bullish} activo(s) en verde y {bearish} en rojo.
        {"Una mayoría alcista sugiere momentum positivo en el sector." if bullish > bearish else
         "La divergencia entre activos sugiere rotación sectorial o factores idiosincráticos." if bullish != bearish else
         "El equilibrio refleja indecisión del mercado — esperar confirmación de dirección."}
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Rendimiento normalizado ──
    st.markdown('<div style="font-size:0.75rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#3B4460;margin-bottom:12px;">Rendimiento Normalizado — Base 100</div>', unsafe_allow_html=True)

    fig = go.Figure()
    all_data = {}
    for ticker in TICKERS + [BENCHMARK]:
        data = fetch_precios(ticker)
        if data:
            closes = pd.Series(data["close"], index=data["fechas"])
            normalized = closes / closes.iloc[0] * 100
            all_data[ticker] = normalized
            fig.add_trace(go.Scatter(
                x=data["fechas"], y=normalized.tolist(),
                name=ticker,
                line=dict(color=ticker_color(ticker), width=1.8),
                hovertemplate=f"<b>{ticker}</b><br>%{{x}}<br>Base 100: %{{y:.2f}}<extra></extra>"
            ))

    fig.update_layout(height=380, title="Rendimiento relativo desde inicio del período")
    st.plotly_chart(fig, use_container_width=True)

    # Interpretación rendimiento
    if all_data:
        final_values = {t: v.iloc[-1] for t, v in all_data.items() if t != BENCHMARK}
        best_ticker = max(final_values, key=final_values.get)
        worst_ticker = min(final_values, key=final_values.get)
        spy_val = all_data.get(BENCHMARK, pd.Series([100])).iloc[-1]
        beating_spy = [t for t, v in final_values.items() if v > spy_val]

        st.markdown(f"""
        <div class="interpretation-box">
            <strong>Mejor desempeño:</strong> {best_ticker} con {final_values[best_ticker]:.1f} (base 100) —
            retorno acumulado de {final_values[best_ticker]-100:+.1f}%.
            <strong>Menor desempeño:</strong> {worst_ticker} con {final_values[worst_ticker]:.1f}.
            {len(beating_spy)} de {len(final_values)} activos superan al benchmark SPY ({spy_val:.1f}),
            {"indicando generación de alpha en el portafolio." if len(beating_spy) >= 3 else
             "lo que sugiere que el SPY ha sido difícil de superar en este período."}
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Matriz de correlaciones ──
    st.markdown('<div style="font-size:0.75rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#3B4460;margin-bottom:12px;">Matriz de Correlaciones</div>', unsafe_allow_html=True)

    prices = {}
    for ticker in TICKERS:
        data = fetch_precios(ticker)
        if data:
            prices[ticker] = data["close"]

    if prices:
        df_prices = pd.DataFrame(prices)
        corr = df_prices.pct_change().corr()

        fig2 = go.Figure(go.Heatmap(
            z=corr.values,
            x=corr.columns.tolist(),
            y=corr.index.tolist(),
            colorscale=[[0, "#1a0a0a"], [0.5, "#0D1018"], [1, "#0a1a2e"]],
            zmid=0,
            zmin=-1, zmax=1,
            text=corr.round(2).values,
            texttemplate="<b>%{text}</b>",
            textfont=dict(size=13, family="DM Mono, monospace"),
            showscale=True,
            colorbar=dict(
                thickness=10,
                tickfont=dict(size=10, color=COLORS["muted"]),
                outlinewidth=0,
            ),
            hovertemplate="%{y} / %{x}<br>Correlación: %{z:.3f}<extra></extra>"
        ))
        fig2.update_layout(height=340, title="Correlaciones de rendimientos logarítmicos diarios")
        st.plotly_chart(fig2, use_container_width=True)

        interp = _interpret_correlation(corr)
        st.markdown(f'<div class="interpretation-box">{interp}</div>', unsafe_allow_html=True)