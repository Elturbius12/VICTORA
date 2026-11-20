"""Módulo – Configuración: calendario de fechas especiales, respaldo y comanda."""
import customtkinter as ctk
from tkinter import filedialog, messagebox
from datetime import date

from core.database import (
    get_fechas_especiales, agregar_fecha_especial, eliminar_fecha_especial,
    respaldar_base, dias_desde_ultimo_respaldo,
)
from core.reportes import calcular_recomendaciones_todas, generar_comanda_pdf
from .tema import COLORS, FONT_FAMILY, FONT_SIZES

ORIGEN_TXT = {"feriado": "Feriado oficial", "comercial": "Fecha comercial", "manual": "Agregada por usted"}


class ConfiguracionFrame(ctk.CTkFrame):
    """Calendario de fechas especiales, copias de seguridad y comanda para imprimir."""

    def __init__(self, master, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="⚙️  Configuración",
                     font=(FONT_FAMILY, FONT_SIZES["title"], "bold"),
                     text_color=COLORS["primary"]).pack(anchor="w", padx=20, pady=(15, 10))

        # ── Respaldo ──
        box1 = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=10)
        box1.pack(fill="x", padx=20, pady=8)
        ctk.CTkLabel(box1, text="💾 Copia de seguridad", font=(FONT_FAMILY, FONT_SIZES["subtitle"], "bold"),
                     text_color=COLORS["primary"]).pack(anchor="w", padx=15, pady=(12, 2))
        self.backup_label = ctk.CTkLabel(box1, text="", font=(FONT_FAMILY, FONT_SIZES["small"]),
                                         text_color=COLORS["text_muted"])
        self.backup_label.pack(anchor="w", padx=15)
        ctk.CTkButton(box1, text="Hacer copia de seguridad ahora", command=self._respaldar,
                       fg_color=COLORS["success"], width=240).pack(anchor="w", padx=15, pady=(8, 12))
        self._actualizar_backup_label()

        # ── Comanda para imprimir ──
        box2 = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=10)
        box2.pack(fill="x", padx=20, pady=8)
        ctk.CTkLabel(box2, text="🧾 Comanda para la cocina", font=(FONT_FAMILY, FONT_SIZES["subtitle"], "bold"),
                     text_color=COLORS["primary"]).pack(anchor="w", padx=15, pady=(12, 2))
        ctk.CTkLabel(box2, text="Genera una hoja simple en PDF, lista para imprimir y pegar en la "
                                "cocina, con lo que toca preparar y comprar hoy.",
                     font=(FONT_FAMILY, FONT_SIZES["small"]), text_color=COLORS["text_muted"],
                     wraplength=850, justify="left").pack(anchor="w", padx=15)
        ctk.CTkButton(box2, text="Generar comanda (PDF)", command=self._generar_comanda,
                       fg_color=COLORS["info"], width=220).pack(anchor="w", padx=15, pady=(8, 12))

        # ── Calendario de fechas especiales ──
        box3 = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=10)
        box3.pack(fill="both", expand=True, padx=20, pady=8)
        ctk.CTkLabel(box3, text="📅 Calendario de feriados y fechas especiales",
                     font=(FONT_FAMILY, FONT_SIZES["subtitle"], "bold"),
                     text_color=COLORS["primary"]).pack(anchor="w", padx=15, pady=(12, 2))
        ctk.CTkLabel(box3, text="Ya incluye los feriados oficiales del Perú 2026 y fechas comerciales "
                                "típicas de comida. Estos días no se mezclan con el promedio normal "
                                "del día de la semana, y se le avisa cuando se acerca uno. Puede "
                                "agregar sus propias fechas (aniversario del local, eventos, etc.).",
                     font=(FONT_FAMILY, FONT_SIZES["small"]), text_color=COLORS["text_muted"],
                     wraplength=850, justify="left").pack(anchor="w", padx=15, pady=(0, 8))

        add_frame = ctk.CTkFrame(box3, fg_color="transparent")
        add_frame.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(add_frame, text="Fecha (AAAA-MM-DD):").pack(side="left")
        self.fecha_var = ctk.StringVar()
        ctk.CTkEntry(add_frame, textvariable=self.fecha_var, width=120).pack(side="left", padx=5)
        ctk.CTkLabel(add_frame, text="Nombre:").pack(side="left", padx=(10, 0))
        self.nombre_var = ctk.StringVar()
        ctk.CTkEntry(add_frame, textvariable=self.nombre_var, width=220).pack(side="left", padx=5)
        ctk.CTkButton(add_frame, text="➕ Agregar", command=self._agregar_fecha,
                       fg_color=COLORS["primary"], width=100).pack(side="left", padx=10)

        self.lista_scroll = ctk.CTkScrollableFrame(box3, fg_color=COLORS["bg_sidebar"], corner_radius=8)
        self.lista_scroll.pack(fill="both", expand=True, padx=15, pady=(5, 15))

        self._cargar_fechas()

    def _actualizar_backup_label(self):
        d = dias_desde_ultimo_respaldo()
        if d is None:
            self.backup_label.configure(text="⚠️ Todavía no ha hecho ninguna copia de seguridad.")
        elif d == 0:
            self.backup_label.configure(text="✅ Último respaldo: hoy.")
        else:
            color = COLORS["warning"] if d > 14 else COLORS["text_muted"]
            self.backup_label.configure(text=f"Último respaldo: hace {d} día(s).", text_color=color)

    def _respaldar(self):
        carpeta = filedialog.askdirectory(title="Elegir carpeta para la copia de seguridad")
        if not carpeta:
            return
        try:
            destino = respaldar_base(carpeta)
            messagebox.showinfo("💾 Copia de seguridad creada", f"Se guardó en:\n{destino}")
            self._actualizar_backup_label()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _generar_comanda(self):
        ruta = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
                                            initialfile=f"comanda_{date.today().isoformat()}.pdf")
        if not ruta:
            return
        try:
            resultados, _ = calcular_recomendaciones_todas(guardar_historial=False)
            generar_comanda_pdf(resultados, ruta)
            messagebox.showinfo("🧾 Comanda generada", f"Se guardó en:\n{ruta}")
        except Exception as e:
            messagebox.showerror("Error al generar la comanda", str(e))

    def _cargar_fechas(self):
        for w in self.lista_scroll.winfo_children():
            w.destroy()
        df = get_fechas_especiales()
        hoy = date.today().isoformat()
        for _, row in df.iterrows():
            fr = ctk.CTkFrame(self.lista_scroll, fg_color="transparent")
            fr.pack(fill="x", pady=1)
            pasada = row["fecha"] < hoy
            color = COLORS["text_muted"] if pasada else COLORS["text"]
            ctk.CTkLabel(fr, text=row["fecha"], width=100, text_color=color,
                         font=(FONT_FAMILY, FONT_SIZES["small"])).pack(side="left", padx=5)
            ctk.CTkLabel(fr, text=row["nombre"], width=220, text_color=color,
                         font=(FONT_FAMILY, FONT_SIZES["small"])).pack(side="left", padx=5)
            ctk.CTkLabel(fr, text=ORIGEN_TXT.get(row["origen"], row["origen"]), width=160,
                         text_color=COLORS["text_muted"],
                         font=(FONT_FAMILY, FONT_SIZES["small"])).pack(side="left", padx=5)
            ctk.CTkButton(fr, text="🗑", width=36, fg_color=COLORS["danger"],
                           command=lambda f=row["fecha"]: self._eliminar_fecha(f)).pack(side="left", padx=5)

    def _agregar_fecha(self):
        fecha = self.fecha_var.get().strip()
        nombre = self.nombre_var.get().strip()
        try:
            date.fromisoformat(fecha)
        except ValueError:
            messagebox.showerror("Error", "Formato de fecha inválido. Use AAAA-MM-DD")
            return
        if not nombre:
            messagebox.showwarning("Atención", "Escriba un nombre para la fecha.")
            return
        agregar_fecha_especial(fecha, nombre, origen="manual")
        self.fecha_var.set("")
        self.nombre_var.set("")
        self._cargar_fechas()

    def _eliminar_fecha(self, fecha):
        eliminar_fecha_especial(fecha)
        self._cargar_fechas()
