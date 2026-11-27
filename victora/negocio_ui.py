"""Pantallas de «Mi negocio»: la app de escritorio La Victoriana, ahora en Streamlit.

Mismas 7 pantallas, mismo orden, mismos nombres y textos que gui/ del programa original
(customtkinter), más las mejoras de la versión web (recetas, restauración de copias, comanda
en el Resumen, filtros…). Los datos viven en la base de datos (SQLite en la PC): se conservan
entre visitas y reinicios.

Rendimiento: solo se ejecuta la pantalla elegida en el menú lateral; los cálculos pesados se
hacen una vez y quedan en st.session_state hasta que cambian los datos.
"""
from __future__ import annotations

import io
from datetime import date, timedelta

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from victora import estilo  # noqa: E402
from victora.estilo import COLORS  # noqa: E402
from victora.nucleo import database as db  # noqa: E402
from victora.nucleo.educativo import MODELOS_EDUCATIVOS  # noqa: E402
from victora.nucleo.optimizer import cantidad_optima, razon_critica  # noqa: E402
from victora.nucleo.reportes import (  # noqa: E402
    MIN_DIAS_HISTORIAL_PROPIO, backfill_historial_pronosticos, calcular_recomendaciones_todas,
    exportar_reporte_excel, exportar_seguimiento_excel, generar_comanda_pdf, mejor_peor_dia_semana,
    productos_que_casi_no_se_mueven,
)
from victora.nucleo.selection import (  # noqa: E402
    backtest, diagnostico, elegir_ganador, modelos_faltantes, nivel_confianza, pronosticar,
    pronosticar_horizonte, simular_politica,
)

# Menú lateral: mismo orden y nombres que gui/main_window.py
TABS = ["🏠 Resumen del día", "📋 Registro de Ventas", "🔮 Motor de Pronóstico", "📈 Seguimiento",
        "📚 Módulo Educativo", "📊 Dashboard", "⚙️ Configuración"]

AYUDA_TEXTO = """**🏠 Resumen del día**
Al abrir la app, aquí verá de un vistazo qué preparar y qué comprar hoy
para todos sus productos, sin tener que revisarlos uno por uno. También
puede exportar un reporte en Excel para el encargado de cocina.

**📋 Registro de Ventas**
Aquí anota cada día cuánto vendió de cada producto y a qué precio lo vende.
Mientras más días registre, mejores serán los cálculos. Si el local estuvo
cerrado, use el botón "Local cerrado hoy" en vez de poner 0 en todo.

**🔮 Motor de Pronóstico**
Elija un producto y el sistema le dirá cuánto se espera vender mañana (y
cuánto conviene preparar o comprar), probando varias formas de calcularlo
y quedándose con la que mejor funciona para ese producto en su negocio.

**📈 Seguimiento**
Compara lo que el sistema pronosticó contra lo que realmente se vendió,
para que vea qué tan bien está acertando y anote la razón de los errores
grandes (llovió, feriado no registrado, etc.).

**📚 Módulo Educativo**
Explica, en palabras simples y con ejemplos de su propio negocio, cómo
funciona cada método de cálculo que usa el sistema.

**📊 Dashboard**
Muestra un vistazo general: qué se vende más, en qué días, y cómo está
clasificado cada producto (si se vende parejo o de forma irregular).

**⚙️ Configuración**
Copias de seguridad de su base de datos, la comanda para imprimir en la
cocina, y el calendario de feriados y fechas especiales.

💡 Consejo: registre sus ventas todos los días. El sistema se vuelve más
preciso mientras más información tenga de su negocio.
"""

ACCION_TXT = {"preparado": "preparar", "reventa": "comprar / reponer"}
CLASE_SIMPLE = {
    "Suave (estable)": ("📈 Se vende de forma pareja",
                        "Casi todos los días vende una cantidad parecida de este producto."),
    "Errática (variable)": ("🎢 Las ventas suben y bajan mucho", "Unos días vende bastante y otros días casi nada."),
    "Intermitente": ("🌙 Se vende pocas veces",
                     "Hay varios días seguidos sin ninguna venta, pero cuando se vende, es poca cantidad."),
    "Irregular (grumosa)": ("⚡ Se vende poco, pero a veces de golpe",
                            "La mayoría de días no se vende nada, pero de vez en cuando se vende bastante de una "
                            "sola vez."),
    "Sin ventas": ("❔ Todavía no hay suficiente información", "Necesita registrar más días de ventas de este producto."),
}
ORIGEN_TXT = {"feriado": "Feriado oficial", "comercial": "Fecha comercial", "manual": "Agregada por usted"}
UMBRAL_ERROR_GRANDE = 0.5


# ------------------------------------------------------------------ utilidades
@st.cache_resource(show_spinner=False)
def iniciar_bd() -> str:
    """Crea tablas (una vez por proceso) y siembra el catálogo si está vacío."""
    db.init_db()
    if db.get_productos().empty:
        db.insertar_productos_default()
    return "postgres" if db.usa_postgres() else "sqlite"


def _refrescar():
    """Invalida los cálculos guardados en la sesión cuando cambian los datos."""
    for k in ("neg_recos", "neg_pron"):
        st.session_state.pop(k, None)


def _png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return buf.getvalue()


def _bytes(funcion, *args) -> bytes:
    buf = io.BytesIO()
    funcion(*args, buf)
    return buf.getvalue()


def _abrir(dialogo, *args):
    """Abre un diálogo propio cerrando el tutorial (Streamlit permite un solo diálogo por ejecución)."""
    st.session_state["tuto_abierto"] = False
    dialogo(*args)


def aviso_bd():
    iniciar_bd()
    st.caption(f"💾 Datos guardados en esta computadora: {db.DB_PATH}")


def _recos(guardar=True):
    if "neg_recos" not in st.session_state:
        with st.spinner("⏳ Calculando recomendaciones para todos los productos... esto puede tardar un momento."):
            st.session_state["neg_recos"] = calcular_recomendaciones_todas(guardar_historial=guardar)
    return st.session_state["neg_recos"]


def _tabla_recos(filas, con_categoria: bool) -> pd.DataFrame:
    t = pd.DataFrame([{
        "": r.get("confianza_icono", ""),
        **({"Categoría": r.get("categoria") or "Sin categoría"} if con_categoria else {}),
        "Producto": r["nombre"] + ("  ⚠️" if r["sin_precio"] else ""),
        "Pronóstico venta": None if r["pronostico"] is None else round(r["pronostico"], 1),
        "Cantidad sugerida": r["cantidad_sugerida"],
        "Acción": (r["accion"] or "—").capitalize(),
        "Ganancia estimada": ("Sin precio" if r.get("ganancia_estimada") is None
                              else f"S/ {r['ganancia_estimada']:.0f}"),
        "Método usado": r.get("modelo") or "—",
    } for r in filas])
    return t


