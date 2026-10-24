"""Versión pública10: corrige soporte antes de proteger familias de resultados.

Los originales completos están bajo data/interim/.../privado. No hay operación
Git ni modificación de microdatos. La propuesta pública se genera por lista.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from markdown_it import MarkdownIt

from .project_paths import PROJECT_ROOT as ROOT
from .statistical_quality import OUT, ORIGINAL, digest, n_band
from .economic_protection import save_json
from .disclosure_quality import protect_rows, redact_financial_paragraphs
from .publication import assert_no_direct_disclosure, sanitize_local_paths


def fmt(value: float|int|None,decimals: int=1) -> str:
    """Formato único; ND nunca se rellena con0."""
    return 'ND' if value is None else f'{value:,.{decimals}f}'


def counts(n: int,protected: bool=False) -> str:
    """Denominador, no estimación; las celdas sensibles pequeñas no se precisan."""
    return '<10' if protected and 0<n<10 else f'{n:,}'


def ci(row: dict,key: str='ic95_folio',scale: float=1) -> str:
    """No imprime un contraste que el análisis declaró no estimable."""
    x=row.get('estimacion');bounds=row.get(key)
    if x is None or bounds is None:
        return 'No estimable'
    return f'{fmt(x*scale)} [{fmt(bounds[0]*scale)}; {fmt(bounds[1]*scale)}]'


def md_table(headers: list[str],rows: list[list[Any]]) -> str:
    """Tabla real Markdown, no HTML con cifras ocultas."""
    return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+'\n'.join('| '+' | '.join(str(v).replace('|',' / ') for v in row)+' |' for row in rows)+'\n'


def esc(value: Any) -> str:
    """Caracteres compatibles con ambos motores LaTeX del proyecto."""
    return str(value).replace('&',r'\&').replace('%',r'\%').replace('_',r'\_').replace('–','--').replace('−','-').replace('→',r'$\to$').replace('≥',r'$\geq$').replace('<',r'$<$')


def latex_table(name: str,title: str,headers: list[str],rows: list[list[Any]],note: str,*,label: str|None=None,align: str|None=None) -> None:
    """Cuadro protegido con título, encabezado repetido, unidad y fuente."""
    n=len(headers);align=align or 'l'+'r'*(n-1)
    header=' & '.join(esc(v) for v in headers)+r' \\'
    text=r'\begingroup\small\setlength{\tabcolsep}{3pt}'+'\n'+r'\begin{longtable}{'+align+'}\n'
    text+=r'\caption{'+title+r'}\label{'+(label or 'tab:calidad-'+name)+r'}\\'+'\n'+r'\toprule'+'\n'+header+'\n'+r'\midrule\endfirsthead'+'\n'+r'\multicolumn{'+str(n)+r'}{l}{Continuación del cuadro \thetable}\\'+'\n'+r'\toprule'+'\n'+header+'\n'+r'\midrule\endhead'+'\n'+r'\bottomrule\endfoot'+'\n'
    text+='\n'.join(' & '.join(esc(v) for v in row)+r' \\' for row in rows)+'\n'+r'\end{longtable}'+'\n'+r'{\footnotesize '+esc(note)+r'\par}'+'\n'+r'\endgroup'+'\n'
    (ROOT/'manuscrito/tablas'/name).with_suffix('.tex').write_text(text)


def clean_tex_rows(text: str,name: str) -> tuple[str,list[dict]]:
    """Censura solo filas con N/estadístico trazable; mantiene labels y captions."""
    lines=text.splitlines();headers=[];log=[]
    for i,line in enumerate(lines):
        if '&' not in line or not '\\\\' in line or '\\caption' in line:
            continue
        cells=[x.strip() for x in line.split('\\\\')[0].split('&')]
        if any(re.search(r'(^|\s)N(\s|$)|N válido|N P/C',x) for x in cells) or any('Vía/ventana' in x for x in cells):
            headers=[re.sub(r'\\[A-Za-z]+|[{}]','',x) for x in cells]
            continue
        if len(cells)!=len(headers) or not headers:
            continue
        output,decisions=protect_rows(headers,[cells],context=name+' '+text[:600])
        if decisions:
            lines[i]=' & '.join(output[0])+r' \\'
            log.append(dict(archivo=name,linea=i+1,decision=decisions[0]['motivo']))
    return '\n'.join(lines)+'\n',log


def markdown_blocks(text: str) -> list[dict]:
    """Recupera todos los valores para convertirlos, sin guardarlos en el censo público."""
    tokens=MarkdownIt('commonmark',{'html':True}).enable('table').parse(text)
    result=[];title='';i=0
    while i<len(tokens):
        if tokens[i].type=='heading_open':title=tokens[i+1].content
        if tokens[i].type=='table_open':
            span=tokens[i].map;rows=[]
            while tokens[i].type!='table_close':
                if tokens[i].type=='tr_open':rows.append([])
                elif tokens[i].type=='inline':rows[-1].append(tokens[i].content)
                i+=1
            result.append(dict(start=span[0],end=span[1],headers=rows[0],rows=rows[1:],title=title))
        i+=1
    return result


def protect_markdown(text: str) -> tuple[str,list[dict]]:
    """Aplica a todos los cuadros, no solo4.14; deriva la decisión del N válido."""
    lines=text.splitlines();log=[]
    for block in reversed(markdown_blocks(text)):
        rows,decisions=protect_rows(block['headers'],block['rows'],context=block['title'])
        if decisions:
            lines[block['start']:block['end']]=md_table(block['headers'],rows).rstrip().splitlines()
            log.extend(dict(linea_original=block['start']+1,**d) for d in decisions)
    text,paragraphs=redact_financial_paragraphs('\n'.join(lines)+'\n')
    log.append(dict(parrafos_financieros_retirados=paragraphs))
    return text,log


def replace_between(text: str,start: str,end: str,replacement: str) -> str:
    """Exige límites inequívocos en fuentes congeladas; nunca edición por intuición."""
    a=text.index(start);b=text.index(end,a)
    return text[:a]+replacement+text[b:]


def quality_tables(audit: dict) -> tuple[dict,str]:
    """Resultados de calidad y reformulación; no se transcriben cifras privadas."""
    all_tables={};markdown=[]
    source='Fuente: auditoría10, insumos01--09 intactos. Muestra sin ponderación; IC condicionales, sin inferencia nacional o causal. P: primera vía observada; C: otra vía basal afirmativa.'
    def table(name,title,headers,rows,note=source,align=None):
        latex_table(name,title,headers,rows,note,align=align)
        all_tables[name]=r'\input{tablas/'+name+'}\n'
        markdown.append('#### '+title+'\n\n'+md_table(headers,rows)+'\n'+note+'\n')
    rows=[]
    for w in audit['robustez']:
        x,y=w['monetario'];order=x.get('intervalo_orden_independencia')
        review='Sin soporte direccional' if min(x['N'])<30 else 'Condicional; empates' if x.get('ic95_folio')==[0.,0.] else 'Medianas coincidentes' if x.get('estimacion')==0 else 'Dirección cruda estable'
        ordertext='No estimable' if order is None else f'[{fmt(order[0])}; {fmt(order[1])}]'
        rows.append([f"{w['via']} {w['origen']}--{w['destino']}",'/'.join(counts(n) for n in x['N']),'No confiable' if x['estado'].startswith('No estimable con confiabilidad') else '['+fmt(x['ic95_folio'][0])+'; '+fmt(x['ic95_folio'][1])+']','No confiable' if y['estado'].startswith('No estimable con confiabilidad') else '['+fmt(y['ic95_folio'][0])+'; '+fmt(y['ic95_folio'][1])+']',review])
    table('tesis_calidad_precision','Precisión monetaria P menos C y estabilidad de remuestreo',['Vía/ventana','N P/C','IC semilla1','IC semilla2','Evaluación'],rows,source+' 9999 réplicas por folio y dos semillas. Se muestran estimación e IC. Los intervalos por orden e influencia están en el informe. La diferencia K2001--2003 no se usa como conclusión direccional aunque pueda calcularse.',align='lrrrp{.21\\textwidth}')
    rows=[]
    for w in audit['robustez']:
        x=next(z for z in w['ajustes'] if (z['estimando'],z['edad_grupos'],z['minimo_celda'])==('tasa',3,20))
        y=next(z for z in w['ajustes'] if (z['estimando'],z['edad_grupos'],z['minimo_celda'])==('tasa',2,30))
        rows.append([f"{w['via']} {w['origen']}--{w['destino']}",ci(x,'ic95',100),ci(y,'ic95',100),'/'.join(counts(n) for n in y['N_soporte'])])
    table('tesis_calidad_gradiente','Sensibilidad del gradiente patrimonial de incorporación',['Vía/ventana','Edad3/celda20 pp','Edad2/celda30 pp','N soporte Q1/Q4'],rows,source+' Q1 menos Q4 entre negativas K/A reobservadas; sexo y escolaridad se mantienen. Edad2=60--69/70+, edad3=60--64/65--69/70+. Cambian soporte y mezcla, no es la misma población. Todas las cuatro especificaciones están en el informe; no se elige por significancia.')
    rows=[]
    for x in audit['patrimonio_mitades']:
        small=min(x['N'])<10
        med=x.get('estadisticas',[])
        rows.append([f"{x['via']} {x['origen']}--{x['destino']}",x['patrimonio'].replace('Mitad ','').capitalize(),
            'Sin soporte' if small else '/'.join(counts(n) for n in x['N']),
            'Reservado' if small else fmt(med[0]['mediana']),
            'Reservado' if small else fmt(med[1]['mediana']),ci(x)])
    latex_table('tesis_central_patrimonio_monto','Monto posterior por mitad patrimonial y protección basal',
        ['Vía/ventana','Mitad','N P/C','Mediana P','Mediana C','P-C [IC95]'],rows,
        source+' Reformulación común Q1+Q2/Q3+Q4, manteniendo población, titularidad, ventanas y precios. 4999 réplicas por folio. K2001--2003 sigue sin soporte; retirar conjuntamente ambas mitades y derivados impide recuperar un importe mediante otra rama. No se escogió la agrupación por significancia.',label='tab:central-patrimonio_monto')
    markdown.append('#### Monto posterior por mitad patrimonial y protección basal\n\n'+md_table(['Vía/ventana','Mitad','N P/C','Mediana P','Mediana C','P-C [IC95]'],rows)+'\n'+source+' Se conserva la evaluación por cuartiles en privado; la simplificación no rescata la ventana escasa.\n')
    rows=[]
    for z in audit['T8_reformulado']['grupos']:
        if z['estadisticas'] is None:continue
        s=z['estadisticas'];rows.append([z['titularidad'],z['escolaridad'],counts(z['N_valido']),fmt(s['q25']/1000),fmt(s['mediana']/1000),fmt(s['q75']/1000)])
    table('tesis_calidad_T8','Reformulación del contexto patrimonial por escolaridad y titularidad,2021',
        ['Titularidad K','Esc. años','N','Q25','Mediana','Q75'],rows,
        'Fuente: EDA original60+ por visita, incluidas modalidades originales; no es la población principal directa09. Patrimonio compartido, miles de unidades almacenadas, no pesos reales. Escolaridad0--5/6+; titularidad o escolaridad ND quedan como exclusiones. Se presentan todos los grupos, no máximos seleccionados.',align='lrrrrr')
    rows=[]
    for w in audit['robustez']:
        for x in w['instituciones']:
            n=min(x['N']);status=x['estado']
            rows.append([f"{w['via']} {w['origen']}--{w['destino']}",x['institucion'],
                '/'.join(counts(v,True) for v in x['N']),
                'No estimable' if x['estado'].startswith('No estimable con confiabilidad') else ci(x),
                'No confiable' if x['estado'].startswith('No estimable con confiabilidad') else 'Exploratorio 10–29' if n<30 else 'Sin equivalencia' if x.get('ic95_folio')==[0.,0.] else 'Exploratorio'])
    table('tesis_calidad_instituciones','Soporte de los contrastes institucionales P menos C',
        ['Vía/ventana','Institución','N P/C','Diferencia [IC95]','Uso'],rows,
        source+' Conteos monetarios pequeños se indican como menos de10. Las ramas con10--29 se revisaron por amplitud e influencia: las viables se conservan como exploratorias, incluyan o no cero. Las no confiables se indican sin estimación. No se mezclan instituciones para obtener N. Sin programa común longitudinalA.',align='lp{.26\\textwidth}rrp{.15\\textwidth}')
    return all_tables,'\n'.join(markdown)


def figures(audit: dict) -> None:
    """Regenera la figura T8 desde distribuciones amplias reales, sin extremos."""
    rows=[z for z in audit['T8_reformulado']['grupos'] if z['estadisticas'] is not None and z['N_valido']>=30]
    fig,ax=plt.subplots(figsize=(10,5.5))
    y=np.arange(len(rows));med=np.array([z['estadisticas']['mediana']/1000 for z in rows]);lo=np.array([z['estadisticas']['q25']/1000 for z in rows]);hi=np.array([z['estadisticas']['q75']/1000 for z in rows])
    ax.errorbar(med,y,xerr=[med-lo,hi-med],fmt='o',capsize=3,color=plt.get_cmap('BrBG')(.15))
    ax.set_yticks(y,[f"{z['titularidad']} / {z['escolaridad']} años; N={z['N_valido']:,}" for z in rows]);ax.invert_yaxis()
    ax.set_xlabel('Patrimonio compartido: miles de unidades almacenadas, sin deflactar')
    ax.set_title('Patrimonio por titularidad K y escolaridad agrupada,2021\nReformulación10: todos los grupos conocidos con soporte revisado')
    ax.grid(axis='x',alpha=.15)
    fig.text(.01,.01,'Punto: mediana; barras: Q25–Q75, no IC. Muestra60+ original del EDA, sin ponderar.\nSe excluyen de la interpretación titularidad o escolaridad ND; no ingreso propio, pobreza o efecto causal.',fontsize=8)
    fig.tight_layout(rect=(0,.07,1,1));fig.savefig(ROOT/'resultados/figuras/pensiones_exploratorio_v1__figuras__T8_2021.png',dpi=170);plt.close(fig)

    # B8: coherencia con T8, sin presentar ND como un perfil patrimonial.
    original=json.loads((ORIGINAL/'data/interim/eda_pensionaria/tablas/B8_2021.json').read_text())
    rows=[x for x in original['patrimonio'] if x['titularidad_grupo']!='Desconocido' and x['N_valido']>=10]
    fig,ax=plt.subplots(figsize=(10,4.5))
    ax.barh([x['titularidad_grupo'] for x in rows],[x['mediana']/1000 for x in rows],color=plt.get_cmap('BrBG')(.15))
    ax.set_xlabel('Mediana patrimonial compartida; miles de unidades almacenadas')
    ax.set_title('Titularidad K conocida y patrimonio,2021')
    fig.text(.02,.01,'Muestra60+ original del EDA, sin ponderar. ND excluido de perfiles; no ingreso individual ni pobreza.',fontsize=8)
    fig.tight_layout(rect=(0,.07,1,1));fig.savefig(ROOT/'resultados/figuras/pensiones_exploratorio_v1__figuras__B8_2021.png',dpi=170);plt.close(fig)


def public_registry(audit: dict) -> dict:
    """Censo consultable sin valores monetarios ni frecuencias exactas por valor."""
    affected=[];frequencies=0
    for row in audit['registro_fuentes']:
        if '/frecuencias/' in row['json_pointer']:
            frequencies+=1;continue
        n=row['N_analitico_minimo']
        if n is not None and 0<n<30 and row['estadisticos']:
            affected.append(dict(archivo_fuente=row['archivo_fuente'],json_pointer=row['json_pointer'],
                contexto=row['contexto'],N_revision='<10' if n<10 else n,
                IC_documentado=row['IC_documentado'],estadisticos_evaluados=row['estadisticos'],
                causa='Escasez del grupo/nodo; ver embudo específico si existe. No implica por sí sola error o invalidez del total.',
                uso='No divulgar estadísticos sensibles; no conclusión poblacional' if n<10 else 'Revisión reforzada; no inferencia nacional'))
    census=[]
    for t in audit['inventario_informe']:
        census.append(dict(analisis=t['id'],linea_original=t['linea'],titulo=t['titulo'],
            filas=len(t['filas']),N_explicito=t['denominador_explicito'],fuentes=t.get('fuentes_candidatas',[]),
            unidad='La del contrato y fuente; no se asume persona a partir del rótuloN',
            no_trazable_en_fila=sum(z.get('N_minimo_analitico_visible') is None for z in t['filas']),
            nota='Censo del original. Los N de frecuencia, eventos, exclusiones y muestras tienen funciones distintas.'))
    return dict(etapa=10,cuadros_originales=len(audit['inventario_informe']),figuras_originales=len(audit['inventario_figuras']),
        tex_auditados=len(audit['inventario_tex']),nodos_conteos_y_estadisticos=len(audit['registro_fuentes']),
        nodos_frecuencia_no_confundir_con_tamano=frequencies,
        analisis_afectados=affected,censo_cuadros=census,censo_figuras=audit['inventario_figuras'],
        censo_tex=audit['inventario_tex'],
        politica='politica_calidad_divulgacion.json',
        limitacion='Un registro de agregado no siempre permite reconstruir retrospectivamente cada N único por filtro; se marca y no se sustituye por el total. La auditoría exacta de microdatos cubre336 embudos de la pregunta central y reformulaciónT8. No se certifican por extensión los119 indicadores o el diseño nacional.')


def report_audit(audit: dict,tables: str) -> str:
    """Un solo informe académico con diagnóstico, causas y efecto en conclusiones."""
    small=[z for z in audit['embudos_contrastes'] if 0<z['N_monto']<30]
    union=audit['union_robustez'][0]
    text=f'''### 10.9 Auditoría de calidad estadística y divulgación (etapa10)

**Alcance y conservación.** Se censaron {len(audit['inventario_informe'])} cuadros y {len(audit['inventario_figuras'])} figuras del informe original; {len(audit['inventario_tex'])} archivos LaTeX de cuadros/macros, activos y auxiliares; fuentes01–09 y222 tablas EDA externas. El registro privado contiene{len(audit['registro_fuentes']):,} nodos de conteos/estadísticos: **no son ese número de contrastes independientes**. Frecuencias por valor, exclusiones, eventos y N de estimación se separan. Los originales completos, incluido el PDF de88 páginas y las versiones previas de las figuras, están en la instantánea privada inmutable; no se alteran microdatos ni stash. La edición actual es la versión pública corregida.

**Cierre del filtro y de la publicación.** Se restauró la figura de cambios reales individuales de continuos (figura 47 del informe): N=1,756/1,223 pares principales y1,183/1,103 en sensibilidades. El filtro anterior leía el separador LaTeX de miles como final del número. La comparación de decisiones sobre las fuentes originales encontró un único bloque LaTeX afectado indebidamente, ninguna estimación recalculada y ningún párrafo Markdown afectado por ese error. Las estadísticas originales se conservan. Los exportadores históricos están bloqueados para evitar sobrescribir salidas revisadas y el flujo de GitHub ya no hace publicaciones automáticas. El manifiesto público define también los retiros propuestos de archivos ya rastreados; excluirlos de una carpeta no equivale a retirarlos de Git. La auditoría aplicada de familias, formatos y rutas se registra en el manifiesto de cierre y sus límites no se confunden con una garantía frente a información externa arbitraria. El historial anterior queda separado, sin reescritura.

**Embudo exacto central.** Hay{len(audit['embudos_contrastes'])} embudos de vía/intervalo/perfil/estrato con N de cohorte, categoría basal, presencia al destino, entrevista directa, ausencia de conflicto vital, recepción conocida/afirmativa, todos los montos captados válidos y factor de precios. Se concilian con09; IDs únicos y LEFT1:1, sin pérdida nueva por programación detectada. Se preservan las alertas originales del proveedor; ello no certifica toda la integración histórica. Cada fila de intervalo es una persona, pero un evento no es una persona y las ventanas se solapan: las cinco cohortes suman{audit['dependencia']['N_suma_personas_intervalo']:,} personas-intervalo y solo{audit['dependencia']['N_personas_unicas_cinco_cohortes']:,} personas únicas.

**Criterios distintos.** N<10 impide divulgar estadísticas monetarias o perfiles continuos del grupo y no permite una conclusión poblacional. N10–29 activa revisión de dispersión, IC, empates, influencia y estabilidad. N≥30 tampoco acredita representatividad, precisión o causalidad. Son criterios operativos conservadores de esta tesis, no mínimos universales de ENASEM ni certificación legal. Las condiciones de acceso MHAS prohíben intentar identificar participantes y redistribuir bases a terceros; la documentación oficial de confidencialidad INEGI exige protección de identificación. No se encontró en las fuentes consultadas una regla universal10/30. Véase [política documentada](../diccionarios/politica_calidad_divulgacion.json).

**Resultado central conservado.** Unión K/A2012–2015: {union['N_incorporados']:,}/{union['N_observados']:,} reobservados desde ambas negativas, {fmt(union['estimacion']*100)}%, IC por folio9999 réplicas [{fmt(union['ic95_folio'][0]*100)}; {fmt(union['ic95_folio'][1]*100)}]%. La cohorte inicial es{union['N_basal']:,}. Dos semillas y la omisión de cada folio mantienen el resultado: máximo cambio de{fmt(union['max_cambio_omitir_folio']*100,3)} puntos porcentuales. Esto evalúa precisión condicional, no corrige la selección de los746 destinos no incluidos en el denominador observado.

**Causas y efecto científico.** K2001–2003 contiene12 receptores C y11 importes: solo un monto falta; no existe una pérdida masiva que justifique relajar filtros. La rareza de otra vía basal, la baja incorporación K y su subdivisión por cuartiles explican las celdas de1–4. Incluso al pasar a mitades el contraste sigue sin soporte: se retira de conclusiones direccionales. No se une con otras ventanas. T8 contextual2021 cruza escolaridad detallada y titularidad K; además seleccionaba máximos/mínimos de medianas y trataba ND como perfil. Se reformula uniformemente a0–5/6+ y titularidad conocida, con todos los grupos, sin escoger extremos; los originales siguen privados.

**Sensibilidad que cambia la redacción.** El gradiente patrimonial A2015–2018 es positivo bajo edad3/celda20, pero incluye cero con edad2 y soporte revisado. K2018–2021 conserva dirección puntual negativa, aunque edad3/celda30 incluye cero. Por tanto, no se presentan sus signos como hallazgos incondicionales. A2003–2012 mantiene señal positiva en las especificaciones viables, con seguimiento selectivo y la especificación fina/celda30 sin retención suficiente. A2012–2015 incluye cero ajustado. Los nulos y contraejemplos se conservan. Los IC de medianas A que colapsan a cero se explican por empates, no por equivalencia distributiva. La diferencia cruda P−C K reciente conserva dirección positiva con dos semillas, rangos binomiales y omisión de folios, pero el extremo superior del IC K2012–2015 es sensible al remuestreo: no se exagera precisión de su magnitud.

'''
    text+=tables
    text+='\n#### Todos los embudos centrales con muestras monetarias pequeñas\n\n'
    rows=[]
    for z in small:
        rows.append([f"{z['via']} {z['origen']}–{z['destino']}",z['grupo'].replace('Incorporación desde ambas negativas','P').replace('Incorporación con otra vía basal','C').replace('Continuidad de la vía','R'),
            z['dimension']+' / '+z['categoria'],counts(z['N_receptores'],True),counts(z['N_monto'],True),counts(z['N_monto_faltante'],True),
            'Rareza basal; no soporte general' if z['origen']==2001 and z['via']=='K' and z['grupo'].endswith('basal') else 'Cruce escaso; ND no es perfil' if z['categoria']=='Desconocido' else 'Subdivisión; revisar incertidumbre'])
    text+=md_table(['Vía/ventana','Perfil','Estrato','N receptor','N monto','Faltantes','Causa/evaluación'],rows)
    text+='\nSon'+str(len(small))+' embudos de1–29; '+str(sum(x['N_monto']<10 for x in small))+' con menos de10. Los N exactos y cada paso están en el registro privado sin IDs; la tabla pública usa menos de10 donde corresponde. El catálogo público [de muestras](../diccionarios/auditoria_calidad_muestras.json) enumera también los nodos de fuentes históricas afectados, sin importes. Un nodo repetido o una frecuencia de clase no es una comparación nueva.\n\n'
    text+='#### Matriz de todos los cuadros del informe original\n\n'
    rows=[]
    conceptual={16,43,49,50,61,62,63,64,65,66,126}
    for i,t in enumerate(audit['inventario_informe'],1):
        ns=[z.get('N_minimo_analitico_visible') for z in t['filas'] if z.get('N_minimo_analitico_visible') is not None]
        status='Conceptual/normativo; no muestra por celda' if i in conceptual else 'N visible y fuente registrada' if t['denominador_explicito'] else 'N no visible: consultar fuente; no inferencia desde este cuadro'
        rows.append([str(i),t['titulo'][:78],str(len(t['filas'])),counts(min(ns),True) if ns else 'No consta',status])
    text+=md_table(['Cuadro original','Contenido','Filas','Menor N visible','Trazabilidad y uso'],rows)
    text+='''
La matriz enumera cada cuadro original, no solo el4.14. Los N visibles incluyen márgenes que no son N de estimación: el catálogo identifica ese límite. No se inventa una secuencia retrospectiva de filtros cuando el agregado histórico no la documenta. Los resultados centrales tienen embudos exactos; una comparación auxiliar no trazable no se usa para sostener las conclusiones centrales. La evaluación de frecuencias no debe confundirse con tamaño de una población o con número de IDs.

#### Sensibilidades completas, incluidas especificaciones sin soporte

'''
    rows=[]
    for w in audit['robustez']:
        for x in w['ajustes']:
            rows.append([f"{w['via']} {w['origen']}–{w['destino']}",x['estimando'],f"edad{x['edad_grupos']}/N{x['minimo_celda']}",
                         '/'.join(counts(n) for n in x['N_soporte']),'/'.join(fmt(v*100,0) for v in x['cobertura']),ci(x,'ic95',100 if x['estimando']=='tasa' else 1)])
    text+=md_table(['Vía/ventana','Estimando','Especificación','N soporte','Retención%','Diferencia [IC95]'],rows)
    text+='\nTasas en puntos porcentuales; montos en pesos de septiembre2026. Las especificaciones no comparten necesariamente población o mezcla; no promediar sus estimadores. No se ha reducido el mínimo de retención para obtener un ajuste. Las diferencias entre estratos no son pruebas formales de interacción.\n\n'
    text+='#### Rangos binomiales, influencia y empates\n\n'
    rows=[]
    for w in audit['robustez']:
        x=w['monetario'][0];order=x.get('intervalo_orden_independencia');stats=x.get('estadisticas',[])
        rows.append([f"{w['via']} {w['origen']}–{w['destino']}",
                     '['+fmt(order[0])+'; '+fmt(order[1])+']' if order else 'No estimable',
                     fmt(x.get('max_cambio_al_omitir_un_folio')),
                     '/'.join(fmt(z['proporcion_en_mediana']*100) for z in stats) if stats else 'No estimable'])
    text+=md_table(['Vía/ventana','Cota95 de diferencia por orden','Máximo cambio LOO folio','% exactamente mediana P/C'],rows)
    text+='\nEl método de orden combina dos IC97.5% por Bonferroni bajo independencia personal, no reemplaza al remuestreo por folio ni al diseño de encuesta. En N par la mediana puede ser promedio de dos valores y no estar observada: porcentaje exactamente en mediana cero no significa ausencia de empates. LOO cero tampoco prueba precisión o equivalencia.\n\n'
    text+='''#### Confidencialidad, reconstrucción e historial

Se retiran conjuntamente la estadística sensible, su IC, contraste, perfiles y derivados de cada rama pequeña. Se retira la familia de cuartiles K2001–2003 y se muestra la falta de soporte también en mitades. Los resultados ND no se convierten en perfiles socioeconómicos. No se publican distribuciones monetarias exactas por valor, máximos/mínimos individuales, JSON privados completos ni salidas con microdatos. Se conserva un procedimiento de supresión complementaria de conteos/márgenes para tablas enlazadas; si una familia no puede protegerse sin reconstrucción, se excluye completa de la propuesta. Los conteos básicos de recepción o de información ND no equivalen por sí solos a un importe individual y no se usan para reconstruir estadísticas retiradas.

La revisión histórica de `origin/main` no encontró rutas de microdatos o credenciales, pero sí la interpretación T8 con mediana en un grupo N=5 en el Informe General publicado anteriormente. Corregir el documento actual no borra commits, descargas o copias anteriores. No se reescribió historia ni se contactó a terceros. La propuesta de archivos públicos se genera localmente por lista explícita; no se declara que el historial de GitHub esté saneado.

**Estado de la pregunta central.** El núcleo observacional conserva apoyo: composición y probabilidad de incorporación distintas, expansión de unión observada en2012–2015, heterogeneidad de montos K y coincidencias medianas A. No está completamente respondida en sentido integral o para todas las ventanas: no se identifica pobreza, necesidad total, causalidad, primera alta administrativa, montos de ausentes o una mediana ajustada P/C con soporte suficiente en cinco ventanas de la especificación principal. La sensibilidad de los gradientes se reconoce. La tesis es defendible como respuesta observacional acotada, no como demostración de focalización universal, equivalencia o evaluación causal. La aceptación académica e institucional y el tratamiento del historial permanecen pendientes.
'''
    return text


def export_public() -> dict:
    """Corrige versión académica actual y prepara después una propuesta pública."""
    if "% FASE_B:" in (ROOT/"manuscrito/main.tex").read_text():
        raise RuntimeError("Fuentes en revisión Fase B: el exportador histórico no puede restaurar instantáneas anteriores. Use la selección explícita de sensibilidades; validación/publicación pendientes.")
    audit=json.loads((OUT/'privado/auditoria.json').read_text())
    # Siempre partir de los originales, no de una versión previamente censurada.
    logs=[]
    for p in sorted((ORIGINAL/'manuscrito').rglob('*.tex')):
        rel=p.relative_to(ORIGINAL)
        if 'build' in rel.parts:continue
        text,decisions=clean_tex_rows(p.read_text(),str(rel));logs.extend(decisions)
        text,n=redact_financial_paragraphs(text)
        if n:logs.append(dict(archivo=str(rel),parrafos=n))
        target=ROOT/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text)
    tables,quality=quality_tables(audit)
    figures(audit)
    # Reformulación sustituye el bloque de cuartiles, no se suman análisis favorables.
    report=(ORIGINAL/'resultados/INFORME_GENERAL.md').read_text()
    block='#### Monto posterior por mitad patrimonial y protección basal'
    replacement=quality[quality.index(block):quality.index('#### Reformulación del contexto patrimonial',quality.index(block))]
    report=replace_between(report,'#### Monto posterior por cuartil patrimonial y protección basal','#### Diferencia de medianas posteriores: P menos C',replacement+'\n')
    report=replace_between(report,'La distribución se condiciona por escolaridad y rama pensionaria a la vez. Extremos de medianas',
        'Spearman imp_neto–monto_k_propio_mensual_observado_parcial:',
        'La auditoría10 identifica aquí cruces escasos, incluido un perfil ND menor de10, y una selección retrospectiva de extremos de mediana. Esa comparación no se conserva como evidencia de necesidad. Se reformula a escolaridad0–5/6+ y titularidad conocida, aplicando la misma regla a todos los grupos. Los conteos de exclusión y el cuadro corregido aparecen en10.9; la figura21 se regenera sin ramas desconocidas y sin grupos no revisados.\n\n')
    report,decisions=protect_markdown(report);logs.extend(decisions)
    # Las afirmaciones09 se acotan explícitamente a su especificación original.
    report=report.replace('A2003–2012 y2015–2018 conservan gradiente positivo.',
        'En la especificación principal A2003–2012 y2015–2018 conservan gradiente positivo; la auditoría10.9 muestra que A2015–2018 incluye cero con otra agrupación etaria válida.')
    report=report.replace('K2018–2021 conserva gradiente negativo.',
        'K2018–2021 conserva dirección puntual negativa, con IC sensible al soporte (10.9).')
    report=re.sub(r'A muestra gradientes crudos de incorporación Q1−Q4 positivos.*?(?=\n\n)', 'A presenta gradientes crudos Q1−Q4 positivos, pero la auditoría10.9 muestra sensibilidad de A2015–2018 al agrupar edades y de K2018–2021 al soporte mínimo. A2012–2015 incluye cero ajustado; A2003–2012 mantiene señal en variantes viables con seguimiento selectivo. No se sostiene una dirección universal ni una focalización por necesidad integral.',report,flags=re.S)
    quality=report_audit(audit,quality)
    index=report.index('## 11. Limitaciones')
    report=report[:index]+quality+'\n\n'+report[index:]
    report=report.replace('**Actualización:**','**Actualización:**')
    report=report.replace('# Informe general acumulativo — tesis ENASEM',
        '# Informe general acumulativo — tesis ENASEM\n\n**Edición pública revisada10:** originales íntegros y PDF previo bajo acceso privado. Los detalles retirados no se utilizan para sostener conclusiones. La versión pública no acredita saneamiento del historial de GitHub.')
    report=spacing(report)
    (ROOT/'resultados/INFORME_GENERAL.md').write_text(report)
    # Descripción metodológica de las decisiones, con fuentes verificables.
    method=r'''
\section{Auditoría de tamaños, precisión y divulgación}
\label{sec:calidad10}
La etapa10 revisa todos los cuadros y figuras del Informe General, las fuentes LaTeX activas y auxiliares y los agregados01--09. El registro distingue N elegible, N válido, personas únicas, personas-ronda, eventos, folios, exclusiones y frecuencias de una clase. No se considera cada nodo JSON como una comparación independiente. Los embudos centrales se reconstruyen exactamente sin rehacer la integración: categoría basal, seguimiento, modalidad, conflicto vital, recepción, integridad monetaria y precios. En los agregados históricos que no documentan un paso se declara esa falta de trazabilidad; no se inventa un N ni se reemplaza por el total.

Se separan protección y estadística: N menor de10 impide divulgar montos y perfiles continuos;10--29 requiere revisión reforzada;30 o más no garantiza validez, precisión o representatividad. Son criterios del proyecto, no reglas universales de ENASEM. Las condiciones de acceso del estudio impiden identificar participantes y redistribuir bases; la política de confidencialidad del INEGI exige protección contra identificación. Ninguna de las páginas consultadas establece aquí un mínimo universal10/30 \citep{mhas2026condiciones,inegi2021confidencialidad}. No se presume validación de un convenio particular no aportado.

La precisión se contrasta con9999 réplicas por folio y dos semillas para medianas P menos C, omisión de cada folio e intervalos de orden binomial bajo independencia personal. La última es una comprobación distinta, no un IC por folio o de diseño. Los IC son puntuales y exploratorios; los empates pueden producir intervalos degenerados sin demostrar equivalencia. El extremo superior del IC K2012--2015 es sensible a semilla, aunque la dirección permanezca. Un valor LOO constante tampoco certifica precisión.

Se evalúan uniformemente edad de tres grupos o dos (60--69/70+) y mínimos de20 o30 por celda, manteniendo sexo, escolaridad, al menos cuatro celdas y70\% de retención por grupo. Se cuentan réplicas sin soporte; no se extrapolan ni completan con cero. Se distinguen cambio de población, mezcla y granularidad. No se selecciona la especificación por significancia.

Cuando la estratificación no es necesaria para el estimando principal se reduce de manera sustantiva: patrimonio basal en mitades Q1+Q2/Q3+Q4 en todas las ventanas y, en el contexto T8, escolaridad0--5/6+ con titularidad conocida. Las medianas se recalculan sobre personas, no promediando medianas de los grupos anteriores. ND permanece como estado de información y no como un nivel de desventaja. K2001--2003 sigue sin soporte direccional y no se combina con otras ventanas para rescatarlo.

La versión privada conserva originales, resultados descartados y trazabilidad; la pública retira conjuntamente estadísticas sensibles y derivados que permitirían reconstruirlas. Se aplica supresión complementaria o exclusión de una familia completa cuando hay márgenes reconstructivos. No se publican frecuencias monetarias exactas por valor ni extremos individuales. El listado público es explícito y excluye bases, eventos, copias privadas y salidas con microdatos. Corregir archivos actuales no elimina una exposición en commits anteriores; la revisión del historial y su eventual tratamiento son independientes y no se ha autorizado aquí su reescritura.
'''
    p=ROOT/'manuscrito/capitulos/03_datos_metodologia.tex';p.write_text(p.read_text()+'\n% BEGIN calidad10\n'+spacing(method)+'\n% END calidad10\n')
    core=r'''
\section{Calidad del soporte y robustez de las comparaciones}
\label{sec:resultados-calidad10}
Los problemas no se corrigen solo ocultando celdas. En K2001--2003 el perfil C ya es escaso antes de estratificar; la falta de un importe explica una parte mínima. Dividirlo en cuartiles produce ramas de1--4 observaciones. La comparación general P/C no permite una conclusión direccional confiable, y tampoco se rescata al pasar a mitades. El cuadro~\ref{tab:central-patrimonio_monto} presenta la reformulación uniforme y mantiene la falta de soporte, sin mezclar ventanas. Los demás contrastes recientes conservan poblaciones y resultados correctos.

'''
    core+=tables['tesis_calidad_precision'].replace('\\n','\n')+tables['tesis_calidad_gradiente'].replace('\\n','\n')
    core+=r'''
La sensibilidad exige matizar las afirmaciones previas. A2015--2018 mantiene dirección puntual positiva del gradiente patrimonial, pero su IC incluye cero al ampliar edades con soporte adecuado; K2018--2021 también muestra dependencia del mínimo por celda. A2003--2012 conserva señal positiva en las especificaciones viables, con seguimiento selectivo. A2012--2015 mantiene intervalos ajustados que incluyen cero. No se sostiene un gradiente uniforme ni se eligen solo los resultados que excluyen cero.

Las diferencias medianas crudas P menos C de K reciente conservan dirección positiva con dos semillas, intervalos de orden y omisión de folios. Su magnitud no es igualmente precisa: el extremo superior K2012--2015 cambia con el remuestreo. Las medianas A coincidentes y sus empates siguen siendo resultados válidos, sin prueba de equivalencia o de programa común.

'''
    core+=tables['tesis_calidad_instituciones'].replace('\\n','\n')
    core+=r'''
Las restricciones de institución y evento único reducen el soporte. En K2012--2015 hay ramas con20 o27 válidos C, que se conservan como exploratorias, sin afirmar equivalencia porque su IC incluya cero; en otras hay menos de10. Se conservan sus registros privados y la causa, no se agrupan regímenes o periodos para obtener significancia. Los resultados institucionales de nuevos frente a continuos de08 responden a otro contraste y no se trasladan automáticamente a P/C.

La figura T8 contextual del informe se reformula por escolaridad agrupada: desaparece la selección de máximos/mínimos y ND no se interpreta como perfil económico. Su población original60+ incluye modalidades que no forman parte de la principal directa09. Se presenta como contexto y no como respuesta causal o longitudinal.
'''
    core+=tables['tesis_calidad_T8'].replace('\\n','\n')
    p=ROOT/'manuscrito/capitulos/04_analisis_exploratorio_resultados.tex';s=p.read_text()
    s=s.replace('conserva una diferencia positiva con IC por encima de cero en2003--2012 y2015--2018, pero el IC ajustado2012--2015 incluye cero.',
        'conserva diferencias positivas en la especificación principal de2003--2012 y2015--2018, pero la auditoría de soporte muestra sensibilidad en esta última;2012--2015 incluye cero.')
    s=s.replace('en2018--2021 permanece negativo.','en2018--2021 su dirección puntual es negativa, con precisión sensible al soporte (sección~\\ref{sec:resultados-calidad10}).')
    s=re.sub(r'La asociación con menor patrimonio no es uniforme\..*?(?=\n\n)', 'La asociación con menor patrimonio no es uniforme. Los gradientes crudos de A son positivos, pero A2015--2018 incluye cero al cambiar a otra granularidad etaria con soporte adecuado, y A2012--2015 incluye cero tras ajuste. A2003--2012 mantiene señal positiva en variantes viables, con seguimiento selectivo. K no reproduce una preferencia uniforme por el menor patrimonio; K2018--2021 conserva dirección puntual negativa con precisión sensible al soporte. Los cuadros de la sección de calidad del soporte muestran todas las especificaciones, sin elegir por significancia.',s,flags=re.S)
    s=s.replace('El cuadro~\\ref{tab:central-patrimonio_monto} cruza las tres dimensiones',
        'El cuadro~\\ref{tab:central-patrimonio_monto}, reformulado a mitades tras la auditoría, cruza las tres dimensiones')
    p.write_text(s+'\n% BEGIN calidad10\n'+spacing(core)+'\n% END calidad10\n')
    discussion=r'''
\section{Balance tras la auditoría estadística}
\label{sec:discusion-calidad10}
El núcleo de la pregunta se apoya en grupos amplios y denominadores comprobados: la incorporación observada de unión2012--2015 no depende de las celdas de1--4; es estable al remuestreo y a omitir folios. La composición de nuevos receptores es un estimando distinto y conserva otra vía basal y ND separados. La presencia de otra vía en el origen no acredita coexistencia al destino.

La desventaja relativa no ofrece una respuesta universal. El patrón ajustado A2015--2018 y la precisión de K2018--2021 dependen de especificaciones de soporte razonables; se matiza la redacción anterior, conservando todos los resultados. A2003--2012 mantiene señal en las variantes viables, sin corregir la selección del intervalo de nueve años. No se demuestra focalización por necesidad integral.

Los contrastes monetarios P/C de K reciente y los nulos de A permanecen como hallazgos descriptivos. El primero no demuestra un efecto de las prestaciones ni una diferencia institucional causal; los segundos no acreditan equivalencia. K2001--2003 carece de soporte confiable y algunas ramas institucionales no sostienen una conclusión direccional. La simplificación patrimonial mejora la estabilidad de subdivisiones útiles, sin cambiar las ventanas o la población para producir un resultado favorable.

La pregunta queda respondida parcialmente en su alcance observacional. No se identifica protección económica integral, pobreza, primera alta administrativa, recepción de ausentes o efecto causal. Persisten cinco ajustes monetarios sin soporte en la especificación principal. La calidad estadística se evalúa antes de la protección de celdas; la publicación segura no convierte una comparación débil en fuerte. La exposición histórica T8 detectada debe tratarse separadamente con autorización, sin afirmar que una corrección actual la borra.
'''
    p=ROOT/'manuscrito/capitulos/05_discusion_conclusiones.tex';s=p.read_text()
    s=s.replace('Este resultado se mantiene tras composición común en2003--2012 y2015--2018; en2012--2015 el IC ajustado incluye cero.',
        'La especificación principal presenta ese resultado en2003--2012 y2015--2018; la auditoría10 muestra que el segundo no es robusto a otra granularidad etaria con soporte. En2012--2015 el IC ajustado incluye cero.')
    s=s.replace('K2018--2021 conserva un gradiente contrario tras el ajuste.',
        'K2018--2021 conserva dirección puntual contraria tras el ajuste, pero su IC depende del soporte.')
    s=s.replace('La pregunta queda respondida descriptivamente para recepción propia K/A, perfiles relativos y recursos captados en las ventanas admisibles.',
        'La pregunta recibe una respuesta observacional parcial para recepción propia K/A, perfiles relativos y recursos captados; no todos los contrastes tienen soporte o estabilidad suficientes.')
    s=re.sub(r'La incorporación A entre negativas K/A.*?(?=\n\n)', 'Entre quienes negaban ambas vías, A presenta un gradiente patrimonial crudo positivo, pero su precisión ajustada depende de la especificación: A2015--2018 incluye cero con edades agrupadas de modo más amplio; A2012--2015 incluye cero ajustado. A2003--2012 conserva señal en las variantes viables, sin eliminar selección longitudinal. K ofrece contraejemplos y K2018--2021 es sensible al soporte. Esto impide afirmar una focalización universal por necesidad económica.',s,flags=re.S)
    p.write_text(s+'\n% BEGIN calidad10\n'+spacing(discussion)+'\n% END calidad10\n')
    p=ROOT/'manuscrito/capitulos/07_estado_redaccion_pendientes_revision.tex';s=p.read_text()
    s+='\n\\section{Revisión de calidad y divulgación10}\nSe preservaron los originales privados y se revisaron tamaños, filtros, precisión y reconstrucción. La versión actual retira estadísticas sensibles y corrige interpretaciones que dependían de granularidad o soporte. El censo y sus límites se documentan en Informe10.9. No se hizo commit, push ni reescritura del historial; no se certifica una tesis lista por superar pruebas de código.\n';p.write_text(spacing(s))
    # Referencias nuevas verificadas: no atribuir un umbral a estas fuentes.
    bib=ROOT/'investigacion/referencias.bib';s=bib.read_text()
    if '@misc{mhas2026condiciones,' not in s:
        s+='\n@misc{mhas2026condiciones, author={{Mexican Health and Aging Study}}, title={Data Products: condiciones de acceso a los datos}, year={2026}, howpublished={\\url{https://www.enasem.org/DataProducts/Home.aspx}}, note={Consultado el 23 de octubre de 2026; sin mínimo numérico de celda certificado}}\n'
    if '@misc{inegi2021confidencialidad,' not in s:
        s+='\n@misc{inegi2021confidencialidad, author={{Instituto Nacional de Estadística y Geografía}}, title={Política para la Gestión de la Confidencialidad en la Información Estadística y Geográfica}, year={2021}, howpublished={\\url{https://sidof.segob.gob.mx/notas/docFuente/5634105}}, note={Consultado el 23 de octubre de 2026}}\n'
    bib.write_text(s)
    registry=public_registry(audit);save_json(ROOT/'diccionarios/auditoria_calidad_muestras.json',registry)
    save_json(OUT/'privado/supresiones.json',dict(decisiones=logs,
        familias_excluidas=['Cuartiles monetarios K2001–2003','Importes/perfiles de otra vía ND','Extremos retrospectivos T8 y ramas ND','Datos/márgenes derivados de cada rama protegida'],
        nota='No contiene importes individuales. Los originales se conservan en la instantánea privada.'))
    write_notebook()
    for name in ['README.md','manuscrito/README.md']:
        p=ROOT/name;s=p.read_text();a='<!-- BEGIN estado10 -->';b='<!-- END estado10 -->'
        if a in s:s=s[:s.index(a)]+s[s.index(b)+len(b):]
        s+='\n'+a+'\n## Auditoría estadística y divulgación — etapa10\n\nEl Informe General10.9 reúne el censo de126 cuadros/50 figuras originales, la trazabilidad de muestras, las reformulaciones y las limitaciones. Se preserva la versión privada original de88 páginas y sus resultados; la edición académica actual es la versión pública corregida, con validación separada. El núcleo de incorporación observado se conserva; algunos gradientes y contrastes institucionales se matizan por soporte/estabilidad. Véanse `diccionarios/politica_calidad_divulgacion.json`, `diccionarios/auditoria_calidad_muestras.json` y `python scripts/export_quality_public.py`. Ningún umbral acredita inferencia nacional. No se hizo commit ni push. El historial público previo contiene un detalle T8 de un grupo pequeño: no se ha saneado ni se reescribirá sin autorización. La propuesta local de archivos públicos excluye los originales y agregados privados, así como artefactos históricos no revisados.\n'+b+'\n';p.write_text(spacing(s))
    return dict(tablas_informe_original=len(audit['inventario_informe']),figuras_original=len(audit['inventario_figuras']),
        embudos=len(audit['embudos_contrastes']),decisiones_divulgacion=len(logs),
        sha_informe=digest(ROOT/'resultados/INFORME_GENERAL.md'))


def spacing(text: str) -> str:
    """Espaciado editorial sin modificar etiquetas, rutas o códigos."""
    words='etapa|etapas|Informe|informe|cohorte|original|privada|privado|pública|público|figura|cuadro|ventana|personas|réplicas|folio|edad|escolaridad|grupos|ramas|basal|en|y|de|con|sin|menor|mayor|solo|Solo|una|los|las|comparación|tienen|hay|contiene|debe|K|A|N|especificación|auditoría|celdas|selección|faltantes'
    pieces=re.split(r'(`[^`]*`|\\(?:label|ref|input|citep|citet|url)\{[^}]*\}|\]\([^)]*\))',text)
    for i,p in enumerate(pieces):
        if p.startswith(('`','\\','](')):continue
        pieces[i]=re.sub(r'\b('+words+r')(?=\d)',r'\1 ',p).replace('N≥30','N ≥30').replace('N<10','N <10')
    return ''.join(pieces)


def write_notebook() -> None:
    """Notebook10 de lectura, sin outputs ni acceso a filas individuales."""
    import nbformat
    nb=nbformat.v4.new_notebook();nb.metadata={'kernelspec':{'display_name':'Python3','language':'python','name':'python3'}}
    nb.cells=[nbformat.v4.new_markdown_cell('# 10 · Calidad estadística, soporte y divulgación\n\nAudita toda la evidencia, conserva originales privados y separa privacidad de precisión. No reconstruye integración. Ver Informe10.9 y política documentada; no se publica microdato ni se realiza Git.'),
        nbformat.v4.new_code_cell("from pathlib import Path\nimport json,pandas as pd\nroot=Path.cwd() if (Path.cwd()/'diccionarios').exists() else Path.cwd().parent\nr=json.loads((root/'diccionarios/auditoria_calidad_muestras.json').read_text())\nprint('Cuadros originales:',r['cuadros_originales'],'Figuras:',r['figuras_originales'])\npd.DataFrame(r['censo_cuadros'])"),
        nbformat.v4.new_markdown_cell('## Flujo y causas\n\nEl censo privado conserva N exactos por336 filtros; no se exportan IDs o importes. Frecuencias de un valor no son N de un contraste. K2001–2003 tiene rareza basal real; la división por cuartiles la agrava. T8 se reformula0–5/6+ con titularidad conocida. No se relajan poblaciones ni ventanas.'),
        nbformat.v4.new_code_cell("pd.DataFrame(r['analisis_afectados'])[['archivo_fuente','json_pointer','N_revision','uso']].head(30)"),
        nbformat.v4.new_markdown_cell('## Resultados y límites\n\nLa unión observada2012–2015 es estable. El gradiente A2015–2018 depende de granularidad etaria; K2018–2021 del soporte. P/C K reciente conserva dirección; A tiene empates sin equivalencia. No inferencia nacional, necesidad integral o causalidad. Las cuatro especificaciones se publican completas. Reproducir en entorno autorizado: audit_statistical_quality.py, complete_quality_audit.py y export_quality_public.py. La etapa requiere fuentes y la instantánea privada congelada; la copia pública no pretende reconstruir evidencia privada ausente.'),
        nbformat.v4.new_code_cell("policy=json.loads((root/'diccionarios/politica_calidad_divulgacion.json').read_text())\npolicy['revision_N']"),
        nbformat.v4.new_markdown_cell('## Confidencialidad e historia\n\nN <10 no publica estadísticas sensibles; se retiran también derivados. N10–29 no se valida automáticamente; N≥30 no acredita precisión. El historial previo contiene exposición T8 de una celda pequeña, sin identificador directo detectado. No se ha reescrito ni actualizado GitHub. Los originales permanecen privados y una corrección actual no elimina descargas anteriores.')]
    nbformat.write(nb,ROOT/'notebooks/10_CALIDAD_ESTADISTICA_DIVULGACION.ipynb')
