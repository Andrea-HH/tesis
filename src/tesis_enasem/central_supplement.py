"""Estandarización descriptiva y sensibilidad del contraste central."""
from __future__ import annotations
import numpy as np
import pandas as pd
from tesis_enasem.central_analysis import (FIRST,OTHER,contrast,SEED,OUTPUT,load,groups,WINDOWS,GATES,classify,pair_frame,union_receipt,save_json)
from tesis_enasem.benefit_transitions import frequency_quantiles

def standardize(q: pd.DataFrame, kind: str, *, replicas: int = 1999) -> dict:
    """Mezcla común sexo×edad3×escolaridad0–5/6+, soporte fijo N>=20.

    Medianas inverso CDF, objetivo combinado recalculado por réplica-folio.
    No ajuste causal, ni ponderación de encuesta o de selección.
    """
    q=q.copy();q['esc']=np.where(q.educacion_a.isna(),'ND',np.where(q.educacion_a.le(5),'0–5','6+'))
    if kind=='dinero':
        q=q.loc[q.grupo.isin([FIRST,OTHER])&q.monto_real.notna()].copy();q['g']=q.grupo.map({FIRST:0,OTHER:1});q['v']=q.monto_real
    else:
        q=q.loc[q.patrimonio_grupo_a.isin(['Q1','Q4'])].copy();q['g']=q.patrimonio_grupo_a.map({'Q1':0,'Q4':1});q['v']=classify(q,q.attrs['via']).eq('No→Sí').astype(float)
    totals=q.g.value_counts()
    q=q.loc[q.sexo_grupo_a.isin(['Hombre','Mujer'])&q.edad_06_a.isin(['60–64','65–69','70+'])&q.esc.ne('ND')].copy()
    q['cell']=q.sexo_grupo_a.astype(str)+'|'+q.edad_06_a.astype(str)+'|'+q.esc
    counts=q.groupby(['cell','g']).size().unstack(fill_value=0).reindex(columns=[0,1],fill_value=0)
    support=counts.index[(counts[0]>=20)&(counts[1]>=20)].tolist();z=q.loc[q.cell.isin(support)].copy()
    retained=[int(z.g.eq(i).sum()) for i in [0,1]];full=[int(totals.get(i,0)) for i in [0,1]]
    coverage=[retained[i]/full[i] if full[i] else 0 for i in [0,1]]
    out=dict(estimando=kind,N_antes=full,N_soporte=retained,cobertura=coverage,N_celdas=len(support),celdas=support,viable=len(support)>=4 and min(coverage)>=.7,replicas=replicas)
    if not out['viable']:return dict(**out,estimacion=None,ic95=None,motivo='Soporte insuficiente: mínimo4 celdas y70% de cada grupo')
    cells=pd.Categorical(z.cell,categories=support).codes;g=z.g.to_numpy();v=z.v.to_numpy();code,fol=pd.factorize(z.cunicah_a);rng=np.random.default_rng(SEED)
    def calc(w):
        target=np.stack([w[:,cells==j].sum(axis=1) for j in range(len(support))],axis=1).astype(float);target/=target.sum(axis=1)[:,None]
        values=[]
        for i in [0,1]:
            mask=g==i;wg=w[:,mask].astype(float).copy();cc=cells[mask]
            for j in range(len(support)):
                c=cc==j;den=wg[:,c].sum(axis=1);wg[:,c]*=np.divide(target[:,j],den,out=np.zeros_like(den),where=den>0)[:,None]
            values.append(frequency_quantiles(v[mask],wg,inverse_cdf=True)[:,1] if kind=='dinero' else np.sum(wg*v[mask],axis=1))
        return values[0]-values[1]
    raw=float(np.median(v[g==0])-np.median(v[g==1])) if kind=='dinero' else float(v[g==0].mean()-v[g==1].mean())
    point=float(calc(np.ones((1,len(z))))[0]);draws=[]
    for start in range(0,replicas,32):
        w=rng.multinomial(len(fol),np.full(len(fol),1/len(fol)),size=min(32,replicas-start))[:,code]
        draws.extend(calc(w))
    return dict(**out,crudo_mismo_soporte=raw,estimacion=point,ic95=np.quantile(draws,[.025,.975]).tolist(),convencion='CDF inversa en dinero; diferencia de probabilidades en tasas')

