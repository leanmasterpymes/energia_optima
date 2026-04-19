"""
Modelo MILP de optimizacion de compras de energia para las EDEs dominicanas.

Formulacion:
    Decision: cuanta energia comprar a cada generador, en cada hora,
              via contrato PPA (precio fijo) o spot (costo marginal).
    Objetivo: minimizar costo total de compra del dia.
    Restricciones: balance demanda, capacidad, minimo tecnico, rampa,
                   tope PPA, take-or-pay heredados (Ley 365-22),
                   cuota renovable (Ley 57-07), reserva rodante.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import pulp


PERFIL_SOLAR = np.array([
    0.00, 0.00, 0.00, 0.00, 0.00, 0.05, 0.20, 0.45,
    0.70, 0.88, 0.96, 1.00, 0.98, 0.92, 0.82, 0.65,
    0.40, 0.15, 0.02, 0.00, 0.00, 0.00, 0.00, 0.00,
])
PERFIL_EOLICO = np.array([
    0.45, 0.50, 0.52, 0.55, 0.58, 0.55, 0.42, 0.30,
    0.25, 0.22, 0.20, 0.18, 0.20, 0.25, 0.30, 0.38,
    0.45, 0.50, 0.55, 0.60, 0.62, 0.58, 0.52, 0.48,
])
PERFIL_HIDRO = np.full(24, 0.60)
PERFIL_BIOMASA = np.full(24, 0.85)


def perfil_disponibilidad(tecnologia: str) -> np.ndarray:
    if tecnologia == "solar":
        return PERFIL_SOLAR
    if tecnologia == "eolica":
        return PERFIL_EOLICO
    if tecnologia == "hidro":
        return PERFIL_HIDRO
    if tecnologia == "biomasa":
        return PERFIL_BIOMASA
    return np.ones(24)


@dataclass
class ModelParams:
    cuota_renovable: float = 0.25
    reserva_rodante: float = 0.07
    aplicar_heredados: bool = True
    aplicar_rampa: bool = True
    aplicar_min_tecnico: bool = True
    solver_msg: bool = False


@dataclass
class ModelResult:
    status: str
    costo_total_usd: float
    costo_ppa_usd: float
    costo_spot_usd: float
    despacho: pd.DataFrame
    kpis: dict = field(default_factory=dict)


def build_and_solve(
    generadores: pd.DataFrame,
    demanda: pd.DataFrame,
    precios_spot: pd.DataFrame,
    params: ModelParams | None = None,
) -> ModelResult:
    params = params or ModelParams()

    G = generadores["id"].tolist()
    T = demanda["hora"].tolist()

    cap = dict(zip(generadores["id"], generadores["capacidad_mw"]))
    min_tec = dict(zip(generadores["id"], generadores["min_tecnico_mw"]))
    rampa = dict(zip(generadores["id"], generadores["rampa_mw_h"]))
    p_ppa = dict(zip(generadores["id"], generadores["precio_ppa_usd_mwh"]))
    cuota_ppa = dict(zip(generadores["id"], generadores["cuota_ppa_mw"]))
    es_ren = dict(zip(generadores["id"], generadores["es_renovable"]))
    es_her = dict(zip(generadores["id"], generadores["es_heredado"]))
    ret_min = dict(zip(generadores["id"], generadores["retiro_min_diario_mwh"]))
    tecnologia = dict(zip(generadores["id"], generadores["tecnologia"]))

    D = dict(zip(demanda["hora"], demanda["demanda_mwh"]))
    p_spot = dict(zip(precios_spot["hora"], precios_spot["precio_spot_usd_mwh"]))

    disp = {
        g: cap[g] * perfil_disponibilidad(tecnologia[g]) for g in G
    }

    prob = pulp.LpProblem("Compras_EDEs", pulp.LpMinimize)

    x_ppa = pulp.LpVariable.dicts("xPPA", (G, T), lowBound=0)
    x_spot = pulp.LpVariable.dicts("xSPOT", (G, T), lowBound=0)
    y = pulp.LpVariable.dicts("y", (G, T), cat="Binary")

    prob += pulp.lpSum(
        p_ppa[g] * x_ppa[g][t] + p_spot[t] * x_spot[g][t]
        for g in G for t in T
    ), "Costo_total"

    for t in T:
        prob += (
            pulp.lpSum(x_ppa[g][t] + x_spot[g][t] for g in G) == D[t],
            f"Balance_demanda_h{t}",
        )

    for g in G:
        for t in T:
            prob += (
                x_ppa[g][t] + x_spot[g][t] <= disp[g][t] * y[g][t],
                f"Capacidad_{g}_h{t}",
            )
            if params.aplicar_min_tecnico:
                prob += (
                    x_ppa[g][t] + x_spot[g][t] >= min_tec[g] * y[g][t],
                    f"MinTec_{g}_h{t}",
                )
            prob += (
                x_ppa[g][t] <= cuota_ppa[g],
                f"TopePPA_{g}_h{t}",
            )

    if params.aplicar_rampa:
        for g in G:
            for t in T[1:]:
                g_t = x_ppa[g][t] + x_spot[g][t]
                g_prev = x_ppa[g][t - 1] + x_spot[g][t - 1]
                prob += g_t - g_prev <= rampa[g], f"RampaUp_{g}_h{t}"
                prob += g_prev - g_t <= rampa[g], f"RampaDn_{g}_h{t}"

    if params.aplicar_heredados:
        for g in G:
            if es_her[g] and ret_min[g] > 0:
                prob += (
                    pulp.lpSum(x_ppa[g][t] for t in T) >= ret_min[g],
                    f"TakeOrPay_{g}",
                )

    D_total = sum(D.values())
    prob += (
        pulp.lpSum(
            x_ppa[g][t] + x_spot[g][t]
            for g in G if es_ren[g]
            for t in T
        ) >= params.cuota_renovable * D_total,
        "Cuota_renovable",
    )

    for t in T:
        prob += (
            pulp.lpSum(disp[g][t] * y[g][t] for g in G)
            >= (1 + params.reserva_rodante) * D[t],
            f"Reserva_h{t}",
        )

    solver = pulp.PULP_CBC_CMD(msg=params.solver_msg)
    prob.solve(solver)

    status = pulp.LpStatus[prob.status]
    registros = []
    for g in G:
        for t in T:
            q_ppa = pulp.value(x_ppa[g][t]) or 0.0
            q_spot = pulp.value(x_spot[g][t]) or 0.0
            registros.append({
                "hora": t,
                "id": g,
                "nombre": generadores.loc[generadores["id"] == g, "nombre"].iat[0],
                "tecnologia": tecnologia[g],
                "sector": generadores.loc[generadores["id"] == g, "sector"].iat[0],
                "mwh_ppa": q_ppa,
                "mwh_spot": q_spot,
                "mwh_total": q_ppa + q_spot,
                "costo_ppa_usd": q_ppa * p_ppa[g],
                "costo_spot_usd": q_spot * p_spot[t],
            })
    despacho = pd.DataFrame.from_records(registros)

    costo_ppa = despacho["costo_ppa_usd"].sum()
    costo_spot = despacho["costo_spot_usd"].sum()
    costo_total = costo_ppa + costo_spot

    energia_ren = despacho.merge(
        generadores[["id", "es_renovable"]], on="id"
    ).query("es_renovable == True")["mwh_total"].sum()

    kpis = {
        "energia_total_mwh": despacho["mwh_total"].sum(),
        "energia_ppa_mwh": despacho["mwh_ppa"].sum(),
        "energia_spot_mwh": despacho["mwh_spot"].sum(),
        "energia_renovable_mwh": energia_ren,
        "pct_renovable": energia_ren / D_total if D_total else 0,
        "pct_ppa": despacho["mwh_ppa"].sum() / D_total if D_total else 0,
        "precio_promedio_usd_mwh": costo_total / D_total if D_total else 0,
    }

    return ModelResult(
        status=status,
        costo_total_usd=costo_total,
        costo_ppa_usd=costo_ppa,
        costo_spot_usd=costo_spot,
        despacho=despacho,
        kpis=kpis,
    )


if __name__ == "__main__":
    from src.data_loader import load_demanda, load_generadores, load_precios_spot

    gen = load_generadores()
    dem = load_demanda()
    spot = load_precios_spot()

    result = build_and_solve(gen, dem, spot, ModelParams(solver_msg=False))

    print(f"Estado: {result.status}")
    print(f"Costo total: USD {result.costo_total_usd:,.2f}")
    print(f"  - PPA:  USD {result.costo_ppa_usd:,.2f}")
    print(f"  - Spot: USD {result.costo_spot_usd:,.2f}")
    for k, v in result.kpis.items():
        print(f"  {k}: {v:,.4f}")
