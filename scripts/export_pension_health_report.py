"""Incorpora solo la síntesis del notebook 03 al informe académico único."""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import json
import re

from tesis_enasem.pension_health import OUTPUT,verify_frozen_inputs
from tesis_enasem.pension_health_outputs import LABELS,conclusions
from tesis_enasem.project_paths import RESULTS_DIR,INTERIM_DIR


def build_contributions(r: dict, figures: list[dict]) -> dict[str,tuple[str,str]]:
    """Selecciona por dimensión, composición y límites; no por significancia."""
    products=[]
    source='**Fuente y procedencia:** ENASEM; [03_PENSIONES_SALUD_COGNICION](../notebooks/03_PENSIONES_SALUD_COGNICION.ipynb), '
    def link(block):return source+f'bloque {block}; [agregados completos](../data/interim/pensiones_salud/resultados.json).'
    def format_value(value):
        if value is None:return 'ND'
        if isinstance(value,float):return f'{value:.3f}'
        return str(value).replace('|','\\|')
    def table(title,rows,columns,question,note,block):
        products.append({'tipo':'tabla','titulo':title,'pregunta_aporte':question,'fuente':'data/interim/pensiones_salud/resultados.json','notebook':'notebooks/03_PENSIONES_SALUD_COGNICION.ipynb','bloque':block,'filas':len(rows),'columnas':[k for k,_ in columns]})
        return f'**Cuadro 0. {title}**\n\n**Objetivo y aporte:** {question}\n\n'+'| '+' | '.join(label for key,label in columns)+' |\n| '+' | '.join('---' for _ in columns)+' |\n'+'\n'.join('| '+' | '.join(format_value(x.get(key)) for key,label in columns)+' |' for x in rows)+f'\n\n**Nota:** {note}\n\n'+link(block)
    def image(key,question,interpretation,block):
        f=next(x for x in figures if x['clave']==key)
        products.append({'tipo':'figura','titulo':f['titulo'],'archivo':'resultados/'+f['archivo'],'pregunta_aporte':question,'notebook':'notebooks/03_PENSIONES_SALUD_COGNICION.ipynb','bloque':block,'sha256':sha256((RESULTS_DIR/f['archivo']).read_bytes()).hexdigest()})
        return f"**Figura 0. {f['titulo']}**\n\n**Objetivo y aporte:** {question}\n\n![Figura 0: {f['titulo']}]({f['archivo']})\n\n**Interpretación:** {interpretation}\n\n**Fuente y nota:** ENASEM; {f['nota'].replace(chr(10),' ')}\n\n"+link(block)
    selected=[]
    for dim in ['Física','Mental','Cognición','Funcionalidad']:
        names=[x['variable'] for x in r['contratos'] if x['dimension']==dim]
        for name in names:
            rows=[x for x in r['cobertura'] if x['variable']==name]
            year=next(x for x in rows if x['ano']==2021)
            spec=next(x for x in r['contratos'] if x['variable']==name)
            selected.append({'variable':name,'escala':LABELS[name],'rondas':', '.join(str(x['ano']) for x in rows if x['N_elegible']),
                'N_elegible':year['N_elegible'],'N_valido':year['N_valido'],'N_NR_NS':year['N_NR_NS'],
                'N_otros':year['N_otros_faltantes'],'imputado':'Sí, producto del proveedor' if spec['imputado'] else 'No declarado como imputado'})
    selected.append({'variable':'tics','escala':'Sin contrato/columna','rondas':'Pendiente','N_elegible':None,'N_valido':None,'N_NR_NS':None,'N_otros':None,'imputado':'No determinado'})
    coverage='### Ampliación de cobertura y elegibilidad: notebook 03\n\nLa ampliación mantiene 56,004 personas-ronda/18,754 personas de 60+ por visita. Las observaciones de una ronda son personas únicas dentro de ella; no se suman como personas únicas del periodo. No se usa el universo completo de J01/2021 para estos contrastes. La unidad y los dominios se toman de los contratos ENASEMsimple v2, con maestro v3 preservado. Son comparaciones descriptivas condicionadas al indicador, no homologación definitiva de ítems.\n\n'+table('Disponibilidad de indicadores y cobertura de salud, referencia 2021',selected,
       [('variable','Indicador'),('escala','Escala / unidad'),('rondas','Rondas disponibles'),('N_elegible','N elegible 2021'),('N_valido','N válido 2021'),('N_NR_NS','NR/NS'),('N_otros','Otros faltantes')],
       'Distinguir instrumentos disponibles, elegibilidad por modalidad y respuesta válida antes de contrastar pensiones.','N elegible corresponde al indicador construido, no a todos los saltos de cada pregunta bruta. NR/NS conserva .r/.d y códigos específicos; otros faltantes no son ceros. No hubo valores fuera del dominio documentado. N válido incluye representaciones imputadas del proveedor cuando corresponden. TICS no se construye sumando escalas.','2: disponibilidad y 1: contratos')
    coverage+='\n\n**Imputación y modalidades:** recuerdo1, recuerdo2, orientación y serial7 son puntuaciones imputadas del proveedor. bmi_imp es promedio de diez imputaciones, no diez observaciones independientes; sus IC no recuperan varianza entre imputaciones. Las escalas cognitivas 0–8, 0–3 y 0–5 no son intercambiables. Salud global, CES-D, soledad, cognición, AIVD y movilidad usan entrevistas directas según contrato; diabetes, enfermedades, BMI y ABVD admiten directa/sustituto. Las sensibilidades directas se conservan en el notebook. No se reclasifican tags ni extremos por presentación.'
    main=[]
    for x in r['principal']:
        if x['ano']!=2021:continue
        main.append({'variable':x['variable'],'N':f"{x['N_si_valido']:,}/{x['N_no_valido']:,}",
          'medianas':f"{x['si']['mediana']:.3f}/{x['no']['mediana']:.3f}",'medida':'pp' if x['variable'] in ['diabetes','cesd_deprimido','solo'] else 'Delta',
          'efecto':x['efecto'],'IC':f"[{x['ic95_inferior']:.3f}, {x['ic95_superior']:.3f}]",'ND_pension':x['N_recepcion_ND']})
    principal='### Pensiones y cuatro dimensiones: ampliación del notebook 03\n\n**Pregunta:** ¿cómo difieren las distribuciones de salud, cognición y funcionalidad entre afirmativa K propia y negativa explícita K propia? La negativa propia puede coexistir con pensión del cónyuge; ND no es ausencia. Para binarios se estima diferencia de proporciones (IC Newcombe/Wilson). Para ordinales, conteos y continuas asimétricas se estima delta de Cliff, P(valor con K mayor) − P(valor con K menor), con empates e IC bootstrap. No se recalculan las 30 correlaciones de Spearman previas: el nuevo contraste incorpora medidas adecuadas, elegibilidad, distribuciones y estratificación.\n\n**Estado:** ejecución y reconciliación técnica verificadas; interpretaciones descriptivas provisionales.\n\n**Alcance:** 80 contrastes principales, 186 contrastes trivariados estimables y 108 complementarios; no selección por p-valores. IC 95% puntuales, condicionales a valores representados y remuestreo iid dentro de grupo/ronda; no diseño de encuesta, dependencia del hogar o incertidumbre MI. No son IC simultáneos ni evidencias confirmatorias aisladas. No se estiman efectos si una rama tiene menos de 30 valores válidos.\n\n'+table('Contrastes de salud por recepción K propia, 2021',main,
       [('variable','Indicador'),('N','N válido K sí/no'),('medianas','Mediana K sí/no'),('medida','Unidad efecto'),('efecto','Sí − no'),('IC','IC 95%'),('ND_pension','K propia ND elegible')],
       'Comparar dirección, magnitud y forma de la distribución sin interpretar K como causa de la diferencia.','Delta va de −1 a 1; pp son puntos porcentuales del indicador binario, no puntos de su escala. Medianas pueden ser iguales con distribuciones distintas. Los desconocidos y salud no válida se reportan por separado; la cobertura del indicador está en el cuadro de disponibilidad.','3: comparación principal')
    explanations={
      'fisica':'Salud autopercibida presenta deltas negativos (1=excelente, 5=mala), pero diabetes diagnosticada y número de enfermedades presentan contrastes positivos pequeños. IMC más alto no se interpreta automáticamente como peor salud o suficiencia. En 2021, diabetes muestra +3.00 pp (IC 1.17–4.84), no una diferencia causal de incidencia; es diagnóstico alguna vez declarado.',
      'mental':'Síntomas CES-D, cinco o más síntomas y soledad presentan contrastes brutos negativos en las seis rondas. En 2021, medianas de síntomas son 2/3, con delta −0.103; cinco o más síntomas difieren −6.30 pp y soledad −5.81 pp. No son diagnósticos clínicos ni prueban un efecto protector. La estandarización posterior atenúa el contraste medio de síntomas.',
      'cognicion':'Aprendizaje verbal muestra un contraste global positivo pequeño, mínimo en 2015. Evocación cambia de signo en 2015. Orientación no se mide en 2001 y restas seriadas comienzan en 2015. Estas son puntuaciones imputadas en escalas distintas; los IC no incluyen la incertidumbre de sus imputaciones. La lectura global de aprendizaje cambia dentro de escolaridad.',
      'funcionalidad':'ABVD, AIVD y movilidad presentan diferencias pequeñas y algunos cambios de signo; las medianas ABVD/AIVD son cero en 2021 en ambas ramas. Conservar estos contrastes cercanos a cero impide concluir una mejor funcionalidad general asociada a K propia. Los IC no excluyen sistemáticamente efectos pequeños en uno u otro sentido.'}
    for key in ['fisica','mental','cognicion','funcionalidad']:
        principal+='\n\n'+image(key,'Comparar contrastes de la misma dimensión entre visitas sin sumar universos ni imponer una dirección favorable.',explanations[key],'3: tamaños de efecto')
    principal+='\n\n'+image('distribuciones_2021','Contrastar la forma de las distribuciones, incluidos ceros y asimetría, más allá de medianas.','Las distribuciones de enfermedades y síntomas no apuntan a una sola dirección de mejor salud; memoria y AIVD tienen escalas y coberturas propias. Las curvas se normalizan por sus N válidos; las filas ND no se agregan a cero.','4: distribuciones')
    others=[]
    for variable in ['n_enf','n_sint_depr','recuerdo2','n_aivd']:
        values=[x for x in r['principal'] if x['ano']==2021 and x['variable']==variable]
        values+=[x for x in r['complementarios'] if x['ano']==2021 and x['variable']==variable]
        for x in values:
            receipt=x.get('recepcion','pension_propia_k')
            others.append({'variable':variable,'rama':{'pension_propia_k':'K propia','apoyo_propio':'A propia','pension_conyuge_k':'K cónyuge confirmado'}[receipt],
             'N_elegible':x['N_elegible'],'N':f"{x['N_si_valido']:,}/{x['N_no_valido']:,}", 'delta':x['efecto'],'IC':f"[{x['ic95_inferior']:.3f}, {x['ic95_superior']:.3f}]"})
    complementary='### Otras ramas de recepción y titularidad: notebook 03\n\n'+table('Contrastes complementarios por rama de recepción, 2021',others,
       [('variable','Indicador'),('rama','Rama'),('N_elegible','N elegible'),('N','N válido sí/no'),('delta','Delta'),('IC','IC 95%')],
       'Distinguir K propia, cónyuge confirmado y A sin atribuirles el mismo universo ni la misma definición.','Cada fila contrasta afirmativa versus negativa de esa rama. Pueden coexistir; no se comparan grupos mutuamente excluyentes entre filas. Cónyuge exige pareja confirmada; su universo de salud puede restringirse a directas. A no es una pensión no contributiva homologada.','7: otras ramas')
    complementary+='\n\nEn 2021, síntomas con A propia presentan delta +0.089 y con cónyuge confirmado +0.002, frente a −0.103 con K propia. Evocación con A tiene delta −0.230 y con cónyuge +0.143; no son efectos alternativos del mismo tratamiento. El notebook conserva además distribuciones por ambas, solo propia, solo cónyuge, ambas negativas y desconocido; sin pareja residente queda separado. Antes de 2018 el universo de pareja no está confirmado: no se ejecuta su contraste complementario.'
    choices=[('n_sint_depr','sexo_grupo'),('salud_glob','edad_salud'),('recuerdo1','educacion_grupo'),('n_aivd','edad_salud'),('diabetes','sexo_grupo'),('recuerdo1','patrimonio_cuartil')]
    strata=[]
    for var,strat in choices:
        for x in r['trivariados']:
            if x['ano']==2021 and x['variable']==var and x['estratificador']==strat and x.get('efecto') is not None:
                strata.append({'variable':var,'estrato':x['estrato'],'N':f"{x['N_si_valido']:,}/{x['N_no_valido']:,}",'unidad':'pp' if var=='diabetes' else 'Delta','efecto':x['efecto'],'IC':f"[{x['ic95_inferior']:.3f}, {x['ic95_superior']:.3f}]"})
    trivariate='### Pensiones, salud y perfiles simultáneos: notebook 03\n\n'+table('Contrastes K propia × indicador × estrato seleccionados, 2021',strata,
       [('variable','Indicador'),('estrato','Tercera variable / estrato'),('N','N válido K sí/no'),('unidad','Unidad'),('efecto','Sí − no'),('IC','IC 95%')],
       'Examinar simultáneamente recepción, salud y un perfil sustantivo; priorizar los seis cruces solicitados, sin todas las combinaciones posibles.','Todos los estratos comparan K propia. IC puntuales y muestras no ponderadas. Q1–Q4 son cuartiles de patrimonio persona/cónyuge válidos dentro de ronda, no pobreza ni ingreso. No se probó interacción formal.','5: trivariados')
    trivariate+='\n\nEn diabetes, la diferencia es +7.40 pp entre hombres y +0.88 pp entre mujeres; síntomas tienen delta −0.102/−0.048 respectivamente. Salud global muestra contrastes −0.100/−0.110/−0.041 en edades 60–69/70–79/80+, mientras AIVD muestra −0.008/−0.056/−0.030. Son diferencias de patrones descriptivos; no pruebas confirmadas de que sexo o edad modifiquen un efecto causal. Los cruces de movilidad, evocación y localidad, junto con las seis rondas y celdas no estimables, permanecen completos en el notebook.'
    trivariate+='\n\n'+image('trivariado_3','Contrastar el patrón cognitivo dentro de escolaridad y patrimonio, en lugar de extrapolar el contraste marginal positivo.','Los cinco estratos conocidos de escolaridad muestran deltas negativos de aprendizaje en 2021, aunque el marginal es +0.091; los cuatro cuartiles patrimoniales muestran deltas positivos pequeños. No se ha controlado simultáneamente todo perfil ni comprobado interacción. Composición, agrupación, forma de distribución y ND condicionan estas diferencias.','5: cognición × escolaridad/patrimonio')
    adjusted=[x for x in r['estandarizados'] if x['ano']==2021]
    for x in adjusted:x['unidad_reporte']='pp' if x['variable']=='diabetes' else {'n_enf':'enfermedades','bmi_imp':'kg/m²','n_sint_depr':'síntomas','recuerdo1':'puntos 0–8','n_aivd':'limitaciones'}[x['variable']]
    adjustment='### Estandarización descriptiva de composición: notebook 03\n\n'+table('Contraste crudo y estandarizado en el mismo soporte, 2021',adjusted,
       [('variable','Indicador'),('N_soporte','N soporte'),('N_fuera_soporte','N fuera soporte'),('unidad_reporte','Unidad'),('diferencia_cruda_mismo_soporte','Cruda'),('diferencia_estandarizada','Estandarizada'),('ic95_inferior','IC inferior'),('ic95_superior','IC superior')],
       'Evaluar cuánto cambia la diferencia media/proporcional al usar una composición común de características observadas.','Target: pares válidos en celdas sexo×edad(60–69/70–79/80+)×escolaridad(0–5/6–9/10+)×modalidad con al menos 20 por rama. Pesos internos de composición, no pesos de encuesta. IC normal condicional a celdas, sin incertidumbre MI/diseño. No hubo regresión ni modelo predictivo.','6: estandarización')
    adjustment+='\n\nLa diferencia media de síntomas pasa de −0.434 a −0.071 en el mismo soporte (IC [−0.190, 0.048]); no conserva un contraste claro al considerar esta composición. La diferencia media de aprendizaje estandarizada es +0.107, mientras los deltas por escolaridad son negativos: no son la misma medida ni el mismo condicionamiento. Las bandas de escolaridad del ajuste agrupan niveles, los estratos se restringen a soporte común y las medias dependen de toda la distribución. No elegir la medida que respalde una conclusión; ambas se conservan con sus límites. La estandarización no elimina sesgo de selección, diferencias residuales o incertidumbre de imputación.'
    integrated='### Interpretación integrada de la ampliación de salud: notebook 03\n\n'+'\n\n'.join(conclusions(r))
    limitations='### Pendientes y límites específicos de pensiones y salud\n\nNo se calculó TICS por falta de columna y contrato, ni orientación/2001 o serial7 antes de 2015. No se inventan equivalencias entre pruebas, poblaciones ni puntuaciones. La bandera CES-D de cinco o más síntomas deriva del conteo: no es corroboración independiente ni diagnóstico. Se comprobaron {N_CESD:,} pares bandera/conteo sin discordancias. Los productos imputados se analizan como representaciones del proveedor; sus IC no son inferencia combinada de imputación múltiple. Los diagnósticos y síntomas declarados no son equivalentes a incidencia o diagnóstico clínico.\n\nLa selección de respuestas válidas y de soporte común puede cambiar composición; el bootstrap de personas y los IC de proporciones ignoran dependencia del hogar y diseño complejo. Los contrastes entre rondas no son pruebas de cambio en las mismas personas ni de alta/baja pensionaria homologada. Múltiples IC puntuales se interpretan como exploración conjunta, sin elegir hallazgos aislados porque excluyan cero. Se mantienen explícitos ND, fuera de universo y modalidad.\n\nEl notebook 03 conserva resultados exhaustivos y ocho figuras comparativas; el informe incorpora seis figuras y cinco cuadros seleccionados por cobertura, contradicciones, composición y alcance. Los resultados anteriores y los capítulos LaTeX permanecen intactos. El seguimiento conjunto de salud y pensiones queda como etapa posterior, no ejecutada aquí.'
    limitations=limitations.format(N_CESD=r['calidad']['CESD_pares_validos'])
    return {'salud_cobertura':('univariado',coverage),'salud_principal':('bivariado',principal),
            'salud_complementarios':('bivariado',complementary),'salud_trivariados':('trivariado',trivariate),
            'salud_ajuste':('trivariado',adjustment),'salud_integracion':('interpretacion',integrated),
            'salud_limites':('limites',limitations)},products


