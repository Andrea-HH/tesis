"""Figuras e interpretación del EDA pensionario de salud; solo agregados calculados."""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from .pension_health import DIMENSIONS,YEARS,OUTPUT,BINARY
from .project_paths import FIGURES_DIR

LABELS={'salud_glob':'Salud autopercibida (1 excelente–5 mala)','diabetes':'Diagnóstico declarado de diabetes',
 'n_enf':'Enfermedades crónicas (0–7)','bmi_imp':'IMC promedio imputado (kg/m²)',
 'n_sint_depr':'Síntomas CES-D (0–9)','cesd_deprimido':'CES-D: cinco o más síntomas',
 'solo':'Soledad declarada en la última semana','recuerdo1':'Aprendizaje verbal imputado (0–8)',
 'recuerdo2':'Evocación imputada (0–8)','orientacion':'Orientación imputada (0–3)',
 'serial7':'Restas seriadas imputadas (0–5)','n_abvd':'Limitaciones ABVD (0–5)',
 'n_aivd':'Limitaciones AIVD (0–4)','n_mov':'Limitaciones de movilidad (0–5)'}


def make_figures(results: dict) -> list[dict]:
    """Produce paneles comparativos; no una figura por cada variable/ronda/estrato."""
    plt.rcParams.update({'font.size':10,'axes.labelsize':10,'axes.titlesize':11,'legend.fontsize':9})
    colors=plt.get_cmap('BrBG');figures=[]
    FIGURES_DIR.mkdir(exist_ok=True)
    def save(fig,key,title,note):
        fig.text(.03,.015,note,fontsize=9,ha='left')
        fig.tight_layout(rect=(0,.09,1,.94))
        path=FIGURES_DIR/f'pensiones_salud__{key}.png';fig.savefig(path,dpi=200);plt.close(fig)
        figures.append({'clave':key,'archivo':str(path.relative_to(FIGURES_DIR.parent)),'titulo':title,'nota':note})
    for dim,names in DIMENSIONS.items():
        variables=[v for v in names if v in LABELS]
        fig,axes=plt.subplots(2,2,figsize=(8.3,6.6),squeeze=False)
        for ax,var in zip(axes.flat,variables):
            rows=[x for x in results['principal'] if x['variable']==var]
            years=[x['ano'] for x in rows];estimate=[x['efecto'] for x in rows]
            lo=[x['efecto']-x['ic95_inferior'] for x in rows];hi=[x['ic95_superior']-x['efecto'] for x in rows]
            ax.errorbar(range(len(rows)),estimate,yerr=[lo,hi],fmt='o-',color=colors(.13),capsize=3,linewidth=1.4)
            ax.axhline(0,color='#777777',linewidth=.8,linestyle='--')
            ax.set_xticks(range(len(rows)),years,rotation=35);ax.set_title(LABELS[var],wrap=True)
            ax.set_ylabel('Diferencia (pp), K sí − K no' if var in BINARY else 'Delta de Cliff, K sí − K no')
            ax.set_xlabel('Ronda nominal')
            for n,row in enumerate(rows):
                ax.annotate(f"{row['N_si_valido']}/{row['N_no_valido']}",(n,estimate[n]),xytext=(0,7),textcoords='offset points',fontsize=7,rotation=20)
        for ax in list(axes.flat)[len(variables):]:ax.set_visible(False)
        title=f'{dim}: contrastes por recepción propia K en seis visitas'
        fig.suptitle(title+'\n60+ por visita; no ponderado',fontsize=13)
        save(fig,{'Física':'fisica','Mental':'mental','Cognición':'cognicion','Funcionalidad':'funcionalidad'}[dim],title,
             'IC 95% puntuales y condicionales; números: N válido K sí/K no. No inferencia nacional ni causal.\nDelta positivo = valores mayores con K; sentido clínico depende del indicador. Imputación no incluida en IC.')
    # Distribuciones completas de cuatro indicadores, en una sola figura.
    variables=['n_enf','n_sint_depr','recuerdo2','n_aivd']
    fig,axes=plt.subplots(2,2,figsize=(8.3,6.6))
    for ax,var in zip(axes.flat,variables):
        row=next(x for x in results['principal'] if x['ano']==2021 and x['variable']==var)
        for group,color,label in [('True',colors(.13),'K propia afirmativa'),('False',colors(.86),'Negativa K propia')]:
            data=next(x for x in row['distribuciones'] if x['grupo']==group)
            values=[x['valor'] for x in data['frecuencias']];cumulative=np.cumsum([x['N'] for x in data['frecuencias']])/data['N_valido']*100
            ax.step(values,cumulative,where='post',color=color,label=f"{label}; N={data['N_valido']:,}",linewidth=1.6)
        ax.set_title(LABELS[var],wrap=True);ax.set_ylabel('Porcentaje acumulado de válidos');ax.set_xlabel('Puntuación del indicador');ax.legend(loc='lower right',fontsize=7)
    title='Distribuciones por K propia: cuatro dimensiones, 2021'
    fig.suptitle(title+'\n60+ elegibles según indicador; no ponderado',fontsize=13)
    save(fig,'distribuciones_2021',title,'No se mezclan pruebas cognitivas ni unidades; recuerdo2 es imputado.\nCada curva tiene su denominador válido. Desconocidos no son negativas K ni ceros de salud.')
    # Estratificaciones seleccionadas con tres variables simultáneas.
    pairs=[('n_sint_depr','sexo_grupo'),('diabetes','sexo_grupo'),('salud_glob','edad_salud'),
           ('n_aivd','edad_salud'),('recuerdo1','educacion_grupo'),('recuerdo1','patrimonio_cuartil')]
    for chunk in range(0,len(pairs),2):
        fig,axes=plt.subplots(2,1,figsize=(8.3,7.5))
        for ax,(var,strat) in zip(axes,pairs[chunk:chunk+2]):
            rows=[x for x in results['trivariados'] if x['ano']==2021 and x['variable']==var and x['estratificador']==strat and x.get('efecto') is not None]
            labels=[f"{x['estrato']} (N {x['N_si_valido']}/{x['N_no_valido']})" for x in rows]
            estimates=np.array([x['efecto'] for x in rows]);low=np.array([x['ic95_inferior'] for x in rows]);high=np.array([x['ic95_superior'] for x in rows])
            ax.errorbar(estimates,range(len(rows)),xerr=[estimates-low,high-estimates],fmt='o',color=colors(.15),capsize=3)
            ax.set_yticks(range(len(rows)),labels);ax.axvline(0,color='#888888',linestyle='--',linewidth=.8)
            ax.set_xlabel('Diferencia (pp), K sí − K no' if var in BINARY else 'Delta de Cliff, K sí − K no')
            ax.set_title(LABELS[var]+' × '+strat.replace('_',' '));ax.invert_yaxis()
        title=f'Contrastes condicionados por {pairs[chunk][1].replace("_grupo","").replace("_salud","")}: 2021'
        fig.suptitle(title+'\n60+; K propia × indicador × estrato',fontsize=13)
        save(fig,f'trivariado_{chunk//2+1}',title,'IC puntuales; N válido K sí/K no. Celdas con <30 por rama no estimadas.\nCuartiles: patrimonio persona/cónyuge relativo a la ronda; no ingreso ni pobreza. No prueba formal de interacción.')
    return figures


