# Energía Óptima — Compras del Mercado Eléctrico Mayorista (RD)

Modelo MILP + dashboard Streamlit para optimizar las compras de energía de las EDEs dominicanas (EdeNorte, EdeSur, EdeEste) en el Mercado Eléctrico Mayorista post-CDEEE.

**Pregunta que responde:** dado un pool de generadores con contratos PPA heredados, capacidades físicas, mínimos técnicos, rampas y cuota renovable exigida por la Ley 57-07, ¿cuál es el mix horario de compra que minimiza el costo total cumpliendo todas las restricciones del SENI?

## Naturaleza del análisis

Este repositorio es un **modelo demostrativo**, no una auditoría. El marco legal y los datos macro del SENI (precio ponderado 2024, volumen, rango de PPAs) son **reales**, tomados del Boletín Anual del Ministerio de Energía y Minas 2024. Los datos por central del pool de 21 generadores y las curvas horarias son **sintéticos calibrados** dentro de esos rangos — la información contractual detallada no es pública. El ahorro estimado es un **techo teórico**, no una predicción ejecutable: el modelo simplificado no captura compromisos de disponibilidad, restricciones de red, mantenimientos ni fricciones políticas. El valor está en la metodología reproducible y en la cuantificación del espacio contrato-spot.

## Resultado del escenario base

| KPI                       | Modelo optimizado | Real 2024 (Ministerio) | Δ        |
| ------------------------- | ----------------- | ---------------------- | -------- |
| Precio promedio (USD/MWh) | **106.48**        | 150.81                 | **−44.33** |
| % vía PPA                 | 99.9%             | 78%                    | +22 pp   |
| % renovable               | 32.3%             | ~17%                   | +15 pp   |
| Costo día (USD)           | 7,567,504         | ~10,720,000            | **−3.15 M** |

**Ahorro potencial anualizado: ≈ USD 1,140 millones.**

Los datos son sintéticos, calibrados dentro de los rangos del Boletín Anual del Ministerio de Energía y Minas 2024 (PPA 76.9 – 406.0 USD/MWh) y estadísticas del OC-SENI.

## Estructura

```
energia_optima/
├── app/
│   └── streamlit_app.py       # Dashboard (dark premium, 4 tabs, sensibilidad)
├── src/
│   ├── model.py               # MILP en PuLP + solver CBC
│   ├── data_loader.py         # Carga de CSVs
│   ├── forecast.py            # Capa de forecasting — XGBoost demanda + spot
│   └── export_figures.py      # Exporta PNGs de resultados
├── data/sample/
│   ├── generadores.csv        # 21 generadores (pool SENI agregado)
│   ├── demanda.csv            # Demanda horaria 24 h (caso base)
│   ├── precios_spot.csv       # Precios spot horarios 24 h (caso base)
│   └── historico_sintetico.csv # 180 d para entrenar XGBoost (auto-gen)
├── outputs/
│   ├── articulo_tecnico.pdf   # Versión técnica del artículo con todas las ecuaciones
│   ├── figures/*.png          # Gráficos del caso base + forecast
│   └── *.csv                  # Despacho, KPIs, forecast, métricas
└── requirements.txt
```

## Entorno

El venv vive fuera del repo:

```bash
source /home/mapo/proyectos/venvs/optimizacion_energia_IO/bin/activate
pip install -r requirements.txt
```

## Uso

**Correr el modelo (MILP puro, datos estáticos):**

```bash
python -m src.model
```

**Entrenar la capa de IA y hacer forecast del día siguiente:**

```bash
python -m src.forecast
```

Genera `data/sample/historico_sintetico.csv` en la primera corrida (180 días horarios), entrena dos XGBoost (demanda + spot), reporta MAPE/RMSE sobre las últimas 2 semanas y emite un forecast de 24 h listo para alimentar al MILP.

**Exportar los PNG y CSV del caso base:**

```bash
python -m src.export_figures
```

**Regenerar el PDF técnico del artículo:**

```bash
python -m src.export_pdf
```

**Lanzar el dashboard:**

```bash
streamlit run app/streamlit_app.py
```

El dashboard expone sliders de cuota renovable, reserva rodante, take-or-pay heredados, rampas y mínimos técnicos, más multiplicadores de demanda y precio spot para análisis de sensibilidad. La optimización re-corre en cada cambio.

## Formulación

Problema MILP: continuas para compras (PPA y spot por generador y hora), binarias para el estado de encendido. Restricciones: balance de demanda, capacidad con perfil horario para renovables, mínimo técnico, tope PPA, take-or-pay heredados, rampa, cuota renovable (Ley 57-07) y reserva rodante. La formulación matemática completa vive en `src/model.py`.

## Capa de IA (forecasting)

Para conectar el optimizador con operación real, `src/forecast.py` entrena dos `XGBRegressor` (`xgboost==2.0.3`) sobre un histórico sintético de 180 días horarios:

- Features: calendario (hora, día de semana, mes, finde), ciclos $\sin/\cos$, lags $t-24$ y $t-168$, media móvil 7 días por horario.
- Objetivo regularizado $\mathcal{L} = \sum \ell(\hat y, y) + \sum \Omega(f_k)$.
- Split temporal: últimas 2 semanas como test.
- Métricas del baseline actual: **MAPE 3.23 %** demanda, **MAPE 8.80 %** spot.

La salida `forecast_dia_siguiente(...)` devuelve un DataFrame compatible con `build_and_solve(...)`, cerrando el lazo IO + IA en un solo comando.

## Marco normativo

- **Ley 125-01** General de Electricidad (modif. 186-07, 365-22; Dec. 523-23) — Mercado Eléctrico Mayorista (contratos + spot), despacho por mérito del OC-SENI.
- **Ley 57-07** de Incentivo a Fuentes Renovables (modif. 115-15; Dec. 65-23) — meta 25% renovable.
- **Ley 340-06 Art. 5** — régimen especial de compras de energía (fuera del régimen general).
- **Decreto 342-20 / Ley 365-22** — liquidación CDEEE, cesión de 38 PPAs a las EDEs, creación del CUED.

## Limitaciones

Precios por central no son los contractuales reales (el Boletín publica ponderados sistémicos). La lista detallada de los 38 PPAs heredados no es pública. Horizonte 24 h (no captura estacionalidad hidrológica ni mantenimientos). Modelo de nodo único (sin red ni pérdidas de transmisión).

## Stack

Python 3.12 · PuLP 2.8 + CBC · XGBoost 2.0 · scikit-learn · pandas · NumPy · Streamlit · Plotly · Kaleido.
