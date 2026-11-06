"""Módulo 2 – Motor de Pronóstico."""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import numpy as np
import pandas as pd
from datetime import timedelta
import threading

from ..core.database import get_productos, get_pivot_ventas, get_config, set_config
from ..core.selection import diagnostico, modelos_sugeridos, backtest, elegir_ganador, pronosticar, simular_politica
from ..core.optimizer import razon_critica, cantidad_optima
from .tema import COLORS, FONT_FAMILY, FONT_SIZES

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


class PronosticoFrame(ctk.CTkFrame):
    """Pantalla del motor de pronóstico con competencia de modelos."""

    def __init__(self, master, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self.resultado = {}
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="🔮  Motor de Pronóstico",
                     font=(FONT_FAMILY, FONT_SIZES["title"], "bold"),
                     text_color=COLORS["primary"]).pack(anchor="w", padx=20, pady=(15, 5))

        # Controles
        ctrl = ctk.CTkFrame(self, fg_color="transparent")
        ctrl.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(ctrl, text="Producto:").pack(side="left")
        self.prod_var = ctk.StringVar()
        self.prod_combo = ctk.CTkComboBox(ctrl, variable=self.prod_var, width=220, state="readonly")
        self.prod_combo.pack(side="left", padx=5)

        ctk.CTkLabel(ctrl, text="Margen (%):").pack(side="left", padx=(15, 0))
        self.margen_var = ctk.StringVar(value="27.5")
        ctk.CTkEntry(ctrl, textvariable=self.margen_var, width=60).pack(side="left", padx=5)

        ctk.CTkButton(ctrl, text="▶ Ejecutar competencia", command=self._run,
                       fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
                       width=180).pack(side="left", padx=15)

        self.status_label = ctk.CTkLabel(self, text="Seleccione un producto y presione Ejecutar.",
                                          font=(FONT_FAMILY, FONT_SIZES["small"]),
                                          text_color=COLORS["text_muted"])
        self.status_label.pack(anchor="w", padx=20)

        # Área de resultados (scrollable)
        self.result_area = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg_card"], corner_radius=10)
        self.result_area.pack(fill="both", expand=True, padx=20, pady=10)

        self._cargar_productos()

    def _cargar_productos(self):
        prods = get_productos()
        nombres = list(prods["nombre"].values) if not prods.empty else []
        self.prod_combo.configure(values=nombres)
        if nombres:
            self.prod_var.set(nombres[0])

    def _run(self):
        nombre = self.prod_var.get()
        if not nombre:
            messagebox.showwarning("Atención", "Seleccione un producto.")
            return
        self.status_label.configure(text=f"⏳ Analizando {nombre}... esto toma unos segundos.")
        self.update_idletasks()
        threading.Thread(target=self._ejecutar, args=(nombre,), daemon=True).start()

    def _ejecutar(self, nombre):
        try:
            pivot, _ = get_pivot_ventas()
            if pivot.empty or nombre not in pivot.columns:
                self.after(0, lambda: self.status_label.configure(
                    text="⚠️ No hay datos suficientes para este producto."))
                return
            y = pivot[nombre].values.astype(float)
            dates = pivot.index

            # Diagnóstico
            diag = diagnostico(y)

            # Backtest
            res, preds = backtest(y, dates)

            # Ganador
            ganador = elegir_ganador(res)

            # Pronóstico siguiente día
            next_date = dates[-1] + timedelta(days=1)
            pron = pronosticar(y, dates, next_date, ganador, res) if ganador else 0

            # Producción óptima
            prods = get_productos()
            prod_row = prods[prods["nombre"] == nombre].iloc[0]
            margen = float(self.margen_var.get()) / 100
            cr, c, cu, co = razon_critica(prod_row["precio"], margen, prod_row["recuperable"])
            rmse = float(res[res.Modelo == ganador]["RMSE"].values[0]) if ganador and not res.empty else 1.0
            q_opt = cantidad_optima(pron, rmse, cr)

            # Simulación
            preds_ganador = preds.get(ganador, np.zeros(len(y)))
            sim = simular_politica(y, preds_ganador, prod_row["precio"], margen,
                                   prod_row["recuperable"], cr, rmse)

            self.resultado = dict(
                nombre=nombre, diag=diag, res=res, ganador=ganador,
                pron=pron, q_opt=q_opt, cr=cr, rmse=rmse,
                sim=sim, y=y, dates=dates, preds=preds, next_date=next_date
            )
            self.after(0, self._mostrar_resultados)
        except Exception as e:
            self.after(0, lambda: self.status_label.configure(text=f"❌ Error: {e}"))

    def _mostrar_resultados(self):
        r = self.resultado
        for w in self.result_area.winfo_children():
            w.destroy()

        self.status_label.configure(text=f"✅ Análisis de {r['nombre']} completado.")

        # ── Diagnóstico ──
        self._seccion("📊 Diagnóstico de demanda")
        diag = r["diag"]
        self._info(f"Clasificación: {diag['clase']}")
        self._info(f"ADI: {diag['adi']:.2f}  |  CV²: {diag['cv2']:.3f}  |  "
                   f"Días: {diag['dias']}  |  % cero: {diag['pct_cero']:.0%}")

        # ── Tabla de modelos ──
        self._seccion("🏆 Competencia de modelos (backtest)")
        res = r["res"]
        if not res.empty:
            hdr_fr = ctk.CTkFrame(self.result_area, fg_color=COLORS["bg_sidebar"], corner_radius=5)
            hdr_fr.pack(fill="x", padx=5, pady=2)
            for col, w in [("Modelo", 230), ("MAE", 70), ("RMSE", 70), ("wMAPE", 75), ("Sesgo", 70)]:
                ctk.CTkLabel(hdr_fr, text=col, width=w,
                             font=(FONT_FAMILY, FONT_SIZES["small"], "bold")).pack(side="left", padx=2)
            for i, row in res.iterrows():
                fg = COLORS["primary"] if row["Modelo"] == r["ganador"] else "transparent"
                row_fr = ctk.CTkFrame(self.result_area, fg_color=fg, corner_radius=3)
                row_fr.pack(fill="x", padx=5, pady=1)
                tag = "🥇 " if row["Modelo"] == r["ganador"] else "   "
                ctk.CTkLabel(row_fr, text=tag + row["Modelo"], width=230,
                             font=(FONT_FAMILY, FONT_SIZES["small"])).pack(side="left", padx=2)
                ctk.CTkLabel(row_fr, text=f"{row['MAE']:.2f}", width=70).pack(side="left", padx=2)
                ctk.CTkLabel(row_fr, text=f"{row['RMSE']:.2f}", width=70).pack(side="left", padx=2)
                ctk.CTkLabel(row_fr, text=f"{row['wMAPE']:.1%}", width=75).pack(side="left", padx=2)
                ctk.CTkLabel(row_fr, text=f"{row['Sesgo']:+.2f}", width=70).pack(side="left", padx=2)

        # ── Resultado ──
        self._seccion("🎯 Pronóstico para mañana")
        self._info(f"Modelo ganador: {r['ganador']}")
        self._info(f"Demanda pronosticada: {r['pron']:.1f} unidades")
        self._info(f"Razón crítica (CR): {r['cr']:.2%}")
        self._info(f"Cantidad óptima a producir: {r['q_opt']} unidades")

        # ── Simulación ──
        self._seccion("💰 Simulación: Método habitual vs. Modelo")
        sim = r["sim"]
        for label, key in [("Método habitual", "base"), ("Con modelo", "modelo")]:
            s = sim[key]
            self._info(f"  {label}:  Utilidad S/ {s['u']:.0f}  |  "
                       f"Sobrantes: {s['sobra']:.0f}  |  Faltantes: {s['falta']:.0f}")
        ahorro = sim["modelo"]["u"] - sim["base"]["u"]
        color = COLORS["success"] if ahorro >= 0 else COLORS["danger"]
        lbl = ctk.CTkLabel(self.result_area,
                           text=f"{'📈 Ganancia' if ahorro >= 0 else '📉 Pérdida'} con modelo: S/ {ahorro:+.0f}",
                           font=(FONT_FAMILY, FONT_SIZES["subtitle"], "bold"),
                           text_color=color)
        lbl.pack(anchor="w", padx=15, pady=5)

        # ── Gráfico ──
        if HAS_MPL:
            self._graficar(r)

    def _graficar(self, r):
        fig = Figure(figsize=(7, 2.5), dpi=100, facecolor=COLORS["bg_card"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(COLORS["bg_card"])
        ax.plot(r["dates"], r["y"], "o-", color=COLORS["info"], markersize=3, label="Real")
        if r["ganador"] in r["preds"]:
            p = r["preds"][r["ganador"]]
            mask = ~np.isnan(p)
            ax.plot(r["dates"][mask], p[mask], "--", color=COLORS["warning"], label=r["ganador"])
        ax.set_title(f"{r['nombre']} – Pronóstico", color=COLORS["text"], fontsize=10)
        ax.tick_params(colors=COLORS["text_muted"], labelsize=8)
        ax.legend(fontsize=8, facecolor=COLORS["bg_card"], edgecolor="none",
                  labelcolor=COLORS["text"])
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.result_area)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="x", padx=10, pady=5)

    # ── Helpers ─────────────────────────────────────────────────────────
    def _seccion(self, titulo):
        ctk.CTkLabel(self.result_area, text=titulo,
                     font=(FONT_FAMILY, FONT_SIZES["subtitle"], "bold"),
                     text_color=COLORS["primary"]).pack(anchor="w", padx=10, pady=(12, 3))

    def _info(self, texto):
        ctk.CTkLabel(self.result_area, text=texto,
                     font=(FONT_FAMILY, FONT_SIZES["body"]),
                     text_color=COLORS["text"]).pack(anchor="w", padx=15, pady=1)
