"""Generación de las 3 plantillas Excel: vacía, de ejemplo y guía de recetas."""
from __future__ import annotations

import io

import pandas as pd

from .utils import UNIDADES

COLOR_OBL, COLOR_OPC = "#FFFFCC", "#E0E0E0"

# (columna, obligatoria, tipo)  tipo: txt, num, ent, fecha, sino, unidad, pct
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
    ("  nombre: ej. Pizza Americana Familiar.   categoria (opcional): Bebidas, Pizza Familiar, Postres…", None),
    ("  precio_venta: en soles, con PUNTO decimal. Ej. 38.50", None),
    ("  margen_esperado_pct: % de ganancia sobre el precio, de 0 a 100. Ej. 40 (si cuesta S/ 23,10 y vendes a S/ 38,50).", None),
    ("  es_perecible: SI si se produce a diario y no se guarda; NO si dura varios días.", None),
    ("  vida_util_dias (opcional, defecto 1). valor_rescate (opcional): S/ que recuperas por unidad sobrante (defecto 0).", None),
    ("  tamano_lote (opcional): unidades que salen por tanda, ej. 6 empanadas por bandeja (defecto 1).", None),
    ("", None),
    ("PASO 2 — Hoja 'Ventas': UNA FILA POR DÍA Y PRODUCTO.", "sub"),
    ("  fecha: formato AAAA-MM-DD, ej. 2026-10-20.   producto_id: igual que en Productos.", None),
    ("  unidades_vendidas: número entero ≥ 0. Si un día no vendiste un producto, escribe 0 (no dejes la fila vacía).", None),
    ("  agotado (opcional): SI si el producto se acabó antes de cerrar ese día.", None),
    ("", None),
    ("PASO 3 — Hoja 'Recetas': una fila por cada insumo de cada producto.", "sub"),
    ("  Ej. P001 | I001 | Harina preparada | 250 | g | 0.004  → cada pizza usa 250 g de harina que cuesta S/ 0,004 por gramo.", None),
    ("  unidad_medida: elige de la lista (g, kg, ml, L, unidad). Para más ayuda descarga 'Plantilla_Recetas_Guia.xlsx'.", None),
    ("", None),
    ("PASO 4 (opcional) — 'Calendario': días cerrados, feriados o eventos.", "sub"),
    ("  Un día con abierto = NO no se cuenta como venta cero.", None),
    ("PASO 5 (opcional) — 'Produccion_real': si anotas cuánto produjiste y cuánto sobró, VICTORA usa la merma REAL.", "sub"),
    ("", None),
    ("ERRORES COMUNES", "sub"),
    ("  • Fechas escritas como texto ('20 de octubre'). Usa el formato de fecha AAAA-MM-DD.", None),
    ("  • Comas en vez de puntos en los decimales (38,50 en lugar de 38.50) si tu Excel está en inglés.", None),
    ("  • producto_id escrito distinto en cada hoja (P001 vs p1 vs 'P001 ').", None),
    ("  • Días sin registrar: si cerraste, anótalo en Calendario; si abriste y no vendiste, pon 0.", None),
    ("", None),
    ("¿CUÁNTOS DÍAS NECESITO?", "sub"),
    ("  Mínimo 7 días (con menos no funciona). Desde 14 días los resultados son útiles; "
     "se recomiendan 28 días o más (4 semanas) para resultados confiables.", None),
]


def _formatos(wb):
    return {
        "tit": wb.add_format({"bold": True, "font_size": 16, "font_color": "#D4380D"}),
        "sub": wb.add_format({"bold": True, "font_size": 12}),
        "txt": wb.add_format({}),
        "obl": wb.add_format({"bold": True, "bg_color": COLOR_OBL, "border": 1}),
        "opc": wb.add_format({"bold": True, "bg_color": COLOR_OPC, "border": 1}),
        "fecha": wb.add_format({"num_format": "yyyy-mm-dd"}),
        "ej": wb.add_format({"italic": True, "font_color": "#7F7F7F"}),
        "cel": wb.add_format({"border": 1}),
    }


def _hoja_datos(wb, f, hoja: str, df: pd.DataFrame | None, estilo_datos=None):
    """Escribe una hoja del esquema: encabezados con color, validaciones, ancho ajustado, freeze panes."""
    cols = ESQUEMA[hoja]
    sh = wb.add_worksheet(hoja)
    for j, (c, obl, tipo) in enumerate(cols):
        sh.write(0, j, c, f["obl"] if obl else f["opc"])
        ancho = len(c) + 4
        if df is not None and len(df):
            ancho = max(ancho, int(df[c].astype(str).str.len().max()) + 2)
        sh.set_column(j, j, min(ancho, 45), f["fecha"] if tipo == "fecha" else None)
        rango = (1, j, 5000, j)
        if tipo == "sino":
            sh.data_validation(*rango, {"validate": "list", "source": ["SI", "NO"]})
        elif tipo == "unidad":
            sh.data_validation(*rango, {"validate": "list", "source": UNIDADES})
        elif tipo == "fecha":
            sh.data_validation(*rango, {"validate": "date", "criteria": ">=",
                                        "value": pd.Timestamp("2000-01-01").to_pydatetime(),
                                        "error_message": "Escribe una fecha válida (AAAA-MM-DD)"})
        elif tipo in ("num", "ent"):
            sh.data_validation(*rango, {"validate": "decimal" if tipo == "num" else "integer",
                                        "criteria": ">=", "value": 0, "error_message": "Debe ser un número ≥ 0"})
        elif tipo == "pct":
            sh.data_validation(*rango, {"validate": "decimal", "criteria": "between", "minimum": 0,
                                        "maximum": 100, "error_message": "El margen va de 0 a 100"})
    sh.freeze_panes(1, 0)
    if df is not None:
        for i, fila in enumerate(df[[c for c, _, _ in cols]].itertuples(index=False), start=1):
            for j, v in enumerate(fila):
                if cols[j][2] == "fecha":
                    sh.write_datetime(i, j, pd.Timestamp(v).to_pydatetime(), f["fecha"])
                elif v is not None and v == v and v != "":
                    sh.write(i, j, v, estilo_datos)
    return sh


