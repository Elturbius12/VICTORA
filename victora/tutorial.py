"""Tutorial de bienvenida (primera apertura) y manual de usuario exportable (.docx).

Una sola fuente de contenido (PASOS y SECCIONES) alimenta el tutorial y el manual,
así ambos siempre dicen lo mismo.
"""
from __future__ import annotations

import io
from datetime import date

import streamlit as st

from victora import __version__

# ---------------------------------------------------------------- tutorial (pasos cortos)
PASOS = [
    ("¡Bienvenido a VICTORA!",
     "VICTORA responde una pregunta diaria: **¿cuánto producir mañana de cada producto?** "
     "Producir de más genera merma; producir de menos, ventas perdidas. VICTORA pronostica la demanda y "
     "calcula la cantidad óptima que minimiza ambos costos.",
     ["Funciona 100 % en su computadora, sin internet.",
      "Sus datos se guardan solo en esta PC.",
      "Este recorrido dura 1 minuto; puede volver a verlo desde la barra lateral."]),
    ("Dos secciones en la parte superior",
     "Con el selector de arriba elige cómo trabajar:",
     ["**🏪 Mi negocio (día a día)**: registre ventas y obtenga cada día qué preparar o comprar.",
      "**🔬 Análisis completo y artículo**: análisis estadístico completo, evidencia en soles y reporte "
      "listo para la gerencia o un artículo científico."]),
    ("Mi negocio: el uso diario",
     "Cada pestaña cumple una tarea:",
     ["**🏠 Resumen del día**: qué preparar/comprar hoy; botón 🔄 *Calcular / Actualizar*.",
      "**📋 Registro de Ventas**: anote ventas diarias, precios, productos y recetas; importe un catálogo.",
      "**🔮 Motor de Pronóstico**: competencia de modelos por producto.",
      "**📈 Seguimiento**: pronóstico vs. venta real.",
      "**📚 Módulo Educativo**, **📊 Dashboard** y **⚙️ Configuración** (copias de seguridad). Las pantallas se eligen en el menú de la izquierda, como en la app de escritorio."]),
    ("Análisis completo: de datos a decisión",
     "Siga las pestañas de izquierda a derecha:",
     ["**🏠 El Problema**: descargue la plantilla o pulse **🧪 Probar con datos de demostración**.",
      "**📤 Cargar Datos**: suba su Excel; el semáforo 🟢🟡🔴 le dice qué corregir.",
      "**✅ Decisión**: veredicto gerencial, dónde actuar primero y cuánto producir mañana.",
      "**💰 Impacto**: costo sin VICTORA vs. con VICTORA, en soles."]),
    ("Evidencia y artículo",
     "Todo lo necesario para justificar la decisión y redactar:",
     ["**📊 Análisis**: hallazgos, pruebas estadísticas y gráficos descargables.",
      "**📑 Reportes**: reporte Excel de 20 hojas con textos ya redactados, plan de producción y figuras.",
      "**📖 Metodología**: métodos, limitaciones y cita sugerida."]),
    ("¡Listo para empezar!",
     "Recomendación para la primera vez: vaya a **🔬 Análisis completo → 🏠 El Problema** y pulse "
     "**🧪 Probar con datos de demostración** para ver un resultado completo en segundos.",
     ["**📘 Manual** (barra lateral): descarga el manual detallado en Word.",
      "**🎓 Ver tutorial** (barra lateral): repite este recorrido.",
      "**🗑️ Restablecer todo**: limpia el análisis de la sesión (no borra ventas registradas)."]),
]

