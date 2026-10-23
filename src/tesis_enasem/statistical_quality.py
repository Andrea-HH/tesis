"""Auditoría10 de tamaños, filtros, dependencia y estabilidad sin cambiar insumos.

El registro exhaustivo es privado. Los resultados no contienen IDs ni filas de
microdatos. Los archivos fuente originales se conservan en la instantánea10.
"""
from __future__ import annotations

import json
import re
import subprocess
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import pandas as pd
from markdown_it import MarkdownIt

from .central_analysis import FIRST, OTHER, CONT, GATES, load, groups
from .benefit_transitions import (
    WINDOWS, pair_frame, classify, frequency_quantiles, median_order_interval,
)
from .economic_protection import union_receipt, save_json
from .project_paths import PROJECT_ROOT as ROOT, INTERIM_DIR

OUT = INTERIM_DIR / 'auditoria_calidad_divulgacion'
ORIGINAL = OUT / 'privado/originales'
STAGES = ('eda_pensionaria', 'pensiones_salud', 'trayectorias_pensiones_salud',
          'pensiones_mortalidad_seleccion', 'cobertura_proteccion_economica',
          'politicas_montos_suficiencia', 'transiciones_montos_pensionarios',
          'incorporacion_proteccion_propia')


def read_original(name: str) -> Any:
    """Lee la copia previa para no auditar contra una versión ya protegida."""
    return json.loads((ORIGINAL / name).read_text())


def digest(path: Path) -> str:
    """Huella de contenido para verificar conservación."""
    return sha256(path.read_bytes()).hexdigest()


def n_band(n: int | None) -> str:
    """Umbrales de revisión, nunca aprobación automática por tamaño."""
    if n is None:
        return 'N no trazable'
    if n == 0:
        return 'Sin observaciones'
    if n < 10:
        return 'Menos de10: no monetario divulgable; sin sustento inferencial'
    if n < 30:
        return '10–29: revisión reforzada'
    return '30+: revisar precisión, soporte y diseño'


def numbers_in_count(value: str) -> list[int]:
    """Lee solo celdas cuyo encabezado identifica conteos; no montos."""
    text = value.replace('\\,', '').replace(',', '')
    text = re.sub(r'\\(?:ensuremath|textbf)\{([^}]+)\}', r'\1', text)
    return [int(x) for x in re.findall(r'(?<![\d.])\d+(?![\d.])', text)]


def count_column(header: str) -> bool:
    """Evita interpretar mediana, año o IC como N."""
    h = re.sub(r'\\[A-Za-z]+', '', header).replace('{', '').replace('}', '')
    return bool(re.search(r'(^|[\s/])N(?:$|[\s_/])|N válido|N observado|N basal', h, re.I))


def markdown_inventory() -> tuple[list[dict], list[dict]]:
    """Censa cada cuadro/fila y figura del informe antes de cualquier edición."""
    path = 'resultados/INFORME_GENERAL.md'
    source = (ORIGINAL / path).read_text()
    tokens = MarkdownIt('commonmark', {'html': True}).enable('table').parse(source)
    tables, figures = [], []
    heading, caption, number = '', '', 0
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t.type == 'heading_open':
            heading = tokens[i+1].content
        if t.type == 'inline' and re.match(r'\*\*Cuadro \d+', t.content):
            caption = t.content.strip('*')
        if t.type == 'table_open':
            number += 1
            rows = []
            start = t.map[0] + 1
            while tokens[i].type != 'table_close':
                if tokens[i].type == 'tr_open':
                    rows.append([])
                elif tokens[i].type == 'inline':
                    rows[-1].append(tokens[i].content)
                i += 1
            headers = rows[0]
            ncols = [j for j,h in enumerate(headers) if count_column(h)]
            audit_rows = []
            for k,row in enumerate(rows[1:], 1):
                ns = {headers[j]: numbers_in_count(row[j]) for j in ncols if j < len(row)}
                positives = [n for v in ns.values() for n in v if n > 0]
                audit_rows.append(dict(fila=k,claves=row[:min(2,len(row))],conteos=ns,
                    N_minimo_documentado=min(positives) if positives else None,
                    revision=n_band(min(positives) if positives else None)))
            tables.append(dict(id=f'informe_cuadro_{number:03}',archivo=path,linea=start,
                titulo=caption or heading,seccion=heading,encabezados=headers,filas=audit_rows,
                denominador_explicito=bool(ncols),
                nota='Conteos de la tabla no prueban el N del estimador; cotejar registro de fuente.'))
            caption = ''
        if t.type == 'inline':
            for c in t.children or []:
                if c.type == 'image':
                    figures.append(dict(id=f'informe_figura_{len(figures)+1:03}',titulo=c.content,
                        archivo='resultados/'+c.attrGet('src'),seccion=heading,
                        unidad='Resolver en fuente, no deducir N del número de marcas gráficas'))
        i += 1
    return tables, figures


