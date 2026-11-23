"""Pantallas del NEGOCIO DIARIO (lo que antes era la app de escritorio), ahora en Streamlit.

Resumen del día · Registro de ventas · Motor de pronóstico · Seguimiento · Dashboard ·
Módulo educativo · Configuración. Los datos viven en la base de datos (Postgres en Render,
SQLite en una PC): se conservan entre visitas y reinicios.
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

ACCION_TXT = {"preparado": "preparar", "reventa": "comprar / reponer"}
CLASE_SIMPLE = {
    "Suave (estable)": ("📈 Se vende de forma pareja", "Casi todos los días vende una cantidad parecida."),
    "Errática (variable)": ("🎢 Las ventas suben y bajan mucho", "Unos días vende bastante y otros casi nada."),
    "Intermitente": ("🌙 Se vende pocas veces", "Hay varios días seguidos sin ventas; cuando se vende, es poco."),
    "Irregular (grumosa)": ("⚡ Se vende poco, pero a veces de golpe",
                            "La mayoría de días no se vende, pero de vez en cuando se vende bastante."),
    "Sin ventas": ("❔ Todavía no hay suficiente información", "Registre más días de ventas de este producto."),
}
ORIGEN_TXT = {"feriado": "Feriado oficial", "comercial": "Fecha comercial", "manual": "Agregada por usted"}
UMBRAL_ERROR_GRANDE = 0.5
COLOR = "#D4380D"


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
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def _bytes(funcion, *args) -> bytes:
    buf = io.BytesIO()
    funcion(*args, buf)
    return buf.getvalue()


def aviso_bd():
    motor = iniciar_bd()
    if motor == "sqlite" and not db.usa_postgres():
        st.caption("💾 Base de datos local (SQLite). En Render se usa Postgres automáticamente.")


def _recos(guardar=True):
    if "neg_recos" not in st.session_state:
        with st.spinner("Calculando recomendaciones para todos los productos…"):
            st.session_state["neg_recos"] = calcular_recomendaciones_todas(guardar_historial=guardar)
    return st.session_state["neg_recos"]


def _tabla_recos(resultados) -> pd.DataFrame:
    filas = []
    for r in sorted(resultados, key=lambda r: (r.get("categoria") or "~", -r["total_vendido"])):
        filas.append({
            "": r.get("confianza_icono", ""),
            "Categoría": r.get("categoria") or "Sin categoría",
            "Producto": r["nombre"] + ("  ⚠️" if r["sin_precio"] else ""),
            "Pronóstico venta": None if r["pronostico"] is None else round(r["pronostico"], 1),
            "Cantidad sugerida": r["cantidad_sugerida"],
            "Acción": (r["accion"] or "—").capitalize(),
            "Ganancia estimada (S/)": None if r.get("ganancia_estimada") is None else round(r["ganancia_estimada"]),
            "Método": r.get("modelo") or "—",
        })
    return pd.DataFrame(filas)


# ================================================================== 🏠 Resumen del día
def tab_resumen():
    aviso_bd()
    st.header("🏠 Resumen del día")
    prox = db.proxima_fecha_especial()
    if prox:
        dias = (date.fromisoformat(prox["fecha"]) - date.today()).days
        if 0 <= dias <= 7:
            st.info(f"📅 En {dias} día(s) es **{prox['nombre']}** ({prox['fecha']}). Si otros años ese día vendió "
                    "distinto a lo normal, considere ajustar lo que sugiere el sistema.")
    d = db.dias_desde_ultimo_respaldo()
    if d is None:
        st.caption("💾 Todavía no ha descargado ninguna copia de seguridad (⚙️ Configuración).")
    elif d > 14:
        st.caption(f"💾 Su última copia de seguridad fue hace {d} días. Considere hacer una nueva.")

    c1, c2 = st.columns([1, 3])
    if c1.button("🔄 Calcular / Actualizar", key="neg_res_calc", type="primary"):
        _refrescar()
    resultados, faltantes = _recos()
    if not resultados:
        st.warning("Todavía no hay productos. Vaya a **📋 Registro** para agregar su catálogo.")
        return
    calculables = [r for r in resultados if r["pronostico"] is not None]
    st.success(f"✅ Recomendaciones listas ({len(calculables)} de {len(resultados)} productos con datos suficientes).")
    if faltantes:
        ej = ", ".join(faltantes[:5]) + ("…" if len(faltantes) > 5 else "")
        st.warning(f"⚠️ Hay {len(faltantes)} día(s) sin ningún registro en su historial ({ej}). Revíselo en 📋 Registro.")
    if not calculables:
        st.warning("Todavía no hay suficientes días de ventas registrados (se necesitan al menos 5).")
        return
    top3 = sorted(calculables, key=lambda r: r["total_vendido"], reverse=True)[:3]
    prep = [r for r in top3 if r["accion"] == "preparar"]
    comp = [r for r in top3 if r["accion"] != "preparar"]
    partes = []
    if prep:
        partes.append("preparar " + ", ".join(f"**{r['cantidad_sugerida']}** de {r['nombre']}" for r in prep))
    if comp:
        partes.append("comprar/reponer " + ", ".join(f"**{r['cantidad_sugerida']}** de {r['nombre']}" for r in comp))
    st.markdown("### 📢 Hoy debería " + " y ".join(partes))
    mp = mejor_peor_dia_semana()
    if mp:
        st.caption(f"📊 En promedio, su mejor día es el {mp['mejor_dia']} ({mp['mejor_valor']} unid.) y el más "
                   f"flojo es el {mp['peor_dia']} ({mp['peor_valor']} unid.).")
    st.dataframe(_tabla_recos(resultados), hide_index=True, width="stretch", height=600)
    st.caption("🟢 confiable · 🟡 información limitada · 🔴 muy poca información")
    sp = sum(1 for r in resultados if r["sin_precio"])
    if sp:
        st.warning(f"⚠️ {sp} producto(s) no tienen precio. Configúrelos en 📋 Registro para ver su ganancia.")
    lentos = productos_que_casi_no_se_mueven()
    if lentos:
        st.caption("🐌 Casi no se mueven (revisar precio o sacarlos del menú): "
                   + ", ".join(p["nombre"] for p in lentos[:8]) + ".")
    hoy = date.today().isoformat()
    a, b = st.columns(2)
    a.download_button("📄 Exportar reporte (Excel)", _bytes(exportar_reporte_excel, resultados),
                      f"reporte_victoriana_{hoy}.xlsx", key="neg_res_xlsx", width="stretch")
    b.download_button("🧾 Comanda para cocina (PDF)", _bytes(generar_comanda_pdf, resultados),
                      f"comanda_{hoy}.pdf", key="neg_res_pdf", width="stretch")


# ================================================================== 📋 Registro de ventas
def tab_registro():
    aviso_bd()
    st.header("📋 Registro de ventas diarias")
    st.caption("Anote cuántas unidades vendió de cada producto. El precio se edita en la misma tabla.")
    _, faltantes = db.get_pivot_ventas()
    stats = db.contar_registros()
    if faltantes:
        ej = ", ".join(faltantes[:5]) + ("…" if len(faltantes) > 5 else "")
        st.warning(f"⚠️ Hay {len(faltantes)} día(s) sin registro entre su primera y última venta ({ej}). Si no abrió, "
                   "use «Local cerrado»; si se le olvidó, anótelo ahora.")
    if stats["fecha_max"] and stats["fecha_max"] < date.today().isoformat():
        st.info(f"📌 Su último registro fue el {stats['fecha_max']}. ¿Ya anotó las ventas de hoy?")

    sub = st.tabs(["🗓️ Ventas del día", "📦 Productos", "🧂 Recetas", "📂 Importar"], key="neg_reg_sub")
    with sub[0]:
        _registro_dia(stats)
    with sub[1]:
        _productos()
    with sub[2]:
        _recetas()
    with sub[3]:
        _importar()


def _registro_dia(stats):
    if "neg_fecha" not in st.session_state:
        st.session_state["neg_fecha"] = date.today()
    c = st.columns([2, 1, 1, 2])
    if c[1].button("◀ Ayer", key="neg_ayer", width="stretch"):
        st.session_state["neg_fecha"] = st.session_state["neg_fecha"] - timedelta(days=1)
    if c[2].button("Hoy ▶", key="neg_hoy", width="stretch"):
        st.session_state["neg_fecha"] = date.today()
    fecha = c[0].date_input("Fecha", key="neg_fecha", format="YYYY-MM-DD")
    fs = fecha.isoformat()

    seg = db.get_seguimiento(desde=fs, hasta=fs)
    if not seg.empty:
        with st.expander(f"🔎 Lo que el sistema pronosticó para el {fs}", expanded=True):
            st.dataframe(seg[["producto", "pronostico", "cantidad_sugerida", "real"]].rename(columns={
                "producto": "Producto", "pronostico": "Pronóstico", "cantidad_sugerida": "Sugerido",
                "real": "Venta real"}), hide_index=True, width="stretch")

    prods = db.get_productos()
    vdf = db.get_ventas(desde=fs, hasta=fs)
    previas = dict(zip(vdf["producto"], vdf["unidades"]))
    obs = dict(zip(vdf["producto"], vdf["observacion"]))
    tabla = pd.DataFrame({
        "id": prods["id"].astype(int),
        "Categoría": prods["categoria"].fillna(""),
        "Producto": prods["nombre"],
        "Precio (S/)": prods["precio"].astype(float),
        "Unidades vendidas": [int(previas.get(n, 0)) for n in prods["nombre"]],
        "Observación": [obs.get(n, "") or "" for n in prods["nombre"]],
    })
    ed = st.data_editor(
        tabla, key=f"neg_editor_{fs}", hide_index=True, width="stretch", height=min(900, 40 + 35 * len(tabla)),
        disabled=["id", "Categoría", "Producto"], column_config={
            "id": None,
            "Precio (S/)": st.column_config.NumberColumn(min_value=0.0, step=0.5, format="%.2f"),
            "Unidades vendidas": st.column_config.NumberColumn(min_value=0, step=1, format="%d"),
        })
    sin_precio = ed.loc[ed["Precio (S/)"] <= 0, "Producto"].tolist()
    if sin_precio:
        st.warning("⚠️ Sin precio (no se podrá calcular su ganancia): " + ", ".join(sin_precio))
    a, b = st.columns(2)
    if a.button("💾 Guardar ventas y precios", key="neg_guardar", type="primary", width="stretch"):
        ventas = {int(r["id"]): int(r["Unidades vendidas"] or 0) for _, r in ed.iterrows()}
        observ = {int(r["id"]): str(r["Observación"] or "") for _, r in ed.iterrows()}
        db.registrar_ventas_dia(fs, ventas, observ)
        for _, r in ed.iterrows():
            db.actualizar_producto(int(r["id"]), precio=float(r["Precio (S/)"] or 0))
        _refrescar()
        st.success(f"✅ Ventas y precios del {fs} guardados.")
    if b.button("🚫 Local cerrado este día", key="neg_cerrado", width="stretch"):
        st.session_state["neg_confirmar_cerrado"] = fs
    if st.session_state.get("neg_confirmar_cerrado") == fs:
        st.warning(f"¿Confirma que el local estuvo CERRADO el {fs}? Se registrará 0 en todos los productos.")
        x, y = st.columns(2)
        if x.button("Sí, estuvo cerrado", key="neg_cerrado_si", type="primary"):
            n = db.marcar_dia_cerrado(fs)
            st.session_state.pop("neg_confirmar_cerrado")
            _refrescar()
            st.success(f"✅ {fs} registrado como día cerrado ({n} productos en 0).")
        if y.button("Cancelar", key="neg_cerrado_no"):
            st.session_state.pop("neg_confirmar_cerrado")
            st.rerun()
    stats = db.contar_registros()
    txt = f"📊 {stats['productos']} productos y {stats['registros']} registros de ventas en {stats['dias']} días"
    if stats["fecha_min"]:
        txt += f" (del {stats['fecha_min']} al {stats['fecha_max']})"
    st.caption(txt)


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

    with st.form("neg_nuevo_prod", clear_on_submit=True):
        st.markdown("**➕ Nuevo producto**")
        a, b = st.columns(2)
        nombre = a.text_input("Nombre del producto")
        cats = sorted({c for c in prods["categoria"].fillna("") if c})
        categoria = b.selectbox("Categoría", [""] + cats, accept_new_options=True)
        a, b, c = st.columns(3)
        precio = a.number_input("Precio de venta (S/)", min_value=0.0, step=0.5)
        margen = b.number_input("Margen de ganancia (%)", 0.0, 100.0, db.MARGEN_DEFECTO * 100)
        tipo = c.radio("Tipo", ["preparado", "reventa"], horizontal=True,
                       captions=["Se prepara/cocina", "Se compra ya hecho"])
        a, b = st.columns(2)
        vida = a.number_input("¿Cuántos días dura? (1 = solo el día)", min_value=1, value=1)
        recup = b.number_input("Si sobra, ¿qué fracción se recupera? (0 a 1)", 0.0, 1.0, 0.5)
        if st.form_submit_button("Guardar producto", type="primary"):
            if not nombre.strip():
                st.warning("Escriba un nombre de producto.")
            else:
                db.agregar_producto(nombre, precio, int(vida), recup, tipo=tipo, margen=margen / 100,
                                    categoria=categoria or "")
                _refrescar()
                st.success(f"✅ «{nombre}» agregado.")
                st.rerun()


def _recetas():
    st.caption("Una fila por insumo de cada producto (ej. Pizza Americana Familiar · I001 · Harina · 250 · g). "
               "Se usan en el análisis completo para calcular la lista de compras.")
    prods = db.get_productos()
    rc = db.get_recetas()
    t = rc[["producto", "insumo_id", "insumo_nombre", "cantidad_por_unidad", "unidad_medida",
            "costo_unitario_insumo"]] if len(rc) else pd.DataFrame(
        columns=["producto", "insumo_id", "insumo_nombre", "cantidad_por_unidad", "unidad_medida",
                 "costo_unitario_insumo"])
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


def _importar():
    st.markdown("**📦 Importar catálogo (productos y precios)** — Excel o CSV con columnas: producto, precio, "
                "tipo (preparado/reventa), margen (0 a 1), categoria, vida_util_dias, recuperable.")
    up = st.file_uploader("Catálogo", type=["xlsx", "xls", "csv"], key="neg_up_cat")
    if up is not None and st.button("Importar catálogo", key="neg_imp_cat"):
        act, cre, ign = db.importar_catalogo(io.BytesIO(up.getvalue()), up.name)
        _refrescar()
        st.success(f"Se actualizaron {act} producto(s) y se crearon {cre} nuevo(s)."
                   + (f" Se ignoraron {ign} fila(s) que parecían notas." if ign else ""))
    st.divider()
    st.markdown("**📂 Importar ventas** — CSV o Excel con columnas: fecha, producto, unidades.")
    up2 = st.file_uploader("Ventas", type=["csv", "xlsx", "xls"], key="neg_up_ventas")
    if up2 is not None and st.button("Importar ventas", key="neg_imp_ventas"):
        n = db.importar_csv(io.BytesIO(up2.getvalue()), up2.name)
        _refrescar()
        st.success(f"Se importaron {n} registros de ventas.")


# ================================================================== 🔮 Motor de pronóstico
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
        base.update(nuevo=True, faltan=MIN_DIAS_HISTORIAL_PROPIO - len(y),
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
    aviso_bd()
    st.header("🔮 ¿Cuánto vas a vender mañana?")
    st.caption("Elija un producto: el sistema prueba varias formas de pronosticar y se queda con la que mejor "
               "funcionó en su negocio. El margen usado es el de cada producto (📋 Registro → Productos).")
    nombres = db.get_productos()["nombre"].tolist()
    if not nombres:
        st.info("No hay productos registrados.")
        return
    c1, c2, c3 = st.columns([3, 1, 1])
    nombre = c1.selectbox("Producto", nombres, key="neg_pron_prod")
    if c2.button("▶ Calcular este producto", key="neg_pron_uno", type="primary", width="stretch"):
        with st.spinner("Probando modelos…"):
            st.session_state["neg_pron"] = ("uno", _calcular_producto(nombre))
    if c3.button("📊 Calcular todo", key="neg_pron_todo", width="stretch"):
        st.session_state.pop("neg_recos", None)
        st.session_state["neg_pron"] = ("todos", None)
    est = st.session_state.get("neg_pron")
    if not est:
        st.info("Seleccione un producto y presione **Calcular**, o use **Calcular todo**.")
        return
    if est[0] == "todos":
        resultados, _ = _recos()
        st.subheader("📊 Recomendación para todos los productos")
        st.caption("«Pronóstico de venta» es lo que se espera vender mañana. «Cantidad sugerida» ya incluye un "
                   "colchón de seguridad según el margen de cada producto.")
        st.dataframe(_tabla_recos(resultados), hide_index=True, width="stretch", height=600)
        return
    r = est[1]
    verbo = ACCION_TXT.get(r["tipo"], "preparar")
    if r["nuevo"]:
        st.subheader("🆕 Este producto es nuevo")
        st.warning(f"Le faltan {r['faltan']} día(s) de historial propio de «{r['nombre']}».")
        if r["apoyo"] is not None:
            cr, *_ = razon_critica(r["precio"], r["margen"], r["recuperable"])
            q = cantidad_optima(r["apoyo"], max(r["apoyo"] * 0.6, 0.5), cr)
            st.info(f"Usando el promedio de otros productos de «{r['categoria']}»: {r['apoyo']:.1f} unid./día.")
            st.metric(f"🧪 Cantidad orientativa a {verbo}", f"{q} unidades")
        else:
            st.info("No hay productos parecidos (misma categoría) con historial. Use su criterio por ahora.")
        return
    if r["falt_cal"]:
        st.warning(f"⚠️ Hay {len(r['falt_cal'])} día(s) sin ningún registro en su historial.")
    if r["sin_precio"]:
        st.warning("⚠️ Este producto no tiene precio: la cantidad sugerida es confiable, la ganancia en S/ no.")
    a, b, c = st.columns(3)
    a.metric("📈 Mañana se espera vender", f"{r['pron']:.1f} unid.")
    b.metric(f"✅ Cantidad recomendada a {verbo}", f"{r['q']} unid.")
    c.metric("📆 Total estimado de la semana", f"{r['total_semana']:.0f} unid.")
    st.markdown(f"**{r['icono']} ¿Qué tan confiable es?** {r['conf']}")
    t, d = CLASE_SIMPLE.get(r["diag"]["clase"], ("", ""))
    st.markdown(f"**🧭 ¿Cómo se vende?** {t} — {d} _(basado en {r['diag']['dias']} días)_")
    if r["falt_mod"]:
        st.caption("Modelos que aún no pueden probarse: " + "; ".join(
            f"{m} (faltan {k} día(s))" for m, k in sorted(r["falt_mod"].items(), key=lambda x: x[1])[:4]))
    st.subheader("🏆 Comparamos varias formas de pronosticar")
    st.caption(f"Ganó: **{r['ganador']}**. Error promedio en días pasados (más bajo = mejor).")
    if not r["res"].empty:
        res = r["res"].copy()
        res.insert(0, "", ["🥇" if m == r["ganador"] else "" for m in res["Modelo"]])
        st.dataframe(res.rename(columns={"MAE": "Se equivocó en promedio (unid.)", "wMAPE": "Error (%)"}).round(3),
                     hide_index=True, width="stretch")
    sim = r["sim"]
    if sim["base"]["prod"] > 0 and not r["sin_precio"]:
        st.subheader("💰 ¿Cuánto cambiaría si usa este método?")
        st.caption("Con los días ya registrados: producir «lo de siempre» (promedio 7 días × 1,3) vs. el método.")
        tb = pd.DataFrame([{"Política": lab, "Ganancia (S/)": round(sim[k]["u"]), "Sobró (unid.)": sim[k]["sobra"],
                            "Faltó (unid.)": sim[k]["falta"]}
                           for k, lab in (("base", "Producción habitual"), ("modelo", "Con el método"))])
        st.dataframe(tb, hide_index=True, width="stretch")
        ah = sim["modelo"]["u"] - sim["base"]["u"]
        st.markdown(f"**{'✅ Habría ganado' if ah >= 0 else '⚠️ Habría ganado'} S/ {abs(ah):.0f} "
                    f"{'más' if ah >= 0 else 'menos'} con el método.**")
    st.subheader("📊 Así se vendió este producto")
    fig, ax = plt.subplots(figsize=(9, 3))
    ax.plot(r["dates"], r["y"], "o-", ms=3, color="#1f77b4", label="Lo que realmente vendió")
    p = r["preds"].get(r["ganador"])
    if p is not None:
        m = ~np.isnan(p)
        ax.plot(r["dates"][m], p[m], "--", color=COLOR, label="Lo que el método hubiera dicho")
    ax.set_title(r["nombre"])
    ax.legend(fontsize=8)
    fig.autofmt_xdate()
    st.image(_png(fig))


# ================================================================== 📈 Seguimiento
def tab_seguimiento():
    aviso_bd()
    st.header("📈 Seguimiento: pronóstico vs. realidad")
    st.caption("Cada pronóstico calculado se guarda. Cuando ya registró la venta real de ese día, aquí compara qué tan "
               "bien acertó y anota la razón de los errores grandes. «Generar historial completo» rellena los días "
               "pasados desde que cada producto tuvo historial suficiente.")
    c1, c2 = st.columns(2)
    if c1.button("📜 Generar historial completo", key="neg_seg_hist", width="stretch"):
        with st.spinner("Generando pronósticos de días pasados…"):
            n = backfill_historial_pronosticos()
        if n:
            st.success(f"Se generaron {n} pronóstico(s) de días pasados.")
        else:
            st.info("No había pronósticos nuevos para generar (productos muy nuevos necesitan más días).")
    df = db.get_seguimiento()
    for col in ("pronostico", "cantidad_sugerida", "real", "error", "error_abs", "error_pct"):
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if df.empty:
        st.info("Todavía no hay pronósticos guardados. Use 🏠 Resumen del día o 🔮 Pronóstico; el sistema los guarda solo.")
        return
    c2.download_button("📄 Exportar a Excel", _bytes(exportar_seguimiento_excel, df), "seguimiento_victoriana.xlsx",
                       key="neg_seg_xlsx", width="stretch")
    con = df[df["real"].notna()]
    if not con.empty:
        ok = int((con["error_pct"].fillna(1) <= UMBRAL_ERROR_GRANDE).sum())
        st.markdown(f"### 📊 De {len(con)} pronóstico(s) ya comparados, {ok} ({ok / len(con):.0%}) tuvieron un error "
                    f"razonable (≤ {UMBRAL_ERROR_GRANDE:.0%}).")
        if len(con) >= 3:
            s = con.assign(semana=pd.to_datetime(con["fecha"]).dt.to_period("W").dt.start_time) \
                .groupby("semana")["error_abs"].mean()
            if len(s) >= 2:
                fig, ax = plt.subplots(figsize=(9, 2.4))
                ax.plot(s.index, s.values, "o-", color="#E8A317")
                ax.set_title("Error promedio por semana (unidades) — ¿va bajando?")
                st.image(_png(fig))
    else:
        st.info("Hay pronósticos guardados, pero ninguno tiene todavía su venta real registrada.")
    prods = sorted(df["producto"].unique())
    filtro = st.selectbox("Filtrar por producto", ["(todos)"] + prods, key="neg_seg_filtro")
    v = df if filtro == "(todos)" else df[df["producto"] == filtro]
    t = pd.DataFrame({
        "⚠️": ["🔴" if (pd.notna(e) and e > UMBRAL_ERROR_GRANDE) else "" for e in v["error_pct"]],
        "Fecha": v["fecha"], "Producto": v["producto"], "Pronosticado": v["pronostico"].round(1),
        "Venta real": v["real"], "Error": v["error"].round(1),
        "Error %": (v["error_pct"] * 100).round(0), "Modelo": v["modelo"],
        "Observación": v["observacion"].fillna(""),
    })
    ed = st.data_editor(t, key=f"neg_seg_editor_{filtro}", hide_index=True, width="stretch", height=500,
                        disabled=[c for c in t.columns if c != "Observación"],
                        column_config={"Observación": st.column_config.TextColumn(
                            help="¿Por qué falló? (llovió, feriado, evento…)")})
    if st.button("💾 Guardar observaciones", key="neg_seg_guardar"):
        ids = dict(zip(*db.get_productos(solo_activos=False)[["nombre", "id"]].values.T))
        n = 0
        for (_, a), (_, b) in zip(t.iterrows(), ed.iterrows()):
            if a["Observación"] != b["Observación"] and pd.notna(b["Venta real"]):
                db.registrar_venta(b["Fecha"], int(ids[b["Producto"]]), int(b["Venta real"]),
                                   observacion=str(b["Observación"]))
                n += 1
        st.success(f"✅ {n} observación(es) guardadas.")


# ================================================================== 📊 Dashboard
def tab_dashboard():
    aviso_bd()
    st.header("📊 Dashboard")
    s = db.contar_registros()
    a, b, c = st.columns(3)
    a.metric("🍗 Productos", s["productos"])
    b.metric("📋 Registros", s["registros"])
    c.metric("📅 Días", s["dias"])
    pivot, _ = db.get_pivot_ventas()
    if pivot.empty:
        st.info("No hay datos de ventas para graficar.")
        return
    fig, ax = plt.subplots(figsize=(9, 2.8))
    tot = pivot.sum(axis=1)
    ax.fill_between(tot.index, tot.values, alpha=0.3, color="#1f77b4")
    ax.plot(tot.index, tot.values, color="#1f77b4", lw=2)
    ax.set_title("Ventas totales por día (unidades)")
    fig.autofmt_xdate()
    st.image(_png(fig))
    c1, c2 = st.columns(2)
    fig, ax = plt.subplots(figsize=(5, 3))
    top5 = pivot.sum().sort_values().tail(5)
    bars = ax.barh(top5.index, top5.values, color=COLOR)
    for br, v in zip(bars, top5.values):
        ax.text(br.get_width() + 0.3, br.get_y() + br.get_height() / 2, f"{int(v)}", va="center", fontsize=8)
    ax.set_title("Top 5 productos (total unidades)")
    c1.image(_png(fig))
    fig, ax = plt.subplots(figsize=(5, 3))
    dow = pivot.groupby(pivot.index.dayofweek).mean()
    nombres = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    x = np.arange(len(dow))
    for i, p in enumerate(pivot.sum().sort_values(ascending=False).head(5).index):
        ax.bar(x + i * 0.15, dow[p], 0.15, label=p[:14])
    ax.set_xticks(x + 0.3)
    ax.set_xticklabels([nombres[i] for i in dow.index])
    ax.set_title("Promedio por día de la semana (Top 5)")
    ax.legend(fontsize=6)
    c2.image(_png(fig))
    st.subheader("Clasificación de demanda por producto")
    filas = []
    for p in pivot.columns:
        d = diagnostico(pivot[p].values.astype(float))
        filas.append({"Producto": p, "Clase": d["clase"], "ADI": round(d["adi"], 2) if np.isfinite(d["adi"]) else None,
                      "CV²": None if d["cv2"] != d["cv2"] else round(d["cv2"], 3), "% días sin venta": round(d["pct_cero"] * 100)})
    st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch")


# ================================================================== 📚 Módulo educativo
def tab_educativo():
    aviso_bd()
    st.header("📚 Módulo educativo")
    st.caption("Cómo funciona cada método de pronóstico, en palabras simples y con ejemplos de su propio negocio.")
    modelo = st.selectbox("Método", list(MODELOS_EDUCATIVOS.keys()), key="neg_edu_modelo")
    info = MODELOS_EDUCATIVOS[modelo]
    st.subheader(info["nombre"])
    st.code(info["formula"], language=None)
    st.markdown(info["explicacion"].replace("\n", "  \n"))
    if "ejemplo" in info:
        pivot, _ = db.get_pivot_ventas()
        if pivot.empty:
            st.info("Registre ventas para ver un ejemplo con sus datos.")
            return
        prod = st.selectbox("Producto para el ejemplo", list(pivot.columns), key="neg_edu_prod")
        if st.button("Ver ejemplo con datos reales", key="neg_edu_btn"):
            try:
                st.code(info["ejemplo"](pivot[prod].values.astype(float), pivot.index), language=None)
            except Exception as e:  # noqa: BLE001
                st.warning(f"No se pudo generar el ejemplo: {e}")


# ================================================================== ⚙️ Configuración
def tab_configuracion():
    aviso_bd()
    st.header("⚙️ Configuración")
    st.subheader("💾 Copia de seguridad")
    d = db.dias_desde_ultimo_respaldo()
    st.caption("⚠️ Todavía no ha hecho ninguna copia." if d is None else
               ("✅ Último respaldo: hoy." if d == 0 else f"Último respaldo: hace {d} día(s)."))
    if db.usa_postgres():
        st.caption("Sus datos se guardan en la base de datos Postgres de Render. La copia es un Excel con todas las "
                   "tablas; guárdela en su computadora. (El Postgres gratuito de Render vence a los 30 días: antes "
                   "de eso descargue una copia y restáurela en la nueva base.)")
    a, b = st.columns(2)
    if a.button("Preparar copia de seguridad", key="neg_resp_prep", width="stretch"):
        st.session_state["neg_respaldo"] = db.respaldar_base()
    if st.session_state.get("neg_respaldo"):
        a.download_button("📥 Descargar copia (.xlsx)", st.session_state["neg_respaldo"],
                          f"victoriana_respaldo_{date.today().isoformat()}.xlsx", key="neg_resp_dl", width="stretch")
    up = b.file_uploader("Restaurar desde una copia (.xlsx)", type=["xlsx"], key="neg_resp_up")
    if up is not None:
        b.warning("Restaurar REEMPLAZA todos los datos actuales por los de la copia.")
        if b.button("Restaurar ahora", key="neg_resp_rest", type="primary"):
            n = db.restaurar_respaldo(up.getvalue())
            _refrescar()
            b.success("✅ Restaurado: " + ", ".join(f"{k}: {v}" for k, v in n.items()))

    st.subheader("🧾 Comanda para la cocina")
    st.caption("Hoja PDF lista para imprimir con lo que toca preparar y comprar hoy.")
    if st.button("Generar comanda (PDF)", key="neg_cmd_gen"):
        res, _ = calcular_recomendaciones_todas(guardar_historial=False)
        st.session_state["neg_comanda"] = _bytes(generar_comanda_pdf, res)
    if st.session_state.get("neg_comanda"):
        st.download_button("📥 Descargar comanda", st.session_state["neg_comanda"],
                           f"comanda_{date.today().isoformat()}.pdf", key="neg_cmd_dl")

    st.subheader("📅 Calendario de feriados y fechas especiales")
    st.caption("Incluye feriados del Perú 2026 y fechas comerciales. Estos días no se mezclan con el promedio normal "
               "del día de la semana y se le avisa cuando se acerca uno.")
    with st.form("neg_fecha_form", clear_on_submit=True):
        a, b, c = st.columns([1, 2, 1])
        f = a.date_input("Fecha", value=None, format="YYYY-MM-DD")
        n = b.text_input("Nombre (aniversario, evento…)")
        if c.form_submit_button("➕ Agregar"):
            if f is None or not n.strip():
                st.warning("Complete fecha y nombre.")
            else:
                db.agregar_fecha_especial(f.isoformat(), n.strip(), origen="manual")
                st.rerun()
    fe = db.get_fechas_especiales()
    if len(fe):
        t = pd.DataFrame({"Borrar": False, "Fecha": fe["fecha"], "Nombre": fe["nombre"],
                          "Origen": [ORIGEN_TXT.get(o, o) for o in fe["origen"]]})
        ed = st.data_editor(t, key="neg_fe_editor", hide_index=True, width="stretch",
                            disabled=["Fecha", "Nombre", "Origen"])
        if st.button("🗑 Borrar fechas marcadas", key="neg_fe_borrar"):
            for fecha in ed.loc[ed["Borrar"], "Fecha"]:
                db.eliminar_fecha_especial(fecha)
            st.rerun()
