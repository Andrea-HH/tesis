"""Bloquea exportaciones históricas no revisadas en el cierre público."""
from .project_paths import PROJECT_ROOT

def block_legacy_export() -> None:
    if (PROJECT_ROOT/'diccionarios/politica_calidad_divulgacion.json').exists():
        raise SystemExit('Exportador histórico bloqueado: usar scripts/export_quality_public.py; los cálculos privados y originales se conservan. No se permite sobrescribir publicaciones revisadas con salidas antiguas.')
