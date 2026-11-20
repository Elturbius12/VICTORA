"""Cálculo de recomendaciones para todos los productos a la vez, y exportación de reportes."""
from datetime import timedelta, date
import numpy as np

from .database import (
    get_productos, get_pivot_ventas, get_fechas_especiales,
    promedio_categoria_diario, guardar_pronostico, MARGEN_DEFECTO,
    get_historial_fechas_por_producto,
)
from .selection import (
    backtest, elegir_ganador, pronosticar, pronosticar_horizonte,
    diagnostico, nivel_confianza, modelos_faltantes,
)
from .optimizer import razon_critica, cantidad_optima

#: Mínimo de días propios que pide un producto antes de confiar en SU
#: PROPIO historial. Por debajo de esto, se usa como apoyo el promedio de
#: su categoría (si existe) en vez de no decir nada.
MIN_DIAS_HISTORIAL_PROPIO = 5


def _set_fechas_especiales():
    df = get_fechas_especiales()
    return set(df["fecha"].tolist()) if not df.empty else set()


def calcular_recomendaciones_todas(margen=None, min_dias=MIN_DIAS_HISTORIAL_PROPIO,
                                    guardar_historial=True, dias_semana=7):
    """Calcula, para cada producto, el método ganador y dos cifras
    separadas:
      - 'pronostico': lo que honestamente se espera vender mañana.
      - 'cantidad_sugerida': el pronóstico + colchón de seguridad (usa el
        margen de ganancia del producto), que es lo que conviene
        preparar/comprar para no quedarse corto.
    Devuelve una lista de dicts ordenada de mayor a menor venta histórica.

    'margen' (opcional) sobreescribe el margen guardado por producto; si
    no se indica, se usa el margen propio de cada producto.
    """
    productos = get_productos()
    pivot, fechas_sin_registro = get_pivot_ventas()
    fechas_especiales = _set_fechas_especiales()
    resultados = []

    for _, prow in productos.iterrows():
        nombre = prow["nombre"]
        tipo = prow["tipo"] or "preparado"
        categoria = prow["categoria"] or ""
        margen_prod = margen if margen is not None else float(prow["margen"] or MARGEN_DEFECTO)
        precio = float(prow["precio"])
        recuperable = float(prow["recuperable"])
        sin_precio = precio <= 0

        y_completo = pivot[nombre].values.astype(float) if (not pivot.empty and nombre in pivot.columns) else np.array([])
        dias_propios = int((y_completo != 0).sum()) if len(y_completo) else 0
        dias_calendario = len(y_completo)

        # ── Producto nuevo / con poco historial: usar la categoría como apoyo ──
        if dias_calendario < min_dias or pivot.empty or nombre not in (pivot.columns if not pivot.empty else []):
            apoyo = promedio_categoria_diario(categoria, excluir_producto_id=int(prow["id"]))
            faltan = max(0, min_dias - dias_calendario)
            if apoyo is not None:
                pron = apoyo
                cr, c, cu, co = razon_critica(precio, margen_prod, recuperable)
                q_opt = cantidad_optima(pron, max(pron * 0.6, 0.5), cr)
                resultados.append(dict(
                    nombre=nombre, categoria=categoria, tipo=tipo,
                    pronostico=round(float(pron), 1), cantidad_sugerida=q_opt,
                    accion="preparar" if tipo == "preparado" else "comprar / reponer",
                    modelo="Promedio de la categoría (producto nuevo)",
                    precio=precio, sin_precio=sin_precio,
                    total_vendido=float(y_completo.sum()) if len(y_completo) else 0.0,
                    ganancia_estimada=(precio * margen_prod * pron) if not sin_precio else None,
                    confianza_icono="🔴", confianza_texto=f"Producto nuevo: aún le faltan {faltan} día(s) de su propio historial.",
                    dias_propios=dias_propios, estimado_por_categoria=True,
                ))
            else:
                resultados.append(dict(
                    nombre=nombre, categoria=categoria, tipo=tipo,
                    pronostico=None, cantidad_sugerida=None, accion=None,
                    modelo=None, precio=precio, sin_precio=sin_precio,
                    total_vendido=float(y_completo.sum()) if len(y_completo) else 0.0,
                    ganancia_estimada=None,
                    confianza_icono="🔴",
                    confianza_texto=f"Todavía no hay suficiente historial (le faltan {faltan} día(s)) ni productos parecidos para estimar.",
                    dias_propios=dias_propios, estimado_por_categoria=False,
                ))
            continue

        y = y_completo
        dates = pivot.index
        res, preds = backtest(y, dates, min_train=min_dias, fechas_especiales=fechas_especiales)
        ganador = elegir_ganador(res)
        if not ganador:
            continue

        next_date = dates[-1] + timedelta(days=1)
        pron = pronosticar(y, dates, next_date, ganador, res, fechas_especiales)
        total_semana, _ = pronosticar_horizonte(y, dates, ganador, res, dias_semana, fechas_especiales)

        cr, c, cu, co = razon_critica(precio, margen_prod, recuperable)
        rmse = float(res[res.Modelo == ganador]["RMSE"].values[0]) if not res.empty else 1.0
        q_sugerida = cantidad_optima(pron, rmse, cr)

        ganancia_estimada = precio * margen_prod * pron if not sin_precio else None

        diag = diagnostico(y)
        icono, texto_conf = nivel_confianza(diag, len(res) if not res.empty else 0)

        if guardar_historial:
            guardar_pronostico(next_date.date().isoformat(), int(prow["id"]), pron, q_sugerida, ganador)

        resultados.append(dict(
            nombre=nombre, categoria=categoria, tipo=tipo,
            pronostico=round(float(pron), 1),
            cantidad_sugerida=q_sugerida,
            accion="preparar" if tipo == "preparado" else "comprar / reponer",
            modelo=ganador,
            precio=precio, sin_precio=sin_precio,
            total_vendido=float(y.sum()),
            total_semana_estimado=round(float(total_semana), 1),
            ganancia_estimada=ganancia_estimada,
            confianza_icono=icono, confianza_texto=texto_conf,
            dias_propios=dias_propios, estimado_por_categoria=False,
            diagnostico=diag["clase"],
        ))

    resultados.sort(key=lambda r: r["total_vendido"], reverse=True)
    return resultados, fechas_sin_registro


