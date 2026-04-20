import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd
from data.client import fetch_capm, TICKERS
from utils.theme import ticker_color, COLORS


def _interpret_capm(data: list) -> str:
    valid = [d for d in data if "error" not in d]
    aggressive = [d["ticker"] for d in valid if d["beta"] > 1.2]
    defensive = [d["ticker"] for d in valid if d["beta"] < 0.8]
    alpha_pos = [d["ticker"] for d in valid if d.get("alpha", 0) > 0]

    parts = []
    if aggressive:
        parts.append(f"<strong>Activos agresivos (β > 1.2):</strong> {', '.join(aggressive)} — amplifican movimientos del mercado, mayor riesgo sistemático")
    if defensive:
        parts.append(f"<strong>Activos defensivos (β < 0.8):</strong> {', '.join(defensive)} — amortiguan caídas del mercado, útiles en portafolios conservadores")
    if alpha_pos:
        parts.append(f"<strong>Alpha positivo:</strong> {', '.join(alpha_pos)} generan retorno por encima del predicho por su beta — posible ventaja competitiva")

    if not parts:
        return "Los activos presentan betas cercanas a 1, moviéndose en línea con el mercado."
    return ". ".join(parts) + "."


def render():
    st.markdown("""
    <div class="section-title">CAPM & Beta</div>
    <div class="section-subtitle">Capital Asset Pricing Model — riesgo sistemático, retorno esperado y Security Market Line</div>
    """, unsafe_allow_html=True)

    data = fetch_capm()
    if not data:
        st.warning("No se pudieron cargar los datos CAPM.")
        return

    valid = [d for d in data if "error" not in d]

    # ── Tarjetas Beta ──
    cols = st.columns(len(valid))
    for i, d in enumerate(valid):
        color = ticker_color(d["ticker"])
        is_aggressive = d["beta"] > 1
        beta_color = COLORS["negative"] if is_aggressive else COLORS["positive"]
        with cols[i]:
            st.markdown(f"""
            <div class="metric-card" style="--card-accent:{color};">
                <div class="metric-value" style="color:{beta_color}; font-family:'DM Mono',monospace;">{d['beta']:.3f}</div>
                <div class="metric-label">{d['ticker']} · Beta</div>
                <div class="metric-change" style="color:{COLORS['muted']};">
                    α {d['alpha']*100:+.3f}% · R² {d['r_squared']:.3f}
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown(f'<div class="interpretation-box" style="margin-top:16px;">{_interpret_capm(data)}</div>', unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── SML ──
    st.markdown('<div style="font-size:0.75rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#3B4460;margin-bottom:12px;">Security Market Line</div>', unsafe_allow_html=True)

    rf = valid[0]["risk_free_rate"]
    mr = valid[0]["market_return"]
    beta_range = np.linspace(0, 2, 100)
    sml = rf + beta_range * (mr - rf)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=beta_range.tolist(), y=sml.tolist(), name="SML (CAPM)",
        line=dict(color=COLORS["border2"], width=1.5, dash="dash"),
        hovertemplate="Beta: %{x:.2f}<br>Ret. esperado: %{y:.2%}<extra></extra>"
    ))

    for d in valid:
        above_sml = d["expected_return"] > (rf + d["beta"] * (mr - rf))
        marker_symbol = "circle" if above_sml else "circle-open"
        fig.add_trace(go.Scatter(
            x=[d["beta"]], y=[d["expected_return"]],
            mode="markers+text", name=d["ticker"],
            marker=dict(
                color=ticker_color(d["ticker"]),
                size=16,
                symbol=marker_symbol,
                line=dict(width=2, color=ticker_color(d["ticker"]))
            ),
            text=[d["ticker"]], textposition="top center",
            textfont=dict(size=11, family="DM Mono, monospace"),
            hovertemplate=f"<b>{d['ticker']}</b><br>Beta: {d['beta']:.3f}<br>Ret. esperado: {d['expected_return']:.2%}<extra></extra>"
        ))

    fig.update_layout(
        height=420,
        title="Security Market Line — activos sobre la línea generan alpha positivo",
        xaxis_title="Beta (riesgo sistemático)",
        yaxis_title="Rendimiento esperado anual",
        xaxis=dict(range=[0, 2]),
        hovermode="closest",
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Tabla ──
    st.markdown('<div style="font-size:0.75rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#3B4460;margin-bottom:12px;">Clasificación de Activos</div>', unsafe_allow_html=True)

    rows = []
    for d in valid:
        if d["beta"] > 1.2:
            cat = "Agresivo"
            badge = '<span class="badge badge-red">Agresivo</span>'
        elif d["beta"] < 0.8:
            cat = "Defensivo"
            badge = '<span class="badge badge-green">Defensivo</span>'
        else:
            cat = "Moderado"
            badge = '<span class="badge badge-yellow">Moderado</span>'
        rows.append({
            "Ticker": d["ticker"],
            "Beta": round(d["beta"], 4),
            "Alpha (anual)": f"{d['alpha']*100:+.3f}%",
            "Ret. Esperado": f"{d['expected_return']*100:.2f}%",
            "R²": round(d["r_squared"], 4),
            "Perfil": cat,
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)