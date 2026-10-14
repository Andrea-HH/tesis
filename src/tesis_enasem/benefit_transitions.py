"""Transiciones08: recepción observada y montos íntegros de eventos captados.

No identifica altas administrativas ni la identidad de una prestación. No suma
montos cuando falta el importe de algún evento captado ni utiliza imputados.
"""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any

import numpy as np
import pandas as pd

from .economic_protection import pct, save_json
from .monetary_policy import (
    QUESTION, REFERENCE, REFERENCE_INDEX, load_events, panel, pricing, sources,
    summarize,
)
from .project_paths import INTERIM_DIR, PROJECT_ROOT

OUTPUT = INTERIM_DIR / "transiciones_montos_pensionarios"
NOTEBOOK = "08_TRANSICIONES_MONTOS_PENSIONARIOS.ipynb"
WINDOWS = ((2001, 2003, "K"), (2012, 2015, "K"), (2018, 2021, "K"),
           (2003, 2012, "A"), (2012, 2015, "A"), (2015, 2018, "A"))
FOCUS = ((2012, 2015, "K"), (2015, 2018, "A"))
GATES = {"K": "pension_propia_k", "A": "apoyo_propio"}
PROFILE_DIMENSIONS = ("sexo_grupo", "edad_06", "educacion_grupo",
                      "localidad_grupo", "ocupacion_grupo", "conyugal_grupo")
PATTERNS = ("No→No", "No→Sí", "Sí→Sí", "Sí→No")