def backfill_historial_pronosticos(min_dias=MIN_DIAS_HISTORIAL_PROPIO):
    """Rellena 'pronosticos_historial' con los días PASADOS que el
    sistema ya podía haber pronosticado (desde el día min_dias en
    adelante), para que 'Seguimiento' tenga evidencia real de cómo le
    fue al modelo — y no solo el pronóstico de mañana, que es lo único
    que guarda 'Calcular todo' cada vez que se usa.

    Usa el mismo backtest de origen rodante (1 paso adelante) que ya
    elige el modelo ganador: para cada día pasado t, el valor guardado
    es exactamente el que el modelo habría pronosticado en su momento,
    usando solo los datos hasta el día anterior. Por eso las comparaciones
    recién tienen sentido como 'evidencia' desde ese día en adelante —
    antes de min_dias el sistema no tenía con qué pronosticar todavía,
    son datos puramente históricos.

    No pisa un pronóstico que ya se había guardado ese mismo día (por
    ejemplo porque 'Calcular todo' ya se usó en esa fecha). Devuelve
    cuántos pronósticos nuevos se guardaron."""
    productos = get_productos()
    pivot, _ = get_pivot_ventas()
    if pivot.empty:
        return 0
    fechas_especiales = _set_fechas_especiales()
    existentes = get_historial_fechas_por_producto()
    total_guardados = 0

    for _, prow in productos.iterrows():
        nombre = prow["nombre"]
        if nombre not in pivot.columns:
            continue
        y = pivot[nombre].values.astype(float)
        dates = pivot.index
        if len(y) <= min_dias:
            continue

        res, preds = backtest(y, dates, min_train=min_dias, fechas_especiales=fechas_especiales)
        ganador = elegir_ganador(res)
        if not ganador:
            continue

        precio = float(prow["precio"])
        margen_prod = float(prow["margen"] or MARGEN_DEFECTO)
        recuperable = float(prow["recuperable"])
        cr, c, cu, co = razon_critica(precio, margen_prod, recuperable)
        rmse = float(res[res.Modelo == ganador]["RMSE"].values[0]) if not res.empty else 1.0

        pid = int(prow["id"])
        ya_guardadas = existentes.get(pid, set())

        for t in range(min_dias, len(y)):
            fecha_t = dates[t].date().isoformat()
            if fecha_t in ya_guardadas:
                continue
            p = preds[ganador][t]
            if p != p:  # NaN: ese modelo no pudo calcular ese día puntual
                continue
            q = cantidad_optima(float(p), rmse, cr)
            guardar_pronostico(fecha_t, pid, float(p), q, ganador)
            total_guardados += 1

    return total_guardados


