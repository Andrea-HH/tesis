"""Figuras e interpretación07 derivadas exclusivamente de agregados."""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import re

from .economic_protection_outputs import readable_prose

from .monetary_policy import REFERENCE
from .project_paths import RESULTS_DIR


def readable(text: str) -> str:
    """Ajusta espacios de prosa07, conservando nombres de producto, código y enlaces."""
    text=readable_prose(text)
    pieces=re.split(r'(\]\([^)]*\)|`[^`]*`)',text)
    for i,piece in enumerate(pieces):
        if piece.startswith(('](','`')):continue
        piece=re.sub(r'\b(INPC|INEGI|DOF|CONEVAL|LPI|PAM)(?=[a-záéíóúñ])',r'\1 ',piece)
        piece=re.sub(r'(?<=[a-záéíóúñ])(?=(?:INPC|INEGI|DOF|CONEVAL|LPI|PAM)\b)',' ',piece)
        for a,b in {'año calendarioprevio':'año calendario previo','año realdeentrevista':'año real de entrevista',
                    'deespecie':'de especie','deimpuestos':'de impuestos','deperiodos':'de periodos',
                    'de montoPAM':'de monto PAM','de pagosobservados':'de pagos observados',
                    'Los segundos se inventarían':'Las versiones alternativas se documentan',
                    'montosbasales':'montos basales','Mortalidadcompleta':'Mortalidad completa',
                    'directasentrevistadas':'directas entrevistadas','declareda':'declarada',
                    'INEGI publicadoDOF':'INEGI publicado en el DOF'}.items():piece=piece.replace(a,b)
        pieces[i]=piece
    return ''.join(pieces)


def amount(r: dict, year: int, via: str, dimension: str="General", group: str="Todas") -> dict:
    """Localiza un estimando monetario, conservando vía, población y ronda."""
    return next(x for x in r['montos'] if (x['ronda'],x['via'],x['dimension'],x['grupo'])==(year,via,dimension,group))


def conclusions(r: dict) -> list[str]:
    """Lectura cuantificada, sin atribución causal ni pobreza de persona/hogar."""
    k,a=amount(r,2021,'K'),amount(r,2021,'A')
    k12,k15=[amount(r,y,'K') for y in [2012,2015]]
    a12,a15,a18=[amount(r,y,'A') for y in [2012,2015,2018]]
    def med(z,u='real'):return z['persona'][u]['mediana']
    def change(x,y,u='real'):return 100*(med(y,u)/med(x,u)-1)
    men,women=[amount(r,2021,'K','sexo_grupo',g) for g in ['Hombre','Mujer']]
    low,high=[amount(r,2021,'K','educacion_grupo',g) for g in ['0 años','≥10 años']]
    norm=next(x for x in r['comparacion_A5'] if x['dimension']=='General')
    return [readable(z) for z in [
        f"**Nominal y real pueden discrepar.** En 2012–2015 la mediana K sigue en ${med(k12,'nominal'):,.0f} nominales, mientras baja de ${med(k12):,.0f} a ${med(k15):,.0f} de septiembre de 2026 ({change(k12,k15):.2f}%). Los N con monto son {k12['N_monto']:,} y {k15['N_monto']:,}. A pasa de ${med(a12,'nominal'):,.0f} a ${med(a15,'nominal'):,.0f} nominales ({change(a12,a15,'nominal'):+.2f}%), pero de ${med(a12):,.0f} a ${med(a15):,.0f} reales ({change(a12,a15):+.2f}%; N={a12['N_monto']:,}/{a15['N_monto']:,}). Es una comparación condicionada entre muestras de receptores, con cambios de slots K y composición; no pérdida individual ni efecto causal.",
        f"**Poder adquisitivo sin aumento nominal suficiente.** A2015–2018 sube nominalmente {change(a15,a18,'nominal'):.2f}%, pero la mediana real baja {abs(change(a15,a18)):.2f}%. El monto normativo PAM permaneció en $580 mensuales durante2014–2018. El patrón es compatible con erosión por precios, pero A incluye otros programas y especie; no se identifica a todos los beneficiarios PAM ni se atribuye a la política.",
        f"**Montos y distribución en 2021.** La suma parcial K tiene mediana ${med(k,'nominal'):,.0f} nominal y ${med(k):,.0f} real (N={k['N_monto']:,}); A ${med(a,'nominal'):,.0f}/${med(a):,.0f} (N={a['N_monto']:,}). Los receptores son universos distintos. A general valora también especie, de modo que no es una comparación homogénea de efectivo; el programa de vejez identificado se examina por separado. No se suman K+A.",
        f"**Brechas entre receptores K.** Hombres: ${med(men,'nominal'):,.0f} nominal/${med(men):,.0f} real, N={men['N_monto']:,}; mujeres: ${med(women,'nominal'):,.0f}/${med(women):,.0f}, N={women['N_monto']:,}. La brecha de medianas reales es ${med(men)-med(women):,.0f} y la razón {med(men)/med(women):.2f}. Con ≥10 años de escolaridad son ${med(high,'nominal'):,.0f}/${med(high):,.0f} (N={high['N_monto']:,}), frente a ${med(low,'nominal'):,.0f}/${med(low):,.0f} sin escolaridad (N={low['N_monto']:,}); razón real {med(high)/med(low):.2f}. Son diferencias descriptivas sin ajuste de composición; escolaridad corresponde al inicio de la participación.",
        f"**Una mediana A común no garantiza suficiencia.** En2021 A tiene mediana de {a['persona']['lpi_pct']['mediana']:.2f}% de la LPI asignable, con N={a['persona']['N_lpi']:,}; {a['persona']['N_geografia_ND_monto']:,} montos no tienen geografía asignable. El {a['persona']['prestacion_inferior_lpi_pct']:.2f}% de los montos parciales A queda por debajo de esa referencia. K tiene mediana {k['persona']['lpi_pct']['mediana']:.2f}%, pero {k['persona']['prestacion_inferior_lpi_pct']:.2f}% queda por debajo. No son porcentajes de pobreza, ni evaluación de ingreso total o protección completa.",
        f"**Programa identificado y ambigüedad temporal.** A5 de vejez2021 reúne {norm['N_eventos']:,} eventos/{norm['N_personas']:,} personas, mediana ${norm['declarado']['nominal']['mediana']:,.0f} nominal. Es {norm['norma_periodo_principal']['razon_pct']['mediana']:.2f}% de la referencia normativa del año previo bajo el criterio principal. Solo {norm['norma_entrevista']['N_iguales']:,} importes coinciden exactamente con la norma del mes de entrevista. El año previo, la ventana de recuerdo y la regla vigente son referencias diferentes; no demuestra sobrepago, incumplimiento o cobertura legal. Hay respuestas de menores de65 y entrevistas2022, conservadas y documentadas.",
        "**Alcance de la hipótesis.** En2021 la unión K/A reduce las brechas de acceso por sexo/localidad en el mismo soporte del notebook06, pero persisten diferencias grandes de montos K y A aporta un valor bajo relativo a la LPI. Sin escolaridad combina mayor cobertura de unión que ≥10 años con menor monto K. La evidencia es parcialmente consistente con acceso más extendido que recursos suficientes; no demuestra convergencia general2001–2021. La mediana A común y algunos aumentos reales son evidencia favorable para ciertos componentes; las rupturas, faltantes y composición impiden una conclusión única.",
        "**Selección actuarial como sensibilidad.** La comparación basal frente a retenidos y los cambios de quienes reciben en ambas visitas son estimandos diferentes de las medianas transversales. Muerte registrada, ausencia vital desconocida, sustituto vivo y recepción ND permanecen separados. Las cotas06 no asignan prestaciones después de morir; no corrigen automáticamente montos ni sesgo de selección. Sin pesos longitudinales, mortalidad completa ni fechas de pago no se estima valor presente actuarial, causalidad o representatividad nacional.",
    ]]