_CFG_RECOS = {
    "Pronóstico venta": st.column_config.NumberColumn(format="%.1f unid."),
    "Cantidad sugerida": st.column_config.NumberColumn(format="%d unid."),
}


def _alto(n: int) -> int:
    return 38 + 35 * max(n, 1)


def _boton_respaldo(contenedor, key: str, etiqueta: str):
    """Copia de seguridad: en el navegador no se elige carpeta; se prepara y se descarga."""
    if contenedor.button(etiqueta, key=key, width="stretch"):
        st.session_state["neg_respaldo"] = db.respaldar_base()
    if st.session_state.get("neg_respaldo"):
        contenedor.download_button("📥 Descargar copia (.xlsx)", st.session_state["neg_respaldo"],
                                   f"victoriana_respaldo_{date.today().isoformat()}.xlsx", key=f"{key}_dl",
                                   width="stretch")


# ================================================================== barra lateral
@st.dialog("❓ Guía rápida de La Victoriana")
def dialogo_ayuda():
    st.markdown(AYUDA_TEXTO.replace("\n", "  \n"))
    if st.button("Entendido", key="neg_ayuda_ok", type="primary"):
        st.rerun()


def _ir_a(pantalla: str):
    st.session_state["tabs_neg"] = pantalla


def barra_lateral(version: str) -> str:
    """Sidebar de la app de escritorio: logo, frase, menú de 7 pantallas, números del negocio,
    ayuda y pie. Devuelve la pantalla elegida."""
    estilo.logo_victoriana()
    if st.session_state.get("tabs_neg") not in TABS:
        st.session_state["tabs_neg"] = TABS[0]
    elegido = st.session_state["tabs_neg"]
    # Botones de navegación (como en la app de escritorio: el activo se pinta de dorado)
    with st.container(gap="xsmall", key="vic_nav"):
        for i, t in enumerate(TABS):
            st.button(t, key=f"nav_neg_{i}", type="primary" if t == elegido else "tertiary", width="stretch",
                      on_click=_ir_a, args=(t,))
    st.divider()
    try:
        s = db.contar_registros()
        estilo.stats_victoriana(s["productos"], s["dias"])
    except Exception:  # noqa: BLE001
        pass
    if st.button("❓ ¿Cómo funciona esto?", key="neg_ayuda", width="stretch"):
        _abrir(dialogo_ayuda)
    return elegido


# ================================================================== 🏠 Resumen del día
def tab_resumen():
    estilo.titulo("🏠  Resumen del día")
    prox = db.proxima_fecha_especial()
    if prox:
        dias = (date.fromisoformat(prox["fecha"]) - date.today()).days
        if 0 <= dias <= 7:
            st.caption(f"📅 En {dias} día(s) es {prox['nombre']} ({prox['fecha']}) — si otros años ese día vendió "
                       "distinto a lo normal, considere ajustar lo que sugiere el sistema ese día.")
    d = db.dias_desde_ultimo_respaldo()
    if d is None:
        st.caption("💾 Todavía no ha hecho ninguna copia de seguridad de su base de datos. Se recomienda hacerlo "
                   "de vez en cuando para no perder su historial.")
    elif d > 14:
        st.caption(f"💾 Su última copia de seguridad fue hace {d} días. Considere hacer una nueva.")

    c1, c2, c3, c4 = st.columns(4)
    if c1.button("🔄 Calcular / Actualizar", key="neg_res_calc", type="primary", width="stretch"):
        _refrescar()
    resultados, faltantes = _recos()
    hoy = date.today().isoformat()
    if resultados:
        c2.download_button("📄 Exportar reporte (Excel)", _bytes(exportar_reporte_excel, resultados),
                           f"reporte_victoriana_{hoy}.xlsx", key="neg_res_xlsx", width="stretch")
        c3.download_button("🧾 Comanda para cocina (PDF)", _bytes(generar_comanda_pdf, resultados),
                           f"comanda_{hoy}.pdf", key="neg_res_pdf", width="stretch")
    _boton_respaldo(c4, "neg_res_resp", "💾 Hacer copia de seguridad")

    if not resultados:
        st.warning("⚠️ Todavía no hay productos cargados. Vaya a 'Registro de Ventas' para importar su catálogo.")
        return
    calculables = [r for r in resultados if r["pronostico"] is not None]
    st.caption(f"✅ Recomendaciones listas ({len(calculables)} de {len(resultados)} productos con datos suficientes).")
    if faltantes:
        ej = ", ".join(faltantes[:5]) + ("..." if len(faltantes) > 5 else "")
        st.warning(f"⚠️ Hay {len(faltantes)} día(s) sin ningún registro en su historial ({ej}). Eso puede hacer "
                   "menos preciso el cálculo — revíselo en 'Registro de Ventas'.")
    with st.container(key="vic_card_resumen"):
        if not calculables:
            st.warning("⚠️ Todavía no hay suficientes días de ventas registrados para ningún producto (ni productos "
                       "parecidos para estimar). Se necesitan al menos 5 días.")
            return
        top3 = sorted(calculables, key=lambda r: r["total_vendido"], reverse=True)[:3]
        prep = [r for r in top3 if r["accion"] == "preparar"]
        comp = [r for r in top3 if r["accion"] != "preparar"]
        partes = []
        if prep:
            partes.append("preparar " + ", ".join(f"{r['cantidad_sugerida']} de {r['nombre']}" for r in prep))
        if comp:
            partes.append("comprar/reponer " + ", ".join(f"{r['cantidad_sugerida']} de {r['nombre']}" for r in comp))
        if partes:
            estilo.seccion("📢 Hoy debería " + " y ".join(partes))
        mp = mejor_peor_dia_semana()
        if mp:
            st.caption(f"📊 En promedio, su mejor día es el {mp['mejor_dia']} ({mp['mejor_valor']} unid.) y su día "
                       f"más flojo es el {mp['peor_dia']} ({mp['peor_valor']} unid.).")
        # Tabla completa, agrupada por categoría (como en el original)
        ordenados = sorted(resultados, key=lambda r: (r.get("categoria") or "~", -r["total_vendido"]))
        grupos: dict[str, list] = {}
        for r in ordenados:
            grupos.setdefault(r.get("categoria") or "Sin categoría", []).append(r)
        for cat, filas in grupos.items():
            st.markdown(f"**:primary[{cat}]**")
            st.dataframe(_tabla_recos(filas, False), hide_index=True, width="stretch", height=_alto(len(filas)),
                         column_config=_CFG_RECOS)
        st.caption("🟢 confiable · 🟡 información limitada · 🔴 muy poca información")
        sp = sum(1 for r in resultados if r["sin_precio"])
        if sp:
            st.warning(f"⚠️ {sp} producto(s) no tienen precio registrado. Configúrelos en 'Registro de Ventas' para "
                       "ver su ganancia estimada.")
        lentos = productos_que_casi_no_se_mueven()
        if lentos:
            st.caption("🐌 Estos productos casi no se mueven (candidatos a revisar precio o sacarlos del menú): "
                       + ", ".join(p["nombre"] for p in lentos[:8]) + ".")


