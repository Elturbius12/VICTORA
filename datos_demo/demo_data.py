"""Datos sintéticos de demostración (FICTICIOS): 32 productos en 8 categorías."""
from __future__ import annotations

import numpy as np
import pandas as pd

# clave: (insumo_id, nombre, unidad, costo por unidad de medida en S/)
INSUMOS = {
    "HAR": ("I001", "Harina preparada", "g", 0.004), "QUE": ("I002", "Queso mozzarella", "g", 0.025),
    "SAL": ("I003", "Salsa de tomate", "ml", 0.008), "JAM": ("I004", "Jamón", "g", 0.03),
    "PIN": ("I005", "Piña", "g", 0.006), "PEP": ("I006", "Pepperoni", "g", 0.04),
    "CHO": ("I007", "Champiñones", "g", 0.012), "PAN": ("I008", "Pan de hamburguesa", "unidad", 0.6),
    "CAR": ("I009", "Carne molida", "g", 0.022), "LEC": ("I010", "Lechuga", "g", 0.005),
    "PAP": ("I011", "Papa", "g", 0.004), "ACE": ("I012", "Aceite", "ml", 0.008),
    "CAF": ("I013", "Café molido", "g", 0.06), "AGU": ("I014", "Agua", "ml", 0.0005),
    "FRU": ("I015", "Fruta", "g", 0.006), "AZU": ("I016", "Azúcar", "g", 0.004),
    "HUE": ("I017", "Huevo", "unidad", 0.5), "LCH": ("I018", "Leche", "ml", 0.004),
    "CAC": ("I019", "Cacao", "g", 0.04), "GAS": ("I020", "Gaseosa personal", "unidad", 1.3),
    "POL": ("I021", "Pollo", "g", 0.018), "HEL": ("I022", "Helado", "g", 0.012),
}

PIZZA_F = "HAR:400,QUE:350,SAL:150"
PIZZA_M = "HAR:240,QUE:210,SAL:90"
PIZZA_P = "HAR:120,QUE:100,SAL:45"

# id, nombre, categoría, precio, perecible, vida, rescate, lote, venta media diaria, receta
P = [
    ("Gaseosa personal", "Bebidas", 3.5, "NO", 30, 0.0, 1, 30, "GAS:1"),
    ("Café/Infusión", "Bebidas", 3.0, "SI", 1, 0.0, 1, 45, "CAF:15,AGU:200"),
    ("Jugo de papaya", "Bebidas", 5.0, "SI", 1, 0.0, 1, 14, "FRU:250,AZU:20"),
    ("Limonada", "Bebidas", 4.5, "SI", 1, 0.0, 1, 16, "FRU:200,AZU:25"),
    ("Chicha morada", "Bebidas", 4.0, "SI", 1, 0.0, 1, 12, "FRU:250,AZU:20"),
    ("Agua mineral", "Bebidas", 2.5, "NO", 30, 0.0, 1, 20, "AGU:500"),
    ("Pizza Americana Familiar", "Pizza Familiar", 38.0, "SI", 1, 3.0, 1, 8, PIZZA_F + ",JAM:100"),
    ("Pizza Hawaiana Familiar", "Pizza Familiar", 42.0, "SI", 1, 3.0, 1, 6, PIZZA_F + ",JAM:80,PIN:100"),
    ("Pizza Pepperoni Familiar", "Pizza Familiar", 45.0, "SI", 1, 3.0, 1, 5, PIZZA_F + ",PEP:120"),
    ("Pizza Champiñones Familiar", "Pizza Familiar", 44.0, "SI", 1, 3.0, 1, 3, PIZZA_F + ",CHO:150"),
    ("Pizza Americana Mediana", "Pizza Mediana", 26.0, "SI", 1, 2.0, 1, 10, PIZZA_M + ",JAM:60"),
    ("Pizza Hawaiana Mediana", "Pizza Mediana", 28.0, "SI", 1, 2.0, 1, 8, PIZZA_M + ",JAM:50,PIN:60"),
    ("Pizza Pepperoni Mediana", "Pizza Mediana", 30.0, "SI", 1, 2.0, 1, 7, PIZZA_M + ",PEP:70"),
    ("Pizza Champiñones Mediana", "Pizza Mediana", 29.0, "SI", 1, 2.0, 1, 2, PIZZA_M + ",CHO:90"),
    ("Pizza Americana Personal", "Pizza Personal", 14.0, "SI", 1, 1.0, 1, 12, PIZZA_P + ",JAM:30"),
    ("Pizza Hawaiana Personal", "Pizza Personal", 15.0, "SI", 1, 1.0, 1, 9, PIZZA_P + ",JAM:25,PIN:30"),
    ("Pizza Pepperoni Personal", "Pizza Personal", 16.0, "SI", 1, 1.0, 1, 7, PIZZA_P + ",PEP:35"),
    ("Torta de chocolate (porción)", "Postres", 6.0, "SI", 2, 1.0, 8, 14, "HAR:40,CAC:15,HUE:0.5,AZU:30"),
    ("Helado copa", "Postres", 7.0, "SI", 3, 0.0, 1, 8, "HEL:120"),
    ("Pie de manzana (porción)", "Postres", 5.5, "SI", 2, 0.8, 8, 4, "HAR:50,FRU:80"),
    ("Flan", "Postres", 4.5, "SI", 2, 0.5, 1, 3, "HUE:1,LCH:150,AZU:30"),
    ("Hamburguesa clásica", "Hamburguesas", 12.0, "SI", 1, 0.0, 1, 11, "PAN:1,CAR:120,LEC:20"),
    ("Hamburguesa con queso", "Hamburguesas", 14.0, "SI", 1, 0.0, 1, 9, "PAN:1,CAR:120,LEC:20,QUE:30"),
    ("Hamburguesa de pollo", "Hamburguesas", 13.0, "SI", 1, 0.0, 1, 7, "PAN:1,POL:120,LEC:20"),
    ("Hamburguesa royal", "Hamburguesas", 16.0, "SI", 1, 0.0, 1, 5, "PAN:1,CAR:120,LEC:20,QUE:30,HUE:1"),
    ("Papas fritas", "Piqueos", 8.0, "SI", 1, 0.0, 1, 18, "PAP:250,ACE:40"),
    ("Alitas (6 unid.)", "Piqueos", 18.0, "SI", 1, 0.0, 6, 6, "POL:300,ACE:30"),
    ("Empanada de pollo", "Piqueos", 4.5, "SI", 1, 0.5, 6, 12, "HAR:80,POL:60"),
    ("Tequeños (6 unid.)", "Piqueos", 9.0, "SI", 1, 0.0, 6, 4, "HAR:60,QUE:50"),
    ("Pan al ajo", "Complementos", 6.0, "SI", 1, 0.0, 4, 5, "HAR:80,ACE:10"),
    ("Ensalada", "Complementos", 9.0, "SI", 1, 0.0, 1, 3, "LEC:150,ACE:10"),
    ("Aros de cebolla", "Complementos", 7.0, "SI", 1, 0.0, 1, 2, "PAP:150,ACE:30"),
]
EFECTO_DIA = np.array([0.90, 0.85, 0.95, 1.00, 1.15, 1.30, 1.10])  # lun..dom


