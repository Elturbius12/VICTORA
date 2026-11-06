"""Cálculo de recomendaciones para todos los productos a la vez, y exportación de reportes."""
from datetime import timedelta, date
import numpy as np

from .database import get_productos, get_pivot_ventas
from .selection import backtest, elegir_ganador, pronosticar
from .optimizer import razon_critica, cantidad_optima


def calcular_recomendaciones_todas(margen=0.275, min_dias=5):
    """Calcula, para cada producto con suficiente historial, el método ganador
    y la cantidad recomendada a producir mañana. Devuelve una lista de dicts
    ordenada de mayor a menor venta histórica total.
    """
    productos = get_productos()
    pivot, _ = get_pivot_ventas()
    resultados = []

    if pivot.empty:
        return resultados

    for _, prow in productos.iterrows():
        nombre = prow["nombre"]
        if nombre not in pivot.columns:
            continue
        y = pivot[nombre].values.astype(float)
        dates = pivot.index
        if len(y) < min_dias:
            continue

        res, preds = backtest(y, dates, min_train=min_dias)
        ganador = elegir_ganador(res)
        if not ganador:
            continue

        next_date = dates[-1] + timedelta(days=1)
        pron = pronosticar(y, dates, next_date, ganador, res)

        precio = float(prow["precio"])
        recuperable = float(prow["recuperable"])
        sin_precio = precio <= 0
        cr, c, cu, co = razon_critica(precio, margen, recuperable)
        rmse = float(res[res.Modelo == ganador]["RMSE"].values[0]) if not res.empty else 1.0
        q_opt = cantidad_optima(pron, rmse, cr)

        ganancia_estimada = None
        if not sin_precio:
            ganancia_estimada = precio * margen * q_opt

        resultados.append(dict(
            nombre=nombre,
            pronostico=round(float(pron), 1),
            cantidad=q_opt,
            modelo=ganador,
            precio=precio,
            sin_precio=sin_precio,
            total_vendido=float(y.sum()),
            ganancia_estimada=ganancia_estimada,
        ))

    resultados.sort(key=lambda r: r["total_vendido"], reverse=True)
    return resultados


def exportar_reporte_excel(resultados, ruta, fecha=None):
    """Exporta las recomendaciones del día a un archivo Excel legible e imprimible."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter

    fecha = fecha or date.today().isoformat()

    wb = Workbook()
    ws = wb.active
    ws.title = "Reporte del día"

    # Título
    ws.merge_cells("A1:E1")
    ws["A1"] = "La Victoriana – ¿Qué preparar hoy?"
    ws["A1"].font = Font(name="Arial", size=16, bold=True, color="B8860B")
    ws["A1"].alignment = Alignment(horizontal="center")

    ws.merge_cells("A2:E2")
    ws["A2"] = f"Reporte generado para el: {fecha}"
    ws["A2"].font = Font(name="Arial", size=11, italic=True, color="666666")
    ws["A2"].alignment = Alignment(horizontal="center")

    # Cabecera de tabla
    headers = ["Producto", "Cantidad a preparar", "Método usado", "Precio (S/)", "Ganancia estimada (S/)"]
    header_row = 4
    for col, h in enumerate(headers, start=1):
        cell = ws.cell(row=header_row, column=col, value=h)
        cell.font = Font(name="Arial", bold=True, color="FFFFFF", size=11)
        cell.fill = PatternFill("solid", fgColor="B8860B")
        cell.alignment = Alignment(horizontal="center", wrap_text=True)

    thin = Side(style="thin", color="CCCCCC")
    border = Border(bottom=thin)

    row = header_row + 1
    for r in resultados:
        ws.cell(row=row, column=1, value=r["nombre"]).font = Font(name="Arial", size=10)
        ws.cell(row=row, column=2, value=r["cantidad"]).font = Font(name="Arial", size=10, bold=True)
        ws.cell(row=row, column=3, value=r["modelo"]).font = Font(name="Arial", size=9, color="666666")
        precio_txt = f"{r['precio']:.2f}" if not r["sin_precio"] else "Sin precio"
        ws.cell(row=row, column=4, value=precio_txt).font = Font(name="Arial", size=10)
        ganancia_txt = f"{r['ganancia_estimada']:.2f}" if r["ganancia_estimada"] is not None else "—"
        ws.cell(row=row, column=5, value=ganancia_txt).font = Font(name="Arial", size=10)
        for col in range(1, 6):
            ws.cell(row=row, column=col).border = border
            if col != 1:
                ws.cell(row=row, column=col).alignment = Alignment(horizontal="center")
        row += 1

    # Anchos de columna
    widths = [26, 20, 28, 14, 22]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # Nota al pie
    ws.cell(row=row + 1, column=1,
            value="Nota: la cantidad ya incluye un margen de seguridad para no quedarse sin stock.")
    ws.cell(row=row + 1, column=1).font = Font(name="Arial", size=9, italic=True, color="999999")

    wb.save(ruta)