def tex_inventory() -> list[dict]:
    """Censa activos, macros y cuadros auxiliares, incluidos no compilados."""
    directory = ORIGINAL / 'manuscrito'
    reachable: set[str] = set()
    def visit(name: str) -> None:
        if name in reachable:
            return
        reachable.add(name)
        p=directory/name
        if not p.exists():
            return
        for ref in re.findall(r'\\(?:input|include)\{([^}]+)\}',p.read_text()):
            visit(ref if ref.endswith('.tex') else ref+'.tex')
    visit('main.tex')
    result=[]
    for p in sorted(directory.rglob('*.tex')):
        text=p.read_text();rel=p.relative_to(directory).as_posix()
        captions=re.findall(r'\\caption\{([^}]+)\}',text)
        if not captions and '/tablas/' not in str(p):
            continue
        rows=[]
        for k,line in enumerate(text.splitlines(),1):
            if '&' not in line or not '\\\\' in line:
                continue
            cells=line.split('&')
            rows.append(dict(linea=k,N_no_inferido=True,columnas=len(cells)))
        result.append(dict(archivo='manuscrito/'+rel,compilado=rel in reachable,
            titulos=captions,filas_tabulares=len(rows),macros=len(re.findall(r'\\(?:newcommand|def)|tesisdato:',text)),
            figuras=re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}',text),
            estado='Auditar semántica/N de fuente; LaTeX no acredita personas únicas'))
    return result


def walk_statistics(value: Any, pointer: str = '', context: dict | None = None) -> Iterator[dict]:
    """Registro de cada nodo estadístico con N, sin copiar los valores sensibles."""
    context=dict(context or {})
    if isinstance(value,dict):
        for key in ['ano','ronda','origen','destino','via','dimension','variable','grupo',
                    'categoria','estrato','transicion','patron','poblacion']:
            if isinstance(value.get(key),(str,int,float,bool)):
                context[key]=value[key]
        ns={}
        for k,v in value.items():
            if re.match(r'^N($|_)',k) and isinstance(v,int) and not isinstance(v,bool):
                ns[k]=v
            elif k=='N' and isinstance(v,list) and all(isinstance(x,int) for x in v):
                ns[k]=v
        statistic_keys=[k for k in value if re.search(r'media|mediana|q25|q75|p25|p75|ic95|IC_|efecto|diferencia|proporcion|pct|estimacion',k)]
        if ns:
            sample_keys=['N','N_valido','N_validos','N_grupo','N_referencia','N_si_valido',
                         'N_no_valido','N_monto','N_monto_real','N_pares_validos','N_observado']
            sampled=[]
            for k in sample_keys:
                if k in ns:
                    sampled.extend(ns[k] if isinstance(ns[k],list) else [ns[k]])
            if not sampled:
                sampled=[v for k,v in ns.items() if isinstance(v,int) and k in ['N_personas','N_personas_unicas','N_receptores']]
            n=min(sampled) if sampled else None
            monetary=bool(re.search(r'monto|patrimonio|imp_neto|nominal|real|LPI|dinero',pointer+' '+str(context),re.I))
            yield dict(json_pointer=pointer,contexto=context,conteos=ns,N_analitico_minimo=n,
                N_personas_unicas_explicito=ns.get('N_personas_unicas',ns.get('N_personas')),
                N_inicialmente_elegibles=ns.get('N_elegible',ns.get('N_cohorte',ns.get('N_origen'))),
                IC_documentado=any(re.search(r'ic95|IC_|ic_',k) for k in value),
                estadisticos=statistic_keys,monetario=monetary,revision=n_band(n),
                unidad='Persona por ronda/intervalo si claves únicas verificadas; eventos y multivisita requieren fuente',
                motivo_N_faltante=None if n is not None else 'No consta N específico del estimador en este nodo; no se sustituye por N total')
        for k,v in value.items():
            yield from walk_statistics(v,pointer+'/'+str(k),context)
    elif isinstance(value,list):
        for i,v in enumerate(value):
            yield from walk_statistics(v,pointer+'/'+str(i),context)


def source_inventory() -> list[dict]:
    """Incluye etapas00–09 y precisión previa, sin transcribir observaciones."""
    rows=[]
    for stage in STAGES:
        names=['resultados.json']+(['precision.json','auditoria.json'] if stage=='transiciones_montos_pensionarios' else [])
        for name in names:
            rel=f'data/interim/{stage}/{name}'
            path=ORIGINAL/rel
            if path.exists():
                for record in walk_statistics(json.loads(path.read_text())):
                    record['archivo_fuente']=rel
                    record['unidad_fuente']='Eventos cuando se indica explícitamente evento; no sumarlos como personas' if '/eventos' in record['json_pointer'] else 'Revisar dominio del contrato de la etapa'
                    rows.append(record)
    return rows


