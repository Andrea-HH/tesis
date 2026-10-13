"""Correspondencias documentales y síntesis académica sin recalcular ENASEM."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text
import json
from dataclasses import asdict
from pathlib import Path
import sys
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(project_path('', 'src')))
from tesis_enasem.program_catalog import STATES, normalized, academic_spacing
from tesis_enasem.pension_ownership import wave_contract
from tesis_enasem.manuscript import render_latex_table, latex_number, escape_latex
D=project_path('', 'docs/pensiones/nacional')

def save(name: str, obj: object) -> None:
    """Escribe agregados y metadatos, sin registros de personas."""
    write_project_text(project_path('docs/pensiones/nacional', name), json.dumps(obj,ensure_ascii=False,indent=2)+'\n')

def main() -> None:
    """Relaciona categorías de instrumentos, nunca asigna un programa a una persona."""
    index=json.loads(read_project_text(project_path('docs/pensiones/nacional', 'indice_catalogo.json')))
    contracts=json.loads(read_project_text(project_path('', 'docs/eda/proteccion_economica/contratos_armonizacion.json')))
    records=[r for s in index['fuentes'] for r in json.loads(read_project_text(project_path('', s['archivo_catalogo'])))]
    gates=[]
    for a in contracts:
        k=wave_contract(a['year'])
        gates.append({'ano':a['year'],'propia_k':list(k.own_gates),'conyuge_k':list(k.spouse_gates),
                      'apoyo_propio':a['own_gate'],'apoyo_conyuge':a['spouse_gate'],
                      'programas_propios':a['own_programs'],'programas_conyuge':a['spouse_programs'],
                      'opciones_programa':a['program_labels'],'periodo':a['periodo'],
                      'titularidad':'aplicar orientación existente; rama cónyuge puede pertenecer a persona de la fila',
                      'cobertura':'IMSS/ISSSTE identifican fuente institucional, no régimen. Instituciones/categorías públicas agrupadas no identifican programa específico.'})
    save('matriz_variables_rondas.json',gates)
    matches=[]
    for r in records:
        name=normalized(r['nombre_oficial']); explicit=[]
        if r['nivel_gobierno']=='federal':
            if 'proagro' in name:explicit.append({'ronda':2018,'codigo':1,'evidencia':'nombre explícito; validar componente y periodo'})
            if 'prospera' in name and 'imss' not in name:explicit.append({'ronda':2018,'codigo':2,'evidencia':'nombre explícito; no atribuye componente individual'})
            if 'produccion para el bienestar' in name:explicit.append({'ronda':2021,'codigo':1,'evidencia':'nombre explícito; antecedente PROAGRO no implica equivalencia'})
            if 'benito juarez' in name:explicit.append({'ronda':2021,'codigo':2,'evidencia':'familia de becas; no identifica nivel educativo ni estudiante'})
            if 'pension para el bienestar de las personas adultas mayores' in name:explicit.append({'ronda':2021,'codigo':5,'evidencia':'programa explícito; fecha de recepción y reglas todavía necesarias'})
        matches.append({'registro_documental':r['registro_documental'],'nivel':r['nivel_gobierno'],
                        'nombre':r['nombre_oficial'],'periodo_documental':r.get('periodo_documental') or r['anios_operacion_comprobados_inventario'],
                        'categoria_correspondencia':'programa_o_familia_nombrado' if explicit else 'sin_programa_especifico_identificable',
                        'rondas_pregunta_potencial':explicit,
                        'categoria_agregada':'K/apoyo público o donativo A según pregunta y tipo de beneficio; solo correspondencia potencial, nunca recepción inferida',
                        'limitacion':'La fila inventariada no prueba continuidad hasta la ronda, identidad de beneficiario, elegibilidad ni operación anual fuera del corte. Edad, residencia y monto no identifican un programa.'})
    save('matriz_programas_enasem.json',matches)
    old=json.loads(read_project_text(project_path('', 'docs/pensiones/catalogo_programas.json')))
    save('versiones_normativas_preexistentes.json',{'origen':'catálogo selectivo previo preservado íntegro','estado':'verificación previa según catálogo; no revalidación indiscriminada','programas':old['programas']})
    new=[]
    for c,date,age,eligibility in [('5608441','2020-12-22','0–29;30–64;30–67 según territorio','Discapacidad permanente; edad y territorios indígenas/afromexicanos o alta/muy alta marginación según §§3.2–3.3; documentación y padrón'),('5624455','2021-07-21','0–29;30 hasta antes de65 según territorio','Discapacidad permanente; adultos menores de65 en municipios/localidades mayoritariamente indígenas/afromexicanas o de alta/muy alta marginación; texto modificado')]:
        new.append({'id':'DISCAPACIDAD-2021-'+c,'nombre_oficial':'Programa Pensión para el Bienestar de las Personas con Discapacidad Permanente',
                    'nombres_historicos':[],'nivel':'federal','institucion':'Secretaría de Bienestar','territorio':'México; elegibilidad territorial diferenciada',
                    'inicio_documentado':2019,'fin':None,'operacion_comprobada':[2021],
                    'edad':age,'requisitos':eligibility,'beneficio':'pensión no contributiva por discapacidad; transferencia monetaria',
                    'monto_mensual_nominal_mxn':1350,'periodicidad':'entrega bimestral; pago de marcha separado, no otro ingreso periódico',
                    'documento_fecha_publicacion':date,'documento_firma':'2021-07-05' if c=='5624455' else '2020-12-14',
                    'vigencia':'2021-07-22' if c=='5624455' else '2021-01-01',
                    'url':'https://sidof.segob.gob.mx/notas/docFuente/'+c,'localizador':'§§3.2,3.3,3.5 y transitorios',
                    'estado':'texto oficial revisado; montos/edades de esta versión, sin completar otros años',
                    'correspondencia_enasem':'K invalidez no identifica automáticamente este programa; A no lo nombra. Mantener programa desconocido.',
                    'rondas_identificacion_individual':[]})
    save('versiones_normativas_nuevas.json',new)
    frames=[]
    for g in gates:
        labels='; '.join(f'{code}: {label}' for code,label in g['opciones_programa'].items()) or 'sin programa nombrado'
        frames.append({'Año':str(g['ano']),'Recepción A propia':g['apoyo_propio'],'Identificación de programa':labels})
    write_project_text(project_path('', 'manuscrito/tablas/catalogo_instrumentos.tex'), render_latex_table(pd.DataFrame(frames),
        'Especificidad del bloque de donativos públicos por ronda', 'tab:catalogo-instrumentos',
        'Fuente: contratos documentados de cuestionarios y libros ENASEM; no se recalculan respuestas. Propio refiere a la rama económica del beneficiario validada, no necesariamente al informante. Cónyuge, códigos, slots y montos se conservan en la matriz completa. Antes de2018 no se observa nombre de programa en este bloque. La categoría otro y las fuentes públicas K permanecen indeterminadas.',
        column_format='lp{3.3cm}p{8cm}'))
    n=index['por_nivel']
    write_project_text(project_path('', 'manuscrito/tablas/catalogo_cifras.tex'), '% Generado desde registros documentales oficiales; no beneficiarios.\n'+''.join(
        rf'\newcommand{{\cat{key}}}{{{latex_number(value)}}}'+'\n' for key,value in [('Federal',n['federal']),('Estatal',n['estatal']),('Municipal',n['municipal']),('Total',index['N_registros_documentales'])]))
    text='''# Catálogo nacional documental de protección económica y otras intervenciones públicas

## Alcance y unidad

Una fila representa una intervención en un ejercicio estatal/federal o en un periodo y municipio del inventario. No representa un programa histórico único, una pensión ni una persona receptora. Se preservan todos los registros de las hojas principales y se excluyen solamente títulos, blancos, notas y años fuera de 2001–2021. Las otras hojas de estado y los subconjuntos COVID no se suman otra vez. Las hojas de fuentes municipales se conservan localmente y no se cuentan como programas.

'''+f"Se extrajeron **{index['N_registros_documentales']:,} registros documentales**: {n['federal']:,} federales, {n['estatal']:,} estatales y {n['municipal']:,} municipales; {len(index['fuentes'])} libros/hojas principales, cero problemas de parseo al cierre. Los nombres originales y alias territoriales se preservan; Veracruz Ignacio de la Llave y Distrito Federal se normalizan explícitamente, sin excluirlos.\n\n"+'''
## Campos, verificación y límites

Los archivos `registros/*.json` contienen nombre oficial, institución, territorio original/normalizado, periodo, población categórica, beneficios reportados, enlaces normativos, hoja/fila, fuente y estado de verificación. Se conservan ND y no aplica como texto; los vacíos no se completan con cero. Las fechas de inicio reportadas por el inventario federal se distinguen de las validadas contra reglas. Edad exacta, terminación, monto individual y periodicidad quedan null cuando no hay cotejo normativo. El ejercicio inventariado demuestra presencia documental, sin probar operación completa, ejecución efectiva o continuidad entre cortes.

`versiones_normativas_preexistentes.json` conserva las versiones selectivas ya verificadas sin sobrescribirlas. `versiones_normativas_nuevas.json` añade dos reglas de discapacidad 2021: publicación inicial 22/12/2020, vigencia 01/01/2021; modificación firmada 05/07 pero publicada 21/07, vigencia 22/07. Ambas documentan 1350 pesos mensuales con entrega bimestral; no trasladar el aumento de 1550 de vejez a discapacidad. La elegibilidad territorial y edades cambian; ninguna limitación funcional observada asigna automáticamente el programa.

Se registran marcadores reproducibles de vejez, discapacidad, alimentación y asistencia para organizar la revisión. Son cribado léxico de nombre/población/apoyo, no prueba de elegibilidad, población efectivamente atendida ni validación de tipo contributivo. Se conserva también la oferta sin marcadores para impedir omisiones por criterio pensionario. Los montos del presupuesto institucional no son prestaciones individuales.

## Cobertura nacional y vacíos

Abrir `COBERTURA_DOCUMENTAL.md`: contiene 32 entidades × 8 cortes estatales y 32 × 5 cortes municipales, además de vacíos históricos. Los cortes estatales son 2010, 2011, 2012, 2013, 2014, 2016, 2018 y 2021. En 2010 la hoja nacional tiene 30 entidades con registros; Aguascalientes y Tlaxcala no tienen filas de programas en esa hoja; no se completan sus vacíos. Los inventarios municipales cubren 2012–2013, 2014–2015, 2015–2016, 2017 y 2020. Los rótulos multianuales no acreditan operación en ambos años. La oferta federal proviene del histórico 2004–2023, restringido a 2004–2021.

No se dispone de catálogo anual homogéneo 2001–2021 de todos los municipios/estados. Para 2001/2003 se preservan reglas seleccionadas; la falta del inventario no demuestra inexistencia. No se reemplaza 2015 por 2014/2016 ni 2021 por 2020. No se comparan conteos como una serie de expansión: cambian metodología, fuentes y disponibilidad. El catálogo no afirma exhaustividad total ni proporciones de cobertura poblacional.

## Programas estatales relacionados con vejez en 2021: índice de revisión

Los siguientes nombres provienen del campo oficial o categorías de población. Se muestran todos los marcados en 2021, sin convertir atención, asistencia o servicios en pensión monetaria. Los demás programas y cortes permanecen en el catálogo completo.

'''
    for state in STATES:
        selected=[r for r in records if r['nivel_gobierno']=='estatal' and r['territorio']==state and r['anios_operacion_comprobados_inventario']==[2021] and 'vejez' in r['marcadores_revision']]
        text+=f'### {state}\n\n'
        if selected:
            for r in selected:
                text+=f"- **{r['nombre_oficial']}**. Institución: {'; '.join(map(str,r['institucion_responsable']))}. Tipo/entrega reportados: {'; '.join(map(str,r['beneficio_reportado']))}. Localizador: `{r['fuente_id']}`, hoja `{r['hoja']}`, fila {r['fila_excel']}. Reglas, edad/monto exactos y continuidad: pendientes salvo versión normativa específica.\n"
        else:text+='Sin coincidencias del cribado explícito de vejez en este corte; no demuestra ausencia de oferta pertinente, receptores ni protección.\n'
        text+='\n'
    text+='''## Consulta reproducible

`python scripts/build_national_catalog.py` verifica las huellas y reconstruye las extracciones; `--download` recupera archivos faltantes según manifiesto y rechaza cambios de SHA. Dependencias: `pip install -e ".[documentacion,manuscrito,notebooks,dev]"`; RAR2016 requiere `tar` compatible con RAR o extracción verificada. `python scripts/export_national_context.py` genera correspondencias y síntesis desde agregados sin abrir ENASEM. Notebook05e conserva cobertura, búsqueda completa y explicación; no vuelve a integrar ni auditar titularidad. Todos los originales se guardan localmente en `data/raw/documentacion_catalogo/`, ignorado.
'''
    write_project_text(project_path('docs/pensiones/nacional', 'CATALOGO_NACIONAL.md'), academic_spacing(text))
    report='''# Programas documentados y límites de identificación individual en ENASEM

## Método y correspondencias

La matriz `matriz_variables_rondas.json` conserva las puertas de recepción K propia/cónyuge, A propia/cónyuge, campos de programa y códigos por ronda, recuperados de los contratos ya auditados. `matriz_programas_enasem.json` registra cada intervención documental y la pregunta potencial; no cruza estados ni datos individuales y no construye nuevas clasificaciones de recepción. Programa documentado, persona potencialmente elegible y recepción observada son tres unidades distintas.

| Especificidad | Identificable | Restricción |
|---|---|---|
| Programa o familia explícitamente nombrado | PROAGRO/PROSPERA 2018; Producción/Becas/vejez 2021 | Validar periodo, código y titular. Nombre de familia no identifica componente, estudiante ni expediente administrativo. |
| Fuente institucional | IMSS/ISSSTE y otras categorías K | No identifica régimen 1973/1997, cotizaciones ni carácter de una prestación pública ambigua. |
| Categoría agregada | Donativo público 2001–2015, otras instituciones 2018/2021 | No adjudicar programa federal, estatal o municipal particular. |
| Información insuficiente | Programa no nombrado, códigos desconocidos, orientación no validada | Mantener ND; no inferir por edad, residencia, monto o calendario. |

## Programas sin identificación suficiente

Los programas estatales y municipales catalogados no cuentan con código nominativo general en las fuentes analizadas. Las categorías de otra institución y el donativo público agregado pueden contener algunas transferencias, pero no prueban cuál ni si abarcan servicios en especie, subsidios de precios, infraestructura o derechos de hogar. La oferta social inventariada es más amplia que un donativo declarado. Por tanto, correspondencia potencial no equivale a captación efectiva de todos los programas.

La Pensión por Discapacidad no se atribuye desde K-invalidez ni limitaciones ADL/IADL. Las instituciones públicas agrupadas no validan contributividad. INAPAM es una institución y no acredita automáticamente transferencia monetaria. PROSPERA no es IMSS-PROSPERA; la familia de becas Benito Juárez no identifica un nivel educativo. Vejez2021 no se extiende retrospectivamente a cualquier apoyo 2001–2018. Los programas locales no se deducen de residencia: no se estiman coberturas estatales individuales con esta base.

La matriz conserva el año documental de cada intervención y las rondas potenciales de pregunta separadas. Una coincidencia de nombre en 2014 con opción de 2018 NO valida operación en 2018 de esa versión. Las series previas de programas se conservan sin convertir cambios de nombre en equivalencia de beneficios.

## Titularidad, solapamiento y doble conteo

Se aplican los auxiliares existentes de recepción propia y del cónyuge. Una persona puede ser beneficiaria de la rama cónyuge; el informante no determina la titularidad. Desconocidos y discrepancias permanecen ND. Para agregados de hogar se emplean eventos únicos por fuente-hogar-ronda-rama-tipo-slot; dos entrevistas de la pareja no crean dos pagos. Original, imputado y construido son versiones y no ingresos adicionales. Coincidencia de importe es una señal de revisión, no prueba de duplicación ni autorización de borrado. La coexistencia K+A no se suma como dinero distinto sin identificar prestaciones y periodos.

## Contexto compatible con el EDA, sin causalidad

Las reglas federales seleccionadas muestran cambios de edad, restricciones de pensión contributiva y alcance territorial; el instrumento 2021 también introduce una opción explícita de vejez. Estos hechos documentados ofrecen mecanismos plausibles para investigar la mayor recepción A y su coexistencia con K. No descomponen cuánto corresponde a política, cambio de medición, incorporación de participantes o composición del seguimiento. En 2021 hay 2019 receptores K+A entre 10482 observaciones 60+; eso no equivale a 2019 beneficiarios de dos programas federales identificados. El contraste institucional más específico identifica 1805 casos con evidencia IMSS/ISSSTE y programa de vejez, con los límites ya publicados.

Los contrastes por sexo, escolaridad, edad y corte de 100 mil describen la muestra sin ponderar. La diferencia de localidad no es estimación rural/urbana estricta. No se producen resultados estatales ni se comparan importes nominales como poder adquisitivo constante. Ponderación/diseño, fechas efectivas, precios, J1 de 2001, punteros discordantes, las33 firmas de 2015y homologaciones siguen abiertos. Este catálogo contextualiza los resultados existentes y no los recalcula ni modifica sus etiquetas.
'''
    write_project_text(project_path('docs/pensiones/nacional', 'IDENTIFICABILIDAD_ENASEM.md'), academic_spacing(report))
    lines=['# Matriz de programas, variables y rondas','',
           'Matriz completa por intervención en `matriz_programas_enasem.json`; contratos exactos de las seis rondas en `matriz_variables_rondas.json`. No asigna beneficiarios.','',
           '| Año | K propia | K cónyuge | A propia / cónyuge | Variables nominativas | Opciones documentadas |',
           '|---|---|---|---|---|---|']
    for g in gates:
        lines.append('| '+' | '.join([str(g['ano']),', '.join(g['propia_k']),', '.join(g['conyuge_k']),g['apoyo_propio']+' / '+g['apoyo_conyuge'],', '.join(g['programas_propios']+g['programas_conyuge']) or 'No disponibles','; '.join(f'{k}: {v}' for k,v in g['opciones_programa'].items()) or 'Agregado sin nombre'])+' |')
    write_project_text(project_path('docs/pensiones/nacional', 'MATRIZ_ENASEM.md'), academic_spacing('\n'.join(lines)+'\n'))
    print('Catálogo/contexto exportados',len(records),'registros; sin microdatos.')
if __name__=='__main__':main()
