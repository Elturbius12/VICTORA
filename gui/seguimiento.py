"""Módulo – Seguimiento: pronóstico vs. venta real, con error y observaciones."""
import customtkinter as ctk
from tkinter import filedialog, messagebox
import numpy as np
import pandas as pd

from core.database import get_seguimiento, registrar_venta, get_productos
from core.reportes import exportar_seguimiento_excel, backfill_historial_pronosticos
from .tema import COLORS, FONT_FAMILY, FONT_SIZES

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

#: Un error se considera "grande" (y se resalta) si es mayor a este % del
#: pronóstico, o si no hay pronóstico pero sí hubo venta inesperada grande.
UMBRAL_ERROR_GRANDE = 0.5


class SeguimientoFrame(ctk.CTkFrame):
    """Compara lo que el sistema pronosticó contra lo que realmente se vendió."""

    def __init__(self, master, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self.df = pd.DataFrame()
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="📈  Seguimiento: pronóstico vs. realidad",
                     font=(FONT_FAMILY, FONT_SIZES["title"], "bold"),
                     text_color=COLORS["primary"]).pack(anchor="w", padx=20, pady=(15, 2))
        ctk.CTkLabel(self, text="Cada vez que el sistema calcula un pronóstico, lo guarda. Cuando "
                                "ya registró la venta real de ese día, aquí puede comparar qué tan "
                                "bien acertó y anotar la razón de los errores grandes. Si quiere ver "
                                "esta comparación también para días pasados (no solo desde hoy), use "
                                "'📜 Generar historial completo': solo cuenta como evidencia desde el "
                                "día en que cada producto ya tenía suficiente historial para que el "
                                "sistema pronosticara de verdad, no desde el primer día de ventas.",
                     font=(FONT_FAMILY, FONT_SIZES["small"]),
                     text_color=COLORS["text_muted"]).pack(anchor="w", padx=20, pady=(0, 8))

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=5)
        ctk.CTkButton(top, text="🔄 Actualizar", command=self._cargar,
                       fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
                       width=150).pack(side="left")
        ctk.CTkButton(top, text="📄 Exportar a Excel", command=self._exportar,
                       fg_color=COLORS["success"], width=170).pack(side="left", padx=10)
        ctk.CTkButton(top, text="📜 Generar historial completo", command=self._generar_historial,
                       fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
                       width=210).pack(side="left", padx=10)

        self.resumen_label = ctk.CTkLabel(self, text="", font=(FONT_FAMILY, FONT_SIZES["small"]),
                                          text_color=COLORS["text_muted"], wraplength=950, justify="left")
        self.resumen_label.pack(anchor="w", padx=20)

        self.scroll = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg_card"], corner_radius=10)
        self.scroll.pack(fill="both", expand=True, padx=20, pady=10)

        self._cargar()

    def _cargar(self):
        self.df = get_seguimiento()
        self._mostrar()

    def _generar_historial(self):
        """Rellena hacia atrás los pronósticos que el sistema YA podía
        haber calculado en días pasados (desde que cada producto tuvo
        suficiente historial propio), para que esta pantalla sirva de
        evidencia real de qué tan bien acierta cada modelo — y no
        muestre solo el pronóstico de mañana."""
        try:
            n = backfill_historial_pronosticos()
        except Exception as e:
            messagebox.showerror("Error al generar el historial", str(e))
            return
        if n == 0:
            messagebox.showinfo("📜 Historial", "No había pronósticos nuevos para generar. Si un "
                                                "producto es muy nuevo, espere a que tenga más días "
                                                "de ventas registradas.")
        else:
            messagebox.showinfo("📜 Historial generado", f"Se generaron {n} pronóstico(s) de días "
                                                          f"pasados. Ya puede ver abajo cómo le habría "
                                                          f"ido al sistema en esas fechas.")
        self._cargar()

    def _mostrar(self):
        for w in self.scroll.winfo_children():
            w.destroy()

        if self.df.empty:
            ctk.CTkLabel(self.scroll, text="Todavía no hay pronósticos guardados. Use el 'Resumen del "
                                           "día' o 'Motor de Pronóstico' para calcular; el sistema "
                                           "va guardando cada pronóstico automáticamente.",
                         text_color=COLORS["text_muted"], wraplength=900).pack(padx=15, pady=20)
            self.resumen_label.configure(text="")
            return

        con_real = self.df[self.df["real"].notna()]
        if not con_real.empty:
            aciertos = (con_real["error_pct"].fillna(1) <= UMBRAL_ERROR_GRANDE).sum()
            self.resumen_label.configure(
                text=f"📊 De los últimos {len(con_real)} pronóstico(s) ya comparados con la venta real, "
                     f"{aciertos} ({aciertos/len(con_real):.0%}) tuvieron un error razonable "
                     f"(≤{UMBRAL_ERROR_GRANDE:.0%}).")
        else:
            self.resumen_label.configure(text="Hay pronósticos guardados, pero ninguno tiene todavía "
                                              "su venta real registrada para comparar.")

        if HAS_MPL and not con_real.empty and len(con_real) >= 3:
            self._graficar_error(con_real)

        hdr = ctk.CTkFrame(self.scroll, fg_color=COLORS["bg_sidebar"], corner_radius=5)
        hdr.pack(fill="x", padx=5, pady=(10, 2))
        for col, w in [("Fecha", 100), ("Producto", 190), ("Pronosticado", 110),
                       ("Venta real", 100), ("Error", 110), ("Modelo", 180), ("Observación", 220)]:
            ctk.CTkLabel(hdr, text=col, width=w,
                         font=(FONT_FAMILY, FONT_SIZES["small"], "bold")).pack(side="left", padx=2)

        for _, row in self.df.iterrows():
            error_grande = pd.notna(row["error_pct"]) and row["error_pct"] > UMBRAL_ERROR_GRANDE
            sin_real = pd.isna(row["real"])
            fg = "transparent" if sin_real else (COLORS["danger"] if error_grande else "transparent")
            fr = ctk.CTkFrame(self.scroll, fg_color=fg, corner_radius=3)
            fr.pack(fill="x", padx=5, pady=1)

            ctk.CTkLabel(fr, text=row["fecha"], width=100,
                         font=(FONT_FAMILY, FONT_SIZES["small"])).pack(side="left", padx=2)
            ctk.CTkLabel(fr, text=row["producto"], width=190,
                         font=(FONT_FAMILY, FONT_SIZES["small"])).pack(side="left", padx=2)
            pron_txt = f"{row['pronostico']:.1f}" if pd.notna(row["pronostico"]) else "—"
            ctk.CTkLabel(fr, text=pron_txt, width=110,
                         font=(FONT_FAMILY, FONT_SIZES["small"])).pack(side="left", padx=2)
            real_txt = f"{int(row['real'])}" if pd.notna(row["real"]) else "(sin registrar aún)"
            ctk.CTkLabel(fr, text=real_txt, width=100,
                         font=(FONT_FAMILY, FONT_SIZES["small"])).pack(side="left", padx=2)
            if sin_real:
                error_txt = "—"
            else:
                error_txt = f"{row['error']:+.1f}" + (f" ({row['error_pct']:.0%})" if pd.notna(row["error_pct"]) else "")
            ctk.CTkLabel(fr, text=error_txt, width=110,
                         font=(FONT_FAMILY, FONT_SIZES["small"], "bold" if error_grande else "normal"),
                         text_color="white" if error_grande else COLORS["text"]).pack(side="left", padx=2)
            ctk.CTkLabel(fr, text=row["modelo"] or "—", width=180,
                         font=(FONT_FAMILY, FONT_SIZES["small"]),
                         text_color="white" if error_grande else COLORS["text_muted"]).pack(side="left", padx=2)

            obs_var = ctk.StringVar(value=row["observacion"] or "")
            obs_entry = ctk.CTkEntry(fr, textvariable=obs_var, width=210,
                                     placeholder_text="¿Por qué falló? (llovió, feriado...)" if error_grande else "")
            obs_entry.pack(side="left", padx=2)
            fecha, producto = row["fecha"], row["producto"]
            obs_entry.bind("<FocusOut>", lambda e, f=fecha, p=producto, v=obs_var: self._guardar_obs(f, p, v.get()))
            obs_entry.bind("<Return>", lambda e, f=fecha, p=producto, v=obs_var: self._guardar_obs(f, p, v.get()))

    def _guardar_obs(self, fecha, producto_nombre, texto):
        prods = get_productos(solo_activos=False)
        fila = prods[prods["nombre"] == producto_nombre]
        if fila.empty:
            return
        pid = int(fila.iloc[0]["id"])
        fila_real = self.df[(self.df["fecha"] == fecha) & (self.df["producto"] == producto_nombre)]
        unidades = int(fila_real.iloc[0]["real"]) if not fila_real.empty and pd.notna(fila_real.iloc[0]["real"]) else 0
        registrar_venta(fecha, pid, unidades, observacion=texto)

    def _graficar_error(self, con_real):
        df = con_real.copy()
        df["fecha_dt"] = pd.to_datetime(df["fecha"])
        df["semana"] = df["fecha_dt"].dt.to_period("W").apply(lambda p: p.start_time)
        por_semana = df.groupby("semana")["error_abs"].mean()
        if len(por_semana) < 2:
            return
        fig = Figure(figsize=(7, 2.2), dpi=100, facecolor=COLORS["bg_card"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(COLORS["bg_card"])
        ax.plot(por_semana.index, por_semana.values, "o-", color=COLORS["warning"])
        ax.set_title("Error promedio por semana (unidades) — ¿va bajando?", color=COLORS["text"], fontsize=10)
        ax.tick_params(colors=COLORS["text_muted"], labelsize=8)
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.scroll)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="x", padx=5, pady=5)

    def _exportar(self):
        if self.df.empty:
            return
        # En algunas instalaciones de Windows, el cuadro "Guardar como" de
        # Windows falla con un error de Tcl/Tk que no tiene que ver con
        # nuestro programa. Si eso pasa, guardamos directo al Escritorio
        # sin preguntar dónde, en vez de dejar la exportación a medias.
        dialogo_fallo = False
        ruta = None
        try:
            ruta = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
                                                initialfile="seguimiento_victoriana.xlsx")
        except Exception:
            dialogo_fallo = True

        if dialogo_fallo:
            from pathlib import Path
            from datetime import datetime
            carpeta = Path.home() / "Desktop"
            if not carpeta.exists():
                carpeta = Path.home()
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            ruta = str(carpeta / f"seguimiento_victoriana_{ts}.xlsx")
        elif not ruta:
            return  # el usuario canceló el cuadro de diálogo normalmente

        try:
            exportar_seguimiento_excel(self.df, ruta)
            if dialogo_fallo:
                messagebox.showinfo("📄 Exportado", f"El cuadro de 'Guardar como' de Windows falló, así "
                                                     f"que se guardó directo en:\n{ruta}")
            else:
                messagebox.showinfo("📄 Exportado", f"Se guardó en:\n{ruta}")
        except Exception as e:
            messagebox.showerror("Error al exportar", str(e))
