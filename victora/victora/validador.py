"""Validación del Excel de carga. Mensajes en español con hoja, fila y columna."""
from __future__ import annotations

import io
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .plantilla import ESQUEMA, HOJAS_OBLIGATORIAS
from .utils import UNIDADES, si_no

ERROR, ADVERTENCIA, INFO = "🔴 Error", "🟡 Advertencia", "🔵 Aviso"


@dataclass
class Resultado:
    mensajes: list[dict] = field(default_factory=list)
    datos: dict[str, pd.DataFrame] = field(default_factory=dict)
    huecos: list = field(default_factory=list)  # fechas faltantes dentro del rango

    def add(self, nivel, hoja, fila, columna, mensaje, sugerencia=""):
        self.mensajes.append({"Nivel": nivel, "Hoja": hoja, "Fila": str(fila) if fila is not None else "",
                              "Columna": columna or "", "Problema": mensaje, "Sugerencia": sugerencia})

    @property
    def n_errores(self):
        return sum(m["Nivel"] == ERROR for m in self.mensajes)

    @property
    def semaforo(self) -> str:
        if self.n_errores:
            return "rojo"
        return "amarillo" if any(m["Nivel"] == ADVERTENCIA for m in self.mensajes) else "verde"

    def tabla(self) -> pd.DataFrame:
        return pd.DataFrame(self.mensajes, columns=["Nivel", "Hoja", "Fila", "Columna", "Problema", "Sugerencia"])


def _numerico(r, df, hoja, col, entero=False, minimo=0.0, maximo=None, obligatorio=True):
    """Convierte una columna a número y registra filas inválidas."""
    crudo = df[col]
    texto = crudo.astype(str).str.strip()
    conv = pd.to_numeric(texto.str.replace(",", ".", regex=False), errors="coerce")
    vacio = crudo.isna() | (texto == "") | (texto.str.lower() == "nan")
    for i in df.index[vacio & obligatorio]:
        r.add(ERROR, hoja, i + 2, col, "Celda vacía en columna obligatoria.", "Escribe un valor.")
    for i in df.index[conv.isna() & ~vacio]:
        r.add(ERROR, hoja, i + 2, col, f"'{crudo[i]}' no es un número.", "Usa solo dígitos y punto decimal (ej. 4.50).")
    coma = texto.str.contains(",", regex=False) & conv.notna()
    for i in df.index[coma][:5]:
        r.add(ADVERTENCIA, hoja, i + 2, col, f"'{crudo[i]}' usa coma decimal; se interpretó como {conv[i]}.",
              "Usa punto decimal para evitar ambigüedades.")
    for i in df.index[conv < minimo]:
        r.add(ERROR, hoja, i + 2, col, f"Valor negativo ({conv[i]}).", f"Debe ser ≥ {minimo:g}.")
    if maximo is not None:
        for i in df.index[conv > maximo]:
            r.add(ERROR, hoja, i + 2, col, f"Valor {conv[i]} fuera de rango.", f"Debe estar entre {minimo:g} y {maximo:g}.")
    if entero:
        for i in df.index[conv.notna() & (conv % 1 != 0)]:
            r.add(ERROR, hoja, i + 2, col, f"{conv[i]} no es entero.", "Usa unidades enteras.")
    return conv


def _fechas(r, df, hoja, col="fecha"):
    conv = pd.to_datetime(df[col], errors="coerce")
    for i in df.index[conv.isna()]:
        r.add(ERROR, hoja, i + 2, col, f"Fecha inválida: '{df[col][i]}'.", "Usa el formato AAAA-MM-DD (ej. 2026-10-05).")
    return conv.dt.normalize()


