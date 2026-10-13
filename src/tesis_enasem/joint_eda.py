"""Agregados conjuntos por ronda; sin causalidad, pesos ni selección predictiva."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


def paired_spearman(frame: pd.DataFrame, x: str, y: str, year: int) -> dict:
    """Pares válidos dentro de onda; ND para variables constantes o menos de tres pares."""
    pair = frame[[x,y]].dropna()
    estimable = len(pair) >= 3 and pair[x].nunique() > 1 and pair[y].nunique() > 1
    rho = float(spearmanr(pair[x],pair[y]).statistic) if estimable else None
    return {"ano": year, "variable_x": x, "variable_y": y, "N_total_ronda": len(frame),
            "N_pares_validos": len(pair), "N_sin_par": len(frame)-len(pair), "rho_spearman": rho,
            "ponderado": False, "interpretacion": "Asociación contemporánea entre rangos; no trayectoria ni causalidad"}


def stratified_descriptions(frame: pd.DataFrame, groups: list[str], variables: list[str]) -> list[dict]:
    """Describe estratos agregados con N total/validez por medida; no suma patrimonio compartido."""
    result = []
    for levels, part in frame.groupby(groups,dropna=False,observed=True):
        levels = levels if isinstance(levels,tuple) else (levels,)
        group = dict(zip(groups,("desconocido" if pd.isna(v) else str(v) for v in levels)))
        for name in variables:
            values = part[name].dropna()
            result.append({**group, "variable": name, "N_estrato": len(part), "N_valido": len(values),
                           "N_no_valido": len(part)-len(values),
                           "mediana": float(values.median()) if len(values) else None,
                           "p25": float(values.quantile(.25)) if len(values) else None,
                           "p75": float(values.quantile(.75)) if len(values) else None})
    return result
