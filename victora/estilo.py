"""Identidad visual de VICTORA / La Victoriana: paleta, CSS fino y piezas de UI reutilizables.

La paleta es la del programa de escritorio original (gui/tema.py): dorado, marrón y azul oscuro.
El tema base (fondos, tablas, widgets) está en .streamlit/config.toml; aquí solo va lo que el tema
no cubre. Todo es local (sin fuentes ni recursos de internet) para que el ejecutable funcione sin conexión.
"""
from __future__ import annotations

import html

import streamlit as st

# Colores corporativos (idénticos a gui/tema.py del original)
COLORS = {
    "primary": "#B8860B",       # Dorado oscuro
    "primary_hover": "#DAA520",
    "secondary": "#2C1810",     # Marrón oscuro
    "bg_dark": "#1A1A2E",       # Fondo principal
    "bg_card": "#16213E",       # Fondo tarjetas
    "bg_sidebar": "#0F3460",    # Sidebar
    "text": "#EAEAEA",
    "text_muted": "#A0A0A0",
    "success": "#27AE60",
    "warning": "#F39C12",
    "danger": "#E74C3C",
    "info": "#3498DB",
}
FONT_FAMILY = "Segoe UI"
TITULO_VENTANA = "La Victoriana – Sistema de Pronóstico de Demanda"

