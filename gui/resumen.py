"""Pantalla de inicio – Resumen del día: ¿qué debo preparar hoy?"""
import customtkinter as ctk
from tkinter import filedialog, messagebox
from datetime import date
import threading

from core.reportes import calcular_recomendaciones_todas, exportar_reporte_excel
from .tema import COLORS, FONT_FAMILY, FONT_SIZES


class ResumenFrame(ctk.CTkFrame):
    """Pantalla de inicio con las recomendaciones del día para todos los productos."""

    def __init__(self, master, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self.resultados = []
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="🏠  Resumen del día",
                     font=(FONT_FAMILY, FONT_SIZES["title"], "bold"),
                     text_color=COLORS["primary"]).pack(anchor="w", padx=20, pady=(15, 2))
        ctk.CTkLabel(self, text="Esto es lo que recomendamos preparar hoy, calculado para todos "
                                "sus productos a la vez.",
                     font=(FONT_FAMILY, FONT_SIZES["small"]),
                     text_color=COLORS["text_muted"]).pack(anchor="w", padx=20, pady=(0, 8))

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=5)
        ctk.CTkButton(top, text="🔄 Calcular / Actualizar", command=self._calcular,
                       fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
                       width=190).pack(side="left")
        self.export_btn = ctk.CTkButton(top, text="📄 Exportar reporte (Excel)", command=self._exportar,
                                        fg_color=COLORS["success"], width=200, state="disabled")
        self.export_btn.pack(side="left", padx=10)

        self.status_label = ctk.CTkLabel(self, text="Presione 'Calcular / Actualizar' para ver las "
                                                     "recomendaciones de hoy.",
                                          font=(FONT_FAMILY, FONT_SIZES["small"]),
                                          text_color=COLORS["text_muted"])
        self.status_label.pack(anchor="w", padx=20)

        self.result_area = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg_card"], corner_radius=10)
        self.result_area.pack(fill="both", expand=True, padx=20, pady=10)

    # ── Acciones ──────────────────────────────────────────────────────
    def _calcular(self):
        self.status_label.configure(text="⏳ Calculando recomendaciones para todos los productos... "
                                          "esto puede tardar un momento.")
        self.export_btn.configure(state="disabled")
        self.update_idletasks()
        threading.Thread(target=self._ejecutar, daemon=True).start()

    def _ejecutar(self):
        try:
            resultados = calcular_recomendaciones_todas()
            self.resultados = resultados
            self.after(0, self._mostrar)
        except Exception as e:
            self.after(0, lambda: self.status_label.configure(text=f"❌ Error: {e}"))

    def _mostrar(self):
        for w in self.result_area.winfo_children():
            w.destroy()

        if not self.resultados:
            self.status_label.configure(text="⚠️ Todavía no hay suficientes días de ventas "
                                              "registrados para calcular recomendaciones. "
                                              "Se necesitan al menos 5 días por producto.")
            return

        self.status_label.configure(text=f"✅ Recomendaciones listas ({len(self.resultados)} productos).")
        self.export_btn.configure(state="normal")

        # Frase resumen con el top 3
        top3 = self.resultados[:3]
        frase = "Hoy debería preparar principalmente: " + ", ".join(
            f"{r['cantidad']} de {r['nombre']}" for r in top3)
        ctk.CTkLabel(self.result_area, text="📢 " + frase,
                     font=(FONT_FAMILY, FONT_SIZES["subtitle"], "bold"),
                     text_color=COLORS["primary"], wraplength=900, justify="left").pack(
            anchor="w", padx=15, pady=(15, 10))

        # Tabla completa
        hdr = ctk.CTkFrame(self.result_area, fg_color=COLORS["bg_sidebar"], corner_radius=5)
        hdr.pack(fill="x", padx=5, pady=2)
        for col, w in [("Producto", 230), ("Cantidad a preparar", 160),
                       ("Método usado", 220), ("Ganancia estimada", 150)]:
            ctk.CTkLabel(hdr, text=col, width=w,
                         font=(FONT_FAMILY, FONT_SIZES["small"], "bold")).pack(side="left", padx=3)

        for r in self.resultados:
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

        sin_precio_count = sum(1 for r in self.resultados if r["sin_precio"])
        if sin_precio_count:
            ctk.CTkLabel(self.result_area,
                        text=f"⚠️ {sin_precio_count} producto(s) no tienen precio registrado. "
                             "Configúrelos en 'Registro de Ventas' para ver su ganancia estimada.",
                        font=(FONT_FAMILY, FONT_SIZES["small"]),
                        text_color=COLORS["warning"], wraplength=900, justify="left").pack(
                anchor="w", padx=15, pady=(10, 5))

    def _exportar(self):
        if not self.resultados:
            return
        ruta = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=f"reporte_victoriana_{date.today().isoformat()}.xlsx")
        if not ruta:
            return
        try:
            exportar_reporte_excel(self.resultados, ruta)
            messagebox.showinfo("📄 Reporte exportado",
                                f"El reporte se guardó en:\n{ruta}\n\n"
                                "Puede imprimirlo o enviarlo al encargado de cocina.")
        except Exception as e:
            messagebox.showerror("Error al exportar", str(e))
