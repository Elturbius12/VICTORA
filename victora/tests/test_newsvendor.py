"""Newsvendor y explosión de materiales contra casos calculados a mano."""
import numpy as np
import pandas as pd
import pytest

from victora.decision import ajustar_lote, cantidad, costos, explosion_insumos


def test_costos_caso_mano():
    # p = 4.50, margen 50 % → c = 2.25; rescate 0.50 → Co = 1.75; Cu = 2.25; CR = 2.25 / 4 = 0.5625
    k = costos(4.50, 50, 0.50)
    assert k["c"] == pytest.approx(2.25)
    assert k["Co"] == pytest.approx(1.75)
    assert k["Cu"] == pytest.approx(2.25)
    assert k["CR"] == pytest.approx(0.5625)


def test_cuantil_y_lote():
    # pronóstico 20 + residuos −4..4 → demanda 16..24; cuantil 0.5625 = 16 + 0.5625 × 8 = 20.5
    q = cantidad(20, np.arange(-4, 5, dtype=float), 0.5625)
    assert q == pytest.approx(20.5)
    assert ajustar_lote(q, 1) == 21
    assert ajustar_lote(q, 10) == 30
    assert ajustar_lote(20.0, 1) == 20


def test_explosion_insumos():
    plan = pd.DataFrame({"fecha": pd.to_datetime(["2026-01-01", "2026-01-02"]), "producto_id": ["P1", "P1"],
                         "producir": [10, 20]})
    rec = pd.DataFrame({"producto_id": ["P1"], "insumo_id": ["I1"], "insumo_nombre": ["Harina"],
                        "cantidad_por_unidad": [0.06], "unidad_medida": ["kg"], "costo_unitario_insumo": [3.5]})
    _, sem = explosion_insumos(plan, rec)
    # 30 unidades × 60 g = 1800 g = 1,8 kg; costo 1,8 × 3,5 = 6,3
    assert sem["necesidad_semana"].iloc[0] == pytest.approx(1800)
    assert sem["comprar"].iloc[0] == pytest.approx(1.8) and sem["unidad"].iloc[0] == "kg"
    assert sem["costo_estimado"].iloc[0] == pytest.approx(6.3)
