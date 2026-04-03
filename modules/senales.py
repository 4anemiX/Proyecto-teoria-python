# ============================================================
# modules/senales.py — Módulo 7 ⭐: Señales y Alertas
# ============================================================
 
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
 
from config import TICKERS, TICKER_INFO, TRADING_DAYS
 
 
# ── Indicadores ───────────────────────────────────────────────────────────────
 
def _rsi(prices: pd.Series, p: int = 14) -> float:
    d = prices.diff().dropna()
    g = d.clip(lower=0).rolling(p).mean()
    l = (-d.clip(upper=0)).rolling(p).mean()
    rs = g / l.replace(0, np.nan)
    return float((100 - 100/(1+rs)).dropna().iloc[-1])
 
def _macd_signal(prices: pd.Series) -> str:
    ema12 = prices.ewm(span=12, adjust=False).mean()
    ema26 = prices.ewm(span=26, adjust=False).mean()
    macd  = ema12 - ema26
    sig   = macd.ewm(span=9, adjust=False).mean()
    last_macd = macd.iloc[-1]
    prev_macd = macd.iloc[-2]
    last_sig  = sig.iloc[-1]
    prev_sig  = sig.iloc[-2]
    if last_macd > last_sig and prev_macd <= prev_sig:
        return "cruce_alcista"
    elif last_macd < last_sig and prev_macd >= prev_sig:
        return "cruce_bajista"
    elif last_macd > last_sig:
        return "alcista"
    else:
        return "bajista"
 
def _bollinger_signal(prices: pd.Series, w: int = 20) -> str:
    mid  = prices.rolling(w).mean()
    std  = prices.rolling(w).std()
    up   = mid + 2*std
    lo   = mid - 2*std
    last = prices.iloc[-1]
    if last > up.iloc[-1]:
        return "ruptura_superior"
    elif last < lo.iloc[-1]:
        return "ruptura_inferior"
    else:
        pct = (last - lo.iloc[-1]) / (up.iloc[-1] - lo.iloc[-1])
        return "zona_alta" if pct > 0.7 else "zona_baja" if pct < 0.3 else "zona_media"
 
def _vol_zscore(rets: pd.Series, w: int = 30) -> float:
    rv = rets.rolling(w).std() * np.sqrt(TRADING_DAYS) * 100
    rv = rv.dropna()
    return float((rv.iloc[-1] - rv.mean()) / rv.std()) if len(rv) > 1 else 0.0
 
def _drawdown(prices: pd.Series) -> float:
    return float((prices / prices.cummax() - 1).iloc[-1] * 100)
 
def _var_signal(rets: pd.Series, cl: float = 0.95) -> float:
    return float(-np.percentile(rets.dropna(), (1-cl)*100) * 100)
 
def _ret_30d(rets: pd.Series) -> float:
    return float((1 + rets.tail(30)).prod() - 1) * 100
 
def _semaforo(val, g_thresh, r_thresh, higher_bad=False):
    if higher_bad:
        if val < g_thresh:  return "🟢", "Normal",    "#22c55e"
        elif val < r_thresh: return "🟡", "Precaución","#f59e0b"
        else:                return "🔴", "Alerta",    "#ef4444"
    else:
        if val > g_thresh:  return "🟢", "Positivo",  "#22c55e"
        elif val > r_thresh: return "🟡", "Neutro",    "#f59e0b"
        else:                return "🔴", "Negativo",  "#ef4444"
 
 
# ── Render ────────────────────────────────────────────────────────────────────
 
