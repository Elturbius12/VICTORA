"""Validación por origen rodante (rolling origin) y selección automática del modelo."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .modelos import MODELOS, modelos_activos, pronosticar

COMBINACION = "Combinación (top 3)"
MAX_PRUEBA = 28  # con series largas se evalúan solo los últimos 28 orígenes (4 semanas)


def inicio_prueba(n: int, activos: list[str]) -> int:
    """Primer origen de prueba: entrenamiento mínimo 10 días (≥ 7 si la serie es muy corta)."""
    req = max(MODELOS[m][2] for m in activos)
    return max(req, 7, min(10, n - 3), n - MAX_PRUEBA)


def metricas(real, pred, escala_abs, escala_cuad) -> dict:
    e = np.asarray(real) - np.asarray(pred)
    mae = np.mean(np.abs(e))
    mse = np.mean(e ** 2)
    suma = np.sum(np.abs(real))
    return {"MASE": mae / escala_abs, "RMSSE": np.sqrt(mse / escala_cuad), "MAE": mae,
            "RMSE": np.sqrt(mse), "WAPE": np.sum(np.abs(e)) / suma * 100 if suma > 0 else np.nan,
            "Sesgo": np.mean(pred - np.asarray(real))}


def escalas(y_train) -> tuple[float, float]:
    d = np.diff(np.asarray(y_train, float))
    a, c = np.mean(np.abs(d)) if len(d) else 0, np.mean(d ** 2) if len(d) else 0
    base = max(np.mean(y_train), 1.0)
    return (a if a > 0 else base), (c if c > 0 else base ** 2)


def evaluar_producto(y: pd.Series, intermitente: bool, n_total: int) -> dict:
    """Backtesting de todos los modelos activos para un producto."""
    vals, dow = y.values.astype(float), y.index.dayofweek.values
    activos = modelos_activos(n_total, intermitente)
    t0 = inicio_prueba(len(vals), activos)
    preds = {m: [] for m in activos}
    for t in range(t0, len(vals)):
        for m in activos:
            preds[m].append(pronosticar(m, vals[:t], 1, dow[:t], dow[t:t + 1])[0])
    real = vals[t0:]
    sa, sc = escalas(vals[:t0])
    principal = "RMSSE" if intermitente else "MASE"
    rank = []
    for m in activos:
        rank.append({"modelo": m, **metricas(real, np.array(preds[m]), sa, sc)})
    rank = pd.DataFrame(rank).sort_values(principal, kind="stable").reset_index(drop=True)
    top = list(rank["modelo"].head(3))
    preds[COMBINACION] = list(np.mean([preds[m] for m in top], axis=0))
    rank = pd.concat([rank, pd.DataFrame([{"modelo": COMBINACION, **metricas(real, np.array(preds[COMBINACION]), sa, sc)}])])
    rank = rank.sort_values(principal, kind="stable").reset_index(drop=True)
    rank["posicion"] = np.arange(1, len(rank) + 1)
    rank["metrica_principal"] = principal
    ganador = rank["modelo"].iloc[0]
    fechas = y.index[t0:]
    bt = pd.concat([pd.DataFrame({"fecha": fechas, "modelo": m, "real": real, "pronostico": preds[m]})
                    for m in preds], ignore_index=True)
    bt["error"] = bt["real"] - bt["pronostico"]
    return {"ranking": rank, "backtest": bt, "ganador": ganador, "top3": top, "t0": t0,
            "residuos": real - np.array(preds[ganador]), "pred_ganador": np.array(preds[ganador]),
            "real": real, "fechas_prueba": fechas}


def pronostico_futuro(y: pd.Series, modelo: str, top3: list[str], h: int = 7):
    """Pronóstico h días hacia adelante con el modelo ganador entrenado con toda la serie."""
    vals, dow = y.values.astype(float), y.index.dayofweek.values
    fechas = pd.date_range(y.index[-1], periods=h + 1, freq="D")[1:]
    dfu = fechas.dayofweek.values
    if modelo == COMBINACION:
        f = np.mean([pronosticar(m, vals, h, dow, dfu) for m in top3], axis=0)
    else:
        f = pronosticar(modelo, vals, h, dow, dfu)
    return fechas, f


def seleccionar(m: pd.DataFrame, clasif: pd.DataFrame) -> dict:
    inter = clasif.set_index("producto_id")["intermitente"]
    res = {}
    for pid in m.columns:
        r = evaluar_producto(m[pid], bool(inter[pid]), len(m))
        r["fechas_fut"], r["pron_fut"] = pronostico_futuro(m[pid], r["ganador"], r["top3"])
        res[pid] = r
    return res