def select_chain(p: pd.DataFrame, masks: list[tuple[str,pd.Series]]) -> list[dict]:
    """Embudo secuencial con personas únicas reales, sin exportar sus IDs."""
    keep=pd.Series(True,index=p.index)
    result=[]
    previous=len(p)
    for label,mask in masks:
        keep &= mask.fillna(False)
        n=int(keep.sum())
        result.append(dict(filtro=label,N_observaciones=n,N_personas_unicas=int(p.index[keep].nunique()),
                           N_excluidas_en_paso=previous-n))
        previous=n
    return result


def frame_for_window(f: pd.DataFrame,a: int,b: int,via: str) -> pd.DataFrame:
    """Reutiliza pares01–09 y conserva todos los destinos de la cohorte."""
    p=pair_frame(f,a,b);p.attrs['joint']=(a,b)==(2012,2015)
    p['grupo']=groups(p,via);p['patron']=classify(p,via)
    p['monto_real']=p['monto_completo_'+via+'_b']*p.factor_b
    return p


def group_flow(p: pd.DataFrame,via: str,label: str,dimension: str|None=None,category: str|None=None) -> dict:
    """Separa rareza basal, seguimiento, incorporación y validez monetaria."""
    other=GATES['A' if via=='K' else 'K'];own=GATES[via]
    mask=pd.Series(True,index=p.index)
    if dimension:
        mask &= p[dimension+'_a'].eq(category).fillna(False)
    q=p.loc[mask]
    direct=q.tipent_b.isin([1,2]);vital=~(q.vital_discordante_a|q.vital_discordante_b).fillna(False)
    if label==FIRST:
        start=q[own+'_a'].eq(False)&q[other+'_a'].eq(False);end=q[own+'_b'].eq(True)
    elif label==OTHER:
        start=q[own+'_a'].eq(False)&q[other+'_a'].eq(True);end=q[own+'_b'].eq(True)
    else:
        start=q[own+'_a'].eq(True);end=q[own+'_b'].eq(True)
    chain=select_chain(q,[('Categoría de recepción basal',start),('Presente destino',q.ano_b.notna()),
        ('Directa destino',direct),('Sin conflicto vital registrado',vital),
        ('Recepción destino conocida',q[own+'_b'].notna()),('Recepción afirmativa destino',end),
        ('Todos los eventos captados con monto válido',q['monto_completo_'+via+'_b'].notna()),
        ('Factor de precios disponible',q.factor_b.notna())])
    selected=q.loc[q.grupo.eq(label)];money=selected.loc[selected.monto_real.notna()]
    assert chain[-1]['N_observaciones']==len(money)
    return dict(via=via,grupo=label,dimension=dimension or 'General',categoria=category or 'Todas',
        N_cohorte=len(p),N_estrato_basal=len(q),embudo=chain,
        N_receptores=int(len(selected)),N_monto=len(money),N_personas_unicas=int(money.index.nunique()),
        N_folios=int(money.cunicah_a.nunique()),N_eventos_captados=int(money['N_eventos_'+via+'_b'].sum()),
        N_monto_faltante=int(selected.monto_real.isna().sum()),
        N_eventos_monto_ND=int((selected['N_eventos_'+via+'_b']-selected['N_montos_'+via+'_b']).fillna(0).sum()),
        N_edad_ND=int(selected.edad_a.isna().sum()),N_escolaridad_ND=int(selected.educacion_a.isna().sum()),
        revision=n_band(len(money)),estadistica_monetaria_divulgable=len(money)>=10,
        causa='Intersección de recepción basal, incorporación y estrato; ver embudo. No se etiqueta como error por el solo tamaño.',
        dependencia='Una fila por persona en intervalo; folio puede compartir integrantes; ventanas y vías se solapan')


def precision_state(counts: list[int],ci: list[float],scale: float,influence: float) -> str:
    """Revisión operativa de amplitud e influencia; no usa excluir cero.

    La escala es max(|mediana referencia|,IQR referencia). Alarma: ancho mayor
    que esa escala o cambio LOO mayor a25%; no es potencia universal ni prueba.
    Un IC que incluye cero es un resultado válido, no una causa de descarte.
    """
    state='Exploratorio; revisión reforzada por10–29' if min(counts)<30 else 'Estimable descriptivamente; IC condicional'
    wide=(ci[1]-ci[0])>scale if scale>0 else ci[1]>ci[0]
    sensitive=influence>.25*scale if scale>0 else influence>0
    if min(counts)<30 and (wide or sensitive):
        state='No estimable con confiabilidad: amplitud/influencia excesiva respecto de referencia; no se evalúa por significancia'
    elif wide or sensitive:
        state+='; amplitud o influencia requiere cautela'
    if ci[0]==ci[1]:state+='; IC degenerado por empates, sin equivalencia'
    return state


