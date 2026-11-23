"""Pruebas de hipótesis y bootstrap sobre los costos simulados."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from .config import N_BOOT, SEMILLA


def _pareado(det: pd.DataFrame) -> pd.DataFrame:
    return det.pivot_table(index=["producto_id", "fecha"], columns="politica", values="costo_total")


def rank_biserial(x, y) -> float:
    """Correlación biserial de rangos para Wilcoxon pareado (Kerby, 2014)."""
    d = np.asarray(x) - np.asarray(y)
    d = d[d != 0]
    if len(d) == 0:
        return 0.0
    r = stats.rankdata(np.abs(d))
    return float((r[d > 0].sum() - r[d < 0].sum()) / r.sum())


def wilcoxon(det: pd.DataFrame) -> pd.DataFrame:
    """Wilcoxon de rangos con signo: costo diario de VICTORA (P4) vs cada política."""
    w = _pareado(det)
    filas = []
    for pol in [c for c in w.columns if c != "P4"]:
        x, y = w[pol].values, w["P4"].values
        try:
            res = stats.wilcoxon(x, y, zero_method="wilcox", alternative="two-sided")
            stat, p = float(res.statistic), float(res.pvalue)
        except ValueError:
            stat, p = np.nan, np.nan
        filas.append({"comparacion": f"{pol} vs P4", "n_pares": int(np.sum(x != y)),
                      "mediana_dif_S/": float(np.median(x - y)), "media_dif_S/": float(np.mean(x - y)),
                      "W": stat, "p_valor": p, "r_rank_biserial": rank_biserial(x, y),
                      "significativo_5pct": "Sí" if p == p and p < 0.05 else "No"})
    out = pd.DataFrame(filas)
    if len(out):  # corrección de Holm
        orden = np.argsort(out["p_valor"].fillna(1).values)
        m = len(out)
        adj = np.empty(m)
        acum = 0
        for k, i in enumerate(orden):
            acum = max(acum, min(1, (m - k) * out["p_valor"].fillna(1).values[i]))
            adj[i] = acum
        out["p_Holm"] = adj
    return out


def friedman(det: pd.DataFrame) -> dict:
    w = _pareado(det).dropna()
    try:
        chi, p = stats.friedmanchisquare(*[w[c].values for c in w.columns])
    except ValueError:
        chi, p = np.nan, np.nan
    n, k = w.shape
    kendall_w = chi / (n * (k - 1)) if n and chi == chi else np.nan
    rangos = w.rank(axis=1).mean()
    return {"chi2": float(chi), "gl": k - 1, "p_valor": float(p), "n_bloques": n,
            "W_Kendall": float(kendall_w), "rangos_medios": rangos.to_dict()}


def bootstrap_ahorro(det: pd.DataFrame, n_boot: int = N_BOOT, semilla: int = SEMILLA) -> dict:
    """IC 95% percentil del ahorro (S/ y %) de P4 frente a P0, remuestreando producto-días."""
    w = _pareado(det)[["P0", "P4"]].values
    rng = np.random.default_rng(semilla)
    idx = rng.integers(0, len(w), size=(n_boot, len(w)))
    p0, p4 = w[idx, 0].sum(axis=1), w[idx, 1].sum(axis=1)
    ah = p0 - p4
    pct = np.where(p0 > 0, ah / p0 * 100, np.nan)
    obs0, obs4 = w[:, 0].sum(), w[:, 1].sum()
    return {"ahorro_S/": obs0 - obs4, "ahorro_pct": (obs0 - obs4) / obs0 * 100 if obs0 else np.nan,
            "IC95_S/_inf": float(np.percentile(ah, 2.5)), "IC95_S/_sup": float(np.percentile(ah, 97.5)),
            "IC95_pct_inf": float(np.nanpercentile(pct, 2.5)), "IC95_pct_sup": float(np.nanpercentile(pct, 97.5)),
            "replicas": n_boot, "semilla": semilla}