# ================================================================== 📋 Registro de Ventas
@st.dialog("➕ Agregar nuevo producto")
def dialogo_nuevo_producto():
    prods = db.get_productos()
    with st.form("neg_nuevo_prod", border=False):
        nombre = st.text_input("Nombre del producto")
        cats = sorted({c for c in prods["categoria"].fillna("") if c})
        categoria = st.selectbox("Categoría (p.ej. 'Pizza Personal', 'Bebidas'; ayuda a estimar productos nuevos "
                                 "usando productos parecidos)", [""] + cats, accept_new_options=True)
        precio = st.number_input("Precio de venta (S/)", min_value=0.0, step=0.5)
        margen = st.number_input("Margen de ganancia sobre el precio (%). Ej: 27.5", 0.0, 100.0,
                                 db.MARGEN_DEFECTO * 100)
        tipo = st.radio("Tipo de producto", ["preparado", "reventa"],
                        format_func=lambda t: {"preparado": "Se prepara/cocina (pizza, hamburguesa...)",
                                               "reventa": "Se compra ya hecho (gaseosa embotellada...)"}[t])
        vida = st.number_input("¿Cuántos días dura antes de malograrse? (1 = solo el día)", min_value=1, value=1)
        recup = st.number_input("Si sobra, ¿qué % se puede recuperar o reutilizar? (0 a 1)", 0.0, 1.0, 0.5)
        if st.form_submit_button("Guardar producto", type="primary"):
            if not nombre.strip():
                st.warning("Escriba un nombre de producto.")
            else:
                db.agregar_producto(nombre.strip(), precio, int(vida), recup, tipo=tipo, margen=margen / 100,
                                    categoria=(categoria or "").strip())
                _refrescar()
                st.rerun()


@st.dialog("📦 Importar catálogo (productos y precios)")
def dialogo_importar_catalogo():
    st.caption("Columnas reconocidas: producto, precio, tipo (preparado/reventa), margen, categoria, "
               "vida_util_dias, recuperable.")
    up = st.file_uploader("Excel o CSV", type=["xlsx", "xls", "csv"], key="neg_up_cat")
    if up is not None and st.button("Importar catálogo", key="neg_imp_cat", type="primary"):
        try:
            act, cre, ign = db.importar_catalogo(io.BytesIO(up.getvalue()), up.name)
        except Exception as e:  # noqa: BLE001
            st.error(f"Error al importar catálogo: {e}")
            return
        _refrescar()
        st.success(f"Se actualizaron {act} producto(s) y se crearon {cre} nuevo(s).")
        if ign:
            st.warning(f"⚠️ Se ignoraron {ign} fila(s) porque parecían notas de texto, no productos.")


@st.dialog("📂 Importar ventas")
def dialogo_importar_ventas():
    st.caption("CSV (o Excel) con columnas: fecha, producto, unidades.")
    up = st.file_uploader("Archivo de ventas", type=["csv", "xlsx", "xls"], key="neg_up_ventas")
    if up is not None and st.button("Importar ventas", key="neg_imp_ventas", type="primary"):
        try:
            n = db.importar_csv(io.BytesIO(up.getvalue()), up.name)
        except Exception as e:  # noqa: BLE001
            st.error(f"Error de importación: {e}")
            return
        _refrescar()
        st.success(f"Se importaron {n} registros de ventas.")


@st.dialog("Confirmar")
def dialogo_cerrado(fs: str):
    st.write(f"¿Confirma que el local estuvo CERRADO el {fs}? Se registrará 0 en todos los productos para ese día.")
    a, b = st.columns(2)
    if a.button("Sí", key="neg_cerrado_si", type="primary", width="stretch"):
        n = db.marcar_dia_cerrado(fs)
        _refrescar()
        st.session_state["neg_msg"] = f"✅ Se registró el {fs} como día cerrado ({n} productos en 0)."
        st.rerun()
    if b.button("No", key="neg_cerrado_no", width="stretch"):
        st.rerun()


def tab_registro():
    estilo.titulo("📋  Registro de Ventas Diarias")
    st.caption("Anote cuántas unidades vendió de cada producto hoy. El precio lo puede editar directamente en la "
               "tabla.")
    _, faltantes = db.get_pivot_ventas()
    stats = db.contar_registros()
    if faltantes:
        ej = ", ".join(faltantes[:5]) + ("..." if len(faltantes) > 5 else "")
        st.warning(f"⚠️ Hay {len(faltantes)} día(s) sin ningún registro entre su primera y última venta ({ej}). Si de "
                   "verdad no abrió esos días, use 'Local cerrado hoy' en esa fecha; si se le olvidó registrar, "
                   "anótelo ahora si recuerda algo.")
    if stats["fecha_max"] and stats["fecha_max"] < date.today().isoformat():
        st.warning(f"📌 Su último registro fue el {stats['fecha_max']}. ¿Ya anotó las ventas de hoy?")
    if "neg_msg" in st.session_state:
        st.success(st.session_state.pop("neg_msg"))

    sub = st.tabs(["🗓️ Ventas del día", "📦 Productos (edición avanzada)", "🧂 Recetas"], key="neg_reg_sub",
                  on_change="rerun")
    with sub[0]:
        if getattr(sub[0], "open", True):
            _registro_dia()
    with sub[1]:
        if getattr(sub[1], "open", True):
            _productos()
    with sub[2]:
        if getattr(sub[2], "open", True):
            _recetas()


