"""Exporta J02 desde agregados: cifras/tablas/figuras y narrativa, sin microdatos."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text

import json
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


if __name__=='__main__':
    export()
    print('J02: cuatro tablas, cifras, dos figuras y narrativa desde agregados.')
