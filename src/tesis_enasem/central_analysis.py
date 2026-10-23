"""Contraste central 09: recepción propia basal, perfiles y dinero posterior.

Reutiliza bases existentes; no reconstruye integración ni modifica microdatos.
"""
from __future__ import annotations
import json
from pathlib import Path
from hashlib import sha256
import numpy as np
import pandas as pd
from tesis_enasem.benefit_transitions import (WINDOWS,GATES,PATTERNS,event_measures,pair_frame,classify,frequency_quantiles,audit)
from tesis_enasem.monetary_policy import panel,pricing,sources,load_events,summarize
from tesis_enasem.economic_protection import save_json,union_receipt
from tesis_enasem.project_paths import PROJECT_ROOT as ROOT,INTERIM_DIR
OUTPUT=INTERIM_DIR/'incorporacion_proteccion_propia'
SEED=20261023
REPLICAS=4999
FIRST='Incorporación desde ambas negativas'
OTHER='Incorporación con otra vía basal'
UNKNOWN='Incorporación con otra vía ND'
CONT='Continuidad de la vía'
NONE='Persistencia sin ambas vías'

def fingerprint(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()

def load() -> tuple[pd.DataFrame, dict]:
    """Verifica insumos estadísticos históricos, no congela documentos editables."""
    old=json.loads((INTERIM_DIR/'transiciones_montos_pensionarios/insumos_protegidos.json').read_text())
    checked={}
    from tesis_enasem.project_paths import project_path
    for name,expected in old.items():
        if name.startswith(('data/raw/','data/processed/')):
            p=project_path(name)
            if fingerprint(p)!=expected: raise ValueError('Fuente estadística cambió: '+name)
            checked[str(p.relative_to(ROOT))]=expected
    indices,lines,manifest=sources()
    f=pricing(panel(),indices,lines)
    first=f.loc[f.tipent.eq(5)].groupby('id').ano.min()
    f['vital_discordante']=f.id.map(first).lt(f.ano)
    diagnostics={}
    for via in ('K','A'):
        e,diagnostics[via]=load_events(f,via)
        f=f.merge(event_measures(e,via),on=['id','ano'],how='left',validate='one_to_one')
        f['todos_capturados_'+via]=f['todos_capturados_'+via].fillna(False).astype(bool)
        f['monto_completo_'+via]=f['monto_completo_'+via].where(f[GATES[via]].eq(True).fillna(False))
    assert len(f)==99676 and f.id.nunique()==27171
    # Reproduce exactamente la auditoría08 guardada antes de nuevos cálculos.
    assert audit(f,dict(eventos=diagnostics,referencia=manifest['inpc_referencia']))==json.loads((INTERIM_DIR/'transiciones_montos_pensionarios/auditoria.json').read_text())
    cuts=[]
    f['patrimonio_grupo']='Desconocido'
    for year in sorted(f.ano.unique()):
        m=f.ano.eq(year)&f.directa&f.universo_60&f.imp_neto.notna()
        q=f.loc[m,'imp_neto'].quantile([.25,.5,.75]).to_numpy()
        assert len(set(q))==3
        f.loc[m,'patrimonio_grupo']=pd.cut(f.loc[m,'imp_neto'],[-np.inf,*q,np.inf],labels=['Q1','Q2','Q3','Q4']).astype(object)
        cuts.append(dict(ronda=int(year),N=int(m.sum()),cortes=q.tolist()))
    return f,dict(fuentes_verificadas=checked,cuartiles=cuts,diagnosticos=diagnostics)

def groups(p: pd.DataFrame, via: str) -> pd.Series:
    """Partición exhaustiva de cohorte; ambas negativas siempre exige dos No."""
    s=classify(p,via);other=GATES['A' if via=='K' else 'K']
    z=s.copy();new=s.eq('No→Sí')
    z.loc[new&p[other+'_a'].eq(False).fillna(False)]=FIRST
    z.loc[new&p[other+'_a'].eq(True).fillna(False)]=OTHER
    z.loc[new&p[other+'_a'].isna()]=UNKNOWN
    z.loc[s.eq('Sí→Sí')]=CONT
    # Conjunción longitudinal únicamente en la ventana admitida por ambas vías.
    if p.attrs.get('joint',False):
        u0=union_receipt(p.pension_propia_k_a,p.apoyo_propio_a)
        u1=union_receipt(p.pension_propia_k_b,p.apoyo_propio_b)
        z.loc[s.eq('No→No')&u0.eq(False).fillna(False)&u1.eq(False).fillna(False)]=NONE
    return z

def stats(q: pd.DataFrame, via: str) -> dict:
    amount=q['monto_completo_'+via+'_b']*q.factor_b
    profiles={}
    for field in ['sexo_grupo','edad_06','educacion_grupo','localidad_grupo','patrimonio_grupo']:
        profiles[field]=[dict(categoria=str(k),N=int(n),pct=100*int(n)/len(q)) for k,n in q[field+'_a'].value_counts(dropna=False).items()]
    return dict(N=len(q),N_patrimonio_valido=int(q.imp_neto_a.notna().sum()),patrimonio_almacenado=summarize(q.imp_neto_a),edad=summarize(q.edad_a),escolaridad=summarize(q.educacion_a),perfiles=profiles,monto_real=summarize(amount),monto_nominal=summarize(q['monto_completo_'+via+'_b']),N_sin_monto_real=int(amount.isna().sum()))

def contrast(q,labels,field,*,cluster=True,seed=SEED,replicas=REPLICAS):
    """Diferencia de medianas primero menos segundo, bootstrap por folio o ID.

    IC condicionales exploratorios, sin diseño de encuesta. Exige N>=20/grupo.
    """
    v=q[field].to_numpy(dtype=float,na_value=np.nan)
    masks=[q.grupo.eq(g).to_numpy()&np.isfinite(v) for g in labels]
    ns=[int(m.sum()) for m in masks]
    result=dict(grupos=list(labels),N=ns,campo=field,agrupamiento='folio' if cluster else 'persona',replicas=replicas,seed=seed)
    if min(ns)<20:return dict(**result,estimacion=None,ic95=None,motivo='Menos de20 válidos por grupo')
    keep=masks[0]|masks[1];q=q.loc[keep];v=v[keep];masks=[m[keep] for m in masks]
    key=q.cunicah_a.astype(str) if cluster else pd.Series(q.index.astype(str),index=q.index)
    codes,unique=pd.factorize(key);n=len(unique);rng=np.random.default_rng(seed)
    estimates=[]
    for start in range(0,replicas,64):
        w=rng.multinomial(n,np.full(n,1/n),size=min(64,replicas-start))[:,codes]
        med=[frequency_quantiles(v[m],w[:,m])[:,1] for m in masks]
        estimates.extend(med[0]-med[1])
    estimates=np.asarray(estimates);valid=np.isfinite(estimates)
    return dict(**result,estimacion=float(np.median(v[masks[0]])-np.median(v[masks[1]])),ic95=np.quantile(estimates[valid],[.025,.975]).tolist(),N_replicas_validas=int(valid.sum()))

def probability(q: pd.DataFrame, event: pd.Series) -> dict:
    """Proporción observada e IC Wilson condicional IID; folio como sensibilidad."""
    from statsmodels.stats.proportion import proportion_confint
    n=len(q);k=int(event.sum());ci=proportion_confint(k,n,method='wilson') if n else (None,None)
    # IC por folio: numerador y denominador se remuestrean juntos.
    if n:
        t=pd.DataFrame({'folio':q.cunicah_a.to_numpy(),'y':event.to_numpy(dtype=int)}).groupby('folio').y.agg(['sum','size'])
        rng=np.random.default_rng(SEED);vals=[];nc=len(t)
        for _ in range(0,1999,64):
            w=rng.multinomial(nc,np.full(nc,1/nc),size=min(64,1999-len(vals)))
            vals.extend((w@t['sum'].to_numpy())/(w@t['size'].to_numpy()))
        folio=np.quantile(vals,[.025,.975]).tolist()
    else:folio=None
    return dict(N_denominador=n,N_incorporados=k,proporcion=k/n if n else None,ic95_wilson=list(ci),ic95_folio=folio)

def analyze() -> dict:
    f,meta=load();waves=[];windows=[]
    for year in sorted(f.ano.unique()):
        q=f.loc[f.ano.eq(year)&f.directa&f.universo_60]
        for via in ('K','A'):
            gate=q[GATES[via]];rec=gate.eq(True).fillna(False)
            waves.append(dict(ronda=int(year),via=via,N=len(q),N_conocido=int(gate.notna().sum()),N_si=int(rec.sum()),N_no=int(gate.eq(False).sum()),N_ND=int(gate.isna().sum()),monto_real=summarize((q['monto_completo_'+via]*q.factor).loc[rec])))
    for a,b,via in WINDOWS:
        print('Analizando',a,b,via,flush=True)
        p=pair_frame(f,a,b);p.attrs['joint']=(a,b)==(2012,2015)
        p['grupo']=groups(p,via);p['monto_real']=p['monto_completo_'+via+'_b']*p.factor_b
        other=GATES['A' if via=='K' else 'K'];s=classify(p,via)
        state=[dict(grupo=g,**stats(p.loc[p.grupo.eq(g)],via)) for g in p.grupo.unique()]
        new=p.loc[s.eq('No→Sí')];n=len(new)
        composition=[dict(grupo=g,N=int(new.grupo.eq(g).sum()),denominador=n,pct=100*int(new.grupo.eq(g).sum())/n if n else None) for g in (FIRST,OTHER,UNKNOWN)]
        baseline=union_receipt(p.pension_propia_k_a,p.apoyo_propio_a).eq(False).fillna(False)
        at_risk=[]
        for label,mask in [('Ambas negativas',baseline),('Otra vía basal',p[GATES[via]+'_a'].eq(False).fillna(False)&p[other+'_a'].eq(True).fillna(False))]:
            t=p.loc[mask];known=classify(t,via).isin(['No→No','No→Sí']);obs=t.loc[known];event=classify(obs,via).eq('No→Sí')
            k=int(event.sum());missing=len(t)-len(obs);dead=int(classify(t,via).eq('Fallecido registrado').sum())
            at_risk.append(dict(perfil=label,N_basal=len(t),destinos=classify(t,via).value_counts().to_dict(),observada=probability(obs,event),fraccion_cohorte_detectada=k/len(t) if len(t) else None,cota_entre_no_fallecidos_registrados=[k/(len(t)-dead),(k+missing-dead)/(len(t)-dead)] if len(t)>dead else None,nota='Cotas de identificación de recepción de destino; no incidencia antes de morir. Ausentes no son vivos confirmados.'))
        rates=[]
        for field in ['patrimonio_grupo','sexo_grupo','edad_06','educacion_grupo','localidad_grupo']:
            for value in sorted(p[field+'_a'].unique()):
                t=p.loc[baseline&p[field+'_a'].eq(value)];known=classify(t,via).isin(['No→No','No→Sí']);obs=t.loc[known]
                rates.append(dict(dimension=field,categoria=value,N_basal=len(t),**probability(obs,classify(obs,via).eq('No→Sí'))))
        contrasts=[]
        for labels in [(FIRST,OTHER),(FIRST,CONT),(OTHER,CONT)]:
            for field in ['monto_real','imp_neto_a','edad_a','educacion_a']:
                contrasts.append(contrast(p,labels,field,seed=SEED+a+b))
            contrasts.append(contrast(p,labels,'monto_real',cluster=False,seed=SEED+a+b))
        # Estratos descriptivos preespecificados: no escoger por signo o IC.
        strat=[]
        for field in ['sexo_grupo','edad_06','educacion_grupo','patrimonio_grupo']:
            for value in sorted(p[field+'_a'].unique()):
                q=p.loc[p[field+'_a'].eq(value)]
                c=contrast(q,(FIRST,OTHER),'monto_real',replicas=1999,seed=SEED+a+b)
                strat.append(dict(dimension=field,categoria=value,**c))
        institution=[]
        if via=='K':
            for name,mask in [('Evidencia IMSS/ISSSTE',p.evidencia_seguridad_K_b.eq(True)),('Programa agrupado',p.evidencia_programa_K_b.eq(True)),('Un evento IMSS',p.N_eventos_K_b.eq(1)&p.institucion_unica_K_b.eq(1)),('Un evento ISSSTE',p.N_eventos_K_b.eq(1)&p.institucion_unica_K_b.eq(2))]:
                institution.append(dict(institucion=name,**contrast(p.loc[mask],(FIRST,OTHER),'monto_real',replicas=1999,seed=SEED+a+b)))
        coexist=[]
        # Solo se describe la otra respuesta al destino, no se infiere su transición.
        for g in (FIRST,OTHER):
            q=p.loc[p.grupo.eq(g)]
            coexist.append(dict(grupo=g,N=len(q),otra_si=int(q[other+'_b'].eq(True).sum()),otra_no=int(q[other+'_b'].eq(False).sum()),otra_ND=int(q[other+'_b'].isna().sum()),transicion_conjunta_admisible=(a,b)==(2012,2015)))
        sensitivity=[]
        for name,sp in [('Incluye sustituto destino',classify(p,via,proxies=True)),('Edad destino60+',s.where(p.edad_b.ge(60),'Destino no60+'))]:
            m=sp.eq('No→Sí');sensitivity.append(dict(criterio=name,N_nuevos=int(m.sum()),N_primera=int((m&p[other+'_a'].eq(False).fillna(False)).sum()),N_otra=int((m&p[other+'_a'].eq(True).fillna(False)).sum())))
        monetary_dates=[dict(criterio=col,**contrast(p.assign(monto_alternativo=p['monto_completo_'+via+'_b']*p[col+'_b']),(FIRST,OTHER),'monto_alternativo',replicas=1999,seed=SEED+a+b)) for col in ['factor_12m','factor_ano_entrevista']]
        windows.append(dict(origen=a,destino=b,via=via,N_cohorte=len(p),grupos=state,composicion=composition,riesgo=at_risk,tasas_perfil=rates,contrastes=contrasts,estratos=strat,instituciones=institution,coexistencia=coexist,sensibilidades=sensitivity,fechas=monetary_dates))
    # Unión conjunta: una persona que inicia K y A simultáneamente cuenta una vez.
    p=pair_frame(f,2012,2015);u0=union_receipt(p.pension_propia_k_a,p.apoyo_propio_a);u1=union_receipt(p.pension_propia_k_b,p.apoyo_propio_b)
    allowed=p.tipent_b.isin([1,2])&~(p.vital_discordante_a|p.vital_discordante_b).fillna(False)
    initial=u0.eq(False).fillna(False);obs=p.loc[initial&allowed&u1.notna()]
    joint=dict(origen=2012,destino=2015,N_basal=int(initial.sum()),**probability(obs,u1.loc[obs.index].eq(True)),N_sin_recepcion_destino=int(u1.loc[obs.index].eq(False).sum()),N_inicia_ambas=int((initial&allowed&p.pension_propia_k_b.eq(True).fillna(False)&p.apoyo_propio_b.eq(True).fillna(False)).sum()))
    sj=classify(p,'K');sj.loc[allowed]='Unión ND al destino';sj.loc[allowed&u1.eq(True).fillna(False)]='Incorpora unión';sj.loc[allowed&u1.eq(False).fillna(False)]='Sin ambas al destino'
    joint['destinos']=sj.loc[initial].value_counts().to_dict()
    result=dict(etapa='09',semilla=SEED,replicas=REPLICAS,metadata=meta,rondas=waves,ventanas=windows,union=joint)
    validate(result);save_json(OUTPUT/'resultados.json',result)
    save_json(OUTPUT/'manifest.json',dict(sha_resultados=fingerprint(OUTPUT/'resultados.json'),codigo=fingerprint(ROOT/'src/tesis_enasem/central_analysis.py'),fuentes=meta['fuentes_verificadas'],metodo='Bootstrap folio/persona; IC puntuales exploratorios, no diseño; 4999/1999 réplicas',unidad_patrimonio='Unidades almacenadas sin moneda/precios homologados: cuartiles dentro de ronda, nunca crecimiento real'))
    return result

def validate(r: dict) -> None:
    assert len(r['rondas'])==12 and len(r['ventanas'])==6
    for w in r['ventanas']:
        assert sum(g['N'] for g in w['grupos'])==w['N_cohorte']
        assert sum(g['N'] for g in w['composicion'])==sum(g['N'] for g in w['grupos'] if g['grupo'] in (FIRST,OTHER,UNKNOWN))
        for t in w['riesgo']:
            assert sum(t['destinos'].values())==t['N_basal']
            assert t['observada']['N_incorporados']<=t['observada']['N_denominador']<=t['N_basal']
        for g in w['grupos']:
            assert g['monto_real']['N']+g['N_sin_monto_real']==g['N']
    assert r['union']['N_incorporados']+r['union']['N_sin_recepcion_destino']==r['union']['N_denominador']
