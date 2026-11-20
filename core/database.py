"""Base de datos SQLite para el registro de ventas de La Victoriana."""
import sqlite3
import os
import shutil
from datetime import datetime, date, timedelta
import pandas as pd

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "victoriana.db")


def _conn():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


#: Tipos de producto reconocidos. Esto es SOLO para que la interfaz use la
#: palabra correcta (no hay ningún cálculo de stock/inventario detrás,
#: porque el negocio no lleva ese control):
#: - "preparado": se cocina/arma cada día (pizzas, hamburguesas, jugos...).
#:   El sistema habla de "cantidad a preparar".
#: - "reventa": se compra ya hecho (p.ej. una gaseosa embotellada).
#:   El sistema habla de "cantidad a comprar / reponer".
TIPOS_PRODUCTO = ("preparado", "reventa")

#: Margen de ganancia por defecto (sobre el precio de venta) para un
#: producto nuevo, cuando el usuario todavía no lo ajustó a mano.
MARGEN_DEFECTO = 0.275

# Columnas que se agregaron después de la primera versión de la base de
# datos. Se usan para migrar (ALTER TABLE) una base ya existente sin borrar
# nada de lo que el usuario ya tenga registrado.
_COLUMNAS_NUEVAS_PRODUCTOS = {
    "tipo": "TEXT DEFAULT 'preparado'",
    "margen": f"REAL DEFAULT {MARGEN_DEFECTO}",
    "categoria": "TEXT DEFAULT ''",
}