def _registro_dia():
    if "neg_fecha" not in st.session_state:
        st.session_state["neg_fecha"] = date.today()
    c = st.columns([2, 1, 1, 2, 2], vertical_alignment="bottom")
    if c[1].button("◀ Ayer", key="neg_ayer", width="stretch"):
        st.session_state["neg_fecha"] = st.session_state["neg_fecha"] - timedelta(days=1)
    if c[2].button("Hoy ▶", key="neg_hoy", width="stretch"):
        st.session_state["neg_fecha"] = date.today()
    fecha = c[0].date_input("Fecha:", key="neg_fecha", format="YYYY-MM-DD")
    fs = fecha.isoformat()
    if c[3].button("🚫 Local cerrado hoy", key="neg_cerrado", width="stretch"):
        _abrir(dialogo_cerrado, fs)
    guardar = c[4].button("💾 Guardar ventas y precios", key="neg_guardar", type="primary", width="stretch")

    c2 = st.columns([1, 2, 1.4, 1.6])
    if c2[0].button("➕ Nuevo producto", key="neg_nuevo", width="stretch"):
        _abrir(dialogo_nuevo_producto)
    if c2[1].button("📦 Importar catálogo (productos y precios)", key="neg_cat", width="stretch"):
        _abrir(dialogo_importar_catalogo)
    if c2[2].button("📂 Importar ventas (CSV)", key="neg_ventas_csv", width="stretch"):
        _abrir(dialogo_importar_ventas)

    # Retroalimentación rápida: lo que se pronosticó para este día
    seg = db.get_seguimiento(desde=fs, hasta=fs)
    if not seg.empty:
        lineas = [f"🔎 Esto fue lo que el sistema pronosticó para el {fs} (compare con lo que anote abajo):"]
        for _, r in seg.sort_values("producto").iterrows():
            real_txt = f"{int(r['real'])}" if pd.notna(r["real"]) else "aún sin registrar"
            lineas.append(f"• {r['producto']}: pronosticó {float(r['pronostico']):.1f} — venta real: {real_txt}")
        with st.container(key="vic_card_feedback"):
            with st.expander(lineas[0], expanded=False):
                st.markdown("  \n".join(lineas[1:]))

    s = db.contar_registros()
    txt = (f"📊 Tiene {s['productos']} productos registrados y {s['registros']} registros de ventas en "
           f"{s['dias']} días distintos")
    if s["fecha_min"]:
        txt += f"  (del {s['fecha_min']} al {s['fecha_max']})"
    st.caption(txt)

    prods = db.get_productos()
    if prods.empty:
        db.insertar_productos_default()
        prods = db.get_productos()
    vdf = db.get_ventas(desde=fs, hasta=fs)
    previas = dict(zip(vdf["producto"], vdf["unidades"]))
    obs = dict(zip(vdf["producto"], vdf["observacion"]))
    tabla = pd.DataFrame({
        "id": prods["id"].astype(int),
        "Categoría": prods["categoria"].fillna(""),
        "Producto": [n + ("  ⚠️" if p <= 0 else "") for n, p in zip(prods["nombre"], prods["precio"])],
        "Precio de venta (S/)": prods["precio"].astype(float),
        "Unidades vendidas": [int(previas.get(n, 0)) for n in prods["nombre"]],
        "Observación": [obs.get(n, "") or "" for n in prods["nombre"]],
    })
    sin_precio = prods.loc[prods["precio"] <= 0, "nombre"].tolist()
    if sin_precio:
        st.warning("⚠️ Estos productos no tienen precio y por eso el Motor de Pronóstico no podrá calcular ganancias "
                   "reales para ellos: " + ", ".join(sin_precio) + ".  Escriba el precio en la columna "
                   "correspondiente y presione 'Guardar ventas y precios', o use 'Importar catálogo'.")
    ed = st.data_editor(
        tabla, key=f"neg_editor_{fs}", hide_index=True, width="stretch", height=min(900, _alto(len(tabla))),
        disabled=["id", "Categoría", "Producto"], column_config={
            "id": None,
            "Precio de venta (S/)": st.column_config.NumberColumn(min_value=0.0, step=0.5, format="%.2f"),
            "Unidades vendidas": st.column_config.NumberColumn(min_value=0, step=1, format="%d"),
        })
    if guardar:
        ventas = {int(r["id"]): int(r["Unidades vendidas"] or 0) for _, r in ed.iterrows()}
        observ = {int(r["id"]): str(r["Observación"] or "") for _, r in ed.iterrows()}
        db.registrar_ventas_dia(fs, ventas, observ)
        for _, r in ed.iterrows():
            db.actualizar_producto(int(r["id"]), precio=float(r["Precio de venta (S/)"] or 0))
        _refrescar()
        st.session_state["neg_msg"] = f"✅ Ventas y precios del {fs} se guardaron correctamente."
        st.rerun()


def _productos():
    st.caption("Edite precio, margen, categoría, tipo y vida útil. Desmarque «Activo» para ocultar un producto.")
    prods = db.get_productos(solo_activos=False)
    t = pd.DataFrame({
        "id": prods["id"].astype(int), "Producto": prods["nombre"], "Categoría": prods["categoria"].fillna(""),
        "Precio (S/)": prods["precio"].astype(float),
        "Margen (%)": (prods["margen"].fillna(db.MARGEN_DEFECTO).astype(float) * 100).round(1),
        "Tipo": prods["tipo"].fillna("preparado"), "Vida útil (días)": prods["vida_util_dias"].fillna(1).astype(int),
        "Recuperable (0-1)": prods["recuperable"].fillna(0.5).astype(float),
        "Activo": prods["activo"].astype(int) == 1,
    })
    ed = st.data_editor(t, key="neg_prod_editor", hide_index=True, width="stretch", disabled=["id", "Producto"],
                        column_config={
                            "id": None,
                            "Tipo": st.column_config.SelectboxColumn(options=list(db.TIPOS_PRODUCTO)),
                            "Margen (%)": st.column_config.NumberColumn(min_value=0.0, max_value=100.0),
                            "Recuperable (0-1)": st.column_config.NumberColumn(min_value=0.0, max_value=1.0),
                            "Precio (S/)": st.column_config.NumberColumn(min_value=0.0, format="%.2f"),
                        })
    if st.button("💾 Guardar cambios de productos", key="neg_prod_guardar", type="primary"):
        for _, r in ed.iterrows():
            db.actualizar_producto(int(r["id"]), precio=float(r["Precio (S/)"]), margen=float(r["Margen (%)"]) / 100,
                                   categoria=str(r["Categoría"] or ""), tipo=str(r["Tipo"]),
                                   vida_util_dias=int(r["Vida útil (días)"]),
                                   recuperable=float(r["Recuperable (0-1)"]), activo=int(bool(r["Activo"])))
        _refrescar()
        st.success("✅ Productos actualizados.")


def _recetas():
    st.caption("Una fila por insumo de cada producto (ej. Pizza Americana Familiar · I001 · Harina · 250 · g). "
               "Se usan en el análisis completo para calcular la lista de compras.")
    prods = db.get_productos()
    rc = db.get_recetas()
    cols = ["producto", "insumo_id", "insumo_nombre", "cantidad_por_unidad", "unidad_medida", "costo_unitario_insumo"]
    t = rc[cols] if len(rc) else pd.DataFrame(columns=cols)
    ed = st.data_editor(t, key="neg_rec_editor", hide_index=True, width="stretch", num_rows="dynamic",
                        column_config={
                            "producto": st.column_config.SelectboxColumn("Producto", options=list(prods["nombre"]),
                                                                         required=True),
                            "insumo_id": st.column_config.TextColumn("Código insumo", required=True),
                            "insumo_nombre": st.column_config.TextColumn("Insumo", required=True),
                            "cantidad_por_unidad": st.column_config.NumberColumn("Cantidad por unidad", min_value=0.0),
                            "unidad_medida": st.column_config.SelectboxColumn(
                                "Unidad", options=["g", "kg", "ml", "L", "unidad"]),
                            "costo_unitario_insumo": st.column_config.NumberColumn("Costo por unidad de medida (S/)",
                                                                                   min_value=0.0, format="%.4f"),
                        })
    if st.button("💾 Guardar recetas", key="neg_rec_guardar", type="primary"):
        n = db.guardar_recetas(ed)
        st.success(f"✅ {n} fila(s) de receta guardadas.")


