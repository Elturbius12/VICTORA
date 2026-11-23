"""Generación de figuras PNG (300 dpi) para el reporte y para el ZIP de figuras."""
from __future__ import annotations

import io
import zipfile

import matplotlib.pyplot as plt

from . import graficos as gr
from .utils import fig_a_png


def figuras_globales(R, dpi: int = 300) -> list[tuple[str, str, bytes]]:
    """(título, leyenda sugerida, png) de las figuras globales del estudio."""
    nom = R["nombres"]
    total = R["m"].sum(axis=1).to_frame("Total")
    perfil_tot = R["perfil"].sum(axis=1).to_frame("Total")
    top = R["desc"].sort_values("media", ascending=False)["producto_id"].iloc[0]
    fuente = R["fuente"].lower() + "s"
    specs = [
        ("Costo total por política de producción",
         f"Costo de merma y margen perdido acumulados en el periodo de prueba para cada política (P0–P4). Valores {fuente}.",
         lambda: gr.costo_politicas(R["res_pol"])),
        ("Merma y faltante por producto: práctica habitual vs. VICTORA",
         "Comparación por producto del costo de merma y de margen perdido entre P0 y P4.",
         lambda: gr.merma_faltante(R["res_pp"], nom)),
        ("Sensibilidad al colchón de la práctica habitual",
         "Costo total de P0 al variar su colchón frente al costo de VICTORA (constante).",
         lambda: gr.sensibilidad(R["sens_col"])),
        ("Frecuencia de victorias por modelo",
         "Número de productos en que cada modelo obtuvo el menor error escalado en la validación con origen rodante.",
         lambda: gr.victorias(R["ganadores"])),
        ("Análisis ABC de los productos por ingreso",
         "Ingreso por producto en orden decreciente (Pareto) con la clase ABC.",
         lambda: gr.abc(R["clasif"], nom)),
        ("Correlaciones de Spearman entre productos",
         "Matriz de correlaciones de Spearman de las ventas diarias.",
         lambda: gr.heatmap(R["corr"], nom)),
        ("Ventas diarias totales",
         "Suma de las unidades vendidas de todos los productos por día; sombreado = fin de semana.",
         lambda: gr.serie(total, "Total", "todos los productos")),
        ("Perfil semanal de la demanda total", "Venta media total por día de la semana.",
         lambda: gr.dia_semana(perfil_tot, "Total", "todos los productos")),
        (f"Real vs. pronóstico — {nom[top]}",
         "Ventas observadas, pronóstico de backtesting del modelo ganador y pronóstico de los próximos 7 días "
         "(banda = intervalo 10–90 %) para el producto de mayor rotación.",
         lambda: gr.real_vs_pronostico(R["m"], R["sel"][top], top, nom[top], R["plan"])),
    ]
    out = []
    for t, ley, fn in specs:
        f = fn()
        out.append((t, ley, fig_a_png(f, dpi)))
        plt.close(f)
    return out


def zip_figuras(figs: list[tuple[str, str, bytes]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for i, (t, ley, png) in enumerate(figs, 1):
            z.writestr(f"Figura_{i:02d}.png", png)
        z.writestr("Leyendas.txt", "\n\n".join(f"Figura {i}. {t}\nNota. {ley}" for i, (t, ley, _) in enumerate(figs, 1)))
    return buf.getvalue()


def zip_figuras_producto(R, dpi: int = 300) -> bytes:
    """Figuras individuales (serie, día de semana, real vs pronóstico) de TODOS los productos."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for pid in R["m"].columns:
            n = R["nombres"][pid]
            for sufijo, mk in [("serie", lambda: gr.serie(R["m"], pid, n)),
                               ("dia_semana", lambda: gr.dia_semana(R["perfil"], pid, n)),
                               ("pronostico", lambda: gr.real_vs_pronostico(R["m"], R["sel"][pid], pid, n, R["plan"]))]:
                f = mk()
                z.writestr(f"{pid}_{sufijo}.png", fig_a_png(f, dpi))
                plt.close(f)
    return buf.getvalue()
