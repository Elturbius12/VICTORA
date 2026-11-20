"""Pruebas del núcleo (sin interfaz gráfica) de La Victoriana.
Corre con: python -m pytest tests/ -v
"""
import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import numpy as np
import pandas as pd


@pytest.fixture
def db(monkeypatch):
    """Base de datos SQLite temporal y aislada para cada prueba."""
    tmp_dir = tempfile.mkdtemp()
    from core import database as dbmod
    monkeypatch.setattr(dbmod, "DB_DIR", tmp_dir)
    monkeypatch.setattr(dbmod, "DB_PATH", os.path.join(tmp_dir, "test.db"))
    dbmod.init_db()
    yield dbmod
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_init_db_crea_tablas(db):
    prods = db.get_productos()
    assert prods.empty  # no se auto-cargan productos de ejemplo


def test_fechas_especiales_sembradas(db):
    fe = db.get_fechas_especiales()
    assert len(fe) == len(db.FERIADOS_PERU_2026) + len(db.FECHAS_COMERCIALES_2026)
    assert "2026-12-25" in fe["fecha"].values


def test_insertar_productos_default_usa_catalogo_real(db):
    db.insertar_productos_default()
    prods = db.get_productos()
    nombres = set(prods["nombre"])
    assert "Gaseosa" in nombres
    assert "Arroz chaufa" not in nombres  # el genérico viejo ya no debe aparecer
    gaseosa = prods[prods["nombre"] == "Gaseosa"].iloc[0]
    assert gaseosa["tipo"] == "reventa"
    pizza = prods[prods["nombre"] == "Clasica"].iloc[0]
    assert pizza["tipo"] == "preparado"


def test_inferir_tipo():
    from core.database import inferir_tipo
    assert inferir_tipo(30, 1.0) == "reventa"
    assert inferir_tipo(1, 0.3) == "preparado"
    assert inferir_tipo(2, 0.4) == "preparado"


def test_precio_vacio_no_sobreescribe(db, tmp_path):
    db.agregar_producto("Pizza Test", precio=20.0, vida_util=1, recuperable=0.3, categoria="Pizza Personal")
    csv = tmp_path / "catalogo.csv"
    csv.write_text("producto,precio\nPizza Test,\n")
    db.importar_catalogo(str(csv))
    prods = db.get_productos()
    row = prods[prods["nombre"] == "Pizza Test"].iloc[0]
    assert row["precio"] == 20.0  # no se sobreescribió con NaN/0


def test_importar_catalogo_ignora_notas(db, tmp_path):
    csv = tmp_path / "catalogo.csv"
    csv.write_text(
        "producto,precio\n"
        "Pizza Real,20\n"
        "Llene esta columna solo con productos reales y no texto suelto como este ejemplo,\n"
    )
    act, cre, ign = db.importar_catalogo(str(csv))
    assert cre == 1
    assert ign == 1
    prods = db.get_productos()
    assert "Pizza Real" in set(prods["nombre"])
    assert not any(n.lower().startswith("llene") for n in prods["nombre"])


def test_importar_catalogo_case_insensitive_no_duplica(db, tmp_path):
    db.agregar_producto("gaseosa", precio=5.0)
    csv = tmp_path / "catalogo.csv"
    csv.write_text("producto,precio\nGaseosa,6\n")
    db.importar_catalogo(str(csv))
    prods = db.get_productos()
    assert len(prods[prods["nombre"].str.lower() == "gaseosa"]) == 1
    assert float(prods[prods["nombre"].str.lower() == "gaseosa"].iloc[0]["precio"]) == 6.0


def test_pivot_rellena_huecos_de_fecha(db):
    db.agregar_producto("X", precio=10)
    pid = db.get_productos().iloc[0]["id"]
    db.registrar_venta("2026-01-01", int(pid), 5)
    db.registrar_venta("2026-01-05", int(pid), 3)  # faltan 02,03,04
    pivot, faltantes = db.get_pivot_ventas()
    assert len(pivot) == 5  # 01 a 05 completos
    assert faltantes == ["2026-01-02", "2026-01-03", "2026-01-04"]
    assert pivot.loc["2026-01-02", "X"] == 0


def test_marcar_dia_cerrado(db):
    db.agregar_producto("A", precio=10)
    db.agregar_producto("B", precio=5)
    n = db.marcar_dia_cerrado("2026-02-01")
    assert n == 2
    ventas = db.get_ventas()
    assert (ventas["unidades"] == 0).all()
    assert (ventas["observacion"] == "Local cerrado").all()


