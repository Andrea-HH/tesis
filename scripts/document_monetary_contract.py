"""Documenta fuentes y decisiones07, sin generar un informe académico paralelo."""

import json

from tesis_enasem.monetary_policy import OUTPUT, QUESTION, save_json
from tesis_enasem.project_paths import PROJECT_ROOT


def document() -> None:
    """Cronología oficial accesible y contrato de importe/periodo/geografía."""
    sidof='https://sidof.segob.gob.mx/notas/docFuente/'
    history=sidof+'5676228'
    chronological=[
        dict(periodo='2001–2003',ambito='Local: Distrito Federal',programa='Apoyo alimentario; derecho a pensión alimentaria',
             cambio='Antecedente local2001; ley publicada18noviembre2003 para70+, residencia local. Sin monto monetario homologado en esta auditoría.',
             mensual_nominal=None,fuente='https://www.congresocdmx.gob.mx/archivo-0c969a6e952fa1b740aef0fbed5c405101985cdf.pdf',
             limite='No se identifica entidad/programa local individual en A histórica; no atribuir todos los apoyos al DF. Fuente legislativa retrospectiva.'),
        dict(periodo='2007',ambito='Federal',programa='70 y Más',
             cambio='RO28febrero2007, vigencia día siguiente:70+, localidades hasta2500, restricciones de duplicación federal y presupuesto.',
             mensual_nominal=500,fuente=sidof+'4964186',limite='Entrega bimestral, excepcional cuatrimestral; norma mensual no es pago observado.'),
        dict(periodo='2008–2009',ambito='Federal',programa='70 y Más',
             cambio='Expansión territorial: hasta20mil habitantes en2008 y30mil en2009, documentada en antecedentes oficiales.2009 apoyo500mensuales.',
             mensual_nominal=500,fuente=history,limite='Resumen retrospectivo, no fecha individual de alta; no equivale al corte100mil. Norma2009 contrastada en RO5076295.'),
        dict(periodo='2012',ambito='Federal',programa='70 y Más',
             cambio='70+, sin ingresos de jubilación/pensión; alcance nacional, incorporación de localidades mayores30mil y dispersión electrónica.',
             mensual_nominal=500,fuente=sidof+'5228700',limite='K código8 agrupa programas federales/estatales; A sin programa identificado. No separar automáticamente régimen contributivo.'),
        dict(periodo='2013',ambito='Federal',programa='Pensión para Adultos Mayores',
             cambio='RO26febrero2013: edad65+, incremento525mensuales desde segundo bimestre; reforma posterior admite pensión contributiva hasta1092mensuales.',
             mensual_nominal=525,fuente=sidof+'5309974',limite='Fuente es modificación de la RO original; inicio/importe contrastados con antecedentes oficiales5676228. Entrevistas tardías2012 no equivalen a exposición al cambio.'),
        dict(periodo='2014–2018',ambito='Federal',programa='Pensión para Adultos Mayores',
             cambio='65+, mexicanas o25años de residencia; pensión contributiva no mayor1092mensuales. Importe580mensuales,1160bimestrales, sin aumento nominal hasta2018.',
             mensual_nominal=580,fuente=sidof+'5509626',limite='PAM2018 cotejado en RO, tramo2014–18 en antecedentes oficiales5676228. K/A mezclan otras instituciones o apoyos; no inferir ingreso total.'),
        dict(periodo='2019',ambito='Federal',programa='Pensión para el Bienestar de las Personas Adultas Mayores',
             cambio='RO28febrero2019:68+ general,65+ indígenas en municipios catalogados, continuidad65–67 del padrón activo diciembre2018;1275mensuales.',
             mensual_nominal=1275,fuente=sidof+'5551445',limite='Registro/presupuesto y pertenencia a padrón no observados. Nuevas condiciones no homologan A2018/2021.'),
        dict(periodo='2020',ambito='Federal',programa='Pensión para el Bienestar',
             cambio='1310mensuales,2620bimestrales;68+ general y65+ indígenas, continuidad de padrón65–67.',
             mensual_nominal=1310,fuente=sidof+'5583304',limite='Referente normativo para año previo de entrevistas2021, sin prueba de pagos o elegibilidad individual.'),
        dict(periodo='2021 enero–junio',ambito='Federal',programa='Pensión para el Bienestar',
             cambio='RO22diciembre2020:1350mensuales,2700bimestrales;68+ general,65+ indígenas/afromexicanos y continuidad del padrón.',
             mensual_nominal=1350,fuente=sidof+'5608440',limite='Mes normal/año pasado ambiguo; no asignar norma del mes de entrevista como fecha de pago.'),
        dict(periodo='2021 julio–diciembre',ambito='Federal',programa='Pensión para el Bienestar',
             cambio='Modificación publicada7julio, vigencia8julio2021:65+ general,1550mensuales,3100bimestrales.',
             mensual_nominal=1550,fuente=sidof+'5623150',limite='Inscripción65–67 inició por etapas en agosto; norma vigente no certifica incorporación o cobro. No prorrateo diario del INPC mensual.'),
        dict(periodo='2022: solo entrevistas tardías de ronda2021',ambito='Federal',programa='Pensión para el Bienestar',
             cambio='1925mensuales,3850bimestrales,65+; se usa únicamente para sensibilidad del referente en fecha real de entrevista.',
             mensual_nominal=1925,fuente=sidof+'5639752',limite='No extender rondas analíticas más allá de2001–2021 ni presentar entrevistas2022 como política2021.'),
        dict(periodo='Todas las rondas; nombres cambian',ambito='Federal y otras instituciones públicas; estatal/local no separable',programa='Apoyos agrícolas, programas de hogar, becas, INAPAM y otros',
             cambio='Cuestionarios citan PROCAMPO/PROAGRO/ProducciónBienestar, Progresa/Oportunidades/Prospera/Becas e INSEN/INAPAM; A incluye valor de especie.',
             mensual_nominal=None,fuente='https://mhasweb.org/Resources/DOCUMENTS/2018/Comparativo_Preguntas_MHAS_2001_2003_2012_2015_2018.pdf',
             limite='A no identifica una pensión federal única. Becas/apoyos agrícolas pueden tener reglas, receptores y periodicidades diferentes; no atribuirles montoPAM/Bienestar.'),
    ]
    waves=[
        dict(ronda=2001,politica='Antecedentes locales; apoyos públicos diversos, antes de70yMás',referencia='Aúltimo año; no programa identificado',limitacion='Sin geografía2500, ni asignación política individual'),
        dict(ronda=2003,politica='Antecedente federal rural y derecho localDF2003; A diversa',referencia='Entrevistasjunio–septiembre2003 preceden leyDFnoviembre',limitacion='La ley posterior no es exposición observada de esta ronda; A rompe2001–03'),
        dict(ronda=2012,politica='70yMás500mensuales y expansión territorial',referencia='A/K: año pasado; 12directas tardías2013, referencia principal2012',limitacion='Kincluye programas agrupados, no es contributiva; A sin programa; K rompe2003–12'),
        dict(ronda=2015,politica='PAM580mensuales,65+ y límite contributivo1092',referencia='Año previo2014, sensibilidad12meses anteriores a entrevista',limitacion='Kslots3/institución por tipo; Avalor agregado; unión solo2012–15 condicionadamente comparable'),
        dict(ronda=2018,politica='PAM580; entrevistas tardías2019 coexisten con nueva política',referencia='202directas entrevistadas2019; precios principales2018 para esas personas',limitacion='K rompe2015–18; A slots/programas2018; comparación de rondas no es efecto de reforma'),
        dict(ronda=2021,politica='Bienestar1350/1550 y ampliación65+; entrevistas tardías2022',referencia='6794directas2021,2630en2022; precio principal2020/2021 respectivamente',limitacion='Aañade código5 explícito: ruptura2018–21; norma actual, recuerdo y pago no son el mismo periodo'),
    ]
    save_json(OUTPUT/'cronologia_politicas.json',dict(pregunta=QUESTION,consulta='2026-10-14',cronologia=chronological,por_ronda=waves))
    contract=dict(pregunta=QUESTION,notebook='07_POLITICAS_MONTOS_SUFICIENCIA.ipynb',poblacion='Directas60+ principal; sustitutos sensibilidad',
        monto='Original mensual por evento y suma parcial por persona; nunca total de ingresos ni K+A. Cónyuge contextual separado.',
        moneda='Pesos mexicanos declarados en preguntas mensuales; no se convierte automáticamente pensiónEEUU a USD ni se supone moneda distinta.',
        periodicidad='K58/K61/K64/K67, A K77/K80/K83: mes normal; entrevistador normalizaperiodos. Montos normativos bimestrales÷2 ya documentados, declaracionesmensuales no se dividenotra vez.',
        precios=dict(fuente='INEGI serie865541, base segundaquincena julio2018=100, actualización2024',referencia='2026-09',inpc=146.075,
            periodo_principal='Media12meses año calendario anterior al año real de entrevista; criterio por año pasado sin mes de pago observado',
            sensibilidad=['12meses anteriores al mes real','Promedio año real de entrevista','Mínimo/máximo INPCmensual del año previo'],
            formula='Nominal×146.075/INPCoriginal; mensual mantiene unidad mensual',valor_presente_actuarial=False),
        lpi=dict(fuente='CONEVAL histórica, archivo marzo2025 reestimado2024; INEGIresponsable desde2025',unidad='Pesos mensuales por persona, canasta alimentaria+no alimentaria',
            fecha='Mismo periodo explícito de valoración de prestación; escenarios12meses',geografia='Rural<2500/urbana≥2500; camposoriginales2012–21;2001/03≥100milurbana, restoND',
            limite='Una prestación parcial inferior al umbral no diagnostica pobreza individual/hogar. Escenarios no asignan ruralidad.'),
        comparabilidad='Condicionada:K2001–03/2012–15/2018–21;A2003–12/2012–15/2015–18. Rupturas limitan también evolución de brechas monetarias.',
        comparacion_entre_vias='Importes mensuales por eventoK frente a A5 de vejez2021 con norma monetaria verificada. TodaA se describe como valoración dinero/especie separada; no se compara como efectivo homogéneo.',
        cero_A='2021puede representar especie sin valoración; no garantiza ingreso efectivo0; sensibilidadpositivos',
        imputados='Inventario198campos, no se suman ni utilizan sin contrato de escala/unidad/beneficiario; no imputación nueva',
        seleccionado='Precios/umbral evaluados solo en07; bloqueos06 describen estado de esa etapa, no anulan autorización07')
    save_json(PROJECT_ROOT/'diccionarios/contrato_monetario_politicas.json',contract)
    text='# Fuentes y cronología documental de políticas de vejez para ENASEM\n\n'+QUESTION+'\n\n'
    text+='Nota documental de la etapa07. No sustituye el informe general ni atribuye prestaciones individuales. Consulta:14octubre2026.\n\n'
    for x in chronological:
        text+=f"## {x['periodo']} · {x['programa']}\n\nÁmbito: {x['ambito']}. {x['cambio']}\n\nLímite para ENASEM: {x['limite']}\n\n[Fuente oficial]({x['fuente']}).\n\n"
    text+='## Criterios de precios y umbrales\n\nINPCmensualINEGI, serie865541,321mesesenero2000–septiembre2026. Referencia septiembre2026=146.075, base segundaquincena julio2018=100, actualizacióncanasta2024. [Serie oficial](https://www.inegi.org.mx/app/indicesdeprecios/Estructura.aspx?idEstructura=112001700010), [aviso INEGIpublicadoDOF9octubre2026](https://sidof.segob.gob.mx/notas/docFuente/5800864).\n\nLPIhistóricasCONEVAL1992–marzo2025, reestimadas2024; cubren años2000–2022 necesarios. ResponsabilidadactualINEGI. [Serie y método](https://www.coneval.org.mx/Medicion/MP/Paginas/Lineas-de-Pobreza-por-Ingresos.aspx), [INEGI](https://www.inegi.org.mx/desarrollosocial/lp/). Corte rural<2500 yurbana≥2500, pesos mensualesporpersona.\n\nPreguntasK/A: año pasado y mes normal, sin mes de pago. Criterioprincipal año calendarioprevio al año realdeentrevista; sensibilidad12mesesprevios, año entrevista y extremos mensuales. No es fecha observada. Los importesAincluyenvaloracionesdeespecie; Knetadeimpuestos según instrucciones2021. [K61](https://www.inegi.org.mx/rnm/index.php/catalog/861/variable/F40/V14717?name=K61_1_1_21), [A K80](https://www.inegi.org.mx/rnm/index.php/catalog/861/variable/F40/V14790?name=K80_1_1_21). No dividir de nuevo los importesya mensualizados ni convertir pesos constantesen valor presente actuarial.\n'
    from tesis_enasem.monetary_policy_outputs import readable
    (PROJECT_ROOT/'investigacion/notas/politicas_publicas_envejecimiento.md').write_text(readable(text))


if __name__=='__main__':document()
