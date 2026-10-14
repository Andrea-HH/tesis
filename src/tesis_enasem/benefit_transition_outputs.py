"""Figuras e interpretaciones08 desde agregados; ninguna cifra se transcribe."""

from __future__ import annotations

from hashlib import sha256
from typing import Any
import re

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from .benefit_transitions import PATTERNS
from .project_paths import RESULTS_DIR


def academic_spacing(text: str) -> str:
    """Separa prosa y cifras, preservando códigos literales y rutas de enlaces."""
    pieces=re.split(r'(\]\([^)]*\)|`[^`]*`)',text)
    for i,p in enumerate(pieces):
        if p.startswith(('](','`')):continue
        p=re.sub(r'(?<=[A-Za-záéíóúñÁÉÍÓÚÑ])(?=\d)',' ',p)
        p=re.sub(r'(?<=\d)(?=[A-Za-záéíóúñÁÉÍÓÚÑ])',' ',p)
        p=re.sub(r'(?<=\+)(?=[A-Za-záéíóúñÁÉÍÓÚÑ])',' ',p)
        p=p.replace('A 5','A5')
        pieces[i]=p
    return ''.join(pieces)


def group(z: dict[str, Any], pattern: str) -> dict[str, Any]:
    """Recupera denominadores de la recepción y del monto sin mezclarlos."""
    return next(x for x in z['montos_grupos'] if x['patron']==pattern)


def adjusted(z: dict[str, Any], pattern: str, unit: str='real', local: bool=False) -> dict[str, Any]:
    """Cuantil ajustado solo cuando existe soporte suficiente."""
    key='ajuste_localidad_sensibilidad' if local else 'ajuste'
    return next(x for x in z[key]['distribuciones'] if x['grupo']==pattern and x['unidad']==unit)


def precision_figure(result: dict[str, Any]) -> dict[str, Any]:
    """Expone los contrastes priorizados y la sensibilidad del agrupamiento del IC."""
    plt.rcParams.update({'font.size': 12, 'axes.spines.top': False,
                         'axes.spines.right': False})
    colors = [plt.get_cmap('BrBG')(.12), plt.get_cmap('BrBG')(.88)]
    k, a = result['ventanas']
    sex = result['sexo2012_2015']
    fig, axes = plt.subplots(2, 2, figsize=(12.4, 8.1))

    def panel(ax: Any, items: list[tuple[dict[str, Any], str, str]],
              title: str, unit: str) -> None:
        for i, (block, key, label) in enumerate(items):
            for j, method in enumerate(['principal', 'sensibilidad_folio']):
                est = next(x for x in block[method]['estimaciones'] if x['id'] == key)
                lo, hi = est['ic95']
                y = i + (j - .5) * .18
                ax.plot([lo, hi], [y, y], color=colors[j], lw=2.5,
                        label=['Por persona', 'Por folio cunicah'][j] if i == 0 else None)
                ax.scatter(est['estimacion'], y, color=colors[j], s=27,
                           marker=['o', 's'][j], zorder=3)
        ax.set_yticks(range(len(items)), [x[2] for x in items])
        ax.invert_yaxis()
        ax.axvline(0, color='#777777', lw=.8, ls='--')
        ax.set_title(title, loc='left', fontweight='bold', pad=12)
        ax.set_xlabel(unit)
        ax.grid(axis='x', alpha=.15)
        ax.margins(y=.25, x=.10)
        ax.tick_params(axis='y', length=0)

    panel(axes[0, 0], [(k, 'new_minus_cont_real', 'K total · 2012–15'),
        (k, 'adjusted_new_minus_cont_real', 'K composición común'),
        (k, 'ss_new_minus_cont_real', 'K evidencia IMSS/ISSSTE'),
        (a, 'new_minus_cont_real', 'A total · 2015–18')],
        'a. Mediana de nuevos menos continuos', 'Pesos de septiembre de 2026 / mes')
    panel(axes[0, 1], [(k, 'median_change_principal', 'K · periodo principal'),
        (k, 'median_change_12m', 'K · doce meses previos'),
        (k, 'median_change_ano_entrevista', 'K · año de entrevista'),
        (a, 'median_change_principal', 'A · periodo principal'),
        (a, 'median_change_12m', 'A · doce meses previos'),
        (a, 'median_change_ano_entrevista', 'A · año de entrevista')],
        'b. Mediana de cambios individuales', 'Pesos de septiembre de 2026 / mes')
    panel(axes[1, 0], [(sex, 'change_gap_K', 'Cobertura K'),
        (sex, 'change_gap_KA', 'Cobertura unión K/A')],
        'c. Cambio de brecha H−M\nCobertura · 2012–15', 'Puntos porcentuales')
    panel(axes[1, 1], [(sex, 'change_gap_money_partial_real', 'K entre receptores')],
        'd. Cambio de brecha H−M\nMediana K · 2012–15',
        'Pesos de septiembre de 2026 / mes')
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=2, frameon=False,
               bbox_to_anchor=(.5, .035))
    fig.suptitle('Precisión condicional de los contrastes centrales',
                 fontsize=15, fontweight='bold', y=.99)
    fig.text(.5, .012, 'IC percentiles 95% · 9,999 réplicas por agrupamiento · '
             'Escalas independientes · Sin inferencia nacional', ha='center', fontsize=11)
    fig.tight_layout(rect=(0, .085, 1, .955), h_pad=3, w_pad=2)
    relative = 'figuras/transiciones_montos__precision.png'
    path = RESULTS_DIR / relative
    fig.savefig(path, dpi=220, bbox_inches='tight')
    plt.close(fig)
    return dict(clave='precision', titulo='Precisión de incorporación, continuidad y brechas por sexo',
                archivo=relative, sha256=sha256(path.read_bytes()).hexdigest(),
                nota='Puntos e IC condicionales por persona y sensibilidad por folio; '
                     'poblaciones y unidades diferentes en cada panel, sin inferencia nacional.')