def conclusions(results: dict) -> list[str]:
    """Narrativa integrada basada en cifras existentes del nuevo agregado."""
    def main(var):return next(x for x in results['principal'] if x['ano']==2021 and x['variable']==var)
    def adjusted(var):return next(x for x in results['estandarizados'] if x['ano']==2021 and x['variable']==var)
    mental=main('n_sint_depr');diabetes=main('diabetes');verbal=main('recuerdo1');adj=adjusted('n_sint_depr')
    return [
      f"En 2021, síntomas CES-D presentan mediana {mental['si']['mediana']:g} entre K propias afirmativas y {mental['no']['mediana']:g} entre negativas K propias (N válido {mental['N_si_valido']:,}/{mental['N_no_valido']:,}); delta={mental['efecto']:.3f}. La diferencia de diabetes diagnosticada declarada es {diabetes['efecto']:.2f} pp, en dirección contraria a una lectura de mejor salud física general. Diagnóstico declarado puede depender también de detección y contacto sanitario; no se identifica ese mecanismo en estos datos.",
      "Los síntomas depresivos y la soledad muestran contrastes brutos negativos en las seis rondas; el número de enfermedades crónicas presenta contrastes positivos pequeños. La salud autopercibida usa 1=excelente y 5=mala: un delta negativo implica valores declarados mejores. Las diferencias ABVD/AIVD/movilidad son pequeñas o cambian de signo; se conservan porque no respaldan una mejora funcional general asociada a K.",
      f"Aprendizaje verbal imputado tiene delta global {verbal['efecto']:.3f} en 2021, pero los cinco estratos de escolaridad conocidos muestran deltas negativos. Evocación no conserva una dirección positiva en todas las rondas. No son pruebas intercambiables; orientación falta en 2001 y restas seriadas antes de 2015. El contraste marginal no reemplaza las comparaciones condicionadas.",
      "Los contrastes físicos varían por sexo: diabetes y enfermedades crónicas muestran diferencias mayores entre hombres en 2021; síntomas depresivos tienen un contraste negativo en ambos sexos, de mayor magnitud entre hombres. Salud global y funcionalidad se contrastan dentro de grupos de edad; aprendizaje verbal se contrasta dentro de escolaridad y cuartiles de patrimonio. Son patrones descriptivos, no pruebas de modificación causal o interacción confirmatoria.",
      f"La estandarización de síntomas CES-D por sexo, edad, escolaridad agrupada y modalidad cambia la diferencia media cruda en el mismo soporte de {adj['diferencia_cruda_mismo_soporte']:.3f} a {adj['diferencia_estandarizada']:.3f} síntomas (IC condicional [{adj['ic95_inferior']:.3f}, {adj['ic95_superior']:.3f}]; N soporte={adj['N_soporte']:,}, fuera de soporte={adj['N_fuera_soporte']:,}). Su IC incluye cero. Esta media estandarizada no es el delta de rangos; agrupación de escolaridad, forma de la distribución y selección del soporte pueden mantener diferencias residuales. El ajuste no elimina automáticamente sesgo.",
      "A propia y pensión del cónyuge muestran perfiles distintos de K propia. En 2021, el contraste de síntomas CES-D con A es positivo, mientras que con cónyuge confirmado es cercano a cero. La comparación de cónyuge utiliza solo parejas confirmadas (2018/2021); antes queda pendiente. A reúne donativos públicos adicionales en dinero o especie, no una pensión no contributiva homologada. Ninguna de estas ramas se interpreta como ingreso del hogar distribuido entre personas.",
      "Las siguientes etapas podrían estudiar continuidad de recepción y cambios en síntomas, memoria y funcionalidad siguiendo los mismos IDs, con muerte, ausencia, reaparición y ND separados, y contratos explícitos por intervalo. No se ha ejecutado ese seguimiento de salud ni se adopta una pregunta definitiva. Los IC presentes son puntuales, no simultáneos ni representativos del diseño nacional; tampoco incluyen incertidumbre entre imputaciones."
    ]