def productos_que_casi_no_se_mueven(dias_min=10, umbral_unidades_totales=3):
    """Lista de productos con historial suficiente pero ventas totales muy
    bajas — candidatos a revisar (bajar precio, sacar del menú, etc.)."""
    pivot, _ = get_pivot_ventas()
    if pivot.empty or len(pivot) < dias_min:
        return []
    totales = pivot.sum().sort_values()
    return [{"nombre": n, "total_vendido": int(v)} for n, v in totales.items() if v <= umbral_unidades_totales]


def mejor_peor_dia_semana():
    """Frase simple: qué día de la semana vende más y cuál menos, en
    promedio, sumando todos los productos."""
    pivot, _ = get_pivot_ventas()
    if pivot.empty or len(pivot) < 7:
        return None
    dias_es = {0: "lunes", 1: "martes", 2: "miércoles", 3: "jueves",
               4: "viernes", 5: "sábado", 6: "domingo"}
    totales = pivot.sum(axis=1)
    por_dia = totales.groupby(totales.index.dayofweek).mean()
    mejor = por_dia.idxmax()
    peor = por_dia.idxmin()
    return {
        "mejor_dia": dias_es[mejor], "mejor_valor": round(float(por_dia[mejor]), 1),
        "peor_dia": dias_es[peor], "peor_valor": round(float(por_dia[peor]), 1),
    }


