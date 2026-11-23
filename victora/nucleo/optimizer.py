"""Producción óptima por producto (modelo del vendedor de periódicos / newsvendor)."""
import numpy as np
from scipy import stats


def razon_critica(precio, margen, recuperable=0.0):
    """margen = utilidad sobre el precio (p.ej. 0.275). Costo c = p(1-margen).
    cu (costo de quedarse corto) = p - c ; co (costo de sobrar) = c*(1-recuperable)."""
    c = precio * (1 - margen)
    cu = precio - c
    co = c * (1 - recuperable)
    if cu + co == 0:
        return 1.0, c, cu, co
    return cu / (cu + co), c, cu, co


def cantidad_optima(pron, rmse, cr, residuos=None):
    """Cantidad = cuantil CR de la demanda. Usa normal con sigma=max(RMSE, sqrt(pron))
    (dispersión mínima tipo Poisson cuando hay pocos datos)."""
    if pron <= 0:
        return 0
    sigma = max(rmse if rmse == rmse else 0, np.sqrt(max(pron, 0.01)))
    cr = min(max(cr, 0.01), 0.99)
    q = stats.norm.ppf(cr, loc=pron, scale=sigma)
    return int(max(0, np.round(q)))


def utilidad(Q, D, precio, c, recuperable=0.0):
    vendido = np.minimum(Q, D)
    sobra = np.maximum(Q - D, 0)
    return precio * vendido - c * Q + c * recuperable * sobra
