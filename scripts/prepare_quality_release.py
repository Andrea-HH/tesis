"""Prepara el índice del único repositorio con su manifiesto, sin commit ni push.

No copia archivos a otra raíz ni crea repositorios. --stage retira del índice
las rutas excluidas conservando cada archivo en disco. Sin --stage solo verifica.
Las rutas nuevas requieren revisión previa y actualización del manifiesto.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from tesis_enasem.project_paths import PROJECT_ROOT as ROOT,INTERIM_DIR

OUT=INTERIM_DIR/'auditoria_calidad_divulgacion'


def git(*args: str,input: bytes|None=None) -> bytes:
    return subprocess.run(['git',*args],cwd=ROOT,input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout


def authorized_paths() -> set[str]:
    policy=json.loads((ROOT/'diccionarios/cierre_publicacion.json').read_text())
    paths=policy['archivos_publicar']
    if len(paths)!=len(set(paths)):
        raise ValueError('Rutas autorizadas repetidas')
    for name in paths:
        p=Path(name)
        if p.is_absolute() or '..' in p.parts or p.parts[0] in {'data','.git'}:
            raise ValueError('Ruta no publicable: '+name)
        if not (ROOT/p).is_file() or (ROOT/p).is_symlink():
            raise ValueError('Archivo ausente o enlace simbólico: '+name)
    return set(paths)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(stage: bool=False) -> dict:
    paths=authorized_paths()
    check=subprocess.run(['git','check-ignore','--no-index','--stdin','-z'],cwd=ROOT,
        input=b'\0'.join(x.encode() for x in sorted(paths))+b'\0',stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if check.returncode not in (0,1) or check.stdout:
        raise ValueError('Una ruta autorizada sigue ignorada: '+check.stdout.decode(errors='replace'))
    tracked=set(filter(None,git('ls-files','-z').decode().split('\0')))
    excluded=tracked-paths
    preserved={name:sha(ROOT/name) for name in excluded}
    head=git('rev-parse','HEAD').decode().strip();stash=git('rev-parse','stash@{0}').decode().strip()
    if stage:
        # Fallar antes de tocar el índice si el contenido no supera la revisión.
        from validate_quality_release import validate
        validate(index=False)
        if excluded:
            git('rm','--cached','-f','--pathspec-from-file=-','--pathspec-file-nul',
                input=b'\0'.join(x.encode() for x in sorted(excluded))+b'\0')
        git('add','--pathspec-from-file=-','--pathspec-file-nul',
            input=b'\0'.join(x.encode() for x in sorted(paths))+b'\0')
        assert set(filter(None,git('ls-files','-z').decode().split('\0')))==paths
    for name,h in preserved.items():
        assert (ROOT/name).is_file() and sha(ROOT/name)==h,'Archivo local alterado: '+name
    assert git('rev-parse','HEAD').decode().strip()==head
    assert git('rev-parse','stash@{0}').decode().strip()==stash
    records={name:{'sha256':sha(ROOT/name),'bytes':(ROOT/name).stat().st_size} for name in sorted(paths)}
    result={'archivos':records,'total':len(records),'raiz':'.','git_head':head,'stash0':stash,
        'origen':'Archivos físicos revisados del mismo repositorio, sin directorio público alternativo',
        'retirados_del_indice_en_esta_ejecucion':sorted(excluded) if stage else [],
        'archivos_locales_conservados':len(preserved),'commit_push':False}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'propuesta_publica.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(f'{len(paths)} rutas autorizadas; {len(excluded)} exclusiones del índice; archivos locales conservados. Sin commit ni push.')
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',action='store_true',help='Preparar exactamente las rutas autorizadas y retirar las demás solo del índice.')
    args=parser.parse_args();prepare(args.stage)
