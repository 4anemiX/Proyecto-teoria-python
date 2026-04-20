import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd
from data.client import fetch_macro, fetch_capm, fetch_precios, TICKERS, BENCHMARK
from utils.theme import ticker_color, COLORS


def _interpret_macro(macro: dict) -> tuple[str, str]:
    vix = macro.get("vix", 20)
    if vix > 30:
        vix_msg = f"VIX en <strong>{vix:.1f}</strong> indica alta volatilidad de mercado — entorno de risk-off, reducir exposición."
        css = "negative"
    elif vix > 20:
        vix_msg = f"VIX en <strong>{vix:.1f}</strong> refleja volatilidad moderada — mercado en alerta pero no en pánico."
        css = "warning"
    else:
        vix_msg = f"VIX en <strong>{vix:.1f}</strong> indica mercado tranquilo — entorno favorable para riesgo."
        css = "positive"

    rf = macro.get("risk_free_rate", 0) * 100
    tnx = macro.get("tnx", 0)
    usdcop = macro.get("usdcop", 0)
    eurusd = macro.get("eurusd", 0)

    env_msg = (
        f"Tasa libre de riesgo en {rf:.2f}% · T-Note 10Y en {tnx:.2f}% "
        f"({'curva invertida — señal recesiva' if rf > tnx else 'curva normal — ciclo expansivo'}). "
        f"USD/COP {usdcop:,.0f} · EUR/USD {eurusd:.4f}."
    )
    return f"{vix_msg} {env_msg}", css


def render():
    st.markdown("""
    <div class="section-title">Macro & Benchmark</div>
    <div class="section-subtitle">Entorno macroeconómico global — tasas, divisas, volatilidad y desempeño relativo al S&P 500</div>
    """, unsafe_allow_html=True)

    macro = fetch_macro()
    if not macro:
        st.warning("No se pudieron cargar los datos macroeconómicos.")
        return

    # ── Indicadores macro ──
    macro_items = [
        ("Tasa Libre Riesgo", f"{macro['risk_free_rate']*100:.2f}%", COLORS["accent"]),
        ("S&P 500", f"${macro['sp500_return']:,.0f}", COLORS["positive"]),
        ("VIX", f"{macro['vix']:.2f}", COLORS["negative"] if macro["vix"] > 25 else COLORS["warning"]),
        ("USD/COP", f"{macro['usdcop']:,.0f}", COLORS["muted"]),
        ("EUR/USD", f"{macro['eurusd']:.4f}", COLORS["muted"]),
        ("T-Note 10Y", f"{macro['tnx']:.2f}%", COLORS["warning"]),
    ]
    cols = st.columns(6)
    for col, (label, val, color) in zip(cols, macro_items):
        with col:
            st.markdown(f"""
            <div class="metric-card" style="--card-accent:{color};">
                <div class="metric-value" style="color:{color}; font-size:1.1rem;">{val}</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    interp_msg, interp_class = _interpret_macro(macro)
    st.markdown(f'<div class="interpretation-box {interp_class}" style="margin-top:16px;">{interp_msg}</div>', unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Alpha, Tracking Error, Information Ratio ──
    st.markdown('<div style="font-size:0.75rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#3B4460;margin-bottom:12px;">Alpha de Jensen · Tracking Error · Information Ratio</div>', unsafe_allow_html=True)

    capm_data = fetch_capm()
    rows = []
    if capm_data:
        bench_data = fetch_precios(BENCHMARK)
        bench_ret = None
        if bench_data:
            bench_close = pd.Series(bench_data["close"]).dropna()
            bench_ret = bench_close.pct_change().dropna()

        for d in capm_data:
            if "error" in d:
                continue
            t = d["ticker"]
            price_data = fetch_precios(t)
            if price_data and bench_ret is not None:
                close = pd.Series(price_data["close"]).dropna()
                asset_ret = close.pct_change().dropna()
                n = min(len(asset_ret), len(bench_ret))
                ar = asset_ret.values[-n:]
                br = bench_ret.values[-n:]
                te = float(np.std(ar - br) * np.sqrt(252))
                excess = float(np.mean(ar - br) * 252)
                ir = excess / te if te > 0 else 0.0
                rows.append({
                    "Ticker": t,
                    "Alpha Jensen": f"{d['alpha']*100:+.3f}%",
                    "Beta": f"{d['beta']:.3f}",
                    "Tracking Error": f"{te*100:.2f}%",
                    "Information Ratio": f"{ir:.3f}",
                    "R²": f"{d['r_squared']:.3f}",
                })

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # Interpretación
        alpha_pos = [r for r in rows if float(r["Alpha Jensen"].replace("%", "").replace("+", "")) > 0]
        ir_vals = [float(r["Information Ratio"]) for r in rows]
        avg_ir = np.mean(ir_vals) if ir_vals else 0
        st.markdown(f"""
        <div class="interpretation-box">
            <strong>Alpha de Jensen:</strong> {len(alpha_pos)} de {len(rows)} activos generan alpha positivo —
            retorno superior al predicho por el CAPM.
            <strong>Information Ratio promedio:</strong> {avg_ir:.3f}
            {"(IR > 0.5 es bueno — el portafolio gestiona activamente con efectividad)." if avg_ir > 0.5 else
             "(IR entre 0 y 0.5 — gestión activa marginal frente al benchmark)." if avg_ir > 0 else
             "(IR negativo — el portafolio no supera al benchmark ajustado por tracking error)."}
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Dispersión vs SPY ──
    st.markdown('<div style="font-size:0.75rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#3B4460;margin-bottom:12px;">Correlación con el S&P 500 (SPY)</div>', unsafe_allow_html=True)

    fig = go.Figure()
    spy_data = fetch_precios(BENCHMARK)
    if spy_data:
        close_spy = pd.Series(spy_data["close"]).pct_change().dropna()
        for t in TICKERS:
            pd_data = fetch_precios(t)
            if pd_data:
                close_t = pd.Series(pd_data["close"]).pct_change().dropna()
                n = min(len(close_t), len(close_spy))
                x_vals = close_spy.values[-n:].tolist()
                y_vals = close_t.values[-n:].tolist()
                fig.add_trace(go.Scatter(
                    x=x_vals, y=y_vals,
                    mode="markers", name=t,
                    marker=dict(color=ticker_color(t), size=4, opacity=0.45),
                    hovertemplate=f"<b>{t}</b><br>SPY: %{{x:.3%}}<br>{t}: %{{y:.3%}}<extra></extra>"
                ))

    fig.update_layout(
        height=380,
        title="Dispersión de rendimientos diarios vs SPY — pendiente ≈ Beta",
        xaxis_title="Rendimiento SPY",
        yaxis_title="Rendimiento activo",
        xaxis=dict(tickformat=".1%"),
        yaxis=dict(tickformat=".1%"),
        hovermode="closest",
    )
    st.plotly_chart(fig, use_container_width=True)