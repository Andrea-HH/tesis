"""Notebook08 independiente, fuente limpia y copia ejecutada desde cero."""

import copy
import json
import os
import re
from hashlib import sha256
from pathlib import Path

import nbformat
from nbclient import NotebookClient

from validate_benefit_transitions import check
from tesis_enasem.benefit_transitions import NOTEBOOK, OUTPUT, QUESTION, save_json, verify_inputs
from tesis_enasem.benefit_transition_outputs import interpretations, make_figures
from tesis_enasem.project_paths import INTERIM_DIR, PROJECT_ROOT


def rebase_links(nb: nbformat.NotebookNode, source_dir: Path, target_dir: Path) -> None:
    """La copia ejecutada conserva enlaces válidos desde su propia ubicación."""
    def replace(match: re.Match) -> str:
        value=match[1]
        if value.startswith(('http:','https:','#','data:')):return match[0]
        path,sep,fragment=value.partition('#')
        relative=os.path.relpath((source_dir/path).resolve(),target_dir)
        return ']('+relative+(sep+fragment if sep else '')+')'
    for cell in nb.cells:
        if cell.cell_type=='markdown':cell.source=re.sub(r'\]\(([^)]+)\)',replace,cell.source)


def build() -> None:
    """Explica, recalcula08 y coteja; nunca modifica01–07 ni los datos fuente."""
    check();r=json.loads((OUTPUT/'resultados.json').read_text());reading=interpretations(r)
    save_json(OUTPUT/'figuras.json',make_figures(r))
    md,code=nbformat.v4.new_markdown_cell,nbformat.v4.new_code_cell
    cells=[md(f'''# 08 · Transiciones de recepción y montos pensionarios, ENASEM

**Pregunta central conservada:** {QUESTION}

**Objetivo independiente:** explicar la divergencia cobertura/monto mediante recepción observada, nuevos y continuos, precios, composición y selección. Se profundiza en K 2012–2015 y A general 2015–2018; no se repite el EDA ni se modifica 01–07.

Principal: cohorte basal de personas vivas registradas con entrevista directa, 60+ por visita inicial. No panel balanceado, causalidad, ponderación nacional ni identidad administrativa del beneficio. Los conflictos de estado vital se conservan y separan de las transiciones válidas.

No se suman importes cuando algún evento captado carece de monto. Captura íntegra no garantiza todos los beneficios reales. A incluye dinero/especie; **A5 de vejez no es una serie longitudinal en estos periodos**. [Contrato de definiciones08](../diccionarios/contrato_transiciones_montos_pensionarios.json).

[Copia ejecutada con resultados](../data/interim/notebooks_ejecutados/08_TRANSICIONES_MONTOS_PENSIONARIOS_ejecutado.ipynb). [Informe académico único](../resultados/INFORME_GENERAL.md).'''),
        code('''import json
import pandas as pd
from IPython.display import display, Markdown, Image
from tesis_enasem.benefit_transitions import analyze, OUTPUT, verify_inputs
from tesis_enasem.benefit_transition_outputs import interpretations
from tesis_enasem.project_paths import RESULTS_DIR
verify_inputs()
r=analyze()  # ejecuta08 desde cero; no ejecuta01–07
assert r==json.loads((OUTPUT/'resultados.json').read_text()),'08 no reproducido exactamente'
audit=r['auditoria'];texts=interpretations(r)
figs=json.loads((OUTPUT/'figuras.json').read_text())
pd.set_option('display.max_columns',None)
pd.set_option('display.max_rows',80)
pd.set_option('display.float_format',lambda x:f'{x:,.3f}')
def tabla(rows):
    display(pd.json_normalize(rows,sep='.'))
def figura(key):
    f=next(f for f in figs if f['clave']==key)
    display(Image(filename=str(RESULTS_DIR/f['archivo'])))
    display(Markdown('**Nota:** '+f['nota']))
def contexto(z):return dict(origen=z['origen'],destino=z['destino'],via=z['via'])
def montos(rows):
    return [dict(**{k:v for k,v in z.items() if k not in ['nominal','real','real_12m','real_ano_entrevista']},
        nominal_N=z['nominal']['N'],nominal_mediana=z['nominal']['mediana'],
        nominal_q25=z['nominal']['q25'],nominal_q75=z['nominal']['q75'],
        real_N=z['real']['N'],real_mediana=z['real']['mediana'],
        real_q25=z['real']['q25'],real_q75=z['real']['q75']) for z in rows]
''')]
    def section(title: str,question: str,source: str,explanation: str) -> None:
        cells.extend([md('## '+title+'\n\n'+question),code(source),md('**Interpretación, estado y límites:** '+explanation)])
    section('1. Auditoría de fuentes y seis rondas','Antes de comparar montos: población, recepción, integridad de captura y unidad.',
        "tabla(audit['rondas']); tabla(audit['intervalos']); tabla(audit['comparabilidad']); tabla([{'via':k,**v} for k,v in audit['diagnosticos']['eventos'].items()])",
        reading['auditoria'])
    section('2. Transiciones de recepción en las seis ventanas elegibles','Mismos IDs, LEFT uno:uno y denominador de toda la cohorte o pares conocidos explícito.',
        "tabla([{**contexto(z),**x,'N_cohorte':z['N_cohorte'],'N_pares_conocidos':z['N_pares_conocidos']} for z in r['transiciones'] for x in z['estados']]); figura('seguimiento')",
        'No→Sí es inicio observado de respuesta afirmativa; Sí→No es fin observado de declaración. No alta/baja administrativa. Muerte, ausencia, sustituto, recepciónND y conflicto vital son categorías distintas. Las rupturas de K/A quedan excluidas de las ventanas analizadas.')
    section('3. Denominadores y cambios de universo','Distinguir probabilidad condicional a reobservación de fracción sobre cohorte basal.',
        "tabla([{**contexto(z),**{k:v for k,v in z.items() if k not in ['estados','origen','destino','via']}} for z in r['transiciones']]); tabla([{**contexto(z),**z['otra_via_previa']} for z in r['analisis']])",
        'Nuevos K pueden haber recibido A antes, y nuevos A pueden haber tenido K. No equivalen a primera protección económica. Las tasas condicionales excluyen muertes/ausencias y no representan riesgos de toda la cohorte.')
    section('4. Nuevos frente a continuos y cese de declaración','Importes de destino para nuevos/continuos; importes basales para Sí→No.',
        "tabla([{**contexto(z),**x} for z in r['analisis'] for x in montos(z['montos_grupos'])]); figura('nuevos_continuos')",
        reading['nuevos'])
    section('5. Mezcla observada y entradas a la población60+','No confundir nuevos receptores de la cohorte con muestra nueva, reaparición o entrada por edad.',
        "tabla([{**contexto(z),**x} for z in r['analisis'] for x in z['mezcla_observada']]); tabla([{**contexto(z),**x} for z in r['analisis'] for x in z['composicion_destino']['grupos']]); tabla([{**contexto(z),**x} for z in r['analisis'] for x in z['perfiles_transversales06_07']])",
        reading['mezcla']+'\n\n'+reading['composicion_transversal']+' Un registro con antecedente sobre fallecido se conserva como conflicto, sin afirmar pago posterior a muerte.')
    section('6. Instituciones y cambios de concepto K','Comprobar evidencia, sin asignar el mismo programa a toda K o repartir importes multiinstitucionales.',
        "tabla([{**contexto(z),**x} for z in r['analisis'] for x in z['evidencia_institucional']])",
        'Código8 agrupa programas públicos federales/estatales. IMSS/ISSSTE identifica evidencia institucional, no contributividad. Las categorías pueden solaparse; los importes son personales de todos los eventos íntegros, no monto atribuible a cada institución.')
    section('7. Tres estimandos monetarios distintos','Medianas transversales, diferencias de medianas de pares y medianas de cambios personales.',
        "tabla([{**contexto(z),'ronda':x['ronda'],'N_parcial07':x['N_monto_parcial07'],'nominal_parcial':x['nominal_parcial07']['mediana'],'real_parcial':x['real_parcial07']['mediana'],'N_integro':x['real_integro']['N'],'nominal_integro':x['nominal_integro']['mediana'],'real_integro':x['real_integro']['mediana']} for z in r['analisis'] for x in z['transversal']]); tabla([{**contexto(z),**z['pares']} for z in r['analisis']]); figura('cambios_personales')",
        reading['pares'])
    section('8. Inflación y nominal: identidad contable','Aplicar INPC por entrevista real antes de resumir; no confundir fecha elegida y fecha de pago.',
        "tabla([{**contexto(z),**z['pares']['puente_medianas']} for z in r['analisis']]); tabla([{**contexto(z),**z['pares']['identidad_contable']} for z in r['analisis']]); tabla([{**contexto(z),'inflacion':z['pares']['inflacion_criterio_periodo_pct'],'meses':z['pares']['meses_entrevistas']} for z in r['analisis']])",
        reading['precios'])
    section('9. Sensibilidad temporal, de evento y concepto','Revisar magnitudes pequeñas y signos dependientes del calendario.',
        "tabla([{**contexto(z),**{k:x.get(k) for k in ['criterio','N','N_vital_discordante']},'delta_real':x['cambio_individual_real']['mediana'],'delta_12m':x['cambio_real_12m']['mediana'],'delta_ano_entrevista':x['cambio_real_ano_entrevista']['mediana']} for z in r['analisis'] for x in z['sensibilidades'] if 'cambio_individual_real' in x])",
        reading['sensibilidad'])
    section('10. Perfiles de nuevos, continuos y cese','Sexo, edad, escolaridad inicial, localidad, ocupación y estado conyugal: basales y finales separados.',
        "for z in r['analisis']:\n    display(Markdown(f\"### {z['via']} {z['origen']}–{z['destino']}\"))\n    for dim in ['sexo_grupo','edad_06','educacion_grupo','localidad_grupo','ocupacion_grupo','conyugal_grupo']:\n        tabla([x for x in z['perfiles'] if x['dimension']==dim])",
        reading['perfiles'])
    section('11. Montos y cambios personales por perfil','Cuantiles monetarios en ambas unidades y medianas de cambios, con N de cada población.',
        "for z in r['analisis']:\n    display(Markdown(f\"### {z['via']} {z['origen']}–{z['destino']}\"))\n    tabla(z['montos_por_perfil'])\n    tabla([{k:x[k] for k in ['dimension','grupo','N','nominal_inicial','nominal_final','real_inicial','real_final','cambio_individual_nominal','cambio_individual_real','N_real_baja','N_real_sube']} for x in z['cambios_por_perfil']])",
        'Medianas/IQR/P10/P90 reducen el dominio de extremos; las medias no gobiernan la interpretación. No se eliminan importes altos ni se fabrican Gini con cuantiles. Grupos pequeños y selección limitan la precisión; no pruebas de significancia o inferencia nacional.')
    section('12. Comparación por composición común','Estimando explícito y celdas mínimas, con soporte y cobertura por grupo.',
        "tabla([{**contexto(z),**{k:v for k,v in z['ajuste'].items() if k not in ['estratos','distribuciones']}} for z in r['analisis']]); tabla([{**contexto(z),**x} for z in r['analisis'] for x in z['ajuste']['estratos']]); tabla([{**contexto(z),**x} for z in r['analisis'] for x in z['ajuste']['distribuciones']])",
        reading['ajuste'])
    section('13. Localidad en soporte y modalidad por sustituto','Sensibilidades con sus propios N, no sustitución del principal.',
        "tabla([{**contexto(z),**{k:v for k,v in z['ajuste_localidad_sensibilidad'].items() if k not in ['estratos','distribuciones']}} for z in r['analisis']]); tabla([{**contexto(z),**x} for z in r['analisis'] for x in z['ajuste_localidad_sensibilidad']['distribuciones']]); tabla([{**contexto(z),**x} for z in r['analisis'] for x in z['sensibilidades'] if 'patron' in x])",
        'La sensibilidad permite sustituto válido solo en destino manteniendo las mismas directas basales. No equivale a incluir sustitutos basales. La estabilidad de medianas generales no garantiza ausencia de selección ni igualdad de las colas.')
    section('14. Mortalidad, ausencia y reapariciones','Características y montos basales de todos los destinos; no imputación de pagos post mortem.',
        "tabla([{**contexto(z),'recepcion_basal':s['recepcion_basal'],'N_basal':s['N_basal'],**x} for z in r['analisis'] for s in z['seleccion'] for x in s['destinos']]); tabla([{**contexto(z),**{k:v for k,v in s.items() if k!='destinos'}} for z in r['analisis'] for s in z['seleccion']])",
        reading['seleccion'])
    cells.append(md('## 15. Política vigente, indicador y lectura\n\n'+reading['politica']))
    cells.append(md('## 16. Conclusión integrada y límites\n\n'+reading['resumen']+'\n\n'+reading['conclusion']+'\n\n**Estado:** validado aritméticamente y reproducido desde cero; comparabilidad operacional condicionada, identidad de programa y representatividad no acreditadas. Resultados relevantes en el mismo informe y PDF.'))
    cells.append(code("verify_inputs()\nassert r==json.loads((OUTPUT/'resultados.json').read_text())\nprint('08 reproducido, denominadores y fuentes anteriores verificados.')"))
    nb=nbformat.v4.new_notebook(cells=cells,metadata={'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'},'language_info':{'name':'python','version':'3.11'}})
    source=PROJECT_ROOT/'notebooks'/NOTEBOOK;ledger=OUTPUT/'notebook.json'
    if source.exists():
        assert ledger.exists() and sha256(source.read_bytes()).hexdigest()==json.loads(ledger.read_text())['fuente_sha256'],'Notebook08 editado manualmente'
    nbformat.write(nb,source)
    executed=NotebookClient(copy.deepcopy(nb),timeout=240,kernel_name='python3',resources={'metadata':{'path':str(PROJECT_ROOT)}}).execute()
    assert not any(o.get('output_type')=='error' for c in executed.cells for o in c.get('outputs',[]))
    copy_path=INTERIM_DIR/'notebooks_ejecutados'/NOTEBOOK.replace('.ipynb','_ejecutado.ipynb')
    rebase_links(executed,source.parent,copy_path.parent)
    nbformat.write(executed,copy_path)
    save_json(ledger,dict(fuente_sha256=sha256(source.read_bytes()).hexdigest(),
        ejecutado_sha256=sha256(copy_path.read_bytes()).hexdigest(),celdas=len(cells),
        celdas_codigo=sum(c.cell_type=='code' for c in cells),ejecutado_desde_cero=True,
        insumos_protegidos=verify_inputs()))
    print('08 ejecutado:',len(cells),'celdas; fuente limpia y copia local con resultados.')


if __name__=='__main__':
    build()
