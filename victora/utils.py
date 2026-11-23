"""Funciones auxiliares compartidas."""
from __future__ import annotations

import hashlib
import io

import numpy as np
import pandas as pd

DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# Conversión de unidades a la unidad base (g, ml, unidad)
CONVERSION = {"g": ("g", 1.0), "kg": ("g", 1000.0), "ml": ("ml", 1.0),
              "L": ("ml", 1000.0), "unidad": ("unidad", 1.0)}
UNIDADES = list(CONVERSION)


def si_no(valor) -> bool:
    """Convierte SI/NO (o variantes) en booleano."""
    if isinstance(valor, (bool, np.bool_)):
        return bool(valor)
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return False
    return str(valor).strip().upper() in {"SI", "SÍ", "S", "TRUE", "1", "YES", "Y"}


def a_base(cantidad: float, unidad: str) -> tuple[float, str]:
    """Convierte una cantidad a su unidad base."""
    base, f = CONVERSION.get(unidad, (unidad, 1.0))
    return cantidad * f, base


def presentar(cantidad: float, base: str) -> tuple[float, str]:
    """Pasa de unidad base a la unidad más legible (kg, L)."""
    if base == "g" and cantidad >= 1000:
        return cantidad / 1000, "kg"
    if base == "ml" and cantidad >= 1000:
        return cantidad / 1000, "L"
    return cantidad, base


def hash_df(*dfs: pd.DataFrame) -> str:
    """Hash SHA-256 de los datos (reproducibilidad)."""
    h = hashlib.sha256()
    for df in dfs:
        if df is not None:
            h.update(pd.util.hash_pandas_object(df, index=False).values.tobytes())
    return h.hexdigest()[:16]


def fmt_s(x: float) -> str:
    """Formato en soles."""
    return f"S/ {fmt_num(x)}"


def fmt_num(x: float, d: int = 2) -> str:
    """Número con coma decimal (estilo español)."""
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_p(p: float) -> str:
    if p is None or np.isnan(p):
        return "no calculable"
    return "p < 0,001" if p < 0.001 else f"p = {fmt_num(p, 3)}"


def fig_a_png(fig, dpi: int = 300) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    return buf.getvalue()