def validar(contenido: bytes) -> Resultado:
    """Valida el Excel y devuelve mensajes + datos limpios."""
    r = Resultado()
    try:
        hojas = pd.read_excel(io.BytesIO(contenido), sheet_name=None, dtype=object)
    except Exception as e:  # noqa: BLE001
        r.add(ERROR, "-", None, None, f"No se pudo leer el archivo: {e}", "Sube un archivo .xlsx válido.")
        return r

    for h in HOJAS_OBLIGATORIAS:
        if h not in hojas:
            r.add(ERROR, h, None, None, f"Falta la hoja '{h}'.", "Descarga la plantilla y copia tus datos en ella.")
    if r.n_errores:
        return r

    crudas = {}
    for h, cols in ESQUEMA.items():
        if h not in hojas:
            continue
        df = hojas[h].copy()
        df.columns = [str(c).strip() for c in df.columns]
        df = df.dropna(how="all").reset_index(drop=True)
        for c, obl, _ in cols:
            if c not in df.columns:
                if obl:
                    r.add(ERROR, h, 1, c, f"Falta la columna obligatoria '{c}'.", "Revisa el encabezado; debe escribirse exactamente así.")
                else:
                    df[c] = np.nan
        crudas[h] = df
    if r.n_errores:
        return r

    # ---------- Productos ----------
    p = crudas["Productos"]
    p["producto_id"] = p["producto_id"].astype(str).str.strip()
    for i in p.index[p["producto_id"].isin(["", "nan", "None"])]:
        r.add(ERROR, "Productos", i + 2, "producto_id", "producto_id vacío.", "Asigna un código como P001.")
    for i in p.index[p["producto_id"].duplicated()]:
        r.add(ERROR, "Productos", i + 2, "producto_id", f"Código repetido '{p['producto_id'][i]}'.", "Cada producto debe tener un código único.")
    p["precio_venta"] = _numerico(r, p, "Productos", "precio_venta")
    p["margen_esperado_pct"] = _numerico(r, p, "Productos", "margen_esperado_pct", maximo=100)
    p["vida_util_dias"] = _numerico(r, p, "Productos", "vida_util_dias", entero=True, obligatorio=False).fillna(1)
    p["valor_rescate"] = _numerico(r, p, "Productos", "valor_rescate", obligatorio=False).fillna(0)
    p["tamano_lote"] = _numerico(r, p, "Productos", "tamano_lote", entero=True, obligatorio=False).fillna(1).clip(lower=1)
    for i in p.index[p["es_perecible"].isna()]:
        r.add(ERROR, "Productos", i + 2, "es_perecible", "Celda vacía.", "Escribe SI o NO.")
    p["es_perecible"] = p["es_perecible"].map(si_no)
    p["nombre"] = p["nombre"].astype(str).str.strip()
    p["categoria"] = p["categoria"].fillna("").astype(str)
    costo = p["precio_venta"] * (1 - p["margen_esperado_pct"] / 100)
    for i in p.index[p["valor_rescate"] > costo]:
        r.add(ADVERTENCIA, "Productos", i + 2, "valor_rescate", "El valor de rescate supera el costo unitario.",
              "Revisa; se usará el costo como tope.")
    p["valor_rescate"] = np.minimum(p["valor_rescate"], costo.fillna(0))
    ids = set(p["producto_id"])

    # ---------- Ventas ----------
    v = crudas["Ventas"]
    v["producto_id"] = v["producto_id"].astype(str).str.strip()
    v["fecha"] = _fechas(r, v, "Ventas")
    v["unidades_vendidas"] = _numerico(r, v, "Ventas", "unidades_vendidas", entero=True)
    v["agotado"] = v["agotado"].map(si_no)
    for i in v.index[~v["producto_id"].isin(ids)]:
        r.add(ERROR, "Ventas", i + 2, "producto_id", f"'{v['producto_id'][i]}' no existe en Productos.",
              "Escribe el código exactamente igual que en la hoja Productos.")
    dup = v.duplicated(["fecha", "producto_id"], keep="first") & v["fecha"].notna()
    for i in v.index[dup]:
        r.add(ERROR, "Ventas", i + 2, "fecha", f"Fecha duplicada para {v['producto_id'][i]} ({v['fecha'][i].date()}).",
              "Deja una sola fila por día y producto (suma las ventas si es necesario).")

    # ---------- Recetas ----------
    rc = crudas["Recetas"]
    for c in ["producto_id", "insumo_id", "insumo_nombre", "unidad_medida"]:
        rc[c] = rc[c].astype(str).str.strip()
    rc["cantidad_por_unidad"] = _numerico(r, rc, "Recetas", "cantidad_por_unidad")
    rc["costo_unitario_insumo"] = _numerico(r, rc, "Recetas", "costo_unitario_insumo", obligatorio=False)
    for i in rc.index[~rc["producto_id"].isin(ids)]:
        r.add(ERROR, "Recetas", i + 2, "producto_id", f"'{rc['producto_id'][i]}' no existe en Productos.",
              "Corrige el código o agrega el producto.")
    for i in rc.index[~rc["unidad_medida"].isin(UNIDADES)]:
        r.add(ERROR, "Recetas", i + 2, "unidad_medida", f"Unidad '{rc['unidad_medida'][i]}' no reconocida.",
              f"Usa una de: {', '.join(UNIDADES)}.")
    from .utils import CONVERSION
    base = rc["unidad_medida"].map(lambda u: CONVERSION.get(u, (u, 1))[0])
    for ins, g in rc.assign(base=base).groupby("insumo_id"):
        if g["base"].nunique() > 1:
            r.add(ERROR, "Recetas", int(g.index[0]) + 2, "unidad_medida",
                  f"El insumo {ins} usa unidades incompatibles ({', '.join(sorted(set(g['unidad_medida'])))}).",
                  "Usa la misma familia de unidad (masa, volumen o unidad) para cada insumo.")
    for pid in sorted(ids - set(rc["producto_id"])):
        r.add(INFO, "Recetas", None, "producto_id", f"El producto {pid} no tiene receta.",
              "No se calcularán sus insumos.")
    if rc["costo_unitario_insumo"].notna().any() and not r.n_errores:
        cr = (rc["cantidad_por_unidad"] * rc["costo_unitario_insumo"]).groupby(rc["producto_id"]).sum(min_count=1)
        for i, fila in p.iterrows():
            c_rec = cr.get(fila["producto_id"], np.nan)
            c_imp = fila["precio_venta"] * (1 - fila["margen_esperado_pct"] / 100)
            if c_rec == c_rec and c_imp > 0 and abs(c_rec - c_imp) / c_imp > 0.25:
                r.add(ADVERTENCIA, "Productos", i + 2, "margen_esperado_pct",
                      f"{fila['producto_id']}: costo de receta S/ {c_rec:.2f} difiere >25% del costo implícito "
                      f"S/ {c_imp:.2f} (precio × (1 − margen)).",
                      "Revisa el margen o los costos de insumos. Se usará el margen declarado.")

    # ---------- Calendario y Producción real (opcionales) ----------
    cal = crudas.get("Calendario")
    if cal is not None and len(cal):
        cal["fecha"] = _fechas(r, cal, "Calendario")
        cal["abierto"] = cal["abierto"].map(lambda x: True if pd.isna(x) else si_no(x))
        cal["feriado"] = cal["feriado"].map(si_no)
        cal["evento"] = cal["evento"].fillna("").astype(str)
    pr = crudas.get("Produccion_real")
    if pr is not None and len(pr):
        pr["fecha"] = _fechas(r, pr, "Produccion_real")
        pr["producto_id"] = pr["producto_id"].astype(str).str.strip()
        pr["unidades_producidas"] = _numerico(r, pr, "Produccion_real", "unidades_producidas", entero=True)
        pr["unidades_sobrantes"] = _numerico(r, pr, "Produccion_real", "unidades_sobrantes", entero=True)
        for i in pr.index[~pr["producto_id"].isin(ids)]:
            r.add(ERROR, "Produccion_real", i + 2, "producto_id", f"'{pr['producto_id'][i]}' no existe en Productos.", "")
        for i in pr.index[pr["unidades_sobrantes"] > pr["unidades_producidas"]]:
            r.add(ERROR, "Produccion_real", i + 2, "unidades_sobrantes", "Sobrantes mayores que lo producido.", "")
    else:
        pr = None

    if r.n_errores:
        return r

    # ---------- Huecos y longitud ----------
    v = v.drop(index=v.index[dup])
    fechas = pd.DatetimeIndex(sorted(v["fecha"].unique()))
    rango = pd.date_range(fechas.min(), fechas.max(), freq="D")
    cerrados = set()
    if cal is not None and len(cal):
        cerrados = set(cal.loc[~cal["abierto"], "fecha"])
    r.huecos = [d for d in rango if d not in set(fechas) and d not in cerrados]
    for d in r.huecos:
        r.add(ADVERTENCIA, "Ventas", None, "fecha", f"No hay registros el {d.date()}.",
              "Indica abajo si ese día estuvo cerrado o si hubo venta cero.")
    n = len(rango) - len(cerrados & set(rango))
    if n < 7:
        r.add(ERROR, "Ventas", None, "fecha", f"Solo hay {n} días de datos.", "Se necesitan al menos 7 días.")
    elif n < 14:
        r.add(ADVERTENCIA, "Ventas", None, "fecha", f"Solo hay {n} días: resultados muy preliminares.",
              "Se recomiendan al menos 14 días (ideal 28 o más).")
    elif n < 28:
        r.add(INFO, "Ventas", None, "fecha", f"Hay {n} días de datos: se tratará como estudio piloto.",
              "Con 28 días o más se activan más modelos (Holt-Winters).")
    if v["agotado"].any():
        r.add(ADVERTENCIA, "Ventas", None, "agotado",
              f"{int(v['agotado'].sum())} registros marcados como agotado: la venta subestima la demanda (datos censurados).",
              "Se usarán igualmente; el sesgo se declara en las limitaciones.")

    r.datos = {"Productos": p, "Ventas": v[["fecha", "producto_id", "unidades_vendidas", "agotado"]],
               "Recetas": rc, "Calendario": cal, "Produccion_real": pr}
    return r


def completar_ventas(datos: dict, tratamiento: dict | None = None) -> pd.DataFrame:
    """Construye la matriz fecha × producto. tratamiento: {fecha: 'cerrado'|'cero'} para huecos."""
    v, p, cal = datos["Ventas"], datos["Productos"], datos.get("Calendario")
    rango = pd.date_range(v["fecha"].min(), v["fecha"].max(), freq="D")
    cerrados = set()
    if cal is not None and len(cal):
        cerrados |= set(cal.loc[~cal["abierto"], "fecha"])
    for d, t in (tratamiento or {}).items():
        if t == "cerrado":
            cerrados.add(pd.Timestamp(d))
    dias = [d for d in rango if d not in cerrados]
    m = v.pivot_table(index="fecha", columns="producto_id", values="unidades_vendidas", aggfunc="sum")
    m = m.reindex(index=dias, columns=list(p["producto_id"])).fillna(0).astype(float)
    m.index.name = "fecha"
    return m
