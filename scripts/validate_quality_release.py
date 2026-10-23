"""Verifica archivos publicables en su ubicación habitual y, opcionalmente, el índice.

No ejecuta análisis, copia archivos, altera Git ni necesita otro checkout.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from tesis_enasem.statistical_quality import ROOT,OUT
from tesis_enasem.release_audit import validate_public_content


def validate(index: bool=False) -> dict:
    policy=json.loads((ROOT/'diccionarios/cierre_publicacion.json').read_text())
    expected=set(policy['archivos_publicar'])
    assert len(expected)==len(policy['archivos_publicar'])
    records={}
    for name in sorted(expected):
        p=ROOT/name
        assert not p.is_symlink() and p.is_file() and p.resolve().is_relative_to(ROOT.resolve()),name
        assert p.parts and Path(name).parts[0] not in {'data','.git'},name
        assert p.suffix not in {'.dta','.parquet','.csv','.sav','.feather','.pkl','.rds','.pem','.key'},name
        records[name]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
        if p.suffix=='.ipynb':
            nb=json.loads(p.read_text())
            assert all(not c.get('outputs') and not c.get('attachments') for c in nb['cells']),name
    # Documento vigente verificado, no recompilado ni reconstruido por este control.
    import pymupdf
    pdf=ROOT/'manuscrito/build/main.pdf'
    assert len(pymupdf.open(pdf))==policy['version_actual']['tesis_paginas']
    editorial=json.loads((ROOT/'manuscrito/build/validacion_pdf.json').read_text())
    assert hashlib.sha256(pdf.read_bytes()).hexdigest()==editorial['pdf_sha256']
    for name,h in editorial['source_files_sha256'].items():
        assert name in expected and records[name]['sha256']==h,name
    content=validate_public_content(ROOT)
    tracked=set(filter(None,subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')))
    if index:
        assert tracked==expected, 'El árbol preparado no coincide con las rutas autorizadas'
        stage=subprocess.check_output(['git','ls-files','--stage','-z'],cwd=ROOT).decode().split('\0')
        objects={}
        for entry in filter(None,stage):
            meta,name=entry.split('\t',1);mode,oid,slot=meta.split()
            assert slot=='0' and mode in {'100644','100755'},name
            objects[name]=oid
        names=sorted(expected)
        hashes=subprocess.run(['git','hash-object','--stdin-paths'],cwd=ROOT,input='\n'.join(names)+'\n',text=True,stdout=subprocess.PIPE,check=True).stdout.splitlines()
        assert all(objects[name]==h for name,h in zip(names,hashes)), 'Índice distinto de los archivos revisados'
    result={'archivos_autorizados':len(expected),'indice_verificado':index,'contenido':content,'pdf_paginas':len(pymupdf.open(pdf)),
        'estado':'Versión revisada en el único repositorio; sin commit ni push'}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index',action='store_true',help='Exigir392 rutas exactas y contenido revisado en el índice Git.')
    args=parser.parse_args();validate(args.index)
