"""Manejo explícito de valores perdidos especiales de Stata (.f, .p, .w...)."""
import pandas as pd
from pandas.io.stata import StataMissingValue


def stata_missing_code(value):
    """Devuelve el código .a-.z de Stata o None para los demás valores."""
    return str(value) if isinstance(value, StataMissingValue) else None


def numeric_enasem(series: pd.Series) -> pd.Series:
    """Convierte valores numéricos a float; códigos especiales se hacen NaN.

    Contar antes los códigos especiales si importan para el análisis de atrición.
    """
    return pd.to_numeric(series.map(lambda x: None if isinstance(x, StataMissingValue) else x), errors='coerce')


def missing_audit(df: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    """Reporte de NaN y de códigos especiales por variable, sin mezclarlos."""
    cols = list(df.columns) if columns is None else columns
    rows=[]
    for col in cols:
        s=df[col]
        n=s.map(stata_missing_code).value_counts(dropna=True)
        for code, count in n.items():
            rows.append({'variable':col,'tipo':code,'n':int(count)})
        if s.isna().any():
            rows.append({'variable':col,'tipo':'NaN','n':int(s.isna().sum())})
    return pd.DataFrame(rows, columns=['variable','tipo','n'])
