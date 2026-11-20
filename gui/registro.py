"""Módulo 1 – Registro de Ventas."""
import customtkinter as ctk
from datetime import date, timedelta
import tkinter as tk
from tkinter import filedialog, messagebox
from core.database import (
    get_productos, agregar_producto, actualizar_producto,
    registrar_ventas_dia, marcar_dia_cerrado, get_ventas, importar_csv, importar_catalogo,
    contar_registros, insertar_productos_default, init_db, inferir_tipo,
    TIPOS_PRODUCTO, MARGEN_DEFECTO, get_pivot_ventas, get_seguimiento,
)
from .tema import COLORS, FONT_FAMILY, FONT_SIZES

ACCION_TXT = {"preparado": "preparar", "reventa": "comprar / reponer"}


class RegistroFrame(ctk.CTkFrame):
    """Pantalla de registro diario de ventas."""

    def __init__(self, master, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self.entries = {}
        self.price_entries = {}
        self._build()

    # ── UI ──────────────────────────────────────────────────────────────
    def _build(self):
        ctk.CTkLabel(self, text="📋  Registro de Ventas Diarias",
                     font=(FONT_FAMILY, FONT_SIZES["title"], "bold"),
                     text_color=COLORS["primary"]).pack(anchor="w", padx=20, pady=(15, 2))
        ctk.CTkLabel(self, text="Anote cuántas unidades vendió de cada producto hoy. "
                                "El precio lo puede editar directamente en la tabla.",
                     font=(FONT_FAMILY, FONT_SIZES["small"]),
                     text_color=COLORS["text_muted"]).pack(anchor="w", padx=20, pady=(0, 8))

        # Aviso de huecos de fechas / recordatorio de registrar hoy
        self.aviso_fechas = ctk.CTkLabel(self, text="", font=(FONT_FAMILY, FONT_SIZES["small"], "bold"),
                                         text_color=COLORS["warning"], wraplength=950, justify="left")
        self.aviso_fechas.pack(anchor="w", padx=20, pady=(0, 2))

        # Barra superior: fecha + botones
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(top, text="Fecha:", font=(FONT_FAMILY, FONT_SIZES["body"])).pack(side="left")
        self.fecha_var = ctk.StringVar(value=date.today().isoformat())
        self.fecha_entry = ctk.CTkEntry(top, textvariable=self.fecha_var, width=130)
        self.fecha_entry.pack(side="left", padx=5)
        self.fecha_entry.bind("<Return>", lambda e: self._cargar_productos())
        self.fecha_entry.bind("<FocusOut>", lambda e: self._cargar_productos())

        ctk.CTkButton(top, text="◀ Ayer", width=70, command=self._ayer,
                       fg_color=COLORS["bg_sidebar"]).pack(side="left", padx=2)
        ctk.CTkButton(top, text="Hoy ▶", width=70, command=self._hoy,
                       fg_color=COLORS["bg_sidebar"]).pack(side="left", padx=2)

        ctk.CTkButton(top, text="🚫 Local cerrado hoy", width=160, command=self._local_cerrado,
                       fg_color=COLORS["danger"]).pack(side="left", padx=(15, 5))

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

        # Retroalimentación rápida: lo que se pronosticó para este día
        self.feedback_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=8)
        self.feedback_label = ctk.CTkLabel(self.feedback_frame, text="",
                                           font=(FONT_FAMILY, FONT_SIZES["small"]),
                                           text_color=COLORS["text"], justify="left", wraplength=950)
        self.feedback_label.pack(anchor="w", padx=12, pady=8)

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
        self._actualizar_aviso_fechas()

    # ── Carga de datos ─────────────────────────────────────────────────
    def _actualizar_aviso_fechas(self):
        _, faltantes = get_pivot_ventas()
        partes = []
        if faltantes:
            ejemplos = ", ".join(faltantes[:5]) + ("..." if len(faltantes) > 5 else "")
            partes.append(f"⚠️ Hay {len(faltantes)} día(s) sin ningún registro entre su primera y última "
                           f"venta ({ejemplos}). Si de verdad no abrió esos días, use 'Local cerrado hoy' "
                           "en esa fecha; si se le olvidó registrar, anótelo ahora si recuerda algo.")
        stats = contar_registros()
        if stats["fecha_max"] and stats["fecha_max"] < date.today().isoformat():
            partes.append(f"📌 Su último registro fue el {stats['fecha_max']}. ¿Ya anotó las ventas de hoy?")
        self.aviso_fechas.configure(text="\n".join(partes))

    def _mostrar_feedback_pronostico(self, fecha):
        """Si para esta fecha ya existe un pronóstico guardado (se calculó
        cuando esa fecha era 'mañana'), lo muestra al lado de las ventas
        reales para que el usuario vea de un vistazo qué tan bien acertó
        el sistema, sin tener que ir a otra pantalla."""
        seg = get_seguimiento(desde=fecha, hasta=fecha)
        if seg.empty:
            self.feedback_frame.pack_forget()
            return
        lineas = [f"🔎 Esto fue lo que el sistema pronosticó para el {fecha} (compare con lo que anote abajo):"]
        for _, r in seg.sort_values("producto").iterrows():
            real_txt = f"{int(r['real'])}" if r["real"] == r["real"] else "aún sin registrar"
            lineas.append(f"   • {r['producto']}: pronosticó {r['pronostico']:.1f} — venta real: {real_txt}")
        self.feedback_label.configure(text="\n".join(lineas))
        self.feedback_frame.pack(fill="x", padx=20, pady=(0, 8), before=self.resumen_label)

    def _cargar_productos(self):
        for w in self.scroll.winfo_children():
            w.destroy()
        self.entries.clear()
        self.price_entries.clear()

        prods = get_productos()
        if prods.empty:
            insertar_productos_default()
            prods = get_productos()

        fecha = self.fecha_var.get().strip()
        ventas_existentes = {}
        try:
            vdf = get_ventas(desde=fecha, hasta=fecha)
            ventas_existentes = dict(zip(vdf["producto"], vdf["unidades"]))
        except Exception:
            pass

        # Cabecera
        hdr = ctk.CTkFrame(self.scroll, fg_color="transparent")
        hdr.pack(fill="x", pady=(5, 2))
        ctk.CTkLabel(hdr, text="Producto", width=220,
                     font=(FONT_FAMILY, FONT_SIZES["body"], "bold")).pack(side="left", padx=5)
        ctk.CTkLabel(hdr, text="Precio de venta (S/)", width=130,
                     font=(FONT_FAMILY, FONT_SIZES["body"], "bold")).pack(side="left")
        ctk.CTkLabel(hdr, text="Unidades vendidas", width=130,
                     font=(FONT_FAMILY, FONT_SIZES["body"], "bold")).pack(side="left")

        categoria_actual = None
        for _, row in prods.iterrows():
            if row["categoria"] and row["categoria"] != categoria_actual:
                categoria_actual = row["categoria"]
                ctk.CTkLabel(self.scroll, text=categoria_actual,
                             font=(FONT_FAMILY, FONT_SIZES["small"], "bold"),
                             text_color=COLORS["primary"]).pack(anchor="w", padx=5, pady=(8, 0))

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

            valor_previo = ventas_existentes.get(row["nombre"], 0)
            var = ctk.StringVar(value=str(int(valor_previo)))
            entry = ctk.CTkEntry(fr, textvariable=var, width=100, justify="center")
            entry.pack(side="left", padx=10)
            self.entries[pid] = var

        self._actualizar_aviso(prods)
        self._mostrar_feedback_pronostico(fecha)

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
        self._cargar_productos()

    def _hoy(self):
        self.fecha_var.set(date.today().isoformat())
        self._cargar_productos()

    def _local_cerrado(self):
        fecha = self.fecha_var.get().strip()
        try:
            date.fromisoformat(fecha)
        except ValueError:
            messagebox.showerror("Error", "Formato de fecha inválido. Use AAAA-MM-DD")
            return
        if not messagebox.askyesno("Confirmar", f"¿Confirma que el local estuvo CERRADO el {fecha}? "
                                                 "Se registrará 0 en todos los productos para ese día."):
            return
        n = marcar_dia_cerrado(fecha)
        messagebox.showinfo("✅ Registrado", f"Se registró el {fecha} como día cerrado ({n} productos en 0).")
        self._cargar_productos()
        self._actualizar_resumen()
        self._actualizar_aviso_fechas()

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

        for pid, pvar in self.price_entries.items():
            try:
                precio = float(pvar.get())
            except ValueError:
                precio = 0.0
            actualizar_producto(pid, precio=precio)

        messagebox.showinfo("✅ Guardado", f"Ventas y precios del {fecha} se guardaron correctamente.")
        self._cargar_productos()
        self._actualizar_resumen()
        self._actualizar_aviso_fechas()

    def _nuevo_producto(self):
        win = ctk.CTkToplevel(self)
        win.title("Nuevo producto")
        win.geometry("420x520")
        win.grab_set()

        ctk.CTkLabel(win, text="➕ Agregar nuevo producto",
                     font=(FONT_FAMILY, FONT_SIZES["subtitle"], "bold"),
                     text_color=COLORS["primary"]).pack(pady=(15, 10))

        ctk.CTkLabel(win, text="Nombre del producto").pack(anchor="w", padx=25)
        nombre_var = ctk.StringVar()
        ctk.CTkEntry(win, textvariable=nombre_var, width=350).pack(padx=25, pady=(0, 10))

        ctk.CTkLabel(win, text="Categoría (p.ej. 'Pizza Personal', 'Bebidas'; ayuda a estimar "
                               "productos nuevos usando productos parecidos)").pack(anchor="w", padx=25)
        cat_var = ctk.StringVar()
        cats_existentes = sorted(set(c for c in get_productos()["categoria"] if c))
        cat_combo = ctk.CTkComboBox(win, variable=cat_var, values=cats_existentes, width=350)
        cat_combo.pack(padx=25, pady=(0, 10))

        ctk.CTkLabel(win, text="Precio de venta (S/)").pack(anchor="w", padx=25)
        precio_var = ctk.StringVar(value="0")
        ctk.CTkEntry(win, textvariable=precio_var, width=350).pack(padx=25, pady=(0, 10))

        ctk.CTkLabel(win, text="Margen de ganancia sobre el precio (%). Ej: 27.5").pack(anchor="w", padx=25)
        margen_var = ctk.StringVar(value=f"{MARGEN_DEFECTO * 100:.1f}")
        ctk.CTkEntry(win, textvariable=margen_var, width=350).pack(padx=25, pady=(0, 10))

        ctk.CTkLabel(win, text="Tipo de producto").pack(anchor="w", padx=25)
        tipo_var = ctk.StringVar(value="preparado")
        tipo_frame = ctk.CTkFrame(win, fg_color="transparent")
        tipo_frame.pack(anchor="w", padx=25, pady=(0, 10))
        ctk.CTkRadioButton(tipo_frame, text="Se prepara/cocina (pizza, hamburguesa...)",
                            variable=tipo_var, value="preparado").pack(anchor="w")
        ctk.CTkRadioButton(tipo_frame, text="Se compra ya hecho (gaseosa embotellada...)",
                            variable=tipo_var, value="reventa").pack(anchor="w")

        ctk.CTkLabel(win, text="¿Cuántos días dura antes de malograrse? (1 = solo el día)").pack(
            anchor="w", padx=25)
        vida_var = ctk.StringVar(value="1")
        ctk.CTkEntry(win, textvariable=vida_var, width=350).pack(padx=25, pady=(0, 10))

        ctk.CTkLabel(win, text="Si sobra, ¿qué % se puede recuperar o reutilizar? (0 a 1)").pack(
            anchor="w", padx=25)
        recup_var = ctk.StringVar(value="0.5")
        ctk.CTkEntry(win, textvariable=recup_var, width=350).pack(padx=25, pady=(0, 15))

        def guardar():
            nombre = nombre_var.get().strip()
            if not nombre:
                messagebox.showwarning("Atención", "Escriba un nombre de producto.")
                return
            try:
                precio = float(precio_var.get())
                vida = int(vida_var.get())
                recup = float(recup_var.get())
                margen = float(margen_var.get()) / 100
            except ValueError:
                messagebox.showerror("Error", "Revise que precio, días, % y margen sean números válidos.")
                return
            agregar_producto(nombre, precio, vida, recup, tipo=tipo_var.get(),
                              margen=margen, categoria=cat_var.get().strip())
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
            actualizados, creados, ignorados = importar_catalogo(ruta)
            msg = (f"Se actualizaron {actualizados} producto(s) y se crearon {creados} nuevo(s).\n\n"
                   "Columnas reconocidas: producto, precio, tipo (preparado/reventa), margen, "
                   "categoria, vida_util_dias, recuperable.")
            if ignorados:
                msg += f"\n\n⚠️ Se ignoraron {ignorados} fila(s) porque parecían notas de texto, no productos."
            messagebox.showinfo("📦 Catálogo importado", msg)
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
            self._actualizar_aviso_fechas()
        except Exception as e:
            messagebox.showerror("Error de importación", str(e))

    def _actualizar_resumen(self):
        stats = contar_registros()
        txt = (f"📊 Tiene {stats['productos']} productos registrados y "
               f"{stats['registros']} registros de ventas en {stats['dias']} días distintos")
        if stats["fecha_min"]:
            txt += f"  (del {stats['fecha_min']} al {stats['fecha_max']})"
        self.resumen_label.configure(text=txt)