def exportar_reporte_excel(resultados, ruta, fecha=None):
    """Exporta las recomendaciones del día a un archivo Excel legible e imprimible."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter

    fecha = fecha or date.today().isoformat()

    wb = Workbook()
    ws = wb.active
    ws.title = "Reporte del día"

    ws.merge_cells("A1:G1")
    ws["A1"] = "La Victoriana – Recomendación del día"
    ws["A1"].font = Font(name="Arial", size=16, bold=True, color="B8860B")
    ws["A1"].alignment = Alignment(horizontal="center")

    ws.merge_cells("A2:G2")
    ws["A2"] = f"Reporte generado para el: {fecha}"
    ws["A2"].font = Font(name="Arial", size=11, italic=True, color="666666")
    ws["A2"].alignment = Alignment(horizontal="center")

    headers = ["Producto", "Pronóstico de venta", "Cantidad sugerida", "Acción",
               "Método usado", "Precio (S/)", "Ganancia estimada (S/)"]
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
        pron_txt = r["pronostico"] if r["pronostico"] is not None else "—"
        ws.cell(row=row, column=2, value=pron_txt).font = Font(name="Arial", size=10)
        cant_txt = r["cantidad_sugerida"] if r["cantidad_sugerida"] is not None else "—"
        ws.cell(row=row, column=3, value=cant_txt).font = Font(name="Arial", size=10, bold=True)
        ws.cell(row=row, column=4, value=(r["accion"] or "—").capitalize()).font = Font(name="Arial", size=10)
        ws.cell(row=row, column=5, value=r["modelo"] or "—").font = Font(name="Arial", size=9, color="666666")
        precio_txt = f"{r['precio']:.2f}" if not r["sin_precio"] else "Sin precio"
        ws.cell(row=row, column=6, value=precio_txt).font = Font(name="Arial", size=10)
        ganancia_txt = f"{r['ganancia_estimada']:.2f}" if r.get("ganancia_estimada") is not None else "—"
        ws.cell(row=row, column=7, value=ganancia_txt).font = Font(name="Arial", size=10)
        for col in range(1, 8):
            ws.cell(row=row, column=col).border = border
            if col != 1:
                ws.cell(row=row, column=col).alignment = Alignment(horizontal="center")
        row += 1

    widths = [26, 18, 16, 16, 28, 14, 20]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.cell(row=row + 1, column=1,
            value="Nota: 'Cantidad sugerida' ya incluye un margen de seguridad; "
                  "'Pronóstico de venta' es la cifra honesta de lo que se espera vender.")
    ws.cell(row=row + 1, column=1).font = Font(name="Arial", size=9, italic=True, color="999999")

    wb.save(ruta)


def generar_comanda_pdf(resultados, ruta, fecha=None):
    """Genera una hoja simple 'para imprimir' (PDF), grande y clara, con lo
    que toca preparar/comprar hoy — pensada para pegar en la cocina sin
    tener que abrir Excel."""
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_pdf import PdfPages

    fecha = fecha or date.today().isoformat()
    calculables = [r for r in resultados if r.get("cantidad_sugerida") and r["cantidad_sugerida"] > 0]
    preparar = sorted([r for r in calculables if r["accion"] == "preparar"],
                       key=lambda r: -r["cantidad_sugerida"])
    comprar = sorted([r for r in calculables if r["accion"] != "preparar"],
                      key=lambda r: -r["cantidad_sugerida"])

    altura = 2.2 + 0.42 * (len(preparar) + len(comprar) + 4)
    fig = Figure(figsize=(8.27, max(altura, 6)))  # ancho A4
    ax = fig.add_subplot(111)
    ax.axis("off")

    y = 0.98
    ax.text(0.5, y, "La Victoriana", fontsize=22, weight="bold", ha="center", color="#B8860B")
    y -= 0.045
    ax.text(0.5, y, f"Comanda del día — {fecha}", fontsize=13, ha="center", color="#333333")
    y -= 0.06

    def _seccion(titulo, items, y):
        ax.text(0.04, y, titulo, fontsize=14, weight="bold", color="#2C1810")
        y -= 0.05
        if not items:
            ax.text(0.08, y, "(nada pendiente)", fontsize=11, color="#888888")
            y -= 0.045
            return y
        for r in items:
            ax.text(0.08, y, f"☐  {r['nombre']}", fontsize=12)
            ax.text(0.80, y, f"{r['cantidad_sugerida']}", fontsize=12, weight="bold", ha="right")
            y -= 0.042
        return y - 0.02

    y = _seccion("🍕  Preparar", preparar, y)
    y = _seccion("🛒  Comprar / reponer", comprar, y)

    fig.text(0.5, 0.02, "Generado automáticamente por el sistema de pronóstico de La Victoriana",
              fontsize=8, ha="center", color="#999999")

    with PdfPages(ruta) as pdf:
        pdf.savefig(fig)


def exportar_seguimiento_excel(df_seguimiento, ruta):
    """Exporta la tabla de pronóstico vs. venta real a Excel."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Seguimiento"

    headers = ["Fecha", "Producto", "Pronosticado", "Venta real", "Error (unid.)",
               "Error (%)", "Modelo usado", "Observación"]
    for col, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="B8860B")
        cell.alignment = Alignment(horizontal="center", wrap_text=True)

    row = 2
    for _, r in df_seguimiento.iterrows():
        ws.cell(row=row, column=1, value=r["fecha"])
        ws.cell(row=row, column=2, value=r["producto"])
        ws.cell(row=row, column=3, value=round(r["pronostico"], 1) if r["pronostico"] == r["pronostico"] else None)
        ws.cell(row=row, column=4, value=r["real"] if r["real"] == r["real"] else None)
        ws.cell(row=row, column=5, value=round(r["error"], 1) if r["error"] == r["error"] else None)
        pct = r.get("error_pct")
        ws.cell(row=row, column=6, value=f"{pct:.0%}" if pct == pct and pct is not None else "—")
        ws.cell(row=row, column=7, value=r["modelo"])
        ws.cell(row=row, column=8, value=r["observacion"])
        row += 1

    widths = [12, 24, 14, 12, 14, 12, 24, 30]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    wb.save(ruta)
