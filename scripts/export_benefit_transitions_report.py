"""Selecciona08 en el único informe acumulativo, preservando todas las etapas."""

from __future__ import annotations

import argparse
import json
import re
from hashlib import sha256
from typing import Any

from validate_benefit_transitions import check
from tesis_enasem.benefit_transitions import NOTEBOOK, OUTPUT, QUESTION, save_json, verify_inputs, validate_precision
from tesis_enasem.benefit_transition_outputs import academic_spacing, adjusted, group, interpretations, precision_figure
from tesis_enasem.project_paths import INTERIM_DIR, PROJECT_ROOT, RESULTS_DIR


def fmt(v: Any) -> str:
    """N desconocido permanece explícito; no se sustituye con0."""
    if v is None:return 'No identificable'
    if isinstance(v,float):return f'{v:,.2f}'
    return str(v)


def export() -> None:
    """Genera solo la nueva contribución académica; no modifica bloques anteriores."""
    from tesis_enasem.release_guard import block_legacy_export
    block_legacy_export()
    check();r=json.loads((OUTPUT/'resultados.json').read_text());texts=interpretations(r)
    figs=json.loads((OUTPUT/'figuras.json').read_text());products=[]
    source=(f"**Fuente y procedencia:** ENASEM; [notebook 08](../notebooks/{NOTEBOOK}), bloques 1–16; "
        "[copia ejecutada](../data/interim/notebooks_ejecutados/08_TRANSICIONES_MONTOS_PENSIONARIOS_ejecutado.ipynb); "
        "[auditoría](../data/interim/transiciones_montos_pensionarios/auditoria.json) y "
        "[agregados 08](../data/interim/transiciones_montos_pensionarios/resultados.json). "
        "Integración, definiciones, precios y seguimiento reutilizados de 01–07; INPC oficial congelado.")
    def table(title: str,rows: list[dict],columns: list[tuple[str,str]],question: str,note: str) -> str:
        products.append(dict(tipo='tabla',titulo=title,notebook='notebooks/'+NOTEBOOK,
            bloque='Síntesis08',pregunta_aporte=question,
            fuente='data/interim/transiciones_montos_pensionarios/resultados.json',contribucion='benefit08'))
        def cell(z: dict,k: str) -> str:return fmt(z.get(k)).replace('|','/').replace('\n',' ')
        return f'**Cuadro 0. {title}**\n\n**Pregunta y aporte:** {question}\n\n| '+' | '.join(t for k,t in columns)+' |\n| '+' | '.join('---' for _ in columns)+' |\n'+'\n'.join('| '+' | '.join(cell(z,k) for k,t in columns)+' |' for z in rows)+f'\n\n**Nota:** {note}\n\n{source}\n\n'
    def figure(key: str) -> str:
        f=next(f for f in figs if f['clave']==key)
        products.append(dict(tipo='figura',titulo=f['titulo'],notebook='notebooks/'+NOTEBOOK,
            bloque='Síntesis08',pregunta_aporte=f['nota'],archivo='resultados/'+f['archivo'],
            sha256=f['sha256'],contribucion='benefit08'))
        return f"**Figura 0. {f['titulo']}**\n\n**Pregunta y aporte:** {f['nota']}\n\n![Figura 0: {f['titulo']}]({f['archivo']})\n\n**Nota:** {f['nota']}\n\n{source}\n\n"
    def period(z: dict) -> str:return f"{z['via']} {z['origen']}–{z['destino']}"
    body=f'''### 10.5 Transiciones, incorporación de receptores y poder adquisitivo

**Pregunta central conservada:** {QUESTION}

**Resultado integrado.** {texts['resumen']}

**Datos, universo y estado.** El análisis 08 se justificó después de la auditoría: nuevas comparaciones de montos por transición, integridad de captura, identidad contable de precios y composición común. Principal: personas registradas vivas, directas y 60+ al inicio; destino directo, sin panel balanceado. Se conservan estados no observados y edad final discordante. Solo dos ventanas monetarias nuevas, K 2012–2015 y A 2015–2018; las matrices de recepción cubren las seis combinaciones vía/intervalo condicionadamente comparables. Sin pesos nacionales, modelos causales, imputación, supervivencia ni identificación administrativa de prestaciones. Cálculos reproducidos desde cero y validados; comparabilidad operacional condicionada e inferencia nacional no acreditadas. No modifica 01–07, bases ni LaTeX.

**Viabilidad antes de analizar.** {texts['auditoria']} Slots y multiselección institucional no acreditan el número total real de beneficios. La periodicidad es mes normal en pesos, ya normalizada en la entrevista; no se divide de nuevo por dos. Variables: `pension_propia_k`, `apoyo_propio`, eventos originales con beneficiario orientado, entrevista real, INPC y características basales validadas.

'''
    rows=[]
    for z in r['auditoria']['intervalos']:
        rows.append(dict(periodo=period(z),basal=z['N_cohorte'],pares=z['N_pares_recepcion_conocida'],
            nuevos=z['N_nuevos'],continuos=z['N_continuos'],parcial=z['N_pares_parciales07'],
            integro=z['N_pares_todos_capturados'],unico=z['N_un_evento_ambas'],
            concepto=z['N_misma_contingencia_IMSS_ISSSTE'],conflicto=z['N_pares_vital_discordante_excluidos']))
    body+=table('Viabilidad longitudinal y selección de montos íntegros captados',rows,
        [('periodo','Vía e intervalo'),('basal','N basal directa60+'),('pares','N pares de recepción válida'),
         ('nuevos','N nuevos observados'),('continuos','N continuos'),('parcial','N pares parciales07'),
         ('integro','N pares íntegros08'),('unico','N un evento ambas'),('concepto','N misma contingencia IMSS/ISSSTE'),('conflicto','N conflicto vital separado')],
        'Determinar qué cambio personal puede construirse sin sumar importes faltantes o identificar un programa inexistente.',
        'Cohorte60+ directa al inicio; pares de recepción en destinos directos. Íntegro: todos los eventos captados tienen monto y fecha válida en ambas visitas. N de un evento es subconjunto del íntegro. Misma contingencia/institución solo K, sin probar identidad administrativa; A no tiene programa longitudinal identificado. 07 preservado: sus pares incluían parciales; 08 añade criterio vital. Las rupturas no se interpretan como transiciones válidas. Solo las dos ventanas centrales tienen nuevo análisis monetario detallado.')
    rows=[]
    for z in r['analisis']:
        t=next(t for t in r['transiciones'] if (t['origen'],t['destino'],t['via'])==(z['origen'],z['destino'],z['via']))
        for s in t['estados']:
            if not s['N'] and s['estado']=='Estado no clasificable':continue
            rows.append(dict(periodo=period(z),estado=s['estado'],N=s['N'],cohorte=s['pct_cohorte'],
                conocidos=s['pct_pares_conocidos'],den=f"Basal={t['N_cohorte']:,}; pares={t['N_pares_conocidos']:,}"))
    body+=table('Transiciones de recepción y destinos de seguimiento en las dos ventanas centrales',rows,
        [('periodo','Vía e intervalo'),('estado','Estado observado'),('N','N'),('cohorte','% cohorte basal'),
         ('conocidos','% pares conocidos'),('den','Denominadores')],
        'Separar incorporación y continuidad observadas de mortalidad, ausencia, modalidad y ND.',
        'Cada persona aparece una vez por intervalo. % pares conocidos solo para las cuatro transiciones; no se asigna un porcentaje de ese denominador a muertos o ausentes. El conflicto vital A es dato original discordante, no nueva muerte inferida. No→Sí no alta administrativa ni continuidad garantizada entre entrevistas. Se documentan las otras cuatro ventanas elegibles en notebook/agregados.')
    body+=figure('seguimiento')
    for z in r['analisis']:
        t=next(t for t in r['transiciones'] if (t['origen'],t['destino'],t['via'])==(z['origen'],z['destino'],z['via']))
        other=z['otra_via_previa']
        body+=f"**{period(z)}: denominadores y protección anterior.** El inicio observado es {t['inicio_entre_negativas_reobservadas_pct']:.2f}% entre negativas iniciales con estado conocido en destino, frente a {t['inicio_sobre_cohorte_negativa_pct']:.2f}% sobre todas las {t['N_basal_no']:,} negativas basales. El cese de declaración es {t['deja_entre_receptores_reobservados_pct']:.2f}% entre receptoras reobservadas con estado conocido; {t['deja_sobre_cohorte_receptora_pct']:.2f}% sobre las {t['N_basal_si']:,} receptoras iniciales. Los primeros porcentajes están condicionados a observación válida. De los {other['N_nuevos']:,} nuevos de esta vía, {other['N_otra_via_basal_si']:,} ya tenían la otra vía propia, {other['N_otra_via_basal_no']:,} la negaban y {other['N_otra_via_basal_ND']} son ND. Nuevo en una vía no es necesariamente primera protección ni prueba de un beneficio adicional neto.\n\n"
    body+='**Incorporación frente a continuidad.** '+texts['nuevos']+'\n\n'
    rows=[]
    for z in r['analisis']:
        for m in z['montos_grupos']:
            rows.append(dict(periodo=period(z),patron=m['patron']+' · '+('basal' if m['visita']=='a' else 'destino'),
                rec=m['N_receptores'],N=m['N_monto_real'],ND=m['N_sin_monto_integro'],
                nominal=m['nominal']['mediana'],real=m['real']['mediana'],
                qnom=f"{m['nominal']['q25']:,.0f} / {m['nominal']['q75']:,.0f}",
                qreal=f"{m['real']['q25']:,.2f} / {m['real']['q75']:,.2f}"))
    body+=table('Montos de nuevos, continuos y quienes dejan de declarar recepción',rows,
        [('periodo','Vía e intervalo'),('patron','Patrón y visita del monto'),('rec','N recepción'),
         ('N','N monto real íntegro'),('ND','N sin monto íntegro'),('nominal','Mediana nominal $/mes'),
         ('real','Mediana real $/mes'),('qnom','Q25/Q75 nominal $'),('qreal','Q25/Q75 real $')],
        'Comprobar si los nuevos observados tienen montos menores y distinguir ausencia declarada de dinero no medido.',
        'Moneda real: septiembre2026. Destino para nuevos/continuos; basal para Sí→No, cuyo monto posterior no se completa con cero. Continua recepción no exige importe basal para este contraste; cambios personales sí. A dinero/especie, no A5. N sin monto íntegro incluye importe faltante de cualquier evento captado; no total de ingreso. Fechas válidas cubren los importes de estos contrastes.')
    body+=figure('nuevos_continuos')
    body+=texts['mezcla']+'\n\n'+texts['composicion_transversal']+'\n\n'
    for z in r['analisis']:
        dest=z['composicion_destino'];parts=[]
        for x in dest['grupos']:
            if x['grupo'] not in ['No→Sí','Sí→Sí']:
                parts.append(f"{x['grupo']}: {x['N_receptores']:,} receptoras/{x['N_monto_integro']:,} importes íntegros")
        body+=f"**Composición transversal de destino {period(z)}:** {dest['N_receptores_transversal']:,} receptoras60+ directas incluyen, además de los pares nuevos/continuos, "+'; '.join(parts)+'. El universo final incluye entradas por edad y orígenes excluidos del basal directo. Edad final discordante se conserva en seguimiento y puede excluirse del transversal60+. Los registros vitales conflictivos se describen como evidencia observada, sin inferir vida real o pagos tras fallecimiento.\n\n'
    body+='**Mismas personas y tres estimandos.** '+texts['pares']+'\n\n'
    rows=[]
    for z in r['analisis']:
        candidates=[('Íntegro captado',z['pares'])]+[(x['criterio'],x) for x in z['sensibilidades'] if x['criterio'].startswith(('Un evento, misma','Un evento en'))]
        for label,p in candidates:
            rows.append(dict(periodo=period(z),criterio=label,N=p['N'],
                nominal=f"${p['nominal_inicial']['mediana']:,.0f} → ${p['nominal_final']['mediana']:,.0f}",
                real=f"${p['real_inicial']['mediana']:,.2f} → ${p['real_final']['mediana']:,.2f}",
                dmed=p['diferencia_medianas_real'],dindividual=p['cambio_individual_real']['mediana'],
                qindividual=f"{p['cambio_individual_real']['q25']:,.2f} / {p['cambio_individual_real']['q75']:,.2f}",
                bajas=100*p['N_real_baja']/p['N'],d12=p['cambio_real_12m']['mediana'],dy=p['cambio_real_ano_entrevista']['mediana']))
    body+=table('Cambios de montos en pares íntegros y sensibilidades de concepto',rows,
        [('periodo','Vía e intervalo'),('criterio','Restricción de captura'),('N','N pares'),('nominal','Medianas nominales $/mes'),
         ('real','Medianas reales $/mes'),('dmed','Diferencia de medianas reales $'),('dindividual','Mediana cambio individual real $'),
         ('qindividual','Q25/Q75 cambios reales $'),('bajas','% cambios reales negativos'),('d12','Mediana cambio real12m $'),('dy','Mediana cambio real año entrevista $')],
        'Distinguir desplazamiento de la distribución y cambio personal, con sensibilidad temporal visible.',
        'Mismos N dentro de cada fila. Concepto K: un evento por visita, misma contingencia y única institución IMSS/ISSSTE; no certifica que sea la misma prestación. A de un evento no identifica programa. No IC ni valoresp. No se interpretan medias dominadas por importes extremos. El original de A conflictivo cambia N1223→1224 en sensibilidad de registros, sin cambiar la mediana; no se supone cobro posterior a muerte.')
    body+=figure('cambios_personales')
    body+=texts['precios']+'\n\n'+texts['sensibilidad']+'\n\n'
    body+='**Perfiles y heterogeneidad.** '+texts['perfiles']+'\n\n'
    pairs=[('sexo_grupo','Hombre','Mujer'),('edad_06','70+','60–64'),('educacion_grupo','≥10 años','0 años'),
           ('localidad_grupo','≥100 mil habitantes','<100 mil habitantes'),('ocupacion_grupo','Trabaja','Labores del hogar'),
           ('conyugal_grupo','Viudo','Casado/unión')]
    rows=[]
    for z in r['analisis']:
        for dim,g1,g2 in pairs:
            item=dict(periodo=period(z),perfil=g1+' / '+g2)
            for pat,key in [('No→Sí','new'),('Sí→Sí','cont')]:
                m=[next(x for x in z['montos_por_perfil'] if (x['dimension'],x['grupo'],x['patron'])==(dim,g,pat)) for g in [g1,g2]]
                item['N_'+key]='/'.join(f"{x['real']['N']:,}" for x in m)
                item['nom_'+key]=' / '.join(f"{x['nominal']['mediana']:,.0f}" for x in m)
                item['real_'+key]=' / '.join(f"{x['real']['mediana']:,.0f}" for x in m)
                item['gap_'+key]=m[0]['real']['mediana']-m[1]['real']['mediana']
                item['ratio_'+key]=m[0]['real']['mediana']/m[1]['real']['mediana'] if m[1]['real']['mediana'] else None
            changes=[next(x for x in z['cambios_por_perfil'] if (x['dimension'],x['grupo'])==(dim,g)) for g in [g1,g2]]
            item['changes']=' / '.join(f"${x['cambio_individual_real']['mediana']:+,.2f} (N={x['N']:,})" for x in changes)
            rows.append(item)
    body+=table('Brechas monetarias dentro de nuevos y continuos por perfil basal',rows,
        [('periodo','Vía e intervalo'),('perfil','Grupo1 / grupo2'),('N_new','N nuevos g1/g2'),('nom_new','Medianas nominales nuevos $'),
         ('real_new','Medianas reales nuevos $'),('gap_new','Brecha real nuevos g1−g2 $'),('ratio_new','Razón nuevos g1/g2'),
         ('N_cont','N continuos g1/g2'),('nom_cont','Medianas nominales continuos $'),('real_cont','Medianas reales continuos $'),
         ('gap_cont','Brecha real continuos g1−g2 $'),('ratio_cont','Razón continuos g1/g2'),('changes','Mediana cambio personal real g1/g2')],
        'Reconocer dimensiones de desigualdad y cambios personales sin confundir sus denominadores.',
        'Cada dimensión es una partición diferente y sus N no se suman entre dimensiones. Medianas por perfil redondeadas a pesos enteros; brechas y razones calculadas con valores sin redondear. Montos de destino íntegros; cambios personales solo pares íntegros. Edad y demás perfiles basales, escolaridad inicial, localidad100mil. Brechas firmadas g1−g2 y razones: dirección no es tamaño absoluto. Comparaciones muestrales sin ajuste conjunto; A de ≥10años tiene N pequeños. Ambos tipos de unidad mensual; real septiembre2026. Los otros niveles y faltantes siguen en notebook/agregados.')
    body+='**Composición común y soporte.** '+texts['ajuste']+'\n\n'
    rows=[]
    for z in r['analisis']:
        for pat in ['No→Sí','Sí→Sí']:
            a=adjusted(z,pat);n=adjusted(z,pat,'nominal');local=adjusted(z,pat,local=True)
            rows.append(dict(periodo=period(z),patron=pat,N0=z['ajuste']['N_original'][pat],N=a['N'],
                pct=z['ajuste']['pct_en_soporte'][pat],observado=a['observado_en_soporte_CDF']['mediana'],
                nom=n['ajustado_CDF']['mediana'],real=a['ajustado_CDF']['mediana'],ESS=a['ESS_descriptivo'],
                Nloc=local['N'],real_loc=local['ajustado_CDF']['mediana']))
    body+=table('Distribuciones estandarizadas de nuevos y continuos en soporte común',rows,
        [('periodo','Vía e intervalo'),('patron','Grupo'),('N0','N original con monto'),('N','N soporte principal'),('pct','% retenido en soporte'),
         ('observado','Mediana real sin ajuste CDF $'),('nom','Mediana nominal ajustada $'),('real','Mediana real ajustada $'),
         ('ESS','ESS pesos descriptivos'),('Nloc','N soporte con localidad'),('real_loc','Mediana real ajuste con localidad $')],
        'Evaluar cuánto del contraste de montos persiste entre grupos con composición basal común.',
        'Sexo×edad3×escolaridad0–5/6+, y sensibilidad añadiendo localidad2. ≥20 por grupo/celda; cobertura≥70% y≥4celdas. Objetivo: mezcla conjunta de los dos grupos dentro de soporte. Cuantil inverso de CDF, distinto del promedio de dos valores centrales de la mediana empírica usual. Comparador sin ajuste mismo soporte/CDF. ESS no es ESS de encuesta o IPW. No ajuste causal ni corrección de pérdidas o muertes.')
    body+='**Sensibilidad actuarial.** '+texts['seleccion']+'\n\n'
    rows=[]
    for z in r['analisis']:
        for s in z['seleccion']:
            item=dict(periodo=period(z),basal=s['recepcion_basal'],N=s['N_basal'],
                reaparece=s['N_reaparece_vivo_despues'],fallece=s['N_registro_fallecido_despues'],overlap=s['N_ambos_registros_posteriores'])
            for label,key in [('Fallecido registrado','dead'),('Ausente; vital desconocido','absent'),
                              ('Sustituto vivo; fuera del principal','proxy')]:
                x=next((x for x in s['destinos'] if x['destino']==label),None)
                item[key]=f"{x['N']:,} ({x['pct_basal']:.2f}%)" if x else '0 (0%)'
            rows.append(item)
    body+=table('Seguimiento por recepción inicial y evidencia posterior de ausentes',rows,
        [('periodo','Vía e intervalo'),('basal','Recepción basal'),('N','N basal'),('dead','Fallecidos N (% basal)'),
         ('absent','Ausentes N (% basal)'),('proxy','Sustitutos N (% basal)'),('reaparece','Ausentes reaparecen vivos'),
         ('fallece','Ausentes registro posterior fallecido'),('overlap','Ambos registros posteriores')],
        'Delimitar selección antes de interpretar diferencias monetarias de sobrevivientes observados.',
        'Todas las directas60+ basales, incluso recepciónND. Fallecimiento registrado no mortalidad completa/tasa anual. Conteos posteriores solo entre ausentes de ese intervalo; vida y muerte posteriores pueden solaparse, no sumar ni asignar estado en la visita ausente. Recepción/montos posteriores de muertos no se imputan. No se estimó IPW, KM, Cox ni escenarios de prestaciones de fallecidos.')
    body+='**Política, indicador, resultado y limitación.** '+texts['politica']+'\n\n'
    body+='**Conclusión para la pregunta central.** '+texts['conclusion']+'\n\n'
    body+='**Siete respuestas de esta etapa.**\n\n'
    answers=[
        'La erosión por precios es verificable; la distribución nominal y la mezcla de receptores K también cambian. No se identifica una descomposición causal única de la caída transversal.',
        'Los nuevos K tienen montos centrales mucho menores que los continuos, incluso en composición común. En A las medianas coinciden; no extrapolar el mecanismo K a A.',
        'Entre las mismas personas, K muestra pequeños cambios heterogéneos y una mediana sensible a fechas; A conserva caída mediana bajo los criterios temporales examinados. No implica pérdida para cada persona.',
        'Las diferencias K por escolaridad y localidad son grandes; la composición por sexo y edad cambia y existen contrastes dentro de perfiles. A presenta medianas mucho más próximas, con heterogeneidad de colas y un contraste inverso entre basales60–64.',
        'Sí: recepción y monto entre receptores son estimandos distintos. Incorporar prestaciones pequeñas puede elevar cobertura sin igualar montos. Tampoco se demuestra primera protección cuando ya existía la otra vía.',
        'Los cambios son compatibles descriptivamente con elegibilidad e importes normativos. No identifican un efecto de PAM, la identidad de un programa A ni todo el recurso económico propio.',
        'La mortalidad y ausencia cambian a quién puede observarse; las sensibilidades de composición/modalidad mantienen la diferencia grande K y el contraste mediano nulo A. No recuperan montos desconocidos ni representan automáticamente la cohorte original.']
    body+='\n'.join(f'{i}. {s}' for i,s in enumerate(answers,1))+'\n\n'+source+'\n'
    body=academic_spacing(body)
    # Actualizar solo el bloque08, con defensa contra ediciones manuales.
    path=RESULTS_DIR/'INFORME_GENERAL.md';text=path.read_text()
    begin,end='<!-- BEGIN benefit08 -->','<!-- END benefit08 -->';ledger=OUTPUT/'informe_contribucion.json'
    if begin in text:
        a=text.index(begin);b=text.index(end,a)+len(end)
        assert sha256(text[a:b].encode()).hexdigest()==json.loads(ledger.read_text())['sha_bloque'],'Bloque08 editado manualmente'
        text=text[:a]+begin+'\n\n'+body+'\n'+end+text[b:]
    else:
        a=text.index('<a id="seccion-limites"></a>')
        text=text[:a].rstrip()+'\n\n'+begin+'\n\n'+body+'\n'+end+'\n\n'+text[a:]
    text=text.replace('actualizada con los notebooks 03–07.','actualizada con los notebooks 03–08.')
    tables,figures={},{};lines=text.splitlines()
    for i,line in enumerate(lines):
        m=re.match(r'\*\*Cuadro \d+\. (.*)\*\*$',line)
        if m:tables[m[1]]=len(tables)+1;lines[i]=f'**Cuadro {tables[m[1]]}. {m[1]}**'
        m=re.match(r'\*\*Figura \d+\. (.*)\*\*$',line)
        if m:figures[m[1]]=len(figures)+1;lines[i]=f'**Figura {figures[m[1]]}. {m[1]}**'
        m=re.match(r'!\[Figura \d+: (.*?)\]\((.*?)\)',line)
        if m:lines[i]=f'![Figura {figures[m[1]]}: {m[1]}]({m[2]})'
    text='\n'.join(lines)+'\n'
    baseline=json.loads((OUTPUT/'bloques_previos.json').read_text())
    for key,expected in baseline.items():
        start,finish=f'<!-- BEGIN {key} -->',f'<!-- END {key} -->'
        a=text.index(start);b=text.index(finish,a)+len(finish)
        assert sha256(text[a:b].encode()).hexdigest()==expected,'Cambió bloque anterior '+key
    path.write_text(text)
    a=text.index(begin);b=text.index(end,a)+len(end)
    save_json(ledger,dict(sha_bloque=sha256(text[a:b].encode()).hexdigest(),productos=products))
    p=INTERIM_DIR/'informe_general_seleccion.json';d=json.loads(p.read_text())
    d['productos']=[x for x in d['productos'] if x.get('contribucion')!='benefit08']+products
    for z in d['productos']:z['numero']=(tables if z['tipo']=='tabla' else figures)[z['titulo']]
    d['cuadros'],d['figuras']=len(tables),len(figures);save_json(p,d)
    p=INTERIM_DIR/'indice_informe.json';d=json.loads(p.read_text())
    matches=list(re.finditer(r'<a id="seccion-([a-z]+)"></a>',text))
    d['secciones_sintesis']={m[1]:dict(inicio=m.start(),fin=matches[i+1].start() if i+1<len(matches) else len(text)) for i,m in enumerate(matches)}
    d['sha_sintesis']=sha256(text.encode()).hexdigest();save_json(p,d)
    print('08 integrado:',len(products),'productos;',len(tables),'cuadros;',len(figures),'figuras;',len(baseline),'bloques previos intactos;',verify_inputs(),'archivos protegidos.')