def median_comparison(q: pd.DataFrame,labels: tuple[str,str]=(FIRST,OTHER),*,replicas: int=9999,seed: int=20261024) -> dict:
    """Precisión, empates, influencia y comprobación por rangos binomiales.

    Solo calcula montos en grupos con10+; con menos guarda únicamente tamaños.
    No produce IC de diseño ni equivale a una prueba de equivalencia.
    """
    q=q.loc[q.grupo.isin(labels)&q.monto_real.notna()].copy()
    counts=[int(q.grupo.eq(g).sum()) for g in labels]
    result=dict(grupos=list(labels),N=counts,N_folios=int(q.cunicah_a.nunique()),semilla=seed,replicas=replicas)
    if min(counts)<10:
        return dict(**result,estado='No estimable con confiabilidad; grupo menor de10',estimacion=None,ic95_folio=None)
    values=q.monto_real.to_numpy(dtype=float);g=q.grupo.eq(labels[0]).to_numpy();codes,folios=pd.factorize(q.cunicah_a)
    point=float(np.median(values[g])-np.median(values[~g]));rng=np.random.default_rng(seed);draws=[]
    for start in range(0,replicas,64):
        weights=rng.multinomial(len(folios),np.full(len(folios),1/len(folios)),size=min(64,replicas-start))[:,codes]
        draws.extend(frequency_quantiles(values[g],weights[:,g])[:,1]-frequency_quantiles(values[~g],weights[:,~g])[:,1])
    draws=np.asarray(draws);valid=np.isfinite(draws);ci=np.quantile(draws[valid],[.025,.975]).tolist()
    # Quitar cada folio: solo se conservan extremos del cambio, nunca valores por ID.
    loo=[]
    for start in range(0,len(folios),64):
        batch=np.arange(start,min(start+64,len(folios)));w=(codes[None,:]!=batch[:,None]).astype(int)
        loo.extend(frequency_quantiles(values[g],w[:,g])[:,1]-frequency_quantiles(values[~g],w[:,~g])[:,1])
    loo=np.asarray(loo);stats=[];order=[]
    for mask in (g,~g):
        v=values[mask];med=float(np.median(v));freq=int(np.sum(v==med))
        stats.append(dict(N=len(v),N_folios=int(q.loc[mask,'cunicah_a'].nunique()),
            mediana=med,q25=float(np.quantile(v,.25)),q75=float(np.quantile(v,.75)),
            N_en_mediana=freq,proporcion_en_mediana=freq/len(v),valores_distintos=int(len(np.unique(v)))))
        order.append(median_order_interval(v,.975))
    lower=order[0]['inferior']-order[1]['superior'] if order[0]['inferior'] is not None and order[1]['superior'] is not None else None
    upper=order[0]['superior']-order[1]['inferior'] if order[0]['superior'] is not None and order[1]['inferior'] is not None else None
    scale=max(abs(stats[1]['mediana']),stats[1]['q75']-stats[1]['q25'])
    width=ci[1]-ci[0];influence=float(np.nanmax(np.abs(loo-point)))
    state=precision_state(counts,ci,scale,influence)
    return dict(**result,estado=state,estimacion=point,ic95_folio=ci,N_replicas_validas=int(valid.sum()),amplitud_relativa_referencia=width/scale if scale else None,influencia_relativa_referencia=influence/scale if scale else None,
        estadisticas=stats,intervalo_orden_independencia=[lower,upper],
        max_cambio_al_omitir_un_folio=float(np.nanmax(np.abs(loo-point))),
        rango_al_omitir_un_folio=[float(np.nanmin(loo)),float(np.nanmax(loo))],
        N_omisiones_con_signo_distinto=int(np.sum(np.sign(loo)!=np.sign(point))),
        nota='Orden: comprobación con independencia personal, no folio/diseño. LOO mide influencia, no cobertura de IC.')


