"""Módulo 4 – Dashboard de métricas y gráficos."""
import customtkinter as ctk
import numpy as np
import pandas as pd
from datetime import timedelta

from ..core.database import get_productos, get_pivot_ventas, get_ventas, contar_registros
from ..core.selection import diagnostico, backtest, elegir_ganador
from .tema import COLORS, FONT_FAMILY, FONT_SIZES

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


class DashboardFrame(ctk.CTkFrame):
    """Dashboard con KPI y gráficos de tendencia."""

    def __init__(self, master, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="📊  Dashboard",
                     font=(FONT_FAMILY, FONT_SIZES["title"], "bold"),
                     text_color=COLORS["primary"]).pack(anchor="w", padx=20, pady=(15, 5))

        ctk.CTkButton(self, text="🔄 Actualizar", width=120, command=self._refresh,
                       fg_color=COLORS["info"]).pack(anchor="w", padx=20, pady=5)

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=15, pady=5)

        self._refresh()

    def _refresh(self):
        for w in self.scroll.winfo_children():
            w.destroy()

        stats = contar_registros()

        # ── KPI Cards ──
        kpi_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        kpi_frame.pack(fill="x", pady=5)

        kpis = [
            ("Productos", str(stats["productos"]), "🍗"),
            ("Registros", str(stats["registros"]), "📋"),
            ("Días", str(stats["dias"]), "📅"),
        ]
        for titulo, valor, icono in kpis:
            card = ctk.CTkFrame(kpi_frame, fg_color=COLORS["bg_card"], corner_radius=10,
                                width=160, height=90)
            card.pack(side="left", padx=8, pady=5)
            card.pack_propagate(False)
            ctk.CTkLabel(card, text=icono + " " + titulo,
                         font=(FONT_FAMILY, FONT_SIZES["small"]),
                         text_color=COLORS["text_muted"]).pack(pady=(12, 2))
            ctk.CTkLabel(card, text=valor,
                         font=(FONT_FAMILY, 24, "bold"),
                         text_color=COLORS["primary"]).pack()

        pivot, _ = get_pivot_ventas()
        if pivot.empty:
            ctk.CTkLabel(self.scroll, text="No hay datos de ventas para graficar.",
                         text_color=COLORS["text_muted"]).pack(pady=20)
            return

        if not HAS_MPL:
            ctk.CTkLabel(self.scroll, text="Instale matplotlib para ver gráficos: pip install matplotlib",
                         text_color=COLORS["warning"]).pack(pady=20)
            return

        # ── Gráfico 1: Ventas totales por día ──
        fig1 = Figure(figsize=(7, 2.5), dpi=100, facecolor=COLORS["bg_card"])
        ax1 = fig1.add_subplot(111)
        ax1.set_facecolor(COLORS["bg_card"])
        totals = pivot.sum(axis=1)
        ax1.fill_between(totals.index, totals.values, alpha=0.3, color=COLORS["info"])
        ax1.plot(totals.index, totals.values, color=COLORS["info"], linewidth=2)
        ax1.set_title("Ventas totales por día (unidades)", color=COLORS["text"], fontsize=10)
        ax1.tick_params(colors=COLORS["text_muted"], labelsize=8)
        fig1.tight_layout()
        c1 = FigureCanvasTkAgg(fig1, master=self.scroll)
        c1.draw()
        c1.get_tk_widget().pack(fill="x", padx=5, pady=5)

        # ── Gráfico 2: Top 5 productos ──
        fig2 = Figure(figsize=(7, 2.5), dpi=100, facecolor=COLORS["bg_card"])
        ax2 = fig2.add_subplot(111)
        ax2.set_facecolor(COLORS["bg_card"])
        top5 = pivot.sum().sort_values(ascending=True).tail(5)
        bars = ax2.barh(top5.index, top5.values, color=COLORS["primary"])
        ax2.set_title("Top 5 productos (total unidades)", color=COLORS["text"], fontsize=10)
        ax2.tick_params(colors=COLORS["text_muted"], labelsize=8)
        for bar, val in zip(bars, top5.values):
            ax2.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                     f"{int(val)}", va="center", color=COLORS["text"], fontsize=8)
        fig2.tight_layout()
        c2 = FigureCanvasTkAgg(fig2, master=self.scroll)
        c2.draw()
        c2.get_tk_widget().pack(fill="x", padx=5, pady=5)

        # ── Gráfico 3: Heatmap día de semana ──
        fig3 = Figure(figsize=(7, 2.5), dpi=100, facecolor=COLORS["bg_card"])
        ax3 = fig3.add_subplot(111)
        ax3.set_facecolor(COLORS["bg_card"])
        pivot_copy = pivot.copy()
        pivot_copy["dia_semana"] = pivot_copy.index.dayofweek
        dias_nombres = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        by_dow = pivot_copy.groupby("dia_semana").mean()
        top_prods = pivot.sum().sort_values(ascending=False).head(5).index
        x = np.arange(len(by_dow))
        width = 0.15
        colors_list = [COLORS["primary"], COLORS["info"], COLORS["success"],
                       COLORS["warning"], COLORS["danger"]]
        for i, prod in enumerate(top_prods):
            if prod in by_dow.columns:
                ax3.bar(x + i * width, by_dow[prod], width, label=prod[:12],
                        color=colors_list[i % len(colors_list)], alpha=0.8)
        ax3.set_xticks(x + width * 2)
        ax3.set_xticklabels([dias_nombres[i] for i in by_dow.index], color=COLORS["text_muted"])
        ax3.set_title("Promedio por día de la semana (Top 5)", color=COLORS["text"], fontsize=10)
        ax3.legend(fontsize=7, facecolor=COLORS["bg_card"], edgecolor="none",
                   labelcolor=COLORS["text"])
        ax3.tick_params(colors=COLORS["text_muted"], labelsize=8)
        fig3.tight_layout()
        c3 = FigureCanvasTkAgg(fig3, master=self.scroll)
        c3.draw()
        c3.get_tk_widget().pack(fill="x", padx=5, pady=5)

        # ── Tabla resumen de clasificación ──
        ctk.CTkLabel(self.scroll, text="Clasificación de demanda por producto",
                     font=(FONT_FAMILY, FONT_SIZES["subtitle"], "bold"),
                     text_color=COLORS["primary"]).pack(anchor="w", padx=10, pady=(15, 5))

        hdr = ctk.CTkFrame(self.scroll, fg_color=COLORS["bg_sidebar"], corner_radius=5)
        hdr.pack(fill="x", padx=5, pady=2)
        for col, w in [("Producto", 200), ("Clase", 150), ("ADI", 60), ("CV²", 60), ("% cero", 60)]:
            ctk.CTkLabel(hdr, text=col, width=w,
                         font=(FONT_FAMILY, FONT_SIZES["small"], "bold")).pack(side="left", padx=3)

        for prod in pivot.columns:
            y = pivot[prod].values.astype(float)
            d = diagnostico(y)
            row_fr = ctk.CTkFrame(self.scroll, fg_color="transparent")
            row_fr.pack(fill="x", padx=5, pady=1)
            ctk.CTkLabel(row_fr, text=prod, width=200,
                         font=(FONT_FAMILY, FONT_SIZES["small"])).pack(side="left", padx=3)
            ctk.CTkLabel(row_fr, text=d["clase"], width=150,
                         font=(FONT_FAMILY, FONT_SIZES["small"]),
                         text_color=COLORS["warning"]).pack(side="left", padx=3)
            ctk.CTkLabel(row_fr, text=f"{d['adi']:.2f}", width=60).pack(side="left", padx=3)
            ctk.CTkLabel(row_fr, text=f"{d['cv2']:.3f}", width=60).pack(side="left", padx=3)
            ctk.CTkLabel(row_fr, text=f"{d['pct_cero']:.0%}", width=60).pack(side="left", padx=3)