def export_precision() -> None:
    """Añade el cierre de precisión y el diagnóstico editorial sin alterar06–08."""
    from tesis_enasem.release_guard import block_legacy_export
    block_legacy_export()
    check()
    result = json.loads((OUTPUT / 'precision.json').read_text())
    validate_precision(result)
    manifest = json.loads((OUTPUT / 'precision_manifest.json').read_text())
    assert sha256((OUTPUT / 'precision.json').read_bytes()).hexdigest() == manifest['sha_precision']
    for name, expected in manifest['codigo'].items():
        assert sha256((PROJECT_ROOT / name).read_bytes()).hexdigest() == expected, name
    k, a = result['ventanas']
    sex = result['sexo2012_2015']
    products: list[dict[str, Any]] = []
    source = ('**Fuente y procedencia:** agregados y definiciones de los notebooks 06–08, '
        'sin modificar sus archivos; [validación reproducible de precisión]'
        '(../data/interim/transiciones_montos_pensionarios/precision.json), '
        '[manifiesto, semillas y versiones]'
        '(../data/interim/transiciones_montos_pensionarios/precision_manifest.json). '
        'Ejecución: `python scripts/run_benefit_transitions.py --precision`; '
        '9,999 réplicas por escenario y agrupamiento. Moneda real: septiembre de 2026; '
        'INPC oficial de referencia 146.075, conservado de 07.')

    def estimate(block: dict[str, Any], key: str, folio: bool = False) -> dict[str, Any]:
        method = 'sensibilidad_folio' if folio else 'principal'
        return next(x for x in block[method]['estimaciones'] if x['id'] == key)

    def ci(block: dict[str, Any], key: str, folio: bool = False) -> str:
        z = estimate(block, key, folio)
        return f"{z['estimacion']:+,.2f} [{z['ic95'][0]:+,.2f}; {z['ic95'][1]:+,.2f}]"

    def bounds(z: dict[str, Any]) -> str:
        return f"[{z['inferior']:+,.2f}; {z['superior']:+,.2f}]"

    def table(title: str, rows: list[list[str]], columns: list[str],
              question: str, note: str, preface: str = '') -> str:
        products.append(dict(tipo='tabla', titulo=title, contribucion='precision08',
            fuente='data/interim/transiciones_montos_pensionarios/precision.json',
            pregunta_aporte=question, bloque='Validación final de precisión06–08',
            notebook='notebooks/' + NOTEBOOK))
        cells = ['| ' + ' | '.join(str(v).replace('|', '/') for v in row) + ' |' for row in rows]
        return (f'**Cuadro 0. {title}**\n\n**Pregunta y aporte:** {question}\n\n'
            + (preface + '\n\n' if preface else '') + '| '
            + ' | '.join(columns) + ' |\n| ' + ' | '.join('---' for _ in columns)
            + ' |\n' + '\n'.join(cells) + f'\n\n**Nota:** {note}\n\n{source}\n\n')

    body = f'''### 10.7 Validación final de precisión y preparación del manuscrito

**Pregunta central conservada:** {QUESTION}

**Diagnóstico al 14 de octubre de 2026.** Los contrastes priorizados permiten sostener una aportación empírica delimitada: en K 2012–2015, incorporar receptores con montos pequeños y observar a quienes continúan son comparaciones económicas diferentes; el contraste de nuevos frente a continuos es grande y persiste con composición basal común, pero cambia sustancialmente al restringir a evidencia IMSS/ISSSTE. En A 2015–2018, las medianas de nuevos y continuos coinciden y no reproducen ese patrón K. Entre continuos A hay una pequeña caída real mediana estable frente a los criterios temporales examinados. La pequeña caída individual K es mucho menos robusta. Por sexo, la reducción de la brecha de cobertura de unión K/A tiene precisión condicional; el aumento puntual de la brecha monetaria K no queda establecido con la misma claridad. La contribución es una comparación descriptiva de estimandos, periodos y poblaciones, no una explicación causal de la caída transversal ni un descubrimiento de que cobertura e ingreso son conceptos distintos.

Esta sección actualiza las reservas sobre precisión expresadas en 10.6. Conserva íntegros sus registros, los bloques anteriores y los ocho notebooks. Los IC que siguen son **incertidumbre bajo remuestreo de la muestra observada**, condicionada a definiciones, seguimiento y mediciones. No son inferencia representativa de México ni intervalos que incorporen todas las fuentes de error. No se inicia otra investigación ni se implementan modelos de supervivencia, predicción o efectos de programas.

#### A. Estimandos, procedimientos y alcance de la incertidumbre

**Poblaciones diferentes.** Incorporación: directas, registradas vivas y 60+ al inicio, reobservadas directamente con recepción conocida; el monto comparado es el de destino. No→Sí es inicio *observado* de declaración, no alta administrativa. Sí→Sí es continuidad entre dos respuestas, sin acreditar pagos ininterrumpidos o la misma prestación. Cambios personales: subconjunto Sí→Sí con todos los eventos captados monetariamente válidos en ambas visitas. Brechas por sexo: cortes dinámicos de directas 60+ en cada ronda, con K o unión K/A conocida para cobertura y con monto válido entre receptores K para dinero. No se exige panel balanceado, ni se suman sus denominadores.

**Bootstrap no paramétrico por persona.** Se muestrean IDs completos con reemplazo y se mantiene la misma multiplicidad en sus dos visitas y en cada subgrupo solapado. Así, un cambio individual usa sus dos montos juntos; el cambio de brecha entre cortes conserva la dependencia de personas repetidas; y la diferencia entre K total y su subgrupo IMSS/ISSSTE conserva la inclusión del segundo en el primero. Se utilizan 9,999 réplicas y percentiles 2.5/97.5, con semilla base 20261014 y semillas de cada escenario en el manifiesto. No se remuestrean celdas o visitas como si fueran personas independientes. El procedimiento retiene empates y no necesita una distribución normal de montos; tampoco usa la media o una prueba aislada como sustituto de la mediana. [Efron (1982)](https://epubs.siam.org/doi/book/10.1137/1.9781611970319) fundamenta el remuestreo; [Cameron y Miller (2015)](https://cameron.econ.ucdavis.edu/research/Cameron_Miller_JHR_2015.pdf) explican por qué debe respetarse la dependencia dentro del agrupamiento.

**Dos comprobaciones adicionales.** Primero, se repite el bootstrap por folio `cunicah`, manteniendo juntos sus integrantes y visitas. Es una sensibilidad a dependencia compartida de origen, no un diseño de encuesta: el folio no acredita hogar actual, UPM, estrato o probabilidades de inclusión. Segundo, las medianas crudas se contrastan con intervalos por estadísticos de orden, cuyos rangos se eligen con una binomial; para diferencias entre dos grupos disjuntos se combinan dos IC de mediana al 97.5% mediante Bonferroni, con cobertura al menos 95% bajo independencia entre personas. Esta comprobación no se aplica a la resta de contrastes solapados ni al ajuste de composición; para ellos se usa el remuestreo conjunto. Los empates pueden hacer conservadores los intervalos de orden. La convención del cuantil usual reproduce el promedio de valores centrales; el ajuste conserva el inverso de CDF de 08. [Documentación de cuantiles](https://search.r-project.org/R/refmans/stats/html/quantile.html) y [medianas por rangos binomiales](https://search.r-project.org/CRAN/refmans/rcompanion/html/quantileCI.html).

**Ajuste de composición y límites.** Se fija el soporte aprobado en 08 (sexo × edad basal de tres grupos × escolaridad 0–5/6+), y se reestima la mezcla objetivo conjunta en cada réplica. No se promedian medianas de celdas. El IC es condicional al soporte seleccionado, no incorpora incertidumbre de seleccionarlo. No es IPW de observación ni ajuste causal. Los IC son puntuales para los contrastes priorizados por la autora; no ofrecen cobertura simultánea de toda la colección auxiliar. No se introducen BCa, suavizado o ruido artificial para hacer desaparecer empates. Ningún IC incorpora incertidumbre por identidad de programa, error de declaración, omisión de eventos, fechas reales de pago desconocidas o selección no observada. La actualización INPC es poder adquisitivo, no valor presente actuarial.

#### B. Incorporación frente a continuidad: contraste principal e instituciones

'''
    rows = []
    for block, key, label in [
        (k, 'new_minus_cont', 'K 2012–15 · íntegro captado'),
        (k, 'adjusted_new_minus_cont', 'K · composición común CDF'),
        (k, 'ss_new_minus_cont', 'K · evidencia IMSS/ISSSTE'),
        (k, 'total_minus_ss_contrast', 'K · contraste total menos subgrupo'),
        (a, 'new_minus_cont', 'A 2015–18 · íntegro captado'),
        (a, 'adjusted_new_minus_cont', 'A · composición común CDF')]:
        if key == 'adjusted_new_minus_cont':
            ns = ' / '.join(f'{n:,}' for n in block['soporte_ajuste']['N_en_soporte'].values())
        elif key == 'total_minus_ss_contrast':
            ns = 'Mismos grupos solapados'
        else:
            point = estimate(block, key + '_real')
            ns = f"{point['N_grupo']:,} / {point['N_referencia']:,}"
        rows.append([label, ns, ci(block, key + '_nominal'),
                     ci(block, key + '_real'), ci(block, key + '_real', True)])
    body += table('Precisión de las diferencias de medianas entre nuevos y continuos', rows,
        ['Comparación', 'N nuevos / continuos', 'Diferencia nominal [IC95%] $/mes',
         'Diferencia real [IC95%] $/mes', 'Real [IC95%] por folio'],
        'Determinar si el contraste de incorporación es preciso, persiste a composición común y es uniforme institucionalmente.',
        'Signo: nuevos menos continuos. La cuarta fila resta esos contrastes, no una mediana de personas y su propio subgrupo. Monto personal completo de eventos captados; evidencia IMSS/ISSSTE no limita el dinero a esa institución si hay multiselección. No son regímenes excluyentes, causalidad institucional ni contributividad demostrada.')
    kn, kc = [k['principal']['distribuciones'][x + '_real'] for x in ['new', 'cont']]
    body += (f"**K: diferencia grande y estable dentro del universo observado.** Nuevos: mediana nominal $580.00 y real ${kn['mediana']:,.2f}; continuos: $2,500.00 y ${kc['mediana']:,.2f}. "
        f"La diferencia representa {100 * (kn['mediana'] / kc['mediana'] - 1):.2f}% del nivel mediano de continuos. "
        f"El contraste real crudo es {ci(k, 'new_minus_cont_real')}; el ajustado es {ci(k, 'adjusted_new_minus_cont_real')}. "
        'Las dos comprobaciones de agrupamiento mantienen la conclusión. La comprobación de orden/Bonferroni da '
        f"{bounds(estimate(k, 'new_minus_cont_real')['comprobacion_orden'])}; no depende de aproximar la densidad de la mediana. "
        'El contraste no desaparece al equilibrar las covariables basales observadas, pero eso no demuestra ausencia de confusión por trayectoria laboral, régimen, otras rentas o modalidad de acceso.\n\n')
    body += (f"**Instituciones: heterogeneidad sustantiva, mecanismo pendiente.** Con evidencia IMSS/ISSSTE, ambas medianas nominales son $2,500 y ambas reales ${kc['mediana']:,.2f}, con contraste {ci(k, 'ss_new_minus_cont_real')}. "
        'No se prueba equivalencia: el IC de orden, más conservador, admite una diferencia de '
        f"{bounds(estimate(k, 'ss_new_minus_cont_real')['comprobacion_orden'])}. "
        'La resta conjunta del contraste total y el del subgrupo permanece muy negativa, aun preservando su solapamiento. '
        'Los datos previos muestran código institucional 8 en 927/1,435 nuevos (64.60%) frente a 144/1,857 continuos (7.75%); '
        'es compatible con mezclas institucionales distintas. Ese código no identifica por sí solo un programa y puede coexistir con IMSS/ISSSTE. '
        'No distribuye el monto personal entre instituciones ni cuantifica qué fracción de la caída transversal explica cada componente. '
        'La restricción cambia la población; no estima un efecto de pertenecer al IMSS/ISSSTE.\n\n')
    body += (f"**A: la igualdad mediana es informativa pero acotada.** Ambas medianas nominales son $580 y reales $886.48; la diferencia es {ci(a, 'new_minus_cont_real')}. "
        'El intervalo estrecho describe estabilidad del centro registrado, no igualdad de distribuciones ni una prueba formal de equivalencia. '
        f"La diferencia Q75 real es {ci(a, 'new_minus_cont_real_q75')}; no establece una diferencia de la cola superior con precisión comparable. "
        'A incluye apoyo general en dinero/especie, sin identificar longitudinalmente el mismo programa ni garantizar que toda respuesta sea pensión no contributiva. '
        'Por ello no se replica automáticamente la interpretación de incorporación de K a A.\n\n')
    body += '**Faltantes y empates: lo que el IC no corrige.** '
    for z in [k, a]:
        pieces = []
        for x, prefix in zip(z['faltantes'], ['new', 'cont']):
            d = z['principal']['distribuciones'][prefix + '_nominal']
            pieces.append(f"{x['grupo']}: {x['N_monto_valido']:,}/{x['N_recepcion']:,} montos válidos, "
                f"{x['N_sin_monto']:,} faltantes ({100*x['N_sin_monto']/x['N_recepcion']:.2f}%); "
                f"{d['valores_distintos']} importes distintos y {d['N_igual_mediana']} exactamente en la mediana; "
                f"moda ${d['moda']:,.0f} ({d['pct_moda']:.2f}%)")
        body += f"{z['via']} {z['origen']}–{z['destino']}: " + '; '.join(pieces) + '. '
    body += ('Estos patrones justifican conservar la distribución discreta. Por ejemplo, el IC Q25 de A colapsa en cero y el Q25 de K en una diferencia fija; '
        'eso no equivale a ausencia de error monetario o certeza poblacional. No se eliminaron importes repetidos.\n\n')
    body += '**Cotas externas por dinero faltante, separadas de los IC.** '
    for z in [k, a]:
        n, c = [x['cotas_reales'] for x in z['faltantes']]
        body += (f"Si únicamente se admite que los importes no observados son no negativos y no se fija máximo, "
            f"el contraste mediano {z['via']} entre *todos los pares de recepción conocida* queda entre "
            f"${n['inferior']-c['superior']:+,.2f} y ${n['superior']-c['inferior']:+,.2f}. ")
    body += ('Son límites de rango extremo de las medianas de registros conocidos, sin rellenar ninguna celda individual. '
        'No son IC ni imputación, y no recuperan a muertos, ausentes, sustitutos o recepción ND. '
        'El gran contraste K no depende de asignar cero a quienes carecen de monto; la igualdad mediana A puede persistir por su concentración de importes.\n\n')
    body += (f"**Estabilidad del cálculo.** K conserva {k['soporte_ajuste']['N_en_soporte']['No→Sí']:,}/{k['soporte_ajuste']['N_original']['No→Sí']:,} nuevos y "
        f"{k['soporte_ajuste']['N_en_soporte']['Sí→Sí']:,}/{k['soporte_ajuste']['N_original']['Sí→Sí']:,} continuos en 12 celdas; "
        f"A conserva {a['soporte_ajuste']['N_en_soporte']['No→Sí']:,}/{a['soporte_ajuste']['N_original']['No→Sí']:,} y "
        f"{a['soporte_ajuste']['N_en_soporte']['Sí→Sí']:,}/{a['soporte_ajuste']['N_original']['Sí→Sí']:,} en 9 celdas. "
        'No hay réplicas con celdas vacías; el mínimo original de 20 se mantiene como regla del soporte, no se vuelve a seleccionar la muestra en cada réplica. '
        f"Alguna celda K baja de 20 en {k['principal']['ajuste_diagnostico']['pct_replicas_alguna_celda_menor20']:.4f}% de réplicas principales; en A, 0%. "
        'La división de las réplicas en dos mitades reproduce los límites centrales de incorporación; pequeñas variaciones de extremos en sensibilidades monetarias no cambian el diagnóstico. '
        'Los intervalos y las medias de indicadores no fallan por ausencia de grupo.\n\n')
    body += '#### C. Cambios personales: magnitud, fechas y población omitida\n\n'
    rows = []
    for z in [k, a]:
        for key, label in [('median_change_principal', 'Periodo principal'),
                           ('median_change_12m', 'Doce meses previos'),
                           ('median_change_ano_entrevista', 'Año de entrevista')]:
            x = estimate(z, key)
            rows.append([f"{z['via']} {z['origen']}–{z['destino']}", label,
                         f"{x['N_grupo']:,}", ci(z, key), ci(z, key, True)])
    rows.append(['K 2012–2015', 'Un evento, misma contingencia e IMSS/ISSSTE',
                 f"{estimate(k, 'median_change_stable_ss')['N_grupo']:,}",
                 ci(k, 'median_change_stable_ss'), ci(k, 'median_change_stable_ss', True)])
    body += table('Precisión de la mediana del cambio real individual entre continuos', rows,
        ['Vía e intervalo', 'Criterio', 'N personas/pares', 'Mediana Δ real [IC95%] $/mes',
         'Mediana Δ real [IC95%] por folio'],
        'Distinguir una pérdida personal del cambio de una mediana transversal y comprobar sensibilidad temporal.',
        'Δ = monto final real menos inicial real de la misma persona. Tres criterios de fecha de 07/08 sobre los mismos pares, no tres poblaciones. Periodo principal: promedio INPC del año calendario anterior al año real de entrevista, criterio explícito para «año pasado», no fecha de pago observada. La última fila restringe concepto y cambia el universo; no verifica identidad administrativa. Todos los IC son condicionales a dos montos captados íntegros.')
    body += (f"**K: precisión local no equivale a robustez sustantiva.** La mediana Δ principal es {ci(k, 'median_change_principal')}; "
        'es pequeña frente a los niveles y la dispersión individual: '
        f"Q25/Q75 del cambio son ${k['principal']['distribuciones']['change_principal']['q25']:+,.2f}/"
        f"${k['principal']['distribuciones']['change_principal']['q75']:+,.2f}. "
        'Aunque el IC principal no contiene cero, ambos criterios temporales alternativos lo incluyen y el puntual anual cambia de signo. '
        'No debe escribirse «los continuos K perdieron poder adquisitivo de forma robusta», ni asignarles el −11.05% transversal. '
        'La restricción de mismo concepto conserva signo negativo bajo el periodo principal, pero no resuelve la incertidumbre temporal general.\n\n')
    body += (f"**A: caída mediana pequeña pero más estable.** La mediana Δ principal es {ci(a, 'median_change_principal')}; "
        'los otros criterios temporales mantienen el signo negativo también en sus IC. '
        f"Q25/Q75 individual ${a['principal']['distribuciones']['change_principal']['q25']:+,.2f}/"
        f"${a['principal']['distribuciones']['change_principal']['q75']:+,.2f} muestran que hay personas con aumentos. "
        f"Cambios negativos: K {ci(k, 'negative_change_pct')}% y A {ci(a, 'negative_change_pct')}%, "
        'con denominadores 1,756 y 1,223, respectivamente. Son proporciones de pares monetarios, no proporciones de toda la cohorte, tasas anuales o pérdidas de bienestar total.\n\n')
    body += '**Faltantes de dos mediciones.** '
    for z in [k, a]:
        x = z['cotas_cambio_individual']
        body += (f"{z['via']}: {x['N_validos']:,}/{x['N_recepcion']:,} continuos con dos montos válidos; "
            f"{x['N_faltantes']:,} sin cambio calculable ({100*x['N_faltantes']/x['N_recepcion']:.2f}%). "
            f"Las cotas extremas de la mediana Δ entre todos los Sí→Sí conocidos son {bounds(x)} pesos reales. ")
    body += ('No se acota el cambio faltante ni se asignan importes; solo se pregunta dónde podría caer la mediana según rangos. '
        'K puede cruzar cero si la información omitida difiere suficientemente; A conserva mediana negativa bajo este ejercicio y el criterio temporal principal. '
        'No son intervalos conjuntos de muestreo y faltantes, ni resultados para la cohorte basal completa.\n\n')
    body += '#### D. Sexo: acceso y dinero responden preguntas diferentes\n\n'
    rows = []
    for label, keys, unit in [
        ('Cobertura K', ['gap_K_2012', 'gap_K_2015', 'change_gap_K'], 'pp'),
        ('Cobertura unión K/A', ['gap_KA_2012', 'gap_KA_2015', 'change_gap_KA'], 'pp'),
        ('Mediana K nominal', ['gap_money_partial_2012_nominal', 'gap_money_partial_2015_nominal', 'change_gap_money_partial_nominal'], '$/mes'),
        ('Mediana K real', ['gap_money_partial_2012_real', 'gap_money_partial_2015_real', 'change_gap_money_partial_real'], '$2026/mes')]:
        rows.append([label + ' · ' + unit, ci(sex, keys[0]), ci(sex, keys[1]),
                     ci(sex, keys[2]), ci(sex, keys[2], True)])
    body += table('Brechas por sexo en 2012–2015 y precisión de su cambio', rows,
        ['Indicador H−M', 'Brecha 2012 [IC95%]', 'Brecha 2015 [IC95%]',
         'Cambio de brecha [IC95%]', 'Cambio [IC95%] por folio'],
        'Evaluar por separado la evolución de acceso y del monto entre receptores.',
        'Cobertura: diferencia de tasas entre respuestas conocidas de cada corte. Dinero: diferencia de medianas entre receptores K con suma parcial válida de 07; sensibilidad íntegra08 conserva las mismas medianas y diagnóstico. Cambio = brecha2015 − brecha2012; remuestreo conjunto de IDs mantiene personas comunes a ambos cortes. No es una cohorte balanceada ni brecha monetaria de unión K/A.')
    body += '**Denominadores y datos no medidos.** '
    sd = sex['principal']['distribuciones']
    for year, eligible in [(2012, 8888), (2015, 9640)]:
        counts = []
        for via in ['K', 'KA']:
            counts.append(f"{via} conocidos H/M {sd[f'{via}_{year}_men']['N']:,}/{sd[f'{via}_{year}_women']['N']:,}")
        m = [x for x in sex['denominadores_monto'] if x['ronda'] == year and x['criterio'] == 'partial']
        body += (f"{year}: {eligible:,} directas60+; " + '; '.join(counts) + '; '
                 + ', '.join(f"montos {x['sexo']} {x['N_monto']:,}/{x['N_recepcion']:,} receptores, {x['N_sin_monto']} sin monto" for x in m) + '. ')
    body += (f"La unión de cortes usa {sex['principal']['N_personas']:,} IDs y {sex['principal']['N_filas']:,} personas-ronda; "
        'cada réplica retiene las dos visitas de quienes aparecen en ambas. Estados desconocidos no se convierten en negativa ni en monto cero.\n\n')
    body += (f"**Lectura que debe regir la redacción.** La brecha de cobertura de unión K/A disminuye {ci(sex, 'change_gap_KA')} pp; "
        f"la de K cambia {ci(sex, 'change_gap_K')} pp y no establece reducción o aumento uniforme. "
        f"La brecha monetaria K es positiva en ambos cortes, pero su cambio real {ci(sex, 'change_gap_money_partial_real')} "
        'incluye cero. El aumento de $504.19 a $684.73 es una descripción puntual de la muestra, no evidencia precisa de ensanchamiento en una población de referencia. '
        '**Corrección de alcance respecto de la síntesis H3/E08:** puede sostenerse «se reduce el contraste de cobertura de unión, sin demostrar cierre monetario»; '
        'no «demostramos que se amplió la brecha monetaria» ni «la expansión causó ese aumento». Los cuadros previos mantienen sus cifras; esta validación precisa su fuerza interpretativa.\n\n')
    fig = precision_figure(result)
    products.append(dict(tipo='figura', titulo=fig['titulo'], contribucion='precision08',
        archivo='resultados/' + fig['archivo'], sha256=fig['sha256'],
        fuente='data/interim/transiciones_montos_pensionarios/precision.json', pregunta_aporte=fig['nota']))
    body += (f"**Figura 0. {fig['titulo']}**\n\n**Pregunta y aporte:** {fig['nota']}\n\n"
        f"![Figura 0: {fig['titulo']}]({fig['archivo']})\n\n**Nota:** Panel a: cohortes de incorporación con montos de destino; "
        'panel b: continuos con dos montos; paneles c–d: cortes directos60+ de 2012 y 2015. '
        'Las escalas monetarias difieren entre paneles para que sean visibles las magnitudes. '
        'La cercanía de las dos barras comprueba sensibilidad al agrupamiento observado, sin validar un diseño nacional. '
        'A y el subgrupo IMSS/ISSSTE se examinan con más precisión numérica en los cuadros; no se concluye equivalencia.\n\n' + source + '\n\n')
    body += '#### E. Qué añade la comparación frente a los antecedentes más cercanos\n\n'
    literature = [
        ['DeGraff, Wong y Orozco-Rocha (2018)',
         'ENASEM2001–2012, 50+; cortes y panel; ingreso y activos, montos reales, fuentes y desigualdad; 12,405/13,946 en cortes y 7,305 longitudinales. Ya diferencia tendencias agregadas y envejecimiento de las mismas personas.',
         'No introducimos esa distinción. Añadimos dos ventanas posteriores y específicas: K2012–15 y A2015–18, nuevos/continuos, suma captada íntegra, incertidumbre y contraste institucional. No es una extensión directa de su ingreso total: aquí son prestaciones propias y universos distintos.'],
        ['Perez-Arce, Prados, Meijer y Lee (2021)',
         'ENASEM2001/2003/2012 y otras encuestas; cobertura e ingreso pensionario, desigualdad por sexo/escolaridad y trayectorias laborales; estimaciones ponderadas y modelos dinámicos. Una definición amplia de cobertura reduce gradientes educativos sin eliminar los de ingreso.',
         'La discordancia acceso/monto y el análisis dinámico no son nuevos. Nuestra adición es el contraste mediano de incorporados/continuos en las dos ventanas, su heterogeneidad K y el nulo mediano A; no atribuir causalidad, adoptar su clasificación contributiva para todo K ni reclamar alcance nacional comparable.'],
        ['García García (2025)',
         'ENASEM2018, 65+, pensión por jubilación; selección a recepción y descomposiciones de brechas de género, con historia laboral2001–2018. El estudio no establece la misma brecha significativa para montos que para cobertura.',
         'Nuestra muestra es60+ y K más amplio; estimamos diferencias de medianas y su cambio2012–15, en vez de una descomposición del logaritmo de la prestación. El IC del cambio monetario cruza cero: tampoco prueba un ensanchamiento. Selección a recibir pensión en Heckman no equivale a mortalidad o pérdida de seguimiento.']]
    body += table('Aportación delimitada frente a los tres antecedentes más próximos', literature,
        ['Antecedente', 'Lo que ya estaba estudiado', 'Qué se añade y qué no se reclama'],
        'Situar la contribución en la comparación concreta, evitando declarar novedosos conceptos o métodos establecidos.',
        'Comparación de estimandos y ventanas, no un metaanálisis. Se reutiliza la auditoría documental10.6; los textos de Perez-Arce y García García se cotejaron nuevamente. Las definiciones y ponderadores no son intercambiables con los de esta tesis.')
    body += ('Fuentes verificadas: [DeGraff et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC6150599/), '
        '[Perez-Arce et al., secciones3 y4.2, cuadros4.2.1–4.2.7]'
        '(https://mrdrc.isr.umich.edu/wp-content/uploads/2024/04/wp439.pdf), '
        '[García García, metodología y resultados]'
        '(https://repositorio.colmex.mx/downloads/p5547w027?locale=es). '
        'No se identificó en estos tres antecedentes el mismo contraste mediano nuevos/continuos para nuestras dos ventanas con la batería de precisión actual. '
        'Esto delimita una diferencia frente a los trabajos cotejados, no demuestra prioridad frente a toda la literatura existente.\n\n'
        '**Aportación defendible para Actuaría y Ciencia de Datos.** Una contribución empírica y de medición: preservar titularidad, eventos y desconocidos; '
        'distinguir incorporación de continuidad y niveles transversales de cambios personales; valorar importes en moneda homogénea; '
        'mantener dependencia longitudinal y exponer lo que cambian composición, instituciones, fechas y selección. '
        'La parte actuarial reside en delimitar quién sobrevive y permanece observable y en comparar recursos reales, con supuestos y límites explícitos. '
        'La precisión fortalece el contraste K y la caída A observada, pero no demuestra mecanismos de elección, monto normativo, elegibilidad administrativa, cotización previa o suficiencia de recursos totales. '
        'La investigación sostiene una tesis descriptiva con aportación específica; la originalidad debe presentarse como ampliación y contraste de evidencia previa, sin prometer una explicación general de veinte años.\n\n')
    body += '#### F. Conjunto reducido para la redacción definitiva\n\n'
    selected = [
        ['C1 · Acceso y exclusión', 'Cuadros39/48; figura44',
         'Cobertura propia K/A y negativas/ND de cada corte; ventana monetaria K2012–15 y A2015–18. En2021, 3,000 ambas negativas y58ND entre9,424 directas60+.',
         'Mantener rupturas de K/A visibles; tendencias por ventanas válidas. Sin CI de diseño, convergencia nacional o primeras altas inferidas.'],
        ['C2 · Monto y referencia económica', 'Cuadros46/48; misma figura44',
         'Nominal/real y denominadores de07; caída mediana K −11.05% en2012–15 y A −5.84% en2015–18, contraejemplo K +27.09% en2018–21. A5/2021 prestación/LPI mediana43.66%.',
         'Cuantías mensuales de receptoras; la línea per cápita es referencia de prestación parcial, no pobreza personal. A5/2021 no se traslada a A general longitudinal.'],
        ['C3 · Nuevos/continuos e instituciones', 'Primer cuadro de10.7 + cuadro56; figura46',
         'K bruto/ajustado/IMSS-ISSSTE y A, con N, IC y faltantes. Contraste K grande; subgrupo institucional y A incluyen cero.',
         'Solo K2012–15/A2015–18. No distribuye montos por institución, explica causalmente una caída o prueba equivalencia en los nulos.'],
        ['C4 · Cambios personales', 'Segundo cuadro de10.7, cuadro54; figura47',
         'Mismos1,756K/1,223A; IC por persona/folio, fechas y cotas por faltantes. K pequeño sensible; A negativo bajo criterios examinados.',
         'No representa toda la cohorte ni identifica continuidad administrativa. Fallecimiento no es un monto faltante imputable.'],
        ['C5 · Desigualdad por sexo', 'Tercer cuadro de10.7; nueva figura de precisión',
         'Unión: cambio−3.19pp con IC negativo; K monetario cambio+$180.54 con IC que contiene0. Mantener nulos junto a contrastes precisos.',
         'Cortes dinámicos2012–15. Sexo no sustituye ajuste por historia laboral y las dos brechas no comparten denominador.']]
    body += table('Propuesta de cinco cuadros y cuatro figuras para el núcleo de resultados', selected,
        ['Producto final propuesto', 'Procedencia actual', 'Conclusión que documenta', 'Límite que debe acompañarla'],
        'Preparar un argumento académico breve conservando nulos, contraejemplos y sensibilidad.',
        'Es una propuesta editorial, no nuevos archivos ni renumeración de los cuadros de LaTeX. Figuras propuestas44,46,47 y la nueva de precisión; las cuatro cumplen funciones diferentes. En la redacción se ensamblarán cinco cuadros desde agregados, sin reproducir las72 tablas acumulativas. Selección por pregunta y comparabilidad, no por valoresp.')
    body += ('**Selección actuarial, como complemento.** Los cuadros52/57 y figura45 documentan, en las cohortes basales K/A de8,888/9,640 personas, '
        '738/771 muertes registradas, 388/928 ausencias de estado vital desconocido y381/618 sustitutos; un conflicto vital A se conserva separado. '
        'Esto limita el alcance de los cambios observados y documenta diferencias por recepción inicial; no ofrece una corrección de sesgo. '
        'No se reponderó por observación, se estimó supervivencia ni se imputaron importes posteriores al fallecimiento. '
        'Puede ir en un cuadro complementario o anexo, sin convertirse en el eje de la pregunta central.\n\n')
    body += '#### G. Diagnóstico exacto del manuscrito: propuesta previa a editar\n\n'
    chapters = [
        ['1 · Introducción', '01_introduccion.tex',
         'L4 y16: orientación y ausencia de pregunta; L27: objetivos exploratorios; L44: vulnerabilidad como eje; L95/125: problema y justificación prospectivos; L155/172/195/221: pregunta, objetivos, hipótesis y aportaciones anteriores.',
         'Introducir la pregunta autorizada, protección propia/acceso/monto y ventanas válidas. Conservar contexto demográfico; separar como antecedente el contenido predictivo único sin convertirlo en diseño vigente. No afirmar que los datos confirman una hipótesis causal.'],
        ['2 · Marco teórico y antecedentes', '02_marco_teorico_antecedentes.tex',
         'L5–13: revisión anunciada de vulnerabilidad y predicción; L62: patrimonio/vulnerabilidad; L103/127/182/222: cronología y clasificación; L244/266/315: oferta pública y correspondencia ENASEM.',
         'Conservar L16/40, regímenes e instituciones válidos; distinguir K/A de contributiva/no contributiva, stock de flujo y prestación de ingreso total. Integrar críticamente los tres antecedentes y el aporte acotado; actualizar cronología07 sin inferir efecto de política.'],
        ['3 · Datos y metodología', '03_datos_metodologia.tex',
         'L19,350/354/357/371/375: predicción/estimando pendiente; L633–636 y749: deflactación/armonización aún pendientes; L840: homologación; L943/974: diseño prospectivo/resultado patrimonial; L1024: estrategia abierta.',
         'Reutilizar L32/65/95/145/197/229/260/385/465/524/676/711/759: IDs, rondas reales, entrevistas, faltantes y titularidad. Definir universos06–08, rupturas, moneda INPC, LPI y estimandos/CIs de10.7. Separar diseño predictivo histórico y no declarar resueltos problemas de medición por haber calculado precios.'],
        ['4 · Análisis exploratorio y resultados', '04_analisis_exploratorio_resultados.tex',
         'L5–8: pregunta ausente; L13/36/64/114/145: EDA amplio; L244/275: continuación y modelos pendientes; L473/495/525/539–625: resultados pensionarios aún preliminares, precios pendientes en621.',
         'Organizar por C1–C5, no por ocho notebooks: cobertura y exclusión; montos nominales/reales y referencia parcial; incorporación/continuidad e instituciones; cambios personales; sexo. Integración/titularidad de181/278/399 como respaldo; salud y patrimonio como contexto o anexo, conservando información única.'],
        ['5 · Discusión y conclusiones', '05_discusion_conclusiones.tex',
         'L4–14: borrador y predicción; L17/21: líneas posibles sin pregunta aprobada; L23/31/39/47/55/63: agenda dispersa; L67: precios pendientes.',
         'Responder la pregunta con magnitud e incertidumbre ya verificadas, comparar con antecedentes y reconocer nulos. Separar K y A, mostrar heterogeneidad y límites de observación; no generalizar convergencia, pérdida individual K, causalidad o suficiencia total. Las conclusiones finales requieren revisión editorial de la autora.']]
    chapter_rows = []
    diagnosis = []
    for chapter, name, locations, action in chapters:
        path = PROJECT_ROOT / 'manuscrito/capitulos' / name
        assert path.exists()
        chapter_rows.append([chapter, f'[{name}](../manuscrito/capitulos/{name})', locations, action])
        diagnosis.append(dict(capitulo=chapter, archivo=str(path.relative_to(PROJECT_ROOT)),
            ubicaciones=locations, propuesta=action, sha256=sha256(path.read_bytes()).hexdigest()))
    body += table('Asignación propuesta a los cinco capítulos y contenidos que requieren actualización', chapter_rows,
        ['Capítulo existente', 'Archivo único', 'Ubicación exacta en el archivo actual', 'Actualización propuesta y conservación'],
        'Identificar qué debe cambiar antes de redactar, sin modificar el manuscrito ni desechar contenido histórico único.',
        'L significa línea del archivo actual, verificada al14/10/2026; las huellas se conservan en la evidencia. Permanecen cinco capítulos y los anexos existentes; no se crean módulos por sección. También main.tex, líneas32–33, conserva en portada la afirmación de que no hay pregunta aprobada; deberá alinearse posteriormente. No se modifica ni compila en esta etapa, porque la autora solicitó primero el diagnóstico.',
        preface='La reorganización del argumento reutilizaría los cinco archivos existentes. Se distinguen las afirmaciones históricas que necesitan actualizarse del contenido metodológico y académico que debe conservarse.')
    body += ('**Secuencia de redacción propuesta.** Primero revisar este cierre de precisión, la corrección interpretativa de la brecha monetaria y el alcance de la originalidad. '
        'Después alinear pregunta y estimandos de capítulos1–3; exportar C1–C5 desde los mismos agregados al capítulo4; '
        'redactar capítulo5 con las conclusiones validadas y los resultados nulos. Finalmente compilar, cotejar citas/referencias y revisar el PDF del manuscrito. '
        'No hace falta otro notebook ni una nueva ronda exploratoria para sostener ese núcleo. Una inferencia nacional o un mecanismo causal requerirían otro diseño y validaciones que esta etapa no acredita.\n\n' + source + '\n')

    body = academic_spacing(body)
    path = RESULTS_DIR / 'INFORME_GENERAL.md'
    text = path.read_text()
    begin, end = '<!-- BEGIN precision08 -->', '<!-- END precision08 -->'
    ledger = OUTPUT / 'precision_informe.json'
    if begin in text:
        start = text.index(begin)
        finish = text.index(end, start) + len(end)
        assert sha256(text[start:finish].encode()).hexdigest() == json.loads(ledger.read_text())['sha_bloque']
        text = text[:start] + begin + '\n\n' + body + '\n' + end + text[finish:]
    else:
        start = text.index('<a id="seccion-limites"></a>')
        text = text[:start].rstrip() + '\n\n' + begin + '\n\n' + body + '\n' + end + '\n\n' + text[start:]
    tables, figures = {}, {}
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r'\*\*Cuadro \d+\. (.*)\*\*$', line)
        if m:
            assert m[1] not in tables
            tables[m[1]] = len(tables) + 1
            lines[i] = f'**Cuadro {tables[m[1]]}. {m[1]}**'
        m = re.match(r'\*\*Figura \d+\. (.*)\*\*$', line)
        if m:
            assert m[1] not in figures
            figures[m[1]] = len(figures) + 1
            lines[i] = f'**Figura {figures[m[1]]}. {m[1]}**'
        m = re.match(r'!\[Figura \d+: (.*?)\]\((.*?)\)', line)
        if m:
            lines[i] = f'![Figura {figures[m[1]]}: {m[1]}]({m[2]})'
    text = '\n'.join(lines) + '\n'
    previous_pending = ('cerrar homologaciones y precisión de los contrastes centrales; '
                        'ampliar evidencia de calidad o seguimiento solo si afecta el argumento.')
    current_pending = ('cerrar las homologaciones aún pendientes; ampliar evidencia de calidad o '
                       'seguimiento solo si afecta el argumento. La precisión condicional de los '
                       'contrastes priorizados quedó documentada en 10.7; no resuelve inferencia '
                       'nacional, errores de medición o selección no observada.')
    assert previous_pending in text or current_pending in text
    text = text.replace(previous_pending, current_pending)
    # Defensa de las catorce contribuciones ya autorizadas, incluida10.6.
    old = path.read_text()
    for match in re.finditer(r'<!-- BEGIN ([\w]+) -->', old):
        key = match[1]
        if key == 'precision08':
            continue
        finish = f'<!-- END {key} -->'
        previous = old[match.start():old.index(finish, match.start()) + len(finish)]
        start = text.index(match[0])
        current = text[start:text.index(finish, start) + len(finish)]
        assert previous == current, 'Se alteraría el bloque previo ' + key
    path.write_text(text)
    start = text.index(begin)
    finish = text.index(end, start) + len(end)
    save_json(ledger, dict(sha_bloque=sha256(text[start:finish].encode()).hexdigest(),
        sha_precision=manifest['sha_precision'], productos=products, diagnostico_manuscrito=diagnosis,
        seleccion_nucleo=selected, fuentes_metodologicas=['efron1982', 'cameronmiller2015'],
        comparacion_literatura=['degraff2018', 'perezarce2021', 'garciagarcia2025'],
        actualizacion_pendientes=dict(seccion='11.3', anterior=previous_pending, actual=current_pending)))
    p = INTERIM_DIR / 'informe_general_seleccion.json'
    data = json.loads(p.read_text())
    data['productos'] = [x for x in data['productos'] if x.get('contribucion') != 'precision08'] + products
    for item in data['productos']:
        item['numero'] = (tables if item['tipo'] == 'tabla' else figures)[item['titulo']]
    data['cuadros'], data['figuras'] = len(tables), len(figures)
    save_json(p, data)
    p = INTERIM_DIR / 'indice_informe.json'
    data = json.loads(p.read_text())
    matches = list(re.finditer(r'<a id="seccion-([a-z]+)"></a>', text))
    data['secciones_sintesis'] = {m[1]: dict(inicio=m.start(),
        fin=matches[i+1].start() if i+1 < len(matches) else len(text)) for i, m in enumerate(matches)}
    data['sha_sintesis'] = sha256(text.encode()).hexdigest()
    data['precision08'] = dict(archivo='data/interim/transiciones_montos_pensionarios/precision_informe.json',
                               sha_bloque=sha256(text[start:finish].encode()).hexdigest())
    save_json(p, data)
    print('Precisión integrada:', len(products), 'productos;', len(tables), 'cuadros;',
          len(figures), 'figuras; bloques anteriores y LaTeX intactos.')


if __name__=='__main__':
    from tesis_enasem.release_guard import block_legacy_export
    block_legacy_export()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--precision', action='store_true', help='Exportar solo la validación final de precisión.')
    args = parser.parse_args()
    export_precision() if args.precision else export()
