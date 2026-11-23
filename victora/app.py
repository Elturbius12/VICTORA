"""VICTORA — interfaz Streamlit (punto de entrada).

Ejecutar:  streamlit run app.py
"""
import streamlit as st

st.set_page_config(page_title="VICTORA — ¿Cuánto producir mañana?", page_icon="🥐", layout="wide")

import gc  # noqa: E402
import os  # noqa: E402
import sys  # noqa: E402
import tempfile  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from victora import __version__  # noqa: E402
from victora import graficos as gr  # noqa: E402
from victora.decision import costos  # noqa: E402
from victora.reporte_excel import HOJAS  # noqa: E402
from victora.simulacion import COLCHON_DEFECTO, POLITICAS  # noqa: E402
from victora.utils import fmt_num, fmt_s  # noqa: E402

TMP_DIR = os.path.join(tempfile.gettempdir(), "victora_tmp")


# ---------------------------------------------------------------- caché
@st.cache_data(show_spinner=False)
def c_plantilla_vacia():
    from victora.plantilla import plantilla_vacia
    return plantilla_vacia()


@st.cache_data(show_spinner=False)
def c_plantilla_ejemplo():
    from victora.plantilla import plantilla_ejemplo
    return plantilla_ejemplo()


@st.cache_data(show_spinner=False, max_entries=5)
def c_validar(contenido: bytes):
    from victora.validador import validar
    r = validar(contenido)
    return r.semaforo, r.tabla(), r.datos, r.huecos


@st.cache_data(show_spinner=False, max_entries=3)
def c_pipeline(contenido: bytes, huecos_key: tuple, colchon: float, _progreso=None):
    from victora.pipeline import ejecutar
    _, _, datos, _ = c_validar(contenido)
    return ejecutar(datos, dict(huecos_key), colchon, progreso=_progreso)


@st.cache_data(show_spinner=False, max_entries=200)
def c_fig(tipo: str, clave: str, _R, pid: str = ""):
    """Gráficos cacheados como PNG (clave = hash de los datos + producto)."""
    R = _R
    nom = R["nombres"].get(pid, pid)
    if tipo == "serie":
        fig = gr.serie(R["m"], pid, nom)
    elif tipo == "dia":
        fig = gr.dia_semana(R["perfil"], pid, nom)
    elif tipo == "pron":
        fig = gr.real_vs_pronostico(R["m"], R["sel"][pid], pid, nom)
    elif tipo == "err":
        fig = gr.errores_modelos(R["sel"][pid]["ranking"], nom)
    elif tipo == "costos":
        fig = gr.costo_politicas(R["res_pol"])
    elif tipo == "mf":
        fig = gr.merma_faltante(R["res_pp"], R["nombres"])
    elif tipo == "sens":
        fig = gr.sensibilidad(R["sens_col"])
    else:
        raise ValueError(tipo)
    from victora.utils import fig_a_png
    png = fig_a_png(fig, dpi=110)
    plt.close(fig)
    return png


def fig(tipo, pid=""):
    R = st.session_state["R"]
    st.image(c_fig(tipo, R["hash"] + str(R["colchon"]) + str(R["tratamiento_huecos"]), R, pid), width="stretch")


# ---------------------------------------------------------------- reset
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
    st.warning("¿Estás seguro? Se eliminarán todos los datos cargados, los resultados del análisis y los "
               "reportes generados. La app volverá al estado inicial.")
    c1, c2 = st.columns(2)
    if c1.button("Sí, borrar todo", type="primary", key="reset_si", width="stretch"):
        restablecer()
        st.rerun()
    if c2.button("Cancelar", key="reset_no", width="stretch"):
        st.session_state["pedir_reset"] = False
        st.rerun()


# ---------------------------------------------------------------- sidebar fijo
with st.sidebar:
    st.markdown(f"### 🥐 VICTORA v{__version__}")
    st.caption("Pronóstico de demanda y decisión óptima de producción")
    R0 = st.session_state.get("R")
    if R0:
        st.success(f"Análisis listo: {R0['n_productos']} productos × {R0['n_dias']} días "
                   f"({R0['segundos']:.1f} s)")
        if st.session_state.get("es_demo"):
            st.info("Usando datos de DEMOSTRACIÓN (ficticios).")
    else:
        st.info("Sin datos cargados.")
    if st.button("🗑️ Restablecer todo", key="reset_sidebar", width="stretch"):
        st.session_state["pedir_reset"] = True
    if st.session_state.get("pedir_reset"):
        dialogo_reset()
    st.caption("Tus datos no salen de esta computadora.")

