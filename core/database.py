"""Base de datos SQLite para el registro de ventas de La Victoriana."""
import sqlite3
import os
import pandas as pd
from datetime import datetime, date

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "victoriana.db")


def _conn():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Crea las tablas si no existen."""
    conn = _conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE NOT NULL,
        precio REAL DEFAULT 0,
        vida_util_dias INTEGER DEFAULT 1,
        recuperable REAL DEFAULT 0.5,
        activo INTEGER DEFAULT 1
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
    """)
    conn.commit()
    conn.close()


def get_productos(solo_activos=True):
    """Devuelve DataFrame de productos."""
    conn = _conn()
    q = "SELECT * FROM productos"
    if solo_activos:
        q += " WHERE activo=1"
    q += " ORDER BY nombre"
    df = pd.read_sql(q, conn)
    conn.close()
    return df


def agregar_producto(nombre, precio=0, vida_util=1, recuperable=0.5):
    conn = _conn()
    try:
        conn.execute(
            "INSERT INTO productos (nombre, precio, vida_util_dias, recuperable) VALUES (?,?,?,?)",
            (nombre.strip(), precio, vida_util, recuperable))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # ya existe
    finally:
        conn.close()


def actualizar_producto(prod_id, **kwargs):
    conn = _conn()
    sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [prod_id]
    conn.execute(f"UPDATE productos SET {sets} WHERE id=?", vals)
    conn.commit()
    conn.close()


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


def registrar_ventas_dia(fecha_str, ventas_dict, observacion=""):
    """Registra ventas de múltiples productos en una fecha.
    ventas_dict: {producto_id: unidades}
    """
    conn = _conn()
    for pid, unidades in ventas_dict.items():
        conn.execute("""
            INSERT INTO ventas (fecha, producto_id, unidades, observacion)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(fecha, producto_id) DO UPDATE SET
                unidades=excluded.unidades,
                observacion=excluded.observacion
        """, (fecha_str, pid, unidades, observacion))
    conn.commit()
    conn.close()


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


def get_pivot_ventas():
    """Devuelve tabla pivote fecha x producto (como la que usa el motor).
    Retorna (pivot_df, fechas_sin_registro).
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
                           values="unidades", fill_value=0)
    pivot.index = pd.to_datetime(pivot.index)
    pivot = pivot.sort_index()
    return pivot, []


def importar_csv(ruta):
    """Importa CSV con columnas: fecha, producto, unidades."""
    df = pd.read_csv(ruta)
    # Normalizar nombres de columnas
    cols = {c.lower().strip(): c for c in df.columns}
    fecha_col = cols.get("fecha", df.columns[0])
    prod_col = cols.get("producto", df.columns[1])
    uni_col = cols.get("unidades", df.columns[2])

    conn = _conn()
    productos_cache = {}
    for _, row in df.iterrows():
        nombre = str(row[prod_col]).strip()
        if nombre not in productos_cache:
            cur = conn.execute("SELECT id FROM productos WHERE nombre=?", (nombre,))
            r = cur.fetchone()
            if r:
                productos_cache[nombre] = r[0]
            else:
                cur = conn.execute(
                    "INSERT INTO productos (nombre) VALUES (?)", (nombre,))
                productos_cache[nombre] = cur.lastrowid
        pid = productos_cache[nombre]
        fecha = str(row[fecha_col]).strip()
        uni = int(row[uni_col])
        conn.execute("""
            INSERT INTO ventas (fecha, producto_id, unidades)
            VALUES (?, ?, ?)
            ON CONFLICT(fecha, producto_id) DO UPDATE SET unidades=excluded.unidades
        """, (fecha, pid, uni))
    conn.commit()
    conn.close()
    return len(df)


def importar_catalogo(ruta):
    """Importa catálogo de productos (nombre + precio) desde CSV o Excel.
    Columnas esperadas: producto, precio (vida_util_dias y recuperable opcionales).
    Si el producto ya existe, actualiza su precio. Si no existe, lo crea.
    Devuelve (actualizados, creados).
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

    conn = _conn()
    actualizados, creados = 0, 0
    for _, row in df.iterrows():
        nombre = str(row[prod_col]).strip()
        if not nombre or nombre.lower() == "nan":
            continue
        try:
            precio = float(row[precio_col]) if precio_col is not None else 0.0
        except (ValueError, TypeError):
            precio = 0.0
        vida = 1
        if vida_col and pd.notna(row.get(vida_col)):
            try:
                vida = int(row[vida_col])
            except (ValueError, TypeError):
                vida = 1
        recup = 0.5
        if recup_col and pd.notna(row.get(recup_col)):
            try:
                recup = float(row[recup_col])
            except (ValueError, TypeError):
                recup = 0.5

        cur = conn.execute("SELECT id FROM productos WHERE nombre=?", (nombre,))
        r = cur.fetchone()
        if r:
            conn.execute(
                "UPDATE productos SET precio=?, vida_util_dias=?, recuperable=? WHERE id=?",
                (precio, vida, recup, r[0]))
            actualizados += 1
        else:
            conn.execute(
                "INSERT INTO productos (nombre, precio, vida_util_dias, recuperable) VALUES (?,?,?,?)",
                (nombre, precio, vida, recup))
            creados += 1
    conn.commit()
    conn.close()
    return actualizados, creados


def productos_sin_precio():
    """Devuelve lista de nombres de productos activos con precio=0 (no configurados)."""
    conn = _conn()
    rows = conn.execute("SELECT nombre FROM productos WHERE activo=1 AND (precio IS NULL OR precio<=0)").fetchall()
    conn.close()
    return [r[0] for r in rows]


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


# Productos por defecto de La Victoriana
PRODUCTOS_DEFAULT = [
    ("Pollo broaster", 10.0, 1, 0.3),
    ("Salchipapa", 7.0, 1, 0.5),
    ("Arroz chaufa", 10.0, 1, 0.4),
    ("Lomo saltado", 12.0, 1, 0.3),
    ("Pollo a la plancha", 10.0, 1, 0.3),
    ("Hamburguesa", 8.0, 1, 0.5),
    ("Alitas", 10.0, 1, 0.3),
    ("Empanada", 3.0, 1, 0.5),
    ("Papa rellena", 4.0, 1, 0.4),
    ("Sopa", 6.0, 1, 0.3),
    ("Ensalada", 5.0, 1, 0.2),
    ("Jugo", 5.0, 1, 0.0),
    ("Gaseosa", 3.0, 30, 1.0),
    ("Cafe / infusion", 3.0, 1, 0.0),
]


def insertar_productos_default():
    for nombre, precio, vida, recup in PRODUCTOS_DEFAULT:
        agregar_producto(nombre, precio, vida, recup)
