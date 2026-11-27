"""VICTORA v3 — interfaz Streamlit (punto de entrada).

Ejecutar:  streamlit run app.py

Rendimiento:
  * Un solo st.set_page_config, antes de cualquier otro comando.
  * El pipeline corre UNA vez (botón «Ejecutar análisis») y guarda todo en st.session_state.
  * Solo se renderiza la pestaña ABIERTA (st.tabs con on_change="rerun" + .open): Streamlit
    ejecuta por defecto el cuerpo de todas las pestañas en cada interacción.
  * Los selectores de producto viven en st.fragment: cambiar de producto no reejecuta la pestaña.
  * Gráficos y tablas Excel se cachean (cache_data) y se muestran como PNG ya renderizado.
"""
import streamlit as st

MODOS = ["🏪 Mi negocio (día a día)", "🔬 Análisis completo y artículo"]
if st.session_state.pop("_abrir_decision", False):
    st.session_state["modo"] = MODOS[1]
    st.session_state["tabs_main"] = "✅ Decisión"  # abre la pestaña de Decisión al terminar el análisis
if st.session_state.get("modo") not in MODOS:
    st.session_state["modo"] = MODOS[0]
ES_NEGOCIO = st.session_state["modo"] == MODOS[0]
# «Mi negocio» conserva la identidad de la app de escritorio La Victoriana; el análisis, la de VICTORA.
if ES_NEGOCIO:
    st.set_page_config(page_title="La Victoriana – Sistema de Pronóstico de Demanda", page_icon="🍗", layout="wide")
else:
    st.set_page_config(page_title="VICTORA — ¿Cuánto producir mañana?", page_icon="🥐", layout="wide")

import gc  # noqa: E402
import io  # noqa: E402
import os  # noqa: E402
import sys  # noqa: E402
import tempfile  # noqa: E402
import traceback  # noqa: E402

import pandas as pd  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from victora import __version__  # noqa: E402
from victora.config import COLCHON_P0, CONTEXTO_DEFECTO, HOJAS_REPORTE  # noqa: E402
from victora.decision import costos  # noqa: E402
from victora.utils import fmt_num, fmt_s  # noqa: E402
from victora import estilo, tutorial  # noqa: E402

estilo.inyectar_css()

TMP_DIR = os.path.join(tempfile.gettempdir(), "victora_tmp")
TABS = ["🏠 El Problema", "📤 Cargar Datos", "✅ Decisión", "💰 Impacto", "📊 Análisis", "📑 Reportes",
        "📖 Metodología"]


# =============================================================== caché
@st.cache_data(show_spinner=False)
def c_plantilla_vacia():
    from victora.plantilla import plantilla_vacia
    return plantilla_vacia()


@st.cache_data(show_spinner=False)
def c_plantilla_ejemplo():
    from victora.plantilla import plantilla_ejemplo
    return plantilla_ejemplo()


@st.cache_data(show_spinner=False)
def c_plantilla_recetas():
    from victora.plantilla import plantilla_recetas
    return plantilla_recetas()


@st.cache_data(show_spinner=False, max_entries=5)
def c_validar(contenido: bytes):
    from victora.validador import validar
    r = validar(contenido)
    return r.semaforo, r.tabla(), r.datos, r.huecos


@st.cache_data(show_spinner=False, max_entries=3)
def c_pipeline(contenido: bytes, huecos_key: tuple, colchon: float, ctx_key: tuple, _progreso=None):
    from victora.pipeline import ejecutar
    _, _, datos, _ = c_validar(contenido)
    return ejecutar(datos, dict(huecos_key), colchon, progreso=_progreso, contexto=dict(ctx_key))


@st.cache_data(show_spinner=False, max_entries=400)
def c_png(tipo: str, clave: str, pid: str, _R) -> bytes:
    """Gráfico renderizado a PNG (150 dpi) y cacheado: cambiar de pestaña no lo vuelve a dibujar."""
    import matplotlib.pyplot as plt

    from victora import graficos as gr
    from victora.utils import fig_a_png
    R = _R
    nom = R["nombres"].get(pid, pid)
    f = {
        "serie": lambda: gr.serie(R["m"], pid, nom),
        "dia": lambda: gr.dia_semana(R["perfil"], pid, nom),
        "pron": lambda: gr.real_vs_pronostico(R["m"], R["sel"][pid], pid, nom, R["plan"]),
        "err": lambda: gr.errores_modelos(R["sel"][pid]["ranking"], nom),
        "costos": lambda: gr.costo_politicas(R["res_pol"]),
        "mf": lambda: gr.merma_faltante(R["res_pp"], R["nombres"]),
        "sens": lambda: gr.sensibilidad(R["sens_col"]),
        "abc": lambda: gr.abc(R["clasif"], R["nombres"]),
        "heat": lambda: gr.heatmap(R["corr"], R["nombres"]),
        "vict": lambda: gr.victorias(R["ganadores"]),
    }[tipo]()
    png = fig_a_png(f, dpi=150)
    plt.close(f)
    return png


