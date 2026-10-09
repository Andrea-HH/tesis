"""Identificación, filtros y enlaces temporales del panel de ENASEM."""
import pandas as pd
from .missing import numeric_enasem


def make_person_id(df: pd.DataFrame, household_col: str = 'cunicah', person_col: str = 'np') -> pd.Series:
    """Identificador compuesto sin colisión entre hogar y número de persona."""
    a=numeric_enasem(df[household_col]); b=numeric_enasem(df[person_col])
    if a.isna().any() or b.isna().any():
        raise ValueError('cunicah/np contienen IDs faltantes; no se pueden enlazar.')
    if ((a % 1 != 0) | (b % 1 != 0)).any():
        raise ValueError('Identificadores no enteros.')
    return a.astype('int64').astype(str).str.cat(b.astype('int64').astype(str), sep='_')


def add_year(df: pd.DataFrame, round_to_year: dict[int, int], round_col: str = 'ronda') -> pd.DataFrame:
    """Agrega año NOMINAL de ronda, no año efectivo de entrevista."""
    out=df.copy()
    out['ano']=numeric_enasem(out[round_col]).map(round_to_year).astype('Int64')
    return out


def filter_population(df: pd.DataFrame, min_age: int = 60, interview_types: tuple[int,...] = (1,2)) -> pd.DataFrame:
    """Filtro exploratorio: edad >= umbral EN ESA RONDA, entrevista directa.

    Advertencia: usar edad >=60 en todas las rondas restringe muy fuertemente
    cohortes del panel balanceado. Definir población objetivo antes de filtrar.
    """
    mask=numeric_enasem(df['edad']).ge(min_age) & numeric_enasem(df['tipent']).isin(interview_types)
    return df.loc[mask].copy()


def balanced_panel_ids(df: pd.DataFrame, id_col: str = 'id', round_col: str = 'ronda', n_rounds: int = 6) -> pd.Index:
    """IDs con n_rounds observadas en este dataframe: NO es muestra principal por defecto."""
    return df.groupby(id_col)[round_col].nunique().loc[lambda s: s.eq(n_rounds)].index


def followup_pairs(df: pd.DataFrame, outcome_col: str, id_col: str = 'id', round_col: str = 'ronda',
                   max_gap: int = 1) -> pd.DataFrame:
    """Pares persona-ronda t -> siguiente ronda realmente observada.

    Si max_gap=1 requiere olas consecutivas; diferencia en AÑOS puede variar
    (2003->2012 = 9 años). Una fila sin outcome válido futuro queda sin etiqueta.
    """
    if df.duplicated([id_col, round_col]).any():
        raise ValueError('Hay pares (id, ronda) duplicados.')
    out=df.sort_values([id_col,round_col]).copy()
    groups=out.groupby(id_col, sort=False)
    out['ronda_futura']=groups[round_col].shift(-1)
    out['outcome_futuro']=groups[outcome_col].shift(-1)
    out['salto_rondas']=out['ronda_futura']-out[round_col]
    out.loc[out['salto_rondas']>max_gap, ['ronda_futura','outcome_futuro']]=pd.NA
    return out
