"""Modelos de pronóstico para series cortas.

Firma común: f(y, h, dow, dow_fut) -> np.ndarray de longitud h (valores ≥ 0)
  y        serie de entrenamiento (np.ndarray)
  h        horizonte
  dow      día de la semana de cada observación de y (0 = lunes)
  dow_fut  día de la semana de cada periodo a pronosticar
"""
from __future__ import annotations

import warnings

import numpy as np


def naive(y, h, dow=None, dow_fut=None):
    """Naïve: repite el último valor."""
    return np.repeat(float(y[-1]), h)


def naive_estacional(y, h, dow=None, dow_fut=None, m=7):
    """Naïve estacional: mismo día de la semana anterior."""
    return np.array([float(y[len(y) - m + (i % m)]) for i in range(h)])


def media_movil(y, h, dow=None, dow_fut=None, k=3):
    """Media móvil de las últimas k observaciones."""
    return np.repeat(float(np.mean(y[-k:])), h)


def mm3(y, h, dow=None, dow_fut=None):
    return media_movil(y, h, k=3)


def mm7(y, h, dow=None, dow_fut=None):
    return media_movil(y, h, k=7)


def perfil_dia(y, h, dow, dow_fut, k=1.0):
    """Media por día de la semana con suavizado (contracción hacia la media global con peso k)."""
    y, dow = np.asarray(y, float), np.asarray(dow)
    g = y.mean()
    out = []
    for d in dow_fut:
        v = y[dow == d]
        out.append((v.sum() + k * g) / (len(v) + k))
    return np.array(out)


def _ses_nivel(y, alpha):
    nivel = y[0]
    sse = 0.0
    for t in range(1, len(y)):
        e = y[t] - nivel
        sse += e * e
        nivel += alpha * e
    return nivel, sse


def ses(y, h, dow=None, dow_fut=None):
    """Suavización exponencial simple; α elegido por mínimo SSE en rejilla 0,05–0,95."""
    y = np.asarray(y, float)
    mejor = min((_ses_nivel(y, a)[1], a) for a in np.arange(0.05, 0.96, 0.05))
    return np.repeat(_ses_nivel(y, mejor[1])[0], h)


def holt_winters(y, h, dow=None, dow_fut=None):
    """Holt-Winters aditivo (tendencia y estacionalidad semanal aditivas) con statsmodels."""
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        mod = ExponentialSmoothing(np.asarray(y, float) + 1e-6, trend="add", seasonal="add",
                                   seasonal_periods=7, initialization_method="estimated").fit()
        return np.asarray(mod.forecast(h))


def _croston_base(y, alpha=0.1):
    y = np.asarray(y, float)
    nz = np.flatnonzero(y > 0)
    if len(nz) == 0:
        return 0.0
    z, p, q = y[nz[0]], float(nz[0] + 1), 1
    for t in range(nz[0] + 1, len(y)):
        if y[t] > 0:
            z += alpha * (y[t] - z)
            p += alpha * (q - p)
            q = 1
        else:
            q += 1
    return z / p


def croston(y, h, dow=None, dow_fut=None, alpha=0.1):
    """Croston (1972): tamaño z / intervalo p, ambos con SES."""
    return np.repeat(_croston_base(y, alpha), h)


def sba(y, h, dow=None, dow_fut=None, alpha=0.1):
    """Syntetos–Boylan Approximation: Croston × (1 − α/2)."""
    return np.repeat(_croston_base(y, alpha) * (1 - alpha / 2), h)


def tsb(y, h, dow=None, dow_fut=None, alpha=0.1, beta=0.1):
    """Teunter–Syntetos–Babai: suaviza probabilidad de demanda y tamaño."""
    y = np.asarray(y, float)
    nz = y[y > 0]
    if len(nz) == 0:
        return np.zeros(h)
    prob, z = float((y > 0).mean()), float(nz[0])
    for v in y:
        if v > 0:
            prob += beta * (1 - prob)
            z += alpha * (v - z)
        else:
            prob += beta * (0 - prob)
    return np.repeat(prob * z, h)


# nombre -> (función, días mínimos de la serie completa para activarlo, mínimo de entrenamiento, solo_intermitente)
MODELOS = {
    "Naïve": (naive, 1, 1, False),
    "Naïve estacional": (naive_estacional, 14, 7, False),
    "Media móvil 3": (mm3, 1, 3, False),
    "Media móvil 7": (mm7, 1, 7, False),
    "Perfil día semana": (perfil_dia, 14, 7, False),
    "SES": (ses, 1, 3, False),
    "Holt-Winters": (holt_winters, 28, 14, False),
    "Croston": (croston, 1, 3, True),
    "SBA": (sba, 1, 3, True),
    "TSB": (tsb, 1, 3, True),
}


def modelos_activos(n_dias: int, intermitente: bool) -> list[str]:
    return [n for n, (_, dmin, _, solo_int) in MODELOS.items()
            if n_dias >= dmin and (intermitente or not solo_int)]


def pronosticar(nombre, y, h, dow, dow_fut) -> np.ndarray:
    f = MODELOS[nombre][0]
    out = np.asarray(f(np.asarray(y, float), h, np.asarray(dow), np.asarray(dow_fut)), float)
    return np.clip(np.nan_to_num(out, nan=0.0), 0, None)
