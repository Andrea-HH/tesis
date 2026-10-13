from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = PROJECT_ROOT / "data/interim"
FIGURES_DIR = PROJECT_ROOT / "resultados/figuras"
TABLES_DIR = PROJECT_ROOT / "data/interim/cp1"

ROUND_TO_YEAR = {1: 2001, 2: 2003, 3: 2012, 4: 2015, 5: 2018, 6: 2021}
DEFAULT_RANDOM_STATE = 42
