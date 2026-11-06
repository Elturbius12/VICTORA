"""Diagnóstico de demanda, backtesting y selección de modelo."""
import numpy as np
import pandas as pd
from .models import MODELS


def diagnostico(y):
    """Clasificación Syntetos-Boylan: ADI (intervalo medio entre ventas) y CV²."""
    y = np.asarray(y, float)
    nz = y[y > 0]
    if len(nz) == 0:
        return dict(adi=np.inf, cv2=np.nan, clase="Sin ventas", dias=len(y), pct_cero=1.0)
    adi = len(y) / len(nz)
    cv2 = (nz.std() / nz.mean()) ** 2 if len(nz) > 1 else 0.0
    if adi < 1.32 and cv2 < 0.49:
        clase = "Suave (estable)"
    elif adi < 1.32:
        clase = "Errática (variable)"
    elif cv2 < 0.49:
        clase = "Intermitente"
    else:
        clase = "Irregular (grumosa)"
    return dict(adi=adi, cv2=cv2, clase=clase, dias=len(y), pct_cero=float((y == 0).mean()))


def modelos_sugeridos(clase):
    return {
        "Suave (estable)": ["Suavizamiento exp. simple", "Media móvil 7d", "Perfil día de semana", "Holt-Winters semanal"],
        "Errática (variable)": ["Perfil día de semana", "Regresión ridge (tend.+día)", "Holt amortiguado"],
        "Intermitente": ["Croston SBA", "TSB", "Croston"],
        "Irregular (grumosa)": ["TSB", "Croston SBA", "Media móvil 7d"],
    }.get(clase, ["Promedio histórico"])


def backtest(y, dates, min_train=5):
    """Origen rodante, 1 paso adelante. Devuelve (métricas por modelo, pronósticos)."""
    y = np.asarray(y, float)
    dates = pd.DatetimeIndex(dates)
    n = len(y)
    preds = {m: np.full(n, np.nan) for m in MODELS}
    for t in range(min_train, n):
        for m, f in MODELS.items():
            try:
                preds[m][t] = f(y[:t], dates[:t], dates[t])
            except Exception:
                preds[m][t] = np.nan
    # Ensamble: promedio de los 3 modelos con menor error acumulado hasta t-1
    ens = np.full(n, np.nan)
    for t in range(min_train + 2, n):
        errs = {}
        for m in MODELS:
            e = np.abs(y[min_train:t] - preds[m][min_train:t])
            if not np.isnan(e).any():
                errs[m] = e.mean()
        top = sorted(errs, key=errs.get)[:3]
        if top:
            ens[t] = np.mean([preds[m][t] for m in top])
    preds["Ensamble (top 3)"] = ens

    rows = []
    for m, p in preds.items():
        mask = ~np.isnan(p)
        mask[:min_train] = False
        k = mask.sum()
        if k < 3:
            continue
        e = y[mask] - p[mask]
        den = y[mask].sum()
        rows.append(dict(
            Modelo=m, N_pruebas=int(k),
            MAE=np.abs(e).mean(), RMSE=np.sqrt((e ** 2).mean()),
            wMAPE=(np.abs(e).sum() / den) if den > 0 else np.nan,
            Sesgo=e.mean(),
        ))
    res = pd.DataFrame(rows).sort_values("MAE").reset_index(drop=True) if rows else pd.DataFrame()
    return res, preds


def elegir_ganador(res, tolerancia=0.03):
    """Elige el modelo de menor MAE; si hay empate técnico (<3%), prefiere el más simple."""
    if res.empty:
        return None
    simples = ["Promedio histórico", "Media móvil 7d", "Media móvil 3d", "Suavizamiento exp. simple",
               "Perfil día de semana", "Ingenuo (ayer)"]
    best = res.iloc[0]
    cand = res[res.MAE <= best.MAE * (1 + tolerancia)]
    for s in simples:
        if s in cand.Modelo.values:
            return s
    return best.Modelo


def pronosticar(y, dates, next_date, modelo, res):
    """Pronóstico del próximo día con el modelo elegido (soporta el ensamble)."""
    from .models import MODELS
    y = np.asarray(y, float)
    if modelo == "Ensamble (top 3)":
        top = [m for m in res.Modelo if m in MODELS][:3]
        vals = [MODELS[m](y, dates, next_date) for m in top]
        vals = [v for v in vals if v == v]
        return float(np.mean(vals)) if vals else float(y.mean())
    v = MODELS[modelo](y, dates, next_date)
    return float(v) if v == v else float(y.mean())


def simular_politica(y, preds_modelo, precio, margen, recuperable, cr, rmse, factor_base=1.3, min_train=5):
    """Compara, en los días del backtest, la producción 'habitual' (promedio 7d × factor)
    contra la producción del método. Devuelve dict de utilidad/sobrantes/faltantes."""
    from .optimizer import cantidad_optima, utilidad
    c = precio * (1 - margen)
    out = {"base": dict(u=0, sobra=0, falta=0, prod=0), "modelo": dict(u=0, sobra=0, falta=0, prod=0)}
    for t in range(min_train, len(y)):
        if np.isnan(preds_modelo[t]):
            continue
        D = y[t]
        qb = int(np.ceil(np.mean(y[max(0, t - 7):t]) * factor_base))
        qm = cantidad_optima(preds_modelo[t], rmse, cr)
        for k, Q in (("base", qb), ("modelo", qm)):
            out[k]["u"] += utilidad(Q, D, precio, c, recuperable)
            out[k]["sobra"] += max(Q - D, 0)
            out[k]["falta"] += max(D - Q, 0)
            out[k]["prod"] += Q
    return out
