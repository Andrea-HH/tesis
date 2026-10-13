"""Mapa de conceptos con contratos existentes; no homologación por nombre parecido."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text
import json
from run_pension_exploration import ROOT,PUBLIC,YEARS,write_json,checked_hashes
from tesis_enasem.pension_ownership import wave_contract
from tesis_enasem.protection_eda import support_contract


def run() -> None:
    old=json.loads(read_project_text(project_path('', 'docs/eda/proteccion_economica/resultados.json')))
    simple={c['variable']:c for c in json.loads(read_project_text(project_path('', 'docs/eda/contratos_simple.json')))['contratos']}
    meta=json.loads(read_project_text(project_path('', 'docs/integracion/diccionario_columnas.json')));lookup={(m.get('fuente_id'),m.get('variable_original')):m for m in meta if m.get('producto')!='auxiliar_faltante'}
    concepts=[]
    for year in YEARS:
        k=wave_contract(year);a=support_contract(year)
        for variable,dim,title,fields,holder in [
            ('pension_propia_k','Pensiones','Recepción propia K',list(k.own_gates)+list(k.spouse_gates),'Sujeto identificado; depende de orientación y rama efectiva'),
            ('pension_conyuge_k','Pensiones','Recepción del cónyuge K',list(k.own_gates)+list(k.spouse_gates),'Otro integrante, con puntero/filtro confirmado'),
            ('apoyo_propio','Apoyos gubernamentales','Recepción propia de donativo público',[a.own_gate,a.spouse_gate],'Sujeto identificado, no hogar completo'),
            ('apoyo_conyuge','Apoyos gubernamentales','Recepción del cónyuge de donativo público',[a.own_gate,a.spouse_gate],'Otro integrante con orientación confirmada')]:
            source=[lookup[(k.household,f)] for f in fields if (k.household,f) in lookup]
            rate=next(z for z in old['recepcion'] if z['ano']==year and z['variable']==variable)
            concepts.append({'concepto':title,'dimension':dim,'variable_derivada':variable,'ano':year,
              'producto':'armonizada provisional en auxiliar; no sustituye originales','variables_fuente':[z['columna'] for z in source],
              'archivo_fuente':source[0].get('archivo') if source else None,'unidad':'Persona-ronda',
              'titularidad':holder,'universo':'60+ por visita, viva; rama orientada y control de pareja cuando corresponde. N elegible potencial distinto de N conocido.',
              'categorias':{'Sí':'Afirmativa admisible','No':'Negativa K/A o No operativo por ausencia explícita de rama cónyuge residente','Desconocido':'Respuesta/titular/fuente no comprobado'},
              'codigos_especiales':'8/9 en estas preguntas binarias y tags Stata; no regla para todas las variables',
              'cobertura':rate,'estado':'Provisional; 2001/J1 y otros pendientes no corregidos',
              'comparabilidad':'Consultar contratos_armonizacion.json y matriz longitudinal; no equivalencia entre programas',
              'fuente_contrato':'docs/eda/proteccion_economica/contratos_armonizacion.json'})
        for key,title,unit,status in [
            ('titularidad_grupo','Ramas propia/cónyuge conjuntas','Persona-ronda','Partición estricta de dos respuestas; provisional'),
            ('instituciones_codigos','Institución/fuente de prestación','Persona-institución; selección múltiple','Código por instrumento; contingencia no slot en2012/2015'),
            ('tipo','Contingencia pensionaria','Evento/beneficiario','Cuatro contingencias; no régimen contributivo'),
            ('monto_mensual_observado','Monto original por evento K','MXN nominal mensual por evento','Contrato previo, montos separados; no ingreso total ni crecimiento real'),
            ('numero_eventos_estado','Slots/eventos observados','Persona-ronda','No equivalente al número total declarado'),
            ('numero_pensiones_declaradas','Número total declarado de pensiones','Persona-ronda','Pendiente: no contrato equivalente en seis rondas'),
            ('programa','Programa/categoría A','Evento/beneficiario','Agregado sin programa hasta2015; lista2018/2021; no separar dinero/especie'),
            ('beneficiario_viudez','Beneficiario de prestación de supervivencia','Evento/beneficiario','Titular efectivo orientado; no generador original del derecho')]:
            concepts.append({'concepto':title,'dimension':'Apoyos gubernamentales' if key=='programa' else 'Pensiones',
             'variable_derivada':key,'ano':year,'producto':'Auxiliar armonizado provisional / evento original',
             'variables_fuente':'Nombres de preguntas/slots y valores originales en contratos y eventos auditados, sin IDs publicados',
             'archivo_fuente':lookup[(k.household,k.own_gates[0])].get('archivo'),'unidad':unit,
             'titularidad':'Beneficiario orientado; ramas de hogar no son ingreso personal sin orientación',
             'universo':'Receptor confirmado del bloque/evento correspondiente; número declarado pendiente',
             'categorias':'Consultar diccionario original por onda; preservadas, sin clasificación automática',
             'codigos_especiales':'Monto K: 888888/999999 en2001/2003, 8888888/9999999 desde2012; institución8/9 temprano,88/99 posterior, selección múltiple por pregunta',
             'cobertura':'tablas/U_'+str(year)+'.json y B6_'+str(year)+'.json',
             'estado':status,'comparabilidad':'Provisional / no comparable cuando cambia captura o listado; no repartir monto por institución'})
    for var in ['edad','sexo','est_conyugal','n_res','n_suj_hog','urbano','educacion','edu_gru','ocupacion','autoem','horas_trabajadas','imp_neto','salud_glob','diabetes','n_sint_depr','n_abvd','recuerdo1']:
        c=simple[var];m=lookup[('F20',var)]
        dim=('Patrimonio' if var=='imp_neto' else 'Educación' if var in ['educacion','edu_gru'] else 'Ocupación y actividad laboral' if var in ['ocupacion','autoem','horas_trabajadas'] else 'Salud, funcionalidad y cognición' if var in ['salud_glob','diabetes','n_sint_depr','n_abvd','recuerdo1'] else 'Demografía')
        concepts.append({'concepto':c['label'],'dimension':dim,'variable_derivada':var,'ano':'Cobertura por onda en B01 y univariados60+',
            'producto':'Construida ENASEMsimple','variables_fuente':[var], 'archivo_fuente':m['archivo'],
            'unidad':c['unit'],'titularidad':'Sujeto y pareja para imp_neto; hogar para composición; sujeto para los otros indicadores',
            'universo':c['eligibility'],'categorias':c['codes'],'codigos_especiales':c['numeric_nonresponse'],
            'cobertura':'B01 / U_'+str(YEARS[0])+'.json y siguientes; ámbitos separados','estado':'Contrato del indicador, saltos brutos según pendientes',
            'comparabilidad':c['temporal'],'referencia':c['reference'],'pagina_libro':c['page']})
    # Ingreso observado con su titular y elegibilidad: no suponer que importe es mensual.
    for y,f,own,spouse,po,ps in [(2001,'F12','k44','k50','k43','k49'),(2003,'F11','k47','k53','k46','k52b'),
        *[(y,f,f'k47_{y%100}',f'k53_{y%100}',f'k46_{y%100}',f'k52b_{y%100}') for y,f in [(2012,'F07'),(2015,'F08'),(2018,'F09'),(2021,'F10')]]]:
        concepts.append({'concepto':'Recepción de salario de trabajo principal','dimension':'Ingresos','variable_derivada':'salario_principal_estado',
            'ano':y,'producto':'Armonizada provisional por rama auditada; originales intactos',
            'variables_fuente':[f'{f}__{v}' for v in [own,spouse,po,ps]],'archivo_fuente':lookup[(f,own)]['archivo'],
            'unidad':'Persona-ronda elegible confirmada; recepción en año previo','titularidad':'Rama correspondiente al sujeto, sin heredar salario de pareja',
            'universo':'Titularidad_rama1/2 conocida y pregunta de trabajo principal asalariado=1; demás no elegibles/no confirmados, no cero',
            'categorias':{'1':'Sí','2':'No','8':'NR','9':'NS'},'codigos_especiales':'NR/NS y tags conservados como desconocidos',
            'cobertura':f'tablas/B8_{y}.json','estado':'Recepción provisional; homologación de monto mes/año pendiente',
            'comparabilidad':'No ingreso total. Solo recepción dentro de onda; validar periodos antes de comparar montos'})
    write_json(PUBLIC/'mapa_conceptos.json',concepts)
    print('Mapa de conceptos sustantivos con contratos y pendientes, separado de columnas candidatas.');checked_hashes()


if __name__=='__main__':run()
