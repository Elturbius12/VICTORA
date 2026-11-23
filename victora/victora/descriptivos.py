"""Estadística descriptiva y clasificación de la demanda."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from .utils import DIAS_ES


def descriptivos(m: pd.DataFrame, productos: pd.DataFrame) -> pd.DataFrame:
    nombres = productos.set_index("producto_id")["nombre"]
    filas = []
    for pid in m.columns:
        y = m[pid].values
        media = y.mean()
        filas.append({
            "producto_id": pid, "nombre": nombres.get(pid, pid), "n": len(y),
            "media": media, "mediana": np.median(y), "DE": y.std(ddof=1),
            "min": y.min(), "max": y.max(), "CV": y.std(ddof=1) / media if media > 0 else np.nan,
            "asimetria": stats.skew(y, bias=False) if y.std() > 0 else 0.0,
            "curtosis": stats.kurtosis(y, bias=False) if y.std() > 0 else 0.0,
            "total": y.sum(),
        })
    return pd.DataFrame(filas)


def adi_cv2(y: np.ndarray) -> tuple[float, float]:
    """ADI = periodos / periodos con demanda; CV² de los tamaños no nulos."""
    nz = y[y > 0]
    if len(nz) == 0:
        return np.inf, np.nan
    adi = len(y) / len(nz)
    cv2 = (nz.std(ddof=0) / nz.mean()) ** 2 if len(nz) > 1 else 0.0
    return adi, cv2


def tipo_demanda(adi: float, cv2: float) -> str:
    """Clasificación de Syntetos–Boylan (2005)."""
    if not np.isfinite(adi):
        return "Sin demanda"
    if adi <= 1.32:
        return "Suave" if cv2 < 0.49 else "Errática"
    return "Intermitente" if cv2 < 0.49 else "Irregular (lumpy)"


def clasificacion(m: pd.DataFrame, productos: pd.DataFrame) -> pd.DataFrame:
    precio = productos.set_index("producto_id")["precio_venta"]
    filas = []
    for pid in m.columns:
        y = m[pid].values
        adi, cv2 = adi_cv2(y)
        media = y.mean()
        cv = y.std(ddof=1) / media if media > 0 else np.inf
        filas.append({"producto_id": pid, "ADI": adi, "CV2": cv2, "tipo_demanda": tipo_demanda(adi, cv2),
                      "ingreso": y.sum() * precio[pid], "CV": cv})
    df = pd.DataFrame(filas).sort_values("ingreso", ascending=False)
    acum = df["ingreso"].cumsum() / max(df["ingreso"].sum(), 1e-9)
    df["pct_ingreso_acum"] = acum * 100
    df["ABC"] = np.where(acum.shift(fill_value=0) < 0.80, "A", np.where(acum.shift(fill_value=0) < 0.95, "B", "C"))
    df["XYZ"] = np.where(df["CV"] <= 0.5, "X", np.where(df["CV"] <= 1.0, "Y", "Z"))
    df["ABC_XYZ"] = df["ABC"] + df["XYZ"]
    df["intermitente"] = (df["ADI"] > 1.32) & (df["CV2"] >= 0.49)
    return df.reset_index(drop=True)


def dia_semana(m: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Perfil medio por día y Kruskal-Wallis por producto."""
    dow = m.index.dayofweek
    perfil = m.groupby(dow).mean()
    perfil.index = [DIAS_ES[i] for i in perfil.index]
    filas = []
    for pid in m.columns:
        grupos = [m[pid].values[dow == d] for d in sorted(set(dow))]
        grupos = [g for g in grupos if len(g) > 0]
        n_min = min(len(g) for g in grupos)
        try:
            h, pval = stats.kruskal(*grupos) if len(grupos) > 1 else (np.nan, np.nan)
        except ValueError:  # todos los valores iguales
            h, pval = 0.0, 1.0
        n = sum(len(g) for g in grupos)
        k = len(grupos)
        eps2 = (h - k + 1) / (n - k) if n > k and h == h else np.nan  # épsilon² (Tomczak)
        filas.append({"producto_id": pid, "H": h, "gl": k - 1, "p_valor": pval, "epsilon2": eps2,
                      "obs_min_por_dia": n_min,
                      "aviso_potencia": "Potencia baja (≤3 obs. por día)" if n_min <= 3 else ""})
    return perfil, pd.DataFrame(filas)


def correlaciones(m: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Spearman entre productos y de cada producto con el día de la semana."""
    var = m.loc[:, m.std() > 0]
    corr = var.corr(method="spearman")
    dow = m.index.dayofweek
    filas = []
    for pid in m.columns:
        if m[pid].std() > 0:
            rho, pval = stats.spearmanr(dow, m[pid])
        else:
            rho, pval = np.nan, np.nan
        filas.append({"producto_id": pid, "rho_dia_semana": rho, "p_valor": pval})
    return corr, pd.DataFrame(filas)
