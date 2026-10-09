"""Transformaciones descriptivas, sin asumir comparabilidad monetaria entre olas."""
import numpy as np
import pandas as pd
from .missing import numeric_enasem


def asinh_transform(series: pd.Series) -> pd.Series:
    """Transformación asinh; conserva ceros y valores negativos de patrimonio."""
    return np.arcsinh(numeric_enasem(series))


def add_asinh(df: pd.DataFrame, column: str, suffix: str='_asinh') -> pd.DataFrame:
    out=df.copy()
    out[f'{column}{suffix}']=asinh_transform(out[column])
    return out