# ================================================================== 🔮 Motor de Pronóstico
def _calcular_producto(nombre: str) -> dict:
    prods = db.get_productos()
    pr = prods[prods["nombre"] == nombre].iloc[0]
    tipo = pr["tipo"] or "preparado"
    margen = float(pr["margen"] or db.MARGEN_DEFECTO)
    precio, recup = float(pr["precio"] or 0), float(pr["recuperable"] or 0)
    esp = set(db.get_fechas_especiales()["fecha"].tolist())
    pivot, falt_cal = db.get_pivot_ventas()
    y = pivot[nombre].values.astype(float) if (not pivot.empty and nombre in pivot.columns) else np.array([])
    base = dict(nombre=nombre, tipo=tipo, precio=precio, sin_precio=precio <= 0, margen=margen, recuperable=recup,
                categoria=pr["categoria"] or "")
    if len(y) < MIN_DIAS_HISTORIAL_PROPIO:
        base.update(nuevo=True, faltan=max(0, MIN_DIAS_HISTORIAL_PROPIO - len(y)),
                    apoyo=db.promedio_categoria_diario(base["categoria"], excluir_producto_id=int(pr["id"])))
        return base
    dates = pivot.index
    diag = diagnostico(y)
    res, preds = backtest(y, dates, min_train=MIN_DIAS_HISTORIAL_PROPIO, fechas_especiales=esp)
    ganador = elegir_ganador(res)
    nd = dates[-1] + timedelta(days=1)
    pron = pronosticar(y, dates, nd, ganador, res, esp) if ganador else 0.0
    tot, diarios = pronosticar_horizonte(y, dates, ganador, res, 7, esp) if ganador else (0.0, [])
    cr, *_ = razon_critica(precio, margen, recup)
    rmse = float(res[res.Modelo == ganador]["RMSE"].values[0]) if ganador and not res.empty else 1.0
    q = cantidad_optima(pron, rmse, cr)
    sim = simular_politica(y, preds.get(ganador, np.full(len(y), np.nan)), precio, margen, recup, cr, rmse)
    icono, texto = nivel_confianza(diag, 0 if res.empty else len(res))
    if ganador:
        db.guardar_pronostico(nd.date().isoformat(), int(pr["id"]), pron, q, ganador)
    base.update(nuevo=False, diag=diag, res=res, preds=preds, ganador=ganador, pron=pron, q=q, cr=cr, sim=sim,
                y=y, dates=dates, nd=nd, total_semana=tot, diarios=diarios, icono=icono, conf=texto,
                falt_mod=modelos_faltantes(diag["dias"]), falt_cal=falt_cal)
    return base


def tab_pronostico():
    estilo.titulo("🔮  ¿Cuánto vas a vender mañana?")
    st.caption("Elija un producto y el sistema probará varias formas de adivinar la demanda, quedándose con la que "
               "mejor funcionó en su negocio.")
    nombres = db.get_productos()["nombre"].tolist()
    if not nombres:
        st.warning("⚠️ No hay productos cargados todavía.")
        return
    c1, c2, c3 = st.columns([3, 1.3, 1], vertical_alignment="bottom")
    nombre = c1.selectbox("Producto:", nombres, key="neg_pron_prod")
    if c2.button("▶ Calcular este producto", key="neg_pron_uno", type="primary", width="stretch"):
        with st.spinner(f"⏳ Analizando {nombre}... esto toma unos segundos."):
            st.session_state["neg_pron"] = ("uno", _calcular_producto(nombre))
    if c3.button("📊 Calcular todo", key="neg_pron_todo", width="stretch"):
        st.session_state.pop("neg_recos", None)
        st.session_state["neg_pron"] = ("todos", None)
    st.caption("El margen de ganancia usado es el que tiene guardado cada producto (editable en 'Registro de Ventas' "
               "→ Nuevo producto / Productos).")
    est = st.session_state.get("neg_pron")
    if not est:
        st.caption("Seleccione un producto y presione Calcular, o use 'Calcular todo' para ver todos de una vez.")
        return
    if est[0] == "todos":
        resultados, _ = _recos()
        if not resultados:
            st.warning("⚠️ No hay productos cargados todavía.")
            return
        calc = [r for r in resultados if r["pronostico"] is not None]
        st.caption(f"✅ Recomendaciones listas para {len(calc)} de {len(resultados)} productos.")
        with st.container(key="vic_card_todos"):
            estilo.seccion("📊 Recomendación para todos los productos")
            st.markdown("'Pronóstico de venta' es lo que honestamente se espera vender mañana. 'Cantidad sugerida' "
                        "ya incluye un colchón de seguridad (usa el margen de cada producto).")
            st.dataframe(_tabla_recos(resultados, True), hide_index=True, width="stretch", height=600,
                         column_config=_CFG_RECOS)
        return
    r = est[1]
    st.caption(f"✅ Análisis de {r['nombre']} completado.")
    verbo = ACCION_TXT.get(r["tipo"], "preparar")
    with st.container(key="vic_card_pron"):
        if r["nuevo"]:
            _mostrar_nuevo(r, verbo)
        else:
            _mostrar_resultado(r, verbo)


def _mostrar_nuevo(r, verbo):
    estilo.seccion("🆕 Este producto es nuevo")
    st.markdown(f"**Todavía le faltan {r['faltan']} día(s) de historial propio de \"{r['nombre']}\" para un "
                "pronóstico confiable solo con sus datos.**")
    if r["apoyo"] is not None:
        cr, *_ = razon_critica(r["precio"], r["margen"], r["recuperable"])
        q = cantidad_optima(r["apoyo"], max(r["apoyo"] * 0.6, 0.5), cr)
        st.caption(f"Mientras tanto, usando el promedio de otros productos de su categoría (\"{r['categoria']}\"), "
                   f"se estima un punto de partida de {r['apoyo']:.1f} unidades/día.")
        estilo.caja("warning", f"🧪 Cantidad orientativa a {verbo} (estimado por categoría):", f"{q} unidades",
                    texto_oscuro=True)
    else:
        st.caption("No hay productos parecidos (misma categoría) con historial para apoyarse. Use su propio criterio "
                   "hasta tener más días registrados.")


