"""Módulo 1 – Registro de Ventas."""
import customtkinter as ctk
from datetime import date, timedelta
import tkinter as tk
from tkinter import filedialog, messagebox
from core.database import (
    get_productos, agregar_producto, actualizar_producto,
    registrar_ventas_dia, get_ventas, importar_csv, importar_catalogo,
    contar_registros, insertar_productos_default, init_db
)
from .tema import COLORS, FONT_FAMILY, FONT_SIZES


class RegistroFrame(ctk.CTkFrame):
    """Pantalla de registro diario de ventas."""

    def __init__(self, master, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self.entries = {}
        self.price_entries = {}
        self._build()

    # ── UI ──────────────────────────────────────────────────────────────
    def _build(self):
        # Título
        ctk.CTkLabel(self, text="📋  Registro de Ventas Diarias",
                     font=(FONT_FAMILY, FONT_SIZES["title"], "bold"),
                     text_color=COLORS["primary"]).pack(anchor="w", padx=20, pady=(15, 2))
        ctk.CTkLabel(self, text="Anote cuántas unidades vendió de cada producto hoy. "
                                "El precio lo puede editar directamente en la tabla.",
                     font=(FONT_FAMILY, FONT_SIZES["small"]),
                     text_color=COLORS["text_muted"]).pack(anchor="w", padx=20, pady=(0, 8))

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

        ctk.CTkButton(top, text="💾 Guardar ventas y precios", width=190, command=self._guardar,
                       fg_color=COLORS["success"]).pack(side="right", padx=5)

        # Segunda fila de botones: catálogo / importar / nuevo producto
        top2 = ctk.CTkFrame(self, fg_color="transparent")
        top2.pack(fill="x", padx=20, pady=(0, 5))

        ctk.CTkButton(top2, text="➕ Nuevo producto", width=150, command=self._nuevo_producto,
                       fg_color=COLORS["bg_sidebar"]).pack(side="left", padx=(0, 8))
        ctk.CTkButton(top2, text="📦 Importar catálogo (productos y precios)", width=260,
                       command=self._importar_catalogo,
                       fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"]).pack(side="left", padx=8)
        ctk.CTkButton(top2, text="📂 Importar ventas (CSV)", width=180, command=self._importar_ventas,
                       fg_color=COLORS["info"]).pack(side="left", padx=8)

        # Resumen rápido
        self.resumen_label = ctk.CTkLabel(self, text="", font=(FONT_FAMILY, FONT_SIZES["small"]),
                                          text_color=COLORS["text_muted"])
        self.resumen_label.pack(anchor="w", padx=20)

        # Aviso de productos sin precio
        self.aviso_label = ctk.CTkLabel(self, text="", font=(FONT_FAMILY, FONT_SIZES["small"], "bold"),
                                        text_color=COLORS["warning"], wraplength=900, justify="left")
        self.aviso_label.pack(anchor="w", padx=20, pady=(2, 0))

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
        self.price_entries.clear()

        prods = get_productos()
        if prods.empty:
            insertar_productos_default()
            prods = get_productos()

        # Cabecera
        hdr = ctk.CTkFrame(self.scroll, fg_color="transparent")
        hdr.pack(fill="x", pady=(5, 2))
        ctk.CTkLabel(hdr, text="Producto", width=220,
                     font=(FONT_FAMILY, FONT_SIZES["body"], "bold")).pack(side="left", padx=5)
        ctk.CTkLabel(hdr, text="Precio de venta (S/)", width=130,
                     font=(FONT_FAMILY, FONT_SIZES["body"], "bold")).pack(side="left")
        ctk.CTkLabel(hdr, text="Unidades vendidas hoy", width=150,
                     font=(FONT_FAMILY, FONT_SIZES["body"], "bold")).pack(side="left")

        for _, row in prods.iterrows():
            pid = int(row["id"])
            sin_precio = row["precio"] <= 0
            fr = ctk.CTkFrame(self.scroll, fg_color="transparent", height=35)
            fr.pack(fill="x", pady=1)

            nombre_txt = row["nombre"] + ("  ⚠️" if sin_precio else "")
            lbl = ctk.CTkLabel(fr, text=nombre_txt, width=220,
                               font=(FONT_FAMILY, FONT_SIZES["body"]),
                               text_color=COLORS["warning"] if sin_precio else COLORS["text"])
            lbl.pack(side="left", padx=5)

            price_var = ctk.StringVar(value=f"{row['precio']:.2f}")
            price_entry = ctk.CTkEntry(fr, textvariable=price_var, width=100, justify="center",
                                       border_color=COLORS["warning"] if sin_precio else None)
            price_entry.pack(side="left", padx=15)
            self.price_entries[pid] = price_var

            var = ctk.StringVar(value="0")
            entry = ctk.CTkEntry(fr, textvariable=var, width=100, justify="center")
            entry.pack(side="left", padx=10)
            self.entries[pid] = var

        self._actualizar_aviso(prods)

    def _actualizar_aviso(self, prods):
        faltantes = prods[prods["precio"] <= 0]["nombre"].tolist()
        if faltantes:
            texto = ("⚠️ Estos productos no tienen precio y por eso el Motor de Pronóstico "
                     "no podrá calcular ganancias reales para ellos: " + ", ".join(faltantes) +
                     ".  Escriba el precio en la columna correspondiente y presione "
                     "'Guardar ventas y precios', o use 'Importar catálogo'.")
        else:
            texto = ""
        self.aviso_label.configure(text=texto)

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

        # Guardar ventas
        ventas = {}
        for pid, var in self.entries.items():
            try:
                u = int(var.get())
            except ValueError:
                u = 0
            ventas[pid] = u
        registrar_ventas_dia(fecha, ventas)

        # Guardar precios editados
        for pid, pvar in self.price_entries.items():
            try:
                precio = float(pvar.get())
            except ValueError:
                precio = 0.0
            actualizar_producto(pid, precio=precio)

        messagebox.showinfo("✅ Guardado", f"Ventas y precios del {fecha} se guardaron correctamente.")
        self._cargar_productos()
        self._actualizar_resumen()

    def _nuevo_producto(self):
        win = ctk.CTkToplevel(self)
        win.title("Nuevo producto")
        win.geometry("380x320")
        win.grab_set()

        ctk.CTkLabel(win, text="➕ Agregar nuevo producto",
                     font=(FONT_FAMILY, FONT_SIZES["subtitle"], "bold"),
                     text_color=COLORS["primary"]).pack(pady=(15, 10))

        ctk.CTkLabel(win, text="Nombre del producto").pack(anchor="w", padx=25)
        nombre_var = ctk.StringVar()
        ctk.CTkEntry(win, textvariable=nombre_var, width=300).pack(padx=25, pady=(0, 10))

        ctk.CTkLabel(win, text="Precio de venta (S/)").pack(anchor="w", padx=25)
        precio_var = ctk.StringVar(value="0")
        ctk.CTkEntry(win, textvariable=precio_var, width=300).pack(padx=25, pady=(0, 10))

        ctk.CTkLabel(win, text="¿Cuántos días dura antes de malograrse? (1 = solo el día)").pack(
            anchor="w", padx=25)
        vida_var = ctk.StringVar(value="1")
        ctk.CTkEntry(win, textvariable=vida_var, width=300).pack(padx=25, pady=(0, 10))

        ctk.CTkLabel(win, text="Si sobra, ¿qué % se puede recuperar o reutilizar? (0 a 1)").pack(
            anchor="w", padx=25)
        recup_var = ctk.StringVar(value="0.5")
        ctk.CTkEntry(win, textvariable=recup_var, width=300).pack(padx=25, pady=(0, 15))

        def guardar():
            nombre = nombre_var.get().strip()
            if not nombre:
                messagebox.showwarning("Atención", "Escriba un nombre de producto.")
                return
            try:
                precio = float(precio_var.get())
                vida = int(vida_var.get())
                recup = float(recup_var.get())
            except ValueError:
                messagebox.showerror("Error", "Revise que precio, días y % sean números válidos.")
                return
            agregar_producto(nombre, precio, vida, recup)
            win.destroy()
            self._cargar_productos()
            self._actualizar_resumen()

        ctk.CTkButton(win, text="Guardar producto", command=guardar,
                       fg_color=COLORS["success"]).pack(pady=5)

    def _importar_catalogo(self):
        ruta = filedialog.askopenfilename(
            filetypes=[("Excel o CSV", "*.xlsx *.xls *.csv"), ("Todos", "*.*")])
        if not ruta:
            return
        try:
            actualizados, creados = importar_catalogo(ruta)
            messagebox.showinfo(
                "📦 Catálogo importado",
                f"Se actualizaron {actualizados} producto(s) y se crearon {creados} nuevo(s).\n\n"
                "El archivo debe tener columnas: producto, precio "
                "(y opcionalmente vida_util_dias y recuperable).")
            self._cargar_productos()
            self._actualizar_resumen()
        except Exception as e:
            messagebox.showerror("Error al importar catálogo", str(e))

    def _importar_ventas(self):
        ruta = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not ruta:
            return
        try:
            n = importar_csv(ruta)
            messagebox.showinfo("Importación", f"Se importaron {n} registros de ventas.")
            self._cargar_productos()
            self._actualizar_resumen()
        except Exception as e:
            messagebox.showerror("Error de importación", str(e))

    def _actualizar_resumen(self):
        stats = contar_registros()
        txt = (f"📊 Tiene {stats['productos']} productos registrados y "
               f"{stats['registros']} registros de ventas en {stats['dias']} días distintos")
        if stats["fecha_min"]:
            txt += f"  (del {stats['fecha_min']} al {stats['fecha_max']})"
        self.resumen_label.configure(text=txt)
