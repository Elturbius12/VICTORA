"""Generación de las plantillas Excel de carga (vacía y de ejemplo)."""
from __future__ import annotations

import io

import pandas as pd

from .utils import UNIDADES

# (columna, obligatoria, tipo, ancho)  tipo: txt, num, ent, fecha, sino, unidad
ESQUEMA: dict[str, list[tuple[str, bool, str]]] = {
    "Productos": [("producto_id", True, "txt"), ("nombre", True, "txt"), ("categoria", False, "txt"),
                  ("precio_venta", True, "num"), ("margen_esperado_pct", True, "pct"),
                  ("es_perecible", True, "sino"), ("vida_util_dias", False, "ent"),
                  ("valor_rescate", False, "num"), ("tamano_lote", False, "ent")],
    "Ventas": [("fecha", True, "fecha"), ("producto_id", True, "txt"),
               ("unidades_vendidas", True, "ent"), ("agotado", False, "sino")],
    "Recetas": [("producto_id", True, "txt"), ("insumo_id", True, "txt"), ("insumo_nombre", True, "txt"),
                ("cantidad_por_unidad", True, "num"), ("unidad_medida", True, "unidad"),
                ("costo_unitario_insumo", False, "num")],
    "Calendario": [("fecha", False, "fecha"), ("abierto", False, "sino"), ("feriado", False, "sino"),
                   ("evento", False, "txt")],
    "Produccion_real": [("fecha", False, "fecha"), ("producto_id", False, "txt"),
                        ("unidades_producidas", False, "ent"), ("unidades_sobrantes", False, "ent")],
}
HOJAS_OBLIGATORIAS = ["Productos", "Ventas", "Recetas"]

LEEME = [
    ("GUÍA PARA LLENAR LA PLANTILLA VICTORA", "titulo"),
    ("", None),
    ("¿Para qué sirve? VICTORA usa tus ventas diarias para decirte cuánto producir de cada producto "
     "y cuánto dinero podrías ahorrar en merma (sobrantes) y en ventas perdidas.", None),
    ("", None),
    ("COLORES: columnas AMARILLAS = obligatorias. Columnas GRISES = opcionales.", "sub"),
    ("", None),
    ("PASO 1 — Hoja 'Productos': una fila por producto.", "sub"),
    ("  producto_id: código único, ej. P001. Escríbelo IGUAL en todas las hojas.", None),
    ("  nombre: ej. Pan francés.   categoria (opcional): panadería, bebida, postre…", None),
    ("  precio_venta: en soles, con PUNTO decimal. Ej. 4.50", None),
    ("  margen_esperado_pct: % de ganancia sobre el precio, de 0 a 100. Ej. 50 (si cuesta S/ 2,25 y vendes a S/ 4,50).", None),
    ("  es_perecible: SI si se pierde al final del día; NO si dura varios días.", None),
    ("  vida_util_dias (opcional, defecto 1). valor_rescate (opcional): S/ que recuperas por unidad sobrante (defecto 0).", None),
    ("  tamano_lote (opcional): unidades que salen por tanda, ej. 10 panes por bandeja (defecto 1).", None),
    ("", None),
    ("PASO 2 — Hoja 'Ventas': UNA FILA POR DÍA Y PRODUCTO.", "sub"),
    ("  fecha: formato AAAA-MM-DD, ej. 2026-10-05.   producto_id: igual que en Productos.", None),
    ("  unidades_vendidas: número entero ≥ 0. Si un día no vendiste un producto, escribe 0 (no dejes la fila vacía).", None),
    ("  agotado (opcional): SI si el producto se acabó antes de cerrar ese día.", None),
    ("", None),
    ("PASO 3 — Hoja 'Recetas': una fila por cada insumo de cada producto.", "sub"),
    ("  Ej. P001 | I01 | Harina | 60 | g | 0.0035  → cada pan usa 60 g de harina que cuesta S/ 0,0035 por gramo.", None),
    ("  unidad_medida: elige de la lista (g, kg, ml, L, unidad).", None),
    ("", None),
    ("PASO 4 (opcional) — 'Calendario': días cerrados, feriados o eventos.", "sub"),
    ("PASO 5 (opcional) — 'Produccion_real': si anotas cuánto produjiste y cuánto sobró, VICTORA usa la merma REAL.", "sub"),
    ("", None),
    ("ERRORES COMUNES", "sub"),
    ("  • Fechas escritas como texto ('5 de octubre'). Usa el formato de fecha AAAA-MM-DD.", None),
    ("  • Comas en vez de puntos en los decimales (4,50 en lugar de 4.50) si tu Excel está en inglés.", None),
    ("  • producto_id escrito distinto en cada hoja (P001 vs p1 vs 'P001 ').", None),
    ("  • Días sin registrar: si cerraste, anótalo en Calendario; si abriste y no vendiste, pon 0.", None),
    ("", None),
    ("¿CUÁNTOS DÍAS NECESITO?", "sub"),
    ("  Mínimo 7 días (con menos no funciona). Desde 14 días los resultados son útiles; "
     "se recomiendan 28 días o más (4 semanas) para resultados confiables.", None),
]


