"""Modelos de pronóstico (1 paso adelante) para series diarias cortas.

Cada modelo es una función f(y, dates, next_date) -> pronóstico (float >= 0)
donde y es el historial de unidades vendidas (np.array) y dates las fechas
(pd.DatetimeIndex) de cada observación. Sin dependencias pesadas (solo numpy).
"""
import numpy as np
import pandas as pd

MIN_OBS = {"Ingenuo (ayer)": 1}

#: Cuántos días de historial necesita cada modelo para poder correr (no
#: para que YA sea bueno, solo para que matemáticamente pueda calcularse).
#: Se usa para explicarle al usuario por qué un modelo "no aparece todavía"
#: en vez de dejarlo sin explicación, y cuántos días le faltan.
MODELOS_MIN_DIAS = {
    "Ingenuo (ayer)": 2,
    "Promedio histórico": 3,
    "Media móvil 3d": 3,
    "Media móvil 7d": 7,
    "Suavizamiento exp. simple": 3,
    "Holt amortiguado": 5,
    "Perfil día de semana": 7,
    "Holt-Winters semanal": 21,
    "Croston": 3,
    "Croston SBA": 3,
    "TSB": 3,
    "Regresión ridge (tend.+día)": 7,
    "Ensamble (top 3)": 8,
}


def _ses_level(y, alpha):
    l = y[0]
    for v in y[1:]:
        l = alpha * v + (1 - alpha) * l
    return l


def _best_alpha(y, grid=np.linspace(0.05, 0.95, 19)):
    if len(y) < 4:
        return 0.3
    best, ba = np.inf, 0.3
    for a in grid:
        l, err = y[0], 0.0
        for v in y[1:]:
            err += (v - l) ** 2
            l = a * v + (1 - a) * l
        if err < best:
            best, ba = err, a
    return ba


def naive(y, d, nd):
    return float(y[-1])


def promedio_total(y, d, nd):
    return float(np.mean(y))


def media_movil_3(y, d, nd):
    return float(np.mean(y[-3:]))


def media_movil_7(y, d, nd):
    return float(np.mean(y[-7:]))


def ses(y, d, nd):
    return float(_ses_level(y, _best_alpha(y)))


def holt_amortiguado(y, d, nd, phi=0.8):
    if len(y) < 5:
        return ses(y, d, nd)
    best = (np.inf, 0.3, 0.1)
    for a in (0.1, 0.3, 0.5, 0.7):
        for b in (0.05, 0.1, 0.2, 0.4):
            l, t, err = y[0], 0.0, 0.0
            for v in y[1:]:
                f = l + phi * t
                err += (v - f) ** 2
                ln = a * v + (1 - a) * (l + phi * t)
                t = b * (ln - l) + (1 - b) * phi * t
                l = ln
            if err < best[0]:
                best = (err, a, b)
    _, a, b = best
    l, t = y[0], 0.0
    for v in y[1:]:
        ln = a * v + (1 - a) * (l + phi * t)
        t = b * (ln - l) + (1 - b) * phi * t
        l = ln
    return max(0.0, float(l + phi * t))


def perfil_dia_semana(y, d, nd, fechas_especiales=None):
    """Promedio del mismo día de la semana, encogido hacia el promedio general
    (con pocos datos, evita sobreajustar a 1-2 observaciones).

    Si se pasa 'fechas_especiales' (un set de fechas AAAA-MM-DD, p.ej.
    feriados o el Día de la Madre), esos días se excluyen del promedio:
    un pico atípico de un feriado no debe hacer creer que "ese día de la
    semana" vende más de lo normal."""
    y = np.asarray(y, float)
    d = pd.DatetimeIndex(d)
    wd = np.asarray(d.dayofweek)
    mask = wd == pd.Timestamp(nd).dayofweek
    if fechas_especiales:
        especial = np.asarray([ts.date().isoformat() in fechas_especiales for ts in d])
        mask = mask & ~especial
    n = mask.sum()
    normales = ~np.asarray([ts.date().isoformat() in fechas_especiales for ts in d]) if fechas_especiales else np.ones(len(y), dtype=bool)
    g = y[normales].mean() if normales.any() else y.mean()
    if n == 0:
        return float(g)
    k = 2.0  # fuerza del encogimiento
    return float((y[mask].sum() + k * g) / (n + k))


