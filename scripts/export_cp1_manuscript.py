"""Exporta exclusivamente los agregados existentes de CP1 al manuscrito LaTeX."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text, read_project_bytes

import argparse
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_path('', 'src')))
from tesis_enasem.manuscript import build_cp1_latex, export_cp1_figures

TABLE_NAMES = ['estructura', 'rondas', 'demografia', 'edad_grupos', 'entradas',
               'numero_rondas', 'transiciones', 'patrones', 'faltantes',
               'muestras', 'muestras_ronda', 'anomalias_resumen',
               'anomalias_posteriores_modalidad', 'anomalias_edad_compatibilidad']


def main() -> None:
    """Comprueba origen, exporta tablas/figuras y registra huellas reproducibles."""
    from tesis_enasem.release_guard import block_legacy_export
    block_legacy_export()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verificar tablas existentes sin escribir archivos.')
    args = parser.parse_args()
    source = project_path('', 'reports/tables')
    paths = {name: source / f'cp1_{name}.json' for name in TABLE_NAMES}
    metadata = json.loads(read_project_text(source / 'cp1_ejecucion.json'))
    raw = project_path('', 'data/raw/simpleMHAS.dta')
    if raw.exists() and hashlib.sha256(read_project_bytes(raw)).hexdigest() != metadata['sha256_datos']:
        raise ValueError('El original no coincide con la ejecución CP1: no exportar cifras.')
    tables = {name: pd.read_json(path, orient='table') for name, path in paths.items()}
    rendered = build_cp1_latex(tables)
    target = project_path('', 'manuscrito/tablas')
    hashes = {path.name: hashlib.sha256(read_project_bytes(path)).hexdigest() for path in paths.values()}
    if args.check:
        for name, text in rendered.items():
            if read_project_text(target / name) != text:
                raise ValueError(f'Tabla desactualizada o editada manualmente: {name}')
        manifest = json.loads(read_project_text(target / 'trazabilidad_cp1.json'))
        if hashes != manifest['sha256_agregados']:
            raise ValueError('Las fuentes agregadas cambiaron: regenerar exportaciones.')
        print(f'{len(rendered)} archivos LaTeX reconciliados con los agregados CP1.')
        return
    target.mkdir(parents=True, exist_ok=True)
    for name, text in rendered.items():
        write_project_text(target / name, text, encoding='utf-8')
    figures = export_cp1_figures(tables, project_path('', 'manuscrito/figuras/borradores'))
    manifest = {
        'checkpoint': 'CP1', 'fecha_ejecucion_fuente': metadata['fecha'],
        'poblacion': 'Toda la población registrada; sin filtros',
        'sha256_original': metadata['sha256_datos'], 'sha256_agregados': hashes,
        'tablas_generadas': sorted(rendered),
        'figuras_para_revision': [str(p.relative_to(ROOT)) for p in figures],
        'estado_editorial_figuras': 'borradores; aprobación de la autora pendiente',
        'regeneracion': 'python scripts/export_cp1_manuscript.py',
    }
    write_project_text(target / 'trazabilidad_cp1.json', json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(f'Exportados {len(rendered)} archivos LaTeX y {len(figures)} figuras agregadas para revisión.')


if __name__ == '__main__':
    from tesis_enasem.release_guard import block_legacy_export
    block_legacy_export()
    main()
