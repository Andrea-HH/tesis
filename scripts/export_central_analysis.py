"""Exportación central protegida y selección editorial de sensibilidades ya calculadas.

El modo --sensibilidades-fase-a solo lee agregados locales preexistentes. No
integra microdatos, calcula estimadores, compila PDF ni realiza operaciones Git.
La selección no sustituye la auditoría conjunta de divulgación previa a publicar.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER = 'sensibilidad_medicion_editorial'


def number(value: float, decimals: int = 1) -> str:
    """Convención numérica española: espacio fino en miles y coma decimal."""
    return f'{value:,.{decimals}f}'.replace(',', '@').replace('.', '{,}').replace('@', r'\,')


def interval(row: dict) -> str:
    """Solo contrastes con soporte mínimo explícito, nunca montos individuales."""
    if row.get('estimacion') is None or row.get('ic95') is None:
        return 'No estimado'
    if isinstance(row.get('N'), list) and min(row['N']) < 20:
        raise ValueError('Contraste monetario sin soporte mínimo20: exportación detenida')
    return number(row['estimacion'])+' ['+'; '.join(number(v) for v in row['ic95'])+']'


def block(target: Path, content: str) -> None:
    """Reemplaza exclusivamente el bloque de sensibilidades, de forma idempotente."""
    old = target.read_text()
    old = re.sub(r'\n?% BEGIN '+MARKER+r'\n.*?% END '+MARKER+r'\n?', '\n', old, flags=re.S)
    target.write_text(old.rstrip()+'\n\n% BEGIN '+MARKER+'\n'+content+'\n% END '+MARKER+'\n')


def table(label: str, caption: str, headers: list[str], rows: list[list[str]], note: str, widths: str) -> str:
    """Nota en pie final del longtable, para conservarla con el cuadro."""
    for old,new in [('con08','con 08'),('08de','08 de'),('8en','8 en'),('solo08','solo 08'),('Solo08','Solo 08'),('P/Cinferior','P/C inferior'),('yP/Csuperior','y P/C superior'),('C20/27','C 20/27'),('semilla202','semilla 202'),('septiembre2026','septiembre de 2026')]:
        note=note.replace(old,new)
    note=re.sub(r'(?<=\d)(?=[A-Za-záéíóúñ])',' ',note)
    note=re.sub(r'(?<=[A-Za-záéíóúñ])(?=\d)',' ',note)
    note=re.sub(r'([,;])(?=[A-Za-záéíóúñ])',r'\1 ',note)
    n=len(headers);header=' & '.join(headers)+r' \\'
    return '\n'.join([r'\begingroup\small\setlength{\tabcolsep}{3pt}',r'\begin{longtable}{'+widths+'}',
        r'\caption{'+caption+r'}\label{'+label+r'}\\',r'\toprule',header,r'\midrule\endfirsthead',
        r'\multicolumn{'+str(n)+r'}{l}{Continuación del cuadro \thetable}\\',r'\toprule',header,r'\midrule\endhead',
        r'\bottomrule\endfoot',r'\bottomrule',r'\multicolumn{'+str(n)+r'}{p{.96\textwidth}}{\footnotesize '+note+r'}\\',
        r'\endlastfoot',*[' & '.join(row)+r' \\' for row in rows],r'\end{longtable}',r'\endgroup'])


def export_sensitivities(source: Path) -> dict:
    """Selecciona tablas agregadas; no publica archivos fuente ni salidas completas."""
    data=json.loads((source/'resultados_auditoria.json').read_text())
    comp=json.loads((source/'complemento_auditoria.json').read_text())
    assert data['protocolo_sha256']=='e757c8449151e03e7a815c1bd0d46ccb64ce4793d9e7ac643d6b866f02d2b144'
    first='Incorporación desde ambas negativas';other='Incorporación con otra vía basal'
    row=next(w for w in data['ventanas'] if (w['via'],w['origen'],w['destino'])==('K',2012,2015))
    a=row['escenarios']['Principal'];b=row['escenarios']['Conservador08_ND']
    assert (a['N_nuevos'],b['N_nuevos'])==(1469,539)
    figures=[]
    for title,key in [('Nuevos','N_nuevos'),('Continuos','N_continuos')]:
        figures.append([title,number(a[key],0),number(b[key],0)])
    for title,key in [('P: desde ambas negativas',first),('C: otra vía basal',other)]:
        groups=[next(g for g in z['grupos'] if g['grupo']==key) for z in [a,b]]
        figures.append([title,' / '.join(number(g['N_receptor'],0)+' ('+number(g['monto']['N'],0)+')' for g in groups[:1]),
                        number(groups[1]['N_receptor'],0)+' ('+number(groups[1]['monto']['N'],0)+')'])
    figures += [['P menos C, pesos reales',interval(a['P_C']),interval(b['P_C'])],
                ['Nuevos menos continuos',interval(a['nuevos_continuos']),interval(b['nuevos_continuos'])]]
    note=r'Fuente: cálculos de sensibilidad sobre las bases analíticas y eventos originales ya armonizados. Principal: definición original K/A. Alternativa estricta: K afirmativa con08 o institución no resuelta pasa a ND en la visita necesaria; nunca a negativa ni a A. Los casos mixtos se apartan íntegramente, sin repartir dinero por institución. P/C: N receptor (N con monto válido). Contrastes monetarios: pesos mensuales de septiembre2026,4999 réplicas percentiles por folio,semilla20261023; N válidos nuevos/continuos1435/1857 y508/1670. La cohorte basal K se mantiene en8888; transiciones K clasificables7195 y5933. Los contrastes son condicionales a distintas poblaciones, no efectos de retirar un programa.'
    ktable=table('tab:sensibilidad-medicion-k','Sensibilidad de la incorporación y los montos K 2012--2015',
        ['Indicador','Principal','Alternativa estricta'],figures,note,'p{.30\\textwidth}p{.30\\textwidth}p{.30\\textwidth}')
    # Derive cohort N from stored count, never a hand-entered analytic denominator.
    ktable=ktable.replace('en8888','en'+number(a['N_cohorte'],0))
    u=data['union'][0];v=data['union'][2]
    ut=[['Basales, ambas negativas',number(u['N_basal_original'],0),number(v['N_basal_original'],0)],
        ['Clasificables en destino',number(u['N_clasificables'],0),number(v['N_clasificables'],0)],
        ['Incorporación identificada',number(u['N_incorporados'],0),number(v['N_incorporados'],0)],
        ['Desconocidos adicionales',number(u['N_nuevos_desconocidos'],0),number(v['N_nuevos_desconocidos'],0)],
        [r'Entre clasificables (\%)',number(100*u['condicional']['proporcion']),number(100*v['condicional']['proporcion'])],
        [r'Identificada sobre3846 (\%)',number(100*u['proporcion_identificada_mismo_denominador']),number(100*v['proporcion_identificada_mismo_denominador'])],
        [r'Cotas sin defunción registrada (\%)','--'.join(number(100*z) for z in u['cotas_sin_defuncion_registrada']),'--'.join(number(100*z) for z in v['cotas_sin_defuncion_registrada'])]]
    unote=r'Fuente: seguimiento de la cohorte original de4592personas con negativas K/A en2012. Alternativa estricta según sección~\ref{sec:sensibilidad-medicion}. Destinos excluidos del principal:319fallecimientos registrados,199ausencias de vital desconocido,186sustitutos y42uniónND. Principal:2188/3846,IC95 por folio9999réplicas,semilla20261024,55,28--58,50\%; alternativa condicional1643/3301,1999réplicas,semilla20261023,47,96--51,62\%. Sobre los3846observados originales,545pasan a ND: cotas de medición42,72--56,89\%. Las cotas sin defunción usan4273personas y no certifican que los ausentes vivan. Cotas e IC son objetos diferentes; no se imputa recepción tras morir.'
    utable=table('tab:sensibilidad-union','Unión K/A 2012--2015: seguimiento y sensibilidad de medición',
        ['Indicador','Principal','Alternativa estricta'],ut,unote,'p{.42\\textwidth}p{.22\\textwidth}p{.22\\textwidth}')
    counts=[]
    for w in data['ventanas']:
        orig=w['escenarios']['Principal'];alt=w['escenarios']['Conservador08_ND']
        c1=next(g['N_receptor'] for g in orig['grupos'] if g['grupo']==other)
        c2=next(g['N_receptor'] for g in alt['grupos'] if g['grupo']==other)
        counts.append([w['via']+' '+str(w['origen'])+'--'+str(w['destino']),number(orig['N_nuevos'],0)+' / '+number(alt['N_nuevos'],0),number(c1,0)+' / '+number(c2,0)])
    ctable=table('tab:sensibilidad-ventanas','Incorporación por vía y otra vía basal ante la restricción institucional',
        ['Vía/ventana','N nuevos: original/alternativo','N C: original/alternativo'],counts,
        r'Fuente: agregados de sensibilidad ya calculados; alternativa estricta con08/ND institucional. Cohortes y ventanas no cambian. A conserva su recepción: cambia la clasificación de K basal. Las variaciones fuera de2012/2015responden a institución no resuelta, no al código08de programas;8en2001/2003no se interpreta así. Son conteos de composición, no probabilidades ni evidencia de prestación adicional.','p{.25\\textwidth}p{.34\\textwidth}p{.29\\textwidth}')
    block(ROOT/'manuscrito/tablas/tesis_central_seleccion.tex',ktable+'\n'+utable+'\n'+ctable)
    ir=[]
    for z in comp['patrimonio']:
        if 'interaccion' not in z or (z['origen']==2018 and z['escenario']!='Principal'):continue
        x=z['interaccion'];assert min(x['N'])>=20
        ir.append([str(z['origen'])+'--'+str(z['destino']),'Original' if z['escenario']=='Principal' else 'Solo08 identificado', '/'.join(map(str,x['N'])),interval(x)])
    itable=table('tab:sensibilidad-interaccion','Diferencia de contrastes P menos C entre mitades patrimoniales en K',
        ['Ventana','Definición','N por rama','Interacción [IC95]'],ir,
        r'Fuente: remuestreo conjunto por folio,4999réplicas,semilla20261024. Interacción=(P--C)superior menos(P--C)inferior; orden de N:P/Cinferior yP/Csuperior. Pesos mensuales reales de septiembre2026. Solo08identificado aparta K afirmativa expuesta a08; conserva la declaración original si la institución no está resuelta, por lo que no identifica una muestra institucional pura. N cuenta personas con monto íntegro válido, no folios: C 20 inferior y 27 superior son exploratorios. La reclasificación y la inestabilidad de muestras reducidas pueden contribuir al cambio de signo; no se separan sus aportaciones. No es efecto causal ni prueba de reversión del gradiente.','p{.17\\textwidth}p{.24\\textwidth}p{.22\\textwidth}p{.27\\textwidth}')
    block(ROOT/'manuscrito/tablas/tesis_central_patrimonio_monto.tex',itable)
    registry=[]
    for z in comp['registro_inferencial']:
        if z.get('tabla') not in ['Cuadro4.16','Cuadro4.20','Procedimiento_armonizado_propuesto']:continue
        bounds=z.get('ic95',z.get('ic95_folio'));r={'estimacion':z['estimacion'],'ic95':bounds,'N':z['N']}
        registry.append([str(z['origen'])+'--'+str(z['destino']), 'Original' if z['tabla']=='Cuadro4.16' else ('Sensibilidad' if z['tabla']=='Cuadro4.20' else 'Común'),str(z['replicas']),str(z.get('seed',z.get('semilla'))),interval(r)])
    rtable=table('tab:procedimientos-institucionales','Mismo contraste institucional con procedimientos de remuestreo explícitos',
        ['K ventana','Procedimiento','Réplicas','Semilla','P--C [IC95]'],registry,
        r'Fuente: reproducción exacta y comprobación de los agregados existentes. P/C con evidencia IMSS/ISSSTE y monto íntegro; todos son IC percentiles por folio.2012--2015:N406/27,427folios;2018--2021:N309/79,386folios. El procedimiento común usa9999réplicas,semilla20261024y conserva el estimando; no sustituye silenciosamente los originales. C27es exploratorio. Diferencias entre extremos reflejan réplicas/semillas y empates, no necesariamente poblaciones o unidades distintas.','p{.18\\textwidth}p{.16\\textwidth}rrp{.29\\textwidth}')
    block(ROOT/'manuscrito/tablas/tesis_calidad_precision.tex',rtable)
    hashes={name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in ['resultados_auditoria.json','complemento_auditoria.json']}
    return {'accion':'Selección editorial sin recalcular análisis; requiere validación posterior', 'fuentes_sha256':hashes,'tablas_actualizadas':4,'sin_registros_individuales':True}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sensibilidades-fase-a',type=Path,help='Directorio privado de agregados auditados; exporta solo la selección')
    args=parser.parse_args()
    if args.sensibilidades_fase_a:
        print(json.dumps(export_sensitivities(args.sensibilidades_fase_a),ensure_ascii=False,indent=2))
    else:
        from tesis_enasem.quality_outputs import export_public
        print(export_public())
