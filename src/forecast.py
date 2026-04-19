"""
Capa de IA — Forecasting de demanda y precio spot para alimentar el MILP.

Pipeline:
  1) Genera (o carga) historico sintetico de 180 dias con estacionalidad
     intra-dia, semanal y ruido calibrado al SENI 2024.
  2) Construye features: calendario + lags + rolling means.
  3) Entrena dos XGBRegressor (demanda y spot) con split temporal.
  4) Reporta MAPE/RMSE en el test set.
  5) Emite forecast 24h listo para ModelParams / build_and_solve.

El forecast reemplaza los CSVs estaticos cuando se quiere optimizar
"dia siguiente" bajo incertidumbre.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error
from xgboost import XGBRegressor


DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "sample"
HIST_PATH = DATA_DIR / "historico_sintetico.csv"

# Calibraciones a partir del Boletin Ministerio de Energia y Minas 2024
DEMANDA_DIA_PROMEDIO_MWH = 71_070
SPOT_PONDERADO_USD_MWH = 205.34
N_DIAS_HISTORICO = 180
SEED = 42

PERFIL_DEM_24H = np.array([
    0.033, 0.031, 0.029, 0.028, 0.029, 0.032, 0.036, 0.040,
    0.044, 0.046, 0.048, 0.048, 0.048, 0.047, 0.047, 0.048,
    0.050, 0.052, 0.055, 0.054, 0.050, 0.044, 0.040, 0.036,
])

PERFIL_SPOT_24H = np.array([
    0.82, 0.76, 0.73, 0.71, 0.73, 0.80, 0.93, 1.05,
    1.10, 1.08, 1.04, 0.96, 0.94, 0.93, 0.93, 0.95,
    1.00, 1.13, 1.29, 1.42, 1.49, 1.40, 1.15, 0.95,
])


# ------------------------------------------------------------------
# 1) Historico sintetico
# ------------------------------------------------------------------
def generar_historico(n_dias: int = N_DIAS_HISTORICO,
                      seed: int = SEED) -> pd.DataFrame:
    """Serie horaria de n_dias con estacionalidad realista + ruido."""
    rng = np.random.default_rng(seed)
    fechas = pd.date_range("2024-01-01", periods=n_dias * 24, freq="h")

    horas = fechas.hour.to_numpy()
    dow = fechas.dayofweek.to_numpy()
    doy = fechas.dayofyear.to_numpy()

    # Demanda: perfil intra-dia * factor semanal * tendencia anual
    fac_semanal = np.where(dow < 5, 1.00, 0.90)
    tendencia = 1 + 0.04 * np.sin(2 * np.pi * doy / 365 - np.pi / 2)
    perfil = PERFIL_DEM_24H[horas] * 24  # normalizacion a dia=1
    demanda = (
        DEMANDA_DIA_PROMEDIO_MWH / 24
        * perfil
        * fac_semanal
        * tendencia
        * rng.normal(1.0, 0.035, size=len(fechas))
    )

    # Spot: perfil intra-dia, con elasticidad hacia la demanda y volatilidad
    dem_norm = demanda / demanda.mean()
    spot = (
        SPOT_PONDERADO_USD_MWH
        * PERFIL_SPOT_24H[horas]
        * (0.7 + 0.3 * dem_norm)
        * rng.normal(1.0, 0.10, size=len(fechas))
    )
    spot = np.clip(spot, 70, 420)

    return pd.DataFrame({
        "timestamp": fechas,
        "hora": horas,
        "dow": dow,
        "demanda_mwh": demanda.round(2),
        "precio_spot_usd_mwh": spot.round(2),
    })


def cargar_o_crear_historico(path: Path = HIST_PATH) -> pd.DataFrame:
    if path.exists():
        df = pd.read_csv(path, parse_dates=["timestamp"])
        return df
    df = generar_historico()
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return df


# ------------------------------------------------------------------
# 2) Feature engineering
# ------------------------------------------------------------------
def construir_features(df: pd.DataFrame, target: str) -> pd.DataFrame:
    """
    Features para predecir el target horario:
      - calendario: hora, dow, mes, es_fin_semana
      - lags: t-24 (mismo horario dia anterior), t-168 (misma semana)
      - rolling: media movil 7 dias del mismo horario
      - senos/cosenos para ciclos horario y semanal
    """
    x = df.copy().sort_values("timestamp").reset_index(drop=True)
    x["mes"] = x["timestamp"].dt.month
    x["es_finde"] = (x["dow"] >= 5).astype(int)

    # Ciclicos
    x["hora_sin"] = np.sin(2 * np.pi * x["hora"] / 24)
    x["hora_cos"] = np.cos(2 * np.pi * x["hora"] / 24)
    x["dow_sin"] = np.sin(2 * np.pi * x["dow"] / 7)
    x["dow_cos"] = np.cos(2 * np.pi * x["dow"] / 7)

    x[f"{target}_lag24"] = x[target].shift(24)
    x[f"{target}_lag168"] = x[target].shift(168)
    x[f"{target}_roll7"] = (
        x[target].shift(24).rolling(window=24 * 7, min_periods=24).mean()
    )

    return x.dropna().reset_index(drop=True)


FEATURES = [
    "hora", "dow", "mes", "es_finde",
    "hora_sin", "hora_cos", "dow_sin", "dow_cos",
]


def feature_cols(target: str) -> list[str]:
    return FEATURES + [f"{target}_lag24", f"{target}_lag168", f"{target}_roll7"]


# ------------------------------------------------------------------
# 3) Entrenamiento
# ------------------------------------------------------------------
@dataclass
class ForecastMetrics:
    mape: float
    rmse: float
    n_train: int
    n_test: int


@dataclass
class ForecastModel:
    target: str
    estimator: XGBRegressor
    metrics: ForecastMetrics
    feature_importance: pd.Series
    y_test: pd.Series
    y_pred: np.ndarray
    timestamps_test: pd.Series


def entrenar(df_feat: pd.DataFrame, target: str,
             dias_test: int = 14) -> ForecastModel:
    cols = feature_cols(target)
    split = df_feat["timestamp"].max() - pd.Timedelta(days=dias_test)
    train = df_feat[df_feat["timestamp"] <= split]
    test = df_feat[df_feat["timestamp"] > split]

    X_train, y_train = train[cols], train[target]
    X_test, y_test = test[cols], test[target]

    model = XGBRegressor(
        n_estimators=400,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_lambda=1.0,
        reg_alpha=0.1,
        random_state=SEED,
        tree_method="hist",
        n_jobs=2,
    )
    model.fit(X_train, y_train, verbose=False)

    y_pred = model.predict(X_test)
    mape = mean_absolute_percentage_error(y_test, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))

    imp = pd.Series(model.feature_importances_, index=cols).sort_values(
        ascending=False
    )

    return ForecastModel(
        target=target,
        estimator=model,
        metrics=ForecastMetrics(
            mape=float(mape),
            rmse=rmse,
            n_train=len(train),
            n_test=len(test),
        ),
        feature_importance=imp,
        y_test=y_test.reset_index(drop=True),
        y_pred=y_pred,
        timestamps_test=test["timestamp"].reset_index(drop=True),
    )


# ------------------------------------------------------------------
# 4) Forecast operativo (dia siguiente)
# ------------------------------------------------------------------
def forecast_dia_siguiente(df_hist: pd.DataFrame,
                           model_dem: ForecastModel,
                           model_spot: ForecastModel) -> pd.DataFrame:
    """
    Pronostica las 24 horas del dia posterior al ultimo timestamp del historico.
    Devuelve DataFrame compatible con load_demanda / load_precios_spot.
    """
    ultima = df_hist["timestamp"].max()
    siguiente = pd.date_range(
        ultima + pd.Timedelta(hours=1), periods=24, freq="h"
    )
    plan = pd.DataFrame({"timestamp": siguiente})
    plan["hora"] = plan["timestamp"].dt.hour
    plan["dow"] = plan["timestamp"].dt.dayofweek
    plan["mes"] = plan["timestamp"].dt.month
    plan["es_finde"] = (plan["dow"] >= 5).astype(int)
    plan["hora_sin"] = np.sin(2 * np.pi * plan["hora"] / 24)
    plan["hora_cos"] = np.cos(2 * np.pi * plan["hora"] / 24)
    plan["dow_sin"] = np.sin(2 * np.pi * plan["dow"] / 7)
    plan["dow_cos"] = np.cos(2 * np.pi * plan["dow"] / 7)

    for tgt, model in [("demanda_mwh", model_dem),
                       ("precio_spot_usd_mwh", model_spot)]:
        serie = df_hist.set_index("timestamp")[tgt]
        lag24 = serie.iloc[-24:].values
        lag168 = serie.iloc[-168:-144].values
        roll7 = [
            serie.iloc[-(24 * 7 + 24):-24]
            .groupby(serie.iloc[-(24 * 7 + 24):-24].index.hour)
            .mean()
            .get(h, serie.mean())
            for h in plan["hora"].values
        ]
        plan[f"{tgt}_lag24"] = lag24
        plan[f"{tgt}_lag168"] = lag168
        plan[f"{tgt}_roll7"] = roll7
        plan[tgt] = model.estimator.predict(plan[feature_cols(tgt)])

    return plan[[
        "timestamp", "hora",
        "demanda_mwh", "precio_spot_usd_mwh",
    ]]


# ------------------------------------------------------------------
# 5) Pipeline completo
# ------------------------------------------------------------------
@dataclass
class ForecastBundle:
    historico: pd.DataFrame
    model_dem: ForecastModel
    model_spot: ForecastModel
    forecast_24h: pd.DataFrame


def entrenar_pipeline_completo() -> ForecastBundle:
    hist = cargar_o_crear_historico()
    feat_dem = construir_features(hist, "demanda_mwh")
    feat_spot = construir_features(hist, "precio_spot_usd_mwh")
    model_dem = entrenar(feat_dem, "demanda_mwh")
    model_spot = entrenar(feat_spot, "precio_spot_usd_mwh")
    forecast = forecast_dia_siguiente(hist, model_dem, model_spot)
    return ForecastBundle(hist, model_dem, model_spot, forecast)


if __name__ == "__main__":
    bundle = entrenar_pipeline_completo()
    for m in (bundle.model_dem, bundle.model_spot):
        print(
            f"[{m.target}]  MAPE={m.metrics.mape*100:5.2f}%  "
            f"RMSE={m.metrics.rmse:7.2f}  "
            f"train={m.metrics.n_train}  test={m.metrics.n_test}"
        )
    print("\nTop features demanda:",
          bundle.model_dem.feature_importance.head(3).to_dict())
    print("Top features spot:   ",
          bundle.model_spot.feature_importance.head(3).to_dict())
    print(f"\nForecast 24h dia siguiente (primeras 5 filas):")
    print(bundle.forecast_24h.head().to_string(index=False))
