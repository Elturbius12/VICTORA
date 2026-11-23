"""Orquestador: ejecuta todo el análisis una sola vez y devuelve un diccionario de resultados."""
from __future__ import annotations

import time
from datetime import datetime

import numpy as np
import pandas as pd

from . import SEMILLA, __version__
from . import descriptivos as ds
from . import estadistica as es
from .decision import explosion_insumos, plan_produccion
from .seleccion import seleccionar
from .simulacion import COLCHON_DEFECTO, resumir, sensibilidad, simular
from .utils import hash_df
from .validador import completar_ventas

PASOS = ["Preparando datos…", "Calculando descriptivos…", "Entrenando y validando modelos…",
         "Calculando plan de producción (newsvendor)…", "Simulando políticas…",
         "Análisis de sensibilidad…", "Pruebas estadísticas…", "Redactando textos…", "Generando reportes Excel…"]


def ejecutar(datos: dict, tratamiento_huecos: dict | None = None, colchon: float = COLCHON_DEFECTO,
             progreso=None) -> dict:
    """progreso(fraccion, texto) se llama en cada paso."""
    np.random.seed(SEMILLA)
    t_ini = time.perf_counter()

    def paso(i):
        if progreso:
            progreso(i / len(PASOS), PASOS[i])

    paso(0)
    prod = datos["Productos"].reset_index(drop=True)
    m = completar_ventas(datos, tratamiento_huecos)
    pr = datos.get("Produccion_real")
    R = {"productos": prod, "m": m, "recetas": datos["Recetas"], "ventas": datos["Ventas"],
         "calendario": datos.get("Calendario"), "produccion_real": pr, "colchon": colchon,
         "n_dias": len(m), "n_productos": m.shape[1], "fecha_ini": m.index.min(), "fecha_fin": m.index.max(),
         "nombres": prod.set_index("producto_id")["nombre"].to_dict(), "version": __version__,
         "semilla": SEMILLA, "generado": datetime.now().strftime("%Y-%m-%d %H:%M"),
         "hash": hash_df(datos["Productos"], datos["Ventas"], datos["Recetas"]),
         "tratamiento_huecos": {str(pd.Timestamp(k).date()): v for k, v in (tratamiento_huecos or {}).items()}}
    R["n_agotados"] = int(datos["Ventas"]["agotado"].sum())

    paso(1)
    R["desc"] = ds.descriptivos(m, prod)
    R["clasif"] = ds.clasificacion(m, prod)
    R["perfil"], R["kw"] = ds.dia_semana(m)
    R["corr"], R["corr_dow"] = ds.correlaciones(m)

    paso(2)
    sel = seleccionar(m, R["clasif"])
    R["sel"] = sel
    R["ranking"] = pd.concat([s["ranking"].assign(producto_id=p) for p, s in sel.items()], ignore_index=True)
    R["backtest"] = pd.concat([s["backtest"].assign(producto_id=p) for p, s in sel.items()], ignore_index=True)
    R["ganadores"] = pd.concat([s["ranking"].head(1).assign(producto_id=p) for p, s in sel.items()], ignore_index=True)
    R["n_prueba"] = int(np.median([len(s["real"]) for s in sel.values()]))

    paso(3)
    R["plan"] = plan_produccion(sel, m, prod)
    R["insumos_dia"], R["insumos_sem"] = explosion_insumos(R["plan"], datos["Recetas"])

    paso(4)
    R["det"] = simular(m, prod, sel, colchon=colchon, produccion_real=pr)
    R["fuente"] = "REAL" if (R["det"]["fuente"] == "REAL").any() else "SIMULADO"
    R["res_pol"], R["res_pp"] = resumir(R["det"])

    paso(5)
    R["sens_col"], R["sens_mar"] = sensibilidad(m, prod, sel)

    paso(6)
    R["wilcoxon"] = es.wilcoxon(R["det"])
    R["friedman"] = es.friedman(R["det"])
    R["boot"] = es.bootstrap_ahorro(R["det"])

    paso(7)
    from . import textos
    R["limitaciones"] = textos.limitaciones(R)
    R["texto_metodos"] = textos.metodos(R)
    R["texto_resultados"] = textos.resultados(R)
    R["texto_resumen"] = textos.resumen(R)

    paso(8)
    from . import reporte_excel
    R["excel_reporte"] = reporte_excel.reporte_completo(R)
    R["excel_plan"] = reporte_excel.plan_cocina(R)
    R["segundos"] = time.perf_counter() - t_ini
    if progreso:
        progreso(1.0, f"Listo en {R['segundos']:.1f} s")
    return R