def init_db():
    """Crea las tablas si no existen, migra columnas nuevas si falta alguna,
    y siembra el calendario de feriados/fechas especiales si está vacío."""
    conn = _conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE NOT NULL,
        precio REAL DEFAULT 0,
        vida_util_dias INTEGER DEFAULT 1,
        recuperable REAL DEFAULT 0.5,
        activo INTEGER DEFAULT 1,
        tipo TEXT DEFAULT 'preparado',
        margen REAL DEFAULT 0.275,
        categoria TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,
        producto_id INTEGER NOT NULL,
        unidades INTEGER NOT NULL DEFAULT 0,
        observacion TEXT DEFAULT '',
        FOREIGN KEY (producto_id) REFERENCES productos(id),
        UNIQUE(fecha, producto_id)
    );
    CREATE TABLE IF NOT EXISTS configuracion (
        clave TEXT PRIMARY KEY,
        valor TEXT
    );
    CREATE TABLE IF NOT EXISTS fechas_especiales (
        fecha TEXT PRIMARY KEY,
        nombre TEXT NOT NULL,
        origen TEXT DEFAULT 'manual'
    );
    CREATE TABLE IF NOT EXISTS pronosticos_historial (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,
        producto_id INTEGER NOT NULL,
        pronostico REAL,
        cantidad_sugerida REAL,
        modelo TEXT,
        creado_en TEXT,
        FOREIGN KEY (producto_id) REFERENCES productos(id),
        UNIQUE(fecha, producto_id)
    );
    """)
    conn.commit()
    _migrar_columnas_productos(conn)
    conn.close()
    sembrar_fechas_especiales_default()


def _migrar_columnas_productos(conn):
    """Agrega columnas nuevas a una base de datos ya existente (creada con
    una versión anterior de la app) sin tocar los datos que ya tiene el
    usuario. CREATE TABLE IF NOT EXISTS no modifica tablas existentes, así
    que las columnas agregadas después de la primera versión necesitan
    ALTER TABLE explícito."""
    existentes = {row[1] for row in conn.execute("PRAGMA table_info(productos)")}
    for col, definicion in _COLUMNAS_NUEVAS_PRODUCTOS.items():
        if col not in existentes:
            conn.execute(f"ALTER TABLE productos ADD COLUMN {col} {definicion}")
    conn.commit()


# ══════════════════════════════════════════════════════════════════════
#  Productos
# ══════════════════════════════════════════════════════════════════════

def get_productos(solo_activos=True):
    """Devuelve DataFrame de productos."""
    conn = _conn()
    q = "SELECT * FROM productos"
    if solo_activos:
        q += " WHERE activo=1"
    q += " ORDER BY categoria, nombre"
    df = pd.read_sql(q, conn)
    conn.close()
    return df


def inferir_tipo(vida_util_dias, recuperable):
    """Adivina si un producto es 'preparado' o 'reventa' a partir de su
    vida útil y qué tan recuperable es lo que sobra: algo que dura varias
    semanas y casi no se pierde si sobra (vida_util >= 7 y recuperable >= 0.9)
    casi siempre es un producto comprado ya hecho (reventa, como una
    gaseosa embotellada), no algo que se cocina cada día. Esto solo decide
    qué palabra usa la interfaz ("preparar" vs "comprar"); no hay ningún
    cálculo de inventario detrás."""
    try:
        vida_util_dias = int(vida_util_dias)
        recuperable = float(recuperable)
    except (TypeError, ValueError):
        return "preparado"
    if vida_util_dias >= 7 and recuperable >= 0.9:
        return "reventa"
    return "preparado"


def agregar_producto(nombre, precio=0, vida_util=1, recuperable=0.5,
                      tipo=None, margen=MARGEN_DEFECTO, categoria=""):
    if tipo not in TIPOS_PRODUCTO:
        tipo = inferir_tipo(vida_util, recuperable)
    conn = _conn()
    try:
        conn.execute(
            """INSERT INTO productos
               (nombre, precio, vida_util_dias, recuperable, tipo, margen, categoria)
               VALUES (?,?,?,?,?,?,?)""",
            (nombre.strip(), precio, vida_util, recuperable, tipo, margen, categoria.strip()))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # ya existe
    finally:
        conn.close()


def actualizar_producto(prod_id, **kwargs):
    if not kwargs:
        return
    conn = _conn()
    sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [prod_id]
    conn.execute(f"UPDATE productos SET {sets} WHERE id=?", vals)
    conn.commit()
    conn.close()


def productos_sin_precio():
    """Devuelve lista de nombres de productos activos con precio=0 (no configurados)."""
    conn = _conn()
    rows = conn.execute("SELECT nombre FROM productos WHERE activo=1 AND (precio IS NULL OR precio<=0)").fetchall()
    conn.close()
    return [r[0] for r in rows]


def promedio_categoria_diario(categoria, excluir_producto_id=None):
    """Para un producto nuevo sin historial propio: promedio diario de
    ventas de OTROS productos de la misma categoría (p.ej. otra 'Pizza
    Personal'), como punto de partida razonable mientras se junta
    historial propio. Devuelve None si no hay con qué comparar."""
    if not categoria:
        return None
    conn = _conn()
    prods = pd.read_sql(
        "SELECT id FROM productos WHERE categoria=? AND activo=1", conn, params=[categoria])
    ids = [i for i in prods["id"].tolist() if i != excluir_producto_id]
    if not ids:
        conn.close()
        return None
    q = f"""SELECT fecha, SUM(unidades) as u FROM ventas
            WHERE producto_id IN ({','.join('?' * len(ids))})
            GROUP BY fecha"""
    df = pd.read_sql(q, conn, params=ids)
    conn.close()
    if df.empty:
        return None
    # Promedio por producto y por día (para que sea comparable con un solo producto nuevo)
    return float(df["u"].sum()) / len(ids) / max(1, df["fecha"].nunique())


# ══════════════════════════════════════════════════════════════════════
#  Ventas
# ══════════════════════════════════════════════════════════════════════

def registrar_venta(fecha_str, producto_id, unidades, observacion=""):
    """Registra o actualiza la venta de un producto en una fecha."""
    conn = _conn()
    conn.execute("""
        INSERT INTO ventas (fecha, producto_id, unidades, observacion)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(fecha, producto_id) DO UPDATE SET
            unidades=excluded.unidades,
            observacion=excluded.observacion
    """, (fecha_str, producto_id, unidades, observacion))
    conn.commit()
    conn.close()


def registrar_ventas_dia(fecha_str, ventas_dict, observaciones=None):
    """Registra ventas de múltiples productos en una fecha.
    ventas_dict: {producto_id: unidades}
    observaciones: {producto_id: texto} (opcional, por producto)
    """
    observaciones = observaciones or {}
    conn = _conn()
    for pid, unidades in ventas_dict.items():
        obs = observaciones.get(pid, "")
        conn.execute("""
            INSERT INTO ventas (fecha, producto_id, unidades, observacion)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(fecha, producto_id) DO UPDATE SET
                unidades=excluded.unidades,
                observacion=CASE WHEN excluded.observacion != '' THEN excluded.observacion
                                  ELSE ventas.observacion END
        """, (fecha_str, pid, unidades, obs))
    conn.commit()
    conn.close()


def marcar_dia_cerrado(fecha_str, nota="Local cerrado"):
    """Registra 0 unidades para TODOS los productos activos en una fecha,
    de un solo golpe (en vez de tener que poner 0 producto por producto),
    y deja la nota en observación para que quede claro que fue un día
    cerrado y no simplemente 'no se vendió nada'."""
    conn = _conn()
    ids = [r[0] for r in conn.execute("SELECT id FROM productos WHERE activo=1").fetchall()]
    for pid in ids:
        conn.execute("""
            INSERT INTO ventas (fecha, producto_id, unidades, observacion)
            VALUES (?, ?, 0, ?)
            ON CONFLICT(fecha, producto_id) DO UPDATE SET
                unidades=0, observacion=excluded.observacion
        """, (fecha_str, pid, nota))
    conn.commit()
    conn.close()
    return len(ids)


def get_ventas(producto_id=None, desde=None, hasta=None):
    """Devuelve DataFrame de ventas con filtros opcionales."""
    conn = _conn()
    q = """SELECT v.fecha, p.nombre as producto, v.unidades, v.observacion
           FROM ventas v JOIN productos p ON v.producto_id = p.id WHERE 1=1"""
    params = []
    if producto_id:
        q += " AND v.producto_id=?"
        params.append(producto_id)
    if desde:
        q += " AND v.fecha>=?"
        params.append(desde)
    if hasta:
        q += " AND v.fecha<=?"
        params.append(hasta)
    q += " ORDER BY v.fecha, p.nombre"
    df = pd.read_sql(q, conn, params=params)
    conn.close()
    return df


def ultima_fecha_registrada():
    conn = _conn()
    r = conn.execute("SELECT MAX(fecha) FROM ventas").fetchone()
    conn.close()
    return r[0]


def get_pivot_ventas():
    """Devuelve tabla pivote fecha x producto (como la que usa el motor).

    IMPORTANTE: si un día no tiene NINGÚN registro de venta (no se abrió la
    tienda, o simplemente no se anotó nada ese día), antes ese día
    desaparecía por completo de la tabla, y los modelos de pronóstico
    (media móvil, Holt-Winters semanal, etc.) terminaban comparando días
    que en el calendario real estaban separados por varios días, como si
    fueran consecutivos. Eso hacía que, por ejemplo, "media móvil de 7
    días" en realidad mezclara semanas distintas sin que nadie se diera
    cuenta.

    Ahora se completa el calendario día por día entre la primera y la
    última fecha registrada, rellenando con 0 los días sin ningún
    registro.

    Retorna (pivot_df, fechas_sin_registro) donde fechas_sin_registro es
    la lista (ordenada) de fechas AAAA-MM-DD que no tenían ningún
    registro y se completaron con 0, para que la interfaz pueda avisarle
    al usuario que revise si de verdad no vendió nada esos días o si se
    le olvidó registrar (usar "Local cerrado" si de verdad no abrió).
    """
    conn = _conn()
    df = pd.read_sql("""
        SELECT v.fecha, p.nombre, v.unidades
        FROM ventas v JOIN productos p ON v.producto_id = p.id
        WHERE p.activo=1
        ORDER BY v.fecha
    """, conn)
    conn.close()
    if df.empty:
        return pd.DataFrame(), []
    pivot = df.pivot_table(index="fecha", columns="nombre",
                           values="unidades", fill_value=0, aggfunc="sum")
    pivot.index = pd.to_datetime(pivot.index)
    pivot = pivot.sort_index()

    dias_originales = set(pivot.index)
    calendario_completo = pd.date_range(pivot.index.min(), pivot.index.max(), freq="D")
    fechas_sin_registro = [d.date().isoformat() for d in calendario_completo
                            if d not in dias_originales]
    pivot = pivot.reindex(calendario_completo, fill_value=0)

    return pivot, fechas_sin_registro


# ══════════════════════════════════════════════════════════════════════
#  Importación de catálogo y de ventas históricas
# ══════════════════════════════════════════════════════════════════════

def importar_csv(ruta):
    """Importa CSV con columnas: fecha, producto, unidades."""
    df = pd.read_csv(ruta)
    cols = {c.lower().strip(): c for c in df.columns}
    fecha_col = cols.get("fecha", df.columns[0])
    prod_col = cols.get("producto", df.columns[1])
    uni_col = cols.get("unidades", df.columns[2])

    conn = _conn()
    productos_cache = {}
    n = 0
    for _, row in df.iterrows():
        nombre = str(row[prod_col]).strip()
        if not nombre or nombre.lower() == "nan":
            continue
        if nombre not in productos_cache:
            pid = _buscar_id_por_nombre_insensible(conn, nombre)
            if pid is None:
                cur = conn.execute(
                    "INSERT INTO productos (nombre, tipo, margen) VALUES (?,?,?)",
                    (nombre, inferir_tipo(1, 0.5), MARGEN_DEFECTO))
                pid = cur.lastrowid
            productos_cache[nombre] = pid
        pid = productos_cache[nombre]
        fecha = str(row[fecha_col]).strip()
        try:
            uni = int(float(row[uni_col]))
        except (ValueError, TypeError):
            continue
        conn.execute("""
            INSERT INTO ventas (fecha, producto_id, unidades)
            VALUES (?, ?, ?)
            ON CONFLICT(fecha, producto_id) DO UPDATE SET unidades=excluded.unidades
        """, (fecha, pid, uni))
        n += 1
    conn.commit()
    conn.close()
    return n


#: Longitud máxima razonable para un nombre de producto. Una fila cuyo
#: "nombre" sea más largo que esto casi siempre es una nota de texto
#: (instrucciones, advertencias) que quedó mezclada en la misma columna
#: del Excel, no un producto real (bug histórico: "productos basura").
_NOMBRE_PRODUCTO_MAX_LARGO = 60

#: Palabras con las que suelen empezar las notas/instrucciones que a veces
#: quedan en la misma columna que los productos del catálogo.
_PREFIJOS_NOTA = ("llene", "revisa", "nota:", "atención", "atencion",
                   "importante", "⚠", "ejemplo:", "ejemplo ")


def _fila_parece_nota_no_producto(nombre):
    """True si 'nombre' parece una nota de texto y no un producto real."""
    if len(nombre) > _NOMBRE_PRODUCTO_MAX_LARGO:
        return True
    bajo = nombre.lower()
    return any(bajo.startswith(p) for p in _PREFIJOS_NOTA)


def _buscar_id_por_nombre_insensible(conn, nombre):
    """Busca un producto por nombre ignorando mayúsculas/minúsculas y
    espacios extra, para no crear un producto duplicado solo porque el
    Excel lo escribió con otra capitalización (p.ej. 'gaseosa' vs
    'Gaseosa')."""
    objetivo = " ".join(nombre.split()).lower()
    cur = conn.execute("SELECT id, nombre FROM productos")
    for pid, n in cur.fetchall():
        if " ".join(n.split()).lower() == objetivo:
            return pid
    return None


def importar_catalogo(ruta):
    """Importa catálogo de productos desde CSV o Excel.

    Columnas reconocidas (todas menos 'producto' y 'precio' son
    opcionales): producto, precio, vida_util_dias, recuperable, tipo
    ('preparado' o 'reventa'), margen (0 a 1), categoria.

    Si el producto ya existe (comparando nombre sin importar mayúsculas
    ni espacios extra), actualiza sus datos. Si no existe, lo crea.
    Ignora filas vacías y filas que parecen notas de texto en vez de
    productos (nombres muy largos o que empiezan como una nota).
    Devuelve (actualizados, creados, ignorados).
    """
    if ruta.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(ruta)
    else:
        df = pd.read_csv(ruta)

    cols = {c.lower().strip(): c for c in df.columns}
    prod_col = cols.get("producto") or cols.get("nombre") or df.columns[0]
    precio_col = cols.get("precio") or (df.columns[1] if len(df.columns) > 1 else None)
    vida_col = cols.get("vida_util_dias") or cols.get("vida_util")
    recup_col = cols.get("recuperable")
    tipo_col = cols.get("tipo")
    margen_col = cols.get("margen")
    cat_col = cols.get("categoria") or cols.get("categoría")

    conn = _conn()
    actualizados, creados, ignorados = 0, 0, 0
    for _, row in df.iterrows():
        crudo = row[prod_col]
        if pd.isna(crudo):
            continue
        nombre = str(crudo).strip()
        if not nombre or nombre.lower() == "nan":
            continue
        if _fila_parece_nota_no_producto(nombre):
            ignorados += 1
            continue

        def _leer(col, caster):
            if col and pd.notna(row.get(col)):
                try:
                    return caster(row[col])
                except (ValueError, TypeError):
                    return None
            return None

        precio = _leer(precio_col, float)
        vida = _leer(vida_col, lambda v: int(float(v)))
        recup = _leer(recup_col, float)
        margen = _leer(margen_col, float)
        cat = _leer(cat_col, lambda v: str(v).strip())
        tipo = None
        if tipo_col and pd.notna(row.get(tipo_col)):
            cand = str(row[tipo_col]).strip().lower()
            if cand in TIPOS_PRODUCTO:
                tipo = cand

        pid = _buscar_id_por_nombre_insensible(conn, nombre)
        if pid:
            # Si una celda viene vacía, NO se sobreescribe el valor ya
            # guardado (bug histórico: un precio vacío se guardaba como
            # NaN y rompía todos los cálculos de ganancia). Solo se
            # actualiza lo que viene con un valor válido en el archivo.
            sets, vals = [], []
            for col, val in (("precio", precio), ("vida_util_dias", vida),
                              ("recuperable", recup), ("tipo", tipo),
                              ("margen", margen), ("categoria", cat)):
                if val is not None:
                    sets.append(f"{col}=?"); vals.append(val)
            if sets:
                vals.append(pid)
                conn.execute(f"UPDATE productos SET {', '.join(sets)} WHERE id=?", vals)
            actualizados += 1
        else:
            tipo_final = tipo or inferir_tipo(vida or 1, recup if recup is not None else 0.5)
            conn.execute(
                """INSERT INTO productos
                   (nombre, precio, vida_util_dias, recuperable, tipo, margen, categoria)
                   VALUES (?,?,?,?,?,?,?)""",
                (nombre, precio or 0.0, vida or 1, recup if recup is not None else 0.5,
                 tipo_final, margen if margen is not None else MARGEN_DEFECTO, cat or ""))
            creados += 1
    conn.commit()
    conn.close()
    return actualizados, creados, ignorados


# ══════════════════════════════════════════════════════════════════════
#  Configuración general
# ══════════════════════════════════════════════════════════════════════

def get_config(clave, default=None):
    conn = _conn()
    r = conn.execute("SELECT valor FROM configuracion WHERE clave=?", (clave,)).fetchone()
    conn.close()
    return r[0] if r else default


def set_config(clave, valor):
    conn = _conn()
    conn.execute("""
        INSERT INTO configuracion (clave, valor) VALUES (?, ?)
        ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor
    """, (clave, str(valor)))
    conn.commit()
    conn.close()


def contar_registros():
    """Devuelve dict con estadísticas rápidas."""
    conn = _conn()
    n_prod = conn.execute("SELECT COUNT(*) FROM productos WHERE activo=1").fetchone()[0]
    n_ventas = conn.execute("SELECT COUNT(*) FROM ventas").fetchone()[0]
    fechas = conn.execute("SELECT MIN(fecha), MAX(fecha), COUNT(DISTINCT fecha) FROM ventas").fetchone()
    conn.close()
    return {
        "productos": n_prod,
        "registros": n_ventas,
        "fecha_min": fechas[0],
        "fecha_max": fechas[1],
        "dias": fechas[2]
    }


# ══════════════════════════════════════════════════════════════════════
#  Copias de seguridad
# ══════════════════════════════════════════════════════════════════════

def respaldar_base(carpeta_destino):
    """Copia el archivo de base de datos (.db) a la carpeta indicada, con
    fecha y hora en el nombre, y registra cuándo se hizo el último
    respaldo (para poder avisar si ya pasó mucho tiempo)."""
    os.makedirs(carpeta_destino, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    destino = os.path.join(carpeta_destino, f"victoriana_respaldo_{ts}.db")
    shutil.copy2(DB_PATH, destino)
    set_config("ultimo_respaldo", datetime.now().isoformat())
    return destino


def dias_desde_ultimo_respaldo():
    """None si nunca se hizo un respaldo."""
    v = get_config("ultimo_respaldo")
    if not v:
        return None
    try:
        return (datetime.now() - datetime.fromisoformat(v)).days
    except ValueError:
        return None


# ══════════════════════════════════════════════════════════════════════
#  Fechas especiales (feriados + fechas comerciales + las que agregue el
#  usuario). Se usan para: (1) no mezclar un pico atípico con el patrón
#  normal de "ese día de la semana", y (2) avisar con anticipación.
# ══════════════════════════════════════════════════════════════════════

#: Feriados oficiales del Perú para 2026 (fuente: calendario de feriados
#: nacionales publicado por el Gobierno; Semana Santa calculada para la
#: fecha de Pascua 2026). El usuario puede corregir o agregar fechas desde
#: la interfaz si alguna cambiara oficialmente.
FERIADOS_PERU_2026 = [
    ("2026-01-01", "Año Nuevo"),
    ("2026-04-02", "Jueves Santo"),
    ("2026-04-03", "Viernes Santo"),
    ("2026-05-01", "Día del Trabajo"),
    ("2026-06-29", "San Pedro y San Pablo"),
    ("2026-07-28", "Fiestas Patrias"),
    ("2026-07-29", "Fiestas Patrias"),
    ("2026-08-06", "Batalla de Junín"),
    ("2026-08-30", "Santa Rosa de Lima"),
    ("2026-10-08", "Combate de Angamos"),
    ("2026-11-01", "Todos los Santos"),
    ("2026-12-08", "Inmaculada Concepción"),
    ("2026-12-09", "Batalla de Ayacucho"),
    ("2026-12-25", "Navidad"),
]

#: Fechas que no son feriado oficial pero mueven mucho las ventas en un
#: negocio de comida (se puede seguir agregando/editando desde la app).
FECHAS_COMERCIALES_2026 = [
    ("2026-02-14", "San Valentín"),
    ("2026-05-10", "Día de la Madre"),
    ("2026-06-21", "Día del Padre"),
    ("2026-10-31", "Halloween"),
    ("2026-12-24", "Nochebuena"),
    ("2026-12-31", "Año Nuevo (víspera)"),
]


def sembrar_fechas_especiales_default():
    """Carga el calendario de feriados y fechas comerciales 2026 SOLO la
    primera vez (si la tabla está vacía), para no pisar fechas que el
    usuario ya haya editado o borrado a propósito."""
    conn = _conn()
    n = conn.execute("SELECT COUNT(*) FROM fechas_especiales").fetchone()[0]
    if n == 0:
        for fecha, nombre in FERIADOS_PERU_2026:
            conn.execute(
                "INSERT OR IGNORE INTO fechas_especiales (fecha, nombre, origen) VALUES (?,?,'feriado')",
                (fecha, nombre))
        for fecha, nombre in FECHAS_COMERCIALES_2026:
            conn.execute(
                "INSERT OR IGNORE INTO fechas_especiales (fecha, nombre, origen) VALUES (?,?,'comercial')",
                (fecha, nombre))
        conn.commit()
    conn.close()


def get_fechas_especiales():
    conn = _conn()
    df = pd.read_sql("SELECT * FROM fechas_especiales ORDER BY fecha", conn)
    conn.close()
    return df


def agregar_fecha_especial(fecha, nombre, origen="manual"):
    conn = _conn()
    conn.execute("""
        INSERT INTO fechas_especiales (fecha, nombre, origen) VALUES (?,?,?)
        ON CONFLICT(fecha) DO UPDATE SET nombre=excluded.nombre, origen=excluded.origen
    """, (fecha, nombre, origen))
    conn.commit()
    conn.close()


def eliminar_fecha_especial(fecha):
    conn = _conn()
    conn.execute("DELETE FROM fechas_especiales WHERE fecha=?", (fecha,))
    conn.commit()
    conn.close()


def proxima_fecha_especial(desde=None):
    """Próxima fecha especial desde hoy (o desde 'desde'), o None."""
    desde = desde or date.today().isoformat()
    conn = _conn()
    r = conn.execute(
        "SELECT fecha, nombre FROM fechas_especiales WHERE fecha>=? ORDER BY fecha LIMIT 1",
        (desde,)).fetchone()
    conn.close()
    return {"fecha": r[0], "nombre": r[1]} if r else None


# ══════════════════════════════════════════════════════════════════════
#  Seguimiento: pronóstico guardado vs. venta real (para medir error)
# ══════════════════════════════════════════════════════════════════════

def guardar_pronostico(fecha, producto_id, pronostico, cantidad_sugerida, modelo):
    """Guarda el pronóstico que el sistema hizo PARA una fecha futura, de
    modo que cuando esa fecha ya pasó y se registró la venta real, se
    pueda comparar pronóstico vs. realidad (tabla de seguimiento)."""
    conn = _conn()
    conn.execute("""
        INSERT INTO pronosticos_historial
            (fecha, producto_id, pronostico, cantidad_sugerida, modelo, creado_en)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(fecha, producto_id) DO UPDATE SET
            pronostico=excluded.pronostico,
            cantidad_sugerida=excluded.cantidad_sugerida,
            modelo=excluded.modelo,
            creado_en=excluded.creado_en
    """, (fecha, producto_id, pronostico, cantidad_sugerida, modelo, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_historial_fechas_por_producto():
    """{producto_id: {fechas ya guardadas en pronosticos_historial}}.
    Sirve para no pisar, al rellenar el historial hacia atrás, un
    pronóstico que ya se calculó y guardó ese mismo día."""
    conn = _conn()
    cur = conn.execute("SELECT producto_id, fecha FROM pronosticos_historial")
    out = {}
    for pid, fecha in cur.fetchall():
        out.setdefault(pid, set()).add(fecha)
    conn.close()
    return out


def get_seguimiento(desde=None, hasta=None, solo_con_real=False):
    """Tabla día / producto / pronosticado / sugerido / venta real / error,
    para que el usuario vea qué tan bien está acertando el sistema y pueda
    anotar la razón de los errores grandes (reutiliza la misma columna de
    observación que ya tiene cada venta)."""
    conn = _conn()
    q = """
        SELECT h.fecha, p.nombre as producto, h.pronostico, h.cantidad_sugerida,
               h.modelo, v.unidades as real, v.observacion
        FROM pronosticos_historial h
        JOIN productos p ON h.producto_id = p.id
        LEFT JOIN ventas v ON v.fecha = h.fecha AND v.producto_id = h.producto_id
        WHERE 1=1
    """
    params = []
    if desde:
        q += " AND h.fecha>=?"; params.append(desde)
    if hasta:
        q += " AND h.fecha<=?"; params.append(hasta)
    if solo_con_real:
        q += " AND v.unidades IS NOT NULL"
    q += " ORDER BY h.fecha DESC, p.nombre"
    df = pd.read_sql(q, conn, params=params)
    conn.close()
    if df.empty:
        return df
    df["error"] = df["real"] - df["pronostico"]
    df["error_abs"] = df["error"].abs()
    df["error_pct"] = df.apply(
        lambda r: (r["error_abs"] / r["pronostico"]) if pd.notna(r["pronostico"]) and r["pronostico"] > 0 else None,
        axis=1)
    return df


# ══════════════════════════════════════════════════════════════════════
#  Catálogo de respaldo (si la tabla de productos queda vacía)
# ══════════════════════════════════════════════════════════════════════

# Catálogo real de La Victoriana (pizzería/snack bar en Juliaca), usado
# SOLO como respaldo si la tabla de productos queda vacía (p.ej. primera
# vez que se abre la app). Antes esta lista tenía platos genéricos
# ("Arroz chaufa", "Lomo saltado", "Ensalada"...) que no existen en este
# negocio; ahora son los 32 productos reales, con los precios del
# catálogo oficial (noviembre 2026).
#
# Formato: (nombre, precio, vida_util_dias, recuperable, tipo, categoria)
PRODUCTOS_DEFAULT = [
    ("Pizza Hawaiana Personal", 16.0, 1, 0.3, "preparado", "Pizza Personal"),
    ("Pizza Pepperoni Personal", 16.0, 1, 0.3, "preparado", "Pizza Personal"),
    ("Pizza Americana Personal", 15.5, 1, 0.3, "preparado", "Pizza Personal"),
    ("Pizza Tropical Personal", 21.0, 1, 0.3, "preparado", "Pizza Personal"),
    ("Pizza Carnivora Personal", 14.0, 1, 0.3, "preparado", "Pizza Personal"),
    ("Pizza Victoriana Personal", 17.5, 1, 0.3, "preparado", "Pizza Personal"),
    ("Pizza Mexicana Personal", 16.5, 1, 0.3, "preparado", "Pizza Personal"),
    ("Pizza Hawaiana Mediana", 28.5, 1, 0.3, "preparado", "Pizza Mediana"),
    ("Pizza Pepperoni Mediana", 27.0, 1, 0.3, "preparado", "Pizza Mediana"),
    ("Pizza Americana Mediana", 26.0, 1, 0.3, "preparado", "Pizza Mediana"),
    ("Pizza Tropical Mediana", 31.0, 1, 0.3, "preparado", "Pizza Mediana"),
    ("Pizza Hawaiana Familiar", 41.0, 1, 0.3, "preparado", "Pizza Familiar"),
    ("Pizza Pepperoni Familiar", 37.5, 1, 0.3, "preparado", "Pizza Familiar"),
    ("Pizza Americana Familiar", 38.5, 1, 0.3, "preparado", "Pizza Familiar"),
    ("Pizza Tropical Familiar", 42.5, 1, 0.3, "preparado", "Pizza Familiar"),
    ("Pizza Victoriana Familiar", 41.0, 1, 0.3, "preparado", "Pizza Familiar"),
    ("Pizza Mexicana Familiar", 39.0, 1, 0.3, "preparado", "Pizza Familiar"),
    ("Pizza Mixta Familiar", 6.5, 1, 0.3, "preparado", "Pizza Familiar"),
    ("Clasica", 8.0, 1, 0.3, "preparado", "Snacks"),
    ("Big Burger", 9.5, 1, 0.3, "preparado", "Snacks"),
    ("Chorizo", 9.0, 1, 0.3, "preparado", "Snacks"),
    ("Salchipollo", 5.5, 1, 0.3, "preparado", "Snacks"),
    ("Salchimixta", 5.0, 1, 0.3, "preparado", "Snacks"),
    ("Montada", 10.5, 1, 0.3, "preparado", "Snacks"),
    ("Pollo Broaster", 15.0, 1, 0.3, "preparado", "Snacks"),
    ("Papa Rellena", 2.0, 1, 0.3, "preparado", "Snacks"),
    ("Frappe", 12.0, 1, 0.0, "preparado", "Bebidas"),
    ("Frappe Oreo", 10.0, 1, 0.0, "preparado", "Bebidas"),
    ("Cafe/Infusion", 3.5, 1, 0.0, "preparado", "Bebidas"),
    ("Jugos y Limonada", 5.0, 1, 0.0, "preparado", "Bebidas"),
    ("Gaseosa", 5.5, 30, 1.0, "reventa", "Bebidas"),
    ("Postres", 2.5, 2, 0.4, "preparado", "Postres"),
]

#: Productos cuyo precio tiene poca evidencia detrás (1-2 apariciones en
#: las transacciones reales usadas para reconstruir precios unitarios) y
#: conviene confirmar con el dueño del negocio antes de confiar del todo
#: en la ganancia estimada que calcula el sistema para ellos.
PRODUCTOS_PRECIO_POR_CONFIRMAR = {
    "Pizza Mexicana Familiar", "Pizza Mixta Familiar", "Pollo Broaster", "Papa Rellena",
}


def insertar_productos_default():
    for nombre, precio, vida, recup, tipo, categoria in PRODUCTOS_DEFAULT:
        agregar_producto(nombre, precio, vida, recup, tipo=tipo,
                          margen=MARGEN_DEFECTO, categoria=categoria)
