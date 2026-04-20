import plotly.io as pio
import plotly.graph_objects as go

COLORS = {
    "ACN":  "#60A5FA",   # blue
    "MSFT": "#A78BFA",   # purple
    "NVDA": "#34D399",   # green
    "KO":   "#F87171",   # red
    "JPM":  "#FBBF24",   # amber
    "SPY":  "#64748B",   # slate

    "bg":       "#0A0C10",
    "surface":  "#0D1018",
    "surface2": "#111420",
    "border":   "#1C2030",
    "border2":  "#2A3050",
    "text":     "#D4D8E2",
    "muted":    "#5A6480",
    "accent":   "#3B82F6",
    "positive": "#34D399",
    "negative": "#F87171",
    "warning":  "#FBBF24",
}

_layout = go.Layout(
    paper_bgcolor=COLORS["surface"],
    plot_bgcolor=COLORS["bg"],
    font=dict(
        color=COLORS["text"],
        family="DM Sans, sans-serif",
        size=12,
    ),
    xaxis=dict(
        gridcolor="#131820",
        zerolinecolor="#1C2030",
        linecolor="#1C2030",
        tickfont=dict(size=11, color=COLORS["muted"]),
    ),
    yaxis=dict(
        gridcolor="#131820",
        zerolinecolor="#1C2030",
        linecolor="#1C2030",
        tickfont=dict(size=11, color=COLORS["muted"]),
    ),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        bordercolor="#1C2030",
        borderwidth=1,
        font=dict(size=11, color=COLORS["muted"]),
    ),
    margin=dict(l=48, r=24, t=48, b=40),
    title=dict(
        font=dict(size=14, color="#8A94B0", family="DM Sans, sans-serif"),
        x=0,
        xanchor="left",
        pad=dict(l=0, b=12),
    ),
    hoverlabel=dict(
        bgcolor=COLORS["surface2"],
        bordercolor=COLORS["border2"],
        font=dict(size=12, family="DM Mono, monospace", color=COLORS["text"]),
    ),
)

pio.templates["risklab"] = go.layout.Template(layout=_layout)
pio.templates.default = "risklab"


def ticker_color(ticker: str) -> str:
    return COLORS.get(ticker, "#94A3B8")


def mini_chart_style() -> dict:
    """Estilo compacto para gráficos pequeños."""
    return dict(height=220, margin=dict(l=32, r=12, t=28, b=28))