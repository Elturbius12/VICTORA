"""Decisión de producción (newsvendor) y explosión de materiales."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .utils import a_base, presentar

NIVEL_NO_PERECIBLE = 0.95
MIN_RESIDUOS = 10
CR_MIN, CR_MAX = 0.01, 0.99


def costos(precio: float, margen_pct: float, rescate: float = 0.0) -> dict:
    """c = p(1 − m); Co = c − rescate; Cu = p − c; CR = Cu/(Cu+Co)."""
    c = precio * (1 - margen_pct / 100)
    co = max(c - rescate, 0.0)
    cu = precio - c
    cr = cu / (cu + co) if (cu + co) > 0 else 0.5
    cr = min(max(cr, CR_MIN), CR_MAX)  # evita cuantiles extremos (0 o 100 %)
    return {"c": c, "Co": co, "Cu": cu, "CR": cr}


def razon_critica(fila) -> float:
    if not fila["es_perecible"]:
        return NIVEL_NO_PERECIBLE
    return costos(fila["precio_venta"], fila["margen_esperado_pct"], fila["valor_rescate"])["CR"]


def ajustar_lote(q: float, lote: int) -> int:
    """Redondea al entero superior y luego al múltiplo superior del tamaño de lote."""
    q = max(math.ceil(q - 1e-9), 0)
    lote = max(int(lote), 1)
    return int(math.ceil(q / lote) * lote)


def residuos_por_producto(sel: dict, m: pd.DataFrame) -> dict[str, np.ndarray]:
    """Residuos empíricos; si un producto tiene < MIN_RESIDUOS, usa residuos agrupados normalizados."""
    escalas = {pid: max(m[pid].mean(), 1.0) for pid in m.columns}
    pool = np.concatenate([sel[p]["residuos"] / escalas[p] for p in sel])
    out = {}
    for pid in sel:
        r = sel[pid]["residuos"]
        out[pid] = r if len(r) >= MIN_RESIDUOS else pool * escalas[pid]
    return out


def cantidad(pron: float, residuos: np.ndarray, cr: float) -> float:
    """Q* = cuantil CR de (pronóstico + residuos), truncado en 0 (sin redondear)."""
    dem = np.clip(pron + residuos, 0, None)
    return float(np.quantile(dem, cr)) if len(dem) else pron


def plan_produccion(sel: dict, m: pd.DataFrame, productos: pd.DataFrame) -> pd.DataFrame:
    res = residuos_por_producto(sel, m)
    filas = []
    for _, p in productos.iterrows():
        pid = p["producto_id"]
        cr = razon_critica(p)
        for fecha, f in zip(sel[pid]["fechas_fut"], sel[pid]["pron_fut"]):
            q = cantidad(f, res[pid], cr)
            filas.append({
                "fecha": fecha, "producto_id": pid, "nombre": p["nombre"], "pronostico": f,
                "razon_critica": cr, "Q_optimo": q,
                "producir": ajustar_lote(q, p["tamano_lote"]),
                "intervalo_10": ajustar_lote(cantidad(f, res[pid], 0.10), 1),
                "intervalo_90": ajustar_lote(cantidad(f, res[pid], 0.90), 1),
                "tamano_lote": int(p["tamano_lote"]), "modelo": sel[pid]["ganador"],
            })
    return pd.DataFrame(filas)


def explosion_insumos(plan: pd.DataFrame, recetas: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Insumos por día y lista de compras semanal (unidades convertidas a la unidad base)."""
    if recetas is None or recetas.empty:
        return pd.DataFrame(), pd.DataFrame()
    r = recetas.copy()
    conv = r.apply(lambda x: a_base(x["cantidad_por_unidad"], x["unidad_medida"]), axis=1)
    r["cant_base"] = [c[0] for c in conv]
    r["unidad_base"] = [c[1] for c in conv]
    factor = r.apply(lambda x: a_base(1, x["unidad_medida"])[0], axis=1)
    r["costo_base"] = r["costo_unitario_insumo"] / factor
    j = plan[["fecha", "producto_id", "producir"]].merge(r, on="producto_id")
    j["necesidad"] = j["producir"] * j["cant_base"]
    j["costo"] = j["necesidad"] * j["costo_base"]
    diario = (j.groupby(["fecha", "insumo_id", "insumo_nombre", "unidad_base"], as_index=False)
               .agg(necesidad=("necesidad", "sum"), costo=("costo", lambda s: s.sum(min_count=1))))
    sem = (j.groupby(["insumo_id", "insumo_nombre", "unidad_base"], as_index=False)
             .agg(necesidad_semana=("necesidad", "sum"), costo_estimado=("costo", lambda s: s.sum(min_count=1)),
                  usado_en=("producto_id", lambda s: ", ".join(sorted(set(s))))))
    pres = sem.apply(lambda x: presentar(x["necesidad_semana"], x["unidad_base"]), axis=1)
    sem["comprar"] = [round(c[0], 2) for c in pres]
    sem["unidad"] = [c[1] for c in pres]
    return diario, sem