def _mostrar_resultado(r, verbo):
    if r["falt_cal"]:
        f = r["falt_cal"]
        ej = ", ".join(f[:4]) + ("..." if len(f) > 4 else "")
        st.warning(f"⚠️ Hay {len(f)} día(s) sin ningún registro en su historial ({ej}). Esto puede afectar la "
                   "precisión del cálculo.")
    if r["sin_precio"]:
        st.error("⚠️  Este producto no tiene un precio registrado todavía.  \nLa cantidad sugerida sí es confiable, "
                 "pero la ganancia estimada en S/ no lo será hasta que le ponga un precio en 'Registro de Ventas'.")

    estilo.seccion(f"{r['icono']} ¿Qué tan confiable es este pronóstico?")
    st.markdown(r["conf"])

    estilo.seccion("🧭 ¿Cómo se vende este producto?")
    t, d = CLASE_SIMPLE.get(r["diag"]["clase"], ("", ""))
    st.markdown(f"**{t}**  \n{d}")
    st.caption(f"(Basado en {r['diag']['dias']} días de calendario registrados)")
    if r["falt_mod"]:
        partes = [f"{m} (le faltan {k} día(s))" for m, k in sorted(r["falt_mod"].items(), key=lambda x: x[1])]
        st.caption("Modelos que todavía no pueden probarse con el historial actual: " + "; ".join(partes[:4])
                   + ("..." if len(partes) > 4 else ""))

    estilo.seccion("🏆 Comparamos varias formas de adivinar la demanda")
    st.markdown("Probamos distintas maneras de calcular cuánto se va a vender. Esta tabla muestra cuánto se equivocó "
                "cada una en los días pasados (mientras más bajo, mejor).")
    res = r["res"]
    if not res.empty:
        t = pd.DataFrame({
            "Método": [("🥇 " if m == r["ganador"] else "") + m for m in res["Modelo"]],
            "Se equivocó en promedio (unidades)": res["MAE"].astype(float).round(1),
            "Error (%)": (res["wMAPE"].astype(float) * 100).round(0),
        })
        st.dataframe(t, hide_index=True, width="stretch", height=_alto(len(t)), column_config={
            "Se equivocó en promedio (unidades)": st.column_config.NumberColumn(format="%.1f unidades"),
            "Error (%)": st.column_config.NumberColumn(format="%d%%")})
        with st.expander("Ver todas las métricas de la competencia (avanzado)"):
            st.dataframe(res.round(3), hide_index=True, width="stretch")

    estilo.seccion("🎯 Pronóstico honesto para mañana")
    st.markdown(f"El método que mejor funcionó para \"{r['nombre']}\" fue: **{r['ganador']}**")
    estilo.caja("info", "📈 Mañana se espera vender aproximadamente:", f"{r['pron']:.1f} unidades")
    if r.get("total_semana") is not None:
        st.caption(f"📆 Sumando día a día, esta semana se espera vender en total aproximadamente "
                   f"{r['total_semana']:.0f} unidades (estimado, no exacto día por día).")

    estilo.seccion(f"✅ Cantidad sugerida a {verbo}")
    st.caption("Esta cantidad ya incluye un pequeño margen de seguridad (usa la ganancia del producto) para no "
               "quedarse sin stock si vende un poco más de lo esperado, sin sobre-producir de más.")
    estilo.caja("success", f"✅ Cantidad recomendada a {verbo}:", f"{r['q']} unidades")

    if not r["sin_precio"]:
        sim = r["sim"]
        estilo.seccion("💰 ¿Cuánto cambiaría si usa este método?")
        st.markdown("Comparamos, con los datos ya registrados, lo que hubiera pasado produciendo 'a ojo' (como se "
                    "hace normalmente) contra seguir la recomendación del sistema.")
        for label, key in [("📋 Como se produce habitualmente", "base"),
                           ("🤖 Con la recomendación del sistema", "modelo")]:
            s = sim[key]
            st.markdown(f"{label}:")
            st.caption(f"Ganancia estimada: S/ {s['u']:.0f}   |   Unidades que se botaron: {s['sobra']:.0f}   |   "
                       f"Clientes que se quedaron sin el producto: {s['falta']:.0f}")
        ah = sim["modelo"]["u"] - sim["base"]["u"]
        if ah >= 0:
            st.markdown(f"#### :green[📈 Con este método habría ganado S/ {ah:+.0f} más]")
        else:
            st.markdown(f"#### :red[📉 Con este método habría ganado S/ {abs(ah):.0f} menos]")

    estilo.seccion("📊 Así se vendió este producto en el tiempo")
    st.image(_png_serie(r), width="stretch")


def _png_serie(r) -> bytes:
    fig, ax = plt.subplots(figsize=(9, 3))
    ax.plot(r["dates"], r["y"], "o-", ms=3, color=COLORS["info"], label="Lo que realmente vendió")
    p = r["preds"].get(r["ganador"])
    if p is not None:
        m = ~np.isnan(p)
        ax.plot(r["dates"][m], p[m], "--", color=COLORS["warning"], label="Lo que el método hubiera dicho")
    ax.set_title(r["nombre"])
    ax.legend(fontsize=8)
    estilo.estilo_mpl(fig, ax)
    fig.autofmt_xdate()
    fig.tight_layout()
    return _png(fig)


# ================================================================== 📈 Seguimiento
@st.cache_data(show_spinner=False, max_entries=20)
def _png_error_semanal(semanas: tuple, valores: tuple) -> bytes:
    fig, ax = plt.subplots(figsize=(9, 2.4))
    ax.plot(list(semanas), list(valores), "o-", color=COLORS["warning"])
    ax.set_title("Error promedio por semana (unidades) — ¿va bajando?")
    estilo.estilo_mpl(fig, ax)
    fig.tight_layout()
    return _png(fig)