def standardization(q: pd.DataFrame,kind: str,*,age_groups: int=3,min_cell: int=20,replicas: int=4999,seed: int=20261024) -> dict:
    """Sensibilidad uniforme a granularidad de edad, sin elegir por significancia.

    Excluye réplicas sin soporte en una celda y cuenta cuántas. La retención se
    mide antes de excluir covariables ND; no se extrapola fuera del soporte.
    """
    q=q.copy();q['esc']=np.where(q.educacion_a.isna(),'ND',np.where(q.educacion_a.le(5),'0–5','6+'))
    q['age']=q.edad_06_a if age_groups==3 else pd.cut(q.edad_a,[59,69,np.inf],labels=['60–69','70+']).astype(object).fillna('ND')
    if kind=='monto':
        q=q.loc[q.grupo.isin([FIRST,OTHER])&q.monto_real.notna()].copy();q['g']=q.grupo.map({FIRST:0,OTHER:1});q['v']=q.monto_real
    else:
        q=q.loc[q.patrimonio_grupo_a.isin(['Q1','Q4'])].copy();q['g']=q.patrimonio_grupo_a.map({'Q1':0,'Q4':1});q['v']=q.patron.eq('No→Sí').astype(float)
    full=[int(q.g.eq(g).sum()) for g in (0,1)]
    q=q.loc[q.sexo_grupo_a.isin(['Hombre','Mujer'])&q.age.isin(['60–64','65–69','60–69','70+'])&q.esc.ne('ND')].copy()
    q['cell']=q.sexo_grupo_a.astype(str)+'|'+q.age.astype(str)+'|'+q.esc
    counts=q.groupby(['cell','g']).size().unstack(fill_value=0).reindex(columns=[0,1],fill_value=0)
    support=counts.index[(counts[0]>=min_cell)&(counts[1]>=min_cell)].tolist();z=q.loc[q.cell.isin(support)]
    kept=[int(z.g.eq(g).sum()) for g in (0,1)];coverage=[kept[i]/full[i] if full[i] else 0 for i in (0,1)]
    out=dict(estimando=kind,edad_grupos=age_groups,minimo_celda=min_cell,N_inicial=full,N_soporte=kept,
        cobertura=coverage,N_celdas=len(support),celdas=[dict(estrato=c,N_P_Q1=int(counts.loc[c,0]),N_C_Q4=int(counts.loc[c,1])) for c in support],
        viable=len(support)>=4 and min(coverage)>=.7,semilla=seed,replicas=replicas)
    if not out['viable']:
        return dict(**out,estimacion=None,ic95=None,estado='No estimable con retención70% y4 celdas; sin extrapolar')
    cell=pd.Categorical(z.cell,categories=support).codes;g=z.g.to_numpy();v=z.v.to_numpy();codes,folios=pd.factorize(z.cunicah_a)
    def evaluate(w: np.ndarray) -> tuple[np.ndarray,np.ndarray]:
        target=np.stack([w[:,cell==j].sum(axis=1) for j in range(len(support))],axis=1).astype(float)
        total=target.sum(axis=1);target/=np.where(total>0,total,1)[:,None]
        stats=[];valid=total>0
        for group in (0,1):
            m=g==group;wg=w[:,m].astype(float).copy();cc=cell[m]
            for j in range(len(support)):
                c=cc==j;den=wg[:,c].sum(axis=1);valid&=den>0
                wg[:,c]*=np.divide(target[:,j],den,out=np.zeros_like(den),where=den>0)[:,None]
            stats.append(frequency_quantiles(v[m],wg,inverse_cdf=True)[:,1] if kind=='monto' else np.sum(wg*v[m],axis=1))
        return stats[0]-stats[1],valid
    point=evaluate(np.ones((1,len(z))))[0][0]
    rng=np.random.default_rng(seed);draws=[];discarded=0
    for start in range(0,replicas,32):
        w=rng.multinomial(len(folios),np.full(len(folios),1/len(folios)),size=min(32,replicas-start))[:,codes]
        d,valid=evaluate(w);draws.extend(d[valid]);discarded+=int((~valid).sum())
    return dict(**out,estimacion=float(point),ic95=np.quantile(draws,[.025,.975]).tolist(),
        N_replicas_sin_soporte=discarded,N_replicas_validas=len(draws),estado='Sensibilidad de composición; distinto soporte, sin causalidad')


