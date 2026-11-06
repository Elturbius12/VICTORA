"""Módulo 2 – Motor de Pronóstico."""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import numpy as np
import pandas as pd
from datetime import timedelta
import threading

from core.database import get_productos, get_pivot_ventas, get_config, set_config
from core.selection import diagnostico, modelos_sugeridos, backtest, elegir_ganador, pronosticar, simular_politica
from core.optimizer import razon_critica, cantidad_optima
from core.reportes import calcular_recomendaciones_todas
from .tema import COLORS, FONT_FAMILY, FONT_SIZES

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

# Traducción de la clasificación técnica a lenguaje cotidiano
CLASE_SIMPLE = {
    "Suave (estable)": ("📈 Se vende de forma pareja", "Casi todos los días vende una cantidad parecida de este producto."),
    "Errática (variable)": ("🎢 Las ventas suben y bajan mucho", "Unos días vende bastante y otros días casi nada."),
    "Intermitente": ("🌙 Se vende pocas veces", "Hay varios días seguidos sin ninguna venta, pero cuando se vende, es poca cantidad."),
    "Irregular (grumosa)": ("⚡ Se vende poco, pero a veces de golpe", "La mayoría de días no se vende nada, pero de vez en cuando se vende bastante de una sola vez."),
    "Sin ventas": ("❔ Todavía no hay suficiente información", "Necesita registrar más días de ventas de este producto."),
}