def tab_seguimiento():
    estilo.titulo("📈  Seguimiento: pronóstico vs. realidad")
    st.caption("Cada vez que el sistema calcula un pronóstico, lo guarda. Cuando ya registró la venta real de ese día, "
               "aquí puede comparar qué tan bien acertó y anotar la razón de los errores grandes. Si quiere ver esta "
               "comparación también para días pasados (no solo desde hoy), use '📜 Generar historial completo': solo "
               "cuenta como evidencia desde el día en que cada producto ya tenía suficiente historial para que el "
               "sistema pronosticara de verdad, no desde el primer día de ventas.")
    c1, c2, c3 = st.columns(3)
    c1.button("🔄 Actualizar", key="neg_seg_act", type="primary", width="stretch")  # rerun = recarga los datos
    if c3.button("📜 Generar historial completo", key="neg_seg_hist", width="stretch"):
        with st.spinner("Generando pronósticos de días pasados…"):
            n = backfill_historial_pronosticos()
        if n:
            st.success(f"📜 Se generaron {n} pronóstico(s) de días pasados. Ya puede ver abajo cómo le habría ido al "
                       "sistema en esas fechas.")
        else:
            st.info("📜 No había pronósticos nuevos para generar. Si un producto es muy nuevo, espere a que tenga más "
                    "días de ventas registradas.")
    df = db.get_seguimiento()
    for col in ("pronostico", "cantidad_sugerida", "real", "error", "error_abs", "error_pct"):
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if df.empty:
        with st.container(key="vic_card_seg_vacio"):
            st.caption("Todavía no hay pronósticos guardados. Use el 'Resumen del día' o 'Motor de Pronóstico' para "
                       "calcular; el sistema va guardando cada pronóstico automáticamente.")
        return
    c2.download_button("📄 Exportar a Excel", _bytes(exportar_seguimiento_excel, df), "seguimiento_victoriana.xlsx",
                       key="neg_seg_xlsx", width="stretch")
    con = df[df["real"].notna()]
    if not con.empty:
        ok = int((con["error_pct"].fillna(1) <= UMBRAL_ERROR_GRANDE).sum())
        st.caption(f"📊 De los últimos {len(con)} pronóstico(s) ya comparados con la venta real, {ok} "
                   f"({ok / len(con):.0%}) tuvieron un error razonable (≤{UMBRAL_ERROR_GRANDE:.0%}).")
    else:
        st.caption("Hay pronósticos guardados, pero ninguno tiene todavía su venta real registrada para comparar.")
    with st.container(key="vic_card_seg"):
        if len(con) >= 3:
            s = con.assign(semana=pd.to_datetime(con["fecha"]).dt.to_period("W").dt.start_time) \
                .groupby("semana")["error_abs"].mean()
            if len(s) >= 2:
                st.image(_png_error_semanal(tuple(s.index), tuple(s.values)), width="stretch")
        prods = sorted(df["producto"].unique())
        filtro = st.selectbox("Filtrar por producto", ["(todos)"] + prods, key="neg_seg_filtro")
        v = (df if filtro == "(todos)" else df[df["producto"] == filtro]).reset_index(drop=True)

        def _err(e, p):
            if pd.isna(e):
                return "—"
            return f"{e:+.1f}" + (f" ({p:.0%})" if pd.notna(p) else "")

        t = pd.DataFrame({
            "⚠️": ["🔴" if (pd.notna(e) and e > UMBRAL_ERROR_GRANDE) else "" for e in v["error_pct"]],
            "Fecha": v["fecha"], "Producto": v["producto"],
            "Pronosticado": [f"{x:.1f}" if pd.notna(x) else "—" for x in v["pronostico"]],
            "Venta real": [f"{int(x)}" if pd.notna(x) else "(sin registrar aún)" for x in v["real"]],
            "Error": [_err(e, p) for e, p in zip(v["error"], v["error_pct"])],
            "Modelo": v["modelo"].fillna("—"),
            "Observación": v["observacion"].fillna(""),
        })
        ed = st.data_editor(t, key=f"neg_seg_editor_{filtro}", hide_index=True, width="stretch", height=500,
                            disabled=[c for c in t.columns if c != "Observación"],
                            column_config={"⚠️": st.column_config.TextColumn(width="small"),
                                           "Observación": st.column_config.TextColumn(
                                               help="¿Por qué falló? (llovió, feriado...)")})
        st.caption("🔴 = error grande (más de 50 %). Escriba en «Observación» la razón y guarde.")
        if st.button("💾 Guardar observaciones", key="neg_seg_guardar"):
            ids = dict(zip(*db.get_productos(solo_activos=False)[["nombre", "id"]].values.T))
            n = 0
            for i in range(len(t)):
                if t.at[i, "Observación"] != ed.at[i, "Observación"] and pd.notna(v.at[i, "real"]) \
                        and v.at[i, "producto"] in ids:
                    db.registrar_venta(v.at[i, "fecha"], int(ids[v.at[i, "producto"]]), int(v.at[i, "real"]),
                                       observacion=str(ed.at[i, "Observación"]))
                    n += 1
            st.success(f"✅ {n} observación(es) guardadas.")


# ================================================================== 📚 Módulo Educativo
@st.dialog("📝 Ejemplo paso a paso", width="large")
def dialogo_ejemplo(modelo: str, producto: str):
    info = MODELOS_EDUCATIVOS[modelo]
    pivot, _ = db.get_pivot_ventas()
    if pivot.empty or producto not in pivot.columns:
        datos = np.array([5, 8, 3, 10, 7, 6, 9, 4, 8, 5], dtype=float)
        fechas = pd.date_range(end=pd.Timestamp(date.today()), periods=len(datos))
        producto = "Ejemplo"
    else:
        datos = pivot[producto].values.astype(float)[-14:]  # últimos 14 días, como en el original
        fechas = pivot.index[-14:]
    estilo.seccion(f"📝 Ejemplo paso a paso: {info['nombre']}")
    st.caption(f"Producto: {producto}  |  Datos: {list(datos[-7:].astype(int))}")
    try:
        pasos = info["ejemplo"](datos, fechas)
    except Exception as e:  # noqa: BLE001
        pasos = f"No se pudo generar el ejemplo: {e}"
    st.code(pasos, language=None, wrap_lines=True)


def tab_educativo():
    estilo.titulo("📚  Módulo Educativo")
    st.markdown("Aprenda cómo funciona cada modelo de pronóstico con explicaciones sencillas.")
    nombres = list(MODELOS_EDUCATIVOS.keys())
    pivot, _ = db.get_pivot_ventas()
    c1, c2, c3 = st.columns([2, 2, 1.3], vertical_alignment="bottom")
    modelo = c1.selectbox("Modelo:", nombres, key="neg_edu_modelo")
    productos = list(pivot.columns) if not pivot.empty else []
    prod = c2.selectbox("Producto para el ejemplo:", productos, key="neg_edu_prod") if productos else None
    info = MODELOS_EDUCATIVOS[modelo]
    if c3.button("Ver ejemplo con datos reales", key="neg_edu_btn", width="stretch") and "ejemplo" in info:
        _abrir(dialogo_ejemplo, modelo, prod or "")
    with st.container(key="vic_card_edu"):
        estilo.seccion(info["nombre"])
        st.markdown("**Fórmula:**")
        estilo.formula(info["formula"])
        st.markdown("**¿Cómo funciona? (explicación sencilla):**")
        st.markdown(info["explicacion"].replace("\n", "  \n"))


