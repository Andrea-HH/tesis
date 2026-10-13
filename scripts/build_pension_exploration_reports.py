"""Informes y notebooks por bloque desde agregados pensionarios v1 existentes."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text

import argparse
import json
from pathlib import Path
import nbformat
from nbclient import NotebookClient
import pandas as pd

from run_pension_exploration import PUBLIC, ROOT, YEARS, checked_hashes, write_json

METHOD = '''La población descriptiva es de 60 años o más **en cada visita**, con todas las modalidades disponibles y sin exigir continuidad. El maestro conserva 99,676 filas/27,171 personas; la selección reproduce 56,004 personas-ronda/18,754 personas. Los filtros están en `PopulationSpec`. Los perfiles por ronda son composiciones transversales; el seguimiento usa IDs reales sin publicarlos.

Las tasas K/A y del cónyuge se calculan entre respuestas conocidas, con N total, N potencialmente elegible vivo, N conocido y ND separados. Elegibilidad potencial viva no prueba respuesta ni enlace válido. La partición Solo propia/Solo cónyuge/Ambas/Ambas negativas exige ambos estados conocidos; una respuesta indeterminada conserva ND incluso si la otra es afirmativa. Las pensiones K no son exclusivamente contributivas; A no es exclusivamente vejez ni pensión no contributiva. Los negativos solo se refieren al bloque observado. Las instituciones son de selección múltiple y sus porcentajes pueden sumar más de 100. Cada tabla explicita si la unidad es persona o evento; en los eventos N_total cuenta eventos y N_personas beneficiarios únicos. No se suman versiones, titulares, instituciones ni K+A.

La prevalencia de pensión del cónyuge en toda la muestra no es la tasa entre personas con rama de pareja elegible. La auditoría conserva un No operativo ante ausencia explícita de rama cónyuge residente; esto no equivale a una respuesta bruta negativa ni a ausencia de prestación de una pareja no residente. La categoría “Ambas negativas K” nombra dos estados derivados negativos y puede incluir ese caso estructural. El universo de pareja solo se confirma mediante el filtro y ambos punteros en2018/2021; los universos tempranos permanecen ND. `universos_conyuge.json` y figuras adicionales separan las dos definiciones sin corregir estados previos.


Edad: 60–64/65–69/70–74/75–79/80+. Escolaridad: 0/1–5/6/7–9/10+ años de la primera entrevista, **no grados académicos acreditados ni escolaridad adquirida entre visitas**. Localidad: <100 mil/≥100 mil habitantes, no rural/urbano estricto. Ocupación: condición de actividad, no profesión; retiro/incapacidad/no trabajo no equivale a pensión. Salario: pregunta específica de trabajo principal en la rama personal, únicamente entre quienes tienen filtro asalariado afirmativo; los demás no se convierten en cero. Montos salariales mes/año pendientes, no ingreso total.

Patrimonio es stock de entrevistado/pareja, con ceros y negativos conservados; no se agrega por vivienda ni se usa para definir vulnerabilidad. Montos K por evento son mensuales nominales originales admitidos por los contratos previos; las distribuciones se comparan dentro de ronda y no como crecimiento real. Los montos personales parciales no equivalen a prestaciones completas. Se excluyen códigos NR/NS conforme a cada contrato, además de tags Stata; ninguna regla global 8/9 se aplica a todos los conceptos.

V de Cramér usa respuestas y perfiles conocidos. Sus N y celdas esperadas <5 se conservan. Spearman utiliza pares continuos válidos dentro de ronda. No se realizan pruebas de significancia ni se seleccionan relaciones confirmatorias: las asociaciones son exploratorias múltiples, sin causalidad. Ponderación, población objetivo y diseño no validados; **todos los resultados representan la muestra observada**.

En seguimiento la cohorte es viva y 60+ en origen; sexo, edad, escolaridad y localidad se fijan en origen. Una edad final desconocida o decreciente no excluye retrospectivamente a la persona: se conserva el estado pensionario orientado de destino, salvo entrevistas sobre fallecido. Esta decisión diferencia las nuevas trayectorias de las matrices J02, que además exigían edad final 60+. No corregimos edades. Fallecimiento registrado prevalece sobre recepción, ausencia no es pérdida ni muerte y reaparición se observa solo si hay una ronda posterior. Intervalos nominales: 2/9/3/3/3 años. Comparabilidad condicionada K: 2001–2003, 2012–2015 y 2018–2021; A: 2003–2012, 2012–2015 y 2015–2018. Las otras matrices describen correspondencias de estados de instrumento, **no inicio o pérdida homologados**. Las ramas del cónyuge mantienen los límites adicionales de orientación/filtro del instrumento.
'''


def md_table(rows: list[dict], columns: list[str] | None = None) -> str:
    """Tablas agregadas legibles, con ND explícito y sin truncar filas."""
    if not rows:return 'Sin celdas evaluables.'
    cols=columns or list(dict.fromkeys(k for x in rows for k in x))
    def fmt(x):
        if x is None or (isinstance(x,float) and pd.isna(x)):return 'ND'
        if isinstance(x,float):return f'{x:,.4f}'
        return str(x).replace('|','/').replace('\n',' ')
    return '\n'.join(['| '+' | '.join(cols)+' |','| '+' | '.join(['---']*len(cols))+' |']+
        ['| '+' | '.join(fmt(x.get(c)) for c in cols)+' |' for x in rows])


def build_reports() -> None:
    """La matriz se funda en resultados reales, nunca en cantidad de archivos."""
    r=json.loads(read_project_text(PUBLIC/'resultados.json'));rows=[]
    report=['# Hallazgos exploratorios pensionarios · versión 1','## Alcance y metodología',METHOD,
      '## Lectura del estado','Completo provisional significa tabla, figura e interpretación reproducibles bajo contratos provisionales; **no validación definitiva de titularidad o equivalencia histórica**. Los ocho bloques bivariados y ocho trivariados son localizables por código y ronda. B8 es parcial por montos salariales sin homologación. No se adopta pregunta, outcome, hipótesis principal ni modelo.']
    for key,x in r['analisis'].items():
        block=PUBLIC/'analisis'/f'{key}.md';block.parent.mkdir(exist_ok=True)
        obj=json.loads(read_project_text(project_path('', x['tabla'])))
        content=[f'# {key} · {x["solicitud"]}',f'**Estado: {x["estado"]}.**','## Pregunta y método',
         f'¿Cómo se distribuye {x["solicitud"].lower()} en {obj["ano"]}? Se usan '+
         ('simultáneamente '+', '.join(obj.get('grupos',[]))+' y la dimensión pensionaria.' if key.startswith(('T','C')) else 'la dimensión pensionaria y la característica indicada.'),
         'Población, filtros, unidades y fórmulas: [método común](../METODOLOGIA.md).',
         '## Resultado e interpretación',x['interpretacion'],
         '## Visualización principal',f'![{x["solicitud"]}](../../../../{x["figura"]})',
         '## Tablas completas y medidas',f'Respaldo exacto: [JSON](../tablas/{key}.json).']
        for name,data in obj.items():
            if isinstance(data,list) and data and isinstance(data[0],dict):
                content += ['### '+name.replace('_',' '),md_table(data)]
        if obj.get('figura_salario'):content += ['## Recepción salarial',f'![Salario](../../../../{obj["figura_salario"]})']
        if obj.get('limite'):content += ['## Límite de la asociación',obj['limite']]
        if obj.get('limite_ingreso'):content+=['## Limitación de ingresos',obj['limite_ingreso']]
        write_project_text(block, '\n\n'.join(content)+'\n')
        report += [f'## {key} · {x["solicitud"]}',x['interpretacion'],f'[Tablas completas y figura](analisis/{key}.md). Estado: **{x["estado"]}**.']
        rows.append({'Solicitud original':x['solicitud']+' · '+str(obj['ano']),
         'Análisis realizado':key+'; variables simultáneas' if key.startswith(('T','C')) else key,
         'Tabla generada':x['tabla'],'Gráfica generada':x['figura'],
         'Interpretación':f'docs/eda/pensiones_exploratorio_v1/analisis/{key}.md',
         'Archivo y ubicación':f'notebooks/06{"c" if key.startswith(("T","C")) else "b"}_eda_{"trivariado" if key.startswith(("T","C")) else "bivariado"}_pensiones.ipynb',
         'Estado':x['estado']})
    for year in YEARS:
        univ=r['univariados'][str(year)]
        content=[f'# Univariado pensionario · {year}','## Método',METHOD,
                 '## Titularidad y eventos observados',md_table(univ['titularidad']),
                 f'![Recepción](../../../reports/pensiones_exploratorio_v1/figuras/U_recepcion_{year}.png)',
                 f'![Ramas](../../../reports/pensiones_exploratorio_v1/figuras/U_titularidad_{year}.png)',
                 md_table(univ['eventos_observados_no_numero_declarado']),
                 f'![Eventos](../../../reports/pensiones_exploratorio_v1/figuras/U_eventos_{year}.png)',
                 'Los slots observados no acreditan el número completo declarado: 2012/2015 cambian la estructura de captura y las 33 firmas candidatas se conservan. No se corrigen ni se eliminan por igualdad de montos.']
        for name,data in univ.items():
            if isinstance(data,list) and data and isinstance(data[0],dict):content+=['## '+name.replace('_',' '),md_table(data)]
        if year>=2018:
            couple=next(x for x in r['universos_conyuge'] if x['ano']==year)
            content += ['## Universo específico de pareja',md_table(couple.get('recepcion_conyuge_en_parejas_por_sexo',[])),f'![Universo pareja](../../../reports/pensiones_exploratorio_v1/figuras/U_conyuge_elegible_{year}.png)',f'N elegible pareja confirmado={couple["N_elegible_pareja_confirmado"]:,}; sin rama pareja residente={couple["N_sin_pareja_residente_explicita"]:,}. No confundir con prevalencia en toda la muestra.']
        for concept,prose in univ.get('interpretaciones',{}).items():content += ['## Interpretación de '+concept,prose]
        for var, data in univ['controles'].items():
            content+=['## '+var,md_table(data),f'![{var}](../../../{univ["figuras_controles"][var]})']
            rows.append({'Solicitud original':f'Univariado {var} · {year}', 'Análisis realizado':'Distribución 60+ con universo del indicador',
              'Tabla generada':f'docs/eda/pensiones_exploratorio_v1/tablas/U_{year}.json',
              'Gráfica generada':univ['figuras_controles'][var], 'Interpretación':f'docs/eda/pensiones_exploratorio_v1/UNIVARIADO_{year}.md',
              'Archivo y ubicación':'notebooks/06a_mapa_y_univariado.ipynb','Estado':'Completo provisional'})
        content += [f'![Tipos](../../../reports/pensiones_exploratorio_v1/figuras/U_tipos_{year}.png)',f'![Programas](../../../reports/pensiones_exploratorio_v1/figuras/U_programas_{year}.png)']
        write_project_text(PUBLIC/f'UNIVARIADO_{year}.md', '\n\n'.join(content)+'\n')
        for req,fig,status in [
          ('Ramas propia/cónyuge y recepción','U_titularidad','Completo provisional'),
          ('Recepción individual propia/cónyuge K y A con ND','U_recepcion','Completo provisional'),
          ('Instituciones pensionarias','B6','Completo provisional'),
          ('Contingencias y beneficiarios de supervivencia','U_tipos','Completo provisional'),
          ('Programas y categorías observados','U_programas','Completo provisional'),
          ('Número de pensiones declaradas','U_eventos','Parcial'),
          ('Distribución de montos K por evento','U_montos_K','Completo provisional'),
          ('Distribución de montos A por evento','U_montos_A','Completo provisional')]:
            rows.append({'Solicitud original':f'{req} · {year}','Análisis realizado':'Univariado; slots observados no equivalen al número declarado' if status=='Parcial' else 'Univariado de fuentes orientadas',
             'Tabla generada':f'docs/eda/pensiones_exploratorio_v1/tablas/U_{year}.json',
             'Gráfica generada':f'reports/pensiones_exploratorio_v1/figuras/{fig}_{year}.png',
             'Interpretación':f'docs/eda/pensiones_exploratorio_v1/UNIVARIADO_{year}.md',
             'Archivo y ubicación':'notebooks/06a_mapa_y_univariado.ipynb','Estado':status})
    for key,x in r['seguimiento'].items():
        report += [f'## {key} · {x["solicitud"]}',x['interpretacion'],f'[Tabla](../../../{x["tabla"]}) · [Figura](../../../{x["figura"]}). **{x["estado"]}**.']
        rows.append({'Solicitud original':'Trayectorias '+x['solicitud'],'Análisis realizado':'Misma persona; origen × destino × perfil de origen',
          'Tabla generada':x['tabla'],'Gráfica generada':x['figura'],'Interpretación':'docs/eda/pensiones_exploratorio_v1/HALLAZGOS.md#'+key.lower(),
          'Archivo y ubicación':'notebooks/06d_trayectorias_pensiones.ipynb','Estado':x['estado']})
    report+=['## Correspondencias longitudinales',md_table(r['correspondencias']),
        '## Universo de rama cónyuge',md_table(r.get('universos_conyuge',[])),
        'Los universos tempranos no se reconstruyen por negativas operativas. La elegibilidad posterior se documenta separadamente de prevalencia general.',
        '## Flujo poblacional y continuidad',md_table(r.get('flujo_muestra',[])),md_table(r.get('rondas_por_persona_60',[])),
        'Primera aparición en el maestro no equivale a primera visita de 60+. Las reapariciones implican presencia anterior y ausencia en la ronda nominal previa; no son nuevas incorporaciones ni prueba de supervivencia.',
        '## Conclusiones exploratorias','La distribución pensionaria depende de rama, edad, escolaridad y condición de actividad. Los apoyos coexisten con K y también se registran en negativas explícitas K. Ninguna de esas coexistencias acredita duplicación del mismo pago o impacto redistributivo. La composición institucional múltiple, los contratos históricos y los ND impiden etiquetar todas las prestaciones como contributivas/no contributivas. Las preguntas siguientes son posibilidades de trabajo, sujetas a revisión documental y al estimando, no una tesis ya seleccionada.']
    write_project_text(PUBLIC/'HALLAZGOS.md', '\n\n'.join(report)+'\n');write_project_text(PUBLIC/'METODOLOGIA.md', '# Método del EDA pensionario v1\n\n'+METHOD)
    mapping=r['mapa'];existing=[{'Análisis':'CP1','Evidencia':'docs/CP1_INFORME_REVISION.md','Uso':'Universo completo; no recalcular'},
      {'Análisis':'B01','Evidencia':'docs/eda/B01_REVISION.md','Uso':'91 conceptos, descriptivos de todas edades; no confundir con submuestra 60+'},
      {'Análisis':'Integración','Evidencia':'docs/integracion/README.md','Uso':'17 fuentes; conservar base y claves'},
      {'Análisis':'Titularidad v1','Evidencia':'docs/integracion/titularidad/README.md','Uso':'Clasificación provisional existente; no repetir auditoría'},
      {'Análisis':'J02','Evidencia':'docs/eda/proteccion_economica/README.md','Uso':'Reutilizar tablas K/A, tasas sexo/escolaridad/localidad, contratos y eventos'},
      {'Análisis':'Catálogo nacional','Evidencia':'docs/pensiones/nacional/README.md','Uso':'Contexto documental; no beneficiarios ni vinculación individual'}]
    write_project_text(PUBLIC/'DIAGNOSTICO.md', '# Diagnóstico y organización conceptual\n\n'+md_table(existing)+'\n\n'+
       f'El diccionario completo conserva {mapping["N_columnas"]:,} columnas y {mapping["N_candidatos"]:,} claves de concepto **candidatas**, no conceptos armonizados comprobados. '
       f'{mapping["N_dimension_pendiente"]:,} columnas requieren validación semántica adicional. El mapa identifica todas las columnas sin descartarlas; agrupación léxica no basta para inferir equivalencia. '
       'Los campos de cobertura pueden referirse a tags de la fuente o valores almacenados por registros 60+ enlazados: se especifica el ámbito y no se llama válido a almacenado. '
       'Las ocho especificaciones anteriores permanecen intactas y pendientes cuando corresponde.\n\n'+md_table(mapping['resumen'])+'\n\n[Mapa de conceptos con contratos](mapa_conceptos.json). [Mapa completo por columna](mapa_columnas.json). [Armonizadas ya documentadas](../proteccion_economica/contratos_armonizacion.json).\n')
    pending='''# Pendientes y comparaciones no admisibles

- Mapa: organización por etiquetas/nombres es candidata para las columnas sin contrato; requiere revisión documental por pregunta, unidad, propietario y saltos. Se preserva todo el diccionario y los conceptos técnicos. No se afirma EDA semántico completo de 8,668 columnas.
- Número declarado: los instrumentos tienen contingencias/slots observables y estructuras distintas; todavía no hay contrato validado de una pregunta equivalente de número completo. No sustituir por conteo de slots ni por instituciones seleccionadas.
- Montos salariales: preguntas permiten mes/año; montos sin periodicidad orientada/homologada no se comparan. La recepción de salario principal sí se presenta con filtro positivo, separada del ingreso total, del patrimonio y de K. Montos, negocios, renta y transferencias pendientes de homologación amplia; B8 parcial.
- Programas: dinero y especie no separables en A; no es posible obtener sus tasas separadas. Hasta 2015 no existe programa nominal observado en el agregado. Ámbito de gobierno específico no inferible por edad o residencia. Catálogo no es recepción individual.
- Titularidad: 2001/J1 original ausente; orientación del proveedor provisional. Punteros discordantes permanecen ND. Las 33 firmas 2015 se conservan; igualdad de monto no demuestra duplicado.
- Institución: selección múltiple por contingencia 2012/2015 no permite repartir monto por slot. Códigos deben interpretarse según onda, no mediante una lista universal. Seguridad social no determina régimen, y otras instituciones mantienen tipo indeterminado.
- Transiciones: K2003–2012/K2015–2018 y A2001–2003/A2018–2021 no se interpretan como cambios homologados. Las figuras muestran correspondencia instrumental y cambio documental explícito. Rama cónyuge condicionada a orientación/filtros por ronda; no se corrigen punteros.
- Ponderación y diseño sin validación: tasas de muestra, sin inferencia nacional ni errores de muestreo de encuesta. Pruebas confirmatorias y ajuste por múltiples comparaciones no ejecutados; no hay afirmaciones de significancia.
- Precios/deflactor pendientes: montos nominales dentro de ronda, no crecimiento real ni suficiencia. Patrimonio compartido no es ingreso individual; no sumas por hogar ni entre versiones/eventos no validados.
- No se escoge pregunta definitiva, outcome, umbral patrimonial, hipótesis principal ni modelo. La alerta temprana queda como antecedente histórico posible. Normas UDLAP e índice final pendientes.
'''
    write_project_text(PUBLIC/'PENDIENTES.md', pending)
    for req,state,loc in [('Mapa conceptual completo y validación semántica','Parcial','DIAGNOSTICO.md'),
        ('Apoyos monetarios y en especie por separado','No viable con los datos actuales','PENDIENTES.md'),
        ('Conteo de pensiones declaradas equivalente entre rondas','Pendiente','PENDIENTES.md'),
        ('Montos salariales comparables, otros ingresos totales','Pendiente','PENDIENTES.md'),
        ('Estimaciones poblacionales con diseño y ponderadores','Pendiente','METODOLOGIA.md'),
        ('Tipos contributivos/no contributivos definitivos','Pendiente','PENDIENTES.md'),
        ('Catálogo documental nacional y comparabilidad histórica','Completo provisional','DIAGNOSTICO.md'),
        ('Mantener abiertas pregunta, hipótesis, outcome y modelo; conservar antecedente histórico','Completo y validado','PREGUNTAS_POTENCIALES.md')]:
        rows.append({'Solicitud original':req,'Análisis realizado':'Estado documentado; no suplir evidencia ausente',
          'Tabla generada':'mapa_columnas.json' if 'Mapa' in req else 'No aplica / pendiente',
          'Gráfica generada':'No aplica / pendiente','Interpretación':loc,'Archivo y ubicación':f'docs/eda/pensiones_exploratorio_v1/{loc}','Estado':state})
    rows.append({'Solicitud original':'Población 60+; modalidades, incorporaciones, entrada a60 y seguimiento',
      'Análisis realizado':'Flujo y panel no balanceado; personas y registros separados',
      'Tabla generada':'docs/eda/pensiones_exploratorio_v1/flujo_muestra.json',
      'Gráfica generada':'reports/pensiones_exploratorio_v1/figuras/U_modalidades_comparativa.png',
      'Interpretación':'docs/eda/pensiones_exploratorio_v1/HALLAZGOS.md',
      'Archivo y ubicación':'notebooks/06a_mapa_y_univariado.ipynb','Estado':'Completo provisional'})
    for var,x in r.get('comparativos_univariados',{}).items():
        rows.append({'Solicitud original':f'Comparativo entre rondas {var}, muestra 60+', 'Análisis realizado':'Composición transversal; no cambio individual ni monetario real',
          'Tabla generada':x['tabla'],'Gráfica generada':x['figura'],'Interpretación':x['interpretacion'],
          'Archivo y ubicación':'notebooks/06a_mapa_y_univariado.ipynb','Estado':x['estado']})
    for couple in r.get('universos_conyuge',[]):
        year=couple['ano']
        rows.append({'Solicitud original':f'N elegible rama cónyuge y tasa específica · {year}',
          'Análisis realizado':'Prevalencia general separada de universo pareja; temprano ND',
          'Tabla generada':'docs/eda/pensiones_exploratorio_v1/universos_conyuge.json',
          'Gráfica generada':f'reports/pensiones_exploratorio_v1/figuras/U_conyuge_elegible_{year}.png' if year>=2018 else 'Pendiente: no universo histórico validado',
          'Interpretación':'docs/eda/pensiones_exploratorio_v1/METODOLOGIA.md',
          'Archivo y ubicación':'notebooks/06a_mapa_y_univariado.ipynb','Estado':'Completo provisional' if year>=2018 else 'Pendiente'})
    for key,x in r.get('complementarios_salud',{}).items():
        rows.append({'Solicitud original':x['solicitud'],'Análisis realizado':'K propia × indicador de salud; rangos y perfiles por titularidad',
          'Tabla generada':x['tabla'],'Gráfica generada':x['figura'],'Interpretación':'docs/eda/pensiones_exploratorio_v1/SALUD_COMPLEMENTARIA.md',
          'Archivo y ubicación':'notebooks/06b_eda_bivariado_pensiones.ipynb','Estado':x['estado']})
    rows += [
      {'Solicitud original':'Informe de hallazgos concretos, débiles e inesperados','Análisis realizado':'Interpretación por solicitud, ronda y estrato',
       'Tabla generada':'docs/eda/pensiones_exploratorio_v1/resultados.json','Gráfica generada':'Figuras vinculadas por análisis, no se requiere figura adicional',
       'Interpretación':'docs/eda/pensiones_exploratorio_v1/HALLAZGOS.md','Archivo y ubicación':'docs/eda/pensiones_exploratorio_v1/HALLAZGOS.md','Estado':'Completo provisional'},
      {'Solicitud original':'Posibles preguntas derivadas de resultados y viabilidad','Análisis realizado':'Seis líneas abiertas con evidencia, variables, ondas y validaciones',
       'Tabla generada':'Resultados B/T/L citados en cada propuesta','Gráfica generada':'Figuras de los cruces que motivan cada pregunta; no figura independiente requerida',
       'Interpretación':'docs/eda/pensiones_exploratorio_v1/PREGUNTAS_POTENCIALES.md','Archivo y ubicación':'manuscrito/capitulos/05_discusion_conclusiones.tex','Estado':'Completo provisional'},
      {'Solicitud original':'Manuscrito LaTeX/PDF, cifras, cuadros, figuras, referencias y decisiones abiertas','Análisis realizado':'Secciones conectadas a main.tex, exportación desde agregados y compilación',
       'Tabla generada':'manuscrito/tablas/exploracion_*.tex','Gráfica generada':'manuscrito/figuras/borradores/exploracion_*.png',
       'Interpretación':'manuscrito/capitulos/04_analisis_exploratorio_resultados.tex','Archivo y ubicación':'manuscrito/build/main.pdf; validacion_tecnica.json registra QA','Estado':'Completo provisional'},
      {'Solicitud original':'Conservar CP1, maestro, auditoría y productos previos; no publicar identificadores ni hacer merge',
       'Análisis realizado':'Huellas SHA previas, unicidad, esquema de agregados y ejecución local',
       'Tabla generada':'docs/eda/pensiones_exploratorio_v1/validacion_tecnica.json','Gráfica generada':'No aplica: requisito de preservación y privacidad',
       'Interpretación':'docs/eda/pensiones_exploratorio_v1/README.md','Archivo y ubicación':'docs/eda/pensiones_exploratorio_v1/huellas_anteriores.json','Estado':'Completo y validado'}]
    write_json(PUBLIC/'matriz_cumplimiento.json',rows)
    write_project_text(PUBLIC/'MATRIZ_CUMPLIMIENTO.md', '# Correspondencia con los requerimientos originales\n\n'
      'Estados sustantivos, no aceptación por conteo de archivos. La revisión metodológica permanece abierta.\n\n'+md_table(rows)+'\n')
    write_json(PUBLIC/'validacion_tecnica.json',{'preservacion':len(checked_hashes()),'poblacion':r['poblacion'],
      'resultados_anonimos':True,'estado_academico':'Provisional / pendientes indicados en matriz','N_filas_matriz':len(rows)})
    write_project_text(PUBLIC/'README.md', '''# Exploración pensionaria longitudinal · v1

Etapa exploratoria autorizada el 12/10/2026: pensiones como eje, sin pregunta ni outcome definitivos. Conserva la pregunta anterior como antecedente. CP1, maestro integrado, titularidad y J02 se reutilizan y verifican por SHA.

Abrir desde VS Code:

- [Diagnóstico y mapa](DIAGNOSTICO.md), `mapa_columnas.json` para trazabilidad completa.
- [Método y denominadores](METODOLOGIA.md).
- [Hallazgos por análisis y ronda](HALLAZGOS.md); `analisis/B1_2021.md`, etc., contienen todas las tablas y figura correspondiente.
- [Matriz obligatoria](MATRIZ_CUMPLIMIENTO.md) y [pendientes](PENDIENTES.md).
- [Preguntas derivadas](PREGUNTAS_POTENCIALES.md).
- Notebooks 06a/06b/06c/06d en `notebooks/`; versiones ejecutadas privadas en `reports/notebooks/`.
- Manuscrito en `manuscrito/main.tex`; PDF local en `manuscrito/build/main.pdf`.

Reproducción (entorno Python >=3.11 con dependencias del proyecto):

```bash
python scripts/run_pension_exploration.py --check
python scripts/run_pension_exploration.py
python scripts/map_pension_concepts.py
python scripts/supplement_pension_univariates.py
python scripts/extend_pension_profiles.py
python scripts/complete_pension_joint_followup.py
python scripts/compare_pension_univariates.py
python scripts/pension_population_flow.py
python scripts/pension_spouse_denominators.py
python scripts/build_pension_exploration_reports.py --execute
python scripts/validate_pension_exploration.py
python scripts/export_pension_exploration.py
python -m pytest -q
python scripts/validate_notebooks.py
python scripts/validate_manuscript.py
python scripts/compile_manuscript.py --engine /tmp/tesis-tectonic-0.17.0/tectonic
```

La ejecución no invoca las 17 uniones ni la auditoría de titularidad. Los notebooks muestran agregados guardados por defecto. Recalcular es explícito; las fuentes privadas permanecen ignoradas. No se publican IDs ni filas individuales. No hay modelos, aprobación de clasificación final o merge. Figuras son borradores académicos y el formato institucional UDLAP está por confirmar.
''')


def notebooks(execute: bool = False) -> None:
    """Cuatro bloques; ejecución muestra únicamente agregados públicos."""
    r=json.loads(read_project_text(PUBLIC/'resultados.json'))
    configurations=[('06a_mapa_y_univariado','Mapa conceptual y univariado',[]),
      ('06b_eda_bivariado_pensiones','Ocho cruces bivariados',[k for k in r['analisis'] if k.startswith('B')]),
      ('06c_eda_trivariado_pensiones','Ocho cruces trivariados y complementarios',[k for k in r['analisis'] if k.startswith(('T','C'))]),
      ('06d_trayectorias_pensiones','Trayectorias por perfiles',[k for k in r['seguimiento']])]
    md,code=nbformat.v4.new_markdown_cell,nbformat.v4.new_code_cell
    for name,title,keys in configurations:
        nb=nbformat.v4.new_notebook();nb.metadata.kernelspec={'display_name':'Python (myenv)','language':'python','name':'myenv'}
        nb.cells=[md('# '+title+'\n\nObjetivo → método → resultados → interpretación. Etapa exploratoria sin pregunta/outcome definitivos. '+METHOD),
          code("from pathlib import Path\nimport json\nimport pandas as pd\nfrom IPython.display import display, Markdown, Image\n"
           "ROOT=next(p for p in [Path.cwd(),*Path.cwd().parents] if (p/'pyproject.toml').exists())\n"
           "PUBLIC=ROOT/'docs/eda/pensiones_exploratorio_v1'\nr=json.loads((PUBLIC/'resultados.json').read_text())\n"
           "from hashlib import sha256\nfor p,h in json.loads((PUBLIC/'huellas_anteriores.json').read_text()).items():\n"
           "    assert sha256((ROOT/p).read_bytes()).hexdigest()==h\n"
           "display(pd.DataFrame([r['poblacion']]))\ndisplay(pd.DataFrame(json.loads((PUBLIC/'matriz_cumplimiento.json').read_text())))")]
        if name.startswith('06b'):
            nb.cells += [md('## Salud complementaria\n\n'+read_project_text(PUBLIC/'SALUD_COMPLEMENTARIA.md')),code("display(pd.DataFrame(json.loads((PUBLIC/'salud_complementaria.json').read_text())))\nfor year in (2001,2003,2012,2015,2018,2021):\n    display(Image(filename=str(ROOT/f'reports/pensiones_exploratorio_v1/figuras/C_salud_{year}.png')))")]
        if name.startswith('06a'):
            nb.cells+=[md('## Inventario conceptual\n\nCada columna queda trazada; la agrupación candidata no valida semántica.'),
              code("display(pd.DataFrame(r['mapa']['resumen']))\nmapa=json.loads((PUBLIC/'mapa_columnas.json').read_text())\nassert len(mapa)==8668\ndisplay(pd.DataFrame(mapa))\ndisplay(pd.DataFrame(json.loads((PUBLIC/'mapa_conceptos.json').read_text())))\ndisplay(pd.DataFrame(r['flujo_muestra']))\ndisplay(pd.DataFrame(r['rondas_por_persona_60']))\ndisplay(Image(filename=str(ROOT/'reports/pensiones_exploratorio_v1/figuras/U_modalidades_comparativa.png')))")]
            for year in YEARS:
                nb.cells += [md(f'## Univariados {year}\n\nLos eventos no son necesariamente el número total declarado. Montos por evento nominal mensual; no sumar titulares.'),
                  code(f"u=r['univariados']['{year}']\nfor k,v in u.items():\n    if isinstance(v,list):\n        display(Markdown('### '+k)); display(pd.DataFrame(v))\n"
                       "for k,v in u['controles'].items():\n    display(Markdown('### '+k)); display(pd.DataFrame(v))\n"
                       "for name,prose in u.get('interpretaciones',{}).items():\n    display(Markdown('### Interpretación de '+name+'\\n\\n'+prose))\n"
                       "for var,figura in u.get('figuras_controles',{}).items():\n    display(Image(filename=str(ROOT/figura)))\n"
                       f"for f in ['U_recepcion_{year}','U_tipos_{year}','U_programas_{year}','U_titularidad_{year}','U_eventos_{year}','U_montos_K_{year}','U_montos_A_{year}']:\n    display(Image(filename=str(ROOT/f'reports/pensiones_exploratorio_v1/figuras/{{f}}.png')))\n")]
            nb.cells += [md('## Universo específico de pareja\n\nLa prevalencia de toda la muestra incluye No estructural cuando no hay rama cónyuge residente. El universo temprano queda ND.'),code("display(pd.DataFrame(r['universos_conyuge']))\nfor year in (2018,2021):\n    q=next(x for x in r['universos_conyuge'] if x['ano']==year)\n    display(pd.DataFrame(q['recepcion_conyuge_en_parejas_por_sexo']))\n    display(Image(filename=str(ROOT/f'reports/pensiones_exploratorio_v1/figuras/U_conyuge_elegible_{year}.png')))")]
            nb.cells += [md('## Comparativos de la muestra 60+ entre rondas'),code("for var,x in r.get('comparativos_univariados',{}).items():\n    display(Markdown('### '+var+'\\n\\n'+x['interpretacion']))\n    display(pd.DataFrame(json.loads((ROOT/x['tabla']).read_text())))\n    display(Image(filename=str(ROOT/x['figura'])))")]
        else:
            section='seguimiento' if name.startswith('06d') else 'analisis'
            if section=='seguimiento':nb.cells += [code("display(pd.DataFrame(r['correspondencias']))")]
            for key in keys:
                x=r[section][key]
                nb.cells += [md(f'## {key} · {x["solicitud"]}\n\n'+x['interpretacion']+'\n\n**Estado: '+x['estado']+'**'),
                 code(f"obj=json.loads((ROOT/'{x['tabla']}').read_text())\n"
                      "if isinstance(obj,list):\n    with pd.option_context('display.max_rows',None,'display.max_columns',None): display(pd.DataFrame(obj))\nelse:\n    for k,v in obj.items():\n        if isinstance(v,list) and v and isinstance(v[0],dict):\n            display(Markdown('### '+k))\n            with pd.option_context('display.max_rows',None,'display.max_columns',None): display(pd.DataFrame(v))\n"
                      f"display(Image(filename=str(ROOT/'{x['figura']}')))\n")]
        nb.cells += [md('## Conclusión y siguientes validaciones\n\n'+read_project_text(PUBLIC/'PENDIENTES.md'))]
        nbformat.write(nb,project_path('', 'notebooks', f'{name}.ipynb'))
        if execute:
            NotebookClient(nb,timeout=300,kernel_name='myenv',resources={'metadata':{'path':str(ROOT)}}).execute()
            nbformat.write(nb,project_path('', 'reports/notebooks', f'{name}_ejecutado.ipynb'))
        print(name,'ejecutado' if execute else 'generado',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');args=p.parse_args()
    build_reports();notebooks(args.execute)