def verify_inputs() -> int:
    """Coteja bases, notebooks01–07, fuentes, resultados y manuscrito anteriores."""
    fingerprints = json.loads((OUTPUT / "insumos_protegidos.json").read_text())
    for name, expected in fingerprints.items():
        if sha256((PROJECT_ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Cambió archivo anterior protegido: {name}")
    return len(fingerprints)


def event_measures(events: pd.DataFrame, via: str) -> pd.DataFrame:
    """Suma únicamente conjuntos con todos sus importes captados válidos.

Un evento único K de IMSS/ISSSTE permite comprobar contingencia e institución,
sin que ello pruebe la identidad administrativa de la pensión entre visitas.
"""
    keys = ["id", "ano"]
    e = events.loc[events.id.notna()].copy()
    e["_finite"] = e.monto_mensual_observado.notna() & np.isfinite(e.monto_mensual_observado) & e.monto_mensual_observado.ge(0)
    assert (e._finite == e.monto_mensual_observado.notna()).all()
    grouped = e.groupby(keys, observed=True)
    n = grouped.size().rename("N_eventos")
    valid = grouped._finite.sum().rename("N_montos")
    total = grouped.monto_mensual_observado.sum(min_count=1)
    f = pd.concat([n, valid], axis=1)
    f["todos_capturados"] = f.N_eventos.gt(0) & f.N_eventos.eq(f.N_montos)
    f["monto_completo"] = total.where(f.todos_capturados)
    f["firma_seguridad"] = None
    f["tipo_unico"] = None
    f["institucion_unica"] = None
    if via == "K":
        f['evidencia_programa']=grouped.programa_publico_agrupado.any()
        f['evidencia_seguridad']=grouped.seguridad_social_identificada.any()
        single = e.set_index(keys).loc[f.index[f.N_eventos.eq(1)]]
        for key, row in single.iterrows():
            codes = tuple(sorted(set(int(x) for x in row.instituciones_codigos)))
            f.loc[key, "tipo_unico"] = int(row.tipo)
            if len(codes) == 1:
                f.loc[key, "institucion_unica"] = codes[0]
            if len(codes) == 1 and codes[0] in (1, 2):
                f.loc[key, "firma_seguridad"] = f"{int(row.tipo)}:{codes[0]}"
    return f.add_suffix("_"+via).reset_index()


def load_inputs() -> tuple[pd.DataFrame, dict[str, Any]]:
    """Reutiliza integración/07; las únicas uniones nuevas son LEFT uno a uno."""
    verify_inputs()
    indices, lines, manifest = sources()
    f = pricing(panel(), indices, lines)
    assert len(f) == 99676 and f.id.nunique() == 27171
    first_dead=f.loc[f.tipent.eq(5)].groupby('id').ano.min()
    f['vital_discordante']=f.id.map(first_dead).lt(f.ano)
    diagnostics = {}
    for via in ("K", "A"):
        e, diagnostics[via] = load_events(f, via)
        measures = event_measures(e, via)
        f = f.merge(measures, on=["id", "ano"], how="left", validate="one_to_one")
        assert len(f) == 99676 and not f[["id", "ronda"]].duplicated().any()
        f["todos_capturados_"+via] = f["todos_capturados_"+via].fillna(False).astype(bool)
        gate = f[GATES[via]].eq(True).fillna(False)
        f["monto_completo_"+via] = f["monto_completo_"+via].where(gate)
        old = f[f"monto_{via.lower()}_propio_mensual_observado_parcial"]
        observed = f["monto_completo_"+via].notna()
        assert np.allclose(f.loc[observed, "monto_completo_"+via], old.loc[observed])
    return f, dict(eventos=diagnostics, referencia=manifest["inpc_referencia"])


def pair_frame(f: pd.DataFrame, a: int, b: int) -> pd.DataFrame:
    """Cohorte basal directa60+; conserva todos los destinos y edad discordante."""
    o = f.loc[f.ano.eq(a) & f.universo_60 & f.directa].set_index("id")
    d = f.loc[f.ano.eq(b)].set_index("id")
    assert o.index.is_unique and d.index.is_unique
    p = o.join(d, how="left", lsuffix="_a", rsuffix="_b", validate="one_to_one")
    assert len(p) == len(o)
    return p


def classify(p: pd.DataFrame, via: str, proxies: bool = False, *, honor_conflicts: bool=True) -> pd.Series:
    """Clasifica sin convertir ND, muerte o exclusión de modalidad en negativa."""
    gate = GATES[via]
    s = pd.Series("Estado no clasificable", index=p.index, dtype=object)
    present = p.ano_b.notna()
    s.loc[~present] = "Ausente; vital desconocido"
    s.loc[p.tipent_b.eq(5)] = "Fallecido registrado"
    allowed = p.tipent_b.isin([1, 2, 3, 4] if proxies else [1, 2])
    s.loc[p.tipent_b.isin([3, 4])] = "Sustituto vivo; fuera del principal"
    s.loc[allowed] = "Recepción ND en alguna visita"
    for x, y, label in [(False, False, PATTERNS[0]), (False, True, PATTERNS[1]),
                        (True, True, PATTERNS[2]), (True, False, PATTERNS[3])]:
        mask = allowed & p[gate+"_a"].eq(x).fillna(False) & p[gate+"_b"].eq(y).fillna(False)
        s.loc[mask] = label
    if honor_conflicts and 'vital_discordante_a' in p:
        conflict=p.vital_discordante_a.eq(True)|p.vital_discordante_b.eq(True)
        s.loc[allowed & conflict]='Conflicto de estado vital registrado'
    assert s.notna().all()
    return s


def audit(f: pd.DataFrame, diagnostics: dict[str, Any]) -> dict[str, Any]:
    """Viabilidad primero; concilia cada N y monto íntegro con los agregados07."""
    r7 = json.loads((INTERIM_DIR / "politicas_montos_suficiencia/resultados.json").read_text())
    waves, intervals = [], []
    for via in ("K", "A"):
        for year in (2001, 2003, 2012, 2015, 2018, 2021):
            q = f.loc[f.ano.eq(year) & f.universo_60 & f.directa]
            old = next(x for x in r7['montos'] if (x['ronda'], x['via'], x['dimension']) == (year, via, 'General'))
            rec = q[GATES[via]].eq(True).fillna(False)
            complete = q['monto_completo_'+via].notna()
            assert int(rec.sum()) == old['N_receptores']
            assert int(complete.sum()) == old['N_todos_eventos_capturados']
            waves.append(dict(ronda=year, via=via, N_directas_60=len(q),
                N_recepcion_conocida=int(q[GATES[via]].notna().sum()),
                N_receptores=int(rec.sum()), N_monto_parcial07=old['N_monto'],
                N_todos_capturados_monto=int(complete.sum()),
                N_algun_evento_ND=old['N_parciales'],
                N_receptores_sin_monto=old['N_receptores_sin_monto']))
    for a, b, via in WINDOWS:
        p = pair_frame(f, a, b);s = classify(p, via)
        old = next(x for x in r7['seleccion'] if (x['origen'],x['destino'],x['via'],x['dimension'])==(a,b,via,'General'))
        complete = s.eq('Sí→Sí') & p['monto_completo_'+via+'_a'].notna() & p['monto_completo_'+via+'_b'].notna() & p.factor_a.notna() & p.factor_b.notna()
        single = complete & p['N_eventos_'+via+'_a'].eq(1) & p['N_eventos_'+via+'_b'].eq(1)
        stable = single & p['firma_seguridad_'+via+'_a'].notna() & p['firma_seguridad_'+via+'_a'].eq(p['firma_seguridad_'+via+'_b']) if via=='K' else pd.Series(False,index=p.index)
        raw=classify(p,via,honor_conflicts=False)
        conflicts=int((raw.isin(PATTERNS)&s.eq('Conflicto de estado vital registrado')).sum())
        assert int(s.isin(PATTERNS).sum())+conflicts == old['N_pares_conocidos']
        intervals.append(dict(origen=a,destino=b,via=via,N_cohorte=len(p),
            N_presentes=int(p.ano_b.notna().sum()),N_directas_destino=int(p.tipent_b.isin([1,2]).sum()),
            N_pares_recepcion_conocida=int(s.isin(PATTERNS).sum()),
            N_pares_vital_discordante_excluidos=conflicts,
            N_continuos=int(s.eq('Sí→Sí').sum()),N_nuevos=int(s.eq('No→Sí').sum()),
            N_pares_parciales07=old['N_receptores_ambas_monto'],
            N_pares_todos_capturados=int(complete.sum()),N_un_evento_ambas=int(single.sum()),
            N_misma_contingencia_IMSS_ISSSTE=int(stable.sum()) if via=='K' else None,
            N_nuevos_monto_completo=int((s.eq('No→Sí') & p['monto_completo_'+via+'_b'].notna() & p.factor_b.notna()).sum()),
            identidad_prestacion_comprobada=False,
            conclusion='Recepción propia y suma íntegra de eventos captados comparables condicionadamente; sin identidad administrativa.' if via=='K' else 'Donativos generales dinero/especie; cambio de captura; sin A5 ni programa longitudinal identificado.'))
    return dict(pregunta=QUESTION,estado='Viabilidad condicionada; nunca identidad administrativa de prestación',
        rondas=waves,intervalos=intervals,diagnosticos=diagnostics,
        foco=[list(x) for x in FOCUS],
        comparabilidad=r7['comparabilidad'],
        nivel='Persona para recepción y suma íntegra captada; evento solo para auditoría y restricción de concepto.',
        periodicidad='Mes normal en pesos; no dividir de nuevo por2.',
        integridad='Completo solo respecto de eventos captados, sin garantía de totalidad real. Todos los eventos captados requieren monto válido.',
        A5='Identificado en2021; no disponible como programa homologado en2015–2018.',
        previo07='1762K y1240A son pares con sumas parciales; se exige mayor integridad en08.',
        continuidad='Mismos IDs, 60+ y directa al inicio. Edad al destino no filtra automáticamente. No panel balanceado.')


def monetary(q: pd.DataFrame, via: str, visit: str) -> dict[str, Any]:
    """Distribución íntegra captada; los N de recepción y de dinero son distintos."""
    amount = q['monto_completo_'+via+'_'+visit]
    factor = q['factor_'+visit]
    return dict(N_receptores=len(q), N_monto_nominal=int(amount.notna().sum()),
        N_monto_real=int((amount.notna() & factor.notna()).sum()),
        N_sin_monto_integro=int(amount.isna().sum()),
        N_precio_ND=int((amount.notna() & factor.isna()).sum()),
        nominal=summarize(amount), real=summarize(amount*factor),
        real_12m=summarize(amount*q['factor_12m_'+visit]),
        real_ano_entrevista=summarize(amount*q['factor_ano_entrevista_'+visit]),
        N_varios_eventos=int(q['N_eventos_'+via+'_'+visit].gt(1).sum()),
        N_edad_final_menor60=int(q.edad_b.lt(60).sum()))


def transition_summary(p: pd.DataFrame, via: str) -> dict[str, Any]:
    """Matriz exhaustiva más probabilidades descriptivas condicionadas a observar."""
    s=classify(p,via);known=int(s.isin(PATTERNS).sum())
    counts=s.value_counts().to_dict()
    rows=[dict(estado=label,N=int(counts.get(label,0)),pct_cohorte=pct(int(counts.get(label,0)),len(p)),
               pct_pares_conocidos=pct(int(counts.get(label,0)),known) if label in PATTERNS else None)
          for label in (*PATTERNS,'Fallecido registrado','Ausente; vital desconocido',
                        'Sustituto vivo; fuera del principal','Recepción ND en alguna visita',
                        'Conflicto de estado vital registrado','Estado no clasificable')]
    assert sum(x['N'] for x in rows)==len(p)
    gate=GATES[via]
    no=int(p[gate+'_a'].eq(False).sum());yes=int(p[gate+'_a'].eq(True).sum())
    return dict(N_cohorte=len(p),N_pares_conocidos=known,estados=rows,
        N_basal_no=no,N_basal_si=yes,N_basal_ND=int(p[gate+'_a'].isna().sum()),
        inicio_entre_negativas_reobservadas_pct=pct(counts.get('No→Sí',0),counts.get('No→No',0)+counts.get('No→Sí',0)),
        inicio_sobre_cohorte_negativa_pct=pct(counts.get('No→Sí',0),no),
        deja_entre_receptores_reobservados_pct=pct(counts.get('Sí→No',0),counts.get('Sí→Sí',0)+counts.get('Sí→No',0)),
        deja_sobre_cohorte_receptora_pct=pct(counts.get('Sí→No',0),yes))


def paired_summary(q: pd.DataFrame, via: str) -> dict[str, Any]:
    """Identidad contable individual y puente de medianas en la misma muestra.

El puente de medianas congela primero nominal y aplica precios de destino.
Sus dos términos suman la diferencia de medianas, pero dependen del orden.
Las medianas de términos individuales no son una descomposición aditiva.
"""
    n0=q['monto_completo_'+via+'_a'];n1=q['monto_completo_'+via+'_b']
    f0,f1=q.factor_a,q.factor_b
    assert n0.notna().all() and n1.notna().all() and f0.notna().all() and f1.notna().all()
    r0,r1=n0*f0,n1*f1
    delta=r1-r0;price=n0*(f1-f0);nominal=(n1-n0)*f1
    assert np.allclose(delta,price+nominal)
    original,reprice,final=r0.median(),(n0*f1).median(),r1.median()
    reverse=(n1*f0).median()
    price_bridge=reprice-original;nominal_bridge=final-reprice
    assert np.isclose(final-original,price_bridge+nominal_bridge) if len(q) else True
    months=(12*(q.a_o_ent_b-q.a_o_ent_a)+q.mes_ent_b-q.mes_ent_a)
    months=months.where(q.mes_ent_a.between(1,12) & q.mes_ent_b.between(1,12) & months.gt(0))
    relative=100*(r1/r0-1).where(n0.gt(0))
    return dict(N=len(q),nominal_inicial=summarize(n0),nominal_final=summarize(n1),
        real_inicial=summarize(r0),real_final=summarize(r1),
        diferencia_medianas_nominal=float(n1.median()-n0.median()) if len(q) else None,
        diferencia_medianas_real=float(final-original) if len(q) else None,
        cambio_individual_nominal=summarize(n1-n0),cambio_individual_real=summarize(delta),
        cambio_individual_real_pct=summarize(relative),
        N_real_baja=int(delta.lt(-1e-9).sum()),N_real_sube=int(delta.gt(1e-9).sum()),N_real_igual=int(delta.abs().le(1e-9).sum()),
        inflacion_criterio_periodo_pct=summarize(100*(q.inpc_original_b/q.inpc_original_a-1)),
        meses_entrevistas=summarize(months),
        cambio_real_12m=summarize(n1*q.factor_12m_b-n0*q.factor_12m_a),
        cambio_real_ano_entrevista=summarize(n1*q.factor_ano_entrevista_b-n0*q.factor_ano_entrevista_a),
        identidad_contable=dict(precio_individual=summarize(price),nominal_individual=summarize(nominal),
            suma_medias=float(price.mean()+nominal.mean()) if len(q) else None,
            media_cambio=float(delta.mean()) if len(q) else None),
        puente_medianas=dict(orden='Nominal basal congelado, luego cambio nominal a precios de destino',
            mediana_basal_repreciada=float(reprice) if len(q) else None,
            termino_precio=float(price_bridge) if len(q) else None,
            termino_nominal=float(nominal_bridge) if len(q) else None,
            precio_orden_inverso=float(final-reverse) if len(q) else None,
            nominal_orden_inverso=float(reverse-original) if len(q) else None,
            causal=False))


def weighted_quantiles(values: pd.Series, weights: pd.Series) -> dict[str, float | None]:
    """Cuantil inverso de CDF ponderada; no promedio de medianas de estratos."""
    valid=values.notna() & weights.notna() & weights.gt(0)
    v=values.loc[valid].to_numpy(float);w=weights.loc[valid].to_numpy(float)
    if not len(v):return {k:None for k in ['p10','q25','mediana','q75','p90']}
    order=np.argsort(v,kind='stable');v,w=v[order],w[order]
    cdf=np.cumsum(w)/w.sum()
    return {k:float(v[min(np.searchsorted(cdf,q,side='left'),len(v)-1)])
            for k,q in [('p10',.1),('q25',.25),('mediana',.5),('q75',.75),('p90',.9)]}


def standardize(q: pd.DataFrame, via: str, *, locality: bool=False) -> dict[str, Any]:
    """Composición común basal sexo×edad×escolaridad, con soporte verificable.

Población objetivo: mezcla empírica de nuevos/continuos con montos íntegros y
datos basales conocidos, en celdas con al menos20 de cada grupo. Requiere70%
de cobertura por grupo; no pondera mortalidad, ausentes ni diseño de ENASEM.
"""
    q=q.loc[q.patron.isin(['No→Sí','Sí→Sí'])].copy()
    q=q.loc[q['monto_completo_'+via+'_b'].notna() & q.factor_b.notna()]
    q['esc_basal']=np.where(q.educacion_a.between(0,5),'0–5',
                          np.where(q.educacion_a.ge(6),'6+','Desconocido'))
    dims=['sexo_grupo_a','edad_06_a','esc_basal']+(['localidad_grupo_a'] if locality else [])
    valid=q[dims].ne('Desconocido').all(axis=1) & q[dims].notna().all(axis=1)
    good=q.loc[valid].copy()
    good['estrato']=good[dims].astype(str).agg(' / '.join,axis=1)
    counts=pd.crosstab(good.estrato,good.patron).reindex(columns=['No→Sí','Sí→Sí'],fill_value=0)
    supported=counts.index[counts.min(axis=1).ge(20)]
    used=good.loc[good.estrato.isin(supported)].copy()
    population={g:int(q.patron.eq(g).sum()) for g in ['No→Sí','Sí→Sí']}
    retained={g:int(used.patron.eq(g).sum()) for g in population}
    fraction={g:pct(retained[g],population[g]) for g in population}
    feasible=len(supported)>=4 and all(v is not None and v>=70 for v in fraction.values())
    target=counts.loc[supported].sum(axis=1)
    target=target/target.sum() if len(target) else target
    rows=[]
    for s,row in counts.iterrows():
        rows.append(dict(estrato=s,N_nuevos=int(row['No→Sí']),N_continuos=int(row['Sí→Sí']),
                         usado=s in supported,peso_objetivo=float(target.get(s,0))))
    results=[]
    for g in population:
        p=used.loc[used.patron.eq(g)].copy()
        if len(p):
            p['peso']=p.estrato.map(target)/p.estrato.map(counts[g])
            assert np.isclose(p.peso.sum(),1)
            for unit,factor in [('nominal',1),('real',p.factor_b)]:
                value=p['monto_completo_'+via+'_b']*factor
                results.append(dict(grupo=g,unidad=unit,N=len(p),
                    observado_en_soporte_CDF=weighted_quantiles(value,pd.Series(1.,index=p.index)),
                    ajustado_CDF=weighted_quantiles(value,p.peso) if feasible else None,
                    ESS_descriptivo=float(p.peso.sum()**2/(p.peso**2).sum())))
    return dict(dimensiones=dims,minimo_por_celda_grupo=20,cobertura_minima_pct=70,
        viable=feasible,N_original=population,N_en_soporte=retained,pct_en_soporte=fraction,
        N_covariables_ND={g:int((q.patron.eq(g)&~valid).sum()) for g in population},
        estratos=rows,distribuciones=results,
        estimando='Distribución mensual de nuevos/continuos entre observados con monto íntegro, a mezcla basal común de soporte.',
        limites='No causalidad, no estimación nacional, no corrección de mortalidad/ausencia. Covariables restantes pueden diferir; cuantil CDF, no media de medianas.')


def profiles(q: pd.DataFrame, suffix: str, population: str) -> list[dict[str, Any]]:
    """Composición categorical con ND separados y denominador de cada grupo."""
    out=[]
    for pattern,p in q.groupby('patron',observed=True):
        for dim in PROFILE_DIMENSIONS:
            values=p[dim+'_'+suffix].fillna('Desconocido')
            known=int(values.ne('Desconocido').sum())
            for label,n in values.value_counts().items():
                out.append(dict(poblacion=population,visita=suffix,patron=str(pattern),
                    dimension=dim,grupo=str(label),N=int(n),N_total=len(p),N_conocido=known,
                    pct_total=pct(int(n),len(p)),pct_conocidos=pct(int(n),known) if label!='Desconocido' else None))
    return out


def destination_partition(f: pd.DataFrame, p: pd.DataFrame, a: int, b: int, via: str) -> dict[str, Any]:
    """Explica quién está fuera de la cohorte basal en la distribución transversal."""
    gate=GATES[via]
    d=f.loc[f.ano.eq(b) & f.universo_60 & f.directa & f[gate].eq(True).fillna(False)].set_index('id')
    o=f.loc[f.ano.eq(a)].set_index('id')
    joined=d.join(o,how='left',lsuffix='_b',rsuffix='_a',validate='one_to_one')
    joined['patron']='Origen no clasificable'
    joined.loc[joined.ano_a.isna(),'patron']='Sin registro en ronda basal'
    joined.loc[joined.tipent_a.isin([1,2,3,4]) & joined.edad_a.lt(60),'patron']='Entrada por edad: basal menor60'
    joined.loc[joined.tipent_a.isin([3,4]) & joined.edad_a.ge(60),'patron']='Basal sustituto60+'
    joined.loc[joined.tipent_a.isin([1,2]) & joined.edad_a.ge(60),'patron']=classify(p,via).reindex(joined.index)
    joined.loc[joined.tipent_a.eq(5),'patron']='Registro previo sobre fallecido; discordancia conservada'
    rows=[]
    for group,q in joined.groupby('patron',observed=True):
        rows.append(dict(grupo=str(group),N_receptores=len(q),
            N_monto_integro=int(q['monto_completo_'+via+'_b'].notna().sum()),
            nominal=summarize(q['monto_completo_'+via+'_b']),
            real=summarize(q['monto_completo_'+via+'_b']*q.factor_b)))
    assert sum(z['N_receptores'] for z in rows)==len(d)
    return dict(N_receptores_transversal=len(d),grupos=rows,
        perfiles=profiles(joined,'b','Receptores transversales de destino'))


def selection(p: pd.DataFrame, f: pd.DataFrame, a: int, b: int, via: str) -> list[dict[str, Any]]:
    """Destinos y montos basales por recepción inicial; no prestación post mortem."""
    gate=GATES[via];s=classify(p,via);out=[]
    for initial,mask in [('No',p[gate+'_a'].eq(False).fillna(False)),
                         ('Sí',p[gate+'_a'].eq(True).fillna(False)),('ND',p[gate+'_a'].isna())]:
        q=p.loc[mask];state=s.loc[mask]
        absent=q.index[state.eq('Ausente; vital desconocido')]
        later=f.loc[f.ano.gt(b) & f.id.isin(absent)]
        live_ids=set(later.loc[later.vivo,'id']);dead_ids=set(later.loc[later.tipent.eq(5),'id'])
        rows=[]
        for label,part in q.groupby(state,observed=True):
            rows.append(dict(destino=str(label),N=len(part),pct_basal=pct(len(part),len(q)),
                nominal_basal=summarize(part['monto_completo_'+via+'_a']),
                real_basal=summarize(part['monto_completo_'+via+'_a']*part.factor_a)))
        assert sum(z['N'] for z in rows)==len(q)
        out.append(dict(recepcion_basal=initial,N_basal=len(q),destinos=rows,
            N_ausentes=int(state.eq('Ausente; vital desconocido').sum()),
            N_reaparece_vivo_despues=len(live_ids) if b<2021 else None,
            N_registro_fallecido_despues=len(dead_ids) if b<2021 else None,
            N_ambos_registros_posteriores=len(live_ids&dead_ids) if b<2021 else None))
    return out


def analyze() -> dict[str, Any]:
    """Etapa08 desde cero; solo dos intervalos monetarios centrales nuevos."""
    f,diagnostics=load_inputs();audited=audit(f,diagnostics)
    assert audited==json.loads((OUTPUT/'auditoria.json').read_text()),'Auditoría08 cambió'
    previous=json.loads((INTERIM_DIR/'politicas_montos_suficiencia/resultados.json').read_text())
    transitions=[]
    for a,b,via in WINDOWS:
        transitions.append(dict(origen=a,destino=b,via=via,**transition_summary(pair_frame(f,a,b),via)))
    details=[]
    for a,b,via in FOCUS:
        p=pair_frame(f,a,b);p['patron']=classify(p,via)
        known=p.loc[p.patron.isin(PATTERNS)]
        complete=p['monto_completo_'+via+'_b'].notna() & p.factor_b.notna()
        summaries=[dict(patron=pattern,visita='b' if pattern!='Sí→No' else 'a',
            **monetary(p.loc[p.patron.eq(pattern)],via,'b' if pattern!='Sí→No' else 'a'))
            for pattern in ['No→Sí','Sí→Sí','Sí→No']]
        paired=p.loc[p.patron.eq('Sí→Sí') & complete & p['monto_completo_'+via+'_a'].notna() & p.factor_a.notna()]
        one=paired.loc[paired['N_eventos_'+via+'_a'].eq(1) & paired['N_eventos_'+via+'_b'].eq(1)]
        stable=one.loc[one['firma_seguridad_'+via+'_a'].notna() & one['firma_seguridad_'+via+'_a'].eq(one['firma_seguridad_'+via+'_b'])] if via=='K' else one.iloc[0:0]
        ageconsistent=paired.loc[paired.edad_b.ge(60)]
        sensitivities=[dict(criterio='Un evento en ambas visitas; no identidad comprobada',**paired_summary(one,via)),
                       dict(criterio='Edad final60+; cambia universo de seguimiento',**paired_summary(ageconsistent,via))]
        raw=classify(p,via,honor_conflicts=False)
        raw_pairs=p.loc[raw.eq('Sí→Sí') & complete & p['monto_completo_'+via+'_a'].notna() & p.factor_a.notna()]
        sensitivities.append(dict(criterio='Registros observados incluyendo conflicto vital; no supuesto de vida real',
            N_vital_discordante=int((raw_pairs.vital_discordante_a.eq(True)|raw_pairs.vital_discordante_b.eq(True)).sum()),
            **paired_summary(raw_pairs,via)))
        if via=='K':sensitivities.append(dict(criterio='Un evento, misma contingencia e instituciónIMSS/ISSSTE',**paired_summary(stable,via)))
        ps=classify(p,via,True)
        for pattern in ['No→Sí','Sí→Sí']:
            q=p.loc[ps.eq(pattern)];z=monetary(q,via,'b')
            sensitivities.append(dict(criterio='Directas basales; destino directo o sustituto válido',patron=pattern,
                N_destino_sustituto=int(q.tipent_b.isin([3,4]).sum()),**z))
        annual=[]
        annual_profiles=[]
        for year in (a,b):
            q=f.loc[f.ano.eq(year)&f.universo_60&f.directa&f[GATES[via]].eq(True).fillna(False)].set_index('id')
            old=next(x for x in previous['montos'] if (x['ronda'],x['via'],x['dimension'])==(year,via,'General'))
            for dim in PROFILE_DIMENSIONS:
                parts=[x for x in previous['montos'] if (x['ronda'],x['via'],x['dimension'])==(year,via,dim)]
                assert sum(x['N_receptores'] for x in parts)==old['N_receptores']
                unknown=sum(x['N_receptores'] for x in parts if x['grupo']=='Desconocido')
                annual_profiles.extend(dict(ronda=year,dimension=dim,grupo=x['grupo'],N=x['N_receptores'],
                    N_total=old['N_receptores'],N_ND=unknown,pct_total=pct(x['N_receptores'],old['N_receptores'])) for x in parts)
            annual.append(dict(ronda=year,N_receptores=len(q),N_monto_parcial07=old['N_monto'],
                nominal_parcial07=old['persona']['nominal'],real_parcial07=old['persona']['real'],
                nominal_integro=summarize(q['monto_completo_'+via]),real_integro=summarize(q['monto_completo_'+via]*q.factor),
                fechas=[dict(ano_entrevista=int(y) if pd.notna(y) else None,N=int(n),
                    inpc=float(q.loc[q.a_o_ent.eq(y),'inpc_original'].iloc[0]) if pd.notna(y) else None)
                    for y,n in q.a_o_ent.value_counts(dropna=False).items()]))
        profiles_all=profiles(known.loc[known.patron.isin(['No→Sí','Sí→Sí','Sí→No'])],'a','Transiciones conocidas, perfiles basales')
        money_people=p.loc[p.patron.isin(['No→Sí','Sí→Sí']) & complete]
        profiles_money=profiles(money_people,'a','Montos íntegros de destino, perfiles basales')+profiles(money_people,'b','Montos íntegros de destino, perfiles finales')
        profile_amounts=[]
        for dim in PROFILE_DIMENSIONS:
            for group,q in money_people.groupby(dim+'_a',observed=True):
                for pattern,part in q.groupby('patron',observed=True):
                    profile_amounts.append(dict(dimension=dim,grupo=str(group),patron=str(pattern),
                        nominal=summarize(part['monto_completo_'+via+'_b']),
                        real=summarize(part['monto_completo_'+via+'_b']*part.factor_b)))
        changes_by_profile=[]
        for dim in PROFILE_DIMENSIONS:
            for group,q in paired.groupby(dim+'_a',observed=True):
                changes_by_profile.append(dict(dimension=dim,grupo=str(group),**paired_summary(q,via)))
        mix=[]
        for label,mask in [('Nuevos y continuos',money_people.patron.isin(['No→Sí','Sí→Sí'])),
                           ('Solo continuos',money_people.patron.eq('Sí→Sí'))]:
            q=money_people.loc[mask]
            mix.append(dict(poblacion=label,N=len(q),
                nominal=summarize(q['monto_completo_'+via+'_b']),
                real=summarize(q['monto_completo_'+via+'_b']*q.factor_b)))
        institutional=[]
        if via=='K':
            for pattern,q in money_people.groupby('patron',observed=True):
                for flag,label in [('evidencia_programa','Programa público agrupado código8'),
                                   ('evidencia_seguridad','IMSS/ISSSTE identificada')]:
                    subset=q.loc[q[flag+'_K_b'].eq(True)]
                    institutional.append(dict(patron=str(pattern),evidencia=label,N_receptores_grupo=len(q),
                        N_con_evidencia=len(subset),pct_grupo=pct(len(subset),len(q)),
                        nominal_personal=summarize(subset.monto_completo_K_b),
                        real_personal=summarize(subset.monto_completo_K_b*subset.factor_b)))
        old_pairs=next(x for x in previous['seleccion'] if (x['origen'],x['destino'],x['via'],x['dimension'])==(a,b,via,'General'))
        new_people=p.loc[p.patron.eq('No→Sí')]
        other_gate=GATES['A' if via=='K' else 'K']+'_a'
        other_counts=dict(N_nuevos=len(new_people),
            N_otra_via_basal_si=int(new_people[other_gate].eq(True).sum()),
            N_otra_via_basal_no=int(new_people[other_gate].eq(False).sum()),
            N_otra_via_basal_ND=int(new_people[other_gate].isna().sum()))
        assert sum(v for k,v in other_counts.items() if k!='N_nuevos')==len(new_people)
        details.append(dict(origen=a,destino=b,via=via,montos_grupos=summaries,pares=paired_summary(paired,via),
            perfiles=profiles_all+profiles_money, montos_por_perfil=profile_amounts,
            cambios_por_perfil=changes_by_profile,mezcla_observada=mix,evidencia_institucional=institutional,
            otra_via_previa=other_counts,
            ajuste=standardize(p,via),ajuste_localidad_sensibilidad=standardize(p,via,locality=True),
            sensibilidades=sensitivities,transversal=annual,perfiles_transversales06_07=annual_profiles,
            composicion_destino=destination_partition(f,p,a,b,via),
            seleccion=selection(p,f,a,b,via),
            previo07_pares=dict(N=old_pairs['N_receptores_ambas_monto'],
                cambio_nominal=old_pairs['cambio_nominal_receptores_ambas'],cambio_real=old_pairs['cambio_real_receptores_ambas']),
            N_pares_edad_final_menor60=int(p.loc[p.patron.isin(PATTERNS),'edad_b'].lt(60).sum())))
    result=dict(pregunta=QUESTION,notebook=NOTEBOOK,referencia=REFERENCE,inpc_referencia=REFERENCE_INDEX,
        auditoria=audited,transiciones=transitions,analisis=details,
        metodologia=dict(principal='Cohorte basal directa60+, sin exigir panel balanceado. Destino directo para principal.',
            monto='Suma íntegra únicamente de eventos captados. Si alguno tiene montoND, se excluye la suma; no se completa con0.',
            continuidad='Recepción declarada en ambas visitas, no continuidad ininterrumpida ni identidad administrativa del beneficio.',
            A='Donativos propios generales dinero/especie. No programaA5 longitudinal.',
            pesos='Descriptivo no ponderado; estandarización de composición no usa pesos de encuesta.',
            inferencia='Sin valoresp, IC de diseño, modelos causales, imputación ni modelos de supervivencia.',
            limites='Rupturas de medición, soporte, montos omitidos no captados y selección impiden descomposición causal única.'))
    validate(result)
    return result


def validate(r: dict[str, Any]) -> None:
    """Cardinalidad, particiones, soporte y cuantiles monetarios sin datos privados."""
    assert r['referencia']==REFERENCE and r['inpc_referencia']==REFERENCE_INDEX
    for z in r['transiciones']:
        assert sum(s['N'] for s in z['estados'])==z['N_cohorte']
        assert sum(s['N'] for s in z['estados'] if s['estado'] in PATTERNS)==z['N_pares_conocidos']
        assert z['N_basal_si']+z['N_basal_no']+z['N_basal_ND']==z['N_cohorte']
    for z in r['analisis']:
        p=z['pares'];n=p['N']
        assert p['N_real_baja']+p['N_real_sube']+p['N_real_igual']==n
        assert p['cambio_individual_real']['N']==n<=z['previo07_pares']['N']
        assert np.isclose(p['diferencia_medianas_real'],p['puente_medianas']['termino_precio']+p['puente_medianas']['termino_nominal'])
        assert np.isclose(p['identidad_contable']['media_cambio'],p['identidad_contable']['suma_medias'])
        for m in z['montos_grupos']:
            assert m['N_monto_nominal']+m['N_sin_monto_integro']==m['N_receptores']
            assert m['N_monto_real']+m['N_precio_ND']==m['N_monto_nominal']
        for adjustment in [z['ajuste'],z['ajuste_localidad_sensibilidad']]:
            for row in adjustment['estratos']:
                if row['usado']:assert min(row['N_nuevos'],row['N_continuos'])>=20
            if adjustment['viable']:
                assert all(x>=70 for x in adjustment['pct_en_soporte'].values())
                assert np.isclose(sum(x['peso_objetivo'] for x in adjustment['estratos']),1)
        for v in z['transversal']:
            assert v['nominal_integro']['N']<=v['N_monto_parcial07']
        assert sum(s['N_basal'] for s in z['seleccion'])==next(t['N_cohorte'] for t in r['transiciones'] if (t['origen'],t['destino'],t['via'])==(z['origen'],z['destino'],z['via']))


# Validación de precisión autorizada después de la auditoría10.6.
# Las funciones08 anteriores y sus resultados guardados se mantienen intactos.
def frequency_quantiles(
    values: np.ndarray, weights: np.ndarray, *, inverse_cdf: bool = False,
) -> np.ndarray:
    """Q25/mediana/Q75 de réplicas sin expandir registros ni romper sus IDs.

    Los pesos enteros representan multiplicidades del bootstrap. La convención
    usual reproduce numpy.quantile(type7), incluida la mediana de N par. Para
    estandarización se usa el inverso de CDF de08, con pesos positivos reales.
    Réplicas sin observaciones válidas devuelven NaN y se contabilizan aparte.
    """
    v = np.asarray(values, dtype=float)
    w = np.atleast_2d(np.asarray(weights, dtype=float))
    if v.ndim != 1 or w.shape[1] != len(v):
        raise ValueError("Valores y multiplicidades no alineados")
    if not np.isfinite(v).all() or not np.isfinite(w).all() or (w < 0).any():
        raise ValueError("Solo valores finitos y pesos no negativos")
    if not inverse_cdf and not np.allclose(w, np.rint(w)):
        raise ValueError("La convención usual exige multiplicidades enteras")
    if not len(v):
        return np.full((len(w), 3), np.nan)
    order = np.argsort(v, kind="stable")
    v = v[order]
    cdf = np.cumsum(w[:, order], axis=1)
    total = cdf[:, -1]
    out = np.empty((len(w), 3))
    for j, prob in enumerate((.25, .5, .75)):
        if inverse_cdf:
            rank = prob * total
            # Una suma flotante puede quedar unas ulps por debajo del punto de
            # corte exacto; tolerancia numérica, sin cambiar valores ni empates.
            tolerance=1e-12*np.maximum(total,1)
            index = (cdf+tolerance[:,None] >= rank[:, None]).argmax(axis=1)
            out[:, j] = v[index]
        else:
            position = prob * np.maximum(total - 1, 0)
            lo = np.floor(position) + 1
            hi = np.ceil(position) + 1
            low_index = (cdf >= lo[:, None]).argmax(axis=1)
            high_index = (cdf >= hi[:, None]).argmax(axis=1)
            fraction = position - np.floor(position)
            out[:, j] = (1-fraction)*v[low_index] + fraction*v[high_index]
    out[total == 0] = np.nan
    return out


def median_order_interval(values: np.ndarray, confidence: float = .95) -> dict[str, Any]:
    """Intervalo bilateral por rangos binomiales para una mediana distributiva.

    No asume densidad continua; con empates la cobertura puede ser conservadora.
    Exige personas independientes: es comprobación del bootstrap por persona,
    no intervalo de diseño ni del bootstrap por folio. N pequeños pueden exigir
    límites abiertos; no se sustituyen por extremos de la muestra.
    """
    from scipy.stats import binom

    if not 0 < confidence < 1:
        raise ValueError("Nivel de confianza fuera de (0,1)")
    v = np.sort(np.asarray(values, dtype=float))
    if not len(v) or not np.isfinite(v).all():
        raise ValueError("Mediana exige observaciones finitas")
    size = len(v)
    tail = (1-confidence)/2
    rank = int(binom.ppf(tail, size, .5))
    while binom.cdf(rank, size, .5) <= tail:
        rank += 1
    return dict(N=size, confianza=confidence, rango_inferior=rank,
                rango_superior=size-rank+1,
                inferior=float(v[rank-1]) if rank else None,
                superior=float(v[size-rank]) if rank else None,
                cobertura_minima_binomial=float(1-2*binom.cdf(rank-1,size,.5)),
                supuesto="Personas independientes; no diseño nacional")


def missing_median_bounds(
    values: np.ndarray, missing: int, *, nonnegative: bool = False,
) -> dict[str, Any]:
    """Cotas externas de la mediana entre respuestas conocidas, sin imputar.

    Solo se alteran posiciones teóricas de los estadísticos de orden. Importes
    faltantes se permiten en [0,+inf); cambios individuales en (-inf,+inf).
    No se asigna un monto a ninguna persona, ni se incluyen muertos/ausentes.
    None indica límite abierto, no un máximo monetario supuesto.
    """
    v=np.sort(np.asarray(values,dtype=float))
    if missing<0 or not len(v) or not np.isfinite(v).all():
        raise ValueError("Valores/cantidad de faltantes inválidos")
    if nonnegative and (v<0).any():
        raise ValueError("Importe no negativo requerido")
    total=len(v)+missing
    ranks=[(total-1)//2,total//2]
    lows=[float(v[r-missing]) if r>=missing else (0. if nonnegative else None) for r in ranks]
    highs=[float(v[r]) if r<len(v) else None for r in ranks]
    return dict(N_validos=len(v),N_faltantes=missing,N_recepcion=total,
                inferior=float(np.mean(lows)) if all(x is not None for x in lows) else None,
                superior=float(np.mean(highs)) if all(x is not None for x in highs) else None,
                supuesto='Importes≥0 sin máximo supuesto' if nonnegative else 'Cambios reales sin cotas supuestas',
                interpretacion='Cotas de faltantes entre respuestas de recepción conocidas; no IC, imputación ni corrección de selección')


def _precision_pool(values: np.ndarray, mask: np.ndarray) -> dict[str, Any]:
    """Prepara posiciones válidas sin convertir ND en importe cero."""
    values = np.asarray(values, dtype=float)
    positions = np.flatnonzero(np.asarray(mask, dtype=bool) & np.isfinite(values))
    v = values[positions]
    if not len(v):
        raise ValueError("Subgrupo sin observaciones válidas")
    unique, counts = np.unique(v, return_counts=True)
    median = float(np.median(v))
    mode = int(counts.argmax())
    return dict(positions=positions, values=v, diagnostics=dict(
        N=len(v), valores_distintos=len(unique), mediana=median,
        q25=float(np.quantile(v,.25)), q75=float(np.quantile(v,.75)),
        N_igual_mediana=int(np.isclose(v,median,rtol=0,atol=1e-8).sum()),
        moda=float(unique[mode]), N_moda=int(counts[mode]),
        pct_moda=100*float(counts[mode])/len(v),
        pct_menor_mediana=100*float((v < median-1e-8).sum())/len(v),
        pct_menor_igual_mediana=100*float((v <= median+1e-8).sum())/len(v)))


def _precision_adjustment(p: pd.DataFrame, via: str) -> dict[str, Any]:
    """Fija soporte08; reestima mezcla basal en cada réplica, sin IPW."""
    original = standardize(p,via)
    if not original['viable']:
        raise ValueError("No hay soporte de composición original viable")
    school = np.where(p.educacion_a.between(0,5),'0–5',
                      np.where(p.educacion_a.ge(6),'6+','Desconocido'))
    strata = p.sexo_grupo_a.astype(str)+' / '+p.edad_06_a.astype(str)+' / '+school
    supported = [x['estrato'] for x in original['estratos'] if x['usado']]
    code = strata.map({s:i for i,s in enumerate(supported)})
    amount = p['monto_completo_'+via+'_b'].to_numpy(float)
    factor = p.factor_b.to_numpy(float)
    valid = code.notna().to_numpy() & np.isfinite(amount) & np.isfinite(factor)
    parts = {}
    for label,name in [('No→Sí','new'),('Sí→Sí','cont')]:
        positions = np.flatnonzero(valid & p.patron.eq(label).to_numpy())
        parts[name] = dict(positions=positions, strata=code.iloc[positions].to_numpy(int),
                          nominal=amount[positions], real=(amount*factor)[positions])
        assert len(positions)==original['N_en_soporte'][label]
    return dict(parts=parts, N_strata=len(supported), original=original)


def precision_bootstrap(
    frame: pd.DataFrame, pools: dict[str, dict[str, Any]],
    recipes: list[dict[str, Any]], *, adjustment: dict[str, Any] | None = None,
    cluster: str = "persona", replicas: int = 9999, seed: int = 20261014,
) -> dict[str, Any]:
    """Bootstrap no paramétrico de IDs/folios completos, con IC percentiles.

    Un solo vector de multiplicidades gobierna todos los contrastes, visitas y
    subgrupos solapados. El soporte ajustado se fija en el original; se reestima
    su mezcla de composición. Sin ruido añadido a montos, sin imputación, pesos
    de encuesta, balanceo, causalidad ni sustitución de ausentes/fallecidos.
    """
    if replicas < 99:
        raise ValueError("Se requieren al menos99 réplicas")
    if cluster not in ('persona','folio'):
        raise ValueError("Agrupación no reconocida")
    ids = pd.Series(frame.index.astype(str))
    if cluster == 'persona':
        labels = ids
    else:
        labels = frame['folio_precision'].reset_index(drop=True)
        if labels.isna().any():
            raise ValueError("Folio faltante; no se inventa agrupación")
    codes, unique = pd.factorize(labels, sort=True)
    size = len(unique)
    if size < 2:
        raise ValueError("No hay unidades independientes suficientes")
    original_weights = np.ones((1,len(frame)))
    draws = {z['id']:[] for z in recipes}
    support_bad, support_empty = 0, 0

    def evaluate(weights: np.ndarray) -> dict[str, np.ndarray]:
        nonlocal support_bad, support_empty
        quantiles, means = {}, {}
        for key,pool in pools.items():
            w = weights[:,pool['positions']]
            quantiles[key] = frequency_quantiles(pool['values'],w)
            total = w.sum(axis=1)
            means[key] = np.divide(w@pool['values'],total,
                                  out=np.full(len(w),np.nan),where=total>0)
        if adjustment is not None:
            parts=adjustment['parts']; cells=adjustment['N_strata']; counts={}
            raw={}
            for group,part in parts.items():
                raw[group]=weights[:,part['positions']]
                counts[group]=np.column_stack([raw[group][:,part['strata']==c].sum(axis=1) for c in range(cells)])
            support_bad += int(((counts['new']<20)|(counts['cont']<20)).any(axis=1).sum())
            empty=((counts['new']==0)|(counts['cont']==0)).any(axis=1)
            support_empty += int(empty.sum())
            target=counts['new']+counts['cont']
            target=np.divide(target,target.sum(axis=1)[:,None],
                             out=np.zeros_like(target),where=target.sum(axis=1)[:,None]>0)
            for group,part in parts.items():
                numerator=target[:,part['strata']]
                denominator=counts[group][:,part['strata']]
                reweight=np.divide(numerator,denominator,out=np.zeros_like(numerator),where=denominator>0)
                w=raw[group]*reweight
                for unit in ('nominal','real'):
                    key='std_'+group+'_'+unit
                    quantiles[key]=frequency_quantiles(part[unit],w,inverse_cdf=True)
                    quantiles[key][empty]=np.nan
        results={}
        for z in recipes:
            if z['op']=='quantile':
                value=quantiles[z['left']][:,z.get('q',1)]
            elif z['op']=='quantile_diff':
                value=quantiles[z['left']][:,z.get('q',1)]-quantiles[z['right']][:,z.get('q',1)]
            elif z['op']=='mean':
                value=means[z['left']]
            elif z['op']=='mean_diff':
                value=means[z['left']]-means[z['right']]
            elif z['op']=='difference':
                value=results[z['left']]-results[z['right']]
            else:
                raise ValueError("Estadístico no reconocido")
            results[z['id']]=value*z.get('scale',1.)
        return results

    points=evaluate(original_weights)
    support_bad=support_empty=0
    rng=np.random.default_rng(seed)
    for start in range(0,replicas,48):
        count=min(48,replicas-start)
        multiplicities=rng.multinomial(size,np.full(size,1/size),size=count)
        weights=multiplicities[:,codes].astype(float)
        for key,value in evaluate(weights).items():
            draws[key].append(value)
    out=[]
    for z in recipes:
        values=np.concatenate(draws[z['id']]); finite=values[np.isfinite(values)]
        if len(finite)<.99*replicas:
            raise ValueError("Demasiadas réplicas no estimables")
        lower,upper=np.quantile(finite,[.025,.975])
        halves=[v[np.isfinite(v)] for v in np.array_split(values,2)]
        splits=[np.quantile(v,[.025,.975]).tolist() for v in halves]
        result={**z,'estimacion':float(points[z['id']][0]),
                'ic95':[float(lower),float(upper)],'replicas_validas':len(finite),
                'replicas_fallidas':replicas-len(finite),'valores_bootstrap_distintos':len(np.unique(finite)),
                'pct_replicas_igual_estimacion':100*float(np.isclose(finite,points[z['id']][0],rtol=0,atol=1e-8).sum())/len(finite),
                'ic95_mitades_MC':splits,'ic_colapsado':bool(np.isclose(lower,upper,rtol=0,atol=1e-8))}
        if cluster=='persona' and z['op'] in ('quantile','quantile_diff') and z.get('q',1)==1 and not z['left'].startswith('std_'):
            if z['op']=='quantile':
                result['comprobacion_orden']=median_order_interval(pools[z['left']]['values'])
            else:
                first=median_order_interval(pools[z['left']]['values'],.975)
                second=median_order_interval(pools[z['right']]['values'],.975)
                result['comprobacion_orden']=dict(metodo='Dos medianas97.5%, contraste Bonferroni≥95%',
                    inferior=first['inferior']-second['superior'] if first['inferior'] is not None and second['superior'] is not None else None,
                    superior=first['superior']-second['inferior'] if first['superior'] is not None and second['inferior'] is not None else None,
                    grupo=first,referencia=second)
        out.append(result)
    return dict(agrupacion=cluster,N_filas=len(frame),N_personas=ids.nunique(),N_clusters=size,
                max_filas_cluster=int(np.bincount(codes).max()),replicas=replicas,semilla=seed,
                estimaciones=out,distribuciones={k:v['diagnostics'] for k,v in pools.items()},
                ajuste_diagnostico=dict(soporte_original_fijo=True,
                    mezcla_objetivo_reestimada=True,N_estratos=adjustment['N_strata'],
                    pct_replicas_alguna_celda_menor20=100*support_bad/replicas,
                    N_replicas_celda_vacia=support_empty) if adjustment else None)


def analyze_precision(*, replicas: int = 9999, seed: int = 20261014) -> dict[str, Any]:
    """Contrastes seleccionados06–08, sin sobrescribir sus productos previos."""
    f,_=load_inputs()
    previous=json.loads((OUTPUT/'resultados.json').read_text())
    analyses=[]

    def recipe(key: str, op: str, left: str, right: str | None = None,
               **metadata: Any) -> dict[str, Any]:
        return dict(id=key,op=op,left=left,**({'right':right} if right else {}),**metadata)

    for ordinal,(a,b,via) in enumerate(FOCUS):
        p=pair_frame(f,a,b);p['patron']=classify(p,via)
        p['folio_precision']=p.cunicah_a
        pools={}; recipes=[]; missing=[]
        amount=p['monto_completo_'+via+'_b'].to_numpy(float)
        factor=p.factor_b.to_numpy(float)
        complete=np.isfinite(amount)&np.isfinite(factor)
        for label,name in [('No→Sí','new'),('Sí→Sí','cont')]:
            mask=p.patron.eq(label).to_numpy()
            missing.append(dict(grupo=label,N_recepcion=int(mask.sum()),
                N_monto_valido=int((mask&complete).sum()),N_sin_monto=int((mask&~complete).sum()),
                cotas_nominales=missing_median_bounds(amount[mask&complete],int((mask&~complete).sum()),nonnegative=True),
                cotas_reales=missing_median_bounds((amount*factor)[mask&complete],int((mask&~complete).sum()),nonnegative=True)))
            for unit,value in [('nominal',amount),('real',amount*factor)]:
                pools[name+'_'+unit]=_precision_pool(value,mask&complete)
        for unit in ('nominal','real'):
            recipes.append(recipe('new_minus_cont_'+unit,'quantile_diff','new_'+unit,'cont_'+unit,
                unidad='pesos/mes '+unit,descripcion='Mediana nuevos menos continuos',
                N_grupo=pools['new_'+unit]['diagnostics']['N'],N_referencia=pools['cont_'+unit]['diagnostics']['N']))
            recipes.append(recipe('adjusted_new_minus_cont_'+unit,'quantile_diff','std_new_'+unit,'std_cont_'+unit,
                unidad='pesos/mes '+unit,descripcion='Medianas CDF en mezcla basal común; soporte fijo'))
        for index,label in [(0,'q25'),(2,'q75')]:
            recipes.append(recipe('new_minus_cont_real_'+label,'quantile_diff','new_real','cont_real',q=index,
                                  unidad='pesos reales/mes',descripcion=label+' nuevos menos continuos'))
        basal=p['monto_completo_'+via+'_a'].to_numpy(float)
        paired=p.patron.eq('Sí→Sí').to_numpy()&complete&np.isfinite(basal)&p.factor_a.notna().to_numpy()
        for criterion,fa,fb in [('principal','factor_a','factor_b'),('12m','factor_12m_a','factor_12m_b'),
                              ('ano_entrevista','factor_ano_entrevista_a','factor_ano_entrevista_b')]:
            delta=amount*p[fb].to_numpy(float)-basal*p[fa].to_numpy(float)
            pools['change_'+criterion]=_precision_pool(delta,paired)
            recipes.append(recipe('median_change_'+criterion,'quantile','change_'+criterion,
                unidad='pesos reales/mes',descripcion='Mediana de cambios individuales: '+criterion,
                N_grupo=int(paired.sum())))
        delta=amount*factor-basal*p.factor_a.to_numpy(float)
        bounds_change=missing_median_bounds(delta[paired],int(p.patron.eq('Sí→Sí').sum())-int(paired.sum()))
        pools['negative_change']=_precision_pool((delta < -1e-9).astype(float),paired)
        recipes.append(recipe('negative_change_pct','mean','negative_change',scale=100,
                              unidad='%',descripcion='Fracción de cambios reales negativos',N_grupo=int(paired.sum())))
        if via=='K':
            evidence=p.evidencia_seguridad_K_b.eq(True).to_numpy()
            for label,name in [('No→Sí','new'),('Sí→Sí','cont')]:
                for unit,value in [('nominal',amount),('real',amount*factor)]:
                    pools['ss_'+name+'_'+unit]=_precision_pool(value,p.patron.eq(label).to_numpy()&complete&evidence)
            for unit in ('nominal','real'):
                recipes.append(recipe('ss_new_minus_cont_'+unit,'quantile_diff','ss_new_'+unit,'ss_cont_'+unit,
                    unidad='pesos/mes '+unit,descripcion='Nuevos menos continuos con evidencia IMSS/ISSSTE',
                    N_grupo=pools['ss_new_'+unit]['diagnostics']['N'],N_referencia=pools['ss_cont_'+unit]['diagnostics']['N']))
                recipes.append(recipe('total_minus_ss_contrast_'+unit,'difference','new_minus_cont_'+unit,'ss_new_minus_cont_'+unit,
                    unidad='pesos/mes '+unit,descripcion='Contraste total menos contraste subgrupo solapado'))
            stable=paired & p.N_eventos_K_a.eq(1).to_numpy() & p.N_eventos_K_b.eq(1).to_numpy()
            stable &= p.firma_seguridad_K_a.notna().to_numpy() & p.firma_seguridad_K_a.eq(p.firma_seguridad_K_b).to_numpy()
            pools['change_stable_ss']=_precision_pool(delta,stable)
            recipes.append(recipe('median_change_stable_ss','quantile','change_stable_ss',
                unidad='pesos reales/mes',descripcion='Cambio individual, un evento de misma contingencia/institución IMSS/ISSSTE',N_grupo=int(stable.sum())))
        adjustment=_precision_adjustment(p,via)
        result=precision_bootstrap(p,pools,recipes,adjustment=adjustment,replicas=replicas,seed=seed+ordinal)
        sensitivity=precision_bootstrap(p,pools,recipes,adjustment=adjustment,cluster='folio',replicas=replicas,seed=seed+100+ordinal)
        old=next(x for x in previous['analisis'] if x['via']==via)
        assert int(paired.sum())==old['pares']['N']
        for pattern,name in [('No→Sí','new'),('Sí→Sí','cont')]:
            saved=next(x for x in old['montos_grupos'] if x['patron']==pattern)
            for unit in ('nominal','real'):
                assert pools[name+'_'+unit]['diagnostics']['N']==saved['N_monto_real']
                assert np.isclose(pools[name+'_'+unit]['diagnostics']['mediana'],saved[unit]['mediana'])
        estimate={x['id']:x for x in result['estimaciones']}
        assert np.isclose(estimate['median_change_principal']['estimacion'],old['pares']['cambio_individual_real']['mediana'])
        for unit in ('nominal','real'):
            adjusted={x['grupo']:x['ajustado_CDF']['mediana'] for x in old['ajuste']['distribuciones'] if x['unidad']==unit}
            assert np.isclose(estimate['adjusted_new_minus_cont_'+unit]['estimacion'],adjusted['No→Sí']-adjusted['Sí→Sí'])
        analyses.append(dict(via=via,origen=a,destino=b,faltantes=missing,
            cotas_cambio_individual=bounds_change,
            N_basal=len(p),N_pares_conocidos=int(p.patron.isin(PATTERNS).sum()),
            soporte_ajuste=adjustment['original'],principal=result,sensibilidad_folio=sensitivity))

    # Cortes dinámicos por visita: remuestreo conjunto de cada ID, no rondas independientes.
    q=f.loc[f.ano.isin([2012,2015])&f.universo_60&f.directa].copy().set_index('id')
    q['folio_precision']=q.cunicah
    from .economic_protection import union_receipt
    q['union_precision']=union_receipt(q.pension_propia_k,q.apoyo_propio)
    pools={}; recipes=[]; denominators=[]
    for year in (2012,2015):
        for via,gate in [('K','pension_propia_k'),('KA','union_precision')]:
            for label,name in [('Hombre','men'),('Mujer','women')]:
                mask=(q.ano.eq(year)&q.sexo_grupo.eq(label)&q[gate].notna()).to_numpy()
                key=f'{via}_{year}_{name}'
                pools[key]=_precision_pool(q[gate].fillna(False).to_numpy(float),mask)
            recipes.append(recipe(f'gap_{via}_{year}','mean_diff',f'{via}_{year}_men',f'{via}_{year}_women',
                scale=100,unidad='pp',descripcion=f'Cobertura {via} Hombre menos Mujer, {year}'))
        for kind,column in [('partial','monto_k_propio_mensual_observado_parcial'),('complete','monto_completo_K')]:
            for label,name in [('Hombre','men'),('Mujer','women')]:
                eligible=q.ano.eq(year)&q.sexo_grupo.eq(label)&q.pension_propia_k.eq(True).fillna(False)
                values=q[column].to_numpy(float);valid=eligible.to_numpy()&np.isfinite(values)&q.factor.notna().to_numpy()
                denominators.append(dict(ronda=year,sexo=label,criterio=kind,N_recepcion=int(eligible.sum()),N_monto=int(valid.sum()),N_sin_monto=int((eligible.to_numpy()&~valid).sum())))
                for unit,value in [('nominal',values),('real',values*q.factor.to_numpy(float))]:
                    pools[f'money_{kind}_{year}_{name}_{unit}']=_precision_pool(value,valid)
            for unit in ('nominal','real'):
                recipes.append(recipe(f'gap_money_{kind}_{year}_{unit}','quantile_diff',f'money_{kind}_{year}_men_{unit}',f'money_{kind}_{year}_women_{unit}',
                    unidad='pesos/mes '+unit,descripcion=f'Brecha mediana K Hombre menos Mujer, {year}; {kind}'))
    for via in ('K','KA'):
        recipes.append(recipe('change_gap_'+via,'difference','gap_'+via+'_2015','gap_'+via+'_2012',unidad='pp',descripcion='Cambio de brecha de cobertura por sexo2012–2015'))
    for kind in ('partial','complete'):
        for unit in ('nominal','real'):
            recipes.append(recipe(f'change_gap_money_{kind}_{unit}','difference',f'gap_money_{kind}_2015_{unit}',f'gap_money_{kind}_2012_{unit}',unidad='pesos/mes '+unit,descripcion='Cambio de brecha mediana K por sexo2012–2015'))
    sex=precision_bootstrap(q,pools,recipes,replicas=replicas,seed=seed+2)
    sex_folio=precision_bootstrap(q,pools,recipes,cluster='folio',replicas=replicas,seed=seed+102)
    synthesis=json.loads((INTERIM_DIR/'sintesis_proteccion_economica/resultados.json').read_text())
    original=next(x for x in synthesis['brechas_por_perfil'] if (x['origen'],x['destino'],x['via_cobertura'],x['dimension'])==(2012,2015,'KA','sexo_grupo'))
    estimates={x['id']:x['estimacion'] for x in sex['estimaciones']}
    assert np.isclose(estimates['gap_KA_2012'],original['brecha_cobertura']['inicial'])
    assert np.isclose(estimates['gap_KA_2015'],original['brecha_cobertura']['final'])
    assert np.isclose(estimates['gap_money_partial_2012_real'],original['K']['brecha_real_inicial'])
    assert np.isclose(estimates['gap_money_partial_2015_real'],original['K']['brecha_real_final'])
    return dict(pregunta=QUESTION,referencia=REFERENCE,inpc_referencia=REFERENCE_INDEX,
        metodologia=dict(replicas=replicas,semilla_base=seed,IC='Percentil bilateral95%, bootstrap no paramétrico de clusters',
            principal='Persona/ID; todas sus visitas y subgrupos usan la misma multiplicidad',
            folio='Sensibilidad por cunicah compartido; no hogar actual, UPM ni diseño nacional validado',
            orden='Comprobación binomial de medianas y Bonferroni para diferencias; independencia entre personas',
            ajuste='Soporte08 fijo; mezcla objetivo reestimada por réplica; no IPW',
            poblacion='Directas60+; cohortes para incorporación/cambio, cortes por visita para brechas',
            limites='IC condicionales a observados/medición; no incertidumbre de precios oficiales, error de declaración, selección ignorada o diseño nacional',
            multiplicidad='Contrastes priorizados por pregunta; IC puntuales, no simultáneos entre todos los contrastes',
            empates='No jitter, suavizado o eliminación automática; se reporta masa y colapso del IC'),
        ventanas=analyses,sexo2012_2015=dict(denominadores_monto=denominators,principal=sex,sensibilidad_folio=sex_folio),
        reproduccion='Puntos y N reconciliados con06–08; agregados/notebooks originales no sobrescritos')


def validate_precision(result: dict[str, Any]) -> None:
    """Coteja intervalos, estados, faltantes y coherencia de población/medición."""
    assert result['referencia']==REFERENCE and result['inpc_referencia']==REFERENCE_INDEX
    assert [(x['origen'],x['destino'],x['via']) for x in result['ventanas']]==list(FOCUS)
    for window in result['ventanas']:
        for x in window['faltantes']:
            assert x['N_monto_valido']+x['N_sin_monto']==x['N_recepcion']
            assert x['cotas_reales']['N_recepcion']==x['N_recepcion']
        assert window['cotas_cambio_individual']['N_validos']==(1756 if window['via']=='K' else 1223)
    groups=result['ventanas']+[result['sexo2012_2015']]
    for group in groups:
        for name in ('principal','sensibilidad_folio'):
            part=group[name]
            assert part['N_clusters']<=part['N_personas']<=part['N_filas']
            assert part['agrupacion']==('persona' if name=='principal' else 'folio')
            assert len({x['id'] for x in part['estimaciones']})==len(part['estimaciones'])
            for x in part['estimaciones']:
                assert np.isfinite(x['estimacion']) and np.isfinite(x['ic95']).all()
                assert x['ic95'][0]<=x['ic95'][1]
                assert x['replicas_validas']+x['replicas_fallidas']==part['replicas']
            if part['ajuste_diagnostico']:
                assert part['ajuste_diagnostico']['soporte_original_fijo']
                assert part['ajuste_diagnostico']['N_replicas_celda_vacia']==0
