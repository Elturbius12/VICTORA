"""Módulo 3 – Módulo Educativo con explicaciones sencillas."""
import customtkinter as ctk
import numpy as np
from core.educativo import MODELOS_EDUCATIVOS
from core.database import get_pivot_ventas, get_productos
from .tema import COLORS, FONT_FAMILY, FONT_SIZES


class EducativoFrame(ctk.CTkFrame):
    """Pantalla educativa: explica cada modelo con fórmulas y ejemplos."""

    def __init__(self, master, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="📚  Módulo Educativo",
                     font=(FONT_FAMILY, FONT_SIZES["title"], "bold"),
                     text_color=COLORS["primary"]).pack(anchor="w", padx=20, pady=(15, 5))
        ctk.CTkLabel(self, text="Aprenda cómo funciona cada modelo de pronóstico con explicaciones sencillas.",
                     font=(FONT_FAMILY, FONT_SIZES["body"]),
                     text_color=COLORS["text_muted"]).pack(anchor="w", padx=20, pady=(0, 10))

        # Selector de modelo
        sel_frame = ctk.CTkFrame(self, fg_color="transparent")
        sel_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(sel_frame, text="Modelo:").pack(side="left")
        nombres = list(MODELOS_EDUCATIVOS.keys())
        self.model_var = ctk.StringVar(value=nombres[0] if nombres else "")
        self.model_combo = ctk.CTkComboBox(sel_frame, variable=self.model_var,
                                            values=nombres, width=280, state="readonly",
                                            command=self._on_select)
        self.model_combo.pack(side="left", padx=5)

        ctk.CTkButton(sel_frame, text="Ver ejemplo con datos reales", width=200,
                       command=self._mostrar_ejemplo,
                       fg_color=COLORS["info"]).pack(side="right", padx=5)

        # Contenido
        self.content = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg_card"], corner_radius=10)
        self.content.pack(fill="both", expand=True, padx=20, pady=10)

        self._on_select(self.model_var.get())

    def _on_select(self, nombre):
        for w in self.content.winfo_children():
            w.destroy()
        info = MODELOS_EDUCATIVOS.get(nombre)
        if not info:
            return

        ctk.CTkLabel(self.content, text=info["nombre"],
                     font=(FONT_FAMILY, FONT_SIZES["subtitle"], "bold"),
                     text_color=COLORS["primary"]).pack(anchor="w", padx=15, pady=(15, 5))

        # Fórmula
        ctk.CTkLabel(self.content, text="Fórmula:",
                     font=(FONT_FAMILY, FONT_SIZES["body"], "bold")).pack(anchor="w", padx=15, pady=(10, 2))
        formula_frame = ctk.CTkFrame(self.content, fg_color=COLORS["bg_sidebar"], corner_radius=8)
        formula_frame.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(formula_frame, text=info["formula"],
                     font=("Consolas", FONT_SIZES["body"]),
                     text_color=COLORS["warning"], justify="left",
                     wraplength=600).pack(padx=15, pady=10)

        # Explicación
        ctk.CTkLabel(self.content, text="¿Cómo funciona? (explicación sencilla):",
                     font=(FONT_FAMILY, FONT_SIZES["body"], "bold")).pack(anchor="w", padx=15, pady=(10, 2))
        ctk.CTkLabel(self.content, text=info["explicacion"],
                     font=(FONT_FAMILY, FONT_SIZES["body"]),
                     text_color=COLORS["text"], wraplength=620,
                     justify="left").pack(anchor="w", padx=15, pady=5)

    def _mostrar_ejemplo(self):
        nombre = self.model_var.get()
        info = MODELOS_EDUCATIVOS.get(nombre)
        if not info or "ejemplo" not in info:
            return

        # Obtener datos reales del primer producto disponible
        pivot, _ = get_pivot_ventas()
        if pivot.empty:
            datos = np.array([5, 8, 3, 10, 7, 6, 9, 4, 8, 5], dtype=float)
            producto = "Ejemplo"
        else:
            producto = pivot.columns[0]
            datos = pivot[producto].values.astype(float)[-14:]  # últimos 14 días

        try:
            pasos = info["ejemplo"](datos, producto)
        except Exception as e:
            pasos = f"No se pudo generar el ejemplo: {e}"

        # Mostrar en una ventana emergente
        win = ctk.CTkToplevel(self)
        win.title(f"Ejemplo: {info['nombre']}")
        win.geometry("650x500")
        win.grab_set()

        ctk.CTkLabel(win, text=f"📝 Ejemplo paso a paso: {info['nombre']}",
                     font=(FONT_FAMILY, FONT_SIZES["subtitle"], "bold"),
                     text_color=COLORS["primary"]).pack(padx=15, pady=10)
        ctk.CTkLabel(win, text=f"Producto: {producto}  |  Datos: {list(datos[-7:].astype(int))}",
                     font=(FONT_FAMILY, FONT_SIZES["small"]),
                     text_color=COLORS["text_muted"]).pack(padx=15)

        text_box = ctk.CTkTextbox(win, font=("Consolas", 12), wrap="word",
                                   fg_color=COLORS["bg_card"])
        text_box.pack(fill="both", expand=True, padx=15, pady=10)
        text_box.insert("1.0", pasos)
        text_box.configure(state="disabled")
