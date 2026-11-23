"""Gráficos estáticos con matplotlib (backend Agg)."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROJO, GRIS, AZUL, VERDE = "#D4380D", "#8C8C8C", "#1D5FA8", "#389E0D"
COLOR_POL = {"P0": ROJO, "P1": "#D9A441", "P2": "#9E6FB8", "P3": GRIS, "P4": VERDE}
plt.rcParams.update({"figure.dpi": 100, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.25, "font.size": 10})


def _fig(w=8, h=3.6):
    return plt.subplots(figsize=(w, h), layout="constrained")


def serie(m, pid, nombre):
    fig, ax = _fig()
    ax.plot(m.index, m[pid], marker="o", color=AZUL, lw=1.5)
    for x in m.index[m.index.dayofweek >= 5]:
        ax.axvspan(x - np.timedelta64(12, "h"), x + np.timedelta64(12, "h"), color=GRIS, alpha=0.12, lw=0)
    ax.set_title(f"Ventas diarias — {nombre}")
    ax.set_ylabel("Unidades")
    fig.autofmt_xdate()
    return fig


def dia_semana(perfil, pid, nombre):
    fig, ax = _fig(7, 3.2)
    v = perfil[pid]
    ax.bar(v.index, v.values, color=[ROJO if x == v.max() else AZUL for x in v.values])
    ax.set_title(f"Venta media por día de la semana — {nombre}")
    ax.set_ylabel("Unidades promedio")
    return fig


def real_vs_pronostico(m, r, pid, nombre):
    fig, ax = _fig()
    ax.plot(m.index, m[pid], marker="o", color=GRIS, label="Venta real", lw=1.2)
    ax.plot(r["fechas_prueba"], r["pred_ganador"], marker="s", color=AZUL, lw=1.5,
            label=f"Pronóstico backtesting ({r['ganador']})")
    ax.plot(r["fechas_fut"], r["pron_fut"], marker="^", ls="--", color=ROJO, label="Pronóstico próximos 7 días")
    ax.set_title(f"Real vs. pronóstico — {nombre}")
    ax.set_ylabel("Unidades")
    ax.legend(fontsize=8, loc="upper left")
    fig.autofmt_xdate()
    return fig


def errores_modelos(rank, nombre):
    fig, ax = _fig(7, 3.6)
    met = rank["metrica_principal"].iloc[0]
    d = rank.sort_values(met, ascending=False)
    ax.barh(d["modelo"], d[met], color=[VERDE if i == len(d) - 1 else GRIS for i in range(len(d))])
    ax.axvline(1, color=ROJO, ls=":", lw=1)
    ax.set_xlabel(f"{met} (menor es mejor; 1 = igual que naïve)")
    ax.set_title(f"Comparación de modelos — {nombre}")
    return fig


def costo_politicas(res):
    fig, ax = _fig(7, 3.6)
    ax.bar(res["politica"], res["costo_merma"], color="#F4A582", label="Merma (sobrante)")
    ax.bar(res["politica"], res["margen_perdido"], bottom=res["costo_merma"], color="#92C5DE",
           label="Margen perdido (faltante)")
    for x, t in zip(res["politica"], res["costo_total"]):
        ax.text(x, t, f"S/ {t:,.0f}", ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax.set_ylabel("Costo total en S/ (⚠ simulado)")
    ax.set_title("Costo total por política en el periodo de prueba")
    ax.legend(fontsize=8)
    return fig


def merma_faltante(pp, nombres):
    d = pp[pp["politica"].isin(["P0", "P4"])].pivot(index="producto_id", columns="politica",
                                                     values=["costo_merma", "margen_perdido"])
    fig, ax = _fig(8, max(3.2, 0.45 * len(d) + 1))
    y = np.arange(len(d))
    lab = [nombres.get(i, i)[:22] for i in d.index]
    ax.barh(y + 0.2, d[("costo_merma", "P0")], 0.4, color=ROJO, alpha=0.85, label="Merma P0")
    ax.barh(y + 0.2, d[("margen_perdido", "P0")], 0.4, left=d[("costo_merma", "P0")], color=ROJO, alpha=0.4,
            label="Faltante P0")
    ax.barh(y - 0.2, d[("costo_merma", "P4")], 0.4, color=VERDE, alpha=0.85, label="Merma P4 (VICTORA)")
    ax.barh(y - 0.2, d[("margen_perdido", "P4")], 0.4, left=d[("costo_merma", "P4")], color=VERDE, alpha=0.4,
            label="Faltante P4 (VICTORA)")
    ax.set_yticks(y, lab)
    ax.set_xlabel("S/ (⚠ simulado)")
    ax.set_title("Merma y faltante por producto: práctica habitual (P0) vs. VICTORA (P4)")
    ax.legend(fontsize=7, loc="lower right")
    return fig


def sensibilidad(s):
    fig, ax = _fig(7, 3.4)
    ax.plot(s["colchon_pct"], s["costo_P0"], marker="o", color=ROJO, label="P0 práctica habitual")
    ax.plot(s["colchon_pct"], s["costo_P4"], marker="s", color=VERDE, label="P4 VICTORA")
    ax.set_xlabel("Colchón de P0 (%)")
    ax.set_ylabel("Costo total S/ (⚠ simulado)")
    ax.set_title("Sensibilidad al colchón de la práctica habitual")
    ax.legend(fontsize=8)
    return fig


def victorias(rank_all):
    g = rank_all[rank_all["posicion"] == 1]["modelo"].value_counts()
    fig, ax = _fig(7, 3.2)
    ax.barh(g.index[::-1], g.values[::-1], color=AZUL)
    ax.set_xlabel("Número de productos en los que ganó")
    ax.set_title("Frecuencia de victorias por modelo")
    return fig