if "_aviso" in st.session_state:
    st.toast(st.session_state.pop("_aviso"), icon="✅")
if st.session_state.pop("_reset_ok", False):
    st.toast("La app se restableció por completo.", icon="🗑️")


def correr(contenido: bytes, huecos: dict, demo=False):
    barra = st.progress(0.0, text="Iniciando…")
    R = c_pipeline(contenido, tuple(sorted((str(k), v) for k, v in huecos.items())),
                   st.session_state.get("colchon", COLCHON_DEFECTO),
                   _progreso=lambda f, t: barra.progress(min(f, 1.0), text=t))
    barra.progress(1.0, text=f"Listo en {R['segundos']:.1f} s")
    st.session_state["R"] = R
    st.session_state["es_demo"] = demo
    st.session_state["_aviso"] = ("Datos de demostración (FICTICIOS) analizados." if demo else "Análisis completo.") +         " Revisa las pestañas 📊 a 📑."
    st.rerun()


tabs = st.tabs(["🏠 Inicio", "📋 Plantilla y Guía", "📤 Cargar y Validar", "📊 Diagnóstico", "🔮 Pronóstico",
                "🏭 Plan de Producción", "💰 Impacto", "📑 Reportes", "📖 Metodología"])
R = st.session_state.get("R")


def sin_datos():
    st.info("Primero carga tu Excel en **📤 Cargar y Validar** o prueba con los datos de demostración en **🏠 Inicio**.")


# ================================================================ 1 Inicio
with tabs[0]:
    st.title("¿Cuánto producir mañana?")
    ej = costos(0.30, 55)
    st.markdown(
        "En una cafetería, lo que no se vende hoy **se bota** (merma) y lo que falta **es una venta perdida** "
        "(quiebre de stock). Casi siempre se decide “a ojo”, y eso cuesta dinero todos los días.  \n"
        f"Ejemplo: un pan cuesta **S/ {fmt_num(ej['c'])}** hacerlo y se vende a **S/ 0,30**. "
        f"Si produces 100 y vendes 70, pierdes **{fmt_s(30 * ej['c'])}** en merma. "
        f"Si produces 50 y la demanda era 70, dejas de ganar **{fmt_s(20 * ej['Cu'])}**.  \n"
        "**VICTORA** usa tus ventas para pronosticar la demanda y te dice la cantidad que minimiza ambas pérdidas.")
    c = st.columns(4)
    for col, (ic, t, d) in zip(c, [("📤", "1. Sube datos", "Tu Excel de ventas, precios y recetas"),
                                   ("📊", "2. Analiza", "Pronóstico y validación automática"),
                                   ("🏭", "3. Decide", "Cuánto producir y qué insumos comprar"),
                                   ("📑", "4. Descarga", "Reportes listos para tu artículo")]):
        col.markdown(f"<div style='text-align:center;font-size:2.2rem'>{ic}</div>"
                     f"<div style='text-align:center'><b>{t}</b><br><small>{d}</small></div>",
                     unsafe_allow_html=True)
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.download_button("📥 Descargar plantilla", c_plantilla_vacia(), "Plantilla_VICTORA_vacia.xlsx",
                       key="dl_plant_inicio", width="stretch")
    if c2.button("🧪 Probar con datos de demostración", key="demo_btn", type="primary", width="stretch"):
        b = c_plantilla_ejemplo()
        st.session_state["contenido"] = b
        correr(b, {}, demo=True)
    if c3.button("🗑️ Restablecer todo", key="reset_inicio", width="stretch"):
        st.session_state["pedir_reset"] = True
        st.rerun()
    if R:
        rp = R["res_pol"].set_index("politica")
        st.markdown(f"#### Resultado actual ({'⚠️ ' + R['fuente']})")
        k = st.columns(3)
        k[0].metric("Costo sin VICTORA (P0)", fmt_s(rp.loc["P0", "costo_total"]))
        k[1].metric("Costo con VICTORA (P4)", fmt_s(rp.loc["P4", "costo_total"]))
        k[2].metric("Ahorro", fmt_s(R["boot"]["ahorro_S/"]), f"{fmt_num(R['boot']['ahorro_pct'], 1)} %")