# ---------------------------------------------------------------- manual (detalle por sección)
SECCIONES = [
    ("1. Qué es VICTORA y qué problema resuelve", [
        "Los negocios de comida perecible deciden cada día cuánto producir sin conocer la demanda. Si producen "
        "de más, el excedente se pierde (merma); si producen de menos, pierden ventas y margen. VICTORA "
        "convierte el historial de ventas en una cantidad recomendada por producto y mide, en soles, cuánto "
        "cuesta decidir sin pronóstico.",
        "Método: pronóstico con modelos para series cortas (naïve, medias móviles, perfil semanal, SES, "
        "Holt-Winters, Croston/SBA/TSB), selección del mejor modelo por validación con origen rodante (MASE) y "
        "decisión con el modelo newsvendor (cantidad óptima Q* según la razón crítica Cu/(Cu+Co)).",
    ]),
    ("2. Instalación y primer uso", [
        "Ejecute VICTORA_Instalador.exe y siga el asistente (no requiere permisos de administrador). Se crea un "
        "acceso directo en el escritorio y en el menú Inicio.",
        "Al abrir VICTORA aparece una ventana negra (el motor del programa; déjela abierta) y luego el navegador "
        "con la aplicación. Para cerrar VICTORA cierre esa ventana.",
        "Si Windows muestra «Windows protegió su PC», pulse «Más información» → «Ejecutar de todas formas».",
        "Sus datos se guardan en %LOCALAPPDATA%\\VICTORA. Para pasarlos a otra PC use Configuración → Copia de "
        "seguridad y, en la otra PC, Restaurar.",
    ]),
    ("3. Pantalla principal", [
        "Encabezado: muestra el caso de estudio y, tras un análisis, el número de productos, días y el ahorro.",
        "Selector de sección: «Mi negocio (día a día)» o «Análisis completo y artículo».",
        "Barra lateral: estado del análisis, botones Ver tutorial, Manual (.docx) y Restablecer todo.",
    ]),
    ("4. Mi negocio (día a día)", [
        "🏠 Resumen del día — Lista qué preparar o comprar hoy por producto, con el pronóstico honesto y la "
        "cantidad sugerida (pronóstico + colchón según el margen). «🔄 Calcular / Actualizar» recalcula tras "
        "registrar ventas. Permite descargar el reporte Excel y la comanda PDF para la cocina.",
        "📋 Registro de Ventas — Anote la venta de cada día por producto, marque «Local cerrado» los días sin atención, "
        "edite precios, agregue productos y recetas (insumos por unidad) e importe catálogos o ventas en CSV/Excel.",
        "🔮 Motor de Pronóstico — Muestra la competencia de modelos de cada producto: qué modelo ganó, su error (MASE) y "
        "el gráfico de pronóstico.",
        "📈 Seguimiento — Compara lo pronosticado con lo vendido realmente; permite anotar observaciones y ver "
        "el historial completo.",
        "📚 Módulo Educativo — Explicación sencilla de cada modelo de pronóstico y del criterio de decisión.",
        "📊 Dashboard — Ventas por día, producto y categoría para una lectura rápida del negocio.",
        "⚙️ Configuración — Copia de seguridad (.xlsx) y restauración, datos de la comanda y fechas especiales "
        "(feriados, eventos).",
    ]),
    ("5. Análisis completo y artículo", [
        "🏠 El Problema — Explica el dilema merma vs. venta perdida con un ejemplo. Botones: Descargar plantilla "
        "de datos, Descargar guía de recetas, Plantilla de ejemplo y «🧪 Probar con datos de demostración» "
        "(32 productos ficticios).",
        "📤 Cargar Datos — Suba el Excel con la plantilla. El semáforo 🟢/🟡/🔴 lista cada problema con hoja, "
        "fila, columna y sugerencia. Indique cómo tratar los días sin registro y pulse «▶️ Ejecutar análisis». "
        "También puede usar «📋 Usar mis ventas registradas». En Configuración puede cambiar el nombre del "
        "negocio, la ciudad y el software (se insertan en los textos del reporte).",
        "✅ Decisión — Arriba, el VEREDICTO GERENCIAL en color: verde (adoptar VICTORA: ahorro estadísticamente "
        "sólido), ámbar (piloto: ahorro positivo pero el intervalo de confianza incluye cero) o rojo (mantener la "
        "práctica actual). Luego «Dónde actuar primero»: costo actual vs. con VICTORA por producto, ahorro y "
        "acción recomendada. Debajo: tarjetas de indicadores, tabla «Producir mañana / Mínimo / Máximo / "
        "Modelo», descarga del plan, gráfico por producto, plan de 7 días e insumos a comprar.",
        "💰 Impacto — Costo total de las 5 políticas comparadas (P0 = práctica actual … P4 = VICTORA): merma, "
        "margen perdido, nivel de servicio. Etiqueta ⚠️ SIMULADO si no hay producción real registrada, "
        "✅ REAL si la hay.",
        "📊 Análisis — Hallazgos clave y 9 secciones (descriptivos, clasificación de demanda, día de la semana, "
        "correlaciones, modelos, backtesting, pruebas de hipótesis Wilcoxon/Friedman/bootstrap, sensibilidad). "
        "Cada tabla (.xlsx) y gráfico (.png) tiene su botón de descarga.",
        "📑 Reportes — Reporte completo (.xlsx, 20 hojas) con párrafos de métodos y resultados ya redactados, "
        "plan de producción (.xlsx) y ZIP de figuras a 300 dpi.",
        "📖 Metodología — Texto de métodos con sus números, limitaciones detectadas automáticamente y cita "
        "sugerida del software.",
    ]),
    ("6. Cómo leer los resultados para decidir", [
        "Gerencia: mire el veredicto y el ahorro en soles con su intervalo de confianza al 95 %. Si el intervalo "
        "no incluye cero, el ahorro es robusto. La tabla «Dónde actuar primero» prioriza los productos con mayor "
        "ahorro.",
        "Operación: la columna «Producir mañana» es la cantidad a preparar; Mínimo y Máximo (percentiles 10 y "
        "90) indican el rango razonable. La lista de insumos indica qué comprar para la semana.",
        "Con menos de 28 días de datos el estudio es piloto: las cantidades son orientativas y mejoran al cargar "
        "más días.",
    ]),
    ("7. Uso del reporte en un artículo científico", [
        "La hoja de resultados del reporte trae párrafos redactados con sus datos (problema, método, resultados). "
        "Las tablas tienen formato para copiar directamente; las figuras están a 300 dpi.",
        "Cite el software con el texto de la pestaña Metodología.",
    ]),
    ("8. Preguntas frecuentes y solución de problemas", [
        "El navegador no se abrió: abra http://localhost:8501 manualmente.",
        "La ventana negra se cerró: VICTORA se detuvo; vuelva a abrirlo desde el acceso directo.",
        "Error en una pestaña: el resto de la app sigue funcionando; abra «Detalle técnico» y revise sus datos.",
        "Diagnóstico: ejecute «VICTORA.exe --autotest» desde la carpeta del programa.",
        "Datos: «Restablecer todo» no borra las ventas registradas; para borrarlas use Restaurar con una copia vacía.",
    ]),
]