@st.cache_data(show_spinner=False, max_entries=300)
def c_xlsx(clave: str, nombre: str, _df) -> bytes:
    buf = io.BytesIO()
    hoja = nombre[:31]
    with pd.ExcelWriter(buf, engine="xlsxwriter") as xw:
        _df.to_excel(xw, sheet_name=hoja, index=False)
        ws = xw.sheets[hoja]
        ws.freeze_panes(1, 0)
        for j, c in enumerate(_df.columns):
            ws.set_column(j, j, max(12, min(40, len(str(c)) + 4)))
    return buf.getvalue()


@st.cache_data(show_spinner=False, max_entries=2)
def c_zip_producto(clave: str, _R) -> bytes:
    from victora.reporte_figuras import zip_figuras_producto
    return zip_figuras_producto(_R)


def clave_R() -> str:
    R = st.session_state["R"]
    return f"{R['hash']}|{R['colchon']}|{R['tratamiento_huecos']}|{R['contexto']}"


# =============================================================== helpers de UI
def dl_tabla(df: pd.DataFrame, nombre: str, key: str):
    st.download_button("📥 Descargar esta tabla (.xlsx)", c_xlsx(clave_R() + nombre, nombre, df), f"{nombre}.xlsx",
                       key=f"dlx_{key}")


def mostrar_fig(tipo: str, nombre: str, key: str, pid: str = ""):
    R = st.session_state["R"]
    png = c_png(tipo, clave_R(), pid, R)
    st.image(png, width="stretch")
    st.download_button("📥 Descargar este gráfico (.png)", png, f"{nombre}.png", mime="image/png", key=f"dlp_{key}")


def tabla(df: pd.DataFrame, nombre: str, key: str, redondeo: int = 2, altura: int | None = None):
    st.dataframe(df.round(redondeo), hide_index=True, width="stretch", height=altura)
    dl_tabla(df.round(redondeo), nombre, key)


def sin_datos():
    st.info("Aún no hay resultados. Carga tu Excel en **📤 Cargar Datos** o pulsa **🧪 Probar con datos de "
            "demostración** en **🏠 El Problema**.")


def selector_producto(key: str):
    R = st.session_state["R"]
    return st.selectbox("Producto", list(R["m"].columns), key=key,
                        format_func=lambda p: f"{p} — {R['nombres'][p]}")


def etiqueta_fuente(R) -> str:
    return "⚠️ SIMULADO" if R["fuente"] == "SIMULADO" else "✅ REAL"


# =============================================================== reset
def restablecer():
    st.cache_data.clear()
    st.session_state.clear()
    if os.path.isdir(TMP_DIR):
        for f in os.listdir(TMP_DIR):
            try:
                os.remove(os.path.join(TMP_DIR, f))
            except OSError:
                pass
    gc.collect()
    st.session_state["_reset_ok"] = True


@st.dialog("🗑️ Restablecer todo")
def dialogo_reset():
    st.warning("¿Estás seguro? Se eliminarán TODOS los datos cargados, resultados y reportes. "
               "La app volverá al estado inicial.")
    c1, c2 = st.columns(2)
    if c1.button("Sí, borrar todo", type="primary", key="reset_si", width="stretch"):
        restablecer()
        st.rerun()
    if c2.button("Cancelar", key="reset_no", width="stretch"):
        st.session_state["pedir_reset"] = False
        st.rerun()


def correr(contenido: bytes, huecos: dict, demo: bool = False):
    """Lanza el pipeline completo con barra de progreso y guarda el resultado en session_state."""
    barra = st.progress(0.0, text="Iniciando…")
    ctx = tuple(sorted({**CONTEXTO_DEFECTO, **st.session_state.get("contexto", {})}.items()))
    R = c_pipeline(contenido, tuple(sorted((str(k), v) for k, v in huecos.items())),
                   st.session_state.get("colchon", COLCHON_P0), ctx,
                   _progreso=lambda f, t: barra.progress(min(f, 1.0), text=t))
    st.session_state["R"] = R
    st.session_state["es_demo"] = demo
    st.session_state["_abrir_decision"] = True
    st.session_state["_aviso"] = ("Datos de demostración (FICTICIOS) analizados." if demo else "Análisis completo.") \
        + f" Listo en {R['segundos']:.1f} s."
    st.rerun()


# =============================================================== sidebar
from victora import negocio_ui as neg  # noqa: E402

neg.iniciar_bd()


