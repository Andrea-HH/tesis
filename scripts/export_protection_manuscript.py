"""Exporta J02 desde agregados: cifras/tablas/figuras y narrativa, sin microdatos."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text

import json
import argparse
from hashlib import sha256
import re
from typing import Any
from pathlib import Path
import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from tesis_enasem.manuscript import render_latex_table, latex_number, escape_latex as latex_escape

ROOT=Path(__file__).resolve().parents[1]


def export() -> None:
    """Mantiene las cifras de la tesis sincronizadas con las tablas calculadas."""
    r=json.loads(read_project_text(project_path('', "docs/eda/proteccion_economica/resultados.json")))
    tables=project_path('', "manuscrito/tablas");figures=project_path('', "manuscrito/figuras/borradores")
    summary,validity=[],[]
    for c in r["cobertura"]:
        year=c["ano"]
        p=next(x for x in r["recepcion"] if x["ano"]==year and x["variable"]=="pension_propia_k")
        a=next(x for x in r["recepcion"] if x["ano"]==year and x["variable"]=="apoyo_propio")
        cats={x["categoria"]:x["N"] for x in r["categorias"] if x["ano"]==year}
        pair=next(x for x in r["asociaciones"] if x["ano"]==year and x["cruce"]=="Pensión K × Apoyo")
        summary.append({"Año":str(year),"N 60+":c["N_60"],"Propia K":p["N_si"],"Apoyo A":a["N_si"],
                        "K y A":cats.get("Pensión K y apoyo",0),"A/K no":cats.get("Apoyo y negativa propia K",0)})
        validity.append({"Año":str(year),"K ND":p["N_desconocido"],"A ND":a["N_desconocido"],
                         "Pares":pair["N_validos"],"K sí (%)":p["pct_si_conocido"],"A sí (%)":a["pct_si_conocido"]})
    write_project_text(tables/"proteccion_cobertura.tex", render_latex_table(pd.DataFrame(summary),
        "Recepción observada de pensiones y apoyos públicos entre personas de 60 años o más",
        "tab:proteccion-cobertura",
        "N 60+: edad en cada visita. K: cuatro contingencias pensionarias, no exclusivamente contributivas. A: donativo público adicional en dinero o especie. A/K no: apoyo con negativa explícita propia K, no ausencia de toda pensión. Sin ponderar; 2001 conserva orientación del proveedor con J1 pendiente.",column_format="lrrrrr"))
    write_project_text(tables/"proteccion_validez.tex", render_latex_table(pd.DataFrame(validity),
        "Denominadores conocidos y estados desconocidos de la recepción económica",
        "tab:proteccion-validez",
        "Porcentajes entre respuestas conocidas de cada indicador, con denominadores distintos. Pares: ambas recepciones conocidas; ND permanece separado de negativas. No son estimaciones nacionales. Los denominadores elegibles y por fuente están en el notebook 05d.",column_format="lrrrrr"))
    rows=[]
    for group,label in (("sexo_grupo","Sexo"),("localidad_grupo","Localidad"),("educacion_grupo","Educación"),("edad_grupo","Edad")):
        data=r["cruces"][f"2021_recepcion_{group}"]
        for level in dict.fromkeys(x[group] for x in data):
            if level=="Desconocido":
                continue
            p=next(x for x in data if x[group]==level and x['variable']=='pension_propia_k')
            a=next(x for x in data if x[group]==level and x['variable']=='apoyo_propio')
            short=level.replace(" habitantes","")
            rows.append({"Perfil":label,"Grupo":short,"N K":p['N_conocido'],"K (%)":p['pct_si_conocido'],
                         "N A":a['N_conocido'],"A (%)":a['pct_si_conocido']})
    write_project_text(tables/"proteccion_perfiles_2021.tex", render_latex_table(pd.DataFrame(rows),
        "Recepción dentro de perfiles de personas de 60 años o más, 2021","tab:proteccion-perfiles",
        "N K/N A: respuestas conocidas de cada indicador. Porcentajes dentro de grupo, no composición de receptores. Localidad usa corte de 100 mil; no identifica ruralidad estricta. Educación: años en la primera entrevista. Edad: visita actual. Desconocidos y conteos afirmativos completos en reportes; sin ponderar.",column_format="llrrrr"))
    flow=[]
    for a,b,var in ((2012,2015,"pension_propia_k"),(2018,2021,"pension_propia_k"),(2012,2015,"apoyo_propio")):
        for state in ("Inicio observado","Continuidad observada","Pérdida de recepción observada","Negativas continuas"):
            rows=[x for x in r['transiciones'] if x['ano_origen']==a and x['ano_destino']==b and x['variable']==var and x['interpretacion']==state]
            n=sum(x['N'] for x in rows)
            cohort=next(x['N_cohorte_origen'] for x in r['transiciones'] if x['ano_origen']==a and x['variable']==var)
            flow.append({"Par":f"{a}/{b}","Bloque":"K" if var.startswith('pension') else "A", "Estado":state.replace(" de recepción", ""),"N":n,"N origen":cohort})
    write_project_text(tables/"proteccion_transiciones.tex", render_latex_table(pd.DataFrame(flow),
        "Transiciones observadas en pares de comparabilidad conceptual condicionada",
        "tab:proteccion-transiciones",
        "Cohorte 60+ viva en origen; se exige edad final 60+ y ambas respuestas conocidas para estos cuatro estados. N origen incluye desconocidos, muerte y ausencias que se muestran en el notebook. Intervalos nominales de tres años; no alta/baja administrativa. La comparabilidad no se declara definitiva ni implica continuidad del mismo programa.",column_format="llp{6cm}rr"))
    write_project_text(tables/"proteccion_cifras.tex", '% Generado desde J02 agregado, no editar cifras.\n'+
        f"\\newcommand{{\\protObservaciones}}{{{latex_number(r['N_personas_ronda_60'])}}}\n"+
        f"\\newcommand{{\\protPersonas}}{{{latex_number(r['N_personas_60_alguna_visita'])}}}\n")
    fig,ax=plt.subplots(figsize=(9,5.2))
    x=np.arange(6); colors=plt.get_cmap('BrBG')
    for j,(v,label) in enumerate((("pension_propia_k","Propia K"),("apoyo_propio","Donativo A"))):
        values=[next(z['pct_si_conocido'] for z in r['recepcion'] if z['ano']==c['ano'] and z['variable']==v) for c in r['cobertura']]
        bars=ax.bar(x+(-.18 if j==0 else .18),values,width=.35,label=label,color=colors(.12 if j==0 else .88))
        counts=[next(z['N_si'] for z in r['recepcion'] if z['ano']==c['ano'] and z['variable']==v) for c in r['cobertura']]
        ax.bar_label(bars,labels=[f'{val:.1f}%\nn={n:,}' for val,n in zip(values,counts)],padding=3,fontsize=9)
    ax.set_xticks(x,[str(c['ano']) for c in r['cobertura']]);ax.set_ylabel('% entre respuestas conocidas',fontsize=12)
    ax.set_ylim(0,65);ax.legend();ax.set_title('Recepción en personas de 60+ por visita\nMuestra sin ponderar; instrumentos parcialmente comparables',fontsize=12)
    ax.grid(axis='y',alpha=.15)
    fig.text(.02,.015,'K no identifica toda pensión contributiva; A incluye dinero/especie y cambia opciones en 2018/2021.\nDenominadores y desconocidos en tabla; no comparación de impacto de políticas.',fontsize=10)
    fig.tight_layout(rect=(0,.1,1,1));fig.savefig(figures/'proteccion_comparativa.png',dpi=170);plt.close(fig)
    shutil.copyfile(project_path('', 'reports/proteccion_economica/figuras/2021_pension_apoyo_localidad_grupo.png'),figures/'proteccion_localidad_2021.png')
    paragraphs=[r"\section{Pensiones y apoyos públicos en la población de 60 años o más}",
                r"\label{sec:proteccion-resultados}",
                r"La recepción de prestaciones se examina como un componente de protección económica, complementario al patrimonio y sin convertirlo en ingreso total. La selección descriptiva contiene \protObservaciones{} observaciones de \protPersonas{} personas con edad de 60 años o más en al menos una visita. Cada ronda utiliza la edad de esa visita; no se exige panel balanceado. La tabla~\ref{tab:proteccion-cobertura} distingue recepción K, donativo A, coexistencia y apoyo ante negativa K. Esta última categoría responde a la pregunta sobre cobertura adicional observada; no identifica personas carentes de toda pensión ni constituye una estimación de efecto del programa.",
                r"\input{tablas/proteccion_cobertura}",r"\input{tablas/proteccion_validez}"]
    for year in (2001,2015,2018,2021):
        c=next(c for c in summary if c['Año']==str(year));gap=next(g for g in r['brechas_apoyo'] if g['ano']==year and 'estrato' not in g)
        g0,g1=gap['grupos']
        paragraphs.append(latex_escape(f"En {year}, se identifican {c['Propia K']:,} receptoras propias K y {c['Apoyo A']:,} receptoras A de {c['N 60+']:,} personas de 60+. Coexisten ambas recepciones en {c['K y A']:,} y se observa apoyo con negativa propia K en {c['A/K no']:,}. Entre respuestas conocidas de apoyo, la proporción es {g0['pct_apoyo_conocido']:.2f}% en negativas K y {g1['pct_apoyo_conocido']:.2f}% en receptoras K, una diferencia de {gap['diferencia_pp_no_menos_si']:.2f} puntos porcentuales (no menos sí). Estos denominadores seleccionan estados conocidos; su contraste es descriptivo de la muestra.").replace('receptoras','personas receptoras'))
    paragraphs += [r"El contraste de 2021 muestra coexistencia de apoyo y pensión K, mientras en las rondas previas seleccionadas el apoyo resulta más frecuente entre negativas K. La incorporación de una opción explícita de vejez, los cambios de programas y la composición del panel impiden interpretar esta diferencia como impacto o ampliación causal de una política. Asimismo, K puede contener programas públicos agrupados: no representa exclusivamente pensiones contributivas. La figura~\ref{fig:proteccion-comparativa} presenta los porcentajes con esta restricción.",
        r"\begin{figure}[htbp]\centering\includegraphics[width=0.98\textwidth]{figuras/borradores/proteccion_comparativa.png}\caption{Recepción K y A por ronda entre respuestas conocidas de personas de 60 años o más. Sin ponderar; definiciones históricas parcialmente comparables.}\label{fig:proteccion-comparativa}\end{figure}",
        r"\subsection{Diferencias por perfil y asociaciones contemporáneas}",
        r"La tabla~\ref{tab:proteccion-perfiles} expresa tasas dentro de grupos, con denominadores separados para K y A. Estos porcentajes no equivalen a la proporción de hombres, mujeres o habitantes de cada localidad dentro del conjunto receptor. La escolaridad corresponde a la primera entrevista; los contrastes por edad incorporan efectos de cohorte y supervivencia que este análisis no separa.",
        r"\input{tablas/proteccion_perfiles_2021}"]
    def cell(group: str, level: str, variable: str) -> dict:
        return next(x for x in r['cruces'][f'2021_recepcion_{group}'] if x[group]==level and x['variable']==variable)
    def detail(group: str, level: str, variable: str) -> str:
        x=cell(group,level,variable)
        return f"{x['N_si']:,}/{x['N_conocido']:,} ({x['pct_si_conocido']:.2f}%)"
    p,a='pension_propia_k','apoyo_propio'
    paragraphs += [latex_escape(
        f"Por sexo, la recepción K de los hombres es {detail('sexo_grupo','Hombre',p)}, frente a {detail('sexo_grupo','Mujer',p)} de las mujeres. En cambio, A registra {detail('sexo_grupo','Hombre',a)} y {detail('sexo_grupo','Mujer',a)}, respectivamente. La diferencia de sexo es más marcada para K que para el donativo público observado: esto motiva examinar distintas trayectorias de protección, sin atribuir la diferencia a una política ni a un mecanismo laboral no medido."),
        latex_escape(f"El gradiente territorial difiere según la fuente. K aparece en {detail('localidad_grupo','<100 mil habitantes',p)} de localidades menores de 100 mil y en {detail('localidad_grupo','≥100 mil habitantes',p)} de las mayores; A registra {detail('localidad_grupo','<100 mil habitantes',a)} y {detail('localidad_grupo','≥100 mil habitantes',a)}, respectivamente. La recepción pública adicional es más frecuente en el grupo con menor recepción K. Esta complementariedad descriptiva no demuestra compensación efectiva de ingresos y el corte no permite inferir ruralidad."),
        latex_escape(f"La escolaridad presenta gradientes opuestos: entre personas sin años de educación, K registra {detail('educacion_grupo','0 años',p)} y A {detail('educacion_grupo','0 años',a)}; con 10 años o más, K registra {detail('educacion_grupo','≥10 años',p)} y A {detail('educacion_grupo','≥10 años',a)}. El apoyo observado alcanza con mayor frecuencia a perfiles de menor escolaridad, mientras K aumenta con ella. Escolaridad, cohortes y trayectorias ocupacionales no se separan causalmente en este diseño."),
        latex_escape(f"La edad muestra mayor contraste para A: en 60–69 se observa {detail('edad_grupo','60–69',a)}, frente a {detail('edad_grupo','70–79',a)} en 70–79. K pasa de {detail('edad_grupo','60–69',p)} a {detail('edad_grupo','70–79',p)}. La recepción K no es monótona en edades posteriores, por lo que el contraste no se interpreta como incremento mecánico al envejecer. La referencia al año previo, la composición de sobrevivientes y el cambio de opciones del cuestionario limitan cualquier interpretación de elegibilidad.")]
    association=next(a for a in r['asociaciones'] if a['ano']==2021 and a['cruce']=='Pensión K × Apoyo')
    paragraphs.append(latex_escape(f"La asociación global K–A en 2021 tiene V de Cramér={association['V_cramer']:.3f}, con {association['N_validos']:,} pares válidos y {association['N_excluidos']:,} excluidos por falta de respuesta. La coexistencia absoluta de receptores puede ser importante aun cuando la dependencia estadística global sea pequeña: una magnitud no sustituye a la otra."))
    for group in ('localidad_grupo','sexo_grupo'):
        for g in r['brechas_apoyo']:
            if g['ano']==2021 and g.get('estratificador')==group:
                no,yes=g['grupos']
                paragraphs.append(latex_escape(f"En {g['estrato']}, el apoyo entre negativas K es {no['pct_apoyo_conocido']:.2f}% ({no['N_apoyo_si']:,}/{no['N_apoyo_conocido']:,}), frente a {yes['pct_apoyo_conocido']:.2f}% ({yes['N_apoyo_si']:,}/{yes['N_apoyo_conocido']:,}) entre receptoras K. La diferencia estratificada es {g['diferencia_pp_no_menos_si']:.2f} puntos porcentuales; permite describir heterogeneidad, sin probar focalización o sustitución de prestaciones."))
    for cruce,explanation in [('Pensión K × Escolaridad en primera entrevista / Sexo',
        'El gradiente de escolaridad aparece en ambos sexos, sin que esta similitud ajuste por cohortes o historia laboral.'),
        ('Pensión K × Edad en la visita / Localidad a 100 mil (no ruralidad estricta)',
        'La magnitud de asociación edad–K cambia entre tamaños de localidad; estratificar evita atribuir al envejecimiento una composición territorial agregada.')]:
        stats=[x for x in r['asociaciones'] if x['ano']==2021 and x['cruce']==cruce]
        numbers='; '.join(f"{x['estrato']}: V={x['V_cramer']:.3f}, N={x['N_validos']:,}" for x in stats)
        paragraphs.append(latex_escape(f"El cruce {cruce} presenta {numbers}. {explanation} Son tamaños descriptivos, sin prueba ajustada por diseño ni comparación causal de estratos."))
    paragraphs += [r"\begin{figure}[htbp]\centering\includegraphics[width=0.98\textwidth]{figuras/borradores/proteccion_localidad_2021.png}\caption{Pensión K, apoyo A y tamaño de localidad en 2021. Cada celda indica N y porcentaje dentro de su fila pensionaria. El corte de 100 mil habitantes no identifica ruralidad estricta.}\label{fig:proteccion-localidad}\end{figure}",
        r"\subsection{Instituciones, eventos y seguimiento}"]
    cov=next(x for x in r['cobertura_institucional'] if x['ano']==2021)
    old=[x for x in r['seguridad_social_vejez_2021'] if x['vejez_identificada']=='Sí']
    both=next(x['N'] for x in old if x['seguridad_social_evidencia']=='Sí')
    negative=next(x['N'] for x in old if x['seguridad_social_evidencia']=='No')
    paragraphs.append(latex_escape(f"En 2021, {cov['N_IMSS_ISSSTE_identificado']:,} personas de 60+ tienen evidencia de pensión IMSS/ISSSTE, que incluye derechos derivados. El programa de vejez explícito se observa junto con esta evidencia en {both:,} personas y ante negativa propia K en {negative:,}. Las demás instituciones no se convierten automáticamente en pensiones no contributivas; tampoco el donativo agregado acredita ese tipo. Los eventos, instituciones y montos se conservan por beneficiario, y no se suman las versiones originales, imputadas y construidas."))
    paragraphs += [r"Los montos son mediciones mensuales nominales observadas de eventos, con datos faltantes; no se presentan como suficiencia, ingreso total ni cambios reales entre rondas. Continúan los 33 candidatos de coincidencia de 2015, los controles de 2001 y los punteros discordantes. Igualdad de montos entre K y A no demuestra que se trate de la misma prestación; por ello no se suman estos bloques ni se descuentan cantidades automáticamente.",
        r"La tabla~\ref{tab:proteccion-transiciones} selecciona pares de comparabilidad conceptual condicionada. Las matrices completas mantienen muerte registrada, ausencia con posterior reaparición, ausencia sin retorno observado y recepción desconocida. Una afirmativa en la visita siguiente no permite fechar el alta, y una negativa no demuestra suspensión definitiva. Los pares con ruptura del instrumento se describen como observación, sin interpretar inicio o pérdida homogénea.",
        r"\input{tablas/proteccion_transiciones}",
        r"El alcance es descriptivo de la muestra observada de personas de 60 años o más. Persisten limitaciones de selección, dependencia entre cónyuges, ponderación y diseño, programas agrupados, dinero frente a especie y cambios de captura. La armonización conserva desconocidos y fuentes; no cierra la clasificación pensionaria ni las decisiones del diseño predictivo de la tesis."]
    write_project_text(project_path('', 'manuscrito/capitulos/04_proteccion_economica.tex'), '% Generado desde J02 agregado; regenerar con export_protection_manuscript.py.\n\n'+'\n\n'.join(paragraphs)+'\n')


def export_formal() -> None:
    """Exporta cinco cuadros y cifras06–08 guardadas, sin nuevos análisis."""
    interim=ROOT/'data/interim';tables=ROOT/'manuscrito/tablas'
    paths={key:interim/folder/file for key,folder,file in [
        ('coverage','cobertura_proteccion_economica','resultados.json'),
        ('money','politicas_montos_suficiencia','resultados.json'),
        ('synthesis','sintesis_proteccion_economica','resultados.json'),
        ('transitions','transiciones_montos_pensionarios','resultados.json'),
        ('precision','transiciones_montos_pensionarios','precision.json')]}
    d={key:json.loads(path.read_text()) for key,path in paths.items()}
    assert d['precision']['referencia']=='2026-09' and d['precision']['metodologia']['replicas']==9999
    numbers: dict[str,str]={};products: list[dict[str,Any]]=[]
    def n(value: float | int | None, decimals: int=2) -> str:
        """Formatea sin cambiar magnitudes ni sustituir desconocidos por cero."""
        return latex_number(value,decimals)
    def put(key: str, value: float | int | None, decimals: int=2) -> None:
        """Registra un dato exportado bajo una clave estable para la prosa."""
        numbers[key]=r'\ensuremath{'+n(value,decimals)+'}'
    def est(block: dict[str,Any], key: str, folio: bool=False) -> dict[str,Any]:
        """Recupera el estimando exacto y su agrupamiento ya calculado."""
        return next(x for x in block['sensibilidad_folio' if folio else 'principal']['estimaciones'] if x['id']==key)
    def ci(z: dict[str,Any]) -> str:
        """Permite saltar entre estimación e intervalo sin cortar sus números."""
        return (r'\ensuremath{'+n(z['estimacion'])+r'}\ \allowbreak\ensuremath{['
                +n(z['ic95'][0])+r';\,'+n(z['ic95'][1])+']}')
    def pe(prefix: str, block: dict[str,Any], key: str) -> None:
        """Exporta conjuntamente punto e intervalo del mismo contraste."""
        z=est(block,key);put(prefix,z['estimacion']);numbers[prefix+'.IC']=ci(z)
    def table(name: str, caption: str, headers: list[str], rows: list[list[str]],
              note: str, widths: str | None=None) -> None:
        """Escribe exclusivamente filas agregadas seleccionadas con nota y fuente."""
        rows=[[re.sub(r'^([KA])(?=20\d\d)',r'\1 ',value) if isinstance(value,str) else value
               for value in row] for row in rows]
        for old,new in [('septiembre de2026','septiembre de 2026'),('K2003','K 2003'),
                        ('K2012','K 2012'),('K2015','K 2015'),('A2001','A 2001'),
                        ('A2015','A 2015'),('A2018','A 2018'),('H/M2012','H/M 2012'),
                        ('y2015','y 2015'),('es8,888','es 8,888'),('por corte:8','por corte: 8'),
                        ('de11,168','de 11,168')]:
            caption=caption.replace(old,new);note=note.replace(old,new)
        label='tab:tesis-'+name
        lines=['% Exportado desde agregados; no editar cifras manualmente.',r'\begin{table}[!htbp]',r'\centering',
            r'\caption{'+caption+r'}\label{'+label+'}',r'\footnotesize\setlength{\tabcolsep}{3pt}\renewcommand{\arraystretch}{1.25}',
            r'\begin{tabularx}{\linewidth}{'+(widths or 'Y'*len(headers))+'}',r'\toprule',
            ' & '.join(r'\textbf{'+h+'}' for h in headers)+r' \\',r'\midrule',
            *[' & '.join(row)+r' \\' for row in rows],r'\bottomrule',r'\end{tabularx}',
            r'\notacuadro{'+note+'}',r'\fuentecuadro{Elaboración propia, ENASEM; agregados de notebooks 06--08 y validación focalizada del informe general, secciones 10.2--10.7. Sin ponderación nacional.}',r'\end{table}','']
        p=tables/('tesis_'+name+'.tex');p.write_text('\n'.join(lines))
        products.append(dict(archivo=str(p.relative_to(ROOT)),etiqueta=label,titulo=caption,filas=len(rows),sha256=sha256(p.read_bytes()).hexdigest()))
    rounds={r['ronda']:next(x for x in r['cobertura'] if x['dimension']=='General') for r in d['coverage']['rondas'] if r['analisis']=='principal'}
    rows=[]
    for year,z in rounds.items():
        for key in ['N_elegible','N_KA_no','N_KA_ND_elegible','N_KA_si','N_KA_conocido']:put(str(year)+'.'+key,z[key],0)
        for v in ['K','A','KA']:put(str(year)+'.'+v,z[v+'_pct'])
        cells=[r'\ensuremath{'+n(z[v+'_pct'])+r'}\ \allowbreak\ensuremath{('+n(z['N_'+v+'_conocido'],0)+')}' for v in ['K','A','KA']]
        rows.append([str(year),n(z['N_elegible'],0),*cells,r'/\allowbreak{}'.join(n(z['N_'+v+'_ND_elegible'],0) for v in ['K','A','KA']),n(z['N_KA_no'],0)])
    table('cobertura','Recepción propia y estados de información por ronda, directas 60+, 2001--2021',
        ['Ronda','N elegible',r'K: \% (N)',r'A: \% (N)',r'Unión: \% (N)','ND K/A/unión','Ambas negativas'],rows,
        r'Cada tasa usa el N conocido entre paréntesis; ND se cuenta sobre el N elegible de la fila y no significa negativa. Unión: alguna afirmativa; no: ambas negativas. K y A se superponen. Las filas son cortes separados, no una serie homogénea a través de rupturas K2003--2012/K2015--2018 o A2001--2003/A2018--2021.',
        r'p{.075\linewidth}p{.085\linewidth}YYYp{.135\linewidth}p{.13\linewidth}')
    rows=[]
    for z in d['money']['montos']:
        if z['dimension']!='General' or z['grupo']!='Todas':continue
        p=z['persona'];nom,real,lpi=[p[x] for x in ['nominal','real','lpi_pct']]
        rows.append([str(z['ronda']),z['via'],n(z['N_receptores'],0),n(nom['N'],0)+r'/\allowbreak{}'+n(real['N'],0),n(nom['mediana']),n(real['mediana']),n(lpi['mediana'])+' ('+n(lpi['N'],0)+')'])
        pre=f"{z['via']}.{z['ronda']}"
        put(pre+'.N',real['N'],0);put(pre+'.Nominal',nom['mediana']);put(pre+'.Real',real['mediana'])
    a5=next(x for x in d['synthesis']['A5'] if x['dimension']=='General');p=a5['declarado']
    rows.append(['2021','A5',n(a5['N_personas'],0),n(p['nominal']['N'],0)+r'/\allowbreak{}'+n(p['real']['N'],0),n(p['nominal']['mediana']),n(p['real']['mediana']),n(p['lpi_pct']['mediana'])+' ('+n(p['lpi_pct']['N'],0)+')'])
    for key,value in [('N',a5['N_personas']),('Valido',p['real']['N']),('Nominal',p['nominal']['mediana']),('Real',p['real']['mediana']),('LPI',p['lpi_pct']['mediana'])]:put('A5.'+key,value,0 if key in ['N','Valido'] else 2)
    table('montos','Montos mensuales captados y referencia económica, directas 60+, 2001--2021',
        ['Ronda','Vía','N recibe','N nom./real',r'Mediana nominal (\$)',r'Mediana real (\$)',r'Prestación/ LPI: mediana \% (N)'],rows,
        r'K/A: suma personal observada parcial, no ingreso total. A5: evento explícito de vejez; no se añade de nuevo a A. Pesos reales de septiembre de 2026, precios del año calendario anterior a entrevista real. LPI por persona/mes del mismo periodo: la razón se calcula individualmente antes de resumir. En 2001/2003 solo localidades de al menos 100 mil habitantes tienen ámbito asignable; su N de LPI no es comparable con el total posterior. Una prestación bajo LPI no clasifica pobreza.',
        r'p{.075\linewidth}p{.04\linewidth}YYYYY')
    k,a=d['precision']['ventanas'];rows=[]
    for z,key,label in [(k,'new_minus_cont','K2012--15: crudo'),(k,'adjusted_new_minus_cont','K: composición común'),(k,'ss_new_minus_cont','K: evidencia IMSS/ISSSTE'),(a,'new_minus_cont','A2015--18: crudo'),(a,'adjusted_new_minus_cont','A: composición común')]:
        point=est(z,key+'_real');ns=list(z['soporte_ajuste']['N_en_soporte'].values()) if key.startswith('adjusted') else [point['N_grupo'],point['N_referencia']]
        rows.append([label,'/'.join(n(v,0) for v in ns),ci(est(z,key+'_nominal')),ci(point)])
    table('incorporacion','Nuevos menos continuos: diferencias de medianas mensuales en K2012--2015 y A2015--2018',
        ['Vía y comparación','N nuevos/continuos',r'Nominal [IC95\%]',r'Real [IC95\%]'],rows,
        r'Directas 60+ basales, destino directo y recepción conocida en ambas visitas; montos íntegros entre eventos captados en destino. IC percentiles por persona, 9,999 réplicas. Composición común: sexo, edad y escolaridad basales, soporte fijo, cuantiles de CDF. Evidencia IMSS/ISSSTE puede coexistir con otras instituciones: no reparte el importe ni identifica régimen. Pesos reales de septiembre de2026; no IC de diseño.')
    rows=[]
    for z in [k,a]:
        for key,label in [('median_change_principal','Periodo principal'),('median_change_12m','Doce meses previos'),('median_change_ano_entrevista','Año de entrevista')]:
            point=est(z,key);rows.append([z['via']+f"{z['origen']}--{z['destino']}",label,n(point['N_grupo'],0),ci(point),ci(est(z,key,True))])
    point=est(k,'median_change_stable_ss');rows.append(['K2012--2015','Un evento; misma contingencia/institución',n(point['N_grupo'],0),ci(point),ci(est(k,'median_change_stable_ss',True))])
    table('cambios','Mediana del cambio real individual entre receptores continuos',
        ['Vía y periodo','Criterio','N pares',r'$\Delta$ [IC95\%]',r'Por folio [IC95\%]'],rows,
        r'Montos mensuales íntegros captados en ambas visitas; cambio final menos inicial de cada persona. Pesos de septiembre de2026. Principal: promedio INPC del año anterior a entrevista real; alternativas conservan los mismos pares. Folio cunicah es sensibilidad, no hogar actual o UPM validada. La última fila cambia el universo y no acredita misma prestación administrativa. No se imputan pagos tras fallecimiento.')
    sex=d['precision']['sexo2012_2015'];rows=[]
    for label,keys in [('Cobertura K (pp)',['gap_K_2012','gap_K_2015','change_gap_K']),('Cobertura unión K/A (pp)',['gap_KA_2012','gap_KA_2015','change_gap_KA']),('Mediana K nominal (pesos/mes)',['gap_money_partial_2012_nominal','gap_money_partial_2015_nominal','change_gap_money_partial_nominal']),('Mediana K real (pesos/mes)',['gap_money_partial_2012_real','gap_money_partial_2015_real','change_gap_money_partial_real'])]:rows.append([label,*[ci(est(sex,key)) for key in keys]])
    distributions=sex['principal']['distribuciones']
    def pair_counts(via: str, year: int) -> str:
        """Extrae ambos denominadores de sexo de los mismos agregados de precisión."""
        return '/'.join(n(distributions[f'{via}_{year}_{group}']['N'],0) for group in ['men','women'])
    money_counts=[]
    for year in [2012,2015]:
        money_counts.append('/'.join(n(next(x['N_monto'] for x in sex['denominadores_monto']
            if (x['ronda'],x['sexo'],x['criterio'])==(year,group,'partial')),0) for group in ['Hombre','Mujer']))
    denominator_note=(r'Cobertura K: N conocidos H/M en2012='+pair_counts('K',2012)
        +' y2015='+pair_counts('K',2015)+r'; unión: '+pair_counts('KA',2012)+' y '+pair_counts('KA',2015)
        +r'. Montos K parciales: '+' y '.join(money_counts)+r' entre receptores. Elegibles por corte: '
        +n(rounds[2012]['N_elegible'],0)+'/'+n(rounds[2015]['N_elegible'],0)
        +r'; ND no es negativa. Bootstrap conjunto de '+n(sex['principal']['N_personas'],0)+r' IDs ('
        +n(sex['principal']['N_filas'],0)+r' personas-ronda), con todas sus visitas. IC puntuales condicionales; '
        +r'pesos reales de septiembre de2026. El cambio de brecha entre cortes no es cambio individual.')
    table('sexo','Brechas hombre--mujer y cambio de brecha, directas 60+, 2012--2015',
        ['Indicador y unidad',r'Brecha2012 [IC95\%]',r'Brecha2015 [IC95\%]',r'Cambio2015--2012 [IC95\%]'],rows,
        denominator_note)
    for z,prefix in [(k,'K'),(a,'A')]:
        put(prefix+'.Basal',z['N_basal'],0);put(prefix+'.Conocidos',z['N_pares_conocidos'],0)
        for group,name in [('new','Nuevo'),('cont','Continuo')]:
            for unit in ['real','nominal']:
                x=z['principal']['distribuciones'][group+'_'+unit];put(prefix+'.'+name+'.'+unit,x['mediana']);put(prefix+'.'+name+'.N',x['N'],0)
            x=next(x for x in z['faltantes'] if x['grupo']==('No→Sí' if group=='new' else 'Sí→Sí'))
            put(prefix+'.'+name+'.Recepcion',x['N_recepcion'],0);put(prefix+'.'+name+'.Faltantes',x['N_sin_monto'],0)
        for stem,key in [('Contraste','new_minus_cont_real'),('Ajustado','adjusted_new_minus_cont_real'),('Cambio','median_change_principal'),('Negativos','negative_change_pct'),('DoceMeses','median_change_12m'),('Anual','median_change_ano_entrevista')]:pe(prefix+'.'+stem,z,key)
        b=z['cotas_cambio_individual'];put(prefix+'.Pares',b['N_validos'],0);put(prefix+'.SinCambio',b['N_faltantes'],0)
        numbers[prefix+'.CotaCambio']=r'\ensuremath{['+n(b['inferior'])+r';\,'+n(b['superior'])+']}'
        for q in ['q25','q75']:put(prefix+'.Cambio.'+q,z['principal']['distribuciones']['change_principal'][q])
        for x in d['transitions']['transiciones']:
            if (x['via'],x['origen'],x['destino'])!=(z['via'],z['origen'],z['destino']):continue
            for stem,state in [('Muertes','Fallecido registrado'),('Ausencias','Ausente; vital desconocido'),('Sustitutos','Sustituto vivo; fuera del principal')]:put(prefix+'.'+stem,next(s['N'] for s in x['estados'] if s['estado']==state),0)
        old=next(x for x in d['transitions']['analisis'] if x['via']==prefix);put(prefix+'.OtraVia',old['otra_via_previa']['N_otra_via_basal_si'],0)
    pe('K.Institucional',k,'ss_new_minus_cont_real');pe('K.DiferenciaContrastes',k,'total_minus_ss_contrast_real')
    for stem,key in [('K','change_gap_K'),('Union','change_gap_KA'),('Monto','change_gap_money_partial_real')]:pe('Sexo.'+stem,sex,key)
    for z in d['synthesis']['perfiles2021']:
        names={('educacion_grupo','0 años'):'SinEscuela',('educacion_grupo','≥10 años'):'AltaEscuela',('edad_06','60–64'):'EdadTemprana',('edad_06','70+'):'EdadMayor',('localidad_grupo','<100 mil habitantes'):'LocalidadMenor',('localidad_grupo','≥100 mil habitantes'):'LocalidadMayor'}
        if (z['dimension'],z['grupo']) not in names:continue
        pre='Perfil.'+names[(z['dimension'],z['grupo'])]
        for stem,key in [('Union','KA_pct'),('UnionN','N_KA_conocido'),('UnionSi','N_KA_si')]:put(pre+'.'+stem,z['cobertura'][key],0 if stem in ['UnionN','UnionSi'] else 2)
        put(pre+'.MontoN',z['K']['N_monto'],0);put(pre+'.Real',z['K']['real']['mediana']);put(pre+'.Nominal',z['K']['nominal']['mediana'])
    macro_path=tables/'tesis_cifras.tex';macro_path.write_text('% Exportado desde agregados06--08; sin microdatos.\n'+'\n'.join(r'\expandafter\def\csname tesisdato:'+key+r'\endcsname{'+value+'}' for key,value in numbers.items())+'\n')
    mp=interim/'migracion_proyecto.json';migration=json.loads(mp.read_text())
    migration['redaccion_formal']['exportacion']={'fuentes':{str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest() for p in paths.values()},'cuadros':products,'macros':list(numbers),'sha_macros':sha256(macro_path.read_bytes()).hexdigest(),'analisis_nuevos':False}
    mp.write_text(json.dumps(migration,ensure_ascii=False,indent=2)+'\n')
    print('Redacción formal:',len(products),'cuadros;',len(numbers),'cifras/comparaciones exportadas; sin recálculo.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--formal',action='store_true',help='Exportar selección académica06--08 validada.')
    args=parser.parse_args()
    if args.formal:export_formal()
    else:
        export()
        print('J02: cuatro tablas, cifras, dos figuras y narrativa desde agregados.')
