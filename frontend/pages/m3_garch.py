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

    with st.spinner("Estimando modelos de volatilidad..."):
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

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Pronóstico comparativo todos los modelos ──
    st.markdown('<div style="font-size:0.75rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#3B4460;margin-bottom:12px;">Pronóstico de Volatilidad — Comparación 5 días</div>', unsafe_allow_html=True)

    dias = [f"Día {i+1}" for i in range(5)]
    all_forecasts = {}
    for name, res in results.items():
        try:
            fc = res.forecast(horizon=5)
            fcast = fc.variance.values[-1] ** 0.5
            all_forecasts[name] = fcast.tolist()
        except Exception:
            pass

    if all_forecasts:
        fig2 = go.Figure()
        for idx, (name, fcast_vals) in enumerate(all_forecasts.items()):
            is_best = name == best
            fig2.add_trace(go.Scatter(
                x=dias,
                y=fcast_vals,
                name=f"{name}{' (mejor)' if is_best else ''}",
                mode="lines+markers",
                line=dict(
                    color=model_colors[list(specs.keys()).index(name)],
                    width=2.5 if is_best else 1.5,
                    dash="solid" if is_best else "dot",
                ),
                marker=dict(
                    size=9 if is_best else 6,
                    color=model_colors[list(specs.keys()).index(name)],
                    symbol="diamond" if is_best else "circle",
                ),
                opacity=1.0 if is_best else 0.65,
                hovertemplate=f"<b>{name}</b><br>%{{x}}: %{{y:.4f}}%<extra></extra>"
            ))

        # Línea de volatilidad actual como referencia
        last_vol = float(results[best].conditional_volatility.iloc[-1])
        fig2.add_hline(
            y=last_vol,
            line_dash="dot",
            line_color=COLORS["muted"],
            line_width=1,
            annotation_text=f"Vol. actual: {last_vol:.4f}%",
            annotation_font=dict(size=10, color=COLORS["muted"]),
            annotation_position="top left",
        )

        fig2.update_layout(
            height=320,
            title=f"Pronóstico de volatilidad diaria — todos los modelos vs vol. actual ({ticker})",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis_title="Volatilidad (%)",
        )
        st.plotly_chart(fig2, use_container_width=True)

        # Interpretación comparativa
        best_fcast = all_forecasts[best]
        avg_best = float(np.mean(best_fcast))
        trend = "al alza" if avg_best > last_vol else "a la baja"

        divergencias = {}
        for name, vals in all_forecasts.items():
            if name != best:
                diff = float(np.mean(vals)) - avg_best
                divergencias[name] = diff

        max_div_name = max(divergencias, key=lambda k: abs(divergencias[k])) if divergencias else None
        max_div_val = divergencias[max_div_name] if max_div_name else 0

        consensus = all(float(np.mean(v)) > last_vol for v in all_forecasts.values())
        consensus_down = all(float(np.mean(v)) <= last_vol for v in all_forecasts.values())

        st.markdown(f"""
        <div class="interpretation-box {'negative' if trend == 'al alza' else 'positive'}">
            <strong>Modelo ganador ({best}):</strong> proyecta volatilidad promedio de <strong>{avg_best:.4f}%</strong>
            en los próximos 5 días vs <strong>{last_vol:.4f}%</strong> actual — tendencia <strong>{trend}</strong>.
            {"Todos los modelos coinciden en un aumento de volatilidad — señal de alerta consistente." if consensus else
             "Todos los modelos coinciden en reducción de volatilidad — entorno de estabilización." if consensus_down else
             f"Los modelos divergen: {max_div_name} difiere en {max_div_val:+.4f}pp — incertidumbre en el pronóstico, usar el ganador como referencia principal."}
        </div>
        """, unsafe_allow_html=True)

        # Tabla comparativa
        st.markdown('<div style="font-size:0.75rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#3B4460;margin:16px 0 8px;">Tabla de pronósticos por modelo</div>', unsafe_allow_html=True)
        tabla = {"Modelo": [], "Día 1": [], "Día 2": [], "Día 3": [], "Día 4": [], "Día 5": [], "Promedio": [], "Tendencia": []}
        for name, vals in all_forecasts.items():
            tabla["Modelo"].append(f"{'★ ' if name == best else ''}{name}")
            for i, v in enumerate(vals):
                tabla[f"Día {i+1}"].append(f"{v:.4f}%")
            tabla["Promedio"].append(f"{np.mean(vals):.4f}%")
            tabla["Tendencia"].append("Alza" if np.mean(vals) > last_vol else "Baja")
        st.dataframe(pd.DataFrame(tabla), use_container_width=True, hide_index=True)