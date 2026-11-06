"""Ventana principal con barra lateral de navegación."""
import customtkinter as ctk
from core.database import contar_registros
from .tema import COLORS, FONT_FAMILY, FONT_SIZES
from .resumen import ResumenFrame
from .registro import RegistroFrame
from .pronostico import PronosticoFrame
from .educativo_gui import EducativoFrame
from .dashboard import DashboardFrame

AYUDA_TEXTO = """🏠 Resumen del día
Al abrir la app, aquí verá de un vistazo qué preparar hoy para todos sus
productos, sin tener que revisarlos uno por uno. También puede exportar
un reporte en Excel para el encargado de cocina.

📋 Registro de Ventas
Aquí anota cada día cuánto vendió de cada producto y a qué precio lo vende.
Mientras más días registre, mejores serán los cálculos.

🔮 Motor de Pronóstico
Elija un producto y el sistema le dirá cuánto preparar mañana, probando
varias formas de calcularlo y quedándose con la que mejor funciona para
ese producto en su negocio.

📚 Módulo Educativo
Explica, en palabras simples y con ejemplos de su propio negocio, cómo
funciona cada método de cálculo que usa el sistema.

📊 Dashboard
Muestra un vistazo general: qué se vende más, en qué días, y cómo está
clasificado cada producto (si se vende parejo o de forma irregular).

💡 Consejo: registre sus ventas todos los días. El sistema se vuelve más
preciso mientras más información tenga de su negocio.
"""


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
        self._show("resumen")

    def _build(self):
        # Sidebar
        sidebar = ctk.CTkFrame(self, width=240, fg_color=COLORS["bg_sidebar"], corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Logo / título
        ctk.CTkLabel(sidebar, text="🍗 La Victoriana",
                     font=(FONT_FAMILY, 19, "bold"),
                     text_color=COLORS["primary"]).pack(pady=(25, 2))
        ctk.CTkLabel(sidebar, text="Pronóstico de Demanda",
                     font=(FONT_FAMILY, 11),
                     text_color=COLORS["text_muted"]).pack(pady=(0, 2))
        ctk.CTkLabel(sidebar, text="\"Vende lo justo, no más, no menos\"",
                     font=(FONT_FAMILY, 10, "italic"),
                     text_color=COLORS["primary"]).pack(pady=(0, 15))

        # Botones de navegación
        self.nav_buttons = {}
        nav_items = [
            ("resumen", "🏠 Resumen del día"),
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

        # Separador
        ctk.CTkFrame(sidebar, height=1, fg_color=COLORS["text_muted"]).pack(fill="x", padx=20, pady=15)

        # Caja de estadísticas rápidas
        self.stats_card = ctk.CTkFrame(sidebar, fg_color=COLORS["bg_card"], corner_radius=10)
        self.stats_card.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(self.stats_card, text="📦  Su negocio en números",
                     font=(FONT_FAMILY, FONT_SIZES["small"], "bold"),
                     text_color=COLORS["primary"]).pack(anchor="w", padx=12, pady=(10, 4))
        self.stats_productos = ctk.CTkLabel(self.stats_card, text="", font=(FONT_FAMILY, FONT_SIZES["small"]),
                                            text_color=COLORS["text"])
        self.stats_productos.pack(anchor="w", padx=12)
        self.stats_dias = ctk.CTkLabel(self.stats_card, text="", font=(FONT_FAMILY, FONT_SIZES["small"]),
                                       text_color=COLORS["text"])
        self.stats_dias.pack(anchor="w", padx=12, pady=(0, 10))

        # Botón de ayuda
        ctk.CTkButton(sidebar, text="❓ ¿Cómo funciona esto?", anchor="w",
                       font=(FONT_FAMILY, FONT_SIZES["small"]),
                       fg_color="transparent", text_color=COLORS["text_muted"],
                       hover_color=COLORS["bg_card"], border_width=1,
                       border_color=COLORS["text_muted"],
                       height=36, corner_radius=8,
                       command=self._mostrar_ayuda).pack(fill="x", padx=15, pady=(10, 5))

        # Footer
        ctk.CTkFrame(sidebar, height=1, fg_color=COLORS["text_muted"]).pack(fill="x", padx=20, pady=(15, 10))
        ctk.CTkLabel(sidebar, text="📍 Juliaca, Perú",
                     font=(FONT_FAMILY, 10), text_color=COLORS["text_muted"]).pack()
        ctk.CTkLabel(sidebar, text="v1.0",
                     font=(FONT_FAMILY, 10), text_color=COLORS["text_muted"]).pack(pady=(2, 10))

        # Área principal
        self.main_area = ctk.CTkFrame(self, fg_color=COLORS["bg_dark"], corner_radius=0)
        self.main_area.pack(side="left", fill="both", expand=True)

        # Crear frames
        self.frames["resumen"] = ResumenFrame(self.main_area)
        self.frames["registro"] = RegistroFrame(self.main_area)
        self.frames["pronostico"] = PronosticoFrame(self.main_area)
        self.frames["educativo"] = EducativoFrame(self.main_area)
        self.frames["dashboard"] = DashboardFrame(self.main_area)

        self._actualizar_stats()

    def _actualizar_stats(self):
        try:
            stats = contar_registros()
            self.stats_productos.configure(text=f"🍗 {stats['productos']} productos")
            self.stats_dias.configure(text=f"📅 {stats['dias']} días registrados")
        except Exception:
            pass

    def _mostrar_ayuda(self):
        win = ctk.CTkToplevel(self)
        win.title("¿Cómo funciona esto?")
        win.geometry("560x480")
        win.grab_set()

        ctk.CTkLabel(win, text="❓ Guía rápida de La Victoriana",
                     font=(FONT_FAMILY, FONT_SIZES["subtitle"], "bold"),
                     text_color=COLORS["primary"]).pack(pady=(15, 10))

        box = ctk.CTkTextbox(win, font=(FONT_FAMILY, 13), wrap="word", fg_color=COLORS["bg_card"])
        box.pack(fill="both", expand=True, padx=20, pady=10)
        box.insert("1.0", AYUDA_TEXTO)
        box.configure(state="disabled")

        ctk.CTkButton(win, text="Entendido", command=win.destroy,
                       fg_color=COLORS["success"]).pack(pady=(0, 15))

    def _show(self, key):
        if self.current:
            self.frames[self.current].pack_forget()
            self.nav_buttons[self.current].configure(fg_color="transparent")
        self.frames[key].pack(fill="both", expand=True)
        self.nav_buttons[key].configure(fg_color=COLORS["primary"])
        self.current = key
        self._actualizar_stats()