def _escribir(datos: dict[str, pd.DataFrame] | None, ejemplo: bool) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as xw:
        wb = xw.book
        f_tit = wb.add_format({"bold": True, "font_size": 16, "font_color": "#D4380D"})
        f_sub = wb.add_format({"bold": True, "font_size": 12})
        f_txt = wb.add_format({"text_wrap": False})
        f_obl = wb.add_format({"bold": True, "bg_color": "#FFE58F", "border": 1})
        f_opc = wb.add_format({"bold": True, "bg_color": "#D9D9D9", "border": 1})
        f_fecha = wb.add_format({"num_format": "yyyy-mm-dd"})
        ws = wb.add_worksheet("LEEME")
        ws.set_column(0, 0, 130)
        for i, (t, est) in enumerate(LEEME):
            ws.write(i, 0, t, {"titulo": f_tit, "sub": f_sub}.get(est, f_txt))
        if ejemplo:
            ws.write(len(LEEME) + 1, 0, "⚠️ ESTE ARCHIVO CONTIENE DATOS FICTICIOS DE DEMOSTRACIÓN.", f_tit)
        for hoja, cols in ESQUEMA.items():
            sh = wb.add_worksheet(hoja)
            df = datos.get(hoja) if datos else None
            for j, (c, obl, tipo) in enumerate(cols):
                sh.write(0, j, c, f_obl if obl else f_opc)
                sh.set_column(j, j, max(16, len(c) + 4), f_fecha if tipo == "fecha" else None)
                rango = (1, j, 5000, j)
                if tipo == "sino":
                    sh.data_validation(*rango, {"validate": "list", "source": ["SI", "NO"]})
                elif tipo == "unidad":
                    sh.data_validation(*rango, {"validate": "list", "source": UNIDADES})
                elif tipo == "fecha":
                    sh.data_validation(*rango, {"validate": "date", "criteria": ">=",
                                                "value": pd.Timestamp("2000-01-01").to_pydatetime()})
                elif tipo in ("num", "ent"):
                    sh.data_validation(*rango, {"validate": "decimal" if tipo == "num" else "integer",
                                                "criteria": ">=", "value": 0,
                                                "error_message": "Debe ser un número ≥ 0"})
                elif tipo == "pct":
                    sh.data_validation(*rango, {"validate": "decimal", "criteria": "between",
                                                "minimum": 0, "maximum": 100,
                                                "error_message": "Margen entre 0 y 100"})
            sh.freeze_panes(1, 0)
            if df is not None:
                for i, fila in enumerate(df[[c for c, _, _ in cols]].itertuples(index=False), start=1):
                    for j, v in enumerate(fila):
                        if cols[j][2] == "fecha":
                            sh.write_datetime(i, j, pd.Timestamp(v).to_pydatetime(), f_fecha)
                        elif v is not None and v == v and v != "":
                            sh.write(i, j, v)
    return buf.getvalue()


def plantilla_vacia() -> bytes:
    return _escribir(None, ejemplo=False)


def plantilla_ejemplo() -> bytes:
    from datos_demo.demo_data import generar
    return _escribir(generar(), ejemplo=True)
