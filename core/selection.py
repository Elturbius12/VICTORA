"""Diagnóstico de demanda, backtesting y selección de modelo."""
import inspect
import numpy as np
import pandas as pd
from .models import MODELS, MODELOS_MIN_DIAS


def _llamar_modelo(f, y, d, nd, fechas_especiales):
    """Llama al modelo f(y, d, nd), pasándole también 'fechas_especiales'
    SOLO si ese modelo en particular sabe qué hacer con ese argumento
    (hoy, solo 'Perfil día de semana' lo usa, para no dejar que un pico
    de feriado distorsione el promedio de 'ese día de la semana')."""
    if "fechas_especiales" in inspect.signature(f).parameters:
        return f(y, d, nd, fechas_especiales=fechas_especiales)
    return f(y, d, nd)


def modelos_faltantes(dias_disponibles):
    """Devuelve {modelo: dias_que_faltan} para los modelos que con los
    días de historial actuales TODAVÍA no pueden correr (no es que sean
    malos, es que matemáticamente necesitan más días)."""
    faltan = {}
    for m, minimo in MODELOS_MIN_DIAS.items():
        if dias_disponibles < minimo:
            faltan[m] = minimo - dias_disponibles
    return faltan


def nivel_confianza(diag, n_modelos_probados):
    """Semáforo simple de qué tan confiable es el pronóstico de un
    producto, para no obligar al usuario a interpretar ADI/CV² o el
    número de días él mismo. Considera tanto el largo del calendario
    como cuántos de esos días tuvieron una venta real (un producto con
    16 días de calendario pero solo 2 ventas no es mucho más confiable
    que uno con 2 días de historial).
    Devuelve (icono, texto_corto)."""
    dias = diag["dias"]
    dias_con_venta = round((1 - diag["pct_cero"]) * dias)
    if dias < 7 or n_modelos_probados == 0 or dias_con_venta < 3:
        return "🔴", "Muy poca información todavía — tómalo con mucha cautela"
    if dias < 14 or dias_con_venta < 7 or diag["clase"] in ("Irregular (grumosa)",):
        return "🟡", "Información limitada — úsalo como referencia, no al pie de la letra"
    return "🟢", "Suficiente historial para confiar razonablemente"


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


def backtest(y, dates, min_train=5, fechas_especiales=None):
    """Origen rodante, 1 paso adelante. Devuelve (métricas por modelo, pronósticos)."""
    y = np.asarray(y, float)
    dates = pd.DatetimeIndex(dates)
    fechas_especiales = fechas_especiales or set()
    n = len(y)
    preds = {m: np.full(n, np.nan) for m in MODELS}
    for t in range(min_train, n):
        for m, f in MODELS.items():
            try:
                preds[m][t] = _llamar_modelo(f, y[:t], dates[:t], dates[t], fechas_especiales)
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


def pronosticar(y, dates, next_date, modelo, res, fechas_especiales=None):
    """Pronóstico del próximo día con el modelo elegido (soporta el ensamble)."""
    from .models import MODELS
    y = np.asarray(y, float)
    fechas_especiales = fechas_especiales or set()
    if modelo == "Ensamble (top 3)":
        top = [m for m in res.Modelo if m in MODELS][:3]
        vals = [_llamar_modelo(MODELS[m], y, dates, next_date, fechas_especiales) for m in top]
        vals = [v for v in vals if v == v]
        return float(np.mean(vals)) if vals else float(y.mean())
    v = _llamar_modelo(MODELS[modelo], y, dates, next_date, fechas_especiales)
    return float(v) if v == v else float(y.mean())


def pronosticar_horizonte(y, dates, modelo, res, dias, fechas_especiales=None):
    """Pronóstico ACUMULADO para los próximos 'dias' días (p.ej. "esta
    semana vas a vender aprox. Y en total"), re-alimentando cada
    pronóstico como si fuera dato real para pronosticar el día siguiente.
    Es una aproximación simple (no vuelve a correr el backtest cada día),
    pensada para dar una idea de volumen, no una cifra exacta día por día.
    Devuelve (total, [pronóstico_dia_1, pronóstico_dia_2, ...])."""
    y_ext = list(np.asarray(y, float))
    dates_ext = list(pd.DatetimeIndex(dates))
    diarios = []
    for i in range(dias):
        nd = dates_ext[-1] + pd.Timedelta(days=1)
        p = pronosticar(np.array(y_ext), pd.DatetimeIndex(dates_ext), nd, modelo, res, fechas_especiales)
        diarios.append(p)
        y_ext.append(p)
        dates_ext.append(nd)
    return float(np.sum(diarios)), diarios


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