# ================================================================ 2 Plantilla
with tabs[1]:
    st.header("📋 Plantilla y guía")
    c1, c2 = st.columns(2)
    c1.download_button("📥 Plantilla vacía (.xlsx)", c_plantilla_vacia(), "Plantilla_VICTORA_vacia.xlsx",
                       key="dl_plant_vacia", width="stretch")
    c2.download_button("📥 Plantilla de ejemplo (.xlsx, datos ficticios)", c_plantilla_ejemplo(),
                       "Plantilla_VICTORA_ejemplo.xlsx", key="dl_plant_ej", width="stretch")
    st.markdown("🟨 **Amarillo** = columna obligatoria · ⬜ **Gris** = opcional. La hoja **LEEME** del archivo "
                "explica todo paso a paso.")
    from victora.plantilla import ESQUEMA
    from datos_demo.demo_data import generar

    @st.cache_data(show_spinner=False)
    def _ejemplo_hojas():
        return {h: d.head(4) for h, d in generar().items()}

    ejh = _ejemplo_hojas()
    desc_hoja = {"Productos": "Una fila por producto con precio y margen.",
                 "Ventas": "Una fila por **día y producto** (formato largo).",
                 "Recetas": "Una fila por insumo de cada producto.",
                 "Calendario": "(Opcional) días cerrados, feriados y eventos.",
                 "Produccion_real": "(Opcional) lo producido y lo que sobró: activa resultados **REAL**."}
    for h, cols in ESQUEMA.items():
        with st.expander(f"Hoja `{h}` — {desc_hoja[h]}", expanded=h == "Ventas"):
            st.markdown(" · ".join(f"{'🟨' if o else '⬜'} `{c}`" for c, o, _ in cols))
            if h in ejh:
                st.dataframe(ejh[h], hide_index=True, width="stretch")
    st.markdown("**Días necesarios:** mínimo 7 · útil desde 14 · recomendado 28 o más.")

# ================================================================ 3 Cargar
with tabs[2]:
    st.header("📤 Cargar y validar")
    up = st.file_uploader("Sube tu archivo Excel (.xlsx) basado en la plantilla", type=["xlsx"], key="uploader")
    if up is not None:
        st.session_state["contenido"] = up.getvalue()
        st.session_state["es_demo"] = False
    contenido = st.session_state.get("contenido")
    if contenido:
        semaf, tabla, datos, huecos = c_validar(contenido)
        icon = {"verde": "🟢", "amarillo": "🟡", "rojo": "🔴"}[semaf]
        msg = {"verde": "Todo correcto: puedes continuar.",
               "amarillo": "Puedes continuar, pero revisa las advertencias.",
               "rojo": "Hay errores que debes corregir en tu Excel antes de continuar."}[semaf]
        getattr(st, {"verde": "success", "amarillo": "warning", "rojo": "error"}[semaf])(f"{icon} {msg}")
        if len(tabla):
            st.dataframe(tabla, hide_index=True, width="stretch")
        trat = {}
        if huecos and semaf != "rojo":
            st.markdown("**Días sin registro:** indica cómo tratar cada uno.")
            for d in huecos:
                trat[d] = st.radio(f"{d:%A %d/%m/%Y}", ["cero", "cerrado"], horizontal=True,
                                   format_func=lambda x: "Venta cero" if x == "cero" else "Local cerrado",
                                   key=f"hueco_{d:%Y%m%d}")
        st.session_state["colchon"] = st.slider(
            "Colchón de la práctica habitual simulada (P0), %", 0, 50, int(COLCHON_DEFECTO * 100), 5,
            key="colchon_slider") / 100
        if semaf != "rojo" and st.button("▶️ Ejecutar análisis", type="primary", key="run_btn"):
            correr(contenido, trat, demo=st.session_state.get("es_demo", False))

