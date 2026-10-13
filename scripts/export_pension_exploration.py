"""Redacción académica, preguntas derivadas y cuadros desde agregados EDA v1."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text
import json
from pathlib import Path
import shutil
import re
import pandas as pd

from tesis_enasem.manuscript import render_latex_table, latex_number, escape_latex
from run_pension_exploration import ROOT,PUBLIC,YEARS,checked_hashes


def academic_latex(text: str) -> str:
    """Convierte solo cifras del agregado a notación del manuscrito."""
    pattern=re.compile(r'(?<![\w])[-+]?\d+(?:,\d{3})*(?:\.\d+)?')
    output=[];position=0
    for match in pattern.finditer(text):
        output.append(escape_latex(text[position:match.start()]));token=match.group()
        if ',' in token or '.' in token:
            decimals=len(token.split('.')[-1]) if '.' in token else 0
            output.append(latex_number(float(token.replace(',','')),decimals))
        else:output.append(escape_latex(token))
        position=match.end()
    output.append(escape_latex(text[position:]));return ''.join(output)


def export() -> None:
    r=json.loads(read_project_text(PUBLIC/'resultados.json'));old=json.loads(read_project_text(project_path('', 'docs/eda/proteccion_economica/resultados.json')))
    tables=project_path('', 'manuscrito/tablas');chapters=project_path('', 'manuscrito/capitulos');figures=project_path('', 'manuscrito/figuras/borradores')
    def load(key):return json.loads(read_project_text(PUBLIC/'tablas'/f'{key}.json'))
    def cell(key,var,**levels):
        return next(z for z in load(key)['tasas'] if z['variable']==var and all(z[k]==v for k,v in levels.items()))
    def rate(z):return latex_number(z['N_si'])+'/'+latex_number(z['N_conocido'])+' ('+latex_number(z['pct_si_conocido'],2)+r'\%)'
    summary=[]
    for year in YEARS:
        categories={z['categoria']:z['N'] for z in r['univariados'][str(year)]['titularidad']}
        summary.append({'Año':str(year),'N 60+':next(z['N'] for z in r['validacion']['rondas_N'] if z['ano']==year),
            'Solo propia':categories.get('Solo propia',0),'Solo pareja':categories.get('Solo cónyuge',0),
            'Ambas':categories.get('Ambas',0),'Negativas':categories.get('Ambas negativas K',0),'ND':categories.get('Desconocido',0)})
    write_project_text(tables.joinpath('exploracion_ramas.tex'), render_latex_table(pd.DataFrame(summary),
      'Situaciones pensionarias propias y del cónyuge en la muestra de 60 años o más',
      'tab:exploracion-ramas',
      'Fuente: agregados exploración v1, titularidad v1 y maestro ENASEM. Sin ponderar. Las categorías exigen ambas ramas conocidas; ND puede incluir una afirmativa propia con cónyuge desconocido. Negativas solo corresponden al bloque K, no a toda pensión. 2001/J1 provisional.'))
    age=[]
    for z in load('B2_2021')['tasas']:
        if z['variable']=='pension_propia_k':
            a=next(x for x in load('B2_2021')['tasas'] if x['edad_quinquenal']==z['edad_quinquenal'] and x['variable']=='apoyo_propio')
            age.append({'Edad':z['edad_quinquenal'],'K sí':z['N_si'],'K válido':z['N_conocido'],'K %':z['pct_si_conocido'],
                'A sí':a['N_si'],'A válido':a['N_conocido'],'A %':a['pct_si_conocido']})
    write_project_text(tables.joinpath('exploracion_edad_2021.tex'), render_latex_table(pd.DataFrame(age),
      'Pensión propia K y apoyo propio A por edad quinquenal, 2021','tab:exploracion-edad',
      'Fuente: B2_2021. Porcentajes dentro de grupos con respuesta conocida; N total y ND en respaldo. Sin ponderar. K/A son bloques observados, no clasificación completa contributiva/no contributiva.'))
    profiles=[]
    for group,label in [('ocupacion_grupo','Actividad'),('sexo_grupo','Sexo')]:
        key='B7_2021' if group=='ocupacion_grupo' else 'B1_2021'
        for z in load(key)['tasas']:
            if z['variable']=='pension_propia_k' and z[group]!='Desconocido':profiles.append({'Perfil':z[group],
                'K sí':z['N_si'],'K válido':z['N_conocido'],'K ND':z['N_desconocido'],'K %':z['pct_si_conocido']})
    for profile in profiles:
        if profile['Perfil']=='Retirado, incapacitado o no trabaja':profile['Perfil']='Retiro/incapacidad/no trabajo'
    write_project_text(tables.joinpath('exploracion_actividad_sexo.tex'), render_latex_table(pd.DataFrame(profiles),
      'Recepción propia según actividad y sexo, 2021','tab:exploracion-actividad',
      'Fuente: B7_2021/B1_2021. Ocupación es condición de actividad, no profesión. Retiro/incapacidad/no trabajo es una sola categoría de fuente. Perfil de sexo y actividad son dos cruces separados, no una tabla trivariada. Tasas no ponderadas entre respuestas conocidas.'))
    edu=[]
    for level in ['0 años','1–5 años','6 años','7–9 años','≥10 años']:
        h=cell('T1_2021','pension_propia_k',sexo_grupo='Hombre',educacion_grupo=level)
        m=cell('T1_2021','pension_propia_k',sexo_grupo='Mujer',educacion_grupo=level)
        edu.append({'Años':level,'H sí':h['N_si'],'H válido':h['N_conocido'],'H %':h['pct_si_conocido'],
                    'M sí':m['N_si'],'M válido':m['N_conocido'],'M %':m['pct_si_conocido']})
    write_project_text(tables.joinpath('exploracion_sexo_educacion.tex'), render_latex_table(pd.DataFrame(edu),
      'Pensión propia K por sexo y escolaridad simultáneamente, 2021','tab:exploracion-sexo-educacion',
      'Fuente: T1_2021. Escolaridad en primera entrevista; grupos en años, no títulos acreditados. Tres dimensiones simultáneas. Porcentajes dentro de sexo-escolaridad entre respuestas K conocidas; ND y estratos de escolaridad desconocida en respaldo.'))
    wealth=[]
    for z in load('B8_2021')['patrimonio']:
        wealth.append({'Ramas K':z['titularidad_grupo'],'N válido':z['N_valido'],'Mediana':z['mediana'],'P25':z['p25'],'P75':z['p75']})
    write_project_text(tables.joinpath('exploracion_patrimonio.tex'), render_latex_table(pd.DataFrame(wealth),
      'Distribución patrimonial según ramas pensionarias, 2021','tab:exploracion-patrimonio',
      'Fuente: B8_2021. Unidades monetarias almacenadas sin deflactor. Patrimonio del sujeto y cónyuge, no ingreso personal. Ramas K estrictas; ND no implica ausencia. No sumar estas filas como hogares diferentes ni definir vulnerabilidad por cuantiles.'))
    inst=load('B6_2021')['instituciones'];iselect=[]
    for z in inst:
        iselect.append({'Institución':{1:'IMSS',2:'ISSSTE',3:'Otra pública',4:'Otra privada',5:'Seguridad social EUA',6:'Otra institución',7:'Una persona'}[z['institucion_codigo']],
          'Personas':z['N_personas'],'% institución conocida':z['pct_receptoras_con_institucion']})
    write_project_text(tables.joinpath('exploracion_instituciones.tex'), render_latex_table(pd.DataFrame(iselect),
      'Instituciones y fuentes declaradas de prestaciones K, 2021','tab:exploracion-instituciones',
      f'Fuente: B6_2021 y etiquetas del original 2021. Denominador: {inst[0]["N_receptoras_institucion_identificada"]} receptoras con al menos una institución identificada; {inst[0]["N_receptoras_institucion_ND"]} sin institución identificada. Selección múltiple: filas no aditivas. Otras instituciones y una persona no permiten asignar automáticamente régimen contributivo.'))
    follow=[]
    for z in r['correspondencias']:
        follow.append({'Periodo':str(z['ano_origen'])+'–'+str(z['ano_destino']),'Origen 60+':z['N_origen_60_vivo'],
          'Presentes':z['N_presente_destino'],'Fallecidos':z['N_sobre_fallecido_destino'],'Ausentes':z['N_ausente_destino'],'Reaparecen':z['N_reaparece_posterior']})
    write_project_text(tables.joinpath('exploracion_correspondencias.tex'), render_latex_table(pd.DataFrame(follow),
      'Correspondencia de personas de 60 años o más en origen entre rondas','tab:exploracion-correspondencias',
      'Fuente: seguimiento v1. Fallecidos es subconjunto de presentes; reaparición posterior es subconjunto de ausentes. Cierre 2021 impide verificar retorno posterior. Ausencia no demuestra pérdida definitiva ni muerte. Destino se conserva aunque la edad final disminuya o falte.'))
    method=r'''\section{Exploración pensionaria y estrategia abierta de investigación}
\label{sec:exploracion-metodo}

La autora autorizó una modificación explícita de estrategia el 12 de octubre de
2026. Esta etapa estudia la distribución y las trayectorias de las pensiones
para formular preguntas sustentadas en los datos; no adopta todavía pregunta
definitiva, hipótesis principal, variable objetivo, definición de vulnerabilidad
ni modelo. La alerta temprana se conserva como antecedente y posibilidad futura.
El universo de CP1 y los productos de integración y titularidad permanecen
inalterados. Esta ampliación reutiliza esos productos y evita repetir las
uniones o deducir titularidad a partir de la presencia de ingresos del hogar.

La selección exploratoria exige edad registrada de al menos 60 años en cada
visita, sin continuidad obligatoria ni restricción inicial a entrevistas
directas. Se reproduce una muestra de 56\,004 personas-ronda de 18\,754 personas;
el maestro conserva 99\,676 registros de 27\,171 personas. Un filtro central
configurable devuelve una copia y comprueba la unicidad de \texttt{id+ronda}.
La función existente concatena \texttt{cunicah:np}, con separador, sin sustituir
los códigos personales históricos ni modificar sus formatos almacenados.
Los registros sobre fallecidos se preservan en el maestro y el seguimiento;
no se interpretan como ingresos actuales de una persona viva. La edad
contemporánea ausente no se rellena para incluirlos en una muestra de 60+.

La organización conceptual distingue columnas, versiones y conceptos.
Las 8\,668 columnas se trazan individualmente, incluidas claves, indicadores de
faltantes y controles. La clasificación léxica de las columnas sin contrato
se presenta como candidata y requiere revisión documental. Los contratos
previos de ENASEMsimple y K2021 se vinculan al mapa, sin tratar nombres parecidos
como equivalencias verificadas. Original, imputado, construido y armonizado
conservan su procedencia; solo eventos originales previamente orientados
alimentan las nuevas distribuciones de recepción e institución.

Se distinguen recepción propia, del cónyuge, ambas, negativas de ambas ramas y
estado conjunto desconocido. Esta última categoría exige prudencia: una
respuesta propia afirmativa puede coexistir con desconocimiento del cónyuge,
por lo que el cuadro conjunto no sustituye la tasa propia. Una negativa K solo
corresponde a las contingencias capturadas en K. El donativo A no identifica
siempre programa, prestación no contributiva o entrega monetaria separada de
especie. Las instituciones múltiples cuentan personas por institución y nunca
replican el monto por cada selección. El número de slots observados se distingue
del número total declarado; todavía no existe un contrato equivalente validado
de este último para las seis ondas. Las prestaciones de viudez se adjudican al
beneficiario del evento, no a quien generó originalmente el derecho.

Para cada cruce se separan $N_{\mathrm{total}}$, elegibilidad potencial,
respuestas conocidas y desconocidas. La prevalencia de rama cónyuge en toda
la muestra no equivale a la tasa entre personas con pareja elegible. Los
No operativos ante ausencia explícita de rama cónyuge residente se conservan;
no son respuestas brutas negativas ni prueban ausencia de prestaciones de
una pareja no residente. La categoría conjunta de negativas contiene esos
No derivados. Solo en 2018/2021 se confirma aquí el universo de pareja mediante
filtro y punteros; el universo temprano permanece desconocido. Una tasa dentro
de un grupo $g$ es
\begin{equation}
 r_g=\frac{\sum_{i\in g}\mathbb{1}(K_i=\mathrm{sí})}
 {\sum_{i\in g}\mathbb{1}(K_i\in\{\mathrm{sí},\mathrm{no}\})},
 \qquad
 c_g=\frac{\sum_{i\in g}\mathbb{1}(K_i=\mathrm{sí})}
 {\sum_i\mathbb{1}(K_i=\mathrm{sí})}.
 \label{eq:exploracion-tasa-composicion}
\end{equation}
El primer cociente expresa recepción entre respuestas conocidas dentro del
grupo y el segundo, composición del conjunto receptor. Ambos denominadores
son distintos y excluyen incertidumbre de manera explícita. Los universos de
los indicadores construidos se recuperan de la revisión B01, sin equipararlos
al universo exacto de cada pregunta bruta. Para salario principal se exige
orientación personal y filtro afirmativo de trabajo asalariado; los demás
registros no reciben salario cero. Los montos salariales con mes/año pendientes
no se convierten ni se agregan como ingreso total.

La edad se divide en 60--64, 65--69, 70--74, 75--79 y 80 o más. La escolaridad
inicial se agrupa en 0, 1--5, 6, 7--9 y 10 o más años; no se atribuye adquisición
educativa entre visitas. \texttt{urbano} distingue menos de 100 mil frente a
100 mil o más habitantes, no ruralidad estricta. \texttt{ocupacion} representa
condición de actividad y combina retiro, incapacidad y ausencia de trabajo
\citep[pp.~17--18, 58--59]{enasem2025simple}. El patrimonio es un stock del
entrevistado y su pareja, mientras la pensión se orienta individualmente; se
conservan ceros, negativos y cuantiles descriptivos sin construir un outcome.

La V de Cramér describe asociación categórica entre respuestas conocidas y
Spearman, relaciones de rangos compatibles con las escalas. Se conservan los
N válidos, exclusiones y celdas esperadas pequeñas. No se realizan pruebas
confirmatorias, no se afirma significancia y no se seleccionan relaciones por
una dirección esperada. Al explorar numerosos contrastes, la búsqueda de
patrones no equivale a confirmación de hipótesis. Los ponderadores y el diseño
permanecen sin validar para estos estimandos: los resultados describen la
muestra, no tasas nacionales. Las distribuciones monetarias son nominales y
se interpretan dentro de onda, sin crecimiento real ni suficiencia aprobada.

En seguimiento se parte de personas vivas de 60+ en origen y se conservan sus
perfiles iniciales. A diferencia de las matrices J02, una edad menor a 60 o
faltante en destino no elimina retrospectivamente la persona: se conserva el
estado pensionario documentado salvo entrevista sobre fallecido. No se corrige
la edad. Fallecimiento, ausencia con retorno posterior, ausencia sin retorno
observado y recepción desconocida permanecen separados. Los intervalos
nominales son dos, nueve y tres años. Solo se interpreta inicio, continuidad o
pérdida observada cuando los contratos son condicionadamente comparables;
no se infiere un cambio administrativo ni el efecto de una política.
'''
    write_project_text(chapters.joinpath('03_exploracion_pensionaria.tex'), method)
    prose=[r'\section{Exploración de pensiones con perfiles contemporáneos y seguimiento}',r'\label{sec:exploracion-resultados}',
     r'Esta ampliación responde a ocho cruces bivariados y ocho trivariados explícitos en cada ronda. El respaldo completo se organiza por solicitud y año en los notebooks 06b y 06c; los trivariados usan tres dimensiones simultáneamente. Los cuadros siguientes seleccionan resultados por relevancia sustantiva y cobertura, no por significancia. Todas las clasificaciones personales permanecen provisionales conforme a la auditoría anterior.',
     r'\subsection{Ramas pensionarias, instituciones y montos}',r'El cuadro~\ref{tab:exploracion-ramas} compara situaciones de las dos ramas entre rondas; el cuadro~\ref{tab:exploracion-instituciones} distingue fuente institucional de régimen.',r'\input{tablas/exploracion_ramas}']
    categories={z['categoria']:z['N'] for z in r['univariados']['2021']['titularidad']}
    prose += [f'En 2021, entre 10\\,482 personas observadas de 60+, {latex_number(categories["Solo propia"])} tienen solo pensión propia, '
      f'{latex_number(categories["Solo cónyuge"])} solo pensión del cónyuge y {latex_number(categories["Ambas"])} ambas ramas afirmativas. '
      f'Las negativas explícitas conjuntas suman {latex_number(categories["Ambas negativas K"])} y los estados conjuntos desconocidos {latex_number(categories["Desconocido"])}. '
      r'Estas categorías son exhaustivas, pero los desconocidos conjuntos pueden conservar una afirmativa propia: la recepción propia individual sigue siendo 3\,599, no la suma automática de dos categorías que exigen pareja conocida. La diferencia responde a denominadores de clasificación y no a una corrección de titularidad.',
      r'\input{tablas/exploracion_instituciones}',
      f'IMSS aparece en {latex_number(inst[0]["N_personas"])} personas, {latex_number(inst[0]["pct_receptoras_con_institucion"],2)}\\% de receptoras con al menos una institución identificada; '
      f'ISSSTE, en {latex_number(inst[1]["N_personas"])} ({latex_number(inst[1]["pct_receptoras_con_institucion"],2)}\\%). '
      r'Las selecciones no son excluyentes y no se suman como instituciones distintas por persona. La fuente de una prestación no determina por sí sola régimen, historial contributivo ni monto atribuible por institución. En 2012/2015, la selección identifica contingencia y no una correspondencia unívoca de institución con slot monetario.']
    types=r['univariados']['2021']['tipos_prestacion']
    prose += ['En 2021 se identifican '+', '.join(f'{latex_number(z["N_beneficiarios"])} beneficiarios de {escape_latex(z["tipo"].lower())}' for z in types)+
      r'. Las contingencias pueden coexistir en una persona. La viudez se describe según quien cobra la prestación; no se atribuye a esa persona el retiro que pudo haber generado el derecho de su pareja fallecida. El número observado de slots no acredita el número total declarado ni su comparabilidad histórica.']
    mount=next(z for z in old['montos'] if z['ano']==2021 and z['bloque']=='K')
    prose += [f'Los eventos pensionarios de 2021 tienen mediana mensual nominal de {latex_number(mount["mediana_nominal_mensual"],2)}, '
      f'con cuartiles {latex_number(mount["p25"],2)} y {latex_number(mount["p75"],2)}; '
      f'{latex_number(mount["N_monto_observado"])} de {latex_number(mount["N_eventos"])} eventos cuentan con monto válido. '
      r'La distribución corresponde a eventos de beneficiarios 60+, no al ingreso completo de todas las personas ni a una medida de suficiencia. Los importes permanecen separados por titular, contingencia y versión.']
    prose += [r'\subsection{Sexo, edad, educación y localidad}',r'El cuadro~\ref{tab:exploracion-edad} y la figura~\ref{fig:exploracion-b2-2021} muestran perfiles quinquenales; el cuadro~\ref{tab:exploracion-sexo-educacion} y la figura~\ref{fig:exploracion-t1-2021} examinan simultáneamente sexo, escolaridad y recepción.',r'\input{tablas/exploracion_edad_2021}',
      r'La desagregación quinquenal revela una diferencia que los grupos decenales resumían. En 2021, el apoyo es mucho menos frecuente entre 60--64 y 65--69 que entre 70--74; los denominadores de cada grupo figuran en el cuadro. La recepción K presenta un perfil diferente y no sigue mecánicamente la distribución del apoyo. Las listas de A cambian en 2021 y añaden vejez explícita: el patrón es compatible con diferencias de captación y elegibilidad histórica, pero no permite escoger una causa ni inferir un efecto de reforma.',
      r'\input{tablas/exploracion_sexo_educacion}']
    h6=cell('T1_2021','pension_propia_k',sexo_grupo='Hombre',educacion_grupo='6 años');m6=cell('T1_2021','pension_propia_k',sexo_grupo='Mujer',educacion_grupo='6 años')
    h10=cell('T1_2021','pension_propia_k',sexo_grupo='Hombre',educacion_grupo='≥10 años');m10=cell('T1_2021','pension_propia_k',sexo_grupo='Mujer',educacion_grupo='≥10 años')
    prose += [f'Al considerar sexo y escolaridad simultáneamente, la diferencia de recepción propia en seis años de educación es '
      f'{latex_number(h6["pct_si_conocido"]-m6["pct_si_conocido"],2)} puntos porcentuales: hombres {rate(h6)} y mujeres {rate(m6)}. '
      f'En diez o más años, hombres {rate(h10)} y mujeres {rate(m10)}, una diferencia de '
      f'{latex_number(h10["pct_si_conocido"]-m10["pct_si_conocido"],2)} puntos. '
      r'La heterogeneidad condicionada impide reducir el contraste agregado por sexo a una brecha uniforme. Tampoco demuestra que escolaridad explique causalmente la diferencia: cohorte, inserción laboral previa, supervivencia y cobertura siguen sin separarse.',
      r'Los cruces simultáneos edad--sexo, educación--localidad y edad--educación conservan todos los estratos, incluidos perfiles desconocidos. En 2021, entre hombres, la amplitud de tasas K por edad es mayor que entre mujeres; educación--localidad muestra un gradiente escolar en ambas categorías territoriales. La interpretación se apoya en tasas dentro de estratos, no en su composición entre receptoras. Las celdas pequeñas permanecen visibles y no se interpretan como confirmación de interacciones.']
    # Dos resultados trivariados adicionales vinculados a sus propios números.
    for key in ['T2_2021','T3_2021','T6_2021']:
        text=load(key)['interpretacion'].split('\n\n')[2]
        prose += [academic_latex(text)]
    prose += [r'\subsection{Actividad, pensiones y otras condiciones económicas}',r'El cuadro~\ref{tab:exploracion-actividad} resume dos cruces bivariados; la figura~\ref{fig:exploracion-t7-2021} condiciona simultáneamente por edad. El cuadro~\ref{tab:exploracion-patrimonio} mantiene la unidad compartida del stock.',r'\input{tablas/exploracion_actividad_sexo}']
    working=cell('B7_2021','pension_propia_k',ocupacion_grupo='Trabaja')
    prose += [f'La actividad y la recepción no son excluyentes: {rate(working)} de las respuestas K conocidas entre quienes trabajan son afirmativas. '
      r'La categoría que agrupa retiro, incapacidad y no trabajo registra mayor recepción que trabajo o labores del hogar, pero su definición no identifica pensionados por sí misma. La simultaneidad de trabajo y pensión abre una pregunta sobre complementariedad de fuentes, no sobre un efecto pensionario en la participación laboral.',
      academic_latex(load('T7_2021')['interpretacion'].split('\n\n')[2]),
      r'\input{tablas/exploracion_patrimonio}']
    rho=load('B8_2021')['spearman'][0]
    prose += [f'El rango de patrimonio y el monto pensionario propio mensual observado parcial muestran Spearman '
      f'$\\rho={latex_number(rho["rho_spearman"],4)}$, con {latex_number(rho["N_pares_validos"])} pares válidos en 2021. '
      r'La relación no identifica acumulación causada por pensiones ni representa igualdad de unidades de análisis: patrimonio puede corresponder a una pareja y el monto se orienta al sujeto. La diferencia de medianas entre ramas se mantiene como descripción de composición, sin convertir cuartiles en vulnerabilidad.',
      academic_latex(load('T8_2021')['interpretacion'].split('\n\n')[2]),
      r'La recepción salarial se estudia en 1\,172 personas con rama propia y filtro asalariado principal confirmado en 2021. Entre quienes declaran salario, K propia es afirmativa en 229/988 respuestas conocidas (23,18\%); entre negativas salariales explícitas, 39/180 (21,67\%). Otros cuatro registros tienen respuesta salarial desconocida. Los 9\,310 sin filtro confirmado no se convierten en ingreso cero. Esta comparación utiliza recepción de una fuente específica: la homologación del monto mes/año y el ingreso total siguen pendientes.',
      r'Los cruces complementarios con salud autopercibida, diabetes, síntomas depresivos, ABVD y recuerdo verbal conservan asociaciones débiles y excluidos por cobertura. Cada indicador mantiene su escala y universo; no se equiparan síntomas con diagnóstico ni cognición con salud global. Estos resultados orientan preguntas adicionales, sin desplazar la exploración pensionaria ni establecer que una prestación mejore salud.']
    couple=next(z for z in r['universos_conyuge'] if z['ano']==2021)
    prose += [f'El universo de pareja confirmado en 2021 contiene {latex_number(couple["N_elegible_pareja_confirmado"])} personas; '
        f'{latex_number(couple["N_sin_pareja_residente_explicita"])} tienen ausencia explícita de rama cónyuge residente. '
        'Entre las parejas confirmadas, la recepción del cónyuge por sexo es '+
        '; '.join(escape_latex(z['sexo_grupo'])+' '+rate(z) for z in couple['recepcion_conyuge_en_parejas_por_sexo'])+
        r'. Son tasas dentro de este universo, distintas de la prevalencia sobre toda la muestra. Los universos tempranos no se infieren a partir de No operativos ni estado conyugal.']
    gap=next(z for z in old['brechas_apoyo'] if z['ano']==2021)
    prose += [r'\subsection{Coexistencia con apoyos y exploración longitudinal}',
      r'Los cuadros anteriores de protección documentan K\(\times\)A por sexo y localidad; se reutilizan y no se repite la integración. En 2021 coexisten K y A en 2\,019 personas y se observa A con negativa K en 3\,558. V de Cramér es 0,0376 en 10\,396 pares conocidos: esta asociación débil no elimina la coexistencia ni demuestra complementariedad o sustitución de prestaciones. Los apoyos se presentan también entre receptoras K; no se infiere reducción de desigualdad o expansión causal a partir de esa distribución.',
      academic_latex(load('T4_2021')['interpretacion'].split('\n\n')[2]),
      academic_latex(load('T5_2021')['interpretacion'].split('\n\n')[2]),
      r'El cuadro~\ref{tab:exploracion-correspondencias} identifica el proceso de observación que condiciona las transiciones.',r'\input{tablas/exploracion_correspondencias}',
      r'La correspondencia del panel distingue personas presentes, entrevistas sobre fallecidos y ausencias. El seguimiento se estratifica por sexo, edad quinquenal, escolaridad y localidad en origen. La observación posterior selecciona la población de pares con recepción conocida; una tasa de inicio entre esos pares no es una incidencia nacional ni una probabilidad incondicional de toda la cohorte. Los intervalos desiguales impiden comparar conteos de inicio como si fueran tasas anuales.']
    for key in ['L_A_entre_negativas_K_2015_2018','L_conjunta_K_A_2012_2015']:
        prose += [academic_latex(r['seguimiento'][key]['interpretacion'])]
    prose += [r'Las transiciones propias, del cónyuge y conjuntas se interpretan únicamente bajo comparabilidad condicionada. K2003--2012 y K2015--2018, así como A2001--2003 y A2018--2021, mantienen rupturas de instrumento: sus matrices registran estados documentados, no pérdida o inicio homogéneos. No se infiere muerte de la ausencia ni se completa desconocimiento con cero. Los pendientes J1/2001, punteros, 33 firmas2015, clasificación institucional, apoyos mixtos, pesos y precios permanecen abiertos.',
      r'\subsection{Conclusiones parciales}',
      r'La ampliación muestra que una clasificación pensionaria única pierde información sobre rama familiar, institución, contingencia y cobertura. Las tasas por edad, escolaridad y actividad presentan patrones diferentes de los apoyos; los contrastes condicionados revelan heterogeneidad que los promedios marginales ocultan. La asociación K/A débil y la coexistencia de trabajo y recepción requieren explicación adicional, sin forzar una narrativa de sustitución o retiro. Los datos sostienen preguntas sobre cobertura y trayectorias, pero todavía no una definición definitiva de vulnerabilidad ni un modelo. La matriz de cumplimiento distingue ejecución provisional, análisis parcial y comparaciones no viables.']
    selected=[('B2_2021','Distribución de recepción K y A por edad quinquenal. Tasas entre respuestas conocidas; sin ponderar.'),
              ('T1_2021','Pensión propia, del cónyuge y apoyo por sexo y escolaridad simultáneamente. Porcentajes dentro de cada perfil entre respuestas conocidas; escolaridad desconocida se conserva.'),
              ('T7_2021','Recepción pensionaria por condición de actividad y edad simultáneamente. Categorías originales de actividad, sin inferencia causal.')]
    for key,caption in selected:
        shutil.copy2(project_path('', r['analisis'][key]['figura']),figures/f'exploracion_{key}.png')
        prose += [r'\begin{figure}[p]\centering\includegraphics[width=0.96\textwidth,height=0.72\textheight,keepaspectratio]{figuras/borradores/exploracion_'+key+'.png}'+
                  r'\caption{'+escape_latex(caption)+r'}\label{fig:exploracion-'+key.lower().replace('_','-')+r'}\end{figure}']
    write_project_text(chapters.joinpath('04_exploracion_pensionaria.tex'), '\n\n'.join(prose)+'\n')
    # Preguntas abiertas, cada una anclada a resultados concretos.
    questions=[('Q1','¿Cómo difiere la recepción propia y del cónyuge por sexo y escolaridad inicial?',
       'T1_2021: brecha propia de '+f'{h6["pct_si_conocido"]-m6["pct_si_conocido"]:.2f} pp en 6 años y {h10["pct_si_conocido"]-m10["pct_si_conocido"]:.2f} pp en ≥10 años.',
       'K propia/cónyuge, sexo, escolaridad inicial, edad, estado conyugal.',
       'Perfiles transversales seis rondas; trayectorias condicionadas K2001–2003/2012–2015/2018–2021.',
       'Validar J1/2001, filtros de pareja, selección y antecedente laboral. Descriptiva estratificada; econométrica asociacional tras fijar estimando; predicción solo futura y opcional.'),
      ('Q2','¿En qué perfiles coexisten pensiones K y apoyos, y cómo varía la coexistencia con la edad?',
       '2021: 2,019 K+A; 3,558 A con negativa K; V=0.03756 y tasas de A muy diferentes por edad quinquenal.',
       'K/A propios, edad, sexo, escolaridad, localidad; programa explícito cuando existe.',
       'Cortes seis rondas con contratos separados; recepción conjunta 2012–2015 condicionada; A2018–2021 no homologado.',
       'No llamar sin pensión a negativa K ni todo A no contributivo; separar dinero/especie requeriría fuente adicional. Descriptiva/econométrica sin causalidad por defecto.'),
      ('Q3','¿Qué continuidad e inicio de apoyo se observa entre personas con negativa K inicial?',
       r['seguimiento']['L_A_entre_negativas_K_2015_2018']['interpretacion'],
       'K en origen, A en ambos momentos, perfiles iniciales, seguimiento y modalidades.',
       'A2003–2012/2012–2015/2015–2018 condicionados; intervalos nominales desiguales.',
       'Necesita examinar selección de pares conocidos, retornos, muerte y sensibilidad. Descriptiva panel; modelo de transición asociacional si se define proceso de observación y estimando.'),
      ('Q4','¿Cómo se combinan recepción pensionaria y trabajo durante el envejecimiento?',
       f'2021: {working["N_si"]:,}/{working["N_conocido"]:,} ({working["pct_si_conocido"]:.2f}%) K propia entre quienes trabajan; T7 presenta heterogeneidad por edad.',
       'Ocupación construida, edad, K propia/cónyuge, salario principal en elegibles, instituciones.',
       'Actividad en seis ondas; recepción K longitudinal solo en periodos compatibles.',
       'Ocupación no profesión; retiro/incapacidad/no trabajo no separables. Validar saltos y periodos salarial/pensionario. Descripción de perfiles y transiciones; econometría asociacional, no efecto retiro.'),
      ('Q5','¿Qué diferencias institucionales aparecen entre receptoras según escolaridad y localidad?',
       f'2021: IMSS {inst[0]["N_personas"]:,}/{inst[0]["N_receptoras_institucion_identificada"]:,}; instituciones múltiples no aditivas. C1/C2 usan perfiles simultáneos.',
       'Instituciones fuente, contingencia, sexo, edad, educación, localidad, titularidad.',
       'Seis cortes por instrumento; cambios institucionales individuales requieren homologación adicional, especialmente2012/2015.',
       'Fuente no régimen y código ambiguo permanece desconocido. No asignar monto por institución cuando selección por contingencia. Descriptiva; transición institucional pendiente, no entrenar un modelo.'),
      ('Q6','¿Cómo varía la asociación de monto pensionario propio y patrimonio compartido por escolaridad?',
       f'2021: Spearman {rho["rho_spearman"]:.4f} en {rho["N_pares_validos"]:,} pares; T8 distribuye patrimonio simultáneamente por ramas y educación.',
       'Patrimonio, monto K parcial, escolaridad, tipo/slot, titular y pareja.',
       'Distribuciones internas a seis rondas; cambio real no disponible hasta validar moneda/precios y unidad compartida.',
       'No vulnerabilidad por cuartil, no ingreso total y no acumulación causal. Descriptiva actual; longitudinal monetaria pendiente de deflactor y consistencia de unidad.')]
    text=['# Preguntas potenciales derivadas del EDA\n\nNinguna se adopta como pregunta definitiva, outcome o hipótesis. La alerta temprana queda como antecedente y línea futura opcional; no organiza obligatoriamente esta etapa.']
    qtex=[r'\section{Posibles líneas de investigación derivadas de los hallazgos}',r'\label{sec:exploracion-preguntas}',
      r'Las siguientes líneas se derivan de los agregados observados y permanecen abiertas. Su prioridad depende de interés sustantivo, cobertura y validación, no de seleccionar un outcome predeterminado. No se estima un modelo ni se aprueba una pregunta definitiva.']
    for code,q,why,variables,waves,limits in questions:
        text += [f'## {code}. {q}',f'**Resultado que motiva:** {why}',f'**Variables:** {variables}',f'**Rondas y longitudinalidad:** {waves}',f'**Validaciones y viabilidad:** {limits}']
        qtex += [r'\subsection{'+escape_latex(q)+'}',academic_latex('Resultado que motiva: '+why),
                 escape_latex('Variables y rondas: '+variables+' '+waves),escape_latex('Viabilidad: '+limits)]
    write_project_text(PUBLIC/'PREGUNTAS_POTENCIALES.md', '\n\n'.join(text)+'\n')
    write_project_text(chapters.joinpath('05_preguntas_exploratorias.tex'), '\n\n'.join(qtex)+'\n')
    checked_hashes();print('Cuadros, narrativa y preguntas derivados de agregados; fuentes originales preservadas.')


if __name__=='__main__':export()