# ---------------------------------------------------------------- tutorial interactivo
def _visto() -> bool:
    try:
        from victora.nucleo import database as db
        return str(db.get_config("tutorial_visto", "0")) == "1"
    except Exception:  # noqa: BLE001
        return False


def _marcar_visto():
    try:
        from victora.nucleo import database as db
        db.set_config("tutorial_visto", "1")
    except Exception:  # noqa: BLE001
        pass


def _cerrar():
    _marcar_visto()
    st.session_state["tuto_abierto"] = False
    st.session_state["tuto_paso"] = 0


@st.dialog("🎓 Tutorial de VICTORA", width="large", on_dismiss=_cerrar)
def _dialogo():
    i = st.session_state.get("tuto_paso", 0)
    titulo, texto, puntos = PASOS[i]
    st.progress((i + 1) / len(PASOS), text=f"Paso {i + 1} de {len(PASOS)}")
    st.subheader(titulo)
    st.markdown(texto)
    for p in puntos:
        st.markdown(f"- {p}")
    c1, c2, c3 = st.columns([1, 1, 1], vertical_alignment="center")
    if i > 0 and c1.button("Anterior", icon=":material/arrow_back:", key="tuto_ant", width="stretch"):
        st.session_state["tuto_paso"] = i - 1
        st.rerun()
    if i < len(PASOS) - 1:
        if c2.button("Saltar tutorial", key="tuto_saltar", width="stretch"):
            _cerrar()
            st.rerun()
        if c3.button("Siguiente", icon=":material/arrow_forward:", type="primary", key="tuto_sig", width="stretch"):
            st.session_state["tuto_paso"] = i + 1
            st.rerun()
    elif c3.button("Empezar a usar VICTORA", icon=":material/rocket_launch:", type="primary", key="tuto_fin",
                   width="stretch"):
        _cerrar()
        st.rerun()


def mostrar_si_corresponde():
    """Abre el tutorial la primera vez (en esta PC) o cuando el usuario lo pide."""
    if "tuto_abierto" not in st.session_state:
        st.session_state["tuto_abierto"] = not _visto()
    if st.session_state["tuto_abierto"]:
        _dialogo()


def abrir():
    st.session_state["tuto_abierto"] = True
    st.session_state["tuto_paso"] = 0


# ---------------------------------------------------------------- manual .docx
def _md_a_texto(s: str) -> str:
    return s.replace("**", "")


@st.cache_data(show_spinner=False)
def manual_docx(version: str = __version__) -> bytes:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt, RGBColor

    naranja = RGBColor(0xC2, 0x41, 0x0C)
    doc = Document()
    estilo = doc.styles["Normal"]
    estilo.font.name = "Calibri"
    estilo.font.size = Pt(11)
    for nivel in (1, 2):
        doc.styles[f"Heading {nivel}"].font.color.rgb = naranja

    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("VICTORA")
    r.bold, r.font.size, r.font.color.rgb = True, Pt(36), naranja
    s = doc.add_paragraph()
    s.alignment = WD_ALIGN_PARAGRAPH.CENTER
    s.add_run("Manual de usuario\n").font.size = Pt(18)
    s.add_run("Pronóstico de demanda y decisión óptima de producción para negocios de comida perecible\n")
    s.add_run(f"Versión {version} · {date.today():%d/%m/%Y}").italic = True
    doc.add_page_break()

    doc.add_heading("Contenido", level=1)
    for titulo, _ in SECCIONES:
        doc.add_paragraph(titulo)
    doc.add_page_break()

    for titulo, parrafos in SECCIONES:
        doc.add_heading(titulo, level=1)
        for p in parrafos:
            if " — " in p:
                cab, cuerpo = p.split(" — ", 1)
                para = doc.add_paragraph(style="List Bullet")
                para.add_run(cab + ": ").bold = True
                para.add_run(cuerpo)
            else:
                doc.add_paragraph(p)

    doc.add_heading("Anexo: recorrido rápido (tutorial)", level=1)
    for n, (titulo, texto, puntos) in enumerate(PASOS, 1):
        doc.add_heading(f"Paso {n}. {titulo}", level=2)
        doc.add_paragraph(_md_a_texto(texto))
        for p in puntos:
            doc.add_paragraph(_md_a_texto(p), style="List Bullet")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