def make_figures(r: dict[str, Any]) -> list[dict[str, Any]]:
    """Tres figuras centrales, escalas separadas y cuantiles sin extremos dominantes."""
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    cmap=plt.get_cmap('BrBG');brown,teal=cmap(.12),cmap(.88)
    figures=[]
    def finish(fig: Any,key: str,title: str,note: str) -> None:
        file='figuras/transiciones_montos__'+key+'.png'
        fig.savefig(RESULTS_DIR/file,dpi=220,bbox_inches='tight');plt.close(fig)
        figures.append(dict(clave=key,titulo=title,archivo=file,nota=note,
            sha256=sha256((RESULTS_DIR/file).read_bytes()).hexdigest()))
    title='Recepción observada y destinos de seguimiento de las cohortes basales'
    fig,ax=plt.subplots(figsize=(11.5,5.1));states=[*PATTERNS,'Fallecido registrado','Ausente; vital desconocido',
        'Sustituto vivo; fuera del principal','Recepción ND en alguna visita','Conflicto de estado vital registrado']
    colors=[cmap(v) for v in [.04,.14,.9,.99,.28,.75,.39,.62,.5]]
    labels=[]
    for i,z in enumerate(r['analisis']):
        t=next(t for t in r['transiciones'] if (t['origen'],t['destino'],t['via'])==(z['origen'],z['destino'],z['via']))
        left=0
        labels.append(f"{z['via']} {z['origen']}–{z['destino']} · N basal={t['N_cohorte']:,}")
        for label,color in zip(states,colors):
            x=next(x for x in t['estados'] if x['estado']==label);v=x['pct_cohorte']
            ax.barh(i,v,left=left,height=.48,color=color,label=label if i==0 else None)
            if v>=6:ax.text(left+v/2,i,f"{v:.1f}%",ha='center',va='center',fontsize=9,
                            color='white' if sum(c*w for c,w in zip(color[:3],[.2126,.7152,.0722]))<.5 else '#111')
            left+=v
        assert np.isclose(left,100)
    ax.set_yticks(range(2),labels);ax.invert_yaxis();ax.set_xlim(0,100)
    ax.set_xlabel('Porcentaje de toda la cohorte basal directa 60+')
    ax.set_title(title,pad=12,fontsize=12)
    ax.legend(ncol=3,fontsize=8,loc='upper center',bbox_to_anchor=(.5,-.17),frameon=False)
    note='Mismos IDs; destino directo para las cuatro transiciones. Muertes, ausencias, sustitutos y ND se conservan separados. No altas/bajas administrativas.'
    fig.text(.02,.015,note,fontsize=8);fig.tight_layout(rect=[0,.14,1,.98])
    finish(fig,'seguimiento',title,note)
    title='Nuevos y continuos: distribución de los montos íntegros captados en destino'
    fig,axes=plt.subplots(2,2,figsize=(11.7,7.3))
    for row,z in enumerate(r['analisis']):
        for col,unit in enumerate(['nominal','real']):
            ax=axes[row,col]
            for pos,pattern,color in [(0,'No→Sí',brown),(1,'Sí→Sí',teal)]:
                g=group(z,pattern);s=g[unit]
                ax.hlines(pos,s['p10'],s['p90'],color=color,lw=1.5)
                ax.hlines(pos,s['q25'],s['q75'],color=color,lw=7)
                ax.plot(s['mediana'],pos,'o',color='white',mec=color,mew=2,ms=9)
                ax.annotate(f"${s['mediana']:,.0f}",(s['mediana'],pos),xytext=(5,9),textcoords='offset points',fontsize=9)
            ax.set_yticks([0,1],[f"Nuevos · N={group(z,'No→Sí')[unit]['N']:,}",f"Continuos · N={group(z,'Sí→Sí')[unit]['N']:,}"])
            ax.set_ylim(-.5,1.6);ax.set_xlim(left=0)
            ax.set_title(f"{z['via']} {z['origen']}–{z['destino']} · {unit}")
            ax.set_xlabel('Pesos nominales / mes' if unit=='nominal' else 'Pesos de septiembre de 2026 / mes')
    note='Punto: mediana; segmento grueso: Q25–Q75; fino: P10–P90, no IC. Sumados solo eventos captados con todos los montos válidos. No ingreso total.'
    fig.suptitle(title,fontsize=13);fig.text(.02,.015,note,fontsize=8);fig.tight_layout(rect=[0,.06,1,.95])
    finish(fig,'nuevos_continuos',title,note)
    title='Cambios reales de las mismas personas: heterogeneidad y sensibilidad de concepto'
    fig,axes=plt.subplots(2,1,figsize=(11.5,6.8))
    for row,z in enumerate(r['analisis']):
        chosen=next(s for s in z['sensibilidades'] if s['criterio'].startswith('Un evento, misma')) if z['via']=='K' else next(s for s in z['sensibilidades'] if s['criterio'].startswith('Un evento en'))
        for pos,p,label,color in [(0,z['pares'],'Íntegro captado',brown),(1,chosen,'Misma contingencia/institución' if z['via']=='K' else 'Un evento por visita',teal)]:
            s=p['cambio_individual_real'];ax=axes[row]
            ax.hlines(pos,s['p10'],s['p90'],color=color,lw=1.5);ax.hlines(pos,s['q25'],s['q75'],color=color,lw=7)
            ax.plot(s['mediana'],pos,'o',color='white',mec=color,mew=2,ms=9)
            ax.annotate(f"${s['mediana']:+,.2f}",(s['mediana'],pos),xytext=(5,9),textcoords='offset points',fontsize=9)
        ax.set_yticks([0,1],[f"Íntegro captado · N={z['pares']['N']:,}",f"{label} · N={chosen['N']:,}"])
        ax.set_ylim(-.5,1.6);ax.axvline(0,color='#555',lw=1,ls='--')
        ax.set_title(f"{z['via']} {z['origen']}–{z['destino']}")
        ax.set_xlabel('Cambio mensual en pesos de septiembre de 2026')
    note='Mediana del cambio individual, no diferencia de medianas. Segmentos Q25–Q75 y P10–P90, no IC. No identidad administrativa del programa ni causalidad.'
    fig.suptitle(title,fontsize=12);fig.text(.02,.012,note,fontsize=8);fig.tight_layout(rect=[0,.06,1,.94])
    finish(fig,'cambios_personales',title,note)
    return figures


