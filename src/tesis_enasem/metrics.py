"""Métricas predictivas robustas para evaluación fuera de muestra."""
import numpy as np
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss


def classification_metrics(y_true, y_prob, sample_weight=None):
    """AUC, Average Precision y Brier; AUC=NaN si solo hay una clase."""
    y=np.asarray(y_true, dtype=float); p=np.asarray(y_prob,dtype=float)
    wt=np.ones_like(y) if sample_weight is None else np.asarray(sample_weight,dtype=float)
    valid=np.isfinite(y)&np.isfinite(p)&np.isfinite(wt)&(wt>0)
    y,p,wt=y[valid],p[valid],wt[valid]
    if len(y)==0:
        raise ValueError('No hay pares predicción-observación válidos.')
    if not np.isin(y,[0,1]).all():
        raise ValueError('y_true debe ser binaria (0/1).')
    if ((p<0)|(p>1)).any():
        raise ValueError('Las probabilidades deben estar entre 0 y 1.')
    two_classes=len(np.unique(y))==2
    return {'n':int(len(y)), 'prevalencia':float(np.average(y,weights=wt)),
            'roc_auc':float(roc_auc_score(y,p,sample_weight=wt)) if two_classes else float('nan'),
            'pr_auc':float(average_precision_score(y,p,sample_weight=wt)) if two_classes else float('nan'),
            'brier':float(brier_score_loss(y,p,sample_weight=wt))}