def generar(n_dias: int = 21, inicio: str = "2026-10-05", semilla: int = 42) -> dict[str, pd.DataFrame]:
    """Genera las hojas del Excel de carga con datos ficticios (32 productos)."""
    rng = np.random.default_rng(semilla)
    fechas = pd.date_range(inicio, periods=n_dias, freq="D")
    prod, rec, ventas = [], [], []
    for i, (nombre, cat, precio, per, vida, resc, lote, media, receta) in enumerate(P, start=1):
        pid = f"P{i:03d}"
        costo = 0.0
        for item in receta.split(","):
            k, q = item.split(":")
            iid, inom, uni, c = INSUMOS[k]
            rec.append((pid, iid, inom, float(q), uni, c))
            costo += float(q) * c
        margen = float(np.clip(np.round((1 - costo * 1.15 / precio) * 100), 10, 95))
        prod.append((pid, nombre, cat, precio, margen, per, vida, resc, lote))
        for f in fechas:
            lam = media * EFECTO_DIA[f.dayofweek]
            v = (rng.poisson(lam * 2.2) if rng.random() < 0.45 else 0) if media < 5 else rng.poisson(lam)
            agot = "SI" if (media >= 5 and rng.random() < 0.04) else "NO"
            ventas.append((f.date(), pid, int(v), agot))
    productos = pd.DataFrame(prod, columns=["producto_id", "nombre", "categoria", "precio_venta",
                                            "margen_esperado_pct", "es_perecible", "vida_util_dias",
                                            "valor_rescate", "tamano_lote"])
    return {
        "Productos": productos,
        "Ventas": pd.DataFrame(ventas, columns=["fecha", "producto_id", "unidades_vendidas", "agotado"]),
        "Recetas": pd.DataFrame(rec, columns=["producto_id", "insumo_id", "insumo_nombre", "cantidad_por_unidad",
                                              "unidad_medida", "costo_unitario_insumo"]),
        "Calendario": pd.DataFrame({"fecha": [f.date() for f in fechas], "abierto": "SI", "feriado": "NO",
                                    "evento": ""}),
    }
