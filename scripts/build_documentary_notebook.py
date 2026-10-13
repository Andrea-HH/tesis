"""Notebook documental reproducible; no integra ni analiza nuevamente microdatos."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text
import argparse
from pathlib import Path
import nbformat
from nbclient import NotebookClient

ROOT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(project_path('', 'src')))
from tesis_enasem.program_catalog import academic_spacing


def build() -> nbformat.NotebookNode:
    """Incluye cobertura íntegra, búsquedas trazables y síntesis de límites."""
    def md(text: str) -> nbformat.NotebookNode:
        return nbformat.v4.new_markdown_cell(academic_spacing(text))
    code=nbformat.v4.new_code_cell
    cells=[md('''# Recuperación del documento original y catálogo nacional

Objetivo: recuperar planteamiento/estilo de la autora y contextualizar protección económica sin cambiar decisiones ni recepción individual. Una fila del catálogo es intervención-ejercicio/periodo-territorio, no persona ni programa histórico único. Se conserva toda la oferta inventariada; su relevancia y normas se validan por separado.

El notebook reutiliza las extracciones guardadas. `RECONSTRUIR=True` vuelve a leer únicamente inventarios documentales; no recalcula integración, CP1, titularidad ni J02. Los cortes discontinuos y documentos normativos no se rellenan con supuestos.
'''),code('''from pathlib import Path
import json, hashlib, sys, subprocess
import pandas as pd
import matplotlib.pyplot as plt
ROOT=Path.cwd()
if not (ROOT/'src').exists(): ROOT=ROOT.parent
sys.path.insert(0,str(ROOT/'src'))
D=ROOT/'docs/pensiones/nacional'
RECONSTRUIR=False
if RECONSTRUIR:
    subprocess.run([sys.executable,str(ROOT/'scripts/build_national_catalog.py')],check=True)
    subprocess.run([sys.executable,str(ROOT/'scripts/export_national_context.py')],check=True)
index=json.loads((D/'indice_catalogo.json').read_text())
catalog=[r for s in index['fuentes'] for r in json.loads((ROOT/s['archivo_catalogo']).read_text())]
assert len(catalog)==index['N_registros_documentales']
assert len({r['registro_documental'] for r in catalog})==len(catalog)
assert not index['problemas_parseo']
display(pd.DataFrame([{'Nivel':k,'Registros documentales':v} for k,v in index['por_nivel'].items()]))
'''),md('''## Diagnóstico y conciliación del PDF

Se revisaron 65 páginas; los cuadros 3.1–3.5 se comprobaron visualmente. El resumen de CVA se excluye, H1–H3 son marcadores y el resultado alterna cuartil/quintil. La pregunta vigente se conserva. No se publica matrícula ni texto íntegro del PDF. La matriz distingue contenido recuperado, conservado, actualizado y pendiente.
'''),code('''pdf=ROOT/'data/raw/Andrea_Hernandez (1).pdf'
assert hashlib.sha256(pdf.read_bytes()).hexdigest()=='f8d02542886fa039bd3b86cf6a7ac9915c4fcf2460fc90a6959fb884f1c5aea8'
import pymupdf
with pymupdf.open(pdf) as doc: assert len(doc)==65
matrix=json.loads((ROOT/'docs/recuperacion/matriz_conciliacion.json').read_text())
display(pd.DataFrame(matrix))
print('Original conservado localmente; no se incorpora el resumen ajeno.')
'''),md('''## Fuentes, huellas y cobertura

El manifiesto permite repoblar el cache con `build_national_catalog.py --download`. Cada descarga y libro se verifica mediante SHA256. Los archivos bloqueados no se consideran revisados. No se suman hojas por entidad al agregado estatal, ni hojas COVID al principal municipal. La cobertura es documental, no efectividad o tasa de recepción.
'''),code('''sources=json.loads((D/'fuentes_descargadas.json').read_text())
for s in sources:
    if 'error' not in s:
        assert hashlib.sha256((ROOT/s['archivo']).read_bytes()).hexdigest()==s['sha256']
display(pd.DataFrame([{k:s.get(k) for k in ['id','periodo','url','fecha_consulta','error']} for s in sources]))
state=pd.DataFrame(json.loads((D/'cobertura_estatal.json').read_text()))
municipal=pd.DataFrame(json.loads((D/'cobertura_municipal.json').read_text()))
assert len(state)==32*8 and len(municipal)==32*5
assert state.intervenciones_inventariadas.sum()==index['por_nivel']['estatal']
assert municipal.intervenciones_documentadas.sum()==index['por_nivel']['municipal']
display(state.pivot(index='entidad',columns='anio',values='intervenciones_inventariadas'))
display(municipal.pivot(index='entidad',columns='periodo_documental',values='intervenciones_documentadas'))
'''),md('''### Visualización de la cobertura documental estatal

La intensidad expresa filas inventariadas; una celda 0 representa cero filas localizadas, no inexistencia de programas. Las diferencias entre cortes también pueden reflejar cambios de recopilación. No se compara como expansión causal ni cobertura de receptores. La matriz numérica anterior es el respaldo íntegro.
'''),code('''wide=state.pivot(index='entidad',columns='anio',values='intervenciones_inventariadas')
fig,ax=plt.subplots(figsize=(9,11))
im=ax.imshow(wide.to_numpy(),cmap='BrBG',aspect='auto')
ax.set_xticks(range(len(wide.columns)),wide.columns)
ax.set_yticks(range(len(wide)),wide.index)
ax.set_title('Intervenciones estatales documentadas por ejercicio\\nConteos de inventario; no beneficiarios')
fig.colorbar(im,ax=ax,label='Registros documentales')
fig.tight_layout()
target=ROOT/'reports/contexto_documental';target.mkdir(exist_ok=True,parents=True)
fig.savefig(target/'cobertura_estatal_brbg.png',dpi=160)
plt.show()
'''),md('''## Consulta completa y relevancia para vejez

Los marcadores organizan la revisión léxica; no asignan elegibilidad ni tipo pensionario. Todos los registros, también sin marcador, se mantienen consultables. Mostrar los nombres de intervenciones no publica beneficiarios. Una prestación dirigida a familias puede ser relevante para hogares de personas mayores, aunque no tenga edad de vejez como criterio.
'''),code('''frame=pd.DataFrame(catalog)
display(pd.DataFrame([{'Nivel':l,'N total documental':int((frame.nivel_gobierno==l).sum()),
                      'Marcadas vejez (revisión)':sum('vejez' in r['marcadores_revision'] for r in catalog if r['nivel_gobierno']==l)}
                     for l in ['estatal','federal','municipal']]))
def buscar(texto='',entidad=None,nivel=None):
    result=frame.loc[frame.nombre_oficial.str.contains(texto,case=False,regex=False)]
    if entidad: result=result.loc[result.territorio.eq(entidad)]
    if nivel: result=result.loc[result.nivel_gobierno.eq(nivel)]
    return result[['registro_documental','nombre_oficial','nivel_gobierno','territorio','fuente_id','hoja','fila_excel','estado_verificacion']]
display(buscar('adult',nivel='estatal'))
'''),md('''## Programas versus variables y rondas ENASEM

Se distingue programa/familia nombrada, institución, donativo agregado y desconocido. La existencia documental no asigna recepción. Nombre coincidente de una versión anterior no demuestra continuidad hasta una ronda posterior. No se identifica discapacidad a partir de K-invalidez, ni INAPAM como pensión monetaria. Los montos y la orientación propia/cónyuge permanecen separados.
'''),code('''contracts=json.loads((D/'matriz_variables_rondas.json').read_text())
mapping=json.loads((D/'matriz_programas_enasem.json').read_text())
assert len(mapping)==len(catalog)
display(pd.DataFrame(contracts))
display(pd.DataFrame(json.loads((D/'versiones_normativas_nuevas.json').read_text())))
display(pd.DataFrame(mapping).groupby(['nivel','categoria_correspondencia']).size().rename('N documental').reset_index())
'''),md('''## Reutilización de los resultados de protección económica

Los conteos siguientes son los ya calculados en J02: 60+ en cada visita, todas las modalidades disponibles y sin ponderar. N válido y desconocidos están separados en el notebook 05d. El contexto no añade clasificaciones ni permite conclusiones estatales. Los cuadros LaTeX preservan sus cifras y cambian solamente formato. Las 65 figuras y tablas completas permanecen en 05d.
'''),code('''j02=json.loads((ROOT/'docs/eda/proteccion_economica/resultados.json').read_text())
assert j02['N_personas_ronda_60']==56004
display(pd.DataFrame(j02['cobertura']))
display(pd.DataFrame(j02['recepcion']))
display(pd.DataFrame(j02['brechas_apoyo']))
print('Interpretación detallada y denominadores: informe J02; catálogo no estima efectos de programas.')
'''),md('''## Conciliación y límites pendientes

El catálogo tiene cobertura territorial nacional mediante cortes, pero no es un censo histórico exhaustivo. Reglas/importes individuales aún requieren cotejo. Los programas locales no se atribuyen desde residencia ni monto. La recepción propia/cónyuge sigue provisional; J1 de 2001, punteros y33 firmas de 2015no se corrigen. No se elige cuartil/quintil, muestra predictiva, pesos ni modelos. El informe de revisión académica distingue validación estructural de aprobación científica.
''')]
    nb=nbformat.v4.new_notebook(cells=cells)
    nb.metadata.kernelspec={'display_name':'Python3','language':'python','name':'python3'}
    nb.metadata.language_info={'name':'python','version':'3.11'}
    nbformat.write(nb,project_path('', 'notebooks/05e_contexto_documental.ipynb'))
    return nb


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');args=p.parse_args()
    nb=build()
    if args.execute:
        NotebookClient(nb,timeout=600,kernel_name='myenv',resources={'metadata':{'path':str(ROOT)}}).execute()
        nbformat.write(nb,project_path('', 'reports/notebooks/05e_contexto_documental_ejecutado.ipynb'))
        print('Notebook documental ejecutado; resultados previos reutilizados.')