# ================================================================ helpers producto
def selector(clave):
    pids = list(R["m"].columns)
    return st.selectbox("Producto", pids, format_func=lambda p: f"{p} — {R['nombres'][p]}", key=clave)


# ================================================================ 4 Diagnóstico
with tabs[3]:
    st.header("📊 Diagnóstico de la demanda")
    if not R:
        sin_datos()
    else:
        if R["n_dias"] < 28:
            st.warning(f"Estudio piloto: solo {R['n_dias']} días de datos. Los resultados son preliminares.")
        st.subheader("Estadística descriptiva")
        st.dataframe(R["desc"].round(2), hide_index=True, width="stretch")
        st.subheader("Clasificación (Syntetos–Boylan y ABC-XYZ)")
        st.dataframe(R["clasif"][["producto_id", "ADI", "CV2", "tipo_demanda", "ingreso", "ABC", "XYZ", "ABC_XYZ"]].round(3),
                     hide_index=True, width="stretch")
        pid = selector("sel_diag")
        c1, c2 = st.columns(2)
        with c1:
            fig("serie", pid)
        with c2:
            fig("dia", pid)
        kw = R["kw"].set_index("producto_id").loc[pid]
        st.caption(f"Kruskal-Wallis día de la semana: H = {fmt_num(kw['H'])}, p = {fmt_num(kw['p_valor'], 3)}. "
                   f"{kw['aviso_potencia']}")

# ================================================================ 5 Pronóstico
with tabs[4]:
    st.header("🔮 Pronóstico")
    if not R:
        sin_datos()
    else:
        g = R["ganadores"].copy()
        g.insert(1, "nombre", g["producto_id"].map(R["nombres"]))
        st.subheader("Modelo ganador por producto")
        st.dataframe(g[["producto_id", "nombre", "modelo", "metrica_principal", "MASE", "RMSSE", "MAE", "RMSE",
                        "WAPE", "Sesgo"]].round(3), hide_index=True, width="stretch")
        st.caption("MASE < 1 = mejor que repetir lo vendido ayer (naïve).")
        pid = selector("sel_pron")
        fig("pron", pid)
        c1, c2 = st.columns([3, 2])
        with c1:
            st.dataframe(R["sel"][pid]["ranking"].drop(columns=["metrica_principal"]).round(3), hide_index=True,
                         width="stretch")
        with c2:
            fig("err", pid)

# ================================================================ 6 Plan
with tabs[5]:
    st.header("🏭 Plan de producción — próximos 7 días")
    if not R:
        sin_datos()
    else:
        pl = R["plan"].copy()
        pl["dia"] = pl["fecha"].dt.strftime("%a %d/%m")
        orden = list(dict.fromkeys(pl["dia"]))
        t = pl.pivot_table(index="nombre", columns="dia", values="producir", aggfunc="sum")[orden]
        t["Total"] = t.sum(axis=1)
        st.dataframe(t, width="stretch")
        pl["intervalo (10%–90%)"] = pl["intervalo_10"].astype(str) + " – " + pl["intervalo_90"].astype(str)
        with st.expander("Detalle: pronóstico, razón crítica, Q* e intervalo"):
            st.dataframe(pl[["fecha", "nombre", "modelo", "pronostico", "razon_critica", "Q_optimo", "tamano_lote",
                             "producir", "intervalo (10%–90%)"]].round(2), hide_index=True, width="stretch")
        st.subheader("🛒 Insumos a comprar para la semana")
        if len(R["insumos_sem"]):
            st.dataframe(R["insumos_sem"][["insumo_nombre", "comprar", "unidad", "costo_estimado", "usado_en"]].round(2),
                         hide_index=True, width="stretch")
        else:
            st.info("No hay recetas registradas.")
        st.download_button("📥 Descargar Plan_Produccion_Semana.xlsx", R["excel_plan"], "Plan_Produccion_Semana.xlsx",
                           key="dl_plan_tab6")

