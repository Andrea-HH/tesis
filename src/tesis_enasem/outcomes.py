"""Definición de vulnerabilidad basada en patrimonio, aún provisional."""
import pandas as pd
from .missing import numeric_enasem
from .weights import weighted_quantile


def wealth_q1_cutoff(df: pd.DataFrame, wealth_col: str = 'imp_neto', weight_col: str | None = None) -> float:
    weights = None if weight_col is None else numeric_enasem(df[weight_col])
    return float(weighted_quantile(numeric_enasem(df[wealth_col]), [0.25], weights)[0])


def classify_relative_vulnerability(df: pd.DataFrame, wealth_col: str = 'imp_neto', weight_col: str | None = None) -> pd.Series:
    """Vulnerable=1 si riqueza <= Q1 del *df provisto*, conservando faltantes.

    Calcular los cortes explícitamente por ronda y sobre población de referencia,
    no sobre el test ni el subconjunto vulnerable sin justificación.
    """
    wealth=numeric_enasem(df[wealth_col])
    cutoff=wealth_q1_cutoff(df,wealth_col,weight_col)
    label=wealth.le(cutoff).astype('Int64')
    return label.mask(wealth.isna(), pd.NA)


def label_by_wave(df: pd.DataFrame, year_col: str='ano', wealth_col: str='imp_neto',
                  weight_col: str|None=None, output_col: str='vulnerable_q1') -> pd.DataFrame:
    """Cuantiles por ola sin mezclar monedas de distintos años."""
    out=df.copy()
    out[output_col]=pd.Series(pd.NA, index=out.index, dtype='Int64')
    for _, sub in out.groupby(year_col, dropna=True):
        out.loc[sub.index,output_col]=classify_relative_vulnerability(sub,wealth_col,weight_col)
    return out