class PronosticoFrame(ctk.CTkFrame):
    """Pantalla del motor de pronóstico con competencia de modelos."""

    def __init__(self, master, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self.resultado = {}
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="🔮  ¿Cuánto debo preparar mañana?",
                     font=(FONT_FAMILY, FONT_SIZES["title"], "bold"),
                     text_color=COLORS["primary"]).pack(anchor="w", padx=20, pady=(15, 2))
        ctk.CTkLabel(self, text="Elija un producto y el sistema probará varias formas de adivinar "
                                "la demanda, quedándose con la que mejor funcionó en su negocio.",
                     font=(FONT_FAMILY, FONT_SIZES["small"]),
                     text_color=COLORS["text_muted"]).pack(anchor="w", padx=20, pady=(0, 8))

        # Controles
        ctrl = ctk.CTkFrame(self, fg_color="transparent")
        ctrl.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(ctrl, text="Producto:").pack(side="left")
        self.prod_var = ctk.StringVar()
        self.prod_combo = ctk.CTkComboBox(ctrl, variable=self.prod_var, width=220, state="readonly")
        self.prod_combo.pack(side="left", padx=5)

        ctk.CTkLabel(ctrl, text="Ganancia sobre el precio (%):").pack(side="left", padx=(15, 0))
        self.margen_var = ctk.StringVar(value="27.5")
        ctk.CTkEntry(ctrl, textvariable=self.margen_var, width=60).pack(side="left", padx=5)

        ctk.CTkButton(ctrl, text="▶ Calcular este producto", command=self._run,
                       fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
                       width=180).pack(side="left", padx=15)

        ctk.CTkButton(ctrl, text="📊 Calcular todo", command=self._run_todos,
                       fg_color=COLORS["info"], width=150).pack(side="left", padx=5)

        self.status_label = ctk.CTkLabel(self, text="Seleccione un producto y presione Calcular, "
                                                     "o use 'Calcular todo' para ver todos de una vez.",
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

    def _run_todos(self):
        self.status_label.configure(text="⏳ Calculando recomendaciones para todos los productos... "
                                          "esto puede tardar un momento.")
        self.update_idletasks()
        threading.Thread(target=self._ejecutar_todos, daemon=True).start()

    def _ejecutar_todos(self):
        try:
            margen = float(self.margen_var.get()) / 100
            resultados = calcular_recomendaciones_todas(margen=margen)
            self.after(0, lambda: self._mostrar_todos(resultados))
        except Exception as e:
            self.after(0, lambda: self.status_label.configure(text=f"❌ Error: {e}"))

    def _mostrar_todos(self, resultados):
        for w in self.result_area.winfo_children():
            w.destroy()

        if not resultados:
            self.status_label.configure(text="⚠️ Todavía no hay suficientes días de ventas "
                                              "registrados para calcular. Se necesitan al menos "
                                              "5 días por producto.")
            return

        self.status_label.configure(text=f"✅ Recomendaciones listas para {len(resultados)} productos.")

        self._seccion("📊 Recomendación para todos los productos")
        self._info("Esta tabla muestra cuánto preparar mañana de cada producto, calculado "
                   "individualmente para cada uno.")

        hdr = ctk.CTkFrame(self.result_area, fg_color=COLORS["bg_sidebar"], corner_radius=5)
        hdr.pack(fill="x", padx=5, pady=(8, 2))
        for col, w in [("Producto", 230), ("Cantidad a preparar", 160),
                       ("Método usado", 220), ("Ganancia estimada", 150)]:
            ctk.CTkLabel(hdr, text=col, width=w,
                         font=(FONT_FAMILY, FONT_SIZES["small"], "bold")).pack(side="left", padx=3)

        for r in resultados:
            fr = ctk.CTkFrame(self.result_area, fg_color="transparent")
            fr.pack(fill="x", padx=5, pady=1)
            nombre_txt = r["nombre"] + ("  ⚠️" if r["sin_precio"] else "")
            ctk.CTkLabel(fr, text=nombre_txt, width=230,
                         font=(FONT_FAMILY, FONT_SIZES["small"]),
                         text_color=COLORS["warning"] if r["sin_precio"] else COLORS["text"]
                         ).pack(side="left", padx=3)
            ctk.CTkLabel(fr, text=f"{r['cantidad']} unidades", width=160,
                         font=(FONT_FAMILY, FONT_SIZES["small"], "bold"),
                         text_color=COLORS["success"]).pack(side="left", padx=3)
            ctk.CTkLabel(fr, text=r["modelo"], width=220,
                         font=(FONT_FAMILY, FONT_SIZES["small"]),
                         text_color=COLORS["text_muted"]).pack(side="left", padx=3)
            ganancia_txt = f"S/ {r['ganancia_estimada']:.0f}" if r["ganancia_estimada"] is not None else "Sin precio"
            ctk.CTkLabel(fr, text=ganancia_txt, width=150,
                         font=(FONT_FAMILY, FONT_SIZES["small"])).pack(side="left", padx=3)

    def _ejecutar(self, nombre):
        try:
            pivot, _ = get_pivot_ventas()
            if pivot.empty or nombre not in pivot.columns:
                self.after(0, lambda: self.status_label.configure(
                    text="⚠️ No hay suficientes ventas registradas de este producto todavía."))
                return
            y = pivot[nombre].values.astype(float)
            dates = pivot.index

            if len(y) < 5:
                self.after(0, lambda: self.status_label.configure(
                    text=f"⚠️ Solo hay {len(y)} día(s) registrado(s) de este producto. "
                         "Se necesitan al menos 5 días para un cálculo confiable."))
                return

            # Diagnóstico
            diag = diagnostico(y)

            # Backtest (competencia de modelos)
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
            precio = float(prod_row["precio"])
            sin_precio = precio <= 0
            cr, c, cu, co = razon_critica(precio, margen, prod_row["recuperable"])
            rmse = float(res[res.Modelo == ganador]["RMSE"].values[0]) if ganador and not res.empty else 1.0
            q_opt = cantidad_optima(pron, rmse, cr)

            # Simulación
            preds_ganador = preds.get(ganador, np.zeros(len(y)))
            sim = simular_politica(y, preds_ganador, precio, margen,
                                   prod_row["recuperable"], cr, rmse)

            self.resultado = dict(
                nombre=nombre, diag=diag, res=res, ganador=ganador,
                pron=pron, q_opt=q_opt, cr=cr, rmse=rmse,
                sim=sim, y=y, dates=dates, preds=preds, next_date=next_date,
                sin_precio=sin_precio, precio=precio
            )
            self.after(0, self._mostrar_resultados)
        except Exception as e:
            self.after(0, lambda: self.status_label.configure(text=f"❌ Error: {e}"))

    def _mostrar_resultados(self):
        r = self.resultado
        for w in self.result_area.winfo_children():
            w.destroy()

        self.status_label.configure(text=f"✅ Análisis de {r['nombre']} completado.")

        # ── Aviso si no tiene precio ──
        if r["sin_precio"]:
            aviso = ctk.CTkFrame(self.result_area, fg_color=COLORS["danger"], corner_radius=8)
            aviso.pack(fill="x", padx=10, pady=(10, 5))
            ctk.CTkLabel(aviso, text="⚠️  Este producto no tiene un precio registrado todavía.\n"
                                     "La cantidad a producir sí es confiable, pero la ganancia "
                                     "estimada en S/ no lo será hasta que le ponga un precio en "
                                     "'Registro de Ventas'.",
                         font=(FONT_FAMILY, FONT_SIZES["body"], "bold"),
                         text_color="white", justify="left").pack(padx=15, pady=10, anchor="w")

        # ── Cómo se vende este producto ──
        self._seccion("🧭 ¿Cómo se vende este producto?")
        diag = r["diag"]
        titulo, detalle = CLASE_SIMPLE.get(diag["clase"], ("", ""))
        self._info(titulo, bold=True)
        self._info(detalle)
        self._info(f"(Basado en {diag['dias']} días de ventas registradas)", muted=True)

        # ── Competencia de métodos ──
        self._seccion("🏆 Comparamos varias formas de adivinar la demanda")
        self._info("Probamos distintas maneras de calcular cuánto se va a vender. "
                   "Esta tabla muestra cuánto se equivocó cada una en los días pasados "
                   "(mientras más bajo, mejor).")
        res = r["res"]
        if not res.empty:
            hdr_fr = ctk.CTkFrame(self.result_area, fg_color=COLORS["bg_sidebar"], corner_radius=5)
            hdr_fr.pack(fill="x", padx=5, pady=(8, 2))
            for col, w in [("Método", 260), ("Se equivocó en promedio (unidades)", 260),
                           ("Error (%)", 100)]:
                ctk.CTkLabel(hdr_fr, text=col, width=w,
                             font=(FONT_FAMILY, FONT_SIZES["small"], "bold")).pack(side="left", padx=2)
            for i, row in res.iterrows():
                fg = COLORS["primary"] if row["Modelo"] == r["ganador"] else "transparent"
                row_fr = ctk.CTkFrame(self.result_area, fg_color=fg, corner_radius=3)
                row_fr.pack(fill="x", padx=5, pady=1)
                tag = "🥇 " if row["Modelo"] == r["ganador"] else "   "
                ctk.CTkLabel(row_fr, text=tag + row["Modelo"], width=260,
                             font=(FONT_FAMILY, FONT_SIZES["small"])).pack(side="left", padx=2)
                ctk.CTkLabel(row_fr, text=f"{row['MAE']:.1f} unidades", width=260).pack(side="left", padx=2)
                ctk.CTkLabel(row_fr, text=f"{row['wMAPE']:.0%}", width=100).pack(side="left", padx=2)

        # ── Resultado principal ──
        self._seccion("🎯 Nuestra recomendación para mañana")
        self._info(f"El método que mejor funcionó para \"{r['nombre']}\" fue: {r['ganador']}")
        self._info(f"Con ese método, se espera vender aproximadamente {r['pron']:.1f} unidades mañana.")

        # Caja destacada con la cantidad a producir
        destacado = ctk.CTkFrame(self.result_area, fg_color=COLORS["success"], corner_radius=10)
        destacado.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(destacado, text="✅ Cantidad recomendada a preparar mañana:",
                     font=(FONT_FAMILY, FONT_SIZES["body"], "bold"),
                     text_color="white").pack(padx=15, pady=(12, 0), anchor="w")
        ctk.CTkLabel(destacado, text=f"{r['q_opt']} unidades",
                     font=(FONT_FAMILY, 30, "bold"),
                     text_color="white").pack(padx=15, pady=(0, 12), anchor="w")

        self._info("Esta cantidad ya incluye un pequeño margen de seguridad, pensado para que "
                   "no se quede sin stock si vende un poco más de lo esperado, sin sobre-producir "
                   "de más.", muted=True)

        # ── Simulación: cuánto se ahorraría ──
        if not r["sin_precio"]:
            self._seccion("💰 ¿Cuánto cambiaría si usa este método?")
            self._info("Comparamos, con los datos ya registrados, lo que hubiera pasado produciendo "
                       "'a ojo' (como se hace normalmente) contra producir siguiendo la recomendación "
                       "del sistema.")
            sim = r["sim"]
            for label, key in [("📋 Como se produce habitualmente", "base"), ("🤖 Con la recomendación del sistema", "modelo")]:
                s = sim[key]
                self._info(f"   {label}:")
                self._info(f"      Ganancia estimada: S/ {s['u']:.0f}   |   "
                           f"Unidades que se botaron: {s['sobra']:.0f}   |   "
                           f"Clientes que se quedaron sin el producto: {s['falta']:.0f}", muted=True)
            ahorro = sim["modelo"]["u"] - sim["base"]["u"]
            color = COLORS["success"] if ahorro >= 0 else COLORS["danger"]
            texto = f"📈 Con este método habría ganado S/ {ahorro:+.0f} más" if ahorro >= 0 \
                else f"📉 Con este método habría ganado S/ {abs(ahorro):.0f} menos"
            lbl = ctk.CTkLabel(self.result_area, text=texto,
                               font=(FONT_FAMILY, FONT_SIZES["subtitle"], "bold"),
                               text_color=color)
            lbl.pack(anchor="w", padx=15, pady=5)

        # ── Gráfico ──
        if HAS_MPL:
            self._graficar(r)

    def _graficar(self, r):
        self._seccion("📊 Así se vendió este producto en el tiempo")
        fig = Figure(figsize=(7, 2.5), dpi=100, facecolor=COLORS["bg_card"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(COLORS["bg_card"])
        ax.plot(r["dates"], r["y"], "o-", color=COLORS["info"], markersize=3, label="Lo que realmente vendió")
        if r["ganador"] in r["preds"]:
            p = r["preds"][r["ganador"]]
            mask = ~np.isnan(p)
            ax.plot(r["dates"][mask], p[mask], "--", color=COLORS["warning"], label="Lo que el método hubiera dicho")
        ax.set_title(f"{r['nombre']}", color=COLORS["text"], fontsize=10)
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

    def _info(self, texto, bold=False, muted=False):
        color = COLORS["text_muted"] if muted else COLORS["text"]
        weight = "bold" if bold else "normal"
        ctk.CTkLabel(self.result_area, text=texto,
                     font=(FONT_FAMILY, FONT_SIZES["body"], weight),
                     text_color=color, wraplength=850, justify="left").pack(anchor="w", padx=15, pady=1)