def analyze() -> dict:
    """Auditoría exhaustiva de artefactos y diagnóstico exacto de cohortes09."""
    tables,figures=markdown_inventory();tex=tex_inventory();registry=source_inventory()
    f,meta=load();old=read_original('data/interim/incorporacion_proteccion_propia/resultados.json')
    flows=[];robust=[];wave_counts=[];checks=0
    for year in sorted(f.ano.unique()):
        q=f.loc[f.ano.eq(year)]
        masks=[('Maestro ronda',pd.Series(True,index=q.index)),('Vivo registrado',q.vivo),
            ('Edad60+',q.edad.ge(60)),('Entrevista directa',q.directa)]
        t=q.set_index('id');wave_counts.append(dict(ronda=int(year),embudo=select_chain(t,[(k,pd.Series(v.to_numpy(),index=t.index)) for k,v in masks])))
    for a,b,via in WINDOWS:
        print('Auditoría10',a,b,via,flush=True)
        p=frame_for_window(f,a,b,via);assert p.index.is_unique
        previous=next(w for w in old['ventanas'] if (w['origen'],w['destino'],w['via'])==(a,b,via))
        for label in (FIRST,OTHER,CONT):
            general=group_flow(p,via,label);general.update(origen=a,destino=b);flows.append(general)
            original=next(z for z in previous['grupos'] if z['grupo']==label)
            assert general['N_receptores']==original['N'] and general['N_monto']==original['monto_real']['N'];checks+=2
            for dimension in ('patrimonio_grupo','sexo_grupo','edad_06','educacion_grupo','localidad_grupo'):
                for category in sorted(p[dimension+'_a'].dropna().unique()):
                    row=group_flow(p,via,label,dimension,str(category));row.update(origen=a,destino=b);flows.append(row)
        comparisons=[]
        for seed in (20261024,20261025):
            comparisons.append(median_comparison(p,replicas=9999,seed=seed))
        # Los diagnósticos de instituciones separan concepto agregado y evento único.
        institutions=[]
        if via=='K':
            for name,mask in [('Evidencia IMSS/ISSSTE',p.evidencia_seguridad_K_b.eq(True)),
                              ('Programas agrupados',p.evidencia_programa_K_b.eq(True)),
                              ('Un evento IMSS',p.N_eventos_K_b.eq(1)&p.institucion_unica_K_b.eq(1)),
                              ('Un evento ISSSTE',p.N_eventos_K_b.eq(1)&p.institucion_unica_K_b.eq(2))]:
                institutions.append(dict(institucion=name,**median_comparison(p.loc[mask],replicas=4999)))
        baseline=union_receipt(p.pension_propia_k_a,p.apoyo_propio_a).eq(False).fillna(False)
        risk=p.loc[baseline&p.patron.isin(['No→No','No→Sí'])].copy()
        adjustments=[]
        for kind in ('tasa','monto'):
            q=risk if kind=='tasa' else p
            for age,min_cell in ((3,20),(3,30),(2,20),(2,30)):
                adjustments.append(standardization(q,kind,age_groups=age,min_cell=min_cell))
        # Heterogeneidad completa por sexo/edad/escolaridad/localidad/patrimonio.
        strata=[]
        for dimension in ('sexo_grupo','edad_06','educacion_grupo','localidad_grupo','patrimonio_grupo'):
            for category in sorted(p[dimension+'_a'].dropna().unique()):
                strata.append(dict(dimension=dimension,categoria=str(category),
                    **median_comparison(p.loc[p[dimension+'_a'].eq(category)],replicas=1999)))
        robust.append(dict(origen=a,destino=b,via=via,N_cohorte=len(p),N_personas=len(p),
            monetario=comparisons,ajustes=adjustments,instituciones=institutions,estratos=strata,
            N_destino_no60=int(p.edad_b.lt(60).sum()),N_conflicto_vital=int(p.patron.eq('Conflicto de estado vital registrado').sum())))
    # Verifica que el registro no confunda pares con personas al acumular ventanas.
    ids=[set(pair_frame(f,a,b).index) for a,b in sorted(set((a,b) for a,b,_ in WINDOWS))]
    dependence=dict(N_personas_unicas_cinco_cohortes=len(set.union(*ids)),N_suma_personas_intervalo=sum(map(len,ids)),
        nota='Solo conteos; no sumar las seis ramas de vía ni tratarlas como independientes.')
    result=dict(etapa=10,instantanea_sha256=digest(OUT/'instantanea.json'),
        inventario_informe=tables,inventario_figuras=figures,inventario_tex=tex,
        registro_fuentes=registry,embudos_rondas=wave_counts,embudos_contrastes=flows,
        robustez=robust,dependencia=dependence,comprobaciones=checks,
        fuentes_originales_verificadas=len(meta['fuentes_verificadas']),
        estado='Auditoría privada sin registros individuales; precisión condicional y soporte explícitos')
    save_json(OUT/'privado/auditoria.json',result)
    print('Censo:',len(tables),'cuadros;',len(figures),'figuras;',len(registry),'nodos estadísticos;',len(flows),'embudos.',flush=True)
    return result


