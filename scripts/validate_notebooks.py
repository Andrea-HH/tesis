"""Valida estructura de los notebooks sin ejecutarlos ni requerir datos."""
from pathlib import Path
import json

root=Path(__file__).resolve().parents[1]
files=sorted((root/'notebooks').glob('*.ipynb'))
assert len(files)>=13, 'Se esperaban los 13 notebooks del roadmap'
for path in files:
    item=json.loads(path.read_text(encoding='utf-8'))
    assert item.get('nbformat')==4, path
    assert item.get('cells') and item['cells'][0]['cell_type']=='markdown', path
    for cell in item['cells']:
        if cell['cell_type']=='code':
            assert cell['execution_count'] is None and cell.get('outputs')==[], path
print(f'{len(files)} notebooks válidos (sin outputs versionados).')
