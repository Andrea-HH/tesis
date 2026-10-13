"""Notebook J02 reproducible con tablas/figuras completas y verificación de preservación."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text

import argparse
import json
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT=Path(__file__).resolve().parents[1]


def build() -> nbformat.NotebookNode:
    """Muestra exclusivamente agregados; RECALCULAR no repite integración/auditoría."""
    public=project_path('', 'docs/eda/proteccion_economica')
    md,code=nbformat.v4.new_markdown_cell,nbformat.v4.new_code_cell
    notebook=nbformat.v4.new_notebook()
    notebook.cells=[md('# 05d · Armonización económica y EDA conjunto de pensiones/apoyos\n\n'
        'Objetivo: describir recepción y coexistencia entre perfiles 60+ por visita, 2001–2021. '
        'Fuente: base longitudinal existente y titularidad v1. CP1, auditoría y base anterior intactos. '
        'K no equivale a contributiva; A no equivale a no contributiva. No hay modelos ni efectos de políticas.'),
        md('## Método, población y denominadores\n\n'
        'N total: edad ≥60 en cada visita. N elegible vivo: modalidades 1–4; fallecidos y edad desconocida '
        'se contabilizan en flujo y seguimiento. N conocido: respuestas 1/2 admisibles y beneficiario orientado. '
        'Los registros sobre fallecidos carecen normalmente de edad contemporánea y no se incluyen por inferencia. '
        'Edad/sexo/anomalías originales no se corrigen. Sustitutos se conservan y se desglosan. '
        'Educación: años en primera entrevista. Localidad: corte 100 mil, no ruralidad estricta. '
        'Resultados descriptivos de muestra; pesos/diseño y deflactor pendientes. '
        'Las sumas se separan por evento/beneficiario/bloque/versión. No se suman K+A ni montos propios y cónyuge.'),
        code("from pathlib import Path\nfrom hashlib import sha256\nimport json,sys\nimport pandas as pd\n"
             "from IPython.display import display,Markdown,Image\n"
             "ROOT=next(p for p in [Path.cwd(),*Path.cwd().parents] if (p/'pyproject.toml').exists())\n"
             "sys.path.insert(0,str(ROOT/'scripts'))\nfrom run_protection_eda import run\nfrom export_protection_manuscript import export\n"
             "RECALCULAR=False\nif RECALCULAR:\n    run()\n"
             "public=ROOT/'docs/eda/proteccion_economica'\nprivate=ROOT/'data/processed/armonizacion_economica_v1'\n"
             "r=json.loads((public/'resultados.json').read_text())\n"
             "for path,digest in r['huellas_preservadas'].items():\n    assert sha256((ROOT/path).read_bytes()).hexdigest()==digest\n"
             "manifest=json.loads((private/'manifest.json').read_text())\n"
             "for path,digest in manifest['salidas'].items():\n    assert sha256((private/path).read_bytes()).hexdigest()==digest\n"
             "p=pd.read_parquet(private/'personas_ronda.parquet')\n"
             "old=pd.read_parquet(ROOT/'data/processed/auditoria_titularidad_v1/personas_ronda.parquet')\n"
             "assert len(p)==99676 and p.id.nunique()==27171 and not p[['id','ronda']].duplicated().any()\n"
             "for field in ['id','cunicah','np','ronda','pension_propia_k','pension_conyuge_k','titularidad_rama']:\n    assert p[field].equals(old[field])\n"
             "assert p.vejez_identificada_2021.equals(old.apoyo_vejez_propio_2021)\n"
             "print('Entradas anteriores preservadas, 99,676 registros, claves y titularidad sin cambios. Ningún ID se muestra.')\n"
             "display(pd.DataFrame(r['cobertura']))"),
        md('## Contratos y procedencia\n\n'
           '2001 depende de orientación publicada sin J1; punteros discordantes permanecen desconocidos. '
           '2015 conserva 33 firmas candidatas y discrepancia documental de códigos monetarios K80/K83. '
           'Hasta 2015 el apoyo es agregado sin programa observado. En 2018 se desglosan dos instituciones; '
           '2021 añade explícitamente vejez. Original, imputado y construido son versiones separadas. '
           'Una cifra almacenada no acredita respuesta válida ni unidad homologada.'),
        code("display(pd.DataFrame(json.loads((public/'contratos_armonizacion.json').read_text())))\n"
             "versions=pd.DataFrame(json.loads((public/'versiones_fuente.json').read_text()))\n"
             "display(versions.groupby(['ano','fuente'],dropna=False).agg(N_columnas_revisadas=('variable','size'),"
             " N_almacenados=('N_almacenado_no_faltante','sum'),N_tags=('N_tags','sum')).reset_index())\n"
             "display(versions)\ndisplay(pd.DataFrame(r['ponderadores']))")]
    report=read_project_text(public/'INFORME_PROTECCION_ECONOMICA.md')
    for year in (2001,2003,2012,2015,2018,2021):
        section=report.split(f'### {year}\n',1)[1].split('\n### ',1)[0].split('\n## ',1)[0]
        # Prosa calculada específica, conservando tablas en las celdas de código correspondientes.
        prose='\n\n'.join(line for line in section.split('\n\n') if line.strip() and not line.startswith('|') and not line.startswith('!['))
        notebook.cells += [md(f'## Ronda {year}: resultados e interpretación\n\n'+prose),
            code(f"part=p.loc[p.ano.eq({year}) & p.edad.ge(60)]\n"
                 f"summary=next(x for x in r['cobertura'] if x['ano']=={year})\nassert len(part)==summary['N_60']\n"
                 f"rates=[x for x in r['recepcion'] if x['ano']=={year}]\n"
                 "for x in rates:\n    assert x['N_si']+x['N_no']+x['N_desconocido']==len(part)\n"
                 "    assert part[x['variable']].eq(True).sum()==x['N_si']\n"
                 f"cats=[x for x in r['categorias'] if x['ano']=={year}]\nassert sum(x['N'] for x in cats)==len(part)\n"
                 "display(pd.DataFrame(rates))\ndisplay(pd.DataFrame(cats))\n"
                 f"display(pd.DataFrame([x for x in r['modalidades'] if x['ano']=={year}]))\n"
                 f"display(pd.DataFrame([x for x in r['asociaciones'] if x['ano']=={year}]))\n"
                 f"display(pd.DataFrame([x for x in r['asociaciones_ordinales'] if x['ano']=={year}]))")]
        for suffix in ('pension_apoyo','recepcion_localidad_grupo','recepcion_sexo_grupo','recepcion_educacion_grupo',
                       'recepcion_edad_grupo','pension_apoyo_localidad_grupo','pension_apoyo_sexo_grupo',
                       'pension_educacion_grupo_sexo_grupo','pension_edad_grupo_localidad_grupo'):
            key=f'{year}_{suffix}'
            notebook.cells += [md('### '+suffix.replace('_',' ')+'\n\n'
                'Tabla numérica de respaldo y BrBG. Tasas dentro de grupos y composición de receptores se presentan '
                'como denominadores diferentes. Las medidas de asociación usan pares conocidos; las tablas incluyen ND.'),
                code(f"rows=r['cruces']['{key}']\ndisplay(pd.DataFrame(rows))\n"
                     f"display(Image(filename=str(ROOT/'reports/proteccion_economica/figuras/{key}.png')))\n"
                     f"assert json.loads((public/'tablas/{key}.json').read_text())==rows")]
        notebook.cells += [code(f"display(pd.DataFrame([x for x in r['programas'] if x['ano']=={year}]))\n"
             f"display(pd.DataFrame([x for x in r['instituciones'] if x['ano']=={year}]))\n"
             f"display(pd.DataFrame([x for x in r['montos'] if x['ano']=={year}]))")]
    notebook.cells += [md('## Seguridad social y programa de vejez explícito\n\n'
        'Evidencia IMSS/ISSSTE incluye prestaciones derivadas. No evidencia no equivale a ausencia de '
        'toda pensión contributiva: ND conserva las demás instituciones no tipificadas. '
        'En el cruce, No seguridad social corresponde a negativa K y No vejez a negativa A. '
        'La vejez explícita solo se construye en 2021 por opción 5, sin inferirla de edad, monto o nombre aproximado.'),
        code("display(pd.DataFrame(r['cobertura_institucional']))\ndisplay(pd.DataFrame(r['seguridad_social_vejez_2021']))\n"
             "display(pd.DataFrame(r['cruces']['2021_pension_apoyo_seguridad_social_vejez']))\n"
             "display(Image(filename=str(ROOT/'reports/proteccion_economica/figuras/2021_pension_apoyo_seguridad_social_vejez.png')))"),
        md('## Seguimiento y comparabilidad\n\n'
           'La cohorte de origen es viva y de 60+. Se distinguen faltantes, muerte registrada y ausencias con/sin '
           'reaparición posterior. No se infiere muerte de ausencia ni inicio administrativo de una afirmativa. '
           'Los intervalos son nominales; año de entrevista efectiva permanece conservado. '
           'Solo los contratos condicionadamente comparables admiten interpretación de transición de recepción.'),
        code("display(pd.DataFrame(r['comparabilidad']))\n"
             "for (a,b,v),g in pd.DataFrame(r['transiciones']).groupby(['ano_origen','ano_destino','variable']):\n"
             "    assert g.N.sum()==g.N_cohorte_origen.iloc[0]\n    display(g)\n"
             "    display(Image(filename=str(ROOT/f'reports/proteccion_economica/figuras/transicion_{v}_{a}_{b}.png')))"),
        md('## Contabilidad, pendientes y escritura\n\n'
           'Se conservan instituciones/montos por evento y beneficiario. No se suman bloques K+A ni versiones. '
           'Coincidencias nominales son candidatos a revisar y no duplicaciones demostradas. '
           'Montos parciales nominales no son suficiencia económica. Clasificación definitiva pendiente.'),
        code("display(pd.DataFrame(r['pendientes_revisados']))\n"
             "k=pd.read_parquet(private/'eventos_pensionarios.parquet')\na=pd.read_parquet(private/'eventos_apoyos.parquet')\n"
             "assert not k[['ano','hogar_fuente','fuente','version','rama','tipo','slot']].duplicated().any()\n"
             "assert not a[['ano','hogar_fuente','fuente','version','rama','slot']].duplicated().any()\n"
             "assert set(k.version)==set(a.version)=={'original'}\n"
             "for z in r['montos']:\n    events=k if z['bloque']=='K' else a\n"
             "    ids=set(p.loc[p.ano.eq(z['ano']) & p.edad.ge(60),'id'])\n"
             "    s=events.loc[events.ano.eq(z['ano']) & events.beneficiario_id.isin(ids)]\n"
             "    assert len(s)==z['N_eventos']\n    assert abs(s.monto_mensual_observado.sum()-z['suma_parcial_por_bloque'])<0.01\n"
             "index=json.loads((public/'indice_artefactos.json').read_text())\nassert len(index)==65\n"
             "for item in index:\n    assert (ROOT/item['tabla']).exists() and (ROOT/item['figura']).exists()\n"
             "display(pd.DataFrame(index))\nexport()\n"
             "print('Manuscrito sincronizado; CP1/auditoría/base preservados, sin modelos ni publicación.')"),
        md('## Conclusión y límites\n\n'
           'Los apoyos aparecen tanto entre negativas K como entre receptoras K. Las asociaciones por perfiles '
           'se interpretan dentro de ronda y con cobertura conocida. En 2021 cambia la opción explícita de vejez: '
           'la diferencia histórica no identifica efecto causal ni prevalencia nacional. '
           'Pendientes: ruralidad estricta, diseño/ponderación, precios, J1/órdenes, punteros, firmas 2015, '
           'programas agrupados, especie y reconciliación entre bloques/versiones. '
           'Las tablas de respaldo y el informe completo permanecen fuera de la selección editorial del manuscrito.')]
    notebook.metadata.kernelspec={'display_name':'Python 3','language':'python','name':'python3'}
    notebook.metadata.language_info={'name':'python','version':'3.11'}
    nbformat.write(notebook,project_path('', 'notebooks/05d_pensiones_apoyos.ipynb'))
    return notebook


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    notebook=build()
    if args.execute:
        NotebookClient(notebook,timeout=1200,kernel_name='myenv',resources={'metadata':{'path':str(ROOT)}}).execute()
        nbformat.write(notebook,project_path('', 'reports/notebooks/05d_pensiones_apoyos_ejecutado.ipynb'))
        print('Notebook J02 ejecutado; exclusivamente tablas y figuras agregadas.')
