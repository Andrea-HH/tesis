"""Funciones para resumen exploratorio con ponderadores individuales."""
import numpy as np


def weighted_quantile(values, quantiles, sample_weight=None):
    """Cuantil ponderado por interpolación; no es idéntico a cuantiles survey oficiales."""
    q=np.asarray(quantiles,dtype=float)
    if np.any((q < 0)|(q > 1)):
        raise ValueError('Los cuantiles deben estar entre 0 y 1.')
    v=np.asarray(values,dtype=float)
    if sample_weight is None:
        if not np.isfinite(v).any():
            raise ValueError('No hay valores finitos.')
        return np.nanquantile(v,q)
    wt=np.asarray(sample_weight,dtype=float)
    if wt.shape!=v.shape:
        raise ValueError('values y sample_weight requieren la misma longitud.')
    mask=np.isfinite(v)&np.isfinite(wt)&(wt>0)
    if not mask.any():
        raise ValueError('No hay pares valor-peso válidos.')
    v=v[mask]; wt=wt[mask]
    order=np.argsort(v,kind='mergesort'); v=v[order]; wt=wt[order]
    p=(np.cumsum(wt)-0.5*wt)/wt.sum()
    return np.interp(q,p,v)