def union_precision(p: pd.DataFrame,seed: int=20261024,replicas: int=9999) -> dict:
    """Audita el estimando de unión sin convertir faltantes o muertes en No."""
    u0=union_receipt(p.pension_propia_k_a,p.apoyo_propio_a)
    u1=union_receipt(p.pension_propia_k_b,p.apoyo_propio_b)
    basal=u0.eq(False).fillna(False)
    allowed=p.tipent_b.isin([1,2])&~(p.vital_discordante_a|p.vital_discordante_b).fillna(False)
    q=p.loc[basal&allowed&u1.notna()];y=u1.loc[q.index].astype(int)
    tab=pd.DataFrame({'folio':q.cunicah_a,'y':y}).groupby('folio').y.agg(['sum','size'])
    rng=np.random.default_rng(seed);draws=[]
    for start in range(0,replicas,64):
        w=rng.multinomial(len(tab),np.full(len(tab),1/len(tab)),size=min(64,replicas-start))
        draws.extend((w@tab['sum'].to_numpy())/(w@tab['size'].to_numpy()))
    point=float(y.mean());den=len(q)-tab['size'].to_numpy();loo=(y.sum()-tab['sum'].to_numpy())/den
    states=classify(p,'K');states.loc[allowed]='Unión ND destino';states.loc[allowed&u1.eq(True).fillna(False)]='Incorpora unión';states.loc[allowed&u1.eq(False).fillna(False)]='Sin ambas'
    from statsmodels.stats.proportion import proportion_confint
    return dict(N_basal=int(basal.sum()),N_observados=len(q),N_personas_unicas=q.index.nunique(),
        N_incorporados=int(y.sum()),N_folios=len(tab),estimacion=point,
        ic95_folio=np.quantile(draws,[.025,.975]).tolist(),ic95_wilson=list(proportion_confint(y.sum(),len(q),method='wilson')),
        max_cambio_omitir_folio=float(np.max(abs(loo-point))),destinos=states.loc[basal].value_counts().to_dict(),
        semilla=seed,replicas=replicas,nota='Condicional a reobservación de unión; ni cohorte completa ni tasa anual.')