# ================================================================== 📊 Dashboard
@st.cache_data(show_spinner=False, max_entries=8)
def _pngs_dashboard(pivot: pd.DataFrame) -> list[bytes]:
    pngs = []
    fig, ax = plt.subplots(figsize=(9, 2.6))
    tot = pivot.sum(axis=1)
    ax.fill_between(tot.index, tot.values, alpha=0.3, color=COLORS["info"])
    ax.plot(tot.index, tot.values, color=COLORS["info"], lw=2)
    ax.set_title("Ventas totales por día (unidades)")
    estilo.estilo_mpl(fig, ax)
    fig.tight_layout()
    pngs.append(_png(fig))

    fig, ax = plt.subplots(figsize=(9, 2.6))
    top5 = pivot.sum().sort_values().tail(5)
    bars = ax.barh(top5.index, top5.values, color=COLORS["primary"])
    for br, v in zip(bars, top5.values):
        ax.text(br.get_width() + 0.3, br.get_y() + br.get_height() / 2, f"{int(v)}", va="center",
                color=COLORS["text"], fontsize=8)
    ax.set_title("Top 5 productos (total unidades)")
    estilo.estilo_mpl(fig, ax)
    fig.tight_layout()
    pngs.append(_png(fig))

    fig, ax = plt.subplots(figsize=(9, 2.6))
    dow = pivot.groupby(pivot.index.dayofweek).mean()
    nombres = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    colores = [COLORS["primary"], COLORS["info"], COLORS["success"], COLORS["warning"], COLORS["danger"]]
    x = np.arange(len(dow))
    w = 0.15
    for i, p in enumerate(pivot.sum().sort_values(ascending=False).head(5).index):
        ax.bar(x + i * w, dow[p], w, label=p[:12], color=colores[i % len(colores)], alpha=0.8)
    ax.set_xticks(x + w * 2)
    ax.set_xticklabels([nombres[i] for i in dow.index])
    ax.set_title("Promedio por día de la semana (Top 5)")
    ax.legend(fontsize=7)
    estilo.estilo_mpl(fig, ax)
    fig.tight_layout()
    pngs.append(_png(fig))
    return pngs


def tab_dashboard():
    estilo.titulo("📊  Dashboard")
    st.button("🔄 Actualizar", key="neg_dash_act")  # rerun = vuelve a leer la base de datos
    s = db.contar_registros()
    estilo.kpis([("Productos", str(s["productos"]), "🍗"), ("Registros", str(s["registros"]), "📋"),
                 ("Días", str(s["dias"]), "📅")])
    pivot, _ = db.get_pivot_ventas()
    if pivot.empty:
        st.caption("No hay datos de ventas para graficar.")
        return
    for png in _pngs_dashboard(pivot):
        st.image(png, width="stretch")
    estilo.seccion("Clasificación de demanda por producto")
    filas = []
    for p in pivot.columns:
        d = diagnostico(pivot[p].values.astype(float))
        filas.append({"Producto": p, "Clase": d["clase"],
                      "ADI": round(d["adi"], 2) if np.isfinite(d["adi"]) else None,
                      "CV²": None if d["cv2"] != d["cv2"] else round(d["cv2"], 3),
                      "% cero": round(d["pct_cero"] * 100)})
    st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch", height=_alto(len(filas)),
                 column_config={"% cero": st.column_config.NumberColumn(format="%d%%")})


# ================================================================== ⚙️ Configuración
def tab_configuracion():
    estilo.titulo("⚙️  Configuración")

    with st.container(key="vic_card_resp"):
        estilo.seccion("💾 Copia de seguridad")
        d = db.dias_desde_ultimo_respaldo()
        if d is None:
            st.caption("⚠️ Todavía no ha hecho ninguna copia de seguridad.")
        elif d == 0:
            st.caption("✅ Último respaldo: hoy.")
        elif d > 14:
            st.markdown(f":orange[Último respaldo: hace {d} día(s).]")
        else:
            st.caption(f"Último respaldo: hace {d} día(s).")
        st.caption("La copia es un Excel con todas las tablas: sirve para guardar sus datos a salvo o pasarlos a otra "
                   "computadora (Restaurar).")
        a, b = st.columns(2)
        _boton_respaldo(a, "neg_resp_prep", "Hacer copia de seguridad ahora")
        up = b.file_uploader("Restaurar desde una copia (.xlsx)", type=["xlsx"], key="neg_resp_up")
        if up is not None:
            b.warning("Restaurar REEMPLAZA todos los datos actuales por los de la copia.")
            if b.button("Restaurar ahora", key="neg_resp_rest", type="primary"):
                n = db.restaurar_respaldo(up.getvalue())
                _refrescar()
                b.success("✅ Restaurado: " + ", ".join(f"{k}: {v}" for k, v in n.items()))

    with st.container(key="vic_card_cmd"):
        estilo.seccion("🧾 Comanda para la cocina")
        st.caption("Genera una hoja simple en PDF, lista para imprimir y pegar en la cocina, con lo que toca preparar "
                   "y comprar hoy.")
        if st.button("Generar comanda (PDF)", key="neg_cmd_gen"):
            res, _ = calcular_recomendaciones_todas(guardar_historial=False)
            st.session_state["neg_comanda"] = _bytes(generar_comanda_pdf, res)
        if st.session_state.get("neg_comanda"):
            st.download_button("📥 Descargar comanda", st.session_state["neg_comanda"],
                               f"comanda_{date.today().isoformat()}.pdf", key="neg_cmd_dl")

    with st.container(key="vic_card_cal"):
        estilo.seccion("📅 Calendario de feriados y fechas especiales")
        st.caption("Ya incluye los feriados oficiales del Perú 2026 y fechas comerciales típicas de comida. Estos días "
                   "no se mezclan con el promedio normal del día de la semana, y se le avisa cuando se acerca uno. "
                   "Puede agregar sus propias fechas (aniversario del local, eventos, etc.).")
        with st.form("neg_fecha_form", clear_on_submit=True, border=False):
            a, b, c = st.columns([1, 2, 1], vertical_alignment="bottom")
            f = a.date_input("Fecha (AAAA-MM-DD):", value=None, format="YYYY-MM-DD")
            n = b.text_input("Nombre:")
            if c.form_submit_button("➕ Agregar", type="primary", width="stretch"):
                if f is None:
                    st.error("Formato de fecha inválido. Use AAAA-MM-DD")
                elif not n.strip():
                    st.warning("Escriba un nombre para la fecha.")
                else:
                    db.agregar_fecha_especial(f.isoformat(), n.strip(), origen="manual")
                    st.rerun()
        fe = db.get_fechas_especiales()
        hoy = date.today().isoformat()
        with st.container(height=380, key="vic_lista_fechas"):
            for _, row in fe.iterrows():
                x, y, z, w = st.columns([1.2, 3, 2, 0.6], vertical_alignment="center")
                pasada = row["fecha"] < hoy
                fmt = (lambda s: f":gray[{s}]") if pasada else (lambda s: s)
                x.markdown(fmt(row["fecha"]))
                y.markdown(fmt(row["nombre"]))
                z.markdown(f":gray[{ORIGEN_TXT.get(row['origen'], row['origen'])}]")
                if w.button("🗑", key=f"neg_fe_del_{row['fecha']}", help="Eliminar esta fecha"):
                    db.eliminar_fecha_especial(row["fecha"])
                    st.rerun()


PANTALLAS = dict(zip(TABS, [tab_resumen, tab_registro, tab_pronostico, tab_seguimiento, tab_educativo,
                            tab_dashboard, tab_configuracion]))
