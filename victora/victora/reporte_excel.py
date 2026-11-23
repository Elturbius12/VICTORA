"""Generación del libro Excel de reporte (para el artículo) y del plan de cocina."""
from __future__ import annotations

import io
import platform
from importlib.metadata import PackageNotFoundError, version

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import graficos as gr
from .simulacion import POLITICAS
from .utils import fig_a_png

HOJAS = {
    "00_Portada": "Título, fecha, versión, periodo, número de productos y días, parámetros.",
    "01_Resumen": "Hallazgos clave en lenguaje llano.",
    "02_Problema_Ahorro": "Costo por política y ahorro de VICTORA frente a la práctica habitual.",
    "03_Descriptivos": "Estadística descriptiva por producto.",
    "04_Clasificacion": "ADI, CV², tipo de demanda, ABC y XYZ.",
    "05_Dia_Semana": "Perfil por día de la semana y Kruskal-Wallis.",
    "06_Correlaciones": "Spearman entre productos y con el día de la semana.",
    "07_Backtesting": "Errores por producto, modelo y fecha.",
    "08_Ranking_Modelos": "MASE, RMSSE, MAE, RMSE, WAPE, sesgo; ganador y frecuencia de victorias.",
    "09_Pruebas": "Wilcoxon, Friedman y bootstrap.",
    "10_Simulacion": "Resultados completos de la simulación contrafactual.",
    "11_Sensibilidad": "Sensibilidad al colchón de P0 y al margen.",
    "12_Plan_Produccion": "Producción recomendada para 7 días con intervalo.",
    "13_Insumos": "Necesidad de insumos y lista de compras.",
    "14_Texto_Metodos": "Párrafos de métodos ya redactados.",
    "15_Texto_Resultados": "Párrafos de resultados ya redactados.",
    "16_Limitaciones": "Limitaciones del estudio.",
    "17_Figuras": "Figuras con título y leyenda sugeridos (300 dpi).",
    "18_Reproducibilidad": "Versiones, semilla, parámetros y hash de los datos.",
    "99_Datos_Limpios": "Datos validados usados en el análisis.",
}