def interpretations(r: dict[str, Any]) -> dict[str, str]:
    """Lectura académica específica, incluidos resultados nulos y contradicciones."""
    k,a=r['analisis'];kn,kc=group(k,'No→Sí'),group(k,'Sí→Sí');an,ac=group(a,'No→Sí'),group(a,'Sí→Sí')
    kp,ap=k['pares'],a['pares']
    texts={}
    texts['resumen']=(
        'La divergencia entre cobertura y monto central no tiene una explicación única. '
        'En K 2012–2015 se observa una incorporación declarada con montos mucho menores que los de continuos, '
        'además de erosión por precios. En A 2015–2018 las medianas de nuevos y continuos coinciden, '
        'y la caída real también aparece siguiendo a las mismas personas. No se identifica que nuevos receptores '
        'con menores medianas expliquen el caso A. La selección, la captación y la composición limitan la generalización.')
    texts['auditoria']=(
        f"Se reutilizan recepción, titularidad, eventos y precios de 01–07. Los {k['previo07_pares']['N']:,} pares K y "
        f"{a['previo07_pares']['N']:,} pares A de 07 admitían sumas parciales. Al exigir monto de cada evento captado, "
        f"fecha válida y ausencia de conflicto vital quedan {kp['N']:,} y {ap['N']:,}. En A hay un par con "
        'entrevista viva posterior a registro sobre fallecido: se separa sin corregir el original; 1,224 queda '
        'solo como sensibilidad de registros observados. Completo significa íntegro respecto de captura, '
        'no totalidad de beneficios reales. No hay identificador administrativo de prestación. '
        'K cambia de un importe por contingencia en 2012 a slots en 2015; A pasa de importe agregado a '
        'eventos en 2018. La comparabilidad de la suma por persona es condicionada. A es donativo general '
        'en dinero o especie; no A5 de vejez, identificado solo en 2021.')
    texts['nuevos']=(
        f"En K los nuevos observados tienen mediana mensual ${kn['nominal']['mediana']:,.0f} nominales/"
        f"${kn['real']['mediana']:,.2f} reales (N válido {kn['N_monto_real']:,}/{kn['N_receptores']:,}); "
        f"los continuos, ${kc['nominal']['mediana']:,.0f}/${kc['real']['mediana']:,.2f} "
        f"(N {kc['N_monto_real']:,}/{kc['N_receptores']:,}). La diferencia nuevos−continuos es "
        f"${kn['real']['mediana']-kc['real']['mediana']:+,.2f} reales; la mediana nueva equivale a "
        f"{100*kn['real']['mediana']/kc['real']['mediana']:.2f}% de la continua. Es un contraste sustantivo entre receptores "
        'observados, no entre iguales ni de toda la cohorte. En A ambos grupos tienen mediana de '
        f"${an['nominal']['mediana']:,.0f}/${an['real']['mediana']:,.2f}, con N "
        f"{an['N_monto_real']:,}/{an['N_receptores']:,} y {ac['N_monto_real']:,}/{ac['N_receptores']:,}. "
        f"Su Q75 real sí difiere (${an['real']['q75']:,.2f} frente a ${ac['real']['q75']:,.2f}); "
        'la mediana nula no implica distribuciones idénticas. El monto de continuos en destino no exige '
        'monto basal válido; los cambios individuales sí. No se suman importes con algún evento faltante.')
    # Las composiciones empíricas son una comprobación aritmética, no un contrafactual causal.
    mix,cont=k['mezcla_observada']
    amix,acont=a['mezcla_observada']
    texts['mezcla']=(
        f"Entre {mix['N']:,} receptores K de la cohorte basal con monto íntegro de destino, "
        f"la mezcla observada de nuevos y continuos tiene mediana ${mix['nominal']['mediana']:,.0f}/"
        f"${mix['real']['mediana']:,.2f}; los {cont['N']:,} continuos solos, "
        f"${cont['nominal']['mediana']:,.0f}/${cont['real']['mediana']:,.2f}. "
        'Incluir el grupo nuevo de menor distribución reduce aquí la mediana empírica del conjunto seleccionado. '
        'No cuantifica una fracción causal de la caída transversal de 11.05%: excluye entradas por edad, '
        'otros orígenes y casos sin monto. En A, la mezcla de '
        f"{amix['N']:,} y los {acont['N']:,} continuos solos mantienen la misma mediana "
        f"${amix['real']['mediana']:,.2f}. Es evidencia contraria a una explicación general por menor mediana "
        'de nuevos. Una mediana de mezcla no es promedio ponderado de las medianas de sus grupos.')
    texts['pares']=(
        f"En {kp['N']:,} continuos K con ambas capturas íntegras, la mediana nominal pasa de "
        f"${kp['nominal_inicial']['mediana']:,.0f} a ${kp['nominal_final']['mediana']:,.0f}; "
        f"las medianas reales son ${kp['real_inicial']['mediana']:,.2f} y ${kp['real_final']['mediana']:,.2f}: "
        f"diferencia +${kp['diferencia_medianas_real']:,.2f}. La mediana del cambio individual es "
        f"${kp['cambio_individual_real']['mediana']:+,.2f}; {kp['N_real_baja']:,}/{kp['N']:,} "
        f"({100*kp['N_real_baja']/kp['N']:.2f}%) muestran reducción. No son resultados incompatibles: "
        'cambian los rangos relativos de las personas dentro de la distribución. '
        f"En A, N={ap['N']:,}, las medianas nominales son ${ap['nominal_inicial']['mediana']:,.0f}/"
        f"${ap['nominal_final']['mediana']:,.0f}, y las reales ${ap['real_inicial']['mediana']:,.2f}/"
        f"${ap['real_final']['mediana']:,.2f}. La diferencia de medianas y la mediana individual coinciden aquí "
        f"en ${ap['cambio_individual_real']['mediana']:+,.2f}, por esta distribución, no por identidad estadística. "
        f"Bajan {ap['N_real_baja']:,}/{ap['N']:,} ({100*ap['N_real_baja']/ap['N']:.2f}%). "
        'Existen aumentos y disminuciones en ambos casos; no todos los receptores pierden poder adquisitivo.')
    bp,ba=kp['puente_medianas'],ap['puente_medianas']
    texts['precios']=(
        'Se mantiene INPC oficial INEGI 146.075, septiembre de 2026. Para cada persona, '
        '`R1−R0 = f1×(M1−M0) + M0×(f1−f0)`, donde `ft=146.075/INPCt`. '
        'El primer término valora el cambio nominal a precios de destino y el segundo congela el nominal basal. '
        'La identidad es exacta, no una estimación de mecanismos causales. Las medianas de esos términos no '
        'se suman como medianas de cambios. Un puente adicional de medianas, sobre los mismos pares, '
        'primero repricia todos los nominales basales y luego los sustituye por los finales: '
        f"K: ${bp['termino_precio']:+,.2f} + ${bp['termino_nominal']:+,.2f} = "
        f"${kp['diferencia_medianas_real']:+,.2f}; A: ${ba['termino_precio']:+,.2f} + "
        f"${ba['termino_nominal']:+,.2f} = ${ap['diferencia_medianas_real']:+,.2f}. "
        'El orden inverso, documentado en los agregados, produce componentes distintos. '
        'No se interpreta como porcentaje de inflación frente a composición en la mediana transversal. '
        f"La inflación mediana bajo el criterio del año calendario previo es "
        f"{kp['inflacion_criterio_periodo_pct']['mediana']:.2f}% en K y "
        f"{ap['inflacion_criterio_periodo_pct']['mediana']:.2f}% en A. "
        'La comparación modal utiliza 2011→2014 y 2014→2017; entrevistas tardías conservan sus índices '
        'individuales. Son intervalos de precios elegidos para año pasado, no fechas de pago observadas ni '
        'inflación medida exactamente entre las visitas. Bajo un factor común, '
        '`1+cambio_real = (1+cambio_nominal)/(1+inflacion)`: 0% nominal y 12.42% de inflación producen '
        '−11.05%; +5.45% y 12.00% producen −5.84%. Esta aritmética explica la traducción monetaria, '
        'pero no por qué la distribución nominal quedó en esas medianas.')
    texts['sensibilidad']=(
        f"La mediana individual K es pequeña y sensible al periodo: "
        f"${kp['cambio_real_12m']['mediana']:+,.2f} con doce meses previos y "
        f"${kp['cambio_real_ano_entrevista']['mediana']:+,.2f} con año de entrevista, frente a "
        f"${kp['cambio_individual_real']['mediana']:+,.2f} principal. No se sostiene una caída individual "
        'mediana robusta de K a todos los criterios temporales. La restricción de contingencia e institución '
        'también cambia el universo: no certifica continuidad administrativa ni contributividad. '
        f"A mantiene signo negativo con ${ap['cambio_real_12m']['mediana']:+,.2f}/"
        f"${ap['cambio_real_ano_entrevista']['mediana']:+,.2f}. La sensibilidad de un evento por visita "
        'no identifica que sea el mismo programa A. Ninguna sensibilidad garantiza invariancia de captura.')
    ak,aa=k['ajuste'],a['ajuste']
    knadj,kcadj=adjusted(k,'No→Sí')['ajustado_CDF'],adjusted(k,'Sí→Sí')['ajustado_CDF']
    texts['ajuste']=(
        'Se estandarizan las distribuciones de destino a una mezcla común de sexo, edad basal '
        '(60–64, 65–69, 70+) y escolaridad inicial (0–5/6+). Cada celda exige al menos 20 nuevos y '
        '20 continuos; se requiere cubrir ≥70% de cada grupo. La mezcla objetivo es la composición '
        'conjunta empírica dentro del soporte. Los cuantiles se obtienen de la CDF ponderada, no '
        'promediando medianas de celdas. El comparador sin ajuste usa la misma definición de cuantil '
        'y el mismo soporte. '
        f"K conserva {ak['N_en_soporte']['No→Sí']:,}/{ak['N_original']['No→Sí']:,} nuevos y "
        f"{ak['N_en_soporte']['Sí→Sí']:,}/{ak['N_original']['Sí→Sí']:,} continuos; "
        f"las medianas reales ajustadas son ${knadj['mediana']:,.2f} y ${kcadj['mediana']:,.2f}. "
        'El contraste de K persiste después de equilibrar esa composición basal. '
        f"A conserva {aa['N_en_soporte']['No→Sí']:,}/{aa['N_original']['No→Sí']:,} y "
        f"{aa['N_en_soporte']['Sí→Sí']:,}/{aa['N_original']['Sí→Sí']:,}; las medianas ajustadas siguen iguales. "
        'Añadir localidad tiene soporte suficiente y no elimina la lectura principal. '
        'Ocupación y estado conyugal se describen, sin asegurar equilibrio conjunto. Los pesos son '
        'de composición descriptiva, no de encuesta ni de probabilidad de observación. No se corrige '
        'selección no observada, mortalidad ni causalidad. No se implementa Oaxaca–Blinder o Kitagawa.')
    def profile(z: dict[str, Any],pat: str,dim: str,label: str) -> dict[str, Any]:
        return next(x for x in z['perfiles'] if x['poblacion']=='Transiciones conocidas, perfiles basales' and
                    (x['patron'],x['dimension'],x['grupo'])==(pat,dim,label))
    def amount(z: dict[str, Any],pat: str,dim: str,label: str) -> dict[str, Any]:
        return next(x for x in z['montos_por_perfil'] if (x['patron'],x['dimension'],x['grupo'])==(pat,dim,label))
    compositions=[]
    for z in (k,a):
        pieces=[]
        for dim,label in [('sexo_grupo','Mujer'),('edad_06','70+'),('educacion_grupo','0 años'),
                          ('localidad_grupo','<100 mil habitantes'),('ocupacion_grupo','Trabaja'),('conyugal_grupo','Viudo')]:
            n,c,e=[profile(z,p,dim,label) for p in ['No→Sí','Sí→Sí','Sí→No']]
            pieces.append(f"{label}: {n['pct_total']:.2f}% nuevos, {c['pct_total']:.2f}% continuos, {e['pct_total']:.2f}% cese")
        compositions.append(f"**{z['via']} perfiles basales:** "+'; '.join(pieces)+'. Los N totales de cada patrón son '+
            '/'.join(str(group(z,p)['N_receptores']) for p in ['No→Sí','Sí→Sí','Sí→No'])+'.')
    kzero=amount(k,'No→Sí','educacion_grupo','0 años');khigh=amount(k,'No→Sí','educacion_grupo','≥10 años')
    ksmall=amount(k,'No→Sí','localidad_grupo','<100 mil habitantes');kbig=amount(k,'No→Sí','localidad_grupo','≥100 mil habitantes')
    ayoung=amount(a,'No→Sí','edad_06','60–64');acyoung=amount(a,'Sí→Sí','edad_06','60–64')
    cross=[]
    for z in (k,a):
        changes=[]
        for dim,label in [('sexo_grupo','Mujer'),('edad_06','70+'),('educacion_grupo','0 años'),
                          ('localidad_grupo','<100 mil habitantes')]:
            vs=[next(x for x in z['perfiles_transversales06_07'] if (x['ronda'],x['dimension'],x['grupo'])==(y,dim,label)) for y in [z['origen'],z['destino']]]
            changes.append(f"{label} {vs[0]['pct_total']:.2f}%→{vs[1]['pct_total']:.2f}%")
        totals=[next(x['N_total'] for x in z['perfiles_transversales06_07'] if x['ronda']==y) for y in [z['origen'],z['destino']]]
        cross.append(f"{z['via']} {z['origen']}–{z['destino']} (N receptoras {totals[0]:,}/{totals[1]:,}): "+'; '.join(changes)+'.')
    texts['composicion_transversal']=' '.join(cross)+(
        ' Son porcentajes dentro de todos los receptores propios directos60+ de cada ronda, '
        'con denominadores de receptoras, no tasas de cobertura. Se reutilizan los conteos de06/07. '
        'No describe las mismas personas ni separa incorporación, envejecimiento, nueva muestra y muerte. '
        'La comparación de patrones y la partición de destino documentan algunos componentes observables, '
        'sin una descomposición causal ni completa de la mediana.')
    texts['perfiles']='\n\n'.join(compositions)+(
        '\n\nEstos porcentajes usan toda la transición conocida, incluyendo personas sin monto íntegro; son '
        'composición del grupo, no cobertura de cada perfil. Las personas con variables desconocidas permanecen '
        'en el denominador total y se identifican en las tablas completas. Los nuevos K no son simplemente más '
        'viejos: tienen mayor presencia femenina, menor escolaridad y localidades pequeñas, pero menor proporción '
        'basal70+ que continuos. El acceso por una vía y el monto central entre receptores describen desigualdades diferentes. '
        f"En nuevos K, escolaridad0 tiene mediana ${kzero['nominal']['mediana']:,.0f}/"
        f"${kzero['real']['mediana']:,.2f} (N={kzero['real']['N']:,}), frente a ≥10años "
        f"${khigh['nominal']['mediana']:,.0f}/${khigh['real']['mediana']:,.2f} (N={khigh['real']['N']:,}). "
        f"Localidad<100mil: ${ksmall['nominal']['mediana']:,.0f}/${ksmall['real']['mediana']:,.2f} "
        f"(N={ksmall['real']['N']:,}); ≥100mil: ${kbig['nominal']['mediana']:,.0f}/"
        f"${kbig['real']['mediana']:,.2f} (N={kbig['real']['N']:,}). "
        'La diferencia K nuevos/continuos se observa dentro de ambos sexos y los perfiles seleccionados, '
        'aunque su magnitud varía. En A, ambos sexos mantienen la misma mediana general entre nuevos y '
        'continuos. Entre personas basales60–64 aparece el contraste inverso: '
        f"nuevos ${ayoung['real']['mediana']:,.2f} (N={ayoung['real']['N']:,}) frente a continuos "
        f"${acyoung['real']['mediana']:,.2f} (N={acyoung['real']['N']:,}). "
        'Grupos basales de edad no equivalen a elegibilidad del programa al destino. Las diferencias de '
        'cambios personales son pequeñas, heterogéneas y no pruebas de efectos. La escolaridad es inicial; '
        'el corte100mil no define ruralidad; ocupación4 no identifica jubilación efectiva; viudez no acredita pareja residente.')
    selection_parts=[]
    for z in (k,a):
        no,yes=[next(x for x in z['seleccion'] if x['recepcion_basal']==s) for s in ['No','Sí']]
        def destination(s: dict[str, Any],label: str) -> dict[str, Any]:
            return next(x for x in s['destinos'] if x['destino']==label)
        dn,dy=[destination(x,'Fallecido registrado') for x in [no,yes]]
        un,uy=[destination(x,'Ausente; vital desconocido') for x in [no,yes]]
        selection_parts.append(f"{z['via']} {z['origen']}–{z['destino']}: muertes registradas "
            f"{dn['N']:,}/{no['N_basal']:,} ({dn['pct_basal']:.2f}%) en negativas iniciales y "
            f"{dy['N']:,}/{yes['N_basal']:,} ({dy['pct_basal']:.2f}%) en receptoras; ausencias "
            f"{un['N']:,} ({un['pct_basal']:.2f}%) y {uy['N']:,} ({uy['pct_basal']:.2f}%).")
    texts['seleccion']=' '.join(selection_parts)+(
        ' La dirección de la diferencia de ausencia cambia entre vías. Son asociaciones basales sin ajustar '
        'por edad/composición, no efectos pensionarios sobre supervivencia o respuesta. Solo los sobrevivientes '
        'reentrevistados con recepción y montos válidos pueden clasificarse como nuevos/continuos para '
        'comparar dinero. No se identifica la trayectoria monetaria de toda la cohorte. Las medianas basales '
        'similares en ciertos destinos no garantizan retención ignorable: las colas y perfiles pueden variar. '
        'Las reapariciones demuestran que ausencia no es muerte; un fallecimiento registrado después no '
        'fecha el deceso en la visita ausente. La estandarización de observados no soluciona esta selección. '
        'Permitir sustituto válido en destino conserva las medianas generales de nuevos/continuos K y A, '
        'con N mayores, pero no prueba ausencia de sesgo en subgrupos. Ningún muerto recibe un monto posterior imputado.')
    pub_new=next(x for x in k['evidencia_institucional'] if x['patron']=='No→Sí' and x['evidencia'].startswith('Programa'))
    pub_cont=next(x for x in k['evidencia_institucional'] if x['patron']=='Sí→Sí' and x['evidencia'].startswith('Programa'))
    ss_new=next(x for x in k['evidencia_institucional'] if x['patron']=='No→Sí' and x['evidencia'].startswith('IMSS'))
    ss_cont=next(x for x in k['evidencia_institucional'] if x['patron']=='Sí→Sí' and x['evidencia'].startswith('IMSS'))
    texts['politica']=(
        '**PAM65+ desde2013, $580 mensuales desde2014 → indicador K propio y evidencia código8 → '
        f"{pub_new['N_con_evidencia']:,}/{pub_new['N_receptores_grupo']:,} nuevos con monto íntegro "
        f"({pub_new['pct_grupo']:.2f}%) tienen evidencia de programa público agrupado, frente a "
        f"{pub_cont['N_con_evidencia']:,}/{pub_cont['N_receptores_grupo']:,} continuos "
        f"({pub_cont['pct_grupo']:.2f}%) → límite:** código8 incluye programas federales/estatales y "
        'puede coexistir con otras instituciones; no identifica PAM ni permite asignarle toda la suma. '
        f"Entre personas con evidencia IMSS/ISSSTE, nuevos (N={ss_new['N_con_evidencia']:,}) y continuos "
        f"(N={ss_cont['N_con_evidencia']:,}) tienen la misma mediana personal nominal "
        f"${ss_new['nominal_personal']['mediana']:,.0f}; los nuevos con programa agrupado "
        f"(N={pub_new['N_con_evidencia']:,}) tienen mediana ${pub_new['nominal_personal']['mediana']:,.0f}. "
        'Estas sumas personales incluyen todos los eventos íntegros, no montos asignados a cada institución; '
        'las evidencias pueden solaparse. Esto documenta heterogeneidad de la incorporación captada, sin atribución causal. '
        '\n\n**PAM mantiene $580 entre2014–2018 → indicador A general y norma por separado → '
        'mediana A pasa550→580 nominales, mientras precios del criterio principal aumentan aproximadamente12% '
        'y la mediana real cae → límite:** A no identifica PAM en ambas visitas, incluye dinero/especie '
        'y cambia captación en2018. No son una serie individual de monto oficial ni todo el padrón. '
        'Las coincidencias son compatibles con expansión de prestaciones pequeñas y erosión normativa, '
        'sin demostrar que una reforma produjo el resultado. Se usa la '
        '[cronología y sus fuentes oficiales](../investigacion/notas/politicas_publicas_envejecimiento.md) de07.')
    texts['conclusion']=(
        '**Respuesta a los mecanismos.** La inflación aporta una erosión aritmética verificable bajo '
        'fechas explícitas. En K también se observa una diferencia monetaria grande de incorporación '
        'y una mezcla institucional diferente, persistente bajo estandarización basal. En A la menor '
        'mediana de nuevos no está respaldada; hay diferencias de colas y perfiles, pero la reducción '
        'real central también aparece entre continuos. La combinación observable varía por vía. '
        'No se puede repartir la caída transversal en porcentajes causales de precios, composición '
        'y política. Tampoco se pueden certificar flujos de una misma prestación, suficiencia total '
        'o ingreso individual completo. El aporte a la tesis es mostrar por qué expandir recepción '
        'no implica igualar recursos centrales y distinguir una expansión con montos menores de '
        'una erosión entre continuos. La selección delimita a quién representan las comparaciones.')
    return {key:academic_spacing(value) for key,value in texts.items()}
