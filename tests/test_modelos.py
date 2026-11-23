"""Cada modelo contra un caso calculado a mano."""
import numpy as np
import pytest

from victora import modelos as M

Y = np.array([4, 6, 5, 7, 3, 8, 9, 5, 6, 4, 7, 5, 9, 10], float)
DOW = np.arange(14) % 7


def test_naive():
    assert M.naive(Y, 3).tolist() == [10, 10, 10]


def test_naive_estacional():
    # y[7], y[8], y[9] = 5, 6, 4
    assert M.naive_estacional(Y, 3).tolist() == [5, 6, 4]


def test_medias_moviles():
    assert M.mm3(Y, 1)[0] == pytest.approx((5 + 9 + 10) / 3)
    assert M.mm7(Y, 1)[0] == pytest.approx((5 + 6 + 4 + 7 + 5 + 9 + 10) / 7)


def test_perfil_dia():
    # lunes (0): observaciones 4 y 5; con k = 1: (4 + 5 + media_global) / 3
    g = Y.mean()
    assert M.perfil_dia(Y, 1, DOW, np.array([0]))[0] == pytest.approx((4 + 5 + g) / 3)


def test_ses_alpha_fijo():
    nivel, sse = M._ses_nivel(np.array([10, 20, 30], float), 0.5)
    # nivel: 10 -> 10 + .5*10 = 15 -> 15 + .5*15 = 22.5 ; SSE = 10² + 15² = 325
    assert nivel == pytest.approx(22.5)
    assert sse == pytest.approx(325)


def test_croston_sba_tsb():
    y = np.array([0, 3, 0, 0, 6], float)
    # inicio z = 3, p = 2; en t = 4 (q = 3): z = 3 + .1*3 = 3.3; p = 2 + .1*(3 − 2) = 2.1
    assert M.croston(y, 1)[0] == pytest.approx(3.3 / 2.1)
    assert M.sba(y, 1)[0] == pytest.approx(3.3 / 2.1 * 0.95)
    # TSB: prob0 = 0.4, z0 = 3; 0→.36; 3→.424 (z=3); 0→.3816; 0→.34344; 6→.409096 (z=3.3)
    assert M.tsb(y, 1)[0] == pytest.approx(0.409096 * 3.3)


def test_holt_winters_y_no_negativos():
    y = np.tile([5, 6, 7, 8, 9, 14, 12], 4).astype(float)
    f = M.pronosticar("Holt-Winters", y, 7, np.arange(28) % 7, np.arange(28, 35) % 7)
    assert np.allclose(f, [5, 6, 7, 8, 9, 14, 12], atol=0.6)
    assert (M.pronosticar("Naïve", np.array([0, 0.0]), 2, [0, 1], [2, 3]) >= 0).all()


def test_activacion_por_longitud():
    assert "Naïve estacional" not in M.modelos_activos(10, False)
    assert "Holt-Winters" not in M.modelos_activos(21, False)
    assert "Holt-Winters" in M.modelos_activos(28, False)
    assert "Croston" in M.modelos_activos(21, True) and "Croston" not in M.modelos_activos(21, False)
