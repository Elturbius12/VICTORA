"""Pruebas del módulo «Mi negocio» (antes app de escritorio): base de datos, cálculos y pantallas."""
import io
import os
from datetime import date, timedelta

import pandas as pd
import pytest

CSV = os.path.join(os.path.dirname(__file__), "..", "datos_demo", "ventas_victoriana.csv")


@pytest.fixture()
def bd(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from victora.nucleo import database as db
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "t.db"))
    db.init_db()
    db.insertar_productos_default()
    with open(CSV, "rb") as f:
        db.importar_csv(io.BytesIO(f.read()), "ventas.csv")
    return db


def test_bd_registro_y_respaldo(bd):
    s = bd.contar_registros()
    assert s["productos"] == 32 and s["dias"] >= 12
    pid = int(bd.get_productos().iloc[0]["id"])
    bd.registrar_ventas_dia("2026-11-10", {pid: 7}, {pid: "feria"})
    v = bd.get_ventas(desde="2026-11-10", hasta="2026-11-10")
    assert int(v["unidades"].iloc[0]) == 7 and v["observacion"].iloc[0] == "feria"
    assert bd.marcar_dia_cerrado("2026-11-11") == 32
    copia = bd.respaldar_base()
    antes = bd.contar_registros()
    bd.registrar_ventas_dia("2026-11-12", {pid: 99})
    bd.restaurar_respaldo(copia)
    assert bd.contar_registros() == antes


def test_recomendaciones_y_seguimiento(bd):
    from victora.nucleo.reportes import backfill_historial_pronosticos, calcular_recomendaciones_todas
    res, _ = calcular_recomendaciones_todas()
    assert sum(r["pronostico"] is not None for r in res) > 10
    assert backfill_historial_pronosticos() > 0
    seg = bd.get_seguimiento(solo_con_real=True)
    assert len(seg) > 0 and "error" in seg


def test_puente_al_analisis_completo(bd):
    from victora.plantilla import _escribir
    from victora.validador import validar
    bd.guardar_recetas(pd.DataFrame([{"producto": "Clasica", "insumo_id": "I001", "insumo_nombre": "Pan",
                                      "cantidad_por_unidad": 1, "unidad_medida": "unidad",
                                      "costo_unitario_insumo": 0.5}]))
    r = validar(_escribir(bd.datos_para_analisis(), ejemplo=False))
    assert r.semaforo != "rojo", r.tabla()
    from victora.pipeline import ejecutar
    R = ejecutar(r.datos, {})
    assert R["n_productos"] == 32


def test_pantallas_negocio(bd, monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("VICTORA_SQLITE", bd.DB_PATH)
    app = os.path.join(os.path.dirname(__file__), "..", "app.py")
    at = AppTest.from_file(app, default_timeout=120).run()
    assert not at.exception, at.exception
    from victora.negocio_ui import TABS
    assert TABS == ["🏠 Resumen del día", "📋 Registro de Ventas", "🔮 Motor de Pronóstico", "📈 Seguimiento",
                    "📚 Módulo Educativo", "📊 Dashboard", "⚙️ Configuración"]  # orden del original
    for nombre in TABS:
        at.session_state["tabs_neg"] = nombre
        at.run()
        assert not at.exception, (nombre, at.exception)
        assert not at.error, (nombre, [e.value for e in at.error])
