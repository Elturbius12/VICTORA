"""Datos sintéticos de demostración (FICTICIOS) para VICTORA."""
from __future__ import annotations

import numpy as np
import pandas as pd

PRODUCTOS = [
    # id, nombre, categoria, precio, margen, perecible, vida, rescate, lote, media
    ("P001", "Pan francés", "panadería", 0.30, 55, "SI", 1, 0.00, 10, 120),
    ("P002", "Empanada de pollo", "salado", 4.50, 50, "SI", 1, 0.50, 1, 25),
    ("P003", "Torta de chocolate (porción)", "postre", 6.00, 60, "SI", 2, 1.00, 8, 14),
    ("P004", "Café pasado", "bebida", 3.50, 70, "SI", 1, 0.00, 1, 40),
    ("P005", "Jugo de papaya", "bebida", 5.00, 55, "SI", 1, 0.00, 1, 18),
    ("P006", "Sándwich de pollo", "salado", 7.00, 45, "SI", 1, 0.00, 1, 15),
    ("P007", "Alfajor", "postre", 2.00, 50, "NO", 15, 0.00, 1, 6),
    ("P008", "Pie de manzana (porción)", "postre", 5.50, 55, "SI", 2, 0.80, 8, 4),
    ("P009", "Tamal", "salado", 4.00, 45, "SI", 1, 0.00, 1, 10),
    ("P010", "Queque (tajada)", "panadería", 2.50, 60, "SI", 2, 0.30, 12, 3),
]

RECETAS = [
    ("P001", "I01", "Harina", 60, "g", 0.0035), ("P001", "I02", "Levadura", 2, "g", 0.02),
    ("P002", "I01", "Harina", 80, "g", 0.0035), ("P002", "I03", "Pollo", 60, "g", 0.018),
    ("P002", "I04", "Cebolla", 30, "g", 0.003),
    ("P003", "I01", "Harina", 40, "g", 0.0035), ("P003", "I05", "Cacao", 15, "g", 0.04),
    ("P003", "I06", "Huevo", 0.5, "unidad", 0.5), ("P003", "I07", "Azúcar", 30, "g", 0.004),
    ("P004", "I08", "Café molido", 15, "g", 0.06), ("P004", "I09", "Agua", 200, "ml", 0.0005),
    ("P005", "I10", "Papaya", 250, "g", 0.006), ("P005", "I07", "Azúcar", 20, "g", 0.004),
    ("P006", "I11", "Pan de molde", 2, "unidad", 0.35), ("P006", "I03", "Pollo", 80, "g", 0.018),
    ("P007", "I01", "Harina", 25, "g", 0.0035), ("P007", "I12", "Manjar", 20, "g", 0.015),
    ("P008", "I01", "Harina", 50, "g", 0.0035), ("P008", "I13", "Manzana", 80, "g", 0.007),
    ("P009", "I14", "Maíz", 150, "g", 0.005), ("P009", "I03", "Pollo", 40, "g", 0.018),
    ("P010", "I01", "Harina", 35, "g", 0.0035), ("P010", "I06", "Huevo", 0.3, "unidad", 0.5),
]

# Efecto del día de la semana (lun..dom)
EFECTO_DIA = np.array([0.90, 0.85, 0.95, 1.00, 1.15, 1.30, 1.10])


def generar(n_dias: int = 21, inicio: str = "2026-10-05", semilla: int = 42) -> dict[str, pd.DataFrame]:
    """Genera las hojas del Excel de carga con datos ficticios."""
    rng = np.random.default_rng(semilla)
    fechas = pd.date_range(inicio, periods=n_dias, freq="D")
    productos = pd.DataFrame(
        [p[:9] for p in PRODUCTOS],
        columns=["producto_id", "nombre", "categoria", "precio_venta", "margen_esperado_pct",
                 "es_perecible", "vida_util_dias", "valor_rescate", "tamano_lote"])
    filas = []
    for p in PRODUCTOS:
        media = p[9]
        for f in fechas:
            lam = media * EFECTO_DIA[f.dayofweek]
            if media < 5:  # intermitente
                v = rng.poisson(lam * 2.2) if rng.random() < 0.45 else 0
            else:
                v = rng.poisson(lam)
            agot = "SI" if (media >= 5 and rng.random() < 0.04) else "NO"
            filas.append((f.date(), p[0], int(v), agot))
    ventas = pd.DataFrame(filas, columns=["fecha", "producto_id", "unidades_vendidas", "agotado"])
    recetas = pd.DataFrame(RECETAS, columns=["producto_id", "insumo_id", "insumo_nombre",
                                             "cantidad_por_unidad", "unidad_medida",
                                             "costo_unitario_insumo"])
    # margen coherente con el costo de receta (+15 % de gastos indirectos), redondeado a 5 puntos
    costo_rec = (recetas["cantidad_por_unidad"] * recetas["costo_unitario_insumo"]).groupby(recetas["producto_id"]).sum()
    c = productos["producto_id"].map(costo_rec) * 1.15
    productos["margen_esperado_pct"] = (np.round((1 - c / productos["precio_venta"]) * 20) * 5).clip(10, 90)
    calendario = pd.DataFrame({"fecha": [f.date() for f in fechas], "abierto": "SI",
                               "feriado": "NO", "evento": ""})
    return {"Productos": productos, "Ventas": ventas, "Recetas": recetas, "Calendario": calendario}
