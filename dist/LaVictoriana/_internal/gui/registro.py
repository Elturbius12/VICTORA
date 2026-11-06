"""Módulo 1 – Registro de Ventas."""
import customtkinter as ctk
from datetime import date, timedelta
import tkinter as tk
from tkinter import filedialog, messagebox
from ..core.database import (
    get_productos, agregar_producto, actualizar_producto,
    registrar_ventas_dia, get_ventas, importar_csv, contar_registros,
    insertar_productos_default, init_db
)
from .tema import COLORS, FONT_FAMILY, FONT_SIZES


class RegistroFrame(ctk.CTkFrame):
    """Pantalla de registro diario de ventas."""

    def __init__(self, master, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self.entries = {}
        self._build()

    # ── UI ──────────────────────────────────────────────────────────────
    def _build(self):
        # Título
        ctk.CTkLabel(self, text="📋  Registro de Ventas Diarias",
                     font=(FONT_FAMILY, FONT_SIZES["title"], "bold"),
                     text_color=COLORS["primary"]).pack(anchor="w", padx=20, pady=(15, 5))

        # Barra superior: fecha + botones
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(top, text="Fecha:", font=(FONT_FAMILY, FONT_SIZES["body"])).pack(side="left")
        self.fecha_var = ctk.StringVar(value=date.today().isoformat())
        self.fecha_entry = ctk.CTkEntry(top, textvariable=self.fecha_var, width=130)
        self.fecha_entry.pack(side="left", padx=5)

        ctk.CTkButton(top, text="◀ Ayer", width=70, command=self._ayer,
                       fg_color=COLORS["bg_sidebar"]).pack(side="left", padx=2)
        ctk.CTkButton(top, text="Hoy ▶", width=70, command=self._hoy,
                       fg_color=COLORS["bg_sidebar"]).pack(side="left", padx=2)

        ctk.CTkButton(top, text="💾 Guardar", width=100, command=self._guardar,
                       fg_color=COLORS["success"]).pack(side="right", padx=5)
        ctk.CTkButton(top, text="📂 Importar CSV", width=120, command=self._importar,
                       fg_color=COLORS["info"]).pack(side="right", padx=5)

        # Resumen rápido
        self.resumen_label = ctk.CTkLabel(self, text="", font=(FONT_FAMILY, FONT_SIZES["small"]),
                                          text_color=COLORS["text_muted"])
        self.resumen_label.pack(anchor="w", padx=20)

        # Tabla de productos (scrollable)
        self.scroll = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg_card"],
                                              corner_radius=10)
        self.scroll.pack(fill="both", expand=True, padx=20, pady=10)

        self._cargar_productos()
        self._actualizar_resumen()

    def _cargar_productos(self):
        for w in self.scroll.winfo_children():
            w.destroy()
        self.entries.clear()

        prods = get_productos()
        if prods.empty:
            insertar_productos_default()
            prods = get_productos()

        # Cabecera
        hdr = ctk.CTkFrame(self.scroll, fg_color="transparent")
        hdr.pack(fill="x", pady=(5, 2))
        ctk.CTkLabel(hdr, text="Producto", width=220,
                     font=(FONT_FAMILY, FONT_SIZES["body"], "bold")).pack(side="left", padx=5)
        ctk.CTkLabel(hdr, text="Precio (S/)", width=90,
                     font=(FONT_FAMILY, FONT_SIZES["body"], "bold")).pack(side="left")
        ctk.CTkLabel(hdr, text="Unidades vendidas", width=140,
                     font=(FONT_FAMILY, FONT_SIZES["body"], "bold")).pack(side="left")

        for _, row in prods.iterrows():
            fr = ctk.CTkFrame(self.scroll, fg_color="transparent", height=35)
            fr.pack(fill="x", pady=1)
            ctk.CTkLabel(fr, text=row["nombre"], width=220,
                         font=(FONT_FAMILY, FONT_SIZES["body"])).pack(side="left", padx=5)
            ctk.CTkLabel(fr, text=f"S/ {row['precio']:.1f}", width=90,
                         font=(FONT_FAMILY, FONT_SIZES["small"]),
                         text_color=COLORS["text_muted"]).pack(side="left")
            var = ctk.StringVar(value="0")
            entry = ctk.CTkEntry(fr, textvariable=var, width=100, justify="center")
            entry.pack(side="left", padx=10)
            self.entries[int(row["id"])] = var

    # ── Acciones ────────────────────────────────────────────────────────
    def _ayer(self):
        try:
            d = date.fromisoformat(self.fecha_var.get()) - timedelta(days=1)
        except ValueError:
            d = date.today() - timedelta(days=1)
        self.fecha_var.set(d.isoformat())

    def _hoy(self):
        self.fecha_var.set(date.today().isoformat())

    def _guardar(self):
        fecha = self.fecha_var.get().strip()
        try:
            date.fromisoformat(fecha)
        except ValueError:
            messagebox.showerror("Error", "Formato de fecha inválido. Use AAAA-MM-DD")
            return
        ventas = {}
        for pid, var in self.entries.items():
            try:
                u = int(var.get())
            except ValueError:
                u = 0
            ventas[pid] = u
        registrar_ventas_dia(fecha, ventas)
        messagebox.showinfo("✅ Guardado", f"Ventas del {fecha} registradas correctamente.")
        self._actualizar_resumen()

    def _importar(self):
        ruta = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not ruta:
            return
        try:
            n = importar_csv(ruta)
            messagebox.showinfo("Importación", f"Se importaron {n} registros.")
            self._cargar_productos()
            self._actualizar_resumen()
        except Exception as e:
            messagebox.showerror("Error de importación", str(e))

    def _actualizar_resumen(self):
        stats = contar_registros()
        txt = (f"Base de datos: {stats['productos']} productos · "
               f"{stats['registros']} registros · "
               f"{stats['dias']} días distintos")
        if stats["fecha_min"]:
            txt += f"  ({stats['fecha_min']} a {stats['fecha_max']})"
        self.resumen_label.configure(text=txt)