# ================================================================ 7 Impacto
with tabs[6]:
    st.header("💰 Impacto: la evidencia del problema")
    if not R:
        sin_datos()
    else:
        rp = R["res_pol"].set_index("politica")
        b = R["boot"]
        etiqueta = "⚠️ SIMULADO" if R["fuente"] == "SIMULADO" else "✅ REAL (P0 con producción registrada)"
        k = st.columns(4)
        k[0].metric("Costo SIN VICTORA (P0)", fmt_s(rp.loc["P0", "costo_total"]))
        k[1].metric("Costo CON VICTORA (P4)", fmt_s(rp.loc["P4", "costo_total"]))
        k[2].metric("Ahorro", fmt_s(b["ahorro_S/"]), f"{fmt_num(b['ahorro_pct'], 1)} %")
        k[3].metric("Origen de las cifras", etiqueta)
        st.markdown(
            f"<div style='background:#FFF1E6;border-left:6px solid #D4380D;padding:12px 16px;border-radius:6px'>"
            f"Estos resultados indican que un sistema de pronóstico y decisión óptima podría reducir los costos de "
            f"producción en un <b>{fmt_num(b['ahorro_pct'], 1)} %</b> (IC 95 %: {fmt_num(b['IC95_pct_inf'], 1)} % a "
            f"{fmt_num(b['IC95_pct_sup'], 1)} %). Este es un estudio piloto basado en <b>{R['n_dias']} días</b> de datos "
            f"(≈{R['n_prueba']} días de prueba por producto). {etiqueta}</div>", unsafe_allow_html=True)
        st.write("")
        tb = R["res_pol"][["politica", "descripcion", "sobrante", "faltante", "costo_merma", "margen_perdido",
                           "costo_total", "fill_rate_pct", "reduccion_vs_P0_pct"]].round(2)
        st.dataframe(tb, hide_index=True, width="stretch")
        c1, c2 = st.columns(2)
        with c1:
            fig("costos")
        with c2:
            fig("sens")
        fig("mf")
        st.subheader("Sensibilidad")
        c1, c2 = st.columns(2)
        c1.markdown("**Colchón de P0**")
        c1.dataframe(R["sens_col"].round(2), hide_index=True, width="stretch")
        c2.markdown("**Margen ± 10 puntos**")
        c2.dataframe(R["sens_mar"].round(2), hide_index=True, width="stretch")
        if R["n_agotados"]:
            st.warning(f"{R['n_agotados']} producto-días se agotaron: la venta subestima la demanda (dato censurado).")

# ================================================================ 8 Reportes
with tabs[7]:
    st.header("📑 Descarga todo lo que necesitas para redactar tu artículo")
    if not R:
        sin_datos()
    else:
        st.download_button("📥 Descargar Reporte Completo (.xlsx)", R["excel_reporte"], "Reporte_VICTORA.xlsx",
                           type="primary", key="dl_reporte", width="stretch")
        st.download_button("📥 Descargar Plan de Producción (.xlsx)", R["excel_plan"], "Plan_Produccion_Semana.xlsx",
                           key="dl_plan_tab8")
        st.info("El reporte incluye párrafos de métodos y resultados ya redactados con tus datos. "
                "Solo copia las tablas y los textos a tu artículo.")
        st.dataframe(pd.DataFrame(list(HOJAS.items()), columns=["Hoja", "Contenido"]), hide_index=True,
                     width="stretch")
        with st.expander("Vista previa: texto de resultados"):
            for sub, txt in R["texto_resultados"]:
                st.markdown(f"**{sub}.** {txt}")

# ================================================================ 9 Metodología
with tabs[8]:
    st.header("📖 Metodología y limitaciones")
    if not R:
        st.markdown("Modelos para series cortas (naïve, naïve estacional, medias móviles, perfil semanal, SES, "
                    "Holt-Winters con ≥ 28 días, Croston/SBA/TSB), selección por validación con origen rodante "
                    "(MASE), decisión de producción con el modelo newsvendor y evaluación contrafactual de políticas.")
    else:
        for sub, txt in R["texto_metodos"]:
            st.markdown(f"**{sub}.** {txt}")
        st.subheader("Limitaciones")
        for t in R["limitaciones"]:
            st.markdown(f"- {t}")
    st.subheader("Cita sugerida del software")
    st.code(f"VICTORA (Versión {__version__}) [Software]. (2026). Sistema de pronóstico de demanda y decisión óptima "
            "de producción para negocios de comida perecible. Caso de estudio: cafetería La Victoriana, Juliaca, Perú.",
            language=None)