def _ayuda_lateral():
    st.markdown("**Ayuda**")
    h1, h2 = st.columns(2)
    if h1.button("Ver tutorial", icon=":material/school:", key="tuto_btn", width="stretch"):
        tutorial.abrir()
    h2.download_button("Manual", tutorial.manual_docx(), "Manual_VICTORA.docx", icon=":material/menu_book:",
                       key="manual_dl", width="stretch", help="Manual detallado de usuario (Word)",
                       mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


PANTALLA_NEG = None
if ES_NEGOCIO:
    with st.sidebar:
        PANTALLA_NEG = neg.barra_lateral(__version__)
        _ayuda_lateral()
        st.divider()
        estilo.pie_victoriana(__version__)
else:
    with st.sidebar:
        estilo.marca_lateral(__version__)
        st.caption("Pronóstico de demanda y decisión óptima de producción para comida perecible.")
        R0 = st.session_state.get("R")
        if R0:
            st.success(f"Análisis listo: {R0['n_productos']} productos × {R0['n_dias']} días ({R0['segundos']:.1f} s)")
            if st.session_state.get("es_demo"):
                st.info("Usando datos de DEMOSTRACIÓN (ficticios).")
        else:
            st.info("Sin datos cargados.")
        _ayuda_lateral()
        st.divider()
        if st.button("🗑️ Restablecer todo", key="reset_sidebar", type="primary", width="stretch"):
            st.session_state["pedir_reset"] = True
        if st.session_state.get("pedir_reset"):
            st.session_state["tuto_abierto"] = False  # un solo diálogo por ejecución
            dialogo_reset()
        st.caption("«Restablecer todo» limpia el análisis de esta sesión; no borra las ventas registradas en la "
                   "base de datos.")


if "_aviso" in st.session_state:
    st.toast(st.session_state.pop("_aviso"), icon="✅")
if st.session_state.pop("_reset_ok", False):
    st.toast("La app se restableció por completo.", icon="🗑️")


# =============================================================== 1. El problema
def tab_problema():
    st.header("El problema")
    ej = costos(0.30, 55)
    st.markdown(
        "### Si produces de más, pierdes en merma. Si produces de menos, pierdes ventas.\n"
        "**VICTORA te dice cuánto producir de cada producto.**")
    st.markdown(
        f"Ejemplo: un pan cuesta S/ {fmt_num(ej['c'])} y se vende a S/ 0,30. "
        f"**Produces 100 → vendes 70 → pierdes {fmt_s(30 * ej['c'])} en merma.** "
        f"**Produces 50 → la demanda era 70 → dejas de ganar {fmt_s(20 * ej['Cu'])}.**")
    estilo.pasos([("Sube datos", "Tu Excel de ventas, precios y recetas"),
                  ("Analiza", "Pronóstico y validación automática por producto"),
                  ("Decide", "Cuánto producir y qué insumos comprar"),
                  ("Exporta", "Reporte, figuras y textos listos para tu artículo")])
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.download_button("📥 Descargar plantilla de datos", c_plantilla_vacia(), "Plantilla_VICTORA_vacia.xlsx",
                       key="dl_plant_inicio", width="stretch")
    c2.download_button("📥 Descargar guía de recetas", c_plantilla_recetas(), "Plantilla_Recetas_Guia.xlsx",
                       key="dl_recetas_inicio", width="stretch")
    if c3.button("🧪 Probar con datos de demostración", key="demo_btn", type="primary", width="stretch"):
        b = c_plantilla_ejemplo()
        st.session_state["contenido"] = b
        correr(b, {}, demo=True)
    c4, c5 = st.columns([1, 2])
    c4.download_button("📥 Plantilla de ejemplo (ficticia)", c_plantilla_ejemplo(), "Plantilla_VICTORA_ejemplo.xlsx",
                       key="dl_plant_ej_inicio", width="stretch")
    if c5.button("🗑️ Restablecer todo", key="reset_inicio", type="primary", width="stretch"):
        st.session_state["pedir_reset"] = True
        st.rerun()
    R = st.session_state.get("R")
    if R:
        rp = R["res_pol"].set_index("politica")
        st.success(f"Análisis listo. Ve a la pestaña **✅ Decisión**. Ahorro estimado: "
                   f"{fmt_s(R['boot']['ahorro_S/'])} ({fmt_num(R['boot']['ahorro_pct'], 1)} %) {etiqueta_fuente(R)}. "
                   f"Costo sin VICTORA {fmt_s(rp.loc['P0', 'costo_total'])} → con VICTORA {fmt_s(rp.loc['P4', 'costo_total'])}.")


# =============================================================== 2. Cargar datos
def tab_cargar():
    st.header("📤 Cargar datos")
    c1, c2, c3 = st.columns(3)
    c1.download_button("📥 Plantilla vacía", c_plantilla_vacia(), "Plantilla_VICTORA_vacia.xlsx",
                       key="dl_plant_vacia", width="stretch")
    c2.download_button("📥 Plantilla de ejemplo (ficticia)", c_plantilla_ejemplo(), "Plantilla_VICTORA_ejemplo.xlsx",
                       key="dl_plant_ej", width="stretch")
    c3.download_button("📥 Guía de recetas", c_plantilla_recetas(), "Plantilla_Recetas_Guia.xlsx",
                       key="dl_recetas_cargar", width="stretch")
    st.markdown("**Opción A — usar lo registrado en 🏪 Mi negocio** (ventas, productos y recetas de la base de datos):")
    if st.button("📋 Usar mis ventas registradas", key="usar_bd", type="primary"):
        from victora.nucleo.database import datos_para_analisis
        from victora.plantilla import _escribir
        st.session_state["contenido"] = _escribir(datos_para_analisis(), ejemplo=False)
        st.session_state["_nombre_subido"] = ("__bd__", 0)
        st.session_state["es_demo"] = False
    st.markdown("**Opción B — subir un Excel:**")
    up = st.file_uploader("Sube tu archivo Excel (.xlsx) basado en la plantilla", type=["xlsx"],
                          key="file_uploader_main")
    if up is not None and st.session_state.get("_nombre_subido") != (up.name, up.size):
        st.session_state["contenido"] = up.getvalue()
        st.session_state["_nombre_subido"] = (up.name, up.size)
        st.session_state["es_demo"] = False
    contenido = st.session_state.get("contenido")
    if not contenido:
        st.info("Sube tu Excel o usa la plantilla de ejemplo para ver cómo funciona.")
        return
    semaf, tb, datos, huecos = c_validar(contenido)
    icon = {"verde": "🟢", "amarillo": "🟡", "rojo": "🔴"}[semaf]
    msg = {"verde": "Todo correcto: puedes continuar.",
           "amarillo": "Puedes continuar, pero revisa las advertencias.",
           "rojo": "Hay errores que debes corregir en tu Excel antes de continuar."}[semaf]
    getattr(st, {"verde": "success", "amarillo": "warning", "rojo": "error"}[semaf])(f"{icon} {msg}")
    if semaf != "rojo":
        v = datos["Ventas"]
        st.markdown(f"**{len(datos['Productos'])} productos, {v['fecha'].nunique()} días de datos, del "
                    f"{v['fecha'].min():%d/%m/%Y} al {v['fecha'].max():%d/%m/%Y}.**")
        sin_rec = sorted(set(datos["Productos"]["producto_id"]) - set(datos["Recetas"]["producto_id"]))
        if sin_rec:
            st.warning(f"⚠️ No se cargaron recetas para {len(sin_rec)} productos. El plan de insumos estará "
                       "incompleto. Descarga la guía de recetas para completarlas.")
    if len(tb):
        st.dataframe(tb, hide_index=True, width="stretch", height=min(400, 40 + 35 * len(tb)))
    trat = {}
    if huecos and semaf != "rojo":
        st.markdown("**Días sin registro:** indica cómo tratar cada uno.")
        for d in huecos:
            trat[d] = st.radio(f"{d:%A %d/%m/%Y}", ["cero", "cerrado"], horizontal=True, key=f"hueco_{d:%Y%m%d}",
                               format_func=lambda x: "Venta cero" if x == "cero" else "Local cerrado")
    with st.expander("⚙️ Configuración del análisis y de los textos"):
        st.session_state["colchon"] = st.slider("Colchón de la práctica habitual simulada (P0), %", 0, 50,
                                                int(COLCHON_P0 * 100), 5, key="colchon_slider") / 100
        ctx = st.session_state.setdefault("contexto", dict(CONTEXTO_DEFECTO))
        ctx["caso"] = st.text_input("Nombre del negocio (caso de estudio)", ctx["caso"], key="ctx_caso")
        ctx["ciudad"] = st.text_input("Ubicación", ctx["ciudad"], key="ctx_ciudad")
        ctx["software"] = st.text_input("Nombre del software", ctx["software"], key="ctx_soft")
    if semaf != "rojo" and st.button("▶️ Ejecutar análisis", type="primary", key="run_btn"):
        correr(contenido, trat, demo=st.session_state.get("es_demo", False))


# =============================================================== 3. Decisión
@st.fragment
def frag_decision_producto():
    R = st.session_state["R"]
    pid = selector_producto("sel_decision")
    mostrar_fig("pron", f"pronostico_{pid}", f"dec_{pid}", pid)
    pl = R["plan"][R["plan"]["producto_id"] == pid]
    t = pl[["fecha", "pronostico", "razon_critica", "producir", "intervalo_10", "intervalo_90"]].copy()
    t["fecha"] = t["fecha"].dt.strftime("%a %d/%m")
    t.columns = ["Día", "Pronóstico", "Razón crítica", "Producir", "Mínimo", "Máximo"]
    st.dataframe(t.round(2), hide_index=True, width="stretch")


def tab_decision():
    R = st.session_state.get("R")
    if not R:
        st.header("✅ Decisión: qué producir mañana")
        sin_datos()
        return
    pl = R["plan"]
    primer = pl["fecha"].min()
    man = pl[pl["fecha"] == primer].sort_values("nombre")
    st.header("✅ Qué producir mañana")
    st.caption(f"Plan para el {primer:%A %d/%m/%Y} (primer día después de tus datos). Cantidad recomendada, con "
               "mínimo y máximo razonables, según el modelo de cada producto.")
    panel_gerencial(R)
    k = st.columns(4)
    k[0].metric("Productos analizados", R["n_productos"], border=True)
    k[1].metric("Unidades a producir mañana", f"{int(man['producir'].sum()):,}".replace(",", "."), border=True)
    k[2].metric("Horizonte del plan", "7 días", border=True)
    k[3].metric(f"Ahorro vs. sin pronóstico ({etiqueta_fuente(R)})",
                fmt_s(R["boot"]["ahorro_S/"]), f"{fmt_num(R['boot']['ahorro_pct'], 1)} %", border=True)
    d = man[["nombre", "producir", "intervalo_10", "intervalo_90", "modelo"]].rename(columns={
        "nombre": "Producto", "producir": "Producir mañana", "intervalo_10": "Mínimo", "intervalo_90": "Máximo",
        "modelo": "Modelo usado"})
    st.dataframe(d, hide_index=True, width="stretch", height=min(700, 40 + 35 * len(d)),
                 column_config={"Producir mañana": st.column_config.NumberColumn("Producir mañana", format="%d unid.",
                                                                                 help="Cantidad óptima Q* (newsvendor)")})
    c1, c2 = st.columns(2)
    c1.download_button("📥 Descargar Plan de Producción (.xlsx)", R["excel_plan"], "Plan_Produccion_Semana.xlsx",
                       type="primary", key="dl_plan_decision", width="stretch")
    c2.download_button("📥 Descargar esta tabla (.xlsx)", c_xlsx(clave_R() + "manana", "Produccion_manana", d),
                       "Produccion_manana.xlsx", key="dl_manana", width="stretch")
    if R["n_dias"] < 28:
        st.warning(f"Estudio piloto: solo {R['n_dias']} días de datos. Las cantidades son orientativas; mejoran "
                   "al ir cargando más días.")
    st.divider()
    st.subheader("Detalle")
    frag_decision_producto()
    st.markdown("**Plan completo de 7 días (unidades a producir)**")
    p2 = pl.copy()
    p2["dia"] = p2["fecha"].dt.strftime("%a %d/%m")
    orden = list(dict.fromkeys(p2["dia"]))
    t = p2.pivot_table(index="nombre", columns="dia", values="producir", aggfunc="sum")[orden]
    t["Total"] = t.sum(axis=1)
    t = t.reset_index().rename(columns={"nombre": "Producto"})
    tabla(t, "Plan_7_dias", "plan7", 0, altura=min(600, 40 + 35 * len(t)))
    st.markdown("**🛒 Insumos a comprar para la semana**")
    if len(R["insumos_sem"]):
        ins = R["insumos_sem"][["insumo_nombre", "comprar", "unidad", "costo_estimado", "usado_en"]]
        ins.columns = ["Insumo", "Comprar", "Unidad", "Costo estimado S/", "Usado en"]
        tabla(ins, "Lista_compras", "compras", 2)
    else:
        st.info("No hay recetas registradas: descarga la guía de recetas para completarlas.")


def panel_gerencial(R):
    """Veredicto claro para la gerencia + semáforo por producto (dónde actuar primero)."""
    b = R["boot"]
    rp = R["res_pol"].set_index("politica")
    c0, c4 = rp.loc["P0", "costo_total"], rp.loc["P4", "costo_total"]
    if b["IC95_S/_inf"] > 0:
        estilo.veredicto("ok", "Decisión recomendada", "Adoptar VICTORA para planificar la producción",
                         f"Reduce el costo de merma + ventas perdidas de {fmt_s(c0)} a {fmt_s(c4)} "
                         f"({fmt_num(b['ahorro_pct'], 1)} %). El ahorro es estadísticamente sólido "
                         f"(IC 95 %: {fmt_s(b['IC95_S/_inf'])} a {fmt_s(b['IC95_S/_sup'])}).")
    elif b["ahorro_S/"] > 0:
        estilo.veredicto("med", "Decisión recomendada", "Adoptar VICTORA en piloto y seguir registrando ventas",
                         f"Ahorro estimado {fmt_s(b['ahorro_S/'])} ({fmt_num(b['ahorro_pct'], 1)} %), pero con "
                         f"{R['n_dias']} días el intervalo de confianza incluye cero "
                         f"({fmt_s(b['IC95_S/_inf'])} a {fmt_s(b['IC95_S/_sup'])}). Con más días la evidencia se fortalece.")
    else:
        estilo.veredicto("no", "Decisión recomendada", "Mantener la práctica actual por ahora",
                         f"Con los datos actuales VICTORA no mejora el costo ({fmt_s(c0)} → {fmt_s(c4)}). "
                         "Revise precios/costos y cargue más días.")
    pp = R["res_pp"].pivot_table(index="producto_id", columns="politica", values="costo_total", aggfunc="sum")
    if not {"P0", "P4"} <= set(pp.columns):
        return
    t = pd.DataFrame({"Producto": pp.index.map(lambda p: R["nombres"].get(p, p)),
                      "Costo actual S/": pp["P0"].values, "Costo con VICTORA S/": pp["P4"].values})
    t["Ahorro S/"] = t["Costo actual S/"] - t["Costo con VICTORA S/"]
    t["Ahorro %"] = 100 * t["Ahorro S/"] / t["Costo actual S/"].where(t["Costo actual S/"] > 0)
    t["Acción"] = t["Ahorro S/"].map(lambda a: "🟢 Aplicar Q* de VICTORA" if a > 0.5 else
                                     ("🔴 Mantener cantidad actual" if a < -0.5 else "🟡 Indiferente"))
    t = t.sort_values("Ahorro S/", ascending=False)
    with st.expander(":material/insights: Dónde actuar primero (ahorro por producto)", expanded=True):
        a, b2, c = st.columns(3)
        a.metric("Productos donde conviene VICTORA", int((t["Ahorro S/"] > 0.5).sum()), border=True)
        b2.metric("Mayor ahorro individual", fmt_s(t["Ahorro S/"].max()), t["Producto"].iloc[0], border=True, delta_arrow="off",
                  delta_color="off")
        c.metric("Productos a mantener como están", int((t["Ahorro S/"] < -0.5).sum()), border=True)
        st.dataframe(t, hide_index=True, width="stretch", height=min(420, 40 + 35 * len(t)),
                     column_config={
                         "Costo actual S/": st.column_config.NumberColumn(format="S/ %.2f"),
                         "Costo con VICTORA S/": st.column_config.NumberColumn(format="S/ %.2f"),
                         "Ahorro S/": st.column_config.ProgressColumn(
                             format="S/ %.2f", min_value=float(min(0, t["Ahorro S/"].min())),
                             max_value=float(max(1, t["Ahorro S/"].max()))),
                         "Ahorro %": st.column_config.NumberColumn(format="%.1f %%")})
        st.caption("Costo = merma (lo producido que no se vende) + margen perdido (ventas que faltaron), "
                   "en el periodo de prueba. «Costo actual» = política P0 del negocio.")


# =============================================================== 4. Impacto
def tab_impacto():
    R = st.session_state.get("R")
    st.header("💰 Impacto: la evidencia del problema")
    if not R:
        sin_datos()
        return
    rp = R["res_pol"].set_index("politica")
    b = R["boot"]
    k = st.columns(3)
    k[0].metric("Sin VICTORA (P0)", fmt_s(rp.loc["P0", "costo_total"]))
    k[1].metric("Con VICTORA (P4)", fmt_s(rp.loc["P4", "costo_total"]))
    k[2].metric(f"Ahorro {etiqueta_fuente(R)}", fmt_s(b["ahorro_S/"]), f"{fmt_num(b['ahorro_pct'], 1)} %")
    st.info(f"Estos resultados indican que un sistema de pronóstico y decisión óptima **podría** reducir los costos "
            f"en un **{fmt_num(b['ahorro_pct'], 1)} %** (IC 95 %: {fmt_num(b['IC95_pct_inf'], 1)} % a "
            f"{fmt_num(b['IC95_pct_sup'], 1)} %). Estudio piloto basado en **{R['n_dias']} días** de datos "
            f"(≈{R['n_prueba']} días de prueba por producto).")
    if R["n_agotados"]:
        st.warning(f"{R['n_agotados']} producto-días se agotaron: la venta subestima la demanda (dato censurado).")
    st.divider()
    st.subheader("Detalle")
    st.markdown("**Comparación de las 5 políticas**")
    tb = R["res_pol"][["politica", "descripcion", "sobrante", "faltante", "costo_merma", "margen_perdido",
                       "costo_total", "fill_rate_pct", "reduccion_vs_P0_pct"]]
    tabla(tb, "Politicas_P0_P4", "pol")
    c1, c2 = st.columns(2)
    with c1:
        mostrar_fig("costos", "Costo_por_politica", "costos")
    with c2:
        mostrar_fig("sens", "Sensibilidad_colchon", "sens_g")
    mostrar_fig("mf", "Merma_faltante_P0_vs_P4", "mf")
    st.markdown("**Sensibilidad al colchón de P0**")
    tabla(R["sens_col"], "Sensibilidad_colchon", "sc")
    st.markdown("**Sensibilidad al margen (± 10 puntos)**")
    tabla(R["sens_mar"], "Sensibilidad_margen", "sm")


# =============================================================== 5. Análisis
def seccion(titulo: str, key: str, abierta: bool = False):
    """Expander que solo ejecuta su cuerpo cuando está abierto."""
    ex = st.expander(titulo, expanded=abierta, on_change="rerun", key=f"ex_{key}")
    return ex, bool(getattr(ex, "open", True))


@st.fragment
def frag_prod_fig(tipo: str, nombre: str, key: str):
    pid = selector_producto(f"sel_{key}")
    mostrar_fig(tipo, f"{nombre}_{pid}", f"{key}_{pid}", pid)


@st.fragment
def frag_ranking():
    R = st.session_state["R"]
    pid = selector_producto("sel_rank")
    rk = R["sel"][pid]["ranking"].drop(columns=["metrica_principal"])
    tabla(rk, f"Ranking_{pid}", f"rk_{pid}", 3)
    mostrar_fig("err", f"Errores_{pid}", f"err_{pid}", pid)


@st.fragment
def frag_backtest():
    R = st.session_state["R"]
    pid = selector_producto("sel_bt")
    bt = R["backtest"][R["backtest"]["producto_id"] == pid][["fecha", "modelo", "real", "pronostico", "error"]].copy()
    bt["fecha"] = bt["fecha"].dt.strftime("%Y-%m-%d")
    tabla(bt, f"Backtesting_{pid}", f"bt_{pid}", 3, altura=300)


def tab_analisis():
    R = st.session_state.get("R")
    st.header("📊 Análisis estadístico")
    if not R:
        sin_datos()
        return
    st.markdown("### Hallazgos clave")
    for h in R["hallazgos"]:
        st.markdown(f"- {h}")
    st.caption("Cada sección tiene botones para descargar su tabla (.xlsx) y su gráfico (.png). "
               "Abre solo lo que necesites: las secciones cerradas no se calculan.")

    ex, ab = seccion("1. Estadística descriptiva", "desc", True)
    with ex:
        if ab:
            tabla(R["desc"], "Descriptivos", "desc", 2)

    ex, ab = seccion("2. Clasificación ABC-XYZ", "abc")
    with ex:
        if ab:
            c = R["clasif"][["producto_id", "ingreso", "pct_ingreso_acum", "ABC", "XYZ", "ABC_XYZ", "CV"]]
            tabla(c, "ABC_XYZ", "abc", 2)
            mostrar_fig("abc", "ABC_Pareto", "abc_g")

    ex, ab = seccion("3. Clasificación de la demanda (Syntetos–Boylan)", "dem")
    with ex:
        if ab:
            c = R["clasif"][["producto_id", "ADI", "CV2", "tipo_demanda", "intermitente"]].copy()
            c["ADI"] = c["ADI"].replace(float("inf"), float("nan"))
            tabla(c, "Clasificacion_demanda", "dem", 3)

    ex, ab = seccion("4. Efecto del día de la semana (Kruskal-Wallis)", "dow")
    with ex:
        if ab:
            perf = R["perfil"].T.reset_index().rename(columns={"index": "producto_id"})
            tabla(perf, "Perfil_dia_semana", "perf", 2)
            tabla(R["kw"], "Kruskal_Wallis", "kw", 4)
            frag_prod_fig("dia", "Dia_semana", "dow")

    ex, ab = seccion("5. Correlaciones de Spearman", "cor")
    with ex:
        if ab:
            mostrar_fig("heat", "Correlaciones_Spearman", "heat")
            tabla(R["corr_dow"], "Correlacion_dia_semana", "cord", 3)
            tabla(R["corr"].reset_index(), "Matriz_Spearman", "corm", 2, altura=300)

    ex, ab = seccion("6. Ranking de modelos", "rank")
    with ex:
        if ab:
            g = R["ganadores"][["producto_id", "modelo", "metrica_principal", "MASE", "RMSSE", "MAE", "RMSE", "WAPE",
                                "Sesgo"]]
            tabla(g, "Modelo_ganador", "gan", 3)
            fq = R["ganadores"]["modelo"].value_counts().rename_axis("modelo").reset_index(name="victorias")
            tabla(fq, "Frecuencia_victorias", "fq", 0)
            mostrar_fig("vict", "Frecuencia_victorias", "vict")
            st.markdown("**Ranking completo por producto**")
            frag_ranking()

    ex, ab = seccion("7. Backtesting detallado", "bt")
    with ex:
        if ab:
            frag_backtest()

    ex, ab = seccion("8. Pruebas de hipótesis", "pru")
    with ex:
        if ab:
            st.markdown("**Wilcoxon pareado: cada política vs. VICTORA (P4)**")
            tabla(R["wilcoxon"], "Wilcoxon", "wil", 4)
            fr = R["friedman"]
            frd = pd.DataFrame([{"chi2": fr["chi2"], "gl": fr["gl"], "p_valor": fr["p_valor"],
                                 "n_bloques": fr["n_bloques"], "W_Kendall": fr["W_Kendall"],
                                 **{f"rango_medio_{k}": v for k, v in fr["rangos_medios"].items()}}])
            st.markdown("**Friedman entre las 5 políticas**")
            tabla(frd, "Friedman", "fri", 4)
            st.markdown("**Bootstrap del ahorro de VICTORA vs. P0**")
            tabla(pd.DataFrame([R["boot"]]), "Bootstrap", "boot", 3)

    ex, ab = seccion("9. Sensibilidad", "sen")
    with ex:
        if ab:
            tabla(R["sens_col"], "Sensibilidad_colchon", "s_col", 2)
            tabla(R["sens_mar"], "Sensibilidad_margen", "s_mar", 2)
            mostrar_fig("sens", "Sensibilidad", "s_fig")

    ex, ab = seccion("Serie de tiempo por producto", "ser")
    with ex:
        if ab:
            frag_prod_fig("serie", "Serie", "serie")


# =============================================================== 6. Reportes
def tab_reportes():
    R = st.session_state.get("R")
    st.header("📑 Descarga todo lo que necesitas para redactar tu artículo")
    if not R:
        sin_datos()
        return
    st.markdown("El reporte incluye **párrafos de métodos y resultados ya redactados** con tus datos reales. "
                "Solo copia las tablas y los textos a tu artículo.")
    st.download_button("📥 REPORTE COMPLETO (.xlsx)", R["excel_reporte"], "Reporte_VICTORA.xlsx", type="primary",
                       key="dl_reporte", width="stretch")
    c1, c2 = st.columns(2)
    c1.download_button("📥 Plan de Producción (.xlsx)", R["excel_plan"], "Plan_Produccion_Semana.xlsx",
                       key="dl_plan_reportes", width="stretch")
    c2.download_button("📥 Todas las figuras (.zip, PNG 300 dpi)", R["zip_figuras"], "Figuras_VICTORA.zip",
                       mime="application/zip", key="dl_zip_figs", width="stretch")
    with st.expander("Figuras individuales por producto (tarda unos segundos)"):
        if st.button("Preparar ZIP de figuras por producto", key="prep_zip_prod"):
            with st.spinner("Generando figuras de todos los productos…"):
                st.session_state["zip_prod"] = c_zip_producto(clave_R(), R)
        if "zip_prod" in st.session_state:
            st.download_button("📥 Descargar figuras por producto (.zip)", st.session_state["zip_prod"],
                               "Figuras_por_producto.zip", mime="application/zip", key="dl_zip_prod")
    st.subheader("Contenido del reporte")
    st.dataframe(pd.DataFrame(list(HOJAS_REPORTE.items()), columns=["Hoja", "Contenido"]), hide_index=True,
                 width="stretch", height=min(760, 40 + 35 * len(HOJAS_REPORTE)))
    st.subheader("Vista previa: texto de resultados")
    for sub, txt in R["texto_resultados"]:
        st.markdown(f"**{sub}.** {txt}")


# =============================================================== 7. Metodología
def tab_metodologia():
    st.header("📖 Metodología y limitaciones")
    R = st.session_state.get("R")
    if not R:
        st.markdown("Modelos para series cortas (naïve, naïve estacional, medias móviles, perfil semanal, SES, "
                    "Holt-Winters con ≥ 28 días, Croston/SBA/TSB), selección por validación con origen rodante "
                    "(MASE), decisión de producción con el modelo newsvendor y evaluación contrafactual de políticas. "
                    "Carga datos para ver el texto con tus números.")
    else:
        for sub, txt in R["texto_metodos"]:
            st.markdown(f"**{sub}.** {txt}")
        st.subheader("Limitaciones")
        for t in R["limitaciones"]:
            st.markdown(f"- {t}")
    st.subheader("Cita sugerida del software")
    ctx = (R or {}).get("contexto", CONTEXTO_DEFECTO)
    st.code(f"{ctx['software']} (Versión {__version__}) [Software]. (2026). Sistema de pronóstico de demanda y decisión "
            f"óptima de producción para negocios de comida perecible. Caso de estudio: {ctx['caso']}, {ctx['ciudad']}.",
            language=None)


# =============================================================== despacho (solo la pantalla abierta)
def _ejecutar_seguro(fn):
    try:
        fn()
    except Exception as e:  # noqa: BLE001 — un error en una pantalla no debe matar toda la app
        st.error(f"Error en esta sección: {e}")
        with st.expander("Detalle técnico"):
            st.code(traceback.format_exc())


if not ES_NEGOCIO:
    _ctx = {**CONTEXTO_DEFECTO, **st.session_state.get("contexto", {})}
    _R = st.session_state.get("R")
    _chips = ["100 % local · sin internet", f"Caso: {_ctx.get('caso', '')}"]
    if _R:
        _chips += [f"{_R['n_productos']} productos × {_R['n_dias']} días",
                   f"Ahorro estimado {fmt_s(_R['boot']['ahorro_S/'])}"]
    estilo.hero("¿Cuánto producir mañana?",
                "Pronóstico de demanda y decisión óptima de producción: menos merma, menos ventas perdidas, "
                "evidencia lista para la gerencia y para tu artículo.", _chips)
modo = st.segmented_control("Sección", MODOS, key="modo", label_visibility="collapsed", required=True)
if ES_NEGOCIO:
    # Mi negocio: menú lateral de 7 pantallas (como la app de escritorio); solo corre la elegida.
    _ejecutar_seguro(neg.PANTALLAS[PANTALLA_NEG])
else:
    tabs = st.tabs(TABS, on_change="rerun", key="tabs_main")
    for tab, fn in zip(tabs, [tab_problema, tab_cargar, tab_decision, tab_impacto, tab_analisis, tab_reportes,
                              tab_metodologia]):
        with tab:
            if getattr(tab, "open", True):
                _ejecutar_seguro(fn)

# Al final: si una pantalla abrió su propio diálogo en esta ejecución, el tutorial no compite con él.
tutorial.mostrar_si_corresponde()
