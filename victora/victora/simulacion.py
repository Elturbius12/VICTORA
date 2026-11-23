"""Evaluación contrafactual de políticas de producción (sin datos de merma).

Supuesto: ventas observadas = demanda. Se simula, día a día en el periodo de prueba del
backtesting, cuánto habría sobrado y faltado con cada política.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from .decision import ajustar_lote, costos, razon_critica
from .modelos import MODELOS, pronosticar
from .seleccion import COMBINACION

POLITICAS = {
    "P0": "Práctica habitual simulada (media 7 días × (1 + colchón))",
    "P1": "Naïve (lo vendido ayer)",
    "P2": "Mismo día de la semana anterior",
    "P3": "Media móvil 7 días",
    "P4": "VICTORA (modelo seleccionado + newsvendor)",
}
COLCHON_DEFECTO = 0.15


def _pred_ganador(vals, dow, t, ganador, top3):
    if ganador == COMBINACION:
        return float(np.mean([pronosticar(m, vals[:t], 1, dow[:t], dow[t:t + 1])[0] for m in top3]))
    return float(pronosticar(ganador, vals[:t], 1, dow[:t], dow[t:t + 1])[0])


def residuos_calentamiento(vals, dow, s) -> list:
    """Residuos a 1 día del modelo ganador en los 7 días previos al periodo de prueba (se guardan en caché)."""
    if "res_calent" not in s:
        usados = s["top3"] if s["ganador"] == COMBINACION else [s["ganador"]]
        req = max(MODELOS[x][2] for x in usados)
        s["res_calent"] = [vals[t] - _pred_ganador(vals, dow, t, s["ganador"], s["top3"])
                           for t in range(max(3, req, s["t0"] - 7), s["t0"])]
    return list(s["res_calent"])


def _q_victora(vals, t, f, cr, residuos_previos):
    """Q* en el origen t usando solo residuos anteriores a t (sin fuga de información)."""
    r = np.asarray(residuos_previos)
    if len(r) >= 5:
        q = float(np.quantile(np.clip(f + r, 0, None), cr))
    else:
        sd = np.std(vals[:t], ddof=1) if t > 1 else 0.0
        q = max(f + stats.norm.ppf(cr) * sd, 0.0)
    return q


def simular(m: pd.DataFrame, productos: pd.DataFrame, sel: dict, colchon: float = COLCHON_DEFECTO,
            produccion_real: pd.DataFrame | None = None, margen_delta: float = 0.0,
            politicas: tuple = ("P0", "P1", "P2", "P3", "P4")) -> pd.DataFrame:
    """Devuelve el detalle por producto × fecha × política."""
    prods = productos.set_index("producto_id")
    real_idx = None
    if produccion_real is not None and len(produccion_real):
        real_idx = produccion_real.set_index(["producto_id", "fecha"])["unidades_producidas"]
    filas = []
    for pid in m.columns:
        p = prods.loc[pid].copy()
        p["margen_esperado_pct"] = float(np.clip(p["margen_esperado_pct"] + margen_delta, 0, 99.9))
        cst = costos(p["precio_venta"], p["margen_esperado_pct"], p["valor_rescate"])
        cr = razon_critica(p)
        lote = int(p["tamano_lote"])
        vals, dow, fechas = m[pid].values.astype(float), m.index.dayofweek.values, m.index
        s = sel[pid]
        t0 = s["t0"]
        res = residuos_calentamiento(vals, dow, s)
        pred = s["pred_ganador"]  # pronósticos a 1 día del backtesting (ya calculados)
        for t in range(t0, len(vals)):
            d = vals[t]
            reglas = {
                "P0": np.mean(vals[max(0, t - 7):t]) * (1 + colchon),
                "P1": vals[t - 1],
                "P2": vals[t - 7] if t >= 7 else vals[t - 1],
                "P3": np.mean(vals[max(0, t - 7):t]),
            }
            f4 = float(pred[t - t0])
            q4 = _q_victora(vals, t, f4, cr, res)
            reglas["P4"] = q4
            res.append(d - f4)
            for pol in politicas:
                fuente = "SIMULADO"
                if pol == "P0" and real_idx is not None and (pid, fechas[t]) in real_idx.index:
                    q = float(real_idx[(pid, fechas[t])])
                    fuente = "REAL"
                else:
                    q = ajustar_lote(reglas[pol], lote)
                sobr, falt = max(q - d, 0), max(d - q, 0)
                filas.append({"producto_id": pid, "fecha": fechas[t], "politica": pol, "producido": q,
                              "demanda": d, "sobrante": sobr, "faltante": falt, "vendido": min(q, d),
                              "costo_merma": sobr * cst["Co"], "margen_perdido": falt * cst["Cu"],
                              "costo_total": sobr * cst["Co"] + falt * cst["Cu"], "fuente": fuente})
    return pd.DataFrame(filas)


def resumir(det: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Resumen por política (global) y por política × producto."""
    agg = dict(sobrante=("sobrante", "sum"), faltante=("faltante", "sum"), costo_merma=("costo_merma", "sum"),
               margen_perdido=("margen_perdido", "sum"), costo_total=("costo_total", "sum"),
               vendido=("vendido", "sum"), demanda=("demanda", "sum"), producido=("producido", "sum"))
    g = det.groupby("politica").agg(**agg).reset_index()
    g["fill_rate_pct"] = g["vendido"] / g["demanda"].replace(0, np.nan) * 100
    g["descripcion"] = g["politica"].map(POLITICAS)
    base = g.loc[g["politica"] == "P0", "costo_total"].iloc[0]
    g["reduccion_vs_P0_pct"] = (base - g["costo_total"]) / base * 100 if base > 0 else np.nan
    pp = det.groupby(["producto_id", "politica"]).agg(**agg).reset_index()
    pp["fill_rate_pct"] = pp["vendido"] / pp["demanda"].replace(0, np.nan) * 100
    return g, pp


def sensibilidad(m, productos, sel, produccion_real=None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Sensibilidad al colchón de P0 y a ±10 puntos de margen."""
    p4 = simular(m, productos, sel, politicas=("P4",), produccion_real=None)["costo_total"].sum()
    filas = []
    for c in [0.0, 0.10, 0.15, 0.25, 0.40]:
        p0 = simular(m, productos, sel, colchon=c, politicas=("P0",))["costo_total"].sum()
        filas.append({"colchon_pct": c * 100, "costo_P0": p0, "costo_P4": p4, "ahorro": p0 - p4,
                      "ahorro_pct": (p0 - p4) / p0 * 100 if p0 > 0 else np.nan})
    s_col = pd.DataFrame(filas)
    filas = []
    for dm in [-10, 0, 10]:
        d = simular(m, productos, sel, margen_delta=dm, politicas=("P0", "P4"))
        t = d.groupby("politica")["costo_total"].sum()
        filas.append({"delta_margen_pts": dm, "costo_P0": t["P0"], "costo_P4": t["P4"], "ahorro": t["P0"] - t["P4"],
                      "ahorro_pct": (t["P0"] - t["P4"]) / t["P0"] * 100 if t["P0"] > 0 else np.nan})
    return s_col, pd.DataFrame(filas)
