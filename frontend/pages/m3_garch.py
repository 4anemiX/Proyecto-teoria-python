import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd
from arch import arch_model
from data.client import fetch_precios, TICKERS
from utils.theme import ticker_color, COLORS


def render():
    st.markdown("""
    <div class="section-title">Modelos ARCH / GARCH</div>
    <div class="section-subtitle">Estimación y comparación de modelos de volatilidad condicional</div>
    """, unsafe_allow_html=True)

    ticker = st.selectbox("Activo", TICKERS)

    with st.spinner("Estimando modelos de volatilidad — esto puede tomar unos segundos..."):
        prices_data = fetch_precios(ticker)
        if not prices_data:
            st.warning("No se pudieron cargar los precios.")
            return
        closes = pd.Series(prices_data["close"], index=prices_data["fechas"]).dropna()
        ret = np.log(closes / closes.shift(1)).dropna() * 100

    specs = {
        "ARCH(1)":    {"vol": "ARCH",   "p": 1, "q": 0, "dist": "normal"},
        "GARCH(1,1)": {"vol": "GARCH",  "p": 1, "q": 1, "dist": "normal"},
        "GJR-GARCH":  {"vol": "GARCH",  "p": 1, "q": 1, "dist": "t", "o": 1},
        "EGARCH":     {"vol": "EGARCH", "p": 1, "q": 1, "dist": "normal"},
    }
    model_colors = [COLORS["accent"], COLORS["warning"], COLORS["positive"], "#A78BFA"]

    results = {}
    cols_info = st.columns(4)
    for idx, (name, sp) in enumerate(specs.items()):
        try:
            kwargs = {"vol": sp["vol"], "p": sp["p"], "dist": sp["dist"]}
            if sp["vol"] != "EGARCH":
                kwargs["q"] = sp.get("q", 0)
            if "o" in sp:
                kwargs["o"] = sp["o"]
            m = arch_model(ret, **kwargs)
            r = m.fit(disp="off", show_warning=False)
            results[name] = r
            with cols_info[idx]:
                st.markdown(f"""
                <div class="metric-card" style="--card-accent:{model_colors[idx]};">
                    <div class="metric-value" style="color:{model_colors[idx]}; font-size:1.1rem;">{r.aic:.1f}</div>
                    <div class="metric-label">{name}</div>
                    <div class="metric-label">AIC</div>
                    <div class="metric-change" style="color:{COLORS['muted']};">BIC {r.bic:.1f}</div>
                </div>
                """, unsafe_allow_html=True)
        except Exception as e:
            with cols_info[idx]:
                st.error(f"{name}: {e}")

    if not results:
        return

    best = min(results.items(), key=lambda x: x[1].aic)[0]
    best_idx = list(specs.keys()).index(best)

    st.markdown(f"""
    <div class="interpretation-box positive" style="margin-top:16px;">
        <strong>Mejor modelo por AIC:</strong> {best} — menor AIC implica mejor ajuste penalizado por complejidad.
        {"El EGARCH captura asimetría: las malas noticias generan más volatilidad que las buenas (efecto leverage)." if best == "EGARCH" else
         "El GJR-GARCH captura el efecto leverage — caídas generan más volatilidad que subidas equivalentes." if best == "GJR-GARCH" else
         "El GARCH(1,1) es el modelo más parsimónico con buen ajuste para este activo." if best == "GARCH(1,1)" else
         "El ARCH(1) sugiere que la volatilidad depende principalmente del shock más reciente."}
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Volatilidad condicional ──
    st.markdown('<div style="font-size:0.75rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#3B4460;margin-bottom:12px;">Volatilidad Condicional Estimada</div>', unsafe_allow_html=True)

    fig = go.Figure()
    for idx, (name, res) in enumerate(results.items()):
        visible = True if name == best else "legendonly"
        fig.add_trace(go.Scatter(
            x=[str(d)[:10] for d in res.conditional_volatility.index],
            y=res.conditional_volatility.tolist(),
            name=name,
            line=dict(color=model_colors[idx], width=1.8 if name == best else 1.2),
            opacity=1.0 if name == best else 0.6,
            visible=visible,
            hovertemplate=f"<b>{name}</b><br>%{{x}}<br>Vol: %{{y:.4f}}%<extra></extra>"
        ))

    fig.update_layout(height=380, title=f"Volatilidad condicional — {ticker}", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    # ── Pronóstico 5 días ──
    st.markdown('<div style="font-size:0.75rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#3B4460;margin-bottom:12px;">Pronóstico de Volatilidad — 5 días</div>', unsafe_allow_html=True)

    best_model = results[best]
    forecast = best_model.forecast(horizon=5)
    fcast = forecast.variance.values[-1] ** 0.5

    fig2 = go.Figure(go.Bar(
        x=[f"Día {i+1}" for i in range(5)],
        y=fcast.tolist(),
        marker_color=[model_colors[best_idx]] * 5,
        marker_line_color="rgba(0,0,0,0)",
        opacity=0.85,
        hovertemplate="Día %{x}<br>Vol. esperada: %{y:.4f}%<extra></extra>"
    ))
    fig2.update_layout(height=240, title=f"Pronóstico ({best}) — volatilidad diaria esperada en %")
    st.plotly_chart(fig2, use_container_width=True)

    avg_fcast = float(np.mean(fcast))
    last_vol = float(best_model.conditional_volatility.iloc[-1])
    trend = "al alza" if avg_fcast > last_vol else "a la baja"
    st.markdown(f"""
    <div class="interpretation-box">
        <strong>Pronóstico:</strong> El modelo {best} estima una volatilidad promedio de <strong>{avg_fcast:.4f}%</strong>
        para los próximos 5 días, frente a <strong>{last_vol:.4f}%</strong> de volatilidad condicional actual.
        La tendencia es <strong>{trend}</strong>.
        {"Una volatilidad creciente implica mayor incertidumbre — reducir exposición o usar coberturas." if trend == "al alza" else
         "Una volatilidad decreciente sugiere estabilización del precio — condiciones favorables para tomar posición."}
    </div>
    """, unsafe_allow_html=True)