C = COLORS
CSS = f"""
<style>
/* ---------- base ---------- */
.block-container {{padding-top: 1.2rem; max-width: 1400px;}}
h1, h2, h3 {{letter-spacing: -0.01em;}}

/* ---------- encabezado de marca (modo Análisis completo) ---------- */
.vx-hero {{
  position: relative; overflow: hidden; border-radius: 18px; padding: 22px 28px; margin-bottom: 6px;
  background: linear-gradient(120deg, #7A1F04 0%, #C2410C 45%, #EA7A1E 100%); color: #fff;
  box-shadow: 0 10px 30px -12px rgba(194, 65, 12, .55);
}}
.vx-hero::after {{
  content: ""; position: absolute; right: -60px; top: -60px; width: 260px; height: 260px; border-radius: 50%;
  background: radial-gradient(circle, rgba(255,255,255,.18), rgba(255,255,255,0) 70%);
}}
.vx-hero .vx-marca {{font-size: .8rem; font-weight: 700; letter-spacing: .18em; opacity: .85; text-transform: uppercase;}}
.vx-hero .vx-titulo {{font-size: 1.9rem; font-weight: 800; line-height: 1.15; margin: 4px 0 6px;}}
.vx-hero .vx-sub {{font-size: 1rem; opacity: .92; max-width: 820px;}}
.vx-chips {{margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap;}}
.vx-chip {{background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.28); border-radius: 999px;
          padding: 3px 12px; font-size: .8rem; font-weight: 600;}}

/* ---------- pasos ---------- */
.vx-pasos {{display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin: 8px 0 4px;}}
.vx-paso {{border: 1px solid #2A3558; background: {C['bg_card']}; border-radius: 14px; padding: 16px; transition: all .18s ease;}}
.vx-paso:hover {{transform: translateY(-3px); border-color: {C['primary']};}}
.vx-paso .n {{display:inline-flex; align-items:center; justify-content:center; width:28px; height:28px; border-radius:50%;
             background:{C['primary']}; color:#fff; font-weight:700; font-size:.85rem;}}
.vx-paso .t {{font-weight: 700; margin-top: 8px;}}
.vx-paso .d {{font-size: .85rem; color: {C['text_muted']};}}
@media (max-width: 900px) {{.vx-pasos {{grid-template-columns: repeat(2, 1fr);}}}}

/* ---------- veredicto gerencial ---------- */
.vx-veredicto {{border-radius: 14px; padding: 16px 20px; border-left: 6px solid; margin: 6px 0 10px;}}
.vx-veredicto.ok {{background: rgba(39,174,96,.14); border-color: {C['success']};}}
.vx-veredicto.med {{background: rgba(243,156,18,.14); border-color: {C['warning']};}}
.vx-veredicto.no {{background: rgba(231,76,60,.14); border-color: {C['danger']};}}
.vx-veredicto .k {{font-size: .75rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; opacity: .7;}}
.vx-veredicto .v {{font-size: 1.15rem; font-weight: 700; margin-top: 2px;}}
.vx-veredicto .e {{font-size: .9rem; margin-top: 4px; color: {C['text']};}}

/* ---------- pestañas ---------- */
.stTabs [data-baseweb="tab-list"] {{gap: 4px; border-bottom: 1px solid #2A3558;}}
.stTabs [data-baseweb="tab"] {{padding: 8px 14px; border-radius: 10px 10px 0 0; font-weight: 600;}}
.stTabs [aria-selected="true"] {{background: {C['bg_card']};}}

/* ---------- barra lateral del modo análisis ---------- */
.vx-side-marca {{display:flex; align-items:center; gap:10px; margin-bottom: 4px;}}
.vx-side-marca .logo {{width:40px; height:40px; border-radius:12px; display:flex; align-items:center; justify-content:center;
  background: linear-gradient(135deg,#C2410C,#EA7A1E); color:#fff; font-weight:800; font-size:1.2rem;}}
.vx-side-marca .nom {{font-weight:800; font-size:1.1rem; line-height:1;}}
.vx-side-marca .ver {{font-size:.75rem; opacity:.65;}}

/* ================= La Victoriana (modo Mi negocio) ================= */
.vic-logo {{text-align:center; margin: 6px 0 4px;}}
.vic-logo .n {{color:{C['primary']}; font-weight:700; font-size:1.45rem;}}
.vic-logo .s {{color:{C['text_muted']}; font-size:.85rem; margin-top:2px;}}
.vic-logo .f {{color:{C['primary']}; font-style:italic; font-size:.8rem; margin-top:2px;}}
.vic-stats {{background:{C['bg_card']}; border-radius:10px; padding:10px 12px; font-size:.85rem;}}
.vic-stats .t {{color:{C['primary']}; font-weight:700; margin-bottom:4px;}}
.vic-pie {{text-align:center; color:{C['text_muted']}; font-size:.78rem; line-height:1.6;}}
.vic-titulo {{color:{C['primary']}; font-weight:700; font-size:1.75rem; margin: 0 0 2px;}}
.vic-sec {{color:{C['primary']}; font-weight:700; font-size:1.2rem; margin: 14px 0 4px;}}
.vic-caja {{border-radius:10px; padding:12px 16px; margin:8px 0 10px;}}
.vic-caja .e {{font-weight:700; font-size:1rem;}}
.vic-caja .v {{font-weight:700; font-size:1.9rem; line-height:1.2;}}
.vic-kpis {{display:flex; gap:16px; flex-wrap:wrap; margin:6px 0 12px;}}
.vic-kpi {{background:{C['bg_card']}; border-radius:10px; width:160px; height:90px; text-align:center; padding-top:12px;}}
.vic-kpi .t {{color:{C['text_muted']}; font-size:.85rem;}}
.vic-kpi .v {{color:{C['primary']}; font-weight:700; font-size:1.6rem;}}
.vic-formula {{background:{C['bg_sidebar']}; color:{C['warning']}; border-radius:8px; padding:10px 15px;
              font-family: Consolas, monospace; white-space: pre-wrap; margin: 4px 0 8px;}}
/* tarjetas (st.container con key vic_card_*) */
[class*="st-key-vic_card"] {{background:{C['bg_card']}; border-radius:10px; padding: 4px 6px;}}
/* menú lateral de La Victoriana: texto alineado a la izquierda, como los CTkButton del original */
[class*="st-key-nav_neg_"] button {{justify-content:flex-start; padding-left:12px; min-height:40px;}}
[class*="st-key-nav_neg_"] button > div, [class*="st-key-nav_neg_"] button p {{justify-content:flex-start; text-align:left; width:100%;}}
[class*="st-key-nav_neg_"] button:hover {{background:{C['primary_hover']}; color:#fff;}}
</style>
"""


def inyectar_css():
    st.html(CSS)


def hero(titulo: str, subtitulo: str, chips: list[str] | None = None, marca: str = "VICTORA"):
    ch = "".join(f"<span class='vx-chip'>{html.escape(c)}</span>" for c in (chips or []))
    st.html(f"<div class='vx-hero'><div class='vx-marca'>{html.escape(marca)}</div>"
            f"<div class='vx-titulo'>{html.escape(titulo)}</div><div class='vx-sub'>{html.escape(subtitulo)}</div>"
            f"<div class='vx-chips'>{ch}</div></div>")