class _Libro:
    def __init__(self, wb):
        self.wb = wb
        self.f = {
            "tit": wb.add_format({"bold": True, "font_size": 12}),
            "h1": wb.add_format({"bold": True, "font_size": 18, "font_color": "#D4380D"}),
            "head": wb.add_format({"bold": True, "bg_color": "#FADBD8", "border": 1, "text_wrap": True, "valign": "top"}),
            "cel": wb.add_format({"border": 1}),
            "num": wb.add_format({"border": 1, "num_format": "#,##0.00"}),
            "ent": wb.add_format({"border": 1, "num_format": "#,##0"}),
            "p": wb.add_format({"border": 1, "num_format": "0.0000"}),
            "fecha": wb.add_format({"border": 1, "num_format": "yyyy-mm-dd"}),
            "nota": wb.add_format({"italic": True, "font_color": "#595959", "text_wrap": True, "valign": "top"}),
            "par": wb.add_format({"text_wrap": True, "valign": "top"}),
            "sim": wb.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": "#D4380D"}),
        }
        self.n_tabla = 0

    def tabla(self, ws, fila, df: pd.DataFrame, titulo: str, nota: str, numerar=True, col=0) -> int:
        """Escribe una tabla con título numerado y nota; devuelve la siguiente fila libre."""
        if numerar:
            self.n_tabla += 1
            titulo = f"Tabla {self.n_tabla}. {titulo}"
        ws.write(fila, col, titulo, self.f["tit"])
        fila += 1
        for j, c in enumerate(df.columns):
            ws.write(fila, col + j, str(c), self.f["head"])
            ws.set_column(col + j, col + j, max(12, min(40, len(str(c)) + 2)))
        for i, r in enumerate(df.itertuples(index=False), start=fila + 1):
            for j, v in enumerate(r):
                if isinstance(v, (pd.Timestamp, np.datetime64)):
                    ws.write_datetime(i, col + j, pd.Timestamp(v).to_pydatetime(), self.f["fecha"])
                elif isinstance(v, (bool, np.bool_)):
                    ws.write(i, col + j, "Sí" if v else "No", self.f["cel"])
                elif isinstance(v, (int, np.integer)):
                    ws.write_number(i, col + j, int(v), self.f["ent"])
                elif isinstance(v, (float, np.floating)):
                    if np.isfinite(v):
                        es_p = "p_" in str(df.columns[j]).lower() or str(df.columns[j]).lower().startswith("p_")
                        ws.write_number(i, col + j, float(v), self.f["p"] if es_p else self.f["num"])
                    else:
                        ws.write(i, col + j, "—", self.f["cel"])
                else:
                    ws.write(i, col + j, "" if v is None else str(v), self.f["cel"])
        fila += len(df) + 1
        ws.merge_range(fila, col, fila + 1, col + max(len(df.columns) - 1, 6), f"Nota. {nota}", self.f["nota"])
        return fila + 3

    def parrafos(self, ws, fila, items, ancho=120):
        ws.set_column(0, 0, ancho)
        for sub, txt in items:
            if sub:
                ws.write(fila, 0, sub, self.f["tit"])
                fila += 1
            ws.write(fila, 0, txt, self.f["par"])
            ws.set_row(fila, 15 * (len(txt) // 105 + 1))
            fila += 2
        return fila


def _r(df, d=4):
    return df.round(d)


def _version(p):
    try:
        return version(p)
    except PackageNotFoundError:
        return "no instalado"


def figuras(R) -> list[tuple[str, str, bytes]]:
    """(título, leyenda, png 300 dpi) de las figuras globales del reporte."""
    nom = R["nombres"]
    total = R["m"].sum(axis=1).to_frame("Total")
    perfil_tot = R["perfil"].sum(axis=1).to_frame("Total")
    pid_top = R["desc"].sort_values("media", ascending=False)["producto_id"].iloc[0]
    specs = [
        ("Costo total por política de producción", "Costo de merma y margen perdido acumulados en el periodo de "
         f"prueba para cada política (P0–P4). Valores {R['fuente'].lower()}s.", lambda: gr.costo_politicas(R["res_pol"])),
        ("Merma y faltante por producto: P0 vs. VICTORA", "Comparación por producto del costo de merma y de margen "
         "perdido entre la práctica habitual simulada y VICTORA.", lambda: gr.merma_faltante(R["res_pp"], nom)),
        ("Sensibilidad al colchón de la práctica habitual", "Costo total de P0 al variar su colchón frente al costo "
         "de VICTORA (constante).", lambda: gr.sensibilidad(R["sens_col"])),
        ("Frecuencia de victorias por modelo", "Número de productos en que cada modelo obtuvo el menor error "
         "escalado en la validación con origen rodante.", lambda: gr.victorias(R["ranking"])),
        ("Ventas diarias totales", "Suma de las unidades vendidas de todos los productos por día; sombreado = fin "
         "de semana.", lambda: gr.serie(total, "Total", "todos los productos")),
        ("Perfil semanal de la demanda total", "Venta media total por día de la semana.",
         lambda: gr.dia_semana(perfil_tot, "Total", "todos los productos")),
        (f"Real vs. pronóstico — {nom[pid_top]}", "Ventas observadas, pronóstico de backtesting del modelo ganador "
         "y pronóstico de los próximos 7 días para el producto de mayor rotación.",
         lambda: gr.real_vs_pronostico(R["m"], R["sel"][pid_top], pid_top, nom[pid_top])),
    ]
    out = []
    for t, ley, fn in specs:
        fig = fn()
        out.append((t, ley, fig_a_png(fig, 300)))
        plt.close(fig)
    return out


def reporte_completo(R) -> bytes:
    buf = io.BytesIO()
    nom = R["nombres"]
    sim = f"⚠️ {R['fuente']}"
    with pd.ExcelWriter(buf, engine="xlsxwriter") as xw:
        wb = xw.book
        L = _Libro(wb)
        ws = {h: wb.add_worksheet(h) for h in HOJAS}

        # 00 Portada
        s = ws["00_Portada"]
        s.set_column(0, 0, 38)
        s.set_column(1, 1, 60)
        s.write(0, 0, "VICTORA — Reporte de análisis de demanda y producción", L.f["h1"])
        filas = [("Fecha de generación", R["generado"]), ("Versión del software", R["version"]),
                 ("Periodo analizado", f"{R['fecha_ini']:%Y-%m-%d} a {R['fecha_fin']:%Y-%m-%d}"),
                 ("N.º de productos", R["n_productos"]), ("N.º de días", R["n_dias"]),
                 ("Días de prueba (backtesting, mediana)", R["n_prueba"]),
                 ("Colchón de P0", f"{R['colchon'] * 100:.0f} %"), ("Semilla", R["semilla"]),
                 ("Réplicas bootstrap", R["boot"]["replicas"]), ("Origen de merma/faltante", sim),
                 ("Tipo de estudio", "Estudio piloto / prueba de concepto" if R["n_dias"] < 28 else "Estudio de caso"),
                 ("Supuesto central", "Ventas observadas = demanda")]
        for i, (a, b) in enumerate(filas, start=2):
            s.write(i, 0, a, L.f["head"])
            s.write(i, 1, b, L.f["cel"])
        s.write(len(filas) + 3, 0, "Contenido del libro", L.f["tit"])
        for i, (h, d) in enumerate(HOJAS.items(), start=len(filas) + 4):
            s.write(i, 0, h)
            s.write(i, 1, d)

        # 01 Resumen
        s = ws["01_Resumen"]
        s.set_column(0, 0, 120)
        s.write(0, 0, "Resumen de hallazgos", L.f["h1"])
        s.write(1, 0, sim, L.f["sim"])
        for i, t in enumerate(R["texto_resumen"], start=3):
            s.write(i, 0, "• " + t, L.f["par"])

        # 02 Problema y ahorro
        s = ws["02_Problema_Ahorro"]
        s.write(0, 0, sim, L.f["sim"])
        rp = R["res_pol"][["politica", "descripcion", "producido", "demanda", "sobrante", "faltante", "costo_merma",
                           "margen_perdido", "costo_total", "fill_rate_pct", "reduccion_vs_P0_pct"]]
        f = L.tabla(s, 2, _r(rp, 2), "Costo de merma y de ventas perdidas por política de producción (S/)",
                    f"Valores {R['fuente'].lower()}s en el periodo de prueba (≈{R['n_prueba']} días por producto). "
                    "Costo de merma = sobrante × Cₒ; margen perdido = faltante × Cᵤ. Reducción respecto a P0.")
        b = R["boot"]
        s.write(f, 0, f"Ahorro de VICTORA (P4) frente a P0: S/ {b['ahorro_S/']:,.2f} ({b['ahorro_pct']:.1f} %). "
                      f"IC 95 % bootstrap: {b['IC95_pct_inf']:.1f} % a {b['IC95_pct_sup']:.1f} %.", L.f["tit"])

        # 03 Descriptivos
        L.tabla(ws["03_Descriptivos"], 0, _r(R["desc"], 3), "Estadística descriptiva de las ventas diarias por producto",
                f"n = días analizados; DE = desviación estándar; CV = DE/media. Asimetría y curtosis (exceso) "
                "con corrección de sesgo.")

        # 04 Clasificación
        c = R["clasif"].copy()
        c["ADI"] = c["ADI"].replace(np.inf, np.nan)
        L.tabla(ws["04_Clasificacion"], 0, _r(c, 3), "Clasificación de la demanda (Syntetos–Boylan y ABC-XYZ)",
                "ADI = intervalo medio entre demandas; CV² de tamaños no nulos. Umbrales ADI = 1,32 y CV² = 0,49. "
                "ABC por ingreso acumulado (80/95 %); XYZ por CV (≤0,5; ≤1,0; >1,0).")

        # 05 Día semana
        s = ws["05_Dia_Semana"]
        perf = R["perfil"].rename(columns=nom).reset_index().rename(columns={"index": "dia"})
        f = L.tabla(s, 0, _r(perf, 2), "Venta media por día de la semana y producto", "Unidades promedio.")
        L.tabla(s, f, _r(R["kw"], 4), "Prueba de Kruskal-Wallis del efecto día de la semana por producto",
                "ε² = (H − k + 1)/(n − k). Con ≤ 3 observaciones por día la potencia es baja: un p no significativo "
                "no implica ausencia de efecto.")

        # 06 Correlaciones
        s = ws["06_Correlaciones"]
        corr = R["corr"].reset_index().rename(columns={"producto_id": "producto"})
        f = L.tabla(s, 0, _r(corr, 3), "Matriz de correlaciones de Spearman entre productos",
                    "Coeficiente ρ de Spearman sobre las ventas diarias. Se excluyen productos sin variación.")
        L.tabla(s, f, _r(R["corr_dow"], 4), "Correlación de Spearman entre ventas y día de la semana",
                "Día codificado 0 (lunes) a 6 (domingo); mide tendencia monótona a lo largo de la semana.")

        # 07 Backtesting
        bt = R["backtest"][["producto_id", "modelo", "fecha", "real", "pronostico", "error"]]
        L.tabla(ws["07_Backtesting"], 0, _r(bt, 3), "Errores de pronóstico en la validación con origen rodante",
                "Pronóstico a 1 día; error = real − pronóstico.")

        # 08 Ranking
        s = ws["08_Ranking_Modelos"]
        g = R["ganadores"][["producto_id", "modelo", "metrica_principal", "MASE", "RMSSE", "MAE", "RMSE", "WAPE", "Sesgo"]]
        g.insert(1, "nombre", g["producto_id"].map(nom))
        f = L.tabla(s, 0, _r(g, 3), "Modelo ganador por producto",
                    "Selección por MASE (RMSSE si la demanda es intermitente). MASE < 1 = mejor que naïve.")
        fq = R["ganadores"]["modelo"].value_counts().rename_axis("modelo").reset_index(name="victorias")
        f = L.tabla(s, f, fq, "Frecuencia de victorias por modelo", "Número de productos en que cada modelo fue elegido.")
        rk = R["ranking"][["producto_id", "posicion", "modelo", "MASE", "RMSSE", "MAE", "RMSE", "WAPE", "Sesgo"]]
        L.tabla(s, f, _r(rk, 3), "Ranking completo de modelos por producto", "WAPE en %; sesgo > 0 = sobrepronóstico.")

        # 09 Pruebas
        s = ws["09_Pruebas"]
        s.write(0, 0, sim, L.f["sim"])
        f = L.tabla(s, 2, _r(R["wilcoxon"], 4), "Prueba de Wilcoxon pareada: costo diario de cada política vs. VICTORA",
                    "Pares = producto-día del periodo de prueba (se excluyen diferencias nulas). r = correlación "
                    "biserial de rangos (> 0: la política comparada cuesta más que VICTORA). p ajustado por Holm.")
        fr = R["friedman"]
        frd = pd.DataFrame([{"chi2": fr["chi2"], "gl": fr["gl"], "p_valor": fr["p_valor"], "n_bloques": fr["n_bloques"],
                             "W_Kendall": fr["W_Kendall"],
                             **{f"rango_medio_{k}": v for k, v in fr["rangos_medios"].items()}}])
        f = L.tabla(s, f, _r(frd, 4), "Prueba de Friedman entre las cinco políticas",
                    "Bloques = producto-día. W de Kendall como tamaño de efecto (rango menor = menor costo).")
        L.tabla(s, f, _r(pd.DataFrame([R["boot"]]), 3), "Intervalo de confianza bootstrap del ahorro de VICTORA frente a P0",
                f"Bootstrap percentil remuestreando producto-días, {b['replicas']} réplicas, semilla {b['semilla']}.")

        # 10 Simulación
        s = ws["10_Simulacion"]
        s.write(0, 0, sim, L.f["sim"])
        pp = R["res_pp"].copy()
        pp.insert(1, "nombre", pp["producto_id"].map(nom))
        f = L.tabla(s, 2, _r(pp, 2), "Resultados de la simulación por producto y política",
                    "Unidades y S/ acumulados en el periodo de prueba. " + "; ".join(f"{k}: {v}" for k, v in POLITICAS.items()))
        L.tabla(s, f, _r(R["det"], 2), "Detalle diario de la simulación", "Supuesto: ventas observadas = demanda.")

        # 11 Sensibilidad
        s = ws["11_Sensibilidad"]
        s.write(0, 0, sim, L.f["sim"])
        f = L.tabla(s, 2, _r(R["sens_col"], 2), "Sensibilidad del ahorro al colchón de la práctica habitual (P0)",
                    "El costo de VICTORA no depende del colchón de P0.")
        L.tabla(s, f, _r(R["sens_mar"], 2), "Sensibilidad del ahorro al margen (± 10 puntos porcentuales)",
                "Se recalculan Cₒ, Cᵤ y la razón crítica de VICTORA con el margen modificado.")

        # 12 Plan
        pl = R["plan"][["fecha", "producto_id", "nombre", "modelo", "pronostico", "razon_critica", "Q_optimo",
                        "tamano_lote", "producir", "intervalo_10", "intervalo_90"]]
        L.tabla(ws["12_Plan_Produccion"], 0, _r(pl, 3), "Plan de producción recomendado para los próximos 7 días",
                "producir = Q* redondeado al entero y al lote superiores; intervalo = cuantiles 10 % y 90 % de la "
                "distribución empírica de la demanda.")

        # 13 Insumos
        s = ws["13_Insumos"]
        if len(R["insumos_sem"]):
            f = L.tabla(s, 0, _r(R["insumos_sem"], 3), "Lista de compras de insumos para la semana",
                        "Necesidad en unidad base (g, ml, unidad); 'comprar' en la unidad más práctica.")
            L.tabla(s, f, _r(R["insumos_dia"], 3), "Necesidad diaria de insumos", "Según el plan de producción.")
        else:
            s.write(0, 0, "No se registraron recetas.")

        # 14-16 textos
        s = ws["14_Texto_Metodos"]
        s.write(0, 0, "Métodos (texto listo para copiar)", L.f["h1"])
        L.parrafos(s, 2, R["texto_metodos"])
        s = ws["15_Texto_Resultados"]
        s.write(0, 0, "Resultados (texto listo para copiar)", L.f["h1"])
        s.write(1, 0, f"Cifras de costo: {sim}", L.f["sim"])
        L.parrafos(s, 3, R["texto_resultados"])
        s = ws["16_Limitaciones"]
        s.write(0, 0, "Limitaciones del estudio", L.f["h1"])
        L.parrafos(s, 2, [(None, f"{i}. {t}") for i, t in enumerate(R["limitaciones"], 1)])

        # 17 Figuras
        s = ws["17_Figuras"]
        s.set_column(0, 0, 110)
        fila = 0
        for i, (t, ley, png) in enumerate(figuras(R), 1):
            s.write(fila, 0, f"Figura {i}. {t}", L.f["tit"])
            s.write(fila + 1, 0, f"Nota. {ley}", L.f["nota"])
            s.insert_image(fila + 2, 0, f"fig{i}.png", {"image_data": io.BytesIO(png), "x_scale": 0.3, "y_scale": 0.3})
            fila += 25

        # 18 Reproducibilidad
        rep = [("VICTORA", R["version"]), ("Python", platform.python_version()), ("Sistema", platform.platform())]
        rep += [(p, _version(p)) for p in ["pandas", "numpy", "scipy", "statsmodels", "matplotlib", "xlsxwriter",
                                           "openpyxl", "streamlit"]]
        rep += [("Semilla", R["semilla"]), ("Réplicas bootstrap", R["boot"]["replicas"]),
                ("Colchón P0", R["colchon"]), ("Entrenamiento mínimo", min(s["t0"] for s in R["sel"].values())),
                ("Horizonte", "1 día (validación); 7 días (plan)"), ("Hash de datos (SHA-256, 16)", R["hash"]),
                ("Tratamiento de huecos", str(R["tratamiento_huecos"] or "ninguno")), ("Generado", R["generado"])]
        L.tabla(ws["18_Reproducibilidad"], 0, pd.DataFrame(rep, columns=["elemento", "valor"]).astype(str),
                "Información de reproducibilidad", "Dos ejecuciones con los mismos datos y parámetros dan resultados idénticos.",
                numerar=False)

        # 99 datos
        s = ws["99_Datos_Limpios"]
        f = L.tabla(s, 0, R["m"].reset_index(), "Matriz de ventas diarias (fecha × producto)", "Datos validados.", numerar=False)
        f = L.tabla(s, f, R["productos"], "Productos", "Valores por defecto aplicados.", numerar=False)
        L.tabla(s, f, R["recetas"], "Recetas", "", numerar=False)
    return buf.getvalue()


def plan_cocina(R) -> bytes:
    """Excel simple para cocina: tabla producto × día con cantidades a producir + lista de compras."""
    buf = io.BytesIO()
    pl = R["plan"].copy()
    pl["dia"] = pl["fecha"].dt.strftime("%a %d/%m")
    orden = list(dict.fromkeys(pl["dia"]))
    t = pl.pivot_table(index="nombre", columns="dia", values="producir", aggfunc="sum")[orden]
    t["TOTAL SEMANA"] = t.sum(axis=1)
    with pd.ExcelWriter(buf, engine="xlsxwriter") as xw:
        t.reset_index().rename(columns={"nombre": "Producto"}).to_excel(xw, sheet_name="Producir", index=False, startrow=2)
        s = xw.sheets["Producir"]
        big = xw.book.add_format({"bold": True, "font_size": 16})
        s.write(0, 0, "PLAN DE PRODUCCIÓN DE LA SEMANA — unidades a preparar cada día", big)
        s.set_column(0, 0, 32)
        s.set_column(1, len(t.columns), 13)
        if len(R["insumos_sem"]):
            c = R["insumos_sem"][["insumo_nombre", "comprar", "unidad", "costo_estimado", "usado_en"]]
            c.columns = ["Insumo", "Cantidad", "Unidad", "Costo estimado S/", "Usado en"]
            c.to_excel(xw, sheet_name="Compras", index=False)
            xw.sheets["Compras"].set_column(0, 4, 18)
    return buf.getvalue()
