import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from scipy import stats as scipy_stats
from data.client import fetch_rendimientos, TICKERS, BENCHMARK
from utils.theme import ticker_color, COLORS


def _interpret_distribution(data: dict, ticker: str) -> tuple[str, str]:
    skew = data.get("skewness", 0)
    kurt = data.get("kurtosis", 0)
    jb_pval = data.get("jarque_bera_pval", 0)
    media = data.get("media", 0) * 100
    std = data.get("std", 0) * 100

    parts = []
    css = "warning"

    if jb_pval < 0.05:
        parts.append("Los rendimientos <strong>no siguen distribución normal</strong> (Jarque-Bera p={:.4f})".format(jb_pval))
        css = "warning"
    else:
        parts.append("Los rendimientos son <strong>aproximadamente normales</strong> (Jarque-Bera p={:.4f})".format(jb_pval))
        css = "positive"

    if abs(skew) > 0.5:
        direction = "negativa" if skew < 0 else "positiva"
        parts.append(f"asimetría {direction} ({skew:.3f}) sugiere {'colas izquierdas largas — mayor riesgo de pérdidas extremas' if skew < 0 else 'colas derechas largas — potencial de ganancias excepcionales'}")
        if skew < 0:
            css = "negative"

    if kurt > 3:
        parts.append(f"curtosis excesiva ({kurt:.2f}) indica distribución leptocúrtica — mayor probabilidad de eventos extremos de la que predicen modelos gaussianos")
        css = "negative"

    parts.append(f"media diaria {media:+.4f}%, volatilidad diaria {std:.4f}%")
    return ". ".join(parts) + ".", css


def render():
    st.markdown("""
    <div class="section-title">Análisis de Rendimientos</div>
    <div class="section-subtitle">Distribución estadística, pruebas de normalidad y comparativa entre activos</div>
    """, unsafe_allow_html=True)

    ticker = st.selectbox("Activo", TICKERS + [BENCHMARK])
    data = fetch_rendimientos(ticker)
    if not data:
        st.warning("No se pudieron cargar los rendimientos.")
        return

    # ── Métricas ──
    col1, col2, col3, col4 = st.columns(4)
    color = ticker_color(ticker)

    metrics = [
        ("Media diaria", f"{data['media']*100:+.4f}%", col1),
        ("Desv. estándar", f"{data['std']*100:.4f}%", col2),
        ("Asimetría", f"{data['skewness']:.4f}", col3),
        ("Curtosis exc.", f"{data['kurtosis']:.4f}", col4),
    ]
    for label, val, col in metrics:
        with col:
            st.markdown(f"""
            <div class="metric-card" style="--card-accent:{color};">
                <div class="metric-value" style="color:{color}; font-size:1.3rem;">{val}</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col5, col6, col7, col8 = st.columns(4)
    jb_ok = data['jarque_bera_pval'] > 0.05
    sh_ok = data['shapiro_pval'] > 0.05

    tests = [
        ("JB Estadístico", f"{data['jarque_bera_stat']:.2f}", col5),
        ("JB p-valor", f"{data['jarque_bera_pval']:.4f}", col6),
        ("Shapiro Estadístico", f"{data['shapiro_stat']:.4f}", col7),
        ("Shapiro p-valor", f"{data['shapiro_pval']:.4f}", col8),
    ]
    for label, val, col in tests:
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color:{COLORS['positive'] if jb_ok else COLORS['negative']}; font-size:1.1rem;">{val}</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    # Interpretación estadística
    interp_msg, interp_class = _interpret_distribution(data, ticker)
    st.markdown(f'<div class="interpretation-box {interp_class}" style="margin-top:16px;">{interp_msg}</div>', unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Histograma + Q-Q ──
    rets = [r for r in data["logaritmicos"] if r is not None]
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=["Distribución de Rendimientos", "Q-Q Plot vs Normal"],
        horizontal_spacing=0.08
    )

    fig.add_trace(go.Histogram(
        x=rets, nbinsx=60, name="Rendimientos",
        marker_color=color, opacity=0.7,
        hovertemplate="Rango: %{x:.4f}<br>Frecuencia: %{y}<extra></extra>"
    ), row=1, col=1)

    x_range = np.linspace(min(rets), max(rets), 200)
    pdf = scipy_stats.norm.pdf(x_range, data["media"], data["std"]) * len(rets) * (max(rets) - min(rets)) / 60
    fig.add_trace(go.Scatter(
        x=x_range, y=pdf, name="Normal teórica",
        line=dict(color=COLORS["negative"], width=1.5, dash="dash")
    ), row=1, col=1)

    (osm, osr), (slope, intercept, r) = scipy_stats.probplot(rets)
    fig.add_trace(go.Scatter(
        x=list(osm), y=list(osr), mode="markers", name="Q-Q",
        marker=dict(color=color, size=3, opacity=0.6)
    ), row=1, col=2)
    fig.add_trace(go.Scatter(
        x=[min(osm), max(osm)],
        y=[slope * min(osm) + intercept, slope * max(osm) + intercept],
        name="Normal teórica", line=dict(color=COLORS["negative"], width=1.5, dash="dash"),
        showlegend=False
    ), row=1, col=2)

    fig.update_layout(height=380, title=f"Distribución estadística — {ticker}", hovermode="x")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Boxplot comparativo ──
    st.markdown('<div style="font-size:0.75rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#3B4460;margin-bottom:12px;">Comparativa del Portafolio</div>', unsafe_allow_html=True)

    fig3 = go.Figure()
    all_means = {}
    for t in TICKERS:
        d = fetch_rendimientos(t)
        if d:
            rets_t = [r for r in d["logaritmicos"] if r is not None]
            all_means[t] = np.mean(rets_t) * 100
            fig3.add_trace(go.Box(
                y=rets_t, name=t,
                marker_color=ticker_color(t),
                line_color=ticker_color(t),
                fillcolor=ticker_color(t).replace(")", ",0.15)").replace("rgb", "rgba") if "rgb" in ticker_color(t) else ticker_color(t),
                boxpoints="outliers",
                hovertemplate=f"<b>{t}</b><br>%{{y:.4f}}<extra></extra>"
            ))

    fig3.update_layout(height=320, title="Distribución de rendimientos logarítmicos diarios", showlegend=False)
    st.plotly_chart(fig3, use_container_width=True)

    if all_means:
        best_t = max(all_means, key=all_means.get)
        worst_t = min(all_means, key=all_means.get)
        st.markdown(f"""
        <div class="interpretation-box">
            <strong>Media más alta:</strong> {best_t} ({all_means[best_t]:+.4f}% diario) —
            <strong>Media más baja:</strong> {worst_t} ({all_means[worst_t]:+.4f}% diario).
            Los valores atípicos (outliers) visibles en el boxplot representan días de volatilidad extrema
            que deben considerarse al dimensionar posiciones.
        </div>
        """, unsafe_allow_html=True)