def pasos(items: list[tuple[str, str]]):
    cuerpo = "".join(f"<div class='vx-paso'><span class='n'>{i}</span><div class='t'>{html.escape(t)}</div>"
                     f"<div class='d'>{html.escape(d)}</div></div>" for i, (t, d) in enumerate(items, 1))
    st.html(f"<div class='vx-pasos'>{cuerpo}</div>")


def veredicto(nivel: str, clave: str, titulo: str, explicacion: str):
    """nivel: 'ok' (verde), 'med' (ámbar) o 'no' (rojo)."""
    st.html(f"<div class='vx-veredicto {nivel}'><div class='k'>{html.escape(clave)}</div>"
            f"<div class='v'>{html.escape(titulo)}</div><div class='e'>{html.escape(explicacion)}</div></div>")


def marca_lateral(version: str):
    st.html(f"<div class='vx-side-marca'><div class='logo'>V</div><div><div class='nom'>VICTORA</div>"
            f"<div class='ver'>v{html.escape(version)} · funciona sin internet</div></div></div>")


# ------------------------------------------------------------------ La Victoriana (Mi negocio)
def logo_victoriana():
    st.html("<div class='vic-logo'><div class='n'>🍗 La Victoriana</div><div class='s'>Pronóstico de Demanda</div>"
            "<div class='f'>\"Vende lo justo, no más, no menos\"</div></div>")


def stats_victoriana(productos: int, dias: int):
    st.html(f"<div class='vic-stats'><div class='t'>📦&nbsp; Su negocio en números</div>"
            f"<div>🍗 {productos} productos</div><div>📅 {dias} días registrados</div></div>")


def pie_victoriana(version: str):
    st.html(f"<div class='vic-pie'>📍 Juliaca, Perú<br>v{html.escape(version)}</div>")


def titulo(texto: str):
    """Título de pantalla en dorado (FONT_SIZES['title'] del original)."""
    st.html(f"<div class='vic-titulo'>{html.escape(texto)}</div>")


def seccion(texto: str):
    """Subtítulo de sección en dorado (FONT_SIZES['subtitle'] del original)."""
    st.html(f"<div class='vic-sec'>{html.escape(texto)}</div>")


def caja(color: str, etiqueta: str, valor: str, texto_oscuro: bool = False):
    """Recuadro destacado de color (pronóstico, cantidad sugerida…) como en la app de escritorio."""
    tc = "black" if texto_oscuro else "white"
    st.html(f"<div class='vic-caja' style='background:{COLORS[color]};color:{tc}'>"
            f"<div class='e'>{html.escape(etiqueta)}</div><div class='v'>{html.escape(valor)}</div></div>")


def kpis(items: list[tuple[str, str, str]]):
    """Tarjetas KPI del Dashboard: (titulo, valor, icono)."""
    cuerpo = "".join(f"<div class='vic-kpi'><div class='t'>{html.escape(i)} {html.escape(t)}</div>"
                     f"<div class='v'>{html.escape(v)}</div></div>" for t, v, i in items)
    st.html(f"<div class='vic-kpis'>{cuerpo}</div>")


def formula(texto: str):
    st.html(f"<div class='vic-formula'>{html.escape(texto)}</div>")


def estilo_mpl(fig, ax):
    """Aplica el estilo oscuro de los gráficos de la app de escritorio a una figura matplotlib."""
    fig.patch.set_facecolor(COLORS["bg_card"])
    ax.set_facecolor(COLORS["bg_card"])
    ax.tick_params(colors=COLORS["text_muted"], labelsize=8)
    ax.title.set_color(COLORS["text"])
    ax.title.set_fontsize(10)
    for s in ax.spines.values():
        s.set_color("#2A3558")
    leg = ax.get_legend()
    if leg is not None:
        leg.get_frame().set_facecolor(COLORS["bg_card"])
        leg.get_frame().set_edgecolor("none")
        for t in leg.get_texts():
            t.set_color(COLORS["text"])