def render(precios: pd.DataFrame, rendimientos: pd.DataFrame):
    st.markdown("## ⚡ Módulo 7 — Señales y Alertas Automáticas ⭐")
    st.caption("Panel de monitoreo con semáforos configurables y texto interpretativo.")
 
    ticker = st.selectbox("Activo a monitorear", TICKERS,
                          format_func=lambda t: f"{t} — {TICKER_INFO[t]['sector']}")
    p = precios[ticker].dropna()
    r = rendimientos[ticker].dropna()
 
    # ── Umbrales configurables ─────────────────────────────────────────────────
    with st.expander("⚙️ Configurar umbrales de alerta", expanded=False):
        c1, c2 = st.columns(2)
        rsi_g   = c1.number_input("RSI — verde (máx)", 20, 60, 45)
        rsi_r   = c1.number_input("RSI — rojo (máx)", 60, 90, 70)
        vol_g   = c2.number_input("Vol. Z-score — amarillo", 0.5, 2.0, 1.0, step=0.1)
        vol_r   = c2.number_input("Vol. Z-score — rojo", 1.0, 3.0, 2.0, step=0.1)
        dd_g    = c1.number_input("Drawdown — amarillo (%)", -30.0, -5.0, -10.0, step=1.0)
        dd_r    = c1.number_input("Drawdown — rojo (%)", -50.0, -10.0, -20.0, step=1.0)
        var_g   = c2.number_input("VaR 95% — amarillo (%)", 0.5, 5.0, 2.0, step=0.1)
        var_r   = c2.number_input("VaR 95% — rojo (%)", 1.0, 10.0, 3.5, step=0.1)
 
    # ── Calcular indicadores ───────────────────────────────────────────────────
    rsi_val   = _rsi(p)
    macd_val  = _macd_signal(p)
    bb_val    = _bollinger_signal(p)
    vol_z     = _vol_zscore(r)
    dd_val    = _drawdown(p)
    var_val   = _var_signal(r)
    ret30     = _ret_30d(r)
 
    macd_labels = {
        "cruce_alcista": ("🟢", "Cruce alcista ▲", "#22c55e"),
        "cruce_bajista": ("🔴", "Cruce bajista ▼", "#ef4444"),
        "alcista":       ("🟢", "MACD positivo",  "#22c55e"),
        "bajista":       ("🟡", "MACD negativo",  "#f59e0b"),
    }
    bb_labels = {
        "ruptura_superior": ("🔴", "Ruptura banda sup.", "#ef4444"),
        "ruptura_inferior": ("🟢", "Ruptura banda inf.", "#22c55e"),
        "zona_alta":        ("🟡", "Zona alta",         "#f59e0b"),
        "zona_baja":        ("🟡", "Zona baja",         "#f59e0b"),
        "zona_media":       ("🟢", "Zona media",        "#22c55e"),
    }
 
    indicators = [
        {
            "nombre": "RSI (14)",
            "valor":  f"{rsi_val:.1f}",
            "semaf":  _semaforo(rsi_val, rsi_g, rsi_r, higher_bad=True),
            "interp": (f"RSI en {rsi_val:.1f}. "
                       + ("⚠️ Sobrecompra — posible corrección." if rsi_val > rsi_r
                          else "📈 Sobreventa — posible rebote." if rsi_val < (100-rsi_r)
                          else "Zona neutral sin señal clara.")),
        },
        {
            "nombre": "MACD",
            "valor":  macd_labels[macd_val][1],
            "semaf":  macd_labels[macd_val],
            "interp": ("Cruce alcista reciente: momentum positivo." if macd_val == "cruce_alcista"
                       else "Cruce bajista reciente: momentum negativo." if macd_val == "cruce_bajista"
                       else "MACD por encima de señal: tendencia positiva." if macd_val == "alcista"
                       else "MACD por debajo de señal: tendencia negativa."),
        },
        {
            "nombre": "Bollinger",
            "valor":  bb_labels[bb_val][1],
            "semaf":  bb_labels[bb_val],
            "interp": ("Precio superó banda superior: posible sobrecompra." if bb_val == "ruptura_superior"
                       else "Precio bajo banda inferior: posible sobreventa." if bb_val == "ruptura_inferior"
                       else "Precio en zona alta de las bandas." if bb_val == "zona_alta"
                       else "Precio en zona baja de las bandas." if bb_val == "zona_baja"
                       else "Precio dentro del rango normal de Bollinger."),
        },
        {
            "nombre": "Volatilidad Z-score",
            "valor":  f"{vol_z:.2f}σ",
            "semaf":  _semaforo(abs(vol_z), vol_g, vol_r, higher_bad=True),
            "interp": (f"Volatilidad {abs(vol_z):.2f}σ {'por encima' if vol_z > 0 else 'por debajo'} "
                       f"de su media. {'⚠️ Régimen de alta volatilidad.' if abs(vol_z) > vol_r else 'Nivel normal.'}"),
        },
        {
            "nombre": "Drawdown actual",
            "valor":  f"{dd_val:.2f}%",
            "semaf":  _semaforo(dd_val, dd_g, dd_r, higher_bad=False),
            "interp": (f"{abs(dd_val):.2f}% bajo máximo histórico. "
                       + ("⚠️ Caída severa." if dd_val < dd_r
                          else "Corrección moderada." if dd_val < dd_g
                          else "Cerca de máximos históricos.")),
        },
        {
            "nombre": "VaR 95% diario",
            "valor":  f"{var_val:.3f}%",
            "semaf":  _semaforo(var_val, var_g, var_r, higher_bad=True),
            "interp": (f"Con 95% de confianza, la pérdida diaria no superará {var_val:.3f}%. "
                       + ("⚠️ Riesgo de cola elevado." if var_val > var_r
                          else "Riesgo moderado." if var_val > var_g
                          else "Riesgo de cola bajo.")),
        },
        {
            "nombre": "Retorno 30 días",
            "valor":  f"{ret30:.2f}%",
            "semaf":  _semaforo(ret30, 2.0, -2.0, higher_bad=False),
            "interp": (f"Retorno acumulado últimos 30d: {ret30:.2f}%. "
                       + ("Performance positiva reciente." if ret30 > 2
                          else "Caída reciente — monitorear." if ret30 < -2
                          else "Rendimiento plano en el mes.")),
        },
    ]
 
    # ── Panel semáforo ────────────────────────────────────────────────────────
    st.markdown(f"### 🚦 Panel de señales — {ticker}")
    cols = st.columns(4)
    for i, ind in enumerate(indicators):
        emoji, label, color = ind["semaf"]
        with cols[i % 4]:
            st.markdown(f"""
<div style="background:white;border-radius:12px;padding:14px;margin-bottom:12px;
    box-shadow:0 2px 8px rgba(0,0,0,.07);
    border-left:5px solid {color};">
  <div style="font-size:10px;color:#94a3b8;font-weight:700;text-transform:uppercase;letter-spacing:.5px">
    {ind['nombre']}
  </div>
  <div style="font-size:20px;font-weight:800;margin:4px 0">{emoji} {ind['valor']}</div>
  <div style="font-size:11px;font-weight:600;color:{color}">{label}</div>
  <div style="font-size:10px;color:#64748b;margin-top:6px;line-height:1.4">{ind['interp']}</div>
</div>""", unsafe_allow_html=True)
 
    # ── Radar chart ────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🕸️ Radar de salud del activo")
    scores = [
        max(0, 100 - abs(rsi_val - 50) * 2),
        100 if macd_val in ("cruce_alcista","alcista") else 30,
        100 if "inferior" in bb_val else (50 if "media" in bb_val else 20),
        max(0, 100 - abs(vol_z) * 30),
        max(0, 100 + dd_val * 3),
        min(100, max(0, 50 + ret30 * 5)),
        max(0, 100 - var_val * 15),
    ]
    cats = ["RSI", "MACD", "Bollinger", "Volatilidad", "Drawdown", "Retorno 30d", "VaR"]
    fig = go.Figure(go.Scatterpolar(
        r=scores + [scores[0]], theta=cats + [cats[0]],
        fill="toself", fillcolor="rgba(108,99,255,0.15)",
        line=dict(color="#6C63FF", width=2),
    ))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,100])),
                      height=420, title=f"Radar de salud — {ticker}",
                      template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)
 
    # ── Comparativa multi-activo ───────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📊 Resumen comparativo — todos los activos")
    rows = []
    for t in TICKERS:
        p_t = precios[t].dropna()
        r_t = rendimientos[t].dropna()
        rows.append({
            "Ticker":    t,
            "RSI":       f"{_rsi(p_t):.1f}",
            "MACD":      _macd_signal(p_t),
            "Bollinger": _bollinger_signal(p_t),
            "Vol. Z":    f"{_vol_zscore(r_t):.2f}σ",
            "Drawdown":  f"{_drawdown(p_t):.2f}%",
            "VaR 95%":   f"{_var_signal(r_t):.3f}%",
            "Ret. 30d":  f"{_ret_30d(r_t):.2f}%",
        })
    st.dataframe(pd.DataFrame(rows).set_index("Ticker"), use_container_width=True)