"""
Dashboard Streamlit — Optimizacion de Compras de Energia (EDEs RD).
Dark premium theme inspired by Bloomberg Terminal / Tesla investor decks.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.data_loader import load_demanda, load_generadores, load_precios_spot
from src.model import ModelParams, build_and_solve


st.set_page_config(
    page_title="EDEs RD · Energy Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Palette (dark premium) ---
BG = "#0A0E1A"
BG_PANEL = "#111827"
BG_ELEVATED = "#1E293B"
BORDER = "rgba(255,255,255,0.06)"
BORDER_HOT = "rgba(34,211,238,0.35)"
INK = "#F1F5F9"
INK_SOFT = "#94A3B8"
INK_DIM = "#64748B"
ACCENT = "#22D3EE"        # electric cyan
ACCENT_GLOW = "rgba(34,211,238,0.25)"
GOLD = "#FBBF24"
EMERALD = "#34D399"
CORAL = "#F87171"
VIOLET = "#A78BFA"

PALETA_TECNOLOGIA = {
    "hidro":   "#22D3EE",
    "eolica":  "#34D399",
    "solar":   "#FBBF24",
    "biomasa": "#F97316",
    "gas":     "#A78BFA",
    "carbon":  "#64748B",
    "fuel":    "#F87171",
}

PRECIO_REAL_2024 = 150.81
PCT_PPA_REAL_2024 = 0.78

# ------------------------------------------------------------------
# Global CSS
# ------------------------------------------------------------------
CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, sans-serif;
    color: {INK};
}}
.stApp {{
    background:
        radial-gradient(1200px 600px at 85% -10%, rgba(34,211,238,0.08), transparent 60%),
        radial-gradient(900px 500px at -10% 110%, rgba(167,139,250,0.06), transparent 60%),
        {BG};
}}
.block-container {{
    padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1480px;
}}
#MainMenu, footer, header {{ visibility: hidden; }}
p, span, div, label {{ color: {INK}; }}

/* HEADER */
.hero {{
    display:flex; justify-content:space-between; align-items:flex-end;
    padding:0 0 1.1rem 0;
    border-bottom:1px solid {BORDER};
    margin-bottom:1.4rem;
}}
.hero .eyebrow {{
    font-family:'JetBrains Mono', monospace;
    font-size:0.68rem; font-weight:600;
    letter-spacing:0.22em; text-transform:uppercase;
    color:{ACCENT}; margin-bottom:0.45rem;
}}
.hero h1 {{
    font-family:'Space Grotesk', sans-serif;
    font-size:2.1rem; font-weight:700;
    color:{INK}; margin:0; line-height:1.1;
    letter-spacing:-0.02em;
    background: linear-gradient(135deg, #FFFFFF 0%, #94A3B8 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}}
.hero .subtitle {{
    font-size:0.88rem; color:{INK_SOFT}; margin-top:0.45rem;
}}
.hero .badge {{
    display:inline-block; padding:0.35rem 0.8rem;
    background:rgba(34,211,238,0.1);
    color:{ACCENT};
    border:1px solid {BORDER_HOT};
    border-radius:999px; font-weight:600;
    font-size:0.7rem; letter-spacing:0.1em;
    font-family:'JetBrains Mono', monospace;
}}
.hero .meta {{
    display:block; margin-top:0.5rem;
    font-size:0.72rem; color:{INK_DIM};
    font-family:'JetBrains Mono', monospace;
    letter-spacing:0.05em;
}}

/* HERO INSIGHT */
.insight {{
    position:relative;
    background:linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
    border:1px solid {BORDER};
    border-radius:16px; padding:1.8rem 2rem;
    margin-bottom:1.3rem; overflow:hidden;
}}
.insight::before {{
    content:""; position:absolute; top:0; left:0; right:0; height:3px;
    background:linear-gradient(90deg, {ACCENT} 0%, {EMERALD} 50%, {GOLD} 100%);
}}
.insight::after {{
    content:""; position:absolute; top:-40%; right:-10%;
    width:420px; height:420px;
    background:radial-gradient(circle, {ACCENT_GLOW} 0%, transparent 65%);
    pointer-events:none;
}}
.insight-label {{
    position:relative; z-index:1;
    font-family:'JetBrains Mono', monospace;
    font-size:0.7rem; letter-spacing:0.22em;
    text-transform:uppercase; color:{ACCENT}; font-weight:600;
}}
.insight-number {{
    position:relative; z-index:1;
    font-family:'Space Grotesk', sans-serif;
    font-size:3.2rem; font-weight:700;
    letter-spacing:-0.03em; line-height:1.05;
    margin:0.4rem 0 0.6rem 0;
    background:linear-gradient(135deg, #FFFFFF 0%, {ACCENT} 100%);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
}}
.insight-caption {{
    position:relative; z-index:1;
    font-size:0.92rem; color:{INK_SOFT};
    max-width:72%; line-height:1.55;
}}
.insight-caption b {{ color:{INK}; font-weight:600; }}
.insight-caption .num {{
    font-family:'JetBrains Mono', monospace;
    color:{ACCENT}; font-weight:600;
}}

/* KPI grid */
.kpi-grid {{ display:grid; grid-template-columns:repeat(4, 1fr); gap:0.9rem; margin-bottom:1.4rem; }}
.kpi {{ position:relative; background:{BG_PANEL}; border:1px solid {BORDER}; border-radius:14px; padding:1.1rem 1.2rem; transition:all 0.25s ease; overflow:hidden; }}
.kpi::before {{ content:""; position:absolute; left:0; top:0; bottom:0; width:3px; background:{ACCENT}; opacity:0.0; transition:opacity 0.25s ease; }}
.kpi:hover {{ border-color:{BORDER_HOT}; transform:translateY(-1px); box-shadow:0 10px 30px rgba(0,0,0,0.35); }}
.kpi:hover::before {{ opacity:1; }}
.kpi .lab {{ font-family:'JetBrains Mono', monospace; font-size:0.65rem; font-weight:600; color:{INK_DIM}; letter-spacing:0.18em; text-transform:uppercase; margin-bottom:0.55rem; }}
.kpi .val {{ font-family:'Space Grotesk', sans-serif; font-size:1.85rem; font-weight:700; color:{INK}; letter-spacing:-0.02em; line-height:1; }}
.kpi .unit {{ font-size:0.75rem; font-weight:500; color:{INK_SOFT}; margin-left:0.3rem; font-family:'Inter'; }}
.kpi .dlt {{ display:inline-block; margin-top:0.7rem; font-family:'JetBrains Mono', monospace; font-size:0.7rem; font-weight:600; padding:0.22rem 0.55rem; border-radius:6px; letter-spacing:0.02em; }}
.kpi .dlt.up {{ background:rgba(52,211,153,0.12); color:{EMERALD}; border:1px solid rgba(52,211,153,0.3); }}
.kpi .dlt.down {{ background:rgba(248,113,113,0.12); color:{CORAL}; border:1px solid rgba(248,113,113,0.3); }}
.kpi .dlt.neu {{ background:rgba(148,163,184,0.1); color:{INK_SOFT}; border:1px solid {BORDER}; }}

/* Section title */
.sec {{ font-family:'Space Grotesk', sans-serif; font-size:1rem; font-weight:600; color:{INK}; margin:0.3rem 0 0.8rem 0; display:flex; align-items:center; gap:0.6rem; }}
.sec::before {{ content:""; width:4px; height:18px; background:linear-gradient(180deg, {ACCENT} 0%, {EMERALD} 100%); border-radius:2px; }}
.sec-sub {{ font-family:'JetBrains Mono', monospace; font-size:0.7rem; color:{INK_DIM}; letter-spacing:0.1em; margin-left:auto; }}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {{ gap:0.3rem; border-bottom:1px solid {BORDER}; margin-bottom:1rem; background:transparent; }}
.stTabs [data-baseweb="tab"] {{ font-size:0.85rem; font-weight:500; color:{INK_SOFT}; padding:0.7rem 1.1rem; background:transparent; border-bottom:2px solid transparent; letter-spacing:0.02em; }}
.stTabs [aria-selected="true"] {{ color:{ACCENT} !important; font-weight:600; border-bottom-color:{ACCENT} !important; background:transparent !important; }}

/* Sidebar */
[data-testid="stSidebar"] {{ background:{BG_PANEL}; border-right:1px solid {BORDER}; }}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{ font-family:'Space Grotesk', sans-serif; font-weight:600; color:{INK}; }}
[data-testid="stSidebar"] label {{ font-size:0.78rem !important; font-weight:500 !important; color:{INK_SOFT} !important; }}
[data-testid="stSidebar"] .stSlider [data-baseweb="slider"] > div > div {{ background:{ACCENT} !important; }}
.sidebar-eyebrow {{ font-family:'JetBrains Mono', monospace; font-size:0.65rem; letter-spacing:0.2em; text-transform:uppercase; color:{ACCENT}; font-weight:600; margin-bottom:0.5rem; }}

/* Inputs readable on dark */
.stSlider, .stCheckbox, .stSelectbox {{ color:{INK} !important; }}
[data-testid="stMetricLabel"], [data-testid="stMetricValue"] {{ color:{INK} !important; }}

/* Dataframe */
[data-testid="stDataFrame"] {{ border:1px solid {BORDER}; border-radius:12px; background:{BG_PANEL}; }}

/* Footer */
.footer-note {{ margin-top:2rem; padding:1rem 1.2rem; background:{BG_PANEL}; border:1px solid {BORDER}; border-radius:12px; font-size:0.75rem; color:{INK_SOFT}; line-height:1.65; font-family:'JetBrains Mono', monospace; letter-spacing:0.02em; }}
.footer-note a {{ color:{ACCENT}; text-decoration:none; font-weight:500; }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ------------------------------------------------------------------
# Cache + helpers
# ------------------------------------------------------------------
@st.cache_data
def cargar_datos_base():
    return load_generadores(), load_demanda(), load_precios_spot()


def ejecutar_optimizacion(gen, dem, spot, params):
    return build_and_solve(gen, dem, spot, params)


def fmt_m(v: float) -> str:
    if abs(v) >= 1_000_000:
        return f"{v/1_000_000:,.2f}M"
    if abs(v) >= 1_000:
        return f"{v/1_000:,.1f}K"
    return f"{v:,.0f}"


def layout_chart(fig: go.Figure, height: int = 420) -> go.Figure:
    fig.update_layout(
        height=height,
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, -apple-system, sans-serif",
                  size=12, color=INK_SOFT),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="rgba(15,23,42,0.96)",
            bordercolor=BORDER_HOT,
            font=dict(color=INK, size=12,
                      family="JetBrains Mono, monospace"),
            align="left",
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.24,
            xanchor="center", x=0.5,
            bgcolor="rgba(0,0,0,0)", borderwidth=0,
            font=dict(size=11, color=INK_SOFT),
        ),
        margin=dict(l=60, r=24, t=16, b=70),
        xaxis=dict(
            title="", showgrid=False, zeroline=False,
            showline=True, linecolor=BORDER, linewidth=1,
            tickfont=dict(size=11, color=INK_DIM,
                          family="JetBrains Mono, monospace"),
        ),
        yaxis=dict(
            title="",
            gridcolor="rgba(255,255,255,0.04)", gridwidth=1, zeroline=False,
            tickfont=dict(size=11, color=INK_DIM,
                          family="JetBrains Mono, monospace"),
            tickformat=",.0f",
        ),
    )
    return fig


# ------------------------------------------------------------------
# Header
# ------------------------------------------------------------------
header_html = (
    '<div class="hero">'
    '<div>'
    '<div class="eyebrow">// Energy Intelligence · República Dominicana</div>'
    '<h1>Compras Óptimas de Energía — EDEs</h1>'
    '<div class="subtitle">Modelo de despacho MILP sobre el Mercado Eléctrico Mayorista '
    '· Ley 125-01 · Ley 57-07 · Ley 365-22</div>'
    '</div>'
    '<div style="text-align:right;">'
    '<span class="badge">// MILP · CBC SOLVER</span>'
    '<span class="meta">21 generadores · 24 h · Pool post-CDEEE</span>'
    '</div>'
    '</div>'
)
st.markdown(header_html, unsafe_allow_html=True)


# ------------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------------
gen_base, dem_base, spot_base = cargar_datos_base()

with st.sidebar:
    st.markdown(
        '<div class="sidebar-eyebrow">// Parámetros del Modelo</div>',
        unsafe_allow_html=True,
    )
    cuota_ren = st.slider("Cuota mínima renovable (Ley 57-07)",
                          0.0, 0.40, 0.25, 0.01, format="%.2f")
    reserva = st.slider("Reserva rodante",
                        0.03, 0.15, 0.07, 0.01, format="%.2f")
    aplicar_her = st.checkbox("Take-or-pay PPAs heredados (CDEEE)", value=True)
    aplicar_rampa = st.checkbox("Restricciones de rampa", value=True)
    aplicar_mintec = st.checkbox("Mínimos técnicos (MILP)", value=True)

    st.divider()
    st.markdown(
        '<div class="sidebar-eyebrow">// Escenarios de Sensibilidad</div>',
        unsafe_allow_html=True,
    )
    mult_demanda = st.slider("Demanda (×)", 0.7, 1.3, 1.0, 0.05)
    mult_spot = st.slider("Precio spot (×)", 0.5, 2.0, 1.0, 0.05)

    st.divider()
    st.caption(
        "Datos calibrados con el Boletín del Ministerio de Energía "
        "y Minas 2024 y OC-SENI."
    )

gen = gen_base.copy()
dem = dem_base.copy()
dem["demanda_mwh"] = dem["demanda_mwh"] * mult_demanda
spot = spot_base.copy()
spot["precio_spot_usd_mwh"] = spot["precio_spot_usd_mwh"] * mult_spot

params = ModelParams(
    cuota_renovable=cuota_ren,
    reserva_rodante=reserva,
    aplicar_heredados=aplicar_her,
    aplicar_rampa=aplicar_rampa,
    aplicar_min_tecnico=aplicar_mintec,
)

with st.spinner("Resolviendo despacho óptimo..."):
    result = ejecutar_optimizacion(gen, dem, spot, params)

if result.status != "Optimal":
    st.error(
        f"**Problema infactible o no óptimo** ({result.status}). "
        "Revise parámetros: reserva muy alta, cuota renovable inalcanzable, "
        "o retiros heredados superan la demanda."
    )

despacho = result.despacho
p_opt = result.kpis["precio_promedio_usd_mwh"]
delta_precio = PRECIO_REAL_2024 - p_opt
ahorro_dia = delta_precio * result.kpis["energia_total_mwh"]
ahorro_anual_m = ahorro_dia * 365 / 1_000_000
twh_anual = result.kpis["energia_total_mwh"] * 365 / 1_000_000

# ------------------------------------------------------------------
# Hero insight
# ------------------------------------------------------------------
insight_html = (
    '<div class="insight">'
    '<div class="insight-label">// Potencial de Ahorro Anualizado</div>'
    f'<div class="insight-number">USD {ahorro_anual_m:,.0f} M</div>'
    '<div class="insight-caption">'
    f'Diferencial de <span class="num">{delta_precio:+.2f} USD/MWh</span> entre '
    f'el óptimo del modelo (<b>{p_opt:.2f}</b>) y el ponderado real 2024 '
    f'reportado por el Ministerio de Energía y Minas (<b>{PRECIO_REAL_2024:.2f}</b>). '
    f'Proyectado sobre <span class="num">{twh_anual:,.1f} TWh/año</span> '
    'de demanda del Mercado Eléctrico Mayorista.'
    '</div>'
    '</div>'
)
st.markdown(insight_html, unsafe_allow_html=True)


# ------------------------------------------------------------------
# KPI grid
# ------------------------------------------------------------------
def kpi(lab: str, val: str, unit: str = "", dlt: str = "", dir_: str = "neu") -> str:
    arrow = {"up": "▲", "down": "▼", "neu": "◆"}[dir_]
    dlt_html = f'<div class="dlt {dir_}">{arrow} {dlt}</div>' if dlt else ""
    return (
        f'<div class="kpi">'
        f'<div class="lab">{lab}</div>'
        f'<div class="val">{val}<span class="unit">{unit}</span></div>'
        f'{dlt_html}'
        f'</div>'
    )

delta_precio_pct = (p_opt - PRECIO_REAL_2024) / PRECIO_REAL_2024 * 100
delta_ren_pp = (result.kpis["pct_renovable"] - cuota_ren) * 100
delta_ppa_pp = (result.kpis["pct_ppa"] - PCT_PPA_REAL_2024) * 100

kpis_html = (
    '<div class="kpi-grid">'
    + kpi("Costo / día",
          f"USD {fmt_m(result.costo_total_usd)}",
          "",
          f"PPA {fmt_m(result.costo_ppa_usd)} · SPOT {fmt_m(result.costo_spot_usd)}",
          "neu")
    + kpi("Precio promedio",
          f"{p_opt:,.2f}", " USD/MWh",
          f"{delta_precio_pct:+.1f}% VS 2024",
          "up" if p_opt < PRECIO_REAL_2024 else "down")
    + kpi("% Renovable",
          f"{result.kpis['pct_renovable']*100:,.1f}", "%",
          f"{delta_ren_pp:+.1f} PP VS CUOTA",
          "up" if delta_ren_pp >= 0 else "down")
    + kpi("Vía PPA",
          f"{result.kpis['pct_ppa']*100:,.1f}", "%",
          f"{delta_ppa_pp:+.1f} PP VS 78% 2024",
          "up" if delta_ppa_pp >= 0 else "down")
    + '</div>'
)
st.markdown(kpis_html, unsafe_allow_html=True)


# ------------------------------------------------------------------
# Tabs
# ------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    ["  DESPACHO HORARIO  ", "  MIX TECNOLÓGICO  ",
     "  COSTOS PPA VS SPOT  ", "  DETALLE POR GENERADOR  "]
)

with tab1:
    st.markdown(
        '<div class="sec">Despacho óptimo por tecnología'
        '<span class="sec-sub">// 24 h · stack por fuente</span></div>',
        unsafe_allow_html=True,
    )
    orden_tec = ["hidro", "eolica", "solar", "biomasa", "gas", "carbon", "fuel"]
    df_plot = despacho.groupby(["hora", "tecnologia"], as_index=False)["mwh_total"].sum()

    fig = go.Figure()
    for tec in orden_tec:
        sub = df_plot[df_plot["tecnologia"] == tec]
        if sub.empty or sub["mwh_total"].sum() == 0:
            continue
        sub = sub.sort_values("hora")
        fig.add_trace(go.Bar(
            x=[f"{h:02d}" for h in sub["hora"]],
            y=sub["mwh_total"],
            name=tec.capitalize(),
            marker=dict(color=PALETA_TECNOLOGIA[tec],
                        line=dict(color=BG, width=1)),
            hovertemplate=f"<b>{tec.capitalize()}</b>  %{{y:,.0f}} MWh<extra></extra>",
        ))

    dem_s = dem.sort_values("hora")
    fig.add_trace(go.Scatter(
        x=[f"{h:02d}" for h in dem_s["hora"]],
        y=dem_s["demanda_mwh"],
        mode="lines+markers", name="Demanda",
        line=dict(color=GOLD, width=2.8, shape="spline", smoothing=0.7),
        marker=dict(size=7, color=GOLD,
                    line=dict(color=BG, width=2)),
        hovertemplate="<b>Demanda</b>  %{y:,.0f} MWh<extra></extra>",
    ))

    fig.update_layout(barmode="stack", bargap=0.24)
    fig = layout_chart(fig, height=470)
    fig.update_yaxes(title=dict(text="MWh",
                                font=dict(color=INK_DIM, size=11)))
    st.plotly_chart(fig, width="stretch")

with tab2:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            '<div class="sec">Mix por tecnología'
            '<span class="sec-sub">// energía total</span></div>',
            unsafe_allow_html=True,
        )
        mix_tec = despacho.groupby("tecnologia", as_index=False)["mwh_total"].sum()
        mix_tec = mix_tec[mix_tec["mwh_total"] > 0].sort_values("mwh_total", ascending=False)
        fig = go.Figure(go.Pie(
            labels=[t.capitalize() for t in mix_tec["tecnologia"]],
            values=mix_tec["mwh_total"],
            marker=dict(
                colors=[PALETA_TECNOLOGIA[t] for t in mix_tec["tecnologia"]],
                line=dict(color=BG, width=3),
            ),
            hole=0.68,
            textinfo="percent",
            textposition="outside",
            textfont=dict(size=12, color=INK, family="JetBrains Mono"),
            hovertemplate="<b>%{label}</b>  %{value:,.0f} MWh (%{percent})<extra></extra>",
            sort=False,
        ))
        fig.add_annotation(
            text=f"<b>{result.kpis['energia_total_mwh']/1000:,.1f}</b><br>"
                 f"<span style='font-size:10px;color:{INK_DIM}'>GWh totales</span>",
            showarrow=False,
            font=dict(size=22, color=INK, family="Space Grotesk"),
        )
        fig = layout_chart(fig, height=380)
        fig.update_layout(
            showlegend=True,
            legend=dict(orientation="v", yanchor="middle", y=0.5,
                        xanchor="left", x=1.05, font=dict(color=INK_SOFT)),
        )
        st.plotly_chart(fig, width="stretch")
    with c2:
        st.markdown(
            '<div class="sec">Mix por sector'
            '<span class="sec-sub">// público / mixto / privado</span></div>',
            unsafe_allow_html=True,
        )
        mix_sec = despacho.groupby("sector", as_index=False)["mwh_total"].sum()
        mix_sec = mix_sec[mix_sec["mwh_total"] > 0].sort_values("mwh_total", ascending=False)
        paleta_sector = {"publico": ACCENT, "mixto": VIOLET, "privado": CORAL}
        fig = go.Figure(go.Pie(
            labels=[s.capitalize() for s in mix_sec["sector"]],
            values=mix_sec["mwh_total"],
            marker=dict(
                colors=[paleta_sector.get(s, INK_SOFT) for s in mix_sec["sector"]],
                line=dict(color=BG, width=3),
            ),
            hole=0.68,
            textinfo="percent",
            textposition="outside",
            textfont=dict(size=12, color=INK, family="JetBrains Mono"),
            hovertemplate="<b>%{label}</b>  %{value:,.0f} MWh (%{percent})<extra></extra>",
            sort=False,
        ))
        fig = layout_chart(fig, height=380)
        fig.update_layout(
            showlegend=True,
            legend=dict(orientation="v", yanchor="middle", y=0.5,
                        xanchor="left", x=1.05, font=dict(color=INK_SOFT)),
        )
        st.plotly_chart(fig, width="stretch")

with tab3:
    st.markdown(
        '<div class="sec">Descomposición horaria · PPA vs Spot'
        '<span class="sec-sub">// USD por hora</span></div>',
        unsafe_allow_html=True,
    )
    costo_hora = despacho.groupby("hora", as_index=False).agg(
        costo_ppa=("costo_ppa_usd", "sum"),
        costo_spot=("costo_spot_usd", "sum"),
    )
    horas_lbl = [f"{h:02d}" for h in costo_hora["hora"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=horas_lbl, y=costo_hora["costo_ppa"],
        name="Contratos PPA",
        marker=dict(color=ACCENT, line=dict(color=BG, width=1)),
        hovertemplate="<b>PPA</b>  USD %{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=horas_lbl, y=costo_hora["costo_spot"],
        name="Mercado Spot",
        marker=dict(color=CORAL, line=dict(color=BG, width=1)),
        hovertemplate="<b>Spot</b>  USD %{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(barmode="stack", bargap=0.24)
    fig = layout_chart(fig, height=380)
    fig.update_yaxes(title=dict(text="USD",
                                font=dict(color=INK_DIM, size=11)))
    st.plotly_chart(fig, width="stretch")

    st.markdown(
        '<div class="sec">Precio marginal spot horario'
        '<span class="sec-sub">// USD/MWh</span></div>',
        unsafe_allow_html=True,
    )
    spot_s = spot.sort_values("hora")
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=[f"{h:02d}" for h in spot_s["hora"]],
        y=spot_s["precio_spot_usd_mwh"],
        mode="lines+markers",
        line=dict(color=ACCENT, width=2.8, shape="spline", smoothing=0.6),
        marker=dict(size=7, color=ACCENT,
                    line=dict(color=BG, width=2)),
        fill="tozeroy",
        fillcolor="rgba(34,211,238,0.12)",
        hovertemplate="<b>Spot</b>  %{y:,.1f} USD/MWh<extra></extra>",
        showlegend=False,
    ))
    fig2 = layout_chart(fig2, height=320)
    fig2.update_yaxes(title=dict(text="USD/MWh",
                                 font=dict(color=INK_DIM, size=11)))
    st.plotly_chart(fig2, width="stretch")

with tab4:
    st.markdown(
        '<div class="sec">Compra por generador del pool'
        '<span class="sec-sub">// ordenado por MWh</span></div>',
        unsafe_allow_html=True,
    )
    resumen = despacho.groupby(
        ["id", "nombre", "tecnologia", "sector"], as_index=False
    ).agg(
        mwh_ppa=("mwh_ppa", "sum"),
        mwh_spot=("mwh_spot", "sum"),
        mwh_total=("mwh_total", "sum"),
        costo_ppa=("costo_ppa_usd", "sum"),
        costo_spot=("costo_spot_usd", "sum"),
    )
    resumen["costo_usd"] = resumen["costo_ppa"] + resumen["costo_spot"]
    resumen["precio_promedio"] = (
        resumen["costo_usd"] / resumen["mwh_total"].replace(0, pd.NA)
    )
    resumen = resumen.sort_values("mwh_total", ascending=False)
    st.dataframe(
        resumen[[
            "nombre", "tecnologia", "sector",
            "mwh_ppa", "mwh_spot", "mwh_total",
            "costo_usd", "precio_promedio",
        ]],
        width="stretch",
        hide_index=True,
        column_config={
            "nombre": st.column_config.TextColumn("Generador", width="large"),
            "tecnologia": st.column_config.TextColumn("Tecnología"),
            "sector": st.column_config.TextColumn("Sector"),
            "mwh_ppa": st.column_config.NumberColumn("MWh PPA", format="%.0f"),
            "mwh_spot": st.column_config.NumberColumn("MWh Spot", format="%.0f"),
            "mwh_total": st.column_config.ProgressColumn(
                "MWh Total", format="%.0f",
                min_value=0,
                max_value=float(resumen["mwh_total"].max() or 1),
            ),
            "costo_usd": st.column_config.NumberColumn("Costo USD", format="$%d"),
            "precio_promedio": st.column_config.NumberColumn(
                "USD/MWh", format="%.2f"
            ),
        },
    )

footer = (
    '<div class="footer-note">'
    '// Datos sintéticos calibrados con el Boletín del Ministerio de Energía y Minas 2024 '
    'y estadísticas del OC-SENI. Precios PPA ilustrativos dentro del rango reportado '
    '(76.9 – 406.0 USD/MWh). &nbsp;·&nbsp; '
    '<a href="https://github.com/leanmasterpymes/energia_optima">'
    'github.com/leanmasterpymes/energia_optima</a>'
    '</div>'
)
st.markdown(footer, unsafe_allow_html=True)