def export() -> None:
    """Actualiza bloques identificados, protege ediciones humanas y renumera presentación."""
    verify_frozen_inputs()
    report=RESULTS_DIR/'INFORME_GENERAL.md';text=report.read_text()
    text=text.replace('Síntesis editorial de resultados previamente calculados; sin nuevos análisis ni pregunta definitiva adoptada.', 'Síntesis académica acumulativa, actualizada con la ampliación del notebook 03; sin pregunta definitiva adoptada.')
    ledger_path=OUTPUT/'informe_contribucion.json'
    ledger=json.loads(ledger_path.read_text()) if ledger_path.exists() else {}
    r=json.loads((OUTPUT/'resultados.json').read_text());figures=json.loads((OUTPUT/'figuras.json').read_text())
    contributions,products=build_contributions(r,figures)
    for key,(section,body) in contributions.items():
        start=f'<!-- BEGIN {key} -->';end=f'<!-- END {key} -->'
        block=start+'\n\n'+body+'\n\n'+end
        if start in text:
            a=text.index(start);b=text.index(end,a)+len(end);old=text[a:b]
            if sha256(old.encode()).hexdigest()!=ledger.get('bloques',{}).get(key):raise ValueError(f'Bloque {key} editado manualmente: conservar')
            text=text[:a]+block+text[b:]
        else:
            anchor=f'<a id="seccion-{section}"></a>';a=text.index(anchor);next_section=text.find('<a id="seccion-',a+len(anchor));b=next_section if next_section>=0 else len(text)
            text=text[:b].rstrip()+'\n\n'+block+'\n\n'+text[b:]
    lines=text.splitlines();table_no=0;figure_no=0;section_no=0;sub_no=0;table_titles={};figure_titles={}
    for n,line in enumerate(lines):
        h=re.match(r'## (\d+)\. ',line)
        if h:section_no=int(h[1]);sub_no=0
        elif line.startswith('### '):
            sub_no+=1;title=re.sub(r'^\d+\.\d+\s+','',line[4:]);lines[n]=f'### {section_no}.{sub_no} {title}'
        t=re.match(r'\*\*Cuadro \d+\. (.*)\*\*$',line)
        if t:table_no+=1;lines[n]=f'**Cuadro {table_no}. {t[1]}**';table_titles[t[1]]=table_no
        f=re.match(r'\*\*Figura \d+\. (.*)\*\*$',line)
        if f:figure_no+=1;lines[n]=f'**Figura {figure_no}. {f[1]}**';figure_titles[f[1]]=figure_no
        image=re.match(r'!\[Figura \d+: (.*?)\]\((.*?)\)',line)
        if image:lines[n]=f'![Figura {figure_titles[image[1]]}: {image[1]}]({image[2]})'
    text='\n'.join(lines)+'\n';report.write_text(text)
    blocks={}
    for key in contributions:
        start=f'<!-- BEGIN {key} -->';end=f'<!-- END {key} -->';a=text.index(start);b=text.index(end,a)+len(end)
        blocks[key]=sha256(text[a:b].encode()).hexdigest()
    ledger_path.write_text(json.dumps({'bloques':blocks,'cuadros_informe':table_no,'figuras_informe':figure_no,'productos_seleccionados':products},ensure_ascii=False,indent=2)+'\n')
    selection_path=INTERIM_DIR/'informe_general_seleccion.json';selection=json.loads(selection_path.read_text())
    selection['productos']=[x for x in selection['productos'] if x.get('notebook')!='notebooks/03_PENSIONES_SALUD_COGNICION.ipynb']+products
    for x in selection['productos']:x['numero']=(table_titles if x['tipo']=='tabla' else figure_titles)[x['titulo']]
    selection['cuadros']=table_no;selection['figuras']=figure_no
    selection_path.write_text(json.dumps(selection,ensure_ascii=False,indent=2)+'\n')
    index_path=INTERIM_DIR/'indice_informe.json';index=json.loads(index_path.read_text());matches=list(re.finditer(r'<a id="seccion-([a-z]+)"></a>',text))
    index['secciones_sintesis']={m[1]:{'inicio':m.start(),'fin':matches[n+1].start() if n+1<len(matches) else len(text)} for n,m in enumerate(matches)}
    index['sha_sintesis']=sha256(text.encode()).hexdigest();index_path.write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n')
    verify_frozen_inputs();print('Informe actualizado por sección:',table_no,'cuadros y',figure_no,'figuras en total.')


if __name__=='__main__':export()
