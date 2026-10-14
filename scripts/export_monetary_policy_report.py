"""Contribución académica07 al único informe, conservando evidencia previa."""

import json
import re
from hashlib import sha256

from validate_monetary_policy import validate
from tesis_enasem.economic_protection_outputs import readable_prose
from tesis_enasem.monetary_policy import NOTEBOOK, OUTPUT, QUESTION, save_json, verify_inputs
from tesis_enasem.monetary_policy_outputs import amount, conclusions, readable
from tesis_enasem.project_paths import INTERIM_DIR, RESULTS_DIR


def export() -> None:
    """Selección editorial07: tablas/figuras, denominadores y lectura sustantiva."""
    validate()
    r=json.loads((OUTPUT/'resultados.json').read_text())
    a=json.loads((OUTPUT/'auditoria.json').read_text())
    figures=json.loads((OUTPUT/'figuras.json').read_text())
    products=[]
    source=f'**Fuente y procedencia:** ENASEM; [{NOTEBOOK.removesuffix(".ipynb")}](../notebooks/{NOTEBOOK}); [agregados07](../data/interim/politicas_montos_suficiencia/resultados.json); [contrato monetario](../diccionarios/contrato_monetario_politicas.json); [fuentes y cronología](../investigacion/notas/politicas_publicas_envejecimiento.md).'
    def fmt(v):
        return 'ND' if v is None else f'{v:,.2f}' if isinstance(v,float) else f'{v:,}' if isinstance(v,int) else str(v).replace('|','/').replace('\n',' ')
    def table(title,rows,cols,question,note,block):
        title=readable(title)
        products.append(dict(tipo='tabla',titulo=title,notebook='notebooks/'+NOTEBOOK,bloque=block,pregunta_aporte=question,fuente='data/interim/politicas_montos_suficiencia/resultados.json'))
        return f'**Cuadro 0. {title}**\n\n**Pregunta y aporte:** {question}\n\n| '+' | '.join(t for k,t in cols)+' |\n| '+' | '.join('---' for _ in cols)+' |\n'+'\n'.join('| '+' | '.join(str(z.get(k)) if k=='ronda' else fmt(z.get(k)) for k,t in cols)+' |' for z in rows)+f'\n\n**Nota:** {note}\n\n{source} Bloque {block}.\n\n'
    def image(key,question,reading,block):
        z=next(x for x in figures if x['clave']==key)
        products.append(dict(tipo='figura',titulo=z['titulo'],notebook='notebooks/'+NOTEBOOK,bloque=block,pregunta_aporte=question,
                             archivo='resultados/'+z['archivo'],sha256=sha256((RESULTS_DIR/z['archivo']).read_bytes()).hexdigest()))
        return f"**Figura 0. {z['titulo']}**\n\n**Pregunta y aporte:** {question}\n\n![Figura 0: {z['titulo']}]({z['archivo']})\n\n**Nota:** {z['nota']}\n\n{reading}\n\n{source} Bloque {block}.\n\n"
    body=f'''### 10.3 Políticas, poder adquisitivo y brechas de prestaciones parciales

**Pregunta central de la autora:** {QUESTION}

La hipótesis de acceso más igualado que monto o suficiencia se contrasta por vía, grupo y periodo. La mortalidad y la no observación funcionan como sensibilidad actuarial. La etapa07 completa las fuentes de precios y umbrales pendientes en06: los resultados nominales anteriores se conservan como evidencia de esa etapa.

**Población y estimandos.** Principal: personas vivas60+ por visita con entrevista directa, sin exigir panel balanceado. Se conservan respuestas válidas por sustituto en sensibilidad. Montos originales mensuales por evento y sumas parciales por persona, separadas entre K propia, A propia y cónyuge contextual. K no prueba contributividad; A incluye valoraciones de especie y distintos programas. No se suman K+A, originales+imputados, instituciones ni personas entre rondas. Las cifras describen muestra no ponderada; diseño y pesos no validados.

**Fecha y precios.** Se verificó y descargó la serie mensual oficial INEGI865541, base segunda quincena julio2018=100, actualización2024:321meses enero2000–septiembre2026. **Referencia común: septiembre2026, INPC146.075**, último mes mensual disponible al consultar14octubre2026, cotejado con el aviso INEGIpublicadoDOF9octubre. Fórmula: **monto constante = nominal ×146.075 / INPCdel periodo original**. [Serie oficial](https://www.inegi.org.mx/app/indicesdeprecios/Estructura.aspx?idEstructura=112001700010), [aviso INEGI](https://sidof.segob.gob.mx/notas/docFuente/5800864).

Las preguntas dicen año pasado y mes normal, sin identificar mes de pago. Principal: promedio del año calendario anterior al **año real de entrevista**, criterio explícito de valoración, no fecha observada. Sensibilidades: doce meses anteriores al mes real, promedio del año de entrevista y extremos mensuales del año previo. En ronda2021 hay6794directas entrevistadas2021 y2630en2022; sus precios principales son2020 y2021 respectivamente. Ronda2012 tiene12directas en2013 y una sin año válido; ronda2018 tiene202directas en2019. Las entrevistas tardías conservan su ronda y se valoran según su fecha real. No se inventan flujos ni fechas de pago.

K/A ya piden cantidades mensuales; las instrucciones2021 de K indican normalizar otros periodos y descontar impuestos. La entrega bimestral normativa se convierte a equivalente mensual; **no se divide otra vez un importe declarado mensual**. La valoración por INPC no es el valor presente actuarial de una pensión vitalicia. [Pregunta e instrucciones K](https://www.inegi.org.mx/rnm/index.php/catalog/861/variable/F40/V14717?name=K61_1_1_21), [A y valoración de especie](https://www.inegi.org.mx/rnm/index.php/catalog/861/variable/F40/V14790?name=K80_1_1_21).

**Disponibilidad monetaria y alcance.** La auditoría identifica96campos originales disponibles,81con eventos captados, y198campos alternativos de archivos imputados. Los15campos sin evento no se tratan como importes cero. Las versiones alternativas se documentan, sin sumarlas ni usar cantidades anuales/imputadas sin validar su contrato. ENASEMsimple no ofrece un total pensionario personal homologado validado. Todos los eventos captados con monto válido tampoco garantizan todos los beneficios realmente recibidos.

'''
    general=[z for z in r['montos'] if z['dimension']=='General']
    rows=[dict(ronda=z['ronda'],via=z['via'],rec=z['N_receptores'],N=z['N_monto'],N_real=z['persona']['real']['N'],
        ND=z['N_receptores_sin_monto'],eventos=z['N_eventos'],eventoND=z['N_eventos_ND'],
        **{u+'_'+k:z['persona'][u][k] for u in ['nominal','real'] for k in ['q25','mediana','q75']}) for z in general]
    body+=table('Montos de prestaciones: receptores, faltantes y cuartiles nominales y reales',rows,
        [('ronda','Ronda'),('via','Vía'),('rec','N receptores'),('N','N monto nominal'),('N_real','N monto real'),('ND','Receptores sin monto'),
         ('nominal_q25','Q25 nominal $/mes'),('nominal_mediana','Mediana nominal $/mes'),('nominal_q75','Q75 nominal $/mes'),
         ('real_q25','Q25 real $/mes'),('real_mediana','Mediana real $/mes'),('real_q75','Q75 real $/mes')],
        'Distinguir aumentos de pesos declarados de cambios de poder adquisitivo entre receptores.',
        'Suma personal observada parcial, no ingreso total. Pesos reales septiembre2026; principal año calendario previo a entrevista real.2012A:1535montos nominales,1534reales por año de entrevistaND. Distribuciones por evento, percentiles10/90/95, DE/IQR, cobertura monetaria y sensibilidad positiva consultables en07. Ningún cero en montos generales60+directos; el inventario original sí conserva la instrucción de cero por especie no valorada.',
        '1–7')
    body+=image('evolucion','Identificar episodios con aumento nominal y erosión real.',
        'Las conexiones se restringen a continuidad condicionada del instrumento. La deflactación no elimina las rupturas K2003–2012/K2015–2018 o A2001–2003/A2018–2021. Tampoco elimina cambios de composición: un nuevo receptor de monto bajo puede reducir la mediana del grupo aunque nadie pierda su prestación.','6–7')
    temporal=[]
    for p in r['comparabilidad']:
        for via in ['K','A']:
            if p[via]:
                x,y=[amount(r,p[k],via) for k in ['origen','destino']]
                temporal.append(dict(intervalo=f"{p['origen']}–{p['destino']}",via=via,N0=x['N_monto'],N1=y['N_monto'],
                    nominal=100*(y['persona']['nominal']['mediana']/x['persona']['nominal']['mediana']-1),
                    real=100*(y['persona']['real']['mediana']/x['persona']['real']['mediana']-1)))
    body+=table('Variación de medianas en ventanas con comparabilidad condicionada',temporal,
        [('intervalo','Intervalo'),('via','Vía'),('N0','N monto inicial'),('N1','N monto final'),('nominal','Variación nominal %'),('real','Variación real %')],
        'Responder si un incremento nominal representó un incremento real.',
        'Muestras transversales de receptores con monto, no mismos individuos. Cambio porcentual de medianas, no mediana del cambio individual. K2012–15 amplía slots/instrumento; A2015–18 pasa a programas/eventos. Cada ventana es condicionada, sin invariancia completa. Año previo principal; sensibilidades temporal y de modalidad en07.', '7')
    body+='\n\n'.join(conclusions(r)[:2])+'\n\n'
    body+='**Composición pensionaria.** Los eventos K con evidencia de programas públicos agrupados pasan de304/2978en2012 a1190/4453en2015; sus medianas declaradas son500y550pesos nominales. Es una agrupación documental de contingencia con multiselección, sin monto separable por institución; no identifica todo el importe como PAM. El aumento de esa participación ayuda a contextualizar la caída de la mediana K y el gran contraste escolar de2015, sin atribuir una reducción a cada pensionado ni llamar contributivos a todos los registros K. En2018/2021 la categoría histórica8 deja de estar disponible: su ausencia no es cero beneficiarios públicos.\n\n'
    selected=[]
    for dim,groups in [('sexo_grupo',['Hombre','Mujer']),('edad_06',['60–64','65–69','70+']),
        ('educacion_grupo',['0 años','≥10 años']),('localidad_grupo',['<100 mil habitantes','≥100 mil habitantes']),
        ('ocupacion_grupo',['Trabaja','Labores del hogar','Retirado/incapacitado/no trabaja'])]:
        for group in groups:
            k,aa=amount(r,2021,'K',dim,group),amount(r,2021,'A',dim,group)
            c=next(x for z in r['cobertura06'] if z['ronda']==2021 and z['analisis']=='principal' for x in z['cobertura'] if x['dimension']==dim and x['grupo']==group)
            selected.append(dict(grupo=group,N_KA=c['N_K_A_conocidas'],KA=c['KA_soporte_conjunto_pct'],NK=k['N_monto'],NA=aa['N_monto'],
                Kn=k['persona']['nominal']['mediana'],Kr=k['persona']['real']['mediana'],An=aa['persona']['nominal']['mediana'],Ar=aa['persona']['real']['mediana'],
                Klpi=k['persona']['lpi_pct']['mediana'],Alpi=aa['persona']['lpi_pct']['mediana']))
    body+=table('Acceso y montos por perfil en2021: poblaciones y unidades distintas',selected,
        [('grupo','Perfil'),('N_KA','N K/A conocidas'),('KA','K o A %'),('NK','N monto K'),('NA','N monto A'),
         ('Kn','Mediana K nominal $'),('Kr','Mediana K real $'),('An','Mediana A nominal $'),('Ar','Mediana A real $'),
         ('Klpi','Mediana K/LPI %'),('Alpi','Mediana A/LPI %')],
        'Detectar grupos con acceso relativamente alto y prestación parcial de monto reducido.',
        'Directas60+. Cobertura06: mismo soporte K/A por grupo; montos07: solo receptores con monto, separados por vía. LPI asignable2021 cubre todos esos montos. Escolaridad al inicio de participación; localidad100mil para perfil,2500para umbral. Ocupación4 no identifica solo jubilados. A no es efectivo homogéneo; no comparar las dos medianas como suma personal.', '8,12–13')
    body+=image('perfiles2021','Comparar importes mensuales K con A5 de vejez identificada, por evento.',
        'La comparación monetaria entre vías se restringe a A5 con norma monetaria verificada; el cuadro anterior describe separadamente todaA, incluyendo especie. Se comparan prestaciones mensuales por evento entre distintos receptores, sin construir ingreso personal total o suponer contributividadK. Las diferencias relativas no desaparecen al cambiar a pesos constantes; las fechas2021/2022 producen factores distintos antes de resumir. Sin ajuste de edad, sexo o historia laboral.','8,11')
    body+='\n\n'.join(conclusions(r)[2:5])+'\n\n'
    gaprows=[]
    for year in [2012,2015,2018,2021]:
        for dim,g1,g2 in [('sexo_grupo','Hombre','Mujer'),('educacion_grupo','≥10 años','0 años')]:
            x,y=amount(r,year,'K',dim,g1),amount(r,year,'K',dim,g2)
            gaprows.append(dict(ronda=year,contraste=g1+' / '+g2,N1=x['N_monto'],N2=y['N_monto'],
                nominal=x['persona']['nominal']['mediana']-y['persona']['nominal']['mediana'],
                real=x['persona']['real']['mediana']-y['persona']['real']['mediana'],
                razon_nominal=x['persona']['nominal']['mediana']/y['persona']['nominal']['mediana'],
                razon_real=x['persona']['real']['mediana']/y['persona']['real']['mediana']))
    body+=table('Brechas absolutas y relativas de medianas K entre receptores',gaprows,
        [('ronda','Ronda'),('contraste','Grupo1 / grupo2'),('N1','N grupo1'),('N2','N grupo2'),('nominal','Diferencia nominal $'),('real','Diferencia real $'),('razon_nominal','Razón nominal'),('razon_real','Razón real')],
        'Examinar si las brechas monetarias se estrechan al valorar en precios constantes.',
        'Diferencia mediana1−mediana2 y razón mediana1/mediana2; no ajuste sociodemográfico.2012–15 y2018–21 comparabilidad K condicionada;2015–18 ruptura. La fuerte diferencia escolar2015 coincide con distinta composición y captación K de programas públicos; no evidencia una caída individual general. Otras324comparaciones dirigidas y distribuciones se conservan en07.', '8–9')
    body+='**Brechas no uniformes.** La razón hombres/mujeres en K se amplía aproximadamente de1.13a1.20entre2012–2015 y de1.20a1.29entre2018–2021 en pesos reales. La razón escolar ≥10/0 es muy alta en2015 y menor en2021; no puede describirse como cierre homogéneo2001–2021 porque cambian captación, composición y definiciones. Las medianas A coinciden entre sexos y varios niveles escolares en2021; eso respalda una igualación de ese punto de la distribución entre receptores observados, sin demostrar igualdad de toda la distribución o recursos totales.\n\n'
    lp=[]
    for z in general:
        p=z['persona'];lp.append(dict(ronda=z['ronda'],via=z['via'],N=p['N_lpi'],ND=p['N_umbral_ND_monto'],
            q25=p['lpi_pct']['q25'],med=p['lpi_pct']['mediana'],q75=p['lpi_pct']['q75'],menos=p['prestacion_inferior_lpi_pct'],
            difn=p['diferencia_lpi_nominal']['mediana'],difr=p['diferencia_lpi_real']['mediana']))
    body+=table('Prestación parcial en relación con la LPI histórica asignable',lp,
        [('ronda','Ronda'),('via','Vía'),('N','N monto/umbral'),('ND','Montos sin umbral'),('q25','Q25 % LPI'),('med','Mediana % LPI'),('q75','Q75 % LPI'),('menos','Prestación <LPI %'),('difn','Mediana diferencia nominal $'),('difr','Mediana diferencia real $')],
        'Medir la referencia cubierta por una prestación sin diagnosticar pobreza de personas.',
        'LPI alimentaria+no alimentaria mensual por persona, promedio del periodo original, geografía2500. Serie CONEVALmarzo2025 reestimada2024; INEGIresponsabledesde2025.2001/03 asignable solo≥100mil, submuestra distinta; restantes tienen escenarios de ambas líneas, no clasificación arbitraria. Primero razón/diferencia individual, luego cuantiles. Diferencias respecto de línea ND excluidas; no pobreza ni ingreso completo.', '5,12')
    body+=image('umbral','Distinguir razón de prestación/umbral y elección geográfica.',
        'Las líneas históricas cubren todos los periodos2000–2022 usados. Para2012/2015 se dejaron2y4discordancias geográficas directas como ND;2018/2021 quedan12y14sin fuente asignable. No se modificaron localidades. Deflactar prestación y línea con el mismo índice deja invariante su razón. [Serie y método CONEVAL](https://www.coneval.org.mx/Medicion/MP/Paginas/Lineas-de-Pobreza-por-Ingresos.aspx), [LPI INEGI](https://www.inegi.org.mx/desarrollosocial/lp/).','5,12')
    body+='**Suficiencia de qué recurso.** El96.35% de montos A y40.17% de montos K observados2021 están bajo la LPI de referencia. Son prestaciones parciales inferiores a un umbral, no proporción de personas pobres. Pueden existir otros ingresos, recursos compartidos y gastos distintos; tampoco una prestación sobre la línea prueba suficiencia integral. A como valor de especie tiene una interpretación diferente de efectivo disponible. Los grupos de edad70+ combinan alta cobertura propia con menores montos K que60–64, sin demostrar peor ingreso total.\n\n'
    policies=json.loads((OUTPUT/'cronologia_politicas.json').read_text())
    cr=[]
    norms=r['norma_programa']
    for x in policies['cronologia']:
        if x['periodo'].startswith(('2001','Todas','2022')):continue
        normperiod='2009' if x['periodo']=='2008–2009' else '2014' if x['periodo']=='2014–2018' else x['periodo']
        n=next(z for z in norms if z['periodo']==normperiod)
        cr.append(dict(periodo=x['periodo'],regla=x['cambio'],nominal=x['mensual_nominal'],real=n['real_mensual'],fuente=f"[DOF]({x['fuente']})"))
    body+=table('Cronología federal y monto normativo mensual nominal y real',cr,
        [('periodo','Periodo'),('regla','Regla y población objetivo'),('nominal','Norma nominal $/mes'),('real','Norma real $/mes'),('fuente','Fuente oficial')],
        'Contextualizar acceso, edades y montos sin atribuir automáticamente registros a programas.',
        'Montos oficiales mensuales; entrega bimestral general. Norma real usa INPCmedio del periodo indicado, distinto del año previo usado para respuestasENASEM.2008–09 columna real refiere2009;2014–18 a2014, evolución completa en figura.2013 incremento desde segundo bimestre;2021julio vigencia8julio, sin flujo diario reconstruido. Antecedentes localesDF y otros programas documentados en nota; no todaA corresponde a estas normas.', '10')
    body+=image('norma','Identificar cambios de poder adquisitivo de importes normativos.',
        'El monto PAM580 sin cambio nominal2014–2018 pasa de$993a$845reales de septiembre2026, una caída aproximada14.88%. El aumento normativo de580en2018 a1275en2019 aumenta el equivalente real, de$845a$1793. El salto normativo no prueba el cambio efectivamente recibido por todaA ni su efecto sobre pobreza.','10')
    norm=next(x for x in r['comparacion_A5'] if x['dimension']=='General')
    comparisons=[]
    for label,key in [('A5 declarado','declarado'),('Norma año previo principal','norma_periodo_principal'),('Norma mes real de entrevista','norma_entrevista')]:
        q=norm[key]; comparisons.append(dict(referencia=label,N=q['nominal']['N'],nominal=q['nominal']['mediana'],real=q['real']['mediana']))
    body+=table('Programa de vejez identificado A5 en2021 y dos referencias normativas',comparisons,
        [('referencia','Importe o referencia'),('N','N eventos con monto'),('nominal','Mediana nominal mensual $'),('real','Mediana real mensual $')],
        'Comparar declaraciones con importes normativos sin confundir ventana de recuerdo con fecha de entrevista.',
        '4784eventos A5/4784personas directas60+; N de montos válidos específico. Solo código5 del programa identificado, sin incluir todos los apoyos. Norma año previo:1310para entrevistas2021 y promedio1450para2022; norma entrevista:1350/1550en2021 según semestre,1925en2022. Equivalentes normativos mensuales, no fechas de pago. Códigos de programa no certifican efectivo pagado o elegibilidad;20eventos en60–64 se conservan sin corregir.', '11')
    body+=conclusions(r)[5]+'\n\n'
    c=next(x for x in r['comparacion_K_A5'] if x['dimension']=='General')
    body+=f"**Comparación monetaria defendible K/A5.** En2021, los {c['K_evento']['nominal']['N']:,}eventosK con monto tienen mediana${c['K_evento']['nominal']['mediana']:,.0f}nominal/${c['K_evento']['real']['mediana']:,.0f}real; los {c['A5_evento']['nominal']['N']:,}eventosA5 de vejez, ${c['A5_evento']['nominal']['mediana']:,.0f}/${c['A5_evento']['real']['mediana']:,.0f}. La diferencia de medianas es${c['diferencia_nominal']:,.0f}nominal y${c['diferencia_real']:,.0f}real; la razón es{c['razon_real']:.2f}en pesos reales. Se compara un importe mensual por evento de programaA5 con norma económica verificada, no todaA como efectivo. Titularidad, poblaciones receptoras y ventanas de recuerdo siguen siendo distintos; no diferencia causal ni ingresos personales completos.\n\n"
    body+='**Lectura política defendible.** La ampliación65+ de2021 es consistente con recepción muy distinta por edad, pero el acceso observado de65–69 queda muy por debajo de70+: reglas previas68+, inscripción escalonada, año de recuerdo y entrevistas2022 impiden atribuir esa distancia a una única política. El predominio de A5 y la concentración de importes en1550coinciden descriptivamente con la norma de segundo semestre2021, pero el criterio año previo produce discrepancia y exige sensibilidad. La reforma territorial no puede estudiarse con el corte100mil como si fuera20/30mil. Sin geografía fina histórica, fecha efectiva de alta, padrón o pagos, no se identifica un efecto causal.\n\n'
    follow=[]
    for x in r['seleccion']:
        if x['dimension']=='General':
            follow.append(dict(intervalo=f"{x['origen']}–{x['destino']}",via=x['via'],N=x['N_basal_recepcion_conocida'],pares=x['N_pares_conocidos'],
                basal=x['cobertura_basal_pct'],ret=x['cobertura_basal_retenidos_pct'],monto0n=x['nominal_basal']['mediana'],montoRn=x['nominal_basal_retenidos']['mediana'],
                monto0=x['real_basal']['mediana'],montoR=x['real_basal_retenidos']['mediana'],np=x['N_receptores_ambas_monto'],
                cambioN=x['cambio_nominal_receptores_ambas']['mediana'],cambioR=x['cambio_real_receptores_ambas']['mediana']))
    body+=table('Selección económica: basal completo, retenidos y cambios monetarios pareados',follow,
        [('intervalo','Intervalo'),('via','Vía'),('N','N basal recepción conocida'),('pares','N pares recepción conocida'),('basal','Basal recepción %'),('ret','Basal retenidos %'),
         ('monto0n','Basal mediana nominal $'),('montoRn','Retenidos mediana nominal $'),('monto0','Basal mediana real $'),('montoR','Retenidos mediana real $'),
         ('np','N receptor ambas/monto'),('cambioN','Mediana cambio nominal $'),('cambioR','Mediana cambio real $')],
        'Examinar cuánto cambia la lectura al condicionar a observación posterior.',
        'Cohorte basal60+ directa. Pares de recepción conocida vivos/directos, sin filtro de edadfinal. Montosbasales solo receptores con monto; pares monetarios solo receptor/monto válido en ambas. Muerte registrada, ausencia vitalND, sustituto vivo y recepciónND separados en07; cotas06 preservadas. No corrección de sesgo, ni pagos posteriores a fallecimiento.2001–03K sensibilidad; restantes ventanas condicionadas de cada vía, no unión completa en todos intervalos.', '14–15')
    body+=image('seleccion','Comprobar si retención modifica la brecha monetaria basal por sexo.',
        'En K2018–2021, el porcentaje basal entre quienes quedan en pares conocidos es35.14%, frente a35.89% de la cohorte basal conocida; la mediana K basal de receptores con monto pasa de$4280a$4432reales al seleccionar retenidos. Estas diferencias son descriptivas y no garantizan ausencia de selección en otros cuantiles o subgrupos.','14–15')
    def selected_gap(dim,g1,g2,key):
        x,y=[next(z for z in r['seleccion'] if z['origen']==2018 and z['via']=='K' and z['dimension']==dim and z['grupo']==g) for g in [g1,g2]]
        return x[key]['mediana']-y[key]['mediana']
    sex=selected_gap('sexo_grupo','Hombre','Mujer','real_basal')
    local0=selected_gap('localidad_grupo','≥100 mil habitantes','<100 mil habitantes','real_basal')
    local1=selected_gap('localidad_grupo','≥100 mil habitantes','<100 mil habitantes','real_basal_retenidos')
    edu0=selected_gap('educacion_grupo','≥10 años','0 años','real_basal')
    edu1=selected_gap('educacion_grupo','≥10 años','0 años','real_basal_retenidos')
    body+=f'**Selección por perfil.** En K2018–2021, la brecha basal hombres−mujeres de medianas reales entre receptores con monto permanece en${sex:,.2f}al seleccionar retenidos. La brecha entre localidades≥100mil y menores pasa de${local0:,.2f}a${local1:,.2f}; la brecha escolar ≥10/0años pasa de${edu0:,.2f}a${edu1:,.2f}. La retención puede ampliar contrastes sin cambiar mucho la mediana global. Los N específicos por perfil están en07; no se atribuyen recursos a quienes mueren o dejan de observarse.\n\n'
    body+='**Transversal frente a individual.** En K2012–2015, la mediana transversal real cae aproximadamente$468; entre1762receptores con monto válido en ambas visitas, la mediana del cambio individual es−$40.26reales y+$223.50nominales. En K2018–2021 la mediana transversal aumenta aproximadamente$1159, pero entre1835receptores pareados la mediana del cambio es+$104.27reales y+$500nominales. Estos contrastes no son una descomposición causal: se condiciona a recepción en ambas visitas y se excluyen nuevos receptores, fallecidos y pérdidas. En A2012–2015/2015–2018 los cambios pareados medianos son−$58.58/−$55.02reales, respectivamente, pese a cambios nominales positivos.\n\n'
    body+='\n\n'.join(conclusions(r)[6:])+'\n\n'
    body+='**Respuesta a las preguntas monetarias y estado.** Algunos incrementos nominales sí representan aumentos reales, como K2018–2021; otros no, como A2012–2015/A2015–2018. Las brechas no se reducen de forma uniforme: persisten contrastes K por sexo/escolaridad y las fechas afectan su escala. Mayor acceso puede coexistir con montos parciales bajos, particularmente los perfiles de poca escolaridad y mayor edad. La expansión de unión propia y suficiencia solo se comparan conjuntamente de manera condicionada2012–2015; para todo2001–2021 la respuesta es parcial por rupturas. Validación operacional y reproducción realizadas; permanecen abiertas interpretación exacta del periodo monetario, ingresos completos, imputaciones, ponderación, instrumentación y atribución política. El siguiente paso útil es validar el periodo de recuerdo/pago y la composición K de programas agrupados antes de un diseño causal o valor presente actuarial.\n'
    body=readable(body)
    path=RESULTS_DIR/'INFORME_GENERAL.md';text=path.read_text()
    begin,end='<!-- BEGIN politicas_montos_07 -->','<!-- END politicas_montos_07 -->'
    ledger=OUTPUT/'informe_contribucion.json'
    if begin in text:
        i=text.index(begin);j=text.index(end,i)+len(end)
        assert sha256(text[i:j].encode()).hexdigest()==json.loads(ledger.read_text())['sha_bloque'],'Bloque07 editado manualmente'
        text=text[:i]+begin+'\n\n'+body+'\n'+end+text[j:]
    else:
        i=text.index('<a id="seccion-limites"></a>')
        text=text[:i].rstrip()+'\n\n'+begin+'\n\n'+body+'\n'+end+'\n\n'+text[i:]
    text=text.replace('actualizada con los notebooks 03–06. La etapa06 examina','actualizada con los notebooks 03–07. La etapa06 examina')
    if 'La etapa07 añade' not in text and 'La etapa 07 añade' not in text:
        text=text.replace('la igualación y la suficiencia permanecen hipótesis por contrastar.','la igualación y la suficiencia permanecen hipótesis por contrastar. La etapa 07 añade precios constantes de septiembre de 2026, umbrales históricos y cronología oficial, con resultados condicionados por definición y periodo monetario.')
    text=text.replace('La etapa07 añade precios constantes de septiembre2026','La etapa 07 añade precios constantes de septiembre de 2026')
    tables,images={},{}
    lines=text.splitlines()
    for i,line in enumerate(lines):
        h=re.match(r'\*\*Cuadro \d+\. (.*)\*\*$',line)
        if h:
            tables[h[1]]=len(tables)+1;lines[i]=f'**Cuadro {tables[h[1]]}. {h[1]}**'
        h=re.match(r'\*\*Figura \d+\. (.*)\*\*$',line)
        if h:
            images[h[1]]=len(images)+1;lines[i]=f'**Figura {images[h[1]]}. {h[1]}**'
        h=re.match(r'!\[Figura \d+: (.*?)\]\((.*?)\)',line)
        if h:lines[i]=f'![Figura {images[h[1]]}: {h[1]}]({h[2]})'
    text='\n'.join(lines)+'\n';path.write_text(text)
    i=text.index(begin);j=text.index(end,i)+len(end)
    save_json(ledger,dict(sha_bloque=sha256(text[i:j].encode()).hexdigest(),productos=products))
    p=INTERIM_DIR/'informe_general_seleccion.json';d=json.loads(p.read_text())
    d['productos']=[x for x in d['productos'] if x.get('notebook')!='notebooks/'+NOTEBOOK]+products
    for x in d['productos']:x['numero']=(tables if x['tipo']=='tabla' else images)[x['titulo']]
    d['cuadros'],d['figuras']=len(tables),len(images);save_json(p,d)
    p=INTERIM_DIR/'indice_informe.json';d=json.loads(p.read_text())
    matches=list(re.finditer(r'<a id="seccion-([a-z]+)"></a>',text))
    d['secciones_sintesis']={m[1]:dict(inicio=m.start(),fin=matches[i+1].start() if i+1<len(matches) else len(text)) for i,m in enumerate(matches)}
    d['sha_sintesis']=sha256(text.encode()).hexdigest();save_json(p,d)
    verify_inputs()
    print('Informe07:',len(tables),'cuadros y',len(images),'figuras totales')


if __name__=='__main__':export()
