import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings("ignore")

# ── Configuración ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RiskLab — Portafolio Economía Digital",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_URL = "http://localhost:8000"
TICKERS = ["ACN", "MSFT", "NVDA", "KO", "JPM"]
BENCHMARK = "SPY"
ALL_TICKERS = TICKERS + [BENCHMARK]
COLORS = {
    "ACN":  "#6366f1",
    "MSFT": "#0ea5e9",
    "NVDA": "#10b981",
    "KO":   "#f59e0b",
    "JPM":  "#ef4444",
    "SPY":  "#8b5cf6",
}
SECTOR_MAP = {
    "ACN": "Consultoría Tech",
    "MSFT": "Cloud / IA",
    "NVDA": "Semiconductores",
    "KO": "Consumo Defensivo",
    "JPM": "Finanzas",
    "SPY": "Benchmark",
}

# ── CSS personalizado ──────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .main { background: #f8fafc; }
    .stMetric { background: white; border-radius: 12px; padding: 1rem; box-shadow: 0 1px 10px rgba(0,0,0,0.06); }
    .stMetric label { color: #64748b !important; font-size: 0.75rem !important; font-weight: 600 !important; text-transform: uppercase; letter-spacing: 0.05em; }
    div[data-testid="stMetricValue"] { font-size: 1.6rem !important; font-weight: 700 !important; }
    .section-header { background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); color: white; padding: 1rem 1.5rem; border-radius: 12px; margin-bottom: 1.5rem; }
    .signal-buy  { background: #dcfce7; color: #166534; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 700; }
    .signal-sell { background: #fee2e2; color: #991b1b; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 700; }
    .signal-neutral { background: #f1f5f9; color: #475569; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 700; }
    .sidebar .sidebar-content { background: #1e1b4b; }
    div[data-testid="stSidebar"] { background: linear-gradient(180deg, #1e1b4b 0%, #312e81 100%); }
    div[data-testid="stSidebar"] * { color: white !important; }
    h1, h2, h3 { color: #1e1b4b; }
</style>
""", unsafe_allow_html=True)

# ── Helper: llamar API ─────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def api_get(endpoint: str):
    try:
        r = requests.get(f"{API_URL}{endpoint}", timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

@st.cache_data(ttl=300)
def api_post(endpoint: str, payload: dict):
    try:
        r = requests.post(f"{API_URL}{endpoint}", json=payload, timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 RiskLab USTA")
    st.markdown("**Portafolio Economía Digital**")
    st.markdown("---")
    page = st.radio("Navegación", [
        "🏠 Resumen",
        "📈 Precios & Técnico",
        "📉 Rendimientos",
        "🔥 Volatilidad GARCH",
        "⚠️ VaR & CVaR",
        "📐 CAPM & Beta",
        "🎯 Frontera Eficiente",
        "🚨 Señales & Alertas",
        "🌍 Macro",
    ])
    st.markdown("---")
    selected_ticker = st.selectbox("Activo individual", TICKERS)
    period = st.selectbox("Periodo histórico", ["6mo", "1y", "2y", "3y"], index=2)
    conf_level = st.slider("Confianza VaR", 0.90, 0.99, 0.95, 0.01)
    st.markdown("---")
    st.markdown("*Teoría del Riesgo · USTA*")

# ── Página: Resumen ────────────────────────────────────────────────────────────
if page == "🏠 Resumen":
    st.markdown('<div class="section-header"><h1 style="margin:0;color:white;">🏦 RiskLab — Portafolio Economía Digital</h1><p style="margin:4px 0 0;opacity:0.8;font-size:14px;">ACN · MSFT · NVDA · KO · JPM | Benchmark: SPY</p></div>', unsafe_allow_html=True)

    # Precios actuales
    cols = st.columns(len(ALL_TICKERS))
    for i, ticker in enumerate(ALL_TICKERS):
        data = api_get(f"/precios/{ticker}?period=5d")
        if "error" not in data and len(data.get("precios", [])) >= 2:
            last = data["precios"][-1]
            prev = data["precios"][-2]
            delta_pct = (last / prev - 1) * 100
            cols[i].metric(ticker, f"${last:,.2f}", f"{delta_pct:+.2f}%")
        else:
            cols[i].metric(ticker, "N/A", "—")

    st.markdown("---")

    # Gráfico de precios normalizados (todos los activos)
    st.subheader("📈 Precios normalizados (base 100)")
    fig = go.Figure()
    for ticker in ALL_TICKERS:
        data = api_get(f"/precios/{ticker}?period={period}")
        if "error" not in data and data.get("precios"):
            prices = data["precios"]
            fechas = data["fechas"]
            normalized = [p / prices[0] * 100 for p in prices]
            fig.add_trace(go.Scatter(
                x=fechas, y=normalized, name=ticker,
                line=dict(color=COLORS[ticker], width=2),
                hovertemplate=f"<b>{ticker}</b><br>%{{x}}<br>Índice: %{{y:.1f}}<extra></extra>"
            ))
    fig.update_layout(
        height=400,
        xaxis_title="Fecha",
        yaxis_title="Precio normalizado (base 100)",
        legend=dict(orientation="h", y=-0.2),
        plot_bgcolor="white",
        paper_bgcolor="white",
        hovermode="x unified",
        margin=dict(l=0, r=0, t=10, b=40),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#f1f5f9")
    fig.update_yaxes(showgrid=True, gridcolor="#f1f5f9")
    st.plotly_chart(fig, use_container_width=True)

    # Métricas de rendimiento
    st.subheader("📊 Rendimientos anualizados")
    ret_data = []
    for ticker in TICKERS:
        d = api_get(f"/rendimientos/{ticker}?period=2y")
        if "error" not in d:
            ann_ret = d["media"] * 252
            ann_vol = d["std"] * np.sqrt(252)
            sharpe = ann_ret / ann_vol if ann_vol > 0 else 0
            ret_data.append({
                "Ticker": ticker,
                "Sector": SECTOR_MAP[ticker],
                "Ret. Anual (%)": f"{ann_ret*100:.2f}%",
                "Volatilidad (%)": f"{ann_vol*100:.2f}%",
                "Sharpe": f"{sharpe:.2f}",
                "Skewness": f"{d['skewness']:.2f}",
                "Kurtosis": f"{d['kurtosis']:.2f}",
            })
    if ret_data:
        df_ret = pd.DataFrame(ret_data)
        st.dataframe(df_ret, use_container_width=True, hide_index=True)

# ── Página: Precios & Técnico ──────────────────────────────────────────────────
elif page == "📈 Precios & Técnico":
    st.markdown(f'<div class="section-header"><h2 style="margin:0;color:white;">📈 Análisis Técnico — {selected_ticker}</h2></div>', unsafe_allow_html=True)

    price_data = api_get(f"/precios/{selected_ticker}?period={period}")
    ind_data = api_get(f"/indicadores/{selected_ticker}")

    if "error" not in price_data and "error" not in ind_data:
        df_p = pd.DataFrame({"fecha": price_data["fechas"], "precio": price_data["precios"]})
        df_p["fecha"] = pd.to_datetime(df_p["fecha"])

        # Métricas
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Precio actual", f"${ind_data['last_price']:,.2f}")
        c2.metric("SMA 20", f"${ind_data['sma_20']:,.2f}")
        c3.metric("SMA 50", f"${ind_data['sma_50']:,.2f}")
        c4.metric("RSI (14)", f"{ind_data['rsi']:.1f}")
        signal = ind_data["signal"]
        sig_color = "🟢" if signal == "COMPRA" else ("🔴" if signal == "VENTA" else "⚪")
        c5.metric("Señal", f"{sig_color} {signal}")

        # Gráfico con Bandas de Bollinger
        prices = np.array(df_p["precio"])
        sma20_arr = pd.Series(prices).rolling(20).mean()
        std20_arr = pd.Series(prices).rolling(20).std()
        bb_up = sma20_arr + 2 * std20_arr
        bb_lo = sma20_arr - 2 * std20_arr
        sma50_arr = pd.Series(prices).rolling(50).mean()

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                            row_heights=[0.7, 0.3],
                            subplot_titles=[f"{selected_ticker} — Precio con Indicadores", "RSI (14)"])

        fig.add_trace(go.Scatter(x=df_p["fecha"], y=bb_up, line=dict(width=0), showlegend=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p["fecha"], y=bb_lo, fill="tonexty", fillcolor="rgba(99,102,241,0.1)",
                                 line=dict(width=0), name="Bandas Bollinger"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p["fecha"], y=df_p["precio"],
                                 line=dict(color=COLORS[selected_ticker], width=2), name="Precio"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p["fecha"], y=sma20_arr,
                                 line=dict(color="#f59e0b", width=1.5, dash="dash"), name="SMA 20"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p["fecha"], y=sma50_arr,
                                 line=dict(color="#ef4444", width=1.5, dash="dash"), name="SMA 50"), row=1, col=1)

        # RSI
        delta = pd.Series(prices).diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rsi_arr = 100 - 100 / (1 + gain / loss)
        fig.add_trace(go.Scatter(x=df_p["fecha"], y=rsi_arr,
                                 line=dict(color="#8b5cf6", width=1.5), name="RSI"), row=2, col=1)
        fig.add_hline(y=70, line=dict(color="red", dash="dot"), row=2, col=1)
        fig.add_hline(y=30, line=dict(color="green", dash="dot"), row=2, col=1)

        fig.update_layout(height=600, plot_bgcolor="white", paper_bgcolor="white",
                          legend=dict(orientation="h", y=-0.05), hovermode="x unified",
                          margin=dict(l=0, r=0, t=30, b=0))
        fig.update_xaxes(showgrid=True, gridcolor="#f1f5f9")
        fig.update_yaxes(showgrid=True, gridcolor="#f1f5f9")
        st.plotly_chart(fig, use_container_width=True)

        # MACD
        prices_s = pd.Series(prices)
        ema12 = prices_s.ewm(span=12).mean()
        ema26 = prices_s.ewm(span=26).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9).mean()
        histogram = macd_line - signal_line

        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=df_p["fecha"], y=histogram,
                              marker_color=["#10b981" if h >= 0 else "#ef4444" for h in histogram],
                              name="Histograma MACD"))
        fig2.add_trace(go.Scatter(x=df_p["fecha"], y=macd_line,
                                  line=dict(color="#6366f1", width=1.5), name="MACD"))
        fig2.add_trace(go.Scatter(x=df_p["fecha"], y=signal_line,
                                  line=dict(color="#f59e0b", width=1.5), name="Señal"))
        fig2.update_layout(title="MACD", height=250, plot_bgcolor="white", paper_bgcolor="white",
                           hovermode="x unified", margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig2, use_container_width=True)

# ── Página: Rendimientos ───────────────────────────────────────────────────────
elif page == "📉 Rendimientos":
    st.markdown('<div class="section-header"><h2 style="margin:0;color:white;">📉 Rendimientos y Propiedades Empíricas</h2></div>', unsafe_allow_html=True)

    d = api_get(f"/rendimientos/{selected_ticker}?period={period}")
    if "error" not in d:
        rets = np.array(d["rendimientos"])
        fechas = pd.to_datetime(d["fechas"])

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Retorno medio diario", f"{d['media']*100:.4f}%")
        c2.metric("Volatilidad diaria", f"{d['std']*100:.4f}%")
        c3.metric("Skewness", f"{d['skewness']:.4f}")
        c4.metric("Kurtosis exceso", f"{d['kurtosis']:.4f}")

        fig = make_subplots(rows=1, cols=2,
                            subplot_titles=["Serie de rendimientos logarítmicos", "Distribución vs Normal"])
        fig.add_trace(go.Scatter(x=fechas, y=rets, mode="lines",
                                 line=dict(color=COLORS[selected_ticker], width=1), name="Retornos"), row=1, col=1)
        fig.add_hline(y=0, line=dict(color="gray", dash="dot"), row=1, col=1)

        # Histograma + Normal
        from scipy import stats as sc
        fig.add_trace(go.Histogram(x=rets, nbinsx=60, name="Distribución empírica",
                                   marker_color=COLORS[selected_ticker], opacity=0.7,
                                   histnorm="probability density"), row=1, col=2)
        x_range = np.linspace(rets.min(), rets.max(), 200)
        norm_y = sc.norm.pdf(x_range, d["media"], d["std"])
        fig.add_trace(go.Scatter(x=x_range, y=norm_y, name="Normal teórica",
                                 line=dict(color="red", width=2)), row=1, col=2)

        fig.update_layout(height=400, plot_bgcolor="white", paper_bgcolor="white",
                          showlegend=True, hovermode="x", margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)

        # Correlación
        st.subheader("🔗 Matriz de correlación del portafolio")
        all_rets = {}
        for t in ALL_TICKERS:
            dd = api_get(f"/rendimientos/{t}?period={period}")
            if "error" not in dd:
                all_rets[t] = dd["rendimientos"]

        if len(all_rets) >= 2:
            min_len = min(len(v) for v in all_rets.values())
            df_rets = pd.DataFrame({k: v[-min_len:] for k, v in all_rets.items()})
            corr = df_rets.corr()
            fig_corr = px.imshow(corr, text_auto=".2f", color_continuous_scale="RdYlGn",
                                 zmin=-1, zmax=1, aspect="auto",
                                 title="Correlación de rendimientos logarítmicos")
            fig_corr.update_layout(height=380, margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig_corr, use_container_width=True)

# ── Página: GARCH ──────────────────────────────────────────────────────────────
elif page == "🔥 Volatilidad GARCH":
    st.markdown(f'<div class="section-header"><h2 style="margin:0;color:white;">🔥 Modelos ARCH/GARCH — {selected_ticker}</h2></div>', unsafe_allow_html=True)

    garch_data = api_get(f"/garch/{selected_ticker}")
    ret_data = api_get(f"/rendimientos/{selected_ticker}?period={period}")

    if "error" not in garch_data and "error" not in ret_data:
        c1, c2, c3 = st.columns(3)
        c1.metric("AIC", f"{garch_data.get('aic', 'N/A')}")
        c2.metric("BIC", f"{garch_data.get('bic', 'N/A')}")
        vf = garch_data.get("vol_forecast_5d", [])
        if vf and vf[0]:
            c3.metric("Vol. forecast (1d)", f"{vf[0]*100:.2f}%")

        # Volatilidad condicional (rolling como proxy visual)
        rets = np.array(ret_data["rendimientos"])
        fechas = pd.to_datetime(ret_data["fechas"])
        roll_vol = pd.Series(rets).rolling(21).std() * np.sqrt(252) * 100

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                            subplot_titles=["Rendimientos logarítmicos", "Volatilidad condicional (rolling 21d anualizada)"])
        fig.add_trace(go.Bar(x=fechas, y=rets * 100,
                             marker_color=[COLORS[selected_ticker] if r >= 0 else "#ef4444" for r in rets],
                             name="Retornos (%)"), row=1, col=1)
        fig.add_trace(go.Scatter(x=fechas, y=roll_vol,
                                 line=dict(color="#f59e0b", width=2), name="Volatilidad (%)"), row=2, col=1)

        fig.update_layout(height=500, plot_bgcolor="white", paper_bgcolor="white",
                          showlegend=False, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)

        # Parámetros GARCH
        if garch_data.get("params"):
            st.subheader("Parámetros estimados GARCH(1,1)")
            params_df = pd.DataFrame([
                {"Parámetro": k, "Valor": f"{v:.6f}"}
                for k, v in garch_data["params"].items()
            ])
            st.dataframe(params_df, use_container_width=True, hide_index=True)

        # Pronóstico 5 días
        if vf and any(v for v in vf):
            st.subheader("📅 Pronóstico de volatilidad (5 días)")
            fig2 = go.Figure(go.Bar(
                x=[f"Día {i+1}" for i in range(len(vf))],
                y=[v * 100 if v else 0 for v in vf],
                marker_color="#6366f1",
                text=[f"{v*100:.3f}%" if v else "N/A" for v in vf],
                textposition="outside",
            ))
            fig2.update_layout(height=280, plot_bgcolor="white", paper_bgcolor="white",
                               yaxis_title="Volatilidad (%)", margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig2, use_container_width=True)

# ── Página: VaR & CVaR ─────────────────────────────────────────────────────────
elif page == "⚠️ VaR & CVaR":
    st.markdown('<div class="section-header"><h2 style="margin:0;color:white;">⚠️ Value at Risk (VaR) y Expected Shortfall (CVaR)</h2></div>', unsafe_allow_html=True)

    n = len(TICKERS)
    default_w = [1/n] * n
    weights = default_w

    st.info(f"📌 Portafolio equiponderado: {', '.join([f'{t}: {w:.0%}' for t, w in zip(TICKERS, weights)])}")

    var_resp = api_post("/var", {
        "tickers": TICKERS,
        "weights": weights,
        "confidence_level": conf_level
    })

    if "error" not in var_resp:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(f"VaR Histórico ({conf_level:.0%})", f"{var_resp['var_historico']*100:.3f}%")
        c2.metric(f"VaR Paramétrico ({conf_level:.0%})", f"{var_resp['var_parametrico']*100:.3f}%")
        c3.metric(f"VaR Monte Carlo ({conf_level:.0%})", f"{var_resp['var_montecarlo']*100:.3f}%")
        c4.metric("CVaR (Expected Shortfall)", f"{var_resp['cvar']*100:.3f}%")

        # Gráfico comparativo VaR
        fig = go.Figure(go.Bar(
            x=["VaR Histórico", "VaR Paramétrico", "VaR Monte Carlo", "CVaR"],
            y=[var_resp["var_historico"]*100, var_resp["var_parametrico"]*100,
               var_resp["var_montecarlo"]*100, var_resp["cvar"]*100],
            marker_color=["#6366f1", "#0ea5e9", "#10b981", "#ef4444"],
            text=[f"{v*100:.3f}%" for v in [var_resp["var_historico"], var_resp["var_parametrico"],
                                              var_resp["var_montecarlo"], var_resp["cvar"]]],
            textposition="outside",
        ))
        fig.update_layout(title=f"Comparación de métricas de riesgo (confianza: {conf_level:.0%})",
                          yaxis_title="Pérdida máxima estimada (%)",
                          height=350, plot_bgcolor="white", paper_bgcolor="white",
                          margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)

        # Distribución con VaR marcado
        st.subheader("📊 Distribución de rendimientos del portafolio")
        all_rets = {}
        for t in TICKERS:
            dd = api_get(f"/rendimientos/{t}?period={period}")
            if "error" not in dd:
                all_rets[t] = np.array(dd["rendimientos"])

        if all_rets:
            min_len = min(len(v) for v in all_rets.values())
            port_rets = sum(all_rets[t][-min_len:] * w for t, w in zip(TICKERS, weights))

            fig2 = go.Figure()
            fig2.add_trace(go.Histogram(x=port_rets * 100, nbinsx=80, name="Rendimientos",
                                        marker_color="#6366f1", opacity=0.7, histnorm="probability density"))
            fig2.add_vline(x=-var_resp["var_historico"]*100, line=dict(color="#f59e0b", dash="dash", width=2),
                           annotation_text=f"VaR Hist. {conf_level:.0%}", annotation_position="top right")
            fig2.add_vline(x=-var_resp["cvar"]*100, line=dict(color="#ef4444", dash="dash", width=2),
                           annotation_text=f"CVaR {conf_level:.0%}", annotation_position="top left")
            fig2.update_layout(height=350, plot_bgcolor="white", paper_bgcolor="white",
                               xaxis_title="Rendimiento diario (%)",
                               yaxis_title="Densidad", margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig2, use_container_width=True)

# ── Página: CAPM ───────────────────────────────────────────────────────────────
elif page == "📐 CAPM & Beta":
    st.markdown('<div class="section-header"><h2 style="margin:0;color:white;">📐 CAPM y Riesgo Sistemático</h2></div>', unsafe_allow_html=True)

    capm_results = []
    for t in TICKERS:
        d = api_get(f"/capm/{t}")
        if "error" not in d:
            capm_results.append(d)

    if capm_results:
        # Tabla
        df_capm = pd.DataFrame([{
            "Ticker": d["ticker"],
            "Beta (β)": f"{d['beta']:.4f}",
            "Alpha (α) anual": f"{d['alpha']*100:.2f}%",
            "Ret. esperado CAPM": f"{d['expected_return']*100:.2f}%",
            "R²": f"{d['r_squared']:.4f}",
        } for d in capm_results])
        st.dataframe(df_capm, use_container_width=True, hide_index=True)

        # Gráfico Beta
        fig = go.Figure()
        betas = [d["beta"] for d in capm_results]
        tickers_capm = [d["ticker"] for d in capm_results]
        colors_bar = [COLORS[t] for t in tickers_capm]
        fig.add_trace(go.Bar(x=tickers_capm, y=betas,
                             marker_color=colors_bar,
                             text=[f"β={b:.3f}" for b in betas],
                             textposition="outside"))
        fig.add_hline(y=1.0, line=dict(color="gray", dash="dash"),
                      annotation_text="β = 1 (mercado)")
        fig.update_layout(title="Beta (β) por activo vs S&P 500",
                          yaxis_title="Beta", height=350,
                          plot_bgcolor="white", paper_bgcolor="white",
                          margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)

        # Security Market Line
        st.subheader("📈 Security Market Line (SML)")
        rf = capm_results[0]["risk_free_rate"]
        rm = capm_results[0]["market_return"]
        beta_range = np.linspace(0, 2, 100)
        sml = rf + beta_range * (rm - rf)

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=beta_range, y=sml * 100,
                                  line=dict(color="gray", dash="dash"), name="SML"))
        for d in capm_results:
            fig2.add_trace(go.Scatter(
                x=[d["beta"]], y=[d["expected_return"] * 100],
                mode="markers+text",
                marker=dict(color=COLORS[d["ticker"]], size=14, symbol="circle"),
                text=[d["ticker"]], textposition="top center",
                name=d["ticker"]
            ))
        fig2.update_layout(xaxis_title="Beta (β)", yaxis_title="Rendimiento esperado (%)",
                           height=400, plot_bgcolor="white", paper_bgcolor="white",
                           legend=dict(orientation="h", y=-0.2),
                           margin=dict(l=0, r=0, t=10, b=40))
        st.plotly_chart(fig2, use_container_width=True)

# ── Página: Frontera Eficiente ─────────────────────────────────────────────────
elif page == "🎯 Frontera Eficiente":
    st.markdown('<div class="section-header"><h2 style="margin:0;color:white;">🎯 Optimización de Portafolio — Markowitz</h2></div>', unsafe_allow_html=True)

    with st.spinner("Calculando frontera eficiente..."):
        n = len(TICKERS)
        frontier = api_post("/frontera-eficiente", {
            "tickers": TICKERS,
            "weights": [1/n] * n,
            "confidence_level": 0.95
        })

    if "error" not in frontier:
        vols = frontier["frontier"]["volatility"]
        rets = frontier["frontier"]["returns"]
        sharpes = frontier["frontier"]["sharpe"]
        opt = frontier["optimal_portfolio"]

        c1, c2, c3 = st.columns(3)
        c1.metric("Sharpe ratio óptimo", f"{frontier['optimal_sharpe']:.4f}")
        c2.metric("Retorno óptimo", f"{frontier['optimal_return']*100:.2f}%")
        c3.metric("Volatilidad óptima", f"{frontier['optimal_volatility']*100:.2f}%")

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[v*100 for v in vols],
            y=[r*100 for r in rets],
            mode="markers",
            marker=dict(color=sharpes, colorscale="Viridis", size=3, opacity=0.5,
                        colorbar=dict(title="Sharpe")),
            name="Portafolios simulados",
            hovertemplate="Vol: %{x:.2f}%<br>Ret: %{y:.2f}%<extra></extra>"
        ))
        fig.add_trace(go.Scatter(
            x=[frontier["optimal_volatility"]*100],
            y=[frontier["optimal_return"]*100],
            mode="markers+text",
            marker=dict(color="red", size=18, symbol="star"),
            text=["Óptimo Sharpe"], textposition="top right",
            name="Portafolio óptimo"
        ))
        fig.update_layout(title="Frontera Eficiente de Markowitz (2,000 portafolios simulados)",
                          xaxis_title="Volatilidad anualizada (%)",
                          yaxis_title="Retorno anualizado (%)",
                          height=500, plot_bgcolor="white", paper_bgcolor="white",
                          margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)

        # Composición óptima
        st.subheader("🥧 Composición del portafolio óptimo")
        fig2 = go.Figure(go.Pie(
            labels=list(opt.keys()),
            values=[v*100 for v in opt.values()],
            marker=dict(colors=[COLORS.get(t, "#999") for t in opt.keys()]),
            textinfo="label+percent",
            hole=0.4,
        ))
        fig2.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig2, use_container_width=True)

# ── Página: Señales & Alertas ──────────────────────────────────────────────────
elif page == "🚨 Señales & Alertas":
    st.markdown('<div class="section-header"><h2 style="margin:0;color:white;">🚨 Señales y Alertas Automatizadas</h2></div>', unsafe_allow_html=True)

    alertas = api_get("/alertas")
    if "error" not in alertas:
        for a in alertas.get("alertas", []):
            sig = a["signal"]
            color = "#dcfce7" if sig == "COMPRA" else ("#fee2e2" if sig == "VENTA" else "#f1f5f9")
            icon = "🟢" if sig == "COMPRA" else ("🔴" if sig == "VENTA" else "⚪")
            with st.container():
                st.markdown(f"""
                <div style="background:{color};border-radius:12px;padding:14px 20px;margin-bottom:10px;display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <strong style="font-size:16px;">{icon} {a['ticker']}</strong>
                        <span style="margin-left:12px;color:#64748b;font-size:13px;">Precio: <b>${a['last_price']:,.2f}</b> | RSI: <b>{a['rsi']:.1f}</b> | SMA50: <b>${a['sma_50']:,.2f}</b></span>
                    </div>
                    <div style="font-weight:700;font-size:14px;">{sig}</div>
                </div>
                """, unsafe_allow_html=True)

    st.subheader("📊 RSI del portafolio")
    rsi_vals, tickers_rsi = [], []
    for t in TICKERS:
        d = api_get(f"/indicadores/{t}")
        if "error" not in d:
            rsi_vals.append(d["rsi"])
            tickers_rsi.append(t)

    if rsi_vals:
        colors_rsi = ["#ef4444" if r > 70 else ("#10b981" if r < 30 else "#6366f1") for r in rsi_vals]
        fig = go.Figure(go.Bar(x=tickers_rsi, y=rsi_vals,
                               marker_color=colors_rsi,
                               text=[f"{r:.1f}" for r in rsi_vals],
                               textposition="outside"))
        fig.add_hline(y=70, line=dict(color="red", dash="dot"), annotation_text="Sobrecomprado (70)")
        fig.add_hline(y=30, line=dict(color="green", dash="dot"), annotation_text="Sobrevendido (30)")
        fig.update_layout(title="RSI por activo", yaxis_title="RSI", yaxis_range=[0, 100],
                          height=350, plot_bgcolor="white", paper_bgcolor="white",
                          margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)

# ── Página: Macro ──────────────────────────────────────────────────────────────
elif page == "🌍 Macro":
    st.markdown('<div class="section-header"><h2 style="margin:0;color:white;">🌍 Contexto Macroeconómico</h2></div>', unsafe_allow_html=True)

    macro = api_get("/macro")
    if "error" not in macro:
        c1, c2, c3 = st.columns(3)
        c1.metric("Tasa libre de riesgo (Rf)", f"{macro['risk_free_rate']*100:.2f}%")
        c2.metric("Fed Funds Rate", f"{macro['fed_funds_rate']*100:.2f}%" if macro.get("fed_funds_rate") else "N/A")
        c3.metric("Fuente", macro.get("source", "FRED"))

    st.subheader("📊 Retorno acumulado vs SPY (benchmark)")
    fig = go.Figure()
    spy_data = api_get(f"/precios/SPY?period={period}")
    if "error" not in spy_data:
        spy_prices = spy_data["precios"]
        spy_ret = [(p / spy_prices[0] - 1) * 100 for p in spy_prices]
        fig.add_trace(go.Scatter(x=spy_data["fechas"], y=spy_ret,
                                 line=dict(color=COLORS["SPY"], width=2.5), name="SPY (Benchmark)"))
    for t in TICKERS:
        d = api_get(f"/precios/{t}?period={period}")
        if "error" not in d and d.get("precios"):
            prices = d["precios"]
            cum_ret = [(p / prices[0] - 1) * 100 for p in prices]
            fig.add_trace(go.Scatter(x=d["fechas"], y=cum_ret, name=t,
                                     line=dict(color=COLORS[t], width=1.5)))
    fig.add_hline(y=0, line=dict(color="gray", dash="dot"))
    fig.update_layout(title="Retorno acumulado vs SPY",
                      yaxis_title="Retorno acumulado (%)", xaxis_title="Fecha",
                      height=450, plot_bgcolor="white", paper_bgcolor="white",
                      legend=dict(orientation="h", y=-0.15),
                      hovermode="x unified", margin=dict(l=0, r=0, t=40, b=40))
    st.plotly_chart(fig, use_container_width=True)