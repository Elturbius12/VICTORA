"""Pantalla de inicio – Resumen del día."""
import customtkinter as ctk
from tkinter import filedialog, messagebox
from datetime import date
import threading

from core.reportes import (
    calcular_recomendaciones_todas, exportar_reporte_excel,
    productos_que_casi_no_se_mueven, mejor_peor_dia_semana,
)
from core.database import proxima_fecha_especial, respaldar_base, dias_desde_ultimo_respaldo
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

        self.contexto_label = ctk.CTkLabel(self, text="", font=(FONT_FAMILY, FONT_SIZES["small"]),
                                           text_color=COLORS["text_muted"], wraplength=950, justify="left")
        self.contexto_label.pack(anchor="w", padx=20, pady=(0, 8))

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=5)
        ctk.CTkButton(top, text="🔄 Calcular / Actualizar", command=self._calcular,
                       fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
                       width=190).pack(side="left")
        self.export_btn = ctk.CTkButton(top, text="📄 Exportar reporte (Excel)", command=self._exportar,
                                        fg_color=COLORS["success"], width=200, state="disabled")
        self.export_btn.pack(side="left", padx=10)
        ctk.CTkButton(top, text="💾 Hacer copia de seguridad", command=self._respaldar,
                       fg_color=COLORS["bg_sidebar"], width=200).pack(side="left", padx=10)

        self.status_label = ctk.CTkLabel(self, text="Presione 'Calcular / Actualizar' para ver las "
                                                     "recomendaciones de hoy.",
                                          font=(FONT_FAMILY, FONT_SIZES["small"]),
                                          text_color=COLORS["text_muted"])
        self.status_label.pack(anchor="w", padx=20)

        self.aviso_label = ctk.CTkLabel(self, text="", font=(FONT_FAMILY, FONT_SIZES["small"], "bold"),
                                        text_color=COLORS["warning"], wraplength=950, justify="left")
        self.aviso_label.pack(anchor="w", padx=20, pady=(4, 0))

        self.result_area = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg_card"], corner_radius=10)
        self.result_area.pack(fill="both", expand=True, padx=20, pady=10)

        self._mostrar_contexto()

    # ── Contexto inicial (sin calcular todo) ─────────────────────────
    def _mostrar_contexto(self):
        partes = []
        prox = proxima_fecha_especial()
        if prox:
            from datetime import date as _date
            dias = (_date.fromisoformat(prox["fecha"]) - _date.today()).days
            if 0 <= dias <= 7:
                partes.append(f"📅 En {dias} día(s) es {prox['nombre']} ({prox['fecha']}) — "
                               "si otros años ese día vendió distinto a lo normal, considere ajustar "
                               "lo que sugiere el sistema ese día.")
        dias_resp = dias_desde_ultimo_respaldo()
        if dias_resp is None:
            partes.append("💾 Todavía no ha hecho ninguna copia de seguridad de su base de datos. "
                           "Se recomienda hacerlo de vez en cuando para no perder su historial.")
        elif dias_resp > 14:
            partes.append(f"💾 Su última copia de seguridad fue hace {dias_resp} días. Considere hacer una nueva.")
        self.contexto_label.configure(text="\n".join(partes))

    # ── Acciones ──────────────────────────────────────────────────────
    def _calcular(self):
        self.status_label.configure(text="⏳ Calculando recomendaciones para todos los productos... "
                                          "esto puede tardar un momento.")
        self.export_btn.configure(state="disabled")
        self.update_idletasks()
        threading.Thread(target=self._ejecutar, daemon=True).start()

    def _ejecutar(self):
        try:
            resultados, faltantes = calcular_recomendaciones_todas()
            self.resultados = resultados
            self.faltantes = faltantes
            self.after(0, self._mostrar)
        except Exception as e:
            msg = str(e)
            self.after(0, lambda: self.status_label.configure(text=f"❌ Error: {msg}"))

    def _respaldar(self):
        carpeta = filedialog.askdirectory(title="Elegir carpeta para la copia de seguridad")
        if not carpeta:
            return
        try:
            destino = respaldar_base(carpeta)
            messagebox.showinfo("💾 Copia de seguridad creada", f"Se guardó en:\n{destino}")
            self._mostrar_contexto()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _mostrar(self):
        for w in self.result_area.winfo_children():
            w.destroy()

        calculables = [r for r in self.resultados if r["pronostico"] is not None]

        if not self.resultados:
            self.status_label.configure(text="⚠️ Todavía no hay productos cargados. Vaya a "
                                              "'Registro de Ventas' para importar su catálogo.")
            return

        self.status_label.configure(text=f"✅ Recomendaciones listas ({len(calculables)} de "
                                          f"{len(self.resultados)} productos con datos suficientes).")
        self.export_btn.configure(state="normal")

        avisos = []
        if getattr(self, "faltantes", None):
            ej = ", ".join(self.faltantes[:5]) + ("..." if len(self.faltantes) > 5 else "")
            avisos.append(f"⚠️ Hay {len(self.faltantes)} día(s) sin ningún registro en su historial ({ej}). "
                           "Eso puede hacer menos preciso el cálculo — revíselo en 'Registro de Ventas'.")
        self.aviso_label.configure(text="\n".join(avisos))

        if not calculables:
            ctk.CTkLabel(self.result_area, text="⚠️ Todavía no hay suficientes días de ventas "
                                                "registrados para ningún producto (ni productos parecidos "
                                                "para estimar). Se necesitan al menos 5 días.",
                         text_color=COLORS["warning"], wraplength=900, justify="left").pack(padx=15, pady=15)
            return

        # Frase resumen con el top 3 (separando preparar / comprar)
        top3 = sorted(calculables, key=lambda r: r["total_vendido"], reverse=True)[:3]
        preparar = [r for r in top3 if r["accion"] == "preparar"]
        comprar = [r for r in top3 if r["accion"] != "preparar"]
        frase_partes = []
        if preparar:
            frase_partes.append("preparar " + ", ".join(f"{r['cantidad_sugerida']} de {r['nombre']}" for r in preparar))
        if comprar:
            frase_partes.append("comprar/reponer " + ", ".join(f"{r['cantidad_sugerida']} de {r['nombre']}" for r in comprar))
        frase = "Hoy debería " + " y ".join(frase_partes) if frase_partes else ""
        if frase:
            ctk.CTkLabel(self.result_area, text="📢 " + frase,
                         font=(FONT_FAMILY, FONT_SIZES["subtitle"], "bold"),
                         text_color=COLORS["primary"], wraplength=900, justify="left").pack(
                anchor="w", padx=15, pady=(15, 10))

        mp = mejor_peor_dia_semana()
        if mp:
            ctk.CTkLabel(self.result_area,
                         text=f"📊 En promedio, su mejor día es el {mp['mejor_dia']} "
                              f"({mp['mejor_valor']} unid.) y su día más flojo es el {mp['peor_dia']} "
                              f"({mp['peor_valor']} unid.).",
                         font=(FONT_FAMILY, FONT_SIZES["small"]), text_color=COLORS["text_muted"],
                         wraplength=900, justify="left").pack(anchor="w", padx=15, pady=(0, 10))

        # Tabla completa, agrupada por categoría
        hdr = ctk.CTkFrame(self.result_area, fg_color=COLORS["bg_sidebar"], corner_radius=5)
        hdr.pack(fill="x", padx=5, pady=2)
        for col, w in [("", 30), ("Producto", 210), ("Pronóstico venta", 130),
                       ("Cantidad sugerida", 140), ("Acción", 140), ("Ganancia estimada", 130)]:
            ctk.CTkLabel(hdr, text=col, width=w,
                         font=(FONT_FAMILY, FONT_SIZES["small"], "bold")).pack(side="left", padx=3)

        categoria_actual = object()
        ordenados = sorted(self.resultados, key=lambda r: (r.get("categoria") or "~", -r["total_vendido"]))
        for r in ordenados:
            if r.get("categoria") != categoria_actual:
                categoria_actual = r.get("categoria")
                ctk.CTkLabel(self.result_area, text=categoria_actual or "Sin categoría",
                             font=(FONT_FAMILY, FONT_SIZES["small"], "bold"),
                             text_color=COLORS["primary"]).pack(anchor="w", padx=8, pady=(10, 2))

            fr = ctk.CTkFrame(self.result_area, fg_color="transparent")
            fr.pack(fill="x", padx=5, pady=1)

            ctk.CTkLabel(fr, text=r.get("confianza_icono", ""), width=30).pack(side="left", padx=3)

            nombre_txt = r["nombre"] + ("  ⚠️" if r["sin_precio"] else "")
            ctk.CTkLabel(fr, text=nombre_txt, width=210,
                         font=(FONT_FAMILY, FONT_SIZES["small"]),
                         text_color=COLORS["warning"] if r["sin_precio"] else COLORS["text"]
                         ).pack(side="left", padx=3)

            pron_txt = f"{r['pronostico']:.1f} unid." if r["pronostico"] is not None else "—"
            ctk.CTkLabel(fr, text=pron_txt, width=130,
                         font=(FONT_FAMILY, FONT_SIZES["small"]),
                         text_color=COLORS["text_muted"]).pack(side="left", padx=3)

            cant_txt = f"{r['cantidad_sugerida']} unid." if r["cantidad_sugerida"] is not None else "—"
            ctk.CTkLabel(fr, text=cant_txt, width=140,
                         font=(FONT_FAMILY, FONT_SIZES["small"], "bold"),
                         text_color=COLORS["success"]).pack(side="left", padx=3)

            accion_txt = (r["accion"] or "—").capitalize()
            ctk.CTkLabel(fr, text=accion_txt, width=140,
                         font=(FONT_FAMILY, FONT_SIZES["small"]),
                         text_color=COLORS["text_muted"]).pack(side="left", padx=3)

            ganancia_txt = f"S/ {r['ganancia_estimada']:.0f}" if r.get("ganancia_estimada") is not None else "Sin precio"
            ctk.CTkLabel(fr, text=ganancia_txt, width=130,
                         font=(FONT_FAMILY, FONT_SIZES["small"])).pack(side="left", padx=3)

        sin_precio_count = sum(1 for r in self.resultados if r["sin_precio"])
        if sin_precio_count:
            ctk.CTkLabel(self.result_area,
                        text=f"⚠️ {sin_precio_count} producto(s) no tienen precio registrado. "
                             "Configúrelos en 'Registro de Ventas' para ver su ganancia estimada.",
                        font=(FONT_FAMILY, FONT_SIZES["small"]),
                        text_color=COLORS["warning"], wraplength=900, justify="left").pack(
                anchor="w", padx=15, pady=(10, 5))

        casi_no_se_mueven = productos_que_casi_no_se_mueven()
        if casi_no_se_mueven:
            nombres = ", ".join(p["nombre"] for p in casi_no_se_mueven[:8])
            ctk.CTkLabel(self.result_area,
                        text=f"🐌 Estos productos casi no se mueven (candidatos a revisar precio o "
                             f"sacarlos del menú): {nombres}.",
                        font=(FONT_FAMILY, FONT_SIZES["small"]),
                        text_color=COLORS["text_muted"], wraplength=900, justify="left").pack(
                anchor="w", padx=15, pady=(5, 10))

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