def make_figures(r: dict) -> list[dict]:
    """Paneles científicos BrBG, sin confundir escalas nominales/reales o universos."""
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    brown,teal=plt.get_cmap('BrBG')(.12),plt.get_cmap('BrBG')(.88)
    figures=[]
    def save(fig,key,title,note):
        title,note=readable(title),readable(note)
        fig.suptitle(title,fontsize=13,y=.995)
        fig.text(.02,.018,note,fontsize=8)
        fig.tight_layout(rect=[0,.09,1,.94])
        name=f'figuras/politicas_montos__{key}.png'
        fig.savefig(RESULTS_DIR/name,dpi=210);plt.close(fig)
        figures.append(dict(clave=key,titulo=title,archivo=name,nota=note))
    years=[2001,2003,2012,2015,2018,2021]
    fig,axes=plt.subplots(2,2,figsize=(11,8))
    for row,via,c in [(0,'K',brown),(1,'A',teal)]:
        data=[amount(r,y,via) for y in years]
        for col,unit in enumerate(['nominal','real']):
            ax=axes[row,col]; stats=[z['persona'][unit] for z in data]
            ax.errorbar(years,[z['mediana'] for z in stats],
                yerr=[[z['mediana']-z['q25'] for z in stats],[z['q75']-z['mediana'] for z in stats]],
                fmt='o',color=c,capsize=3,label='Mediana y cuartiles')
            for pair in r['comparabilidad']:
                if pair[via]:
                    a,b=[years.index(pair[k]) for k in ['origen','destino']]
                    ax.plot([years[a],years[b]],[stats[a]['mediana'],stats[b]['mediana']],':',color=c)
            ax.set_xticks(years);ax.tick_params(axis='x',rotation=40)
            ax.set_title(f'{via}: '+('pesos nominales' if unit=='nominal' else 'pesos de septiembre2026'))
            ax.set_ylabel('Pesos mensuales, suma parcial');ax.set_ylim(bottom=0)
    save(fig,'evolucion','Montos nominales y poder adquisitivo, seis rondas',
         'Directas60+ con monto observado. Barras: cuartiles, no IC. N en cuadros. Líneas: continuidad condicionada.\nK y A no tienen serie homogénea completa; A incluye especie. Precios del año previo a la entrevista real.')
    data=[z for z in r['montos'] if z['ronda']==2021 and z['via']=='K' and z['dimension'] in
          ['sexo_grupo','edad_06','educacion_grupo','localidad_grupo','ocupacion_grupo'] and z['grupo']!='Desconocido']
    fig,axes=plt.subplots(1,2,figsize=(13,8.8),sharey=True)
    pos=np.arange(len(data))
    for ax,unit in zip(axes,['nominal','real']):
        for via,c,marker in [('K',brown,'o'),('A5',teal,'s')]:
            ds=[next(x for x in r['comparacion_K_A5'] if x['dimension']==z['dimension'] and x['grupo']==z['grupo']) for z in data]
            ax.plot([z[via+'_evento'][unit]['mediana'] for z in ds],pos,marker,color=c,label=via if via=='K' else 'A5 de vejez')
        ax.set_xlabel('Pesos nominales' if unit=='nominal' else 'Pesos de septiembre2026')
        ax.set_xlim(left=0);ax.legend();ax.grid(axis='x',alpha=.15)
    axes[0].set_yticks(pos,[z['grupo'] for z in data],fontsize=9);axes[0].invert_yaxis()
    save(fig,'perfiles2021','Medianas por vía y perfil, 2021',
         'Montos por evento en directas60+. K frente a A5 de vejez con norma monetaria verificada; no todoA.\nReceptores diferentes, no K+A ni contributividadK. N/limitaciones en notebook; escolaridad inicial.')
    fig,axes=plt.subplots(1,2,figsize=(10,5.5))
    for ax,via,c in zip(axes,['K','A'],[brown,teal]):
        d=[amount(r,y,via) for y in years]
        ax.plot(years,[z['persona']['lpi_pct']['mediana'] for z in d],'o',color=c,label='Geografía asignable')
        for field,marker in [('escenario_todos_rural_pct','^'),('escenario_todos_urbana_pct','v')]:
            ax.plot(years,[z['persona'][field]['mediana'] for z in d],marker,alpha=.55,color=c,label=field.replace('escenario_todos_','').replace('_pct',''))
        ax.axhline(100,color='0.35',ls='--');ax.set_title(via);ax.set_xticks(years);ax.tick_params(axis='x',rotation=40)
        ax.set_ylabel('Mediana prestación / LPI (%)');ax.legend(fontsize=8);ax.set_ylim(bottom=0)
    save(fig,'umbral','Prestación parcial respecto de la LPI del periodo',
         'Directas60+ con monto y geografía asignable.2001/2003 asignable incluye solo≥100mil: selección distinta.\nEscenarios aplican ambas líneas a todos los montos; no clasifican ruralidad ni pobreza. No IC.')
    fig,axes=plt.subplots(1,2,figsize=(11,5.7))
    d=r['norma_programa'];x=np.arange(len(d))
    for ax,field,label in zip(axes,['nominal_mensual','real_mensual'],['Pesos nominales','Pesos de septiembre2026']):
        ax.bar(x,[z[field] for z in d],color=[plt.get_cmap('BrBG')(.15+i*.7/len(d)) for i in x])
        ax.set_xticks(x,[z['periodo'].replace('enero–junio','I').replace('julio–diciembre','II') for z in d],rotation=70)
        ax.set_ylabel(label+' / mes');ax.set_ylim(bottom=0)
    save(fig,'norma','Monto normativo federal nominal y real',
         '70yMás/PAM/Bienestar: referencia normativa, no importes observados ENASEM. Promedio INPC del periodo.\n2013 cambio desde segundo bimestre;2021-II vigencia8julio sin prorrateo diario. No equivale a todaA.')
    fig,axes=plt.subplots(1,2,figsize=(11,6))
    d=[z for z in r['seleccion'] if z['via']=='K' and z['dimension']=='sexo_grupo']
    for ax,unit in zip(axes,['nominal','real']):
        for i,(a,b) in enumerate([(2001,2003),(2012,2015),(2018,2021)]):
            for off,g,c in [(-.14,'Hombre',brown),(.14,'Mujer',teal)]:
                z=next(x for x in d if x['origen']==a and x['grupo']==g)
                lo=z[unit+'_basal']['mediana'];hi=z[unit+'_basal_retenidos']['mediana']
                ax.plot([i+off,i+off],[lo,hi],color=c,lw=2)
                ax.plot(i+off,lo,'o',color=c,label=g+' basal' if i==0 else None)
                ax.plot(i+off,hi,'s',mfc='white',color=c,label=g+' retenidos' if i==0 else None)
        ax.set_xticks(range(3),['2001–03','2012–15','2018–21']);ax.set_ylabel('Mediana K basal: '+unit)
        ax.set_ylim(bottom=0);ax.legend(fontsize=8)
    save(fig,'seleccion','Monto K basal de la cohorte y de quienes permanecen observables',
         'Directas60+ basales receptoras con monto; retenidos vivos/directos y K conocida en destino. N en notebook.\nNo corrección de sesgo ni ingreso después de muerte. Precios comunes2026, referencia basal individual.')
    return figures
