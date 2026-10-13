from tesis_enasem.project_paths import project_path, read_project_text, write_project_text
"""Valida estructura de los notebooks sin ejecutarlos ni requerir datos."""
from pathlib import Path
import json
import nbformat

root=Path(__file__).resolve().parents[1]
principal=[root/'notebooks'/name for name in ('01_INTEGRACION.ipynb','02_EDA_COMPLETO.ipynb')]
assert all(path.is_file() for path in principal), 'Faltan notebooks principales'
files=sorted((root/'notebooks').glob('*.ipynb'))
files+=sorted((root/'investigacion/notas/notebooks_historicos').glob('*.ipynb'))
for path in files:
    # Validar la fuente física, no su alias hacia una ejecución con outputs.
    item=json.loads(path.read_text(encoding='utf-8'))
    nbformat.validate(item)
    assert item.get('nbformat')==4, path
    assert item.get('cells') and item['cells'][0]['cell_type']=='markdown', path
    for cell in item['cells']:
        if cell['cell_type']=='code':
            assert cell['execution_count'] is None and cell.get('outputs')==[], path
print(f'{len(files)} notebooks válidos (sin outputs versionados).')