def seasonal_hw(y, d, nd):
    """Holt-Winters aditivo con estacionalidad semanal (m=7). Requiere >= 3
    semanas de datos; si no, cae a SES (el motor lo marca como no elegible)."""
    m = 7
    y = np.asarray(y, float)
    if len(y) < 3 * m:
        return np.nan
    best = (np.inf, 0.3, 0.05, 0.3)
    def run(a, b, g):
        l = y[:m].mean(); t = 0.0
        s = list(y[:m] - l)
        err = 0.0
        for i in range(m, len(y)):
            f = l + t + s[i - m]
            err += (y[i] - f) ** 2
            ln = a * (y[i] - s[i - m]) + (1 - a) * (l + t)
            t = b * (ln - l) + (1 - b) * t
            s.append(g * (y[i] - ln) + (1 - g) * s[i - m])
            l = ln
        return err, l, t, s
    for a in (0.1, 0.3, 0.5):
        for b in (0.01, 0.05, 0.1):
            for g in (0.1, 0.3, 0.5):
                e = run(a, b, g)[0]
                if e < best[0]:
                    best = (e, a, b, g)
    _, l, t, s = run(*best[1:])
    return max(0.0, float(l + t + s[len(y) - m]))


def _croston_core(y, alpha=0.1, variant="classic"):
    y = np.asarray(y, float)
    nz = np.nonzero(y)[0]
    if len(nz) == 0:
        return 0.0
    z = y[nz[0]]
    p = float(nz[0] + 1)
    q = 1
    for v in y[nz[0] + 1:]:
        if v > 0:
            z = alpha * v + (1 - alpha) * z
            p = alpha * q + (1 - alpha) * p
            q = 1
        else:
            q += 1
    f = z / p
    if variant == "sba":
        f *= (1 - alpha / 2)
    return float(f)


def croston(y, d, nd):
    return _croston_core(y, 0.1, "classic")


def croston_sba(y, d, nd):
    return _croston_core(y, 0.1, "sba")


def tsb(y, d, nd, alpha=0.2, beta=0.1):
    """Teunter-Syntetos-Babai: actualiza la probabilidad de demanda cada día,
    útil cuando un producto puede 'dejar de venderse' (obsolescencia)."""
    y = np.asarray(y, float)
    nz = y[y > 0]
    if len(nz) == 0:
        return 0.0
    p = (y > 0).mean()
    z = nz[0]
    for v in y:
        if v > 0:
            z = alpha * v + (1 - alpha) * z
            p = beta * 1 + (1 - beta) * p
        else:
            p = (1 - beta) * p
    return float(p * z)


def regresion_ridge(y, d, nd, lam=3.0):
    """Regresión ridge con tendencia lineal + día de la semana (dummies)."""
    y = np.asarray(y, float)
    if len(y) < 7:
        return np.nan
    d = pd.DatetimeIndex(d)
    def feat(idx, t0):
        X = np.zeros((len(idx), 8))
        X[:, 0] = 1
        X[:, 1] = (idx - t0).days / 7.0
        X[np.arange(len(idx)), 2 + np.minimum(np.asarray(idx.dayofweek), 5)] = 1  # lun..sáb
        return X[:, :8]
    X = feat(d, d[0])
    Xn = feat(pd.DatetimeIndex([nd]), d[0])
    R = lam * np.eye(X.shape[1]); R[0, 0] = 0
    w = np.linalg.solve(X.T @ X + R, X.T @ y)
    return max(0.0, float(Xn @ w))


MODELS = {
    "Ingenuo (ayer)": naive,
    "Promedio histórico": promedio_total,
    "Media móvil 3d": media_movil_3,
    "Media móvil 7d": media_movil_7,
    "Suavizamiento exp. simple": ses,
    "Holt amortiguado": holt_amortiguado,
    "Perfil día de semana": perfil_dia_semana,
    "Holt-Winters semanal": seasonal_hw,
    "Croston": croston,
    "Croston SBA": croston_sba,
    "TSB": tsb,
    "Regresión ridge (tend.+día)": regresion_ridge,
}

DESCRIPCION = {
    "Ingenuo (ayer)": "Pronostica lo mismo que ayer. Referencia mínima.",
    "Promedio histórico": "Promedio de todos los días. Bueno si la demanda es estable.",
    "Media móvil 3d": "Promedio de los últimos 3 días: reacciona rápido.",
    "Media móvil 7d": "Promedio de la última semana: suaviza el ruido.",
    "Suavizamiento exp. simple": "Da más peso a los días recientes (alfa optimizado).",
    "Holt amortiguado": "Captura tendencia que se va frenando (crecimiento/caída).",
    "Perfil día de semana": "Usa lo que se vende cada día de la semana (encogido al promedio).",
    "Holt-Winters semanal": "Nivel + tendencia + estacionalidad semanal. Necesita ≥3 semanas.",
    "Croston": "Para demanda intermitente (muchos días en cero).",
    "Croston SBA": "Croston corregido por sesgo (Syntetos-Boylan).",
    "TSB": "Intermitente con probabilidad de demanda que se actualiza a diario.",
    "Regresión ridge (tend.+día)": "Tendencia lineal + efecto día de semana, regularizada.",
}
