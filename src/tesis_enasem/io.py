"""Carga de datos ENASEM desde disco local, sin modificar originales."""
from pathlib import Path
import pandas as pd


def load_stata(path: str | Path, preserve_missing: bool = True, columns: list[str] | None = None) -> pd.DataFrame:
    """Carga datos ENASEM conservando códigos .f/.p/.w como objetos de Stata.

    Para preparar modelos usar `numeric_enasem`; para auditoría conservar originales.
    """
    path=Path(path)
    if not path.is_file():
        raise FileNotFoundError(f'No se encuentra {path}. Guarda simpleMHAS.dta en data/raw/.')
    return pd.read_stata(path, convert_categoricals=False, convert_missing=preserve_missing, columns=columns)


def save_parquet(df: pd.DataFrame, path: str | Path) -> None:
    """Guarda tabla procesada; convertir primero objetos StataMissingValue."""
    path=Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
