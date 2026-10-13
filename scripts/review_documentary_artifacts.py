"""Verificación de documentos/agregados existentes, sin abrir filas ENASEM."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text, read_project_bytes
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import nbformat
import pandas as pd
import pymupdf

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(project_path('', 'src')))
from tesis_enasem.program_catalog import STATES
from tesis_enasem.manuscript import latex_number


def sha(path: Path) -> str:
    """Huella del artefacto, nunca identificador de una persona."""
    return hashlib.sha256(read_project_bytes(path)).hexdigest()


def review(baseline: Path | None = None) -> dict:
    """Reconcilia catálogo, macros, cuadros y evidencia ejecutada."""
    d=project_path('', 'docs/pensiones/nacional')
    index=json.loads(read_project_text(d/'indice_catalogo.json'))
    catalog=[r for s in index['fuentes'] for r in json.loads(read_project_text(project_path('', s['archivo_catalogo'])))]
    assert len(catalog)==46495==index['N_registros_documentales']
    assert len({r['registro_documental'] for r in catalog})==len(catalog)
    assert len(index['fuentes'])==169 and not index['problemas_parseo']
    assert {r['territorio'] for r in catalog if r['nivel_gobierno']=='estatal'}==set(STATES)
    for level,n in index['por_nivel'].items():
        assert sum(r['nivel_gobierno']==level for r in catalog)==n
    state=pd.DataFrame(json.loads(read_project_text(d/'cobertura_estatal.json')))
    mun=pd.DataFrame(json.loads(read_project_text(d/'cobertura_municipal.json')))
    assert len(state)==256 and len(mun)==160
    assert state.intervenciones_inventariadas.sum()==17511
    assert mun.intervenciones_documentadas.sum()==25593
    mapping=json.loads(read_project_text(d/'matriz_programas_enasem.json'))
    assert {r['registro_documental'] for r in mapping}=={r['registro_documental'] for r in catalog}
    manifest=json.loads(read_project_text(d/'fuentes_descargadas.json'))
    valid=[s for s in manifest if 'error' not in s]
    for s in valid:assert sha(project_path('', s['archivo']))==s['sha256']
    for s in index['fuentes']:
        books=list((project_path('', 'data/raw/documentacion_catalogo', s['fuente'])).glob('*.xls*'))
        assert len(books)==1 and sha(books[0])==s['sha256_libro']
    macros=read_project_text(project_path('', 'manuscrito/tablas/catalogo_cifras.tex'))
    for k,v in [('Total',46495),('Federal',3391),('Estatal',17511),('Municipal',25593)]:
        assert rf'\newcommand{{\cat{k}}}{{{latex_number(v)}}}' in macros
    tex=read_project_text(project_path('', 'manuscrito/tablas/catalogo_cobertura.tex'))
    for entity in STATES:
        values=[int(state.loc[state.entidad.eq(entity)&state.anio.eq(y),'intervenciones_inventariadas'].iloc[0]) for y in [2012,2018,2021]]
        values+=[int(mun.loc[mun.entidad.eq(entity)&mun.periodo_documental.eq('2020'),'intervenciones_documentadas'].iloc[0])]
        assert ' & '.join([entity]+[latex_number(v) for v in values]) in tex
    j=json.loads(read_project_text(project_path('', 'docs/eda/proteccion_economica/resultados.json')))
    assert j['N_personas_ronda_60']==56004 and j['N_personas_60_alguna_visita']==18754
    for c in j['cobertura']:
        year=c['ano']
        p=next(r for r in j['recepcion'] if r['ano']==year and r['variable']=='pension_propia_k')
        a=next(r for r in j['recepcion'] if r['ano']==year and r['variable']=='apoyo_propio')
        cats={r['categoria']:r['N'] for r in j['categorias'] if r['ano']==year}
        values=[c['N_60'],p['N_si'],a['N_si'],cats['Pensión K y apoyo'],cats['Apoyo y negativa propia K']]
        assert str(year)+' & '+' & '.join(latex_number(v) for v in values) in read_project_text(project_path('', 'manuscrito/tablas/proteccion_cobertura.tex'))
        for r in [p,a]:assert r['N_si']+r['N_no']+r['N_desconocido']==r['N_total']
    # Estos identificadores pertenecen a documentos, no a beneficiarios.
    nb=nbformat.read(project_path('', 'reports/notebooks/05e_contexto_documental_ejecutado.ipynb'),as_version=4)
    code=[c for c in nb.cells if c.cell_type=='code']
    assert all(c.execution_count is not None for c in code)
    assert not any(o.output_type=='error' for c in code for o in c.outputs)
    original=project_path('', 'data/raw/Andrea_Hernandez (1).pdf')
    original_sha=sha(original)
    assert original_sha=='f8d02542886fa039bd3b86cf6a7ac9915c4fcf2460fc90a6959fb884f1c5aea8'
    download=Path('/Users/andrea/Downloads/Andrea_Hernandez (1).pdf')
    assert not download.exists() or sha(download)==original_sha
    with pymupdf.open(original) as doc:assert len(doc)==65
    with pymupdf.open(project_path('', 'manuscrito/build/main.pdf')) as doc:
        pages=len(doc);text='\n'.join(p.get_text() for p in doc)
        assert 'Cuadro 2.2' in text and 'Cuadro 3.10' in text
        assert 'NVIDIA' not in text and 'Tesla' not in text
        assert not re.search(r'175\s*523',text)
    hashes={}
    evidence_path=project_path('', 'docs/recuperacion/validacion_tecnica.json')
    previous = json.loads(read_project_text(baseline)) if baseline else (
        json.loads(read_project_text(evidence_path)).get('huellas_previas_intactas', {})
        if evidence_path.exists() else {})
    for name,value in previous.items():
        actual=sha(project_path('', name));assert actual==value,name;hashes[name]=actual
    out={'fecha':'2026-10-12','unidad':'registros documentales; no beneficiarios',
         'catalogo':{'N':len(catalog),'por_nivel':index['por_nivel'],'libros':169,
                     'celdas_estatales':len(state),'celdas_municipales':len(mun),'fuentes_hash_verificado':len(valid)},
         'notebook':{'codigo_ejecutado':len(code),'errores':0},'cuadros':'32 entidades y seis rondas J02 reconciliadas; CP1 se verifica mediante su exportador',
         'pdf':{'paginas':pages,'sha256':sha(project_path('', 'manuscrito/build/main.pdf')),'original_paginas':65,'original_sha256':original_sha,'copias_original_iguales':download.exists()},
         'huellas_previas_intactas':hashes,
         'limite':'Validación técnica y cotejo de fuentes nuevas; no aprobación metodológica, editorial institucional o censo normativo completo.'}
    write_project_text(project_path('', 'docs/recuperacion/validacion_tecnica.json'), json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    return out


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path);args=p.parse_args()
    r=review(args.baseline)
    print(f"Revisión: {r['catalogo']['N']} registros documentales; {r['notebook']['codigo_ejecutado']} celdas sin error; PDF {r['pdf']['paginas']} páginas; {len(r['huellas_previas_intactas'])} huellas anteriores intactas.")