def rate_difference(q: pd.DataFrame, via: str) -> dict:
    """Q1 menos Q4 entre negativas basales reobservadas con respuesta conocida."""
    q=q.loc[q.patrimonio_grupo_a.isin(['Q1','Q4'])];g=q.patrimonio_grupo_a.eq('Q1').to_numpy();y=classify(q,via).eq('No→Sí').to_numpy();codes,fol=pd.factorize(q.cunicah_a);rng=np.random.default_rng(SEED)
    if not g.any() or g.all():return dict(estimacion=None,ic95=None)
    point=float(y[g].mean()-y[~g].mean());draws=[]
    for start in range(0,4999,64):
        w=rng.multinomial(len(fol),np.full(len(fol),1/len(fol)),size=min(64,4999-start))[:,codes]
        draws.extend((w[:,g]@y[g])/w[:,g].sum(axis=1)-(w[:,~g]@y[~g])/w[:,~g].sum(axis=1))
    return dict(estimacion=point,ic95=np.quantile(draws,[.025,.975]).tolist(),N=[int(g.sum()),int((~g).sum())],replicas=4999)

def analyze() -> dict:
    import json
    f,_=load()
    from tesis_enasem.monetary_policy import load_events
    events,_=load_events(f,'A')
    counts=events.loc[events.id.notna()].groupby(['id','ano']).size()
    single=events.loc[events.id.notna()].set_index(['id','ano']).loc[counts.index[counts.eq(1)],'programa']
    assert single.index.is_unique
    r=json.loads((OUTPUT/'resultados.json').read_text())
    for w in r['ventanas']:
        a,b,via=w['origen'],w['destino'],w['via'];p=pair_frame(f,a,b);p.attrs['joint']=(a,b)==(2012,2015);p.attrs['via']=via
        p['grupo']=groups(p,via);p['monto_real']=p['monto_completo_'+via+'_b']*p.factor_b
        initial=union_receipt(p.pension_propia_k_a,p.apoyo_propio_a).eq(False).fillna(False);known=classify(p,via).isin(['No→No','No→Sí']);q=p.loc[initial&known].copy();q.attrs['via']=via
        if via=='A' and b==2018:
            program=single.xs(b,level='ano').reindex(p.index)
            w['instituciones']=[dict(institucion='Un evento A: '+name,**contrast(p.loc[program.eq(name)],(FIRST,OTHER),'monto_real',replicas=1999,seed=SEED)) for name in sorted(program.dropna().unique())]
        from tesis_enasem.benefit_transitions import missing_median_bounds
        bounds=[]
        for group in [FIRST,OTHER]:
            vals=p.loc[p.grupo.eq(group),'monto_real'];valid=vals.dropna().to_numpy(dtype=float)
            bounds.append(missing_median_bounds(valid,int(vals.isna().sum()),nonnegative=True))
        w['cotas_monto_P_C']=dict(perfiles=bounds,inferior=bounds[0]['inferior']-bounds[1]['superior'] if bounds[1]['superior'] is not None else None,superior=bounds[0]['superior']-bounds[1]['inferior'] if bounds[0]['superior'] is not None else None,nota='Cotas de identificación entre receptores observados; no IC ni imputación de ausentes/muertos')
        from tesis_enasem.monetary_policy import summarize
        for row in w['estratos']:
            sub=p.loc[p[row['dimension']+'_a'].eq(row['categoria'])]
            row['distribuciones']=[dict(grupo=group,**summarize(sub.loc[sub.grupo.eq(group),'monto_real'])) for group in [FIRST,OTHER]]
        w['gradiente_patrimonio']=rate_difference(q,via)
        w['ajuste_tasa']=standardize(q,'tasa')
        w['ajuste_monto']=standardize(p,'dinero')
        print(a,b,via,'gradiente',w['gradiente_patrimonio'],'ajustes',w['ajuste_tasa'],w['ajuste_monto'],flush=True)
    save_json(OUTPUT/'resultados.json',r)
    from tesis_enasem.central_analysis import fingerprint
    manifest=json.loads((OUTPUT/'manifest.json').read_text());manifest['sha_resultados']=fingerprint(OUTPUT/'resultados.json');manifest['codigo_suplemento']=fingerprint(__import__('pathlib').Path(__file__));save_json(OUTPUT/'manifest.json',manifest)
    return r
