"""Registro reproducible de experimentos sin almacenar microdatos en Git."""
from datetime import datetime, timezone
from pathlib import Path
import json


def save_experiment(meta: dict, folder: str|Path) -> Path:
    """Guarda JSON de un experimento documentado (no guardar filas/personas)."""
    required={'id','objetivo','muestra','target','metodo'}
    missing=required-set(meta)
    if missing:
        raise ValueError(f'Faltan campos: {sorted(missing)}')
    name=str(meta['id'])
    if not name.startswith('EXP-') or not name[4:].isdigit():
        raise ValueError('ID esperado: EXP-001')
    path=Path(folder)/f'{name}.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    record=dict(meta,registrado_utc=datetime.now(timezone.utc).isoformat())
    path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'
',encoding='utf-8')
    return path
