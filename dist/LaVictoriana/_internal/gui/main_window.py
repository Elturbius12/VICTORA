"""Ventana principal con barra lateral de navegación."""
import customtkinter as ctk
from .tema import COLORS, FONT_FAMILY, FONT_SIZES
from .registro import RegistroFrame
from .pronostico import PronosticoFrame
from .educativo_gui import EducativoFrame
from .dashboard import DashboardFrame


class MainWindow(ctk.CTk):
    """Ventana principal de La Victoriana."""

    def __init__(self):
        super().__init__()
        self.title("La Victoriana – Sistema de Pronóstico de Demanda")
        self.geometry("1100x700")
        self.minsize(900, 600)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.frames = {}
        self.current = None
        self._build()
        self._show("registro")

    def _build(self):
        # Sidebar
        sidebar = ctk.CTkFrame(self, width=220, fg_color=COLORS["bg_sidebar"], corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Logo / título
        ctk.CTkLabel(sidebar, text="🍗 La Victoriana",
                     font=(FONT_FAMILY, 18, "bold"),
                     text_color=COLORS["primary"]).pack(pady=(25, 5))
        ctk.CTkLabel(sidebar, text="Pronóstico de Demanda",
                     font=(FONT_FAMILY, 11),
                     text_color=COLORS["text_muted"]).pack(pady=(0, 25))

        # Botones de navegación
        self.nav_buttons = {}
        nav_items = [
            ("registro", "📋 Registro de Ventas"),
            ("pronostico", "🔮 Motor de Pronóstico"),
            ("educativo", "📚 Módulo Educativo"),
            ("dashboard", "📊 Dashboard"),
        ]
        for key, label in nav_items:
            btn = ctk.CTkButton(
                sidebar, text=label, anchor="w",
                font=(FONT_FAMILY, FONT_SIZES["body"]),
                fg_color="transparent", text_color=COLORS["text"],
                hover_color=COLORS["primary_hover"],
                height=40, corner_radius=8,
                command=lambda k=key: self._show(k)
            )
            btn.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[key] = btn

        # Separador + info
        ctk.CTkFrame(sidebar, height=1, fg_color=COLORS["text_muted"]).pack(fill="x", padx=20, pady=20)
        ctk.CTkLabel(sidebar, text="Juliaca, Perú",
                     font=(FONT_FAMILY, 10), text_color=COLORS["text_muted"]).pack()
        ctk.CTkLabel(sidebar, text="v1.0",
                     font=(FONT_FAMILY, 10), text_color=COLORS["text_muted"]).pack(pady=(2, 0))

        # Área principal
        self.main_area = ctk.CTkFrame(self, fg_color=COLORS["bg_dark"], corner_radius=0)
        self.main_area.pack(side="left", fill="both", expand=True)

        # Crear frames
        self.frames["registro"] = RegistroFrame(self.main_area)
        self.frames["pronostico"] = PronosticoFrame(self.main_area)
        self.frames["educativo"] = EducativoFrame(self.main_area)
        self.frames["dashboard"] = DashboardFrame(self.main_area)

    def _show(self, key):
        if self.current:
            self.frames[self.current].pack_forget()
            self.nav_buttons[self.current].configure(fg_color="transparent")
        self.frames[key].pack(fill="both", expand=True)
        self.nav_buttons[key].configure(fg_color=COLORS["primary"])
        self.current = key
