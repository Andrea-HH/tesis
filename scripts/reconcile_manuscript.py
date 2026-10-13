"""Adaptación editorial idempotente: modifica encabezados, nunca celdas numéricas."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text, read_project_bytes

import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Compara contenido numérico de cada cuadro antes/después del formato."""
    edits = []
    for path in sorted((project_path('', 'manuscrito/tablas')).glob('*.tex')):
        original = read_project_text(path)
        lines = original.splitlines(keepends=True)
        header = False
        for i, line in enumerate(lines):
            if r'\toprule' in line:
                header = True
                if ' & ' not in line:
                    continue
                prefix, line = line.split(r'\toprule',1)
                prefix += r'\toprule '
            else:
                prefix = ''
            if r'\midrule' in line:
                header = False
            if header and ' & ' in line and r'\textbf{' not in line:
                body, suffix = line.rsplit(r'\\', 1)
                lines[i] = prefix + ' & '.join(r'\textbf{' + cell.strip() + '}' for cell in body.split(' & ')) + r' \\' + suffix
        changed = ''.join(lines)
        assert re.findall(r'\d+(?:[,\.]\d+)?', original) == re.findall(r'\d+(?:[,\.]\d+)?', changed)
        if changed != original:
            write_project_text(path, changed)
            edits.append(str(path.relative_to(ROOT)))
    evidence = {'objetivo':'estilo de cuadros original; ninguna cifra modificada',
                'modificados':edits,'adaptacion':'encabezados en negritas; no celdas de datos',
                'huellas_finales':{str(p.relative_to(ROOT)):hashlib.sha256(read_project_bytes(p)).hexdigest()
                                  for p in (project_path('', 'manuscrito/tablas')).glob('*.tex')}}
    write_project_text(project_path('', 'docs/recuperacion/estilo_verificacion.json'), json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    print(f'{len(edits)} cuadros adaptados; todas las cifras conservadas.')


if __name__ == '__main__':
    main()
