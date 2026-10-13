"""Catálogo nacional reproducible desde inventarios oficiales descargados.

No accede a microdatos ENASEM, no asigna beneficiarios ni recalcula el EDA.
Con --download repone las fuentes del manifiesto con verificación SHA-256.
"""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text, read_project_bytes

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(project_path('', 'src')))
from tesis_enasem.program_catalog import STATES, documentary_coverage, parse_inventory, parse_municipal, state_name
from tesis_enasem.manuscript import render_latex_table

DOCS = project_path('', 'docs/pensiones/nacional')
CACHE = project_path('', 'data/raw/documentacion_catalogo')


def save(path: Path, value: object) -> None:
    """JSON legible, sin NaN ni objetos numpy."""
    path.parent.mkdir(exist_ok=True,parents=True)
    write_project_text(path, json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def main() -> None:
    """Conserva cada corte independiente y deja pendientes normativos explícitos."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    args = parser.parse_args()
    sources=json.loads(read_project_text(project_path('docs/pensiones/nacional', 'fuentes_descargadas.json')))
    sources=[s for s in sources if 'error' not in s]
    records=[]; extracted=[]; failure=[]
    # Los resultados detallados públicos describen programas, nunca personas.
    target=project_path('docs/pensiones/nacional', 'registros');target.mkdir(exist_ok=True)
    for source in sources:
        p=project_path('', source['archivo'])
        if args.download and not p.exists():
            import requests
            response=requests.get(source['url'],timeout=60);response.raise_for_status()
            p.parent.mkdir(exist_ok=True,parents=True);p.write_bytes(response.content)
        if hashlib.sha256(read_project_bytes(p)).hexdigest()!=source['sha256']:
            raise ValueError(f"Huellas diferentes: {source['id']}")
        if p.suffix not in {'.zip', '.rar'}:
            continue
        directory=project_path('data/raw/documentacion_catalogo', source['id']);directory.mkdir(exist_ok=True)
        if not any(directory.iterdir()):
            if p.suffix=='.rar':
                subprocess.run(['tar','-xf',str(p),'-C',str(directory)],check=True)
            else:
                with zipfile.ZipFile(p) as archive:
                    for name in archive.namelist():
                        if not name.endswith('/'):(directory/Path(name).name).write_bytes(archive.read(name))
        files=[f for f in directory.iterdir() if f.suffix.lower() in {'.xlsx','.xls'}]
        if len(files)!=1:
            failure.append({'fuente':source['id'],'error':'No hay un libro único; requiere inspección','archivos':[f.name for f in files]});continue
        file=files[0]; workbook=pd.ExcelFile(file)
        try:
            if source['id'].startswith('estatal_'):
                sheet=workbook.sheet_names[0];level='estatal';year=int(source['id'].split('_')[-1])
                rows=parse_inventory(pd.read_excel(file,sheet_name=sheet,header=None),source['id'],year,sheet,source['url'],level)
            elif source['id']=='federal_historico':
                sheet='3. IF_Histórico';level='federal'
                rows=parse_inventory(pd.read_excel(file,sheet_name=sheet,header=None),source['id'],None,sheet,source['url'],level)
            else:
                sheet=next(s for s in workbook.sheet_names if s.strip().rstrip('.').lower()=='intervenciones');level='municipal'
                slug=source['pagina_descarga'].split('/')[-1].replace('.aspx','').replace('_',' ')
                territory=state_name(slug)
                if territory is None:territory='San Luis Potosí' if slug=='San Luis Potos' else None
                if territory is None:raise ValueError('Entidad documental desconocida')
                rows=parse_municipal(pd.read_excel(file,sheet_name=sheet,header=None),source,sheet,territory)
            # Campos extensos originales quedan en copias oficiales locales. El catálogo
            # público mantiene referencias de hoja/fila y campos sustantivos, sin presupuesto
            # como monto individual ni transcripción completa de objetivos.
            public=[{k:v for k,v in r.items() if k!='campos_originales'} for r in rows]
            save(target/(source['id']+'.json'),public)
            records.extend(public)
            extracted.append({'fuente':source['id'],'nivel':level,'hoja':sheet,
                              'filas_extraidas':len(public),'archivo_catalogo':str((target/(source['id']+'.json')).relative_to(ROOT)),
                              'sha256_libro':hashlib.sha256(read_project_bytes(file)).hexdigest(),
                              'otras_hojas':workbook.sheet_names,'regla':'solo agregado nacional o INTERVENCIONES; no duplicar hojas territoriales/COVID'})
        except (ValueError,StopIteration,TypeError) as e:
            failure.append({'fuente':source['id'],'error':str(e)})
        print(source['id'],len(rows) if not failure or failure[-1]['fuente']!=source['id'] else 'PENDIENTE',flush=True)
    cov=documentary_coverage(records);save(project_path('docs/pensiones/nacional', 'cobertura_estatal.json'),cov)
    municipal=[]
    for state in STATES:
        for period in ['2012-2013','2014-2015','2015-2016','2017','2020']:
            selected=[r for r in records if r['nivel_gobierno']=='municipal' and r['territorio']==state and r['periodo_documental']==period]
            municipal.append({'entidad':state,'periodo_documental':period,'intervenciones_documentadas':len(selected),
                             'municipios_con_intervenciones':len({r['municipio'] for r in selected}),
                             'marcadas_vejez':sum('vejez' in r['marcadores_revision'] for r in selected),
                             'estado':'periodo_documental; no_operacion_anual_validada'})
    save(project_path('docs/pensiones/nacional', 'cobertura_municipal.json'),municipal)
    save(project_path('docs/pensiones/nacional', 'indice_catalogo.json'),{'fuentes':extracted,'problemas_parseo':failure,
                                  'N_registros_documentales':len(records),
                                  'por_nivel':{l:sum(r['nivel_gobierno']==l for r in records) for l in ['federal','estatal','municipal']},
                                  'unidad':'intervencion-ejercicio o intervencion-periodo-municipio; NO programas únicos históricos ni receptores',
                                  'alcance':'todos los registros de las hojas principales disponibles; no censo exhaustivo de prestaciones',
                                  'marcadores':'cribado lexical reproducible para revisión; no validación de elegibilidad ni clasificación contributiva'})
    # Tabla 32 entidades: conteos de documentos, no tasas ENASEM.
    summary=[]
    for state in STATES:
        summary.append({'Entidad':state,**{str(y):next(r['intervenciones_inventariadas'] for r in cov if r['entidad']==state and r['anio']==y) for y in [2012,2018,2021]},
                        'Municipal 2020':next(r['intervenciones_documentadas'] for r in municipal if r['entidad']==state and r['periodo_documental']=='2020')})
    write_project_text(project_path('', 'manuscrito/tablas/catalogo_cobertura.tex'), render_latex_table(pd.DataFrame(summary),
        'Cobertura documental por entidad: intervenciones en inventarios oficiales seleccionados',
        'tab:catalogo-cobertura','Fuente: extracción reproducible de inventarios CONEVAL. Conteos de intervenciones, no beneficiarios ni programas históricos únicos. Estatal: ejercicio fiscal; municipal: corte documental 2020. No mide cobertura poblacional. Las reglas, importes y continuidad se validan por separado. Para 2001/2003 no se dispone de un inventario estatal equivalente; 2015 no se sustituye por 2014/2016.',
        column_format='lrrrr',long=True))
    lines=['# Cobertura documental nacional por entidad y periodo','',
           'Todos los conteos corresponden a registros documentales, no personas ni prestaciones únicas. Las entidades sin registro no se interpretan como ausencia de programas. El catálogo incluye otras intervenciones sociales; el cribado de vejez/discapacidad/alimentación/asistencia es una ayuda de revisión, no prueba de elegibilidad.','',
           '## Inventarios estatales','',pd.DataFrame(cov).pivot(index='entidad',columns='anio',values='intervenciones_inventariadas').reindex(STATES).to_markdown(),'',
           '## Inventarios municipales','',pd.DataFrame(municipal).pivot(index='entidad',columns='periodo_documental',values='intervenciones_documentadas').reindex(STATES).to_markdown(),'',
           'El periodo publicado puede combinar documentos de distintos años y planes de desarrollo. No se traslada como operación continua a cada ronda ENASEM. No se suman las hojas COVID al listado principal ni las hojas estatales al agregado nacional.','',
           '## Vacíos históricos','',
           '2001–2003: reglas seleccionadas, sin inventario nacional equivalente descargado. Estatal 2015: no hay corte listado por CONEVAL; los cortes 2014/2016 no lo reemplazan. Municipal 2018/2021: no hay corte exacto aquí; 2017/2020 no prueban continuidad. Federal: se retiene 2004–2021 del libro 2004–2023; 2022/2023 se excluyen. 2024 no se incorpora a ENASEM.','',
           'Las hojas contienen intervenciones cuya relevancia directa o de hogar para adultos mayores debe revisarse. El número de intervenciones varía con la metodología y disponibilidad documental; no mide expansión, gasto individual, eficacia ni cobertura de beneficiarios.','',
           'Los requisitos, beneficios monetarios/en especie y fecha efectiva se cotejan por programa antes de asignar tipos. Los campos nulos son pendientes; presupuesto de programa/hogar nunca es monto individual.']
    write_project_text(project_path('docs/pensiones/nacional', 'COBERTURA_DOCUMENTAL.md'), '\n'.join(lines)+'\n')
    print('TOTAL',len(records),'PENDIENTES',len(failure))


if __name__=='__main__':
    main()
