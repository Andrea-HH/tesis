"""Validaciones básicas para detectar errores de panel antes de modelar."""
import pandas as pd
from .missing import numeric_enasem


def panel_quality(df: pd.DataFrame, id_col='id', round_col='ronda') -> dict:
    return {'filas':len(df), 'personas':int(df[id_col].nunique()),
            'pares_duplicados':int(df.duplicated([id_col,round_col]).sum()),
            'rondas':sorted(numeric_enasem(df[round_col]).dropna().unique().astype(int).tolist())}