def enrich_audit() -> dict:
    """Completa trazabilidad de EDA previo y evalúa reducciones sustantivas."""
    result=json.loads((OUT/'privado/auditoria.json').read_text())
    # Las frecuencias de un valor/bin no son el N de un estimador por subgrupo.
    for row in result['registro_fuentes']:
        row['rol_del_N']='Frecuencia de clase; no tamaño de contraste' if '/frecuencias/' in row['json_pointer'] else 'N del nodo; confirmar rol del estimador y denominador'
    supplement=read_original('data/interim/eda_pensionaria/resultados.json')
    paths=set(json.loads((OUT/'privado/fuentes_eda_adicionales.json').read_text()))
    result['registro_fuentes']=[row for row in result['registro_fuentes'] if row['archivo_fuente'] not in paths]
    for rel in sorted(paths):
        for row in walk_statistics(json.loads((ORIGINAL/rel).read_text())):
            row['archivo_fuente']=rel
            row['rol_del_N']='Frecuencia de clase; no tamaño de contraste' if '/frecuencias/' in row['json_pointer'] else 'N específico del producto EDA externo'
            result['registro_fuentes'].append(row)
    # Registrar fuentes/roles de cada artefacto; no inventar un N cuando falta.
    text=(ORIGINAL/'resultados/INFORME_GENERAL.md').read_text();lines=text.splitlines()
    for table in result['inventario_informe']:
        i=table['linea']-1;near='\n'.join(lines[max(0,i-14):min(len(lines),i+80)])
        refs=re.findall(r'\.\./(data/interim/[^)\s]+\.json)',near)
        table['fuentes_candidatas']=sorted(set(refs))
        if not table['denominador_explicito']:
            table['estado_trazabilidad']='Documento/matriz conceptual o denominador implícito: resolver con registro de fuente; no inferir tamaño'
        else:
            table['estado_trazabilidad']='Conteos visibles y registro privado de fuente; unidad según contrato'
        for row in table['filas']:
            analytical={k:v for k,v in row['conteos'].items() if not re.search(r'ND|excluid|fuera|faltan|sin monto',k,re.I)}
            row['conteos_analiticos']=analytical
            pos=[n for values in analytical.values() for n in values if n>0]
            row['N_minimo_analitico_visible']=min(pos) if pos else None
            row['nota_N']='Márgenes de elegibilidad, exclusiones y frecuencias no acreditan por sí solos N de una mediana o efecto.'
    f,_=load();result['union_robustez']=[union_precision(pair_frame(f,2012,2015),seed) for seed in (20261024,20261025)]
    halves=[]
    for a,b,via in WINDOWS:
        p=frame_for_window(f,a,b,via)
        for name,categories in [('Mitad inferior',['Q1','Q2']),('Mitad superior',['Q3','Q4'])]:
            q=p.loc[p.patrimonio_grupo_a.isin(categories)]
            halves.append(dict(via=via,origen=a,destino=b,patrimonio=name,
                criterio='Agrupación Q1+Q2/Q3+Q4 relativa al basal; misma regla en seis ventanas, no seleccionada por signo',
                **median_comparison(q,replicas=4999)))
    result['patrimonio_mitades']=halves
    # Reformulación de T8: escolaridad0–5/6+ y titularidad conocida; sin maximizar medianas.
    from .pension_exploration import ownership_category
    q=f.loc[f.ano.eq(2021)&f.universo_60].copy()
    q['titularidad']=[ownership_category(a,b) for a,b in zip(q.pension_propia_k,q.pension_conyuge_k)]
    q['escolaridad2']=np.where(q.educacion.isna(),'Desconocido',np.where(q.educacion.le(5),'0–5','6+'))
    original_t8=read_original('data/interim/eda_pensionaria/tablas/T8_2021.json')
    assert sum(z['N_total'] for z in original_t8['patrimonio'])==len(q)
    t8=[]
    for (owner,school),part in q.groupby(['titularidad','escolaridad2'],observed=True):
        valid=part.imp_neto.dropna();n=len(valid)
        # Grupos desconocidos solo conteos, no perfiles económicos artificiales.
        allowed=n>=10 and owner!='Desconocido' and school!='Desconocido'
        quant=dict(q25=float(valid.quantile(.25)),mediana=float(valid.median()),q75=float(valid.quantile(.75))) if allowed else None
        t8.append(dict(titularidad=owner,escolaridad=school,N_total=len(part),N_valido=n,
            N_personas_unicas=part.id.nunique(),revision=n_band(n),estadisticas=quant,
            decision='Contexto descriptivo, sin elegir extremos' if allowed else 'Solo conteo de exclusión/ND; sin comparación monetaria'))
    result['T8_reformulado']=dict(ronda=2021,N_inicial=len(q),N_personas_unicas=q.id.nunique(),
        N_titularidad_ND=int(q.titularidad.eq('Desconocido').sum()),N_escolaridad_ND=int(q.escolaridad2.eq('Desconocido').sum()),
        N_ambas_ND=int((q.titularidad.eq('Desconocido')&q.escolaridad2.eq('Desconocido')).sum()),
        N_analisis=int((q.titularidad.ne('Desconocido')&q.escolaridad2.ne('Desconocido')&q.imp_neto.notna()).sum()),
        grupos=t8,nota='60+ por visita con modalidades originales del EDA; no mezclar con principal directa60+09. Patrimonio compartido en unidades almacenadas.')
    # Unidad evento frente a personas: doble conteo explícito para recepción.
    from .monetary_policy import load_events
    events=[]
    for via in ('K','A'):
        e,_=load_events(f,via)
        for year in sorted(f.ano.unique()):
            part=e.loc[e.ano.eq(year)&e.universo_60.eq(True)]
            events.append(dict(via=via,ronda=int(year),N_eventos=len(part),N_personas=part.id.nunique(),
                N_eventos_monto_valido=int(part.monto_mensual_observado.notna().sum()),N_sin_monto=int(part.monto_mensual_observado.isna().sum()),
                N_personas_monto=part.loc[part.monto_mensual_observado.notna(),'id'].nunique(),
                nota='Eventos enlazados a beneficiarios60+ de todas las modalidades originales, no suma personal ni directa09.'))
    result['unidades_evento_persona']=events
    # Matriz de cuadros por familias, incluidos conceptos y estadísticos sin N visible.
    result['causas']={
        'K2001_general':'Rareza basal de otra vía A y baja incorporación K;12 receptores,11 montos, no pérdida masiva. La división en cuartiles agrava escasez.',
        'T8_2021':'Titularidad×escolaridad de seis niveles; categorías ND tratadas como perfiles y selección de extremos de mediana. Reformular a0–5/6+ conocidas.',
        'otros_estratos':'Cruces de grupos de incorporación con sexo/edad/escolaridad/patrimonio; categoría ND no es perfil sustantivo. Ver embudo de cada fila.',
        'instituciones':'Restricciones de institución y evento único reducen naturalmente grupos; no juntar regímenes para ganar N.',
        'ajuste':'Falta de solapamiento etario/escolar, además de faltantes. Conservar retención70% y celdas mínimas, sin extrapolar.',
        'integracion':'Unicidad de IDs, LEFT1:1 y auditoría08 reproducidas; no se detectó pérdida nueva por programación en336 embudos. No equivale a certificar todas las alertas originales del proveedor.'}
    save_json(OUT/'privado/auditoria.json',result)
    print('Auditoría enriquecida:',len(paths),'tablas EDA fuente;',len(result['registro_fuentes']),'nodos; unión y reformulaciones verificadas.',flush=True)
    return result
