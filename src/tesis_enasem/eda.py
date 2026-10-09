"""EDA univariado de ENASEM con observaciones por ronda."""
import pandas as pd
from .missing import numeric_enasem


def summarize_by_wave(df: pd.DataFrame, variable: str, wave_col: str='ano') -> pd.DataFrame:
    """Media/mediana/desviación por ronda; sin sumar personas entre rondas."""
    d=df[[wave_col,variable]].copy()
    d[variable]=numeric_enasem(d[variable])
    return d.groupby(wave_col)[variable].agg(n='count',mean='mean',median='median',std='std',min='min',max='max').reset_index()


def availability_by_wave(df: pd.DataFrame, cols: list[str], wave_col: str='ronda') -> pd.DataFrame:
    """Número de valores observados, no faltantes Stata, por ola y variable."""
    parts=[]
    for variable in cols:
        d=df[[wave_col,variable]].copy()
        d[variable]=numeric_enasem(d[variable])
        tab=d.groupby(wave_col)[variable].agg(['size','count']).reset_index()
        tab['variable']=variable
        tab['n_disponible']=tab['count']
        parts.append(tab[[wave_col,'variable','n_disponible','size']])
    return pd.concat(parts,ignore_index=True)