def test_seguimiento_calcula_error(db):
    db.agregar_producto("X", precio=10)
    pid = int(db.get_productos().iloc[0]["id"])
    db.guardar_pronostico("2026-03-01", pid, pronostico=5.0, cantidad_sugerida=6, modelo="SES")
    db.registrar_venta("2026-03-01", pid, 8)
    seg = db.get_seguimiento()
    assert len(seg) == 1
    assert seg.iloc[0]["error"] == 3.0  # 8 real - 5 pronosticado


def test_backup(db, tmp_path):
    db.agregar_producto("X", precio=10)
    destino = db.respaldar_base(str(tmp_path))
    assert os.path.exists(destino)
    assert db.dias_desde_ultimo_respaldo() == 0


# ── Pruebas de selection.py / optimizer.py ──────────────────────────────

def test_modelos_faltantes():
    from core.selection import modelos_faltantes
    faltan = modelos_faltantes(12)
    assert "Holt-Winters semanal" in faltan
    assert faltan["Holt-Winters semanal"] == 9
    assert "Ingenuo (ayer)" not in faltan


def test_perfil_dia_semana_excluye_fechas_especiales():
    from core.models import perfil_dia_semana
    # 14 días, todos domingo=10, salvo un domingo con pico de 100 (feriado)
    dates = pd.date_range("2026-01-04", periods=14, freq="D")  # empieza domingo
    y = np.array([10.0 if d.dayofweek != 6 else 10.0 for d in dates])
    # Forzamos un domingo (índice 0) a tener un pico de feriado
    y[0] = 100.0
    nd = dates[-1] + pd.Timedelta(days=7)  # próximo domingo
    especiales = {dates[0].date().isoformat()}
    sin_filtro = perfil_dia_semana(y, dates, nd)
    con_filtro = perfil_dia_semana(y, dates, nd, fechas_especiales=especiales)
    assert con_filtro < sin_filtro  # el pico del feriado ya no infla el promedio


def test_razon_critica_caso_borde():
    from core.optimizer import razon_critica
    cr, c, cu, co = razon_critica(precio=0, margen=0.275, recuperable=0.0)
    assert cr == 1.0  # no debe dividir por cero


def test_cantidad_optima_no_negativa():
    from core.optimizer import cantidad_optima
    assert cantidad_optima(0, 1.0, 0.5) == 0
    assert cantidad_optima(5, 2.0, 0.9) >= 5


def test_calcular_recomendaciones_producto_nuevo_usa_categoria(db):
    # Producto A con 10 días de historial real
    db.agregar_producto("Pizza A", precio=16, categoria="Pizza Personal")
    pid_a = int(db.get_productos().iloc[0]["id"])
    base = pd.Timestamp("2026-01-01")
    for i in range(10):
        db.registrar_venta((base + pd.Timedelta(days=i)).date().isoformat(), pid_a, 5 + (i % 3))
    # Producto B, misma categoría, recién agregado (sin ventas)
    db.agregar_producto("Pizza B", precio=16, categoria="Pizza Personal")

    from core.reportes import calcular_recomendaciones_todas
    resultados, _ = calcular_recomendaciones_todas(guardar_historial=False)
    por_nombre = {r["nombre"]: r for r in resultados}
    assert por_nombre["Pizza A"]["pronostico"] is not None
    assert por_nombre["Pizza B"]["estimado_por_categoria"] is True
    assert por_nombre["Pizza B"]["pronostico"] is not None  # usó el promedio de la categoría


def test_calcular_recomendaciones_usa_tipo_para_accion(db):
    db.agregar_producto("Gaseosa", precio=5.5, vida_util=30, recuperable=1.0, categoria="Bebidas")
    pid = int(db.get_productos().iloc[0]["id"])
    base = pd.Timestamp("2026-01-01")
    for i in range(10):
        db.registrar_venta((base + pd.Timedelta(days=i)).date().isoformat(), pid, 3)
    from core.reportes import calcular_recomendaciones_todas
    resultados, _ = calcular_recomendaciones_todas(guardar_historial=False)
    r = next(x for x in resultados if x["nombre"] == "Gaseosa")
    assert r["accion"] == "comprar / reponer"
