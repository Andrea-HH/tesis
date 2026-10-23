"""Matriz conceptual propuesta: evidencia física comprobada, sin armonizar microdatos."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text
import json
from pathlib import Path
from export_pension_review import md_table
from tesis_enasem.manuscript import escape_latex

ROOT = Path(__file__).resolve().parents[1]
YEARS = [2001, 2003, 2012, 2015, 2018, 2021]
NAMES = ['pension_contributiva','pension_no_contributiva','otro_apoyo_publico','ayuda_familiar',
         'ingreso_pension_contributiva','ingreso_pension_no_contributiva',
         'ingreso_transferencias_publicas','ingreso_total']
# Estados de identificabilidad documental, no conteos de receptores ni variables calculadas.
STATES = [
 ['C']*6,
 ['T','T','P','P','T','E'],
 ['P','P','P','P','C','C'],
 ['T','T','C','C','C','C'],
 ['C']*6,
 ['T','T','P','P','T','C'],
 ['C']*6,
 ['R','R','R','D','R','R'],
]
LIMITS = [
 'Recepción e institución permiten casos identificados; no declarar 0 con modalidades o fuentes desconocidas.',
 'T: apoyo agregado sin identificación específica; P: categoría federal/estatal conjunta en K59/K65; E: opción explícita en 2021. No equivale a cobertura íntegra.',
 '«Otra institución» y ayudas sin tipo permanecen desconocidas; excluir especie de ingresos monetarios.',
 'G permite parentesco desde 2012; en 2001/2003 transferencias de personas no prueban ayuda familiar.',
 'Monto y titular propios/cónyuge requieren orientación; totales pens_t e inc_pension mezclan fuentes potenciales.',
 '2012/2015 pueden agrupar instituciones en un mismo monto; 2021 hasta dos apoyos por fuente, validar periodo.',
 'No usar tran_t/inc_trans como total público: pueden incluir transferencias privadas o de propiedades.',
 'D solo presencia de income_15 del proveedor, sin aprobación de unidad; R requiere reconstrucción validada o producto total separado. No sustituir por imp_neto.',
]


def export_availability() -> dict:
    """Verifica nombres candidatos y exporta disponibilidad por concepto y ronda."""
    audit = json.loads(read_project_text(project_path('', 'docs/pensiones/inventario_fuentes.json')))
    files = {s['archivo']: s for s in audit['fuentes']}
    fields = audit['variables']
    out = project_path('', 'docs/pensiones')
    rows=[]
    for index, concept in enumerate(NAMES):
        for year in YEARS:
            suffix = str(year)[-2:]
            original = 'sect_k.dta' if year == 2001 else 'sect_k (1).dta' if year == 2003 else f'sect_g_j_k_sa_{year}.dta'
            individual = f'sect_k_ind_{year}.dta' if year != 2018 else 'Sect_K_ind_2018.dta'
            # Grupos de pregunta diferentes según la ola; no sustitución mecánica de sufijos.
            own_receive = ['k55a','k56_'] if year == 2001 else ['k58a','k59']
            own_public = ['k76a','k77_'] if year == 2001 else ['k79a','k80']
            own_money = ['k58_'] if year == 2001 else ['k61']
            group = own_receive if index == 0 else own_receive+own_public if index == 1 else own_public if index in [2,6] else ['g17','g18','g24','g25'] if index == 3 else own_receive+own_money if index == 4 else own_receive+own_public+own_money if index == 5 else ['k11','k25','k36','k47','k50']
            evidence=[]
            for file in [original, individual]:
                selected = [v for v in fields if v['archivo']==file]
                for v in selected:
                    n=v['variable']
                    physical = any(n.startswith(p) for p in group) if file == original else (
                        (index in [0,4] and (n.startswith('pens_') or n.startswith('inc_pension') or n.startswith('imamk61') or n.startswith('imam55') or n.startswith('imam58')))
                        or (index in [1,2,5,6] and (n.startswith('imamk80') or n.startswith('imam76a') or n.startswith('imam79a') or n.startswith('tran_') or n.startswith('inc_trans')))
                        or (index==3 and n.startswith('inc_family'))
                        or (index==7 and n.startswith(('income_','inc_','earn_','pens_','tran_'))))
                    if physical:
                        evidence.append({'fuente_id':files[file]['fuente_id'],'archivo':file,
                                         'variable':n,'etiqueta':v['etiqueta']})
            rows.append({'variable_armonizada':concept,'ronda':year,'estado_propuesto':STATES[index][YEARS.index(year)],
                         'evidencia_columnas':evidence,'limite':LIMITS[index],
                         'construida':False,'verificacion_semantica':'Titular, filtros, unidad y periodo pendientes por pregunta'})
    result={'fecha':'2026-10-12','periodo':YEARS,'estados':{
        'C':'Candidata condicionada a fuente, titular, filtros y periodo',
        'P':'Identificación parcial de tipo; programa/ámbito o monto no separable todavía',
        'T':'Solo agregado o fuente sin tipo/parentesco suficiente',
        'E':'Existe opción explícita de programa; no recepción armonizada ya construida',
        'D':'Total del proveedor físicamente disponible; definición pendiente',
        'R':'Necesita reconstrucción validada o archivo adicional'},'disponibilidad':rows,
        'separado_2024':'Fuentes y códigos revisados separadamente; sin persona-ronda 2024 en ENASEMsimple proporcionado'}
    write_project_text(out/'disponibilidad_armonizadas.json', json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    text='# Disponibilidad y comparabilidad por ronda\n\nLa presencia física se comprobó en las 20 fuentes. Esta matriz evalúa **posibilidad de identificación**, no prevalencia ni equivalencia final. Las ocho variables todavía no se han construido. Las evidencias exactas, incluidos montos y derivados, se conservan en disponibilidad_armonizadas.json; los nombres de las fuentes corresponden a INVENTARIO_CONSOLIDADO.md.\n\n'
    text+=md_table(['Variable propuesta']+[str(y) for y in YEARS]+['Restricción'],[[n]+s+[l] for n,s,l in zip(NAMES,STATES,LIMITS)])+'\n'
    text+='\n'.join('- **'+k+'**: '+v+'.' for k,v in result['estados'].items())+'\n\n'
    for year in YEARS:
        text+=f'## Ronda {year}: evidencia por concepto\n\n'
        text+=md_table(['Variable','Estado','Columnas candidatas verificadas, sin sustituir el diccionario completo'],[
            [r['variable_armonizada'],r['estado_propuesto'],'; '.join(f"{v['fuente_id']}: `{v['variable']}`" for v in r['evidencia_columnas']) or 'No identificadas con los grupos documentados']
            for r in rows if r['ronda']==year])+'\n'
    dimensions=[
      ['Recepción pensionaria y contingencia','K55a–d (2001) / K58a–d (2003+)','Candidata conceptual propia/cónyuge','Revisar respuesta de supervivencia/invalidez y régimen, no solo jubilación'],
      ['Institución pensionaria','K56 (2001), K59/K65 (2003+)','Condicionada; cambia respuesta múltiple y número de pensiones','2012/2015 incluyen programas federales/estatales; 2018/2021 no repiten esa categoría en K59'],
      ['Inicio de recepción','K57 (2001), K60 (2003+) y cónyuge','Candidata si declarado y orientación válida','No atribuir a todos los apoyos K79; censura izquierda y desconocidos'],
      ['Pensión futura/expectativas','Preguntas de pensión futura etiquetadas en cada K','Comparar expectativas por separado','K75 de 2018 incluye programas públicos futuros; no demuestra recepción actual'],
      ['Trabajo y remuneraciones','K44/K47 y cónyuge; earn_t/inc_earned/imam','Concepto general con unidad y titular pendientes','Trabajo principal/secundario, distintos códigos y periodicidades'],
      ['Negocios, ingresos y gastos','K1–K16, am/imam, inc_business_15','Comparar componente tras cotejo por ola','Hogar/pareja; hasta dos negocios; ingresos brutos no utilidad neta'],
      ['Propiedades y renta','K y J: tenencia, valor, deuda, renta y gastos','Componentes separados, universo y precios pendientes','No confundir venta de propiedad/herencia con ingreso recurrente'],
      ['Capital, ahorros, acciones y deuda','K de activos financieros, rangos, am/imam','Conceptos generales; no montos nominales directamente','Valores de stock, flujos y umbrales de brackets cambian'],
      ['Donativos públicos y privados','K76/K79/K82 y montos de fuentes','Tipo parcial; códigos cambian entre rondas','2018/2021 cambian programas; 2024 K79 código 2 cambia nuevamente'],
      ['Apoyo familiar monetario/en especie','G en combinados 2012–2021; inc_family_15','2012+ candidato; K temprano no identifica siempre parentesco','G refiere dos años y puede incluir pareja; separar ayudas recibidas/dadas y horas de ayuda'],
      ['Vivienda y entorno','J en combinados 2012–2021','Módulo físico disponible; comparabilidad por pregunta pendiente','Vivienda/hogar; no adjudicar cada activo íntegro a ambos cónyuges'],
      ['Gasto/autoconsumo/inseguridad alimentaria','K85 (2001), K88 (2003+) y K90/K92 donde figuran','Comprobar periodo y categorías por ola','No equivalen a ingreso; algunos módulos solo aparecen en ciertas fuentes'],
      ['Información económica de fallecimiento','SA y gastos asociados en combinados','Separada de mediciones de participantes vivos','No llamar entrevistas directas ni usar información posterior como predictor previo'],
      ['Patrimonio construido','imp_neto en ENASEMsimple','Referencia CP1 conservada; unidad pareja y precios pendientes','Ingreso y patrimonio no intercambiables; productos separados no suministrados'],
      ['Monto reportado/derivado/imputado y banderas','Original, am, imam, imp/dum de cada archivo','Comparar solo misma clave, titular y referencia','No sumar versiones; 2018 hogar imputado no suministrado; 2021 puede reutilizar información 2018'],
    ]
    text+='## Dimensiones sustantivas adicionales: comparabilidad a revisar\n\nLa matriz exhaustiva contiene **todas las columnas**, incluidas G/J/SA, rangos, montos, banderas y agregados. El cuadro siguiente organiza conceptos y no autoriza a descartar variables que no encajen en una fila. Una equivalencia completa de cada pregunta requiere su instrumento y se mantiene pendiente, explícitamente, en el diccionario.\n\n'+md_table(['Dimensión','Evidencia por familia','Comparabilidad propuesta','Límite'],dimensions)
    text+='\n## Cambios críticos documentados\n\nEn 2012/2015, K59/K65 opción 08 agrupa programas federales/estatales y no acredita un nombre individual. En 2018, K79 incluye PROAGRO, PROSPERA, INAPAM y otra institución: no existe allí una categoría explícita de pensión federal de vejez. En 2021, K79a_1 y K82c_1 incorporan opción 5 para Bienestar de personas adultas mayores. Esa opción no vuelve retrospectivamente identificables los apoyos previos. Las preguntas K79/K82 originales y sus imam deben orientarse con el informante/cónyuge. La documentación de ingreso total de 2018/2021 existe, pero esos productos separados no están entre los archivos disponibles.\n\nNo se declara equivalencia final entre dos columnas por retirar el año o coincidir su etiqueta. Las ocho columnas propuestas necesitan universos de pregunta y valores válidos, no solamente nombres disponibles. Faltan cotejos completos de cuestionarios y códigos tempranos, causas de discrepancia de universos y unidades de los agregados.\n\n2024 conserva sus 507 columnas en la matriz completa, pero no integra esta tabla de seis rondas. En K79 las opciones incluyen pensión de vejez, discapacidad y ONG; revisar instrumento y naturaleza pública/privada antes de construir conceptos.\n'
    write_project_text(out/'DISPONIBILIDAD_RONDAS.md', text)
    tex = r"""\begin{table}[htbp]
\centering\small\singlespacing
\caption{Identificabilidad propuesta de los ocho conceptos económicos}\label{tab:pensiones_disponibilidad}
\begin{tabular}{p{5.1cm}cccccc}
\toprule Concepto & 2001 & 2003 & 2012 & 2015 & 2018 & 2021 \\
\midrule
"""
    for n, states in zip(NAMES, STATES):
        tex += escape_latex(n.replace('_', ' '))+' & '+' & '.join(states)+r' \\'+"\n"
    tex += r"""\bottomrule\end{tabular}
\par\medskip\begin{minipage}{\textwidth}\footnotesize
C: candidata condicionada; P: tipo parcial; T: agregado sin identificación suficiente; E: opción explícita de programa; D: total disponible del proveedor; R: reconstrucción o archivo adicional. No son resultados de recepción ni variables ya armonizadas.
\end{minipage}\end{table}
"""
    write_project_text(project_path('', 'manuscrito/tablas/pensiones_disponibilidad.tex'), tex)
    return result

if __name__=='__main__':
    from tesis_enasem.release_guard import block_legacy_export
    block_legacy_export()
    print('Matriz exportada:',len(export_availability()['disponibilidad']),'concepto-ronda; ninguna variable integrada.')