def _escribir(datos: dict[str, pd.DataFrame] | None, ejemplo: bool) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as xw:
        wb = xw.book
        f = _formatos(wb)
        ws = wb.add_worksheet("LEEME")
        ws.set_column(0, 0, 130)
        for i, (t, est) in enumerate(LEEME):
            ws.write(i, 0, t, {"titulo": f["tit"], "sub": f["sub"]}.get(est, f["txt"]))
        if ejemplo:
            ws.write(len(LEEME) + 1, 0, "⚠️ ESTE ARCHIVO CONTIENE DATOS FICTICIOS DE DEMOSTRACIÓN.", f["tit"])
        for hoja in ESQUEMA:
            _hoja_datos(wb, f, hoja, datos.get(hoja) if datos else None)
    return buf.getvalue()


def plantilla_vacia() -> bytes:
    return _escribir(None, ejemplo=False)


def plantilla_ejemplo() -> bytes:
    from datos_demo.demo_data import generar
    return _escribir(generar(), ejemplo=True)


def plantilla_recetas() -> bytes:
    """Plantilla específica de recetas: hoja de guía + hoja Recetas con 3 filas de ejemplo."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as xw:
        wb = xw.book
        f = _formatos(wb)
        g = wb.add_worksheet("GUIA_RECETAS")
        g.set_column(0, 0, 34)
        g.set_column(1, 3, 28)
        g.write(0, 0, "GUÍA PARA REGISTRAR LAS RECETAS", f["tit"])
        lineas = [
            "Esta plantilla es para registrar los insumos y cantidades que usa cada producto.",
            "Cada fila representa UN insumo de UN producto.",
            "Si un producto usa 5 insumos, tendrá 5 filas (todas con el mismo producto_id).",
            "La cantidad es la que se gasta para hacer UNA unidad del producto.",
            "El producto_id debe ser exactamente el mismo de la hoja Productos de la plantilla principal.",
            "El costo por insumo es opcional, pero si lo llenas, VICTORA puede verificar que tu margen sea coherente.",
            "Al terminar, copia estas filas a la hoja 'Recetas' de la plantilla principal (o sube este archivo "
            "junto con las hojas Productos y Ventas).",
        ]
        for i, t in enumerate(lineas, start=2):
            g.write(i, 0, f"{i - 1}. {t}", f["txt"])
        r0 = len(lineas) + 3
        g.write(r0, 0, "EJEMPLO COMPLETO: Pizza Americana Familiar (P001)", f["sub"])
        enc = ["producto_id", "insumo_id", "insumo_nombre", "cantidad_por_unidad", "unidad_medida", "costo_unitario_insumo"]
        for j, c in enumerate(enc):
            g.write(r0 + 1, j, c, f["obl"] if j < 5 else f["opc"])
        ej = [("P001", "I001", "Harina preparada", 250, "g", 0.004), ("P001", "I002", "Queso mozzarella", 200, "g", 0.025),
              ("P001", "I003", "Salsa de tomate", 100, "ml", 0.008), ("P001", "I004", "Jamón", 80, "g", 0.03)]
        for i, fila in enumerate(ej, start=r0 + 2):
            for j, v in enumerate(fila):
                g.write(i, j, v, f["cel"])
        g.write(r0 + 7, 0, "Lectura: cada pizza usa 250 g de harina, 200 g de queso, 100 ml de salsa y 80 g de jamón. "
                           "Costo de receta = 250×0,004 + 200×0,025 + 100×0,008 + 80×0,03 = S/ 9,20.", f["txt"])
        e0 = r0 + 9
        g.write(e0, 0, "EQUIVALENCIAS DE UNIDADES", f["sub"])
        g.write(e0 + 1, 0, "Unidad", f["obl"])
        g.write(e0 + 1, 1, "Equivale a", f["obl"])
        g.write(e0 + 1, 2, "Úsala para", f["obl"])
        eq = [("1 kg", "1000 g", "harina, queso, carne, azúcar"), ("1 g", "0,001 kg", "cantidades pequeñas"),
              ("1 L", "1000 ml", "salsas, leche, aceite, agua"), ("1 ml", "0,001 L", "cantidades pequeñas"),
              ("1 unidad", "1 pieza", "huevos, panes, gaseosas"), ("1 docena", "12 unidades", "huevos (escribe 12 unidades)"),
              ("1 cucharada", "≈ 15 ml / 15 g", "aproximado"), ("1 taza", "≈ 240 ml", "aproximado")]
        for i, fila in enumerate(eq, start=e0 + 2):
            for j, v in enumerate(fila):
                g.write(i, j, v, f["cel"])
        g.write(e0 + len(eq) + 3, 0, "Nota: si el costo_unitario_insumo es por kg, divídelo entre 1000 para obtener el costo por g. "
                                     "Ej.: queso a S/ 25 el kg = 0,025 por g.", f["ej"])
        ej_df = pd.DataFrame(ej[:3], columns=enc)
        sh = _hoja_datos(wb, f, "Recetas", ej_df, estilo_datos=f["ej"])
        sh.write(0, 7, "← FILAS EN CURSIVA = EJEMPLO (bórralas y escribe tus recetas)", f["ej"])
        sh.set_column(7, 7, 60)
    return buf.getvalue()
