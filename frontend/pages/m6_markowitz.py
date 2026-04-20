import streamlit as st
import plotly.graph_objects as go
from data.client import fetch_frontera, TICKERS
from utils.theme import ticker_color, COLORS


def render():
    st.markdown("""
    <div class="section-title">Frontera Eficiente de Markowitz</div>
    <div class="section-subtitle">Optimización media-varianza — portafolios de mínima varianza y máximo Sharpe Ratio</div>
    """, unsafe_allow_html=True)

    n = len(TICKERS)
    weights = [1 / n] * n

    with st.spinner("Calculando frontera eficiente..."):
        data = fetch_frontera(TICKERS, weights)
    if not data:
        st.warning("No se pudo calcular la frontera eficiente.")
        return

    # ── Frontera ──
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data["volatilities"], y=data["returns"],
        mode="lines", name="Frontera Eficiente",
        line=dict(color=COLORS["accent"], width=2),
        hovertemplate="Vol: %{x:.2%}<br>Ret: %{y:.2%}<extra></extra>"
    ))

    # Min varianza
    fig.add_trace(go.Scatter(
        x=[data["min_var_vol"]], y=[data["min_var_return"]],
        mode="markers+text", name="Mínima Varianza",
        marker=dict(color=COLORS["positive"], size=14, symbol="diamond",
                    line=dict(width=2, color=COLORS["positive"])),
        text=["Min Var"], textposition="top right",
        textfont=dict(size=10, family="DM Mono, monospace"),
        hovertemplate=f"Min Varianza<br>Vol: {data['min_var_vol']:.2%}<br>Ret: {data['min_var_return']:.2%}<extra></extra>"
    ))

    # Max Sharpe
    fig.add_trace(go.Scatter(
        x=[data["max_sharpe_vol"]], y=[data["max_sharpe_return"]],
        mode="markers+text", name=f"Max Sharpe ({data['max_sharpe_ratio']:.2f})",
        marker=dict(color=COLORS["warning"], size=14, symbol="star",
                    line=dict(width=2, color=COLORS["warning"])),
        text=["Max Sharpe"], textposition="top right",
        textfont=dict(size=10, family="DM Mono, monospace"),
        hovertemplate=f"Max Sharpe<br>Sharpe: {data['max_sharpe_ratio']:.3f}<br>Vol: {data['max_sharpe_vol']:.2%}<br>Ret: {data['max_sharpe_return']:.2%}<extra></extra>"
    ))

    fig.update_layout(
        height=460,
        title="Frontera eficiente — conjunto de portafolios óptimos por nivel de riesgo",
        xaxis_title="Volatilidad anual",
        yaxis_title="Rendimiento anual",
        xaxis=dict(tickformat=".1%"),
        yaxis=dict(tickformat=".1%"),
        hovermode="closest",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Interpretación
    sharpe = data["max_sharpe_ratio"]
    ret_diff = (data["max_sharpe_return"] - data["min_var_return"]) * 100
    vol_diff = (data["max_sharpe_vol"] - data["min_var_vol"]) * 100
    st.markdown(f"""
    <div class="interpretation-box">
        <strong>Frontera eficiente:</strong> El portafolio de máximo Sharpe ({sharpe:.2f}) ofrece
        {ret_diff:+.2f}pp de retorno adicional frente al de mínima varianza,
        a costa de {vol_diff:+.2f}pp de volatilidad adicional.
        {"Un Sharpe > 1 es considerado excelente — el portafolio recompensa bien el riesgo asumido." if sharpe > 1 else
         "Un Sharpe entre 0.5 y 1 es aceptable para un portafolio de renta variable." if sharpe > 0.5 else
         "Un Sharpe < 0.5 sugiere que el retorno no compensa adecuadamente la volatilidad del portafolio."}
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Pesos ──
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div style="font-size:0.75rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#3B4460;margin-bottom:8px;">Portafolio Mínima Varianza</div>', unsafe_allow_html=True)
        mv_c1, mv_c2 = st.columns(2)
        mv_c1.metric("Rendimiento", f"{data['min_var_return']*100:.2f}%")
        mv_c2.metric("Volatilidad", f"{data['min_var_vol']*100:.2f}%")
        mv_w = {k: v for k, v in data["min_var_weights"].items() if v > 0.001}
        fig2 = go.Figure(go.Pie(
            labels=list(mv_w.keys()), values=list(mv_w.values()),
            marker_colors=[ticker_color(t) for t in mv_w],
            hole=0.5,
            textfont=dict(size=11, family="DM Mono, monospace"),
            hovertemplate="%{label}: %{percent}<extra></extra>"
        ))
        fig2.update_layout(
            height=280,
            margin=dict(l=0, r=0, t=20, b=0),
            showlegend=True,
            legend=dict(font=dict(size=10)),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        st.markdown('<div style="font-size:0.75rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#3B4460;margin-bottom:8px;">Portafolio Máximo Sharpe</div>', unsafe_allow_html=True)
        ms_c1, ms_c2, ms_c3 = st.columns(3)
        ms_c1.metric("Rendimiento", f"{data['max_sharpe_return']*100:.2f}%")
        ms_c2.metric("Volatilidad", f"{data['max_sharpe_vol']*100:.2f}%")
        ms_c3.metric("Sharpe", f"{data['max_sharpe_ratio']:.3f}")
        ms_w = {k: v for k, v in data["max_sharpe_weights"].items() if v > 0.001}
        fig3 = go.Figure(go.Pie(
            labels=list(ms_w.keys()), values=list(ms_w.values()),
            marker_colors=[ticker_color(t) for t in ms_w],
            hole=0.5,
            textfont=dict(size=11, family="DM Mono, monospace"),
            hovertemplate="%{label}: %{percent}<extra></extra>"
        ))
        fig3.update_layout(
            height=280,
            margin=dict(l=0, r=0, t=20, b=0),
            showlegend=True,
            legend=dict(font=dict(size=10)),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig3, use_container_width=True)

    # Interpretación de concentración
    dominant_mv = max(data["min_var_weights"], key=data["min_var_weights"].get)
    dominant_ms = max(data["max_sharpe_weights"], key=data["max_sharpe_weights"].get)
    st.markdown(f"""
    <div class="interpretation-box">
        <strong>Concentración:</strong> El portafolio de mínima varianza está dominado por
        <strong>{dominant_mv}</strong> ({data['min_var_weights'][dominant_mv]*100:.1f}%),
        activo de menor riesgo relativo. El portafolio de máximo Sharpe concentra en
        <strong>{dominant_ms}</strong> ({data['max_sharpe_weights'][dominant_ms]*100:.1f}%),
        el activo con mejor relación riesgo-retorno.
        Una concentración excesiva (>60%) en un solo activo reduce la diversificación efectiva.
    </div>
    """, unsafe_allow_html=True)