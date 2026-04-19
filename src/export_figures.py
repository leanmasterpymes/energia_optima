"""
Exporta las figuras clave del modelo a PNG para el post de LinkedIn.

Genera en outputs/figures/:
  01_hero_ahorro.png              — card tipo hero con el ahorro anual
  02_despacho_horario.png         — stack por tecnologia + linea demanda
  03_mix_tecnologia.png           — donut mix tecnologico
  04_costo_ppa_vs_spot.png        — costos horarios PPA vs Spot
  05_precio_spot_horario.png      — curva de precio marginal spot
  06_comparacion_kpis.png         — barras modelo vs real 2024
  07_forecast_vs_real.png         — IA: pronostico XGBoost vs real (test set)
  08_feature_importance.png       — IA: importancia de variables

Resolucion 1600x900 (16:9) a 2x, optimizada para LinkedIn.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from src.data_loader import load_demanda, load_generadores, load_precios_spot
from src.forecast import ForecastModel, entrenar_pipeline_completo
from src.model import ModelParams, build_and_solve


# --- Paleta (coincide con el dashboard) ---
BG = "#0A0E1A"
BG_PANEL = "#111827"
BORDER = "rgba(255,255,255,0.06)"
BORDER_HOT = "rgba(34,211,238,0.35)"
INK = "#F1F5F9"
INK_SOFT = "#94A3B8"
INK_DIM = "#64748B"
ACCENT = "#22D3EE"
GOLD = "#FBBF24"
EMERALD = "#34D399"
CORAL = "#F87171"
VIOLET = "#A78BFA"

PALETA_TEC = {
    "hidro":   "#22D3EE",
    "eolica":  "#34D399",
    "solar":   "#FBBF24",
    "biomasa": "#F97316",
    "gas":     "#A78BFA",
    "carbon":  "#64748B",
    "fuel":    "#F87171",
}

PRECIO_REAL_2024 = 150.81
PCT_PPA_REAL = 0.78
PCT_REN_REAL = 0.17
COSTO_REAL_DIA_USD = 10_720_000

OUT_DIR = Path(__file__).resolve().parents[1] / "outputs" / "figures"
W, H, SCALE = 1600, 900, 2


def base_layout(fig: go.Figure, title: str, subtitle: str = "") -> go.Figure:
    fig.update_layout(
        width=W,
        height=H,
        template="plotly_dark",
        plot_bgcolor=BG,
        paper_bgcolor=BG,
        font=dict(family="Inter, sans-serif", size=16, color=INK_SOFT),
        title=dict(
            text=(
                f"<span style='color:{ACCENT};font-family:JetBrains Mono;"
                f"font-size:22px;letter-spacing:0.18em'>// {subtitle}</span>"
                f"<br><span style='color:{INK};font-family:Space Grotesk;"
                f"font-size:36px;font-weight:700'>{title}</span>"
            ),
            x=0.04, y=0.94, xanchor="left",
        ),
        margin=dict(l=90, r=60, t=150, b=200),
        hovermode=False,
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.20,
            xanchor="center", x=0.5,
            bgcolor="rgba(0,0,0,0)", borderwidth=0,
            font=dict(size=14, color=INK_SOFT, family="Inter"),
        ),
        xaxis=dict(
            showgrid=False, zeroline=False,
            showline=True, linecolor=BORDER, linewidth=1,
            tickfont=dict(size=13, color=INK_DIM,
                          family="JetBrains Mono, monospace"),
        ),
        yaxis=dict(
            gridcolor="rgba(255,255,255,0.05)", zeroline=False,
            tickfont=dict(size=13, color=INK_DIM,
                          family="JetBrains Mono, monospace"),
            tickformat=",.0f",
        ),
        annotations=[dict(
            text=(
                "<span style='color:" + INK_DIM + ";font-family:JetBrains Mono;"
                "font-size:11px;letter-spacing:0.08em'>"
                "github.com/leanmasterpymes/energia_optima · "
                "MILP · CBC · Fuente: Ministerio de Energía y Minas 2024"
                "</span>"
            ),
            xref="paper", yref="paper",
            x=0.04, y=-0.30, xanchor="left", showarrow=False,
        )],
    )
    return fig


def save(fig: go.Figure, name: str) -> None:
    path = OUT_DIR / name
    fig.write_image(str(path), width=W, height=H, scale=SCALE)
    print(f"  ✓ {path.relative_to(OUT_DIR.parents[1])}")


def fig_hero(ahorro_anual_m: float, p_opt: float, p_real: float) -> go.Figure:
    """Tarjeta tipo hero con el ahorro anualizado en grande."""
    delta = p_real - p_opt
    fig = go.Figure()
    fig.add_annotation(
        text=(
            f"<span style='color:{ACCENT};font-family:JetBrains Mono;"
            f"font-size:34px;font-weight:600;letter-spacing:0.22em'>"
            "// POTENCIAL DE AHORRO ANUALIZADO</span>"
        ),
        xref="paper", yref="paper", x=0.5, y=0.82,
        xanchor="center", showarrow=False,
    )
    fig.add_annotation(
        text=(
            f"<span style='font-family:Space Grotesk;font-size:160px;"
            f"font-weight:700;color:{INK}'>USD {ahorro_anual_m:,.0f}M</span>"
        ),
        xref="paper", yref="paper", x=0.5, y=0.55,
        xanchor="center", showarrow=False,
    )
    fig.add_annotation(
        text=(
            f"<span style='font-family:Inter;font-size:22px;color:{INK_SOFT}'>"
            f"Diferencial de <b style='color:{ACCENT}'>"
            f"{delta:+.2f} USD/MWh</b> entre el óptimo del modelo "
            f"(<b style='color:{INK}'>{p_opt:.2f}</b>) y el ponderado "
            f"real 2024 (<b style='color:{INK}'>{p_real:.2f}</b>)</span>"
        ),
        xref="paper", yref="paper", x=0.5, y=0.28,
        xanchor="center", showarrow=False, align="center",
    )
    fig.add_annotation(
        text=(
            f"<span style='font-family:Inter;font-size:18px;color:{INK_DIM}'>"
            "EDEs · Mercado Eléctrico Mayorista (RD) · MILP sobre 21 generadores"
            "</span>"
        ),
        xref="paper", yref="paper", x=0.5, y=0.17,
        xanchor="center", showarrow=False,
    )
    fig.add_annotation(
        text=(
            f"<span style='color:{INK_DIM};font-family:JetBrains Mono;"
            f"font-size:12px;letter-spacing:0.08em'>"
            "github.com/leanmasterpymes/energia_optima · "
            "Fuente: Boletín Ministerio de Energía y Minas 2024</span>"
        ),
        xref="paper", yref="paper", x=0.5, y=0.05,
        xanchor="center", showarrow=False,
    )
    fig.update_layout(
        width=W, height=H,
        plot_bgcolor=BG, paper_bgcolor=BG,
        xaxis=dict(visible=False, range=[0, 1]),
        yaxis=dict(visible=False, range=[0, 1]),
        margin=dict(l=0, r=0, t=0, b=0),
        shapes=[
            dict(type="rect", xref="paper", yref="paper",
                 x0=0.04, x1=0.96, y0=0.04, y1=0.96,
                 line=dict(color=BORDER_HOT, width=1), fillcolor="rgba(0,0,0,0)"),
            dict(type="rect", xref="paper", yref="paper",
                 x0=0.04, x1=0.96, y0=0.92, y1=0.96,
                 line=dict(width=0),
                 fillcolor=ACCENT, opacity=0.9),
        ],
    )
    return fig


def fig_despacho(despacho: pd.DataFrame, dem: pd.DataFrame) -> go.Figure:
    orden = ["hidro", "eolica", "solar", "biomasa", "gas", "carbon", "fuel"]
    df = despacho.groupby(["hora", "tecnologia"], as_index=False)["mwh_total"].sum()
    fig = go.Figure()
    for tec in orden:
        sub = df[df["tecnologia"] == tec].sort_values("hora")
        if sub.empty or sub["mwh_total"].sum() == 0:
            continue
        fig.add_trace(go.Bar(
            x=[f"{h:02d}" for h in sub["hora"]],
            y=sub["mwh_total"],
            name=tec.capitalize(),
            marker=dict(color=PALETA_TEC[tec], line=dict(color=BG, width=1)),
        ))
    dem_s = dem.sort_values("hora")
    fig.add_trace(go.Scatter(
        x=[f"{h:02d}" for h in dem_s["hora"]],
        y=dem_s["demanda_mwh"],
        mode="lines+markers", name="Demanda",
        line=dict(color=GOLD, width=3, shape="spline", smoothing=0.7),
        marker=dict(size=9, color=GOLD, line=dict(color=BG, width=2)),
    ))
    fig.update_layout(barmode="stack", bargap=0.22)
    fig = base_layout(fig, "Despacho óptimo por tecnología",
                      "24 h · stack por fuente · demanda superpuesta")
    fig.update_yaxes(title=dict(text="MWh",
                                font=dict(color=INK_DIM, size=14)))
    fig.update_xaxes(title=dict(text="Hora",
                                font=dict(color=INK_DIM, size=14)))
    return fig


def fig_mix(despacho: pd.DataFrame, energia_total_mwh: float) -> go.Figure:
    mix = despacho.groupby("tecnologia", as_index=False)["mwh_total"].sum()
    mix = mix[mix["mwh_total"] > 0].sort_values("mwh_total", ascending=False)
    fig = go.Figure(go.Pie(
        labels=[t.capitalize() for t in mix["tecnologia"]],
        values=mix["mwh_total"],
        marker=dict(
            colors=[PALETA_TEC[t] for t in mix["tecnologia"]],
            line=dict(color=BG, width=4),
        ),
        hole=0.62,
        textinfo="label+percent",
        textposition="outside",
        textfont=dict(size=16, color=INK, family="JetBrains Mono"),
        sort=False,
    ))
    fig = base_layout(fig, "Mix tecnológico del despacho óptimo",
                      "energía total del día · escenario base")
    fig.add_annotation(
        text=(
            f"<b style='font-size:54px;color:{INK};font-family:Space Grotesk'>"
            f"{energia_total_mwh/1000:,.1f}</b><br>"
            f"<span style='font-size:16px;color:{INK_DIM};"
            f"font-family:JetBrains Mono'>GWh / día</span>"
        ),
        showarrow=False, x=0.5, y=0.5,
        xref="paper", yref="paper", xanchor="center", yanchor="middle",
    )
    fig.update_layout(showlegend=False)
    return fig


def fig_costo(despacho: pd.DataFrame) -> go.Figure:
    cost = despacho.groupby("hora", as_index=False).agg(
        ppa=("costo_ppa_usd", "sum"),
        spot=("costo_spot_usd", "sum"),
    )
    horas = [f"{h:02d}" for h in cost["hora"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=horas, y=cost["ppa"], name="Contratos PPA",
        marker=dict(color=ACCENT, line=dict(color=BG, width=1)),
    ))
    fig.add_trace(go.Bar(
        x=horas, y=cost["spot"], name="Mercado Spot",
        marker=dict(color=CORAL, line=dict(color=BG, width=1)),
    ))
    fig.update_layout(barmode="stack", bargap=0.22)
    fig = base_layout(fig, "Costo horario · PPA vs Spot",
                      "USD por hora · descomposición del día")
    fig.update_yaxes(title=dict(text="USD",
                                font=dict(color=INK_DIM, size=14)))
    fig.update_xaxes(title=dict(text="Hora",
                                font=dict(color=INK_DIM, size=14)))
    return fig


def fig_spot(spot: pd.DataFrame) -> go.Figure:
    s = spot.sort_values("hora")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[f"{h:02d}" for h in s["hora"]],
        y=s["precio_spot_usd_mwh"],
        mode="lines+markers",
        line=dict(color=ACCENT, width=3, shape="spline", smoothing=0.6),
        marker=dict(size=9, color=ACCENT, line=dict(color=BG, width=2)),
        fill="tozeroy",
        fillcolor="rgba(34,211,238,0.15)",
        showlegend=False,
    ))
    fig = base_layout(fig, "Precio marginal spot horario",
                      "USD/MWh · perfil del día")
    fig.update_yaxes(title=dict(text="USD/MWh",
                                font=dict(color=INK_DIM, size=14)))
    fig.update_xaxes(title=dict(text="Hora",
                                font=dict(color=INK_DIM, size=14)))
    return fig


def fig_comparacion(p_opt: float, pct_ren_opt: float,
                    pct_ppa_opt: float, costo_dia_opt: float) -> go.Figure:
    categorias = ["Precio USD/MWh", "% Renovable", "% vía PPA",
                  "Costo día (MM USD)"]
    real = [PRECIO_REAL_2024, PCT_REN_REAL * 100, PCT_PPA_REAL * 100,
            COSTO_REAL_DIA_USD / 1_000_000]
    opt = [p_opt, pct_ren_opt * 100, pct_ppa_opt * 100,
           costo_dia_opt / 1_000_000]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=categorias, y=real, name="Real 2024 (Ministerio)",
        marker=dict(color=INK_DIM, line=dict(color=BG, width=1)),
        text=[f"{v:,.1f}" for v in real],
        textposition="outside",
        textfont=dict(color=INK_SOFT, size=14,
                      family="JetBrains Mono"),
    ))
    fig.add_trace(go.Bar(
        x=categorias, y=opt, name="Modelo optimizado",
        marker=dict(color=ACCENT, line=dict(color=BG, width=1)),
        text=[f"{v:,.1f}" for v in opt],
        textposition="outside",
        textfont=dict(color=ACCENT, size=14,
                      family="JetBrains Mono"),
    ))
    fig.update_layout(barmode="group", bargap=0.28)
    fig = base_layout(fig, "Real vs Optimizado",
                      "KPIs clave · escenario base")
    fig.update_yaxes(title=dict(text="", font=dict(color=INK_DIM, size=14)))
    return fig


def fig_forecast(model: ForecastModel, n_horas: int = 168) -> go.Figure:
    """Real vs predicho sobre el test set (ultimos n_horas por claridad)."""
    ts = pd.Series(model.timestamps_test).iloc[-n_horas:]
    y_real = pd.Series(model.y_test).iloc[-n_horas:]
    y_hat = pd.Series(model.y_pred).iloc[-n_horas:]
    mape = model.metrics.mape * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=ts, y=y_real, mode="lines", name="Real",
        line=dict(color=GOLD, width=2.8, shape="spline", smoothing=0.5),
    ))
    fig.add_trace(go.Scatter(
        x=ts, y=y_hat, mode="lines", name="Pronóstico XGBoost",
        line=dict(color=ACCENT, width=2.2, dash="dash",
                  shape="spline", smoothing=0.5),
    ))
    label = ("Demanda (MWh)" if model.target == "demanda_mwh"
            else "Precio spot (USD/MWh)")
    fig = base_layout(
        fig,
        f"Pronóstico vs Real · {label}",
        f"XGBoost · MAPE {mape:.2f}% · últimas {n_horas} h del test set",
    )
    fig.update_yaxes(title=dict(text=label,
                                font=dict(color=INK_DIM, size=14)))
    fig.update_xaxes(title=dict(text="Tiempo",
                                font=dict(color=INK_DIM, size=14)))
    return fig


def fig_feature_importance(model_dem: ForecastModel,
                           model_spot: ForecastModel) -> go.Figure:
    dem = model_dem.feature_importance.head(8).iloc[::-1]
    spot = model_spot.feature_importance.head(8).iloc[::-1]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=dem.index, x=dem.values, orientation="h",
        name="Modelo de demanda",
        marker=dict(color=ACCENT, line=dict(color=BG, width=1)),
    ))
    fig.add_trace(go.Bar(
        y=spot.index, x=spot.values, orientation="h",
        name="Modelo de spot",
        marker=dict(color=GOLD, line=dict(color=BG, width=1)),
    ))
    fig.update_layout(barmode="group", bargap=0.28)
    fig = base_layout(
        fig,
        "Importancia de variables — XGBoost",
        "top 8 features por modelo · gain normalizado",
    )
    fig.update_yaxes(
        tickfont=dict(size=13, color=INK_SOFT, family="JetBrains Mono"),
    )
    fig.update_xaxes(title=dict(text="Importancia (gain)",
                                font=dict(color=INK_DIM, size=14)))
    return fig


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    gen = load_generadores()
    dem = load_demanda()
    spot = load_precios_spot()
    result = build_and_solve(gen, dem, spot, ModelParams())

    p_opt = result.kpis["precio_promedio_usd_mwh"]
    energia_total = result.kpis["energia_total_mwh"]
    ahorro_dia = (PRECIO_REAL_2024 - p_opt) * energia_total
    ahorro_anual_m = ahorro_dia * 365 / 1_000_000

    print(f"Modelo: {result.status} · p_opt={p_opt:.2f} · "
          f"ahorro_anual≈USD {ahorro_anual_m:,.0f}M")
    print(f"Exportando a {OUT_DIR.relative_to(OUT_DIR.parents[1])}/ "
          f"({W}x{H} @ {SCALE}x)")

    save(fig_hero(ahorro_anual_m, p_opt, PRECIO_REAL_2024),
         "01_hero_ahorro.png")
    save(fig_despacho(result.despacho, dem),
         "02_despacho_horario.png")
    save(fig_mix(result.despacho, energia_total),
         "03_mix_tecnologia.png")
    save(fig_costo(result.despacho),
         "04_costo_ppa_vs_spot.png")
    save(fig_spot(spot),
         "05_precio_spot_horario.png")
    save(fig_comparacion(p_opt, result.kpis["pct_renovable"],
                         result.kpis["pct_ppa"], result.costo_total_usd),
         "06_comparacion_kpis.png")

    # Capa IA — entrena XGBoost sobre historico sintetico
    print("\nEntrenando capa de IA (XGBoost)...")
    bundle = entrenar_pipeline_completo()
    for m in (bundle.model_dem, bundle.model_spot):
        print(f"  · {m.target:22s}  MAPE={m.metrics.mape*100:5.2f}%  "
              f"RMSE={m.metrics.rmse:7.2f}")
    save(fig_forecast(bundle.model_dem), "07_forecast_vs_real.png")
    save(fig_feature_importance(bundle.model_dem, bundle.model_spot),
         "08_feature_importance.png")

    # Exports CSV utiles para outputs/
    csv_dir = OUT_DIR.parent
    result.despacho.to_csv(csv_dir / "despacho_base.csv", index=False)
    pd.DataFrame([result.kpis]).T.reset_index().rename(
        columns={"index": "kpi", 0: "valor"}
    ).to_csv(csv_dir / "kpis_base.csv", index=False)
    bundle.forecast_24h.to_csv(csv_dir / "forecast_dia_siguiente.csv",
                               index=False)
    metricas_ia = pd.DataFrame([
        {"target": m.target, "mape_pct": m.metrics.mape * 100,
         "rmse": m.metrics.rmse, "n_train": m.metrics.n_train,
         "n_test": m.metrics.n_test}
        for m in (bundle.model_dem, bundle.model_spot)
    ])
    metricas_ia.to_csv(csv_dir / "metricas_forecast.csv", index=False)
    print(f"  ✓ outputs/despacho_base.csv  outputs/kpis_base.csv")
    print(f"  ✓ outputs/forecast_dia_siguiente.csv  "
          f"outputs/metricas_forecast.csv")


if __name__ == "__main__":
    main()
