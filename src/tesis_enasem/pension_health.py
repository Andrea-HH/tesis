"""Contrastes descriptivos pensionarios de salud: contratos, tamaños de efecto y cobertura."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from statsmodels.stats.proportion import confint_proportions_2indep

from .independent_eda import VariableSpec, validate_values
from .integration import restore_stata, person_id
from .pension_exploration import PopulationSpec, ownership_category
from .project_paths import PROJECT_ROOT, INTERIM_DIR, PROCESSED_DIR, project_path

YEARS = (2001,2003,2012,2015,2018,2021)
DIMENSIONS = {'Física':('salud_glob','diabetes','n_enf','bmi_imp'),
              'Mental':('n_sint_depr','cesd_deprimido','solo'),
              'Cognición':('recuerdo1','recuerdo2','orientacion','serial7','tics'),
              'Funcionalidad':('n_abvd','n_aivd','n_mov')}
BINARY = {'diabetes','cesd_deprimido','solo'}
TRIVARIATES = (('n_sint_depr','sexo_grupo'),('salud_glob','edad_salud'),
               ('recuerdo1','educacion_grupo'),('recuerdo2','educacion_grupo'),
               ('n_aivd','edad_salud'),('n_mov','edad_salud'),
               ('n_enf','sexo_grupo'),('diabetes','sexo_grupo'),
               ('recuerdo1','patrimonio_cuartil'),('n_sint_depr','localidad_grupo'))
OUTPUT = INTERIM_DIR/'pensiones_salud'


def read_json(path: str | Path) -> Any:
    """Lee una entrada existente mediante las rutas únicas del proyecto."""
    return json.loads(project_path(path).read_text())


def contracts() -> tuple[dict[str,VariableSpec],dict,dict]:
    """Recupera dominio, universo del indicador y metadatos; no inventa elegibilidad."""
    specs={s['variable']:VariableSpec(**s) for s in read_json('diccionarios/contratos_enasemsimple.json')['contratos']}
    universes=read_json('diccionarios/universos_enasemsimple.json')['reglas']
    metadata={r['columna']:r for r in read_json('docs/integracion/diccionario_columnas.json')}
    return specs,universes,metadata


def load_population() -> tuple[pd.DataFrame,dict[str,VariableSpec],dict,list[dict]]:
    """Usa el sidecar validado y un lookup 1:1 del maestro; ninguna base se reescribe."""
    specs,universes,metadata=contracts()
    names=[v for values in DIMENSIONS.values() for v in values]
    usable=[v for v in names if v in specs and v in universes and v in metadata]
    fields=['imp_neto',*usable]
    tags=[metadata[v]['campo_tag'] for v in fields if metadata[v].get('campo_tag')]
    master=pd.read_parquet(PROCESSED_DIR/'enasem_integrada_provisional.parquet',columns=['id','ronda',*fields,*tags])
    people=pd.read_parquet(PROCESSED_DIR/'armonizacion_economica_v1/personas_ronda.parquet')
    if len(people)!=99676 or people.id.nunique()!=27171 or people[['id','ronda']].duplicated().any():
        raise ValueError('Maestro o claves alterados')
    if not people.id.equals(person_id(people)):raise ValueError('Formato del ID alterado')
    frame=people.merge(master,on=['id','ronda'],how='left',validate='one_to_one',indicator=True)
    if len(frame)!=99676 or not frame._merge.eq('both').all():raise ValueError('Lookup incompleto o multiplicado')
    frame=PopulationSpec(minimum_age=60).select(frame.drop(columns='_merge'))
    if len(frame)!=56004 or frame.id.nunique()!=18754:raise ValueError('Selección 60+ inesperada')
    for variable in fields:
        values,states=validate_values(restore_stata(frame[variable],frame[metadata[variable]['campo_tag']]),specs[variable])
        frame[variable]=values
        frame[variable+'__estado_salud']=states
    frame['edad_salud']=pd.cut(frame.edad,[59,69,79,np.inf],labels=['60–69','70–79','80+']).astype(object).fillna('Desconocido')
    frame['educacion_ajuste']=pd.cut(frame.educacion,[-.01,5,9,np.inf],labels=['0–5','6–9','10+']).astype(object).fillna('Desconocido')
    frame['modalidad_ajuste']=frame.tipent.map({1:'Directa',2:'Directa',3:'Sustituto',4:'Sustituto'}).fillna('Desconocido')
    frame['titularidad_salud']=[ownership_category(a,b) for a,b in zip(frame.pension_propia_k,frame.pension_conyuge_k)]
    absent=frame.titularidad_pareja_estado.eq('sin_pareja_residente_explicita')
    frame.loc[absent,'titularidad_salud']='Sin pareja residente; rama propia separada'
    quartiles=[]
    frame['patrimonio_cuartil']='Desconocido'
    for year in YEARS:
        mask=frame.ano.eq(year)&frame.imp_neto.notna();values=frame.loc[mask,'imp_neto']
        cuts=values.quantile([.25,.5,.75]).to_numpy()
        if len(set(cuts))==3:
            frame.loc[mask,'patrimonio_cuartil']=pd.cut(values,[-np.inf,*cuts,np.inf],labels=['Q1','Q2','Q3','Q4'],include_lowest=True).astype(object)
        quartiles.append({'ano':year,'N_patrimonio_valido':len(values),'p25':float(cuts[0]),'p50':float(cuts[1]),'p75':float(cuts[2]),'nota':'Cuartiles relativos de patrimonio persona/cónyuge en 60+; no pobreza ni ingreso.'})
    return frame,specs,universes,quartiles


def eligible_population(frame: pd.DataFrame, variable: str, year: int, universes: dict) -> pd.DataFrame:
    """Selecciona modalidades del indicador construido, no infiere saltos de pregunta bruta."""
    rule=universes[variable][str(year)]
    if rule.get('modalidades') is None:raise ValueError(f'Elegibilidad no reconstruida: {variable}/{year}')
    return frame.loc[frame.ano.eq(year)&frame.tipent.isin(rule['modalidades'])]


def summarize(values: pd.Series) -> dict:
    """Resume valores válidos sin convertir desconocidos a cero ni borrar extremos."""
    x=values.dropna().astype(float)
    if not len(x):return {'N_valido':0,'media':None,'mediana':None,'p25':None,'p75':None,'DE':None}
    return {'N_valido':len(x),'media':float(x.mean()),'mediana':float(x.median()),
            'p25':float(x.quantile(.25)),'p75':float(x.quantile(.75)),
            'DE':float(x.std()) if len(x)>1 else None,'min':float(x.min()),'max':float(x.max())}


def rank_effect(x: np.ndarray,y: np.ndarray,replicates: int,seed: int) -> dict:
    """Delta=P(X>Y)-P(X<Y), con empates; bootstrap de personas dentro de grupo/ronda.

    El bootstrap multinomial de las frecuencias empíricas es equivalente a remuestrear
    individuos con reemplazo. No une rondas ni incorpora diseño complejo/imputación MI.
    """
    support=np.union1d(x,y)
    if len(support)==1:
        return {'efecto':0.0,'ic95_inferior':None,'ic95_superior':None,
                'medida':'Delta de Cliff','unidad_efecto':'−1 a 1',
                'nota_ic':'Ambos grupos constantes: bootstrap empírico degenerado; no afirmar precisión poblacional.'}
    a=np.bincount(np.searchsorted(support,x),minlength=len(support))
    b=np.bincount(np.searchsorted(support,y),minlength=len(support))
    def delta(left: np.ndarray,right: np.ndarray) -> np.ndarray:
        probability=(left*(np.cumsum(right,axis=-1)-.5*right)).sum(axis=-1)/(len(x)*len(y))
        return 2*probability-1
    effect=float(delta(a,b));rng=np.random.default_rng(seed);draws=[]
    for start in range(0,replicates,64):
        size=min(64,replicates-start)
        left=rng.multinomial(len(x),a/a.sum(),size=size)
        right=rng.multinomial(len(y),b/b.sum(),size=size)
        draws.extend(delta(left,right).tolist())
    low,high=np.quantile(draws,[.025,.975])
    return {'efecto':effect,'ic95_inferior':float(low),'ic95_superior':float(high),
            'medida':'Delta de Cliff','unidad_efecto':'−1 a 1','bootstrap_replicas':replicates}


def compare_groups(frame: pd.DataFrame,variable: str,receipt: str,replicates: int=999,
                   min_group: int=30,key: str='') -> dict:
    """Contrasta sí versus negativa explícita; registra ND y no calcula p-valores."""
    a=frame.loc[frame[receipt].eq(True).fillna(False),variable].dropna().to_numpy(dtype=float)
    b=frame.loc[frame[receipt].eq(False).fillna(False),variable].dropna().to_numpy(dtype=float)
    result={'N_elegible':len(frame),'N_salud_valido':int(frame[variable].notna().sum()),
            'N_salud_no_valido':int(frame[variable].isna().sum()),
            'N_recepcion_ND':int(frame[receipt].isna().sum()),'N_pares_validos':len(a)+len(b),
            'N_si_valido':len(a),'N_no_valido':len(b),'si':summarize(pd.Series(a)),
            'no':summarize(pd.Series(b)),'efecto':None,'ic95_inferior':None,'ic95_superior':None}
    if min(len(a),len(b))<min_group:
        return {**result,'estado':'No estimado: menos de 30 valores válidos en uno de los grupos'}
    if variable in BINARY:
        count1=int(a.sum());count2=int(b.sum())
        lo,hi=confint_proportions_2indep(count1,len(a),count2,len(b),method='newcomb',compare='diff')
        result.update(efecto=float(100*(a.mean()-b.mean())),ic95_inferior=float(100*lo),ic95_superior=float(100*hi),
                      medida='Diferencia de proporciones',unidad_efecto='puntos porcentuales',N_evento_si=count1,N_evento_no=count2,
                      pct_evento_si=float(100*a.mean()),pct_evento_no=float(100*b.mean()))
    else:
        seed=int(sha256((variable+'|'+receipt+'|'+key).encode()).hexdigest()[:8],16)
        result.update(rank_effect(a,b,replicates,seed))
    result['estado']='Estimado descriptivo provisional'
    return result


def group_distributions(part: pd.DataFrame,variable: str,group: str) -> list[dict]:
    """Conserva distribuciones y cobertura por grupos, incluidos los estados desconocidos."""
    rows=[]
    labels=part[group].astype(object).fillna('Desconocido').astype(str)
    for name,indices in labels.groupby(labels).groups.items():
        values=part.loc[indices,variable];counts=values.dropna().value_counts().sort_index()
        rows.append({'grupo':name,'N_elegible_grupo':len(indices),'N_no_valido':int(values.isna().sum()),
                     **summarize(values),'frecuencias':[{'valor':float(v),'N':int(n)} for v,n in counts.items()]})
    return rows


def standardize(frame: pd.DataFrame,variable: str,min_cell: int=20) -> dict:
    """Medias/proporciones descriptivas con composición común, sin modelo ni causalidad.

    Target: casos válidos en celdas sexo×edad×escolaridad×modalidad con ≥20 por rama.
    Pesos fijos de composición; IC normal condicional a celdas/valores representados.
    """
    known=frame.loc[frame[variable].notna()&frame.pension_propia_k.notna()].copy()
    fields=['sexo_grupo','edad_salud','educacion_ajuste','modalidad_ajuste']
    eligible=known.loc[~known[fields].eq('Desconocido').any(axis=1)]
    cells=[];indices=[]
    for levels,group in eligible.groupby(fields,observed=True):
        a=group.loc[group.pension_propia_k.eq(True),variable].astype(float)
        b=group.loc[group.pension_propia_k.eq(False),variable].astype(float)
        if min(len(a),len(b))<min_cell:continue
        cells.append({'estrato':dict(zip(fields,levels)),'N':len(group),'N_si':len(a),'N_no':len(b),
                      'media_si':float(a.mean()),'media_no':float(b.mean()),
                      'var_media_si':float(a.var()/len(a)),'var_media_no':float(b.var()/len(b))})
        indices.extend(group.index)
    if not cells:return {'variable':variable,'estado':'Sin soporte común suficiente','N_soporte':0}
    target=sum(c['N'] for c in cells);a=sum(c['N']/target*c['media_si'] for c in cells);b=sum(c['N']/target*c['media_no'] for c in cells)
    variance=sum((c['N']/target)**2*(c['var_media_si']+c['var_media_no']) for c in cells)
    support=known.loc[indices];raw_a=support.loc[support.pension_propia_k.eq(True),variable].mean();raw_b=support.loc[support.pension_propia_k.eq(False),variable].mean()
    multiplier=100 if variable in BINARY else 1
    return {'variable':variable,'estado':'Estandarización descriptiva en soporte común',
            'N_pares_completos':len(known),'N_soporte':target,'N_fuera_soporte':len(known)-target,'N_celdas':len(cells),
            'diferencia_cruda_mismo_soporte':float(multiplier*(raw_a-raw_b)),
            'diferencia_estandarizada':float(multiplier*(a-b)),
            'ic95_inferior':float(multiplier*(a-b-1.96*np.sqrt(variance))),
            'ic95_superior':float(multiplier*(a-b+1.96*np.sqrt(variance))),
            'unidad':'pp' if variable in BINARY else 'unidades originales',
            'celdas':cells,'nota':'IC condicional: no incertidumbre del diseño, composición estimada o imputaciones; sin control automático de sesgo.'}


def analyze(replicates: int=999) -> dict:
    """Amplía efectos y estratificaciones; reutiliza las 30 correlaciones históricas."""
    frame,specs,universes,quartiles=load_population()
    paired=frame.n_sint_depr.notna()&frame.cesd_deprimido.notna()
    discordant=int(frame.loc[paired,'cesd_deprimido'].ne(frame.loc[paired,'n_sint_depr'].ge(5).astype(int)).sum())
    if discordant:raise ValueError('Bandera CES-D y conteo incompatibles: verificar antes de incorporar resultados')
    output={'metodologia':{'poblacion':'60+ por visita; sin panel balanceado','N_persona_ronda':len(frame),
            'N_personas':frame.id.nunique(),'rondas':list(YEARS),'ponderado':False,
            'contraste':'Sí K propia menos negativa explícita K propia',
            'ic':'95% puntual, condicional a muestra y valores representados; no diseño complejo, no incertidumbre MI',
            'multiplicidad':'Exploratorio; sin p-valores ni selección por exclusión de cero; no IC simultáneos',
            'minimo_por_grupo':30,'bootstrap_principal':replicates,'bootstrap_estratos':499},
            'contratos':[],'cobertura':[],'principal':[],'complementarios':[],'titularidad':[],
            'trivariados':[],'sensibilidad_modalidad':[],'estandarizados':[],
            'cuartiles_patrimonio':quartiles,
            'calidad':{'CESD_pares_validos':int(paired.sum()),'CESD_bandera_conteo_discordantes':discordant,
                       'nota':'Cinco o más síntomas deriva del conteo; no es confirmación independiente ni diagnóstico.'},
            'reutilizados':read_json('data/interim/eda_pensionaria/salud_complementaria.json')}
    for dimension,names in DIMENSIONS.items():
        for variable in names:
            if variable not in specs or variable not in universes:
                for year in YEARS:output['cobertura'].append({'ano':year,'variable':variable,'dimension':dimension,'N_total_60':int(frame.ano.eq(year).sum()),'N_elegible':None,'estado':'No analizado: variable/contrato/eligibilidad no disponibles; no construir TICS sumando escalas'})
                continue
            spec=specs[variable]
            output['contratos'].append({**spec.__dict__,'dimension':dimension,'imputado':'imput' in spec.label.lower(),
             'nota_comparabilidad':'Comparación descriptiva condicionada a contrato del indicador; no homologación definitiva de ítems ni escala común entre pruebas cognitivas.'})
            for year in YEARS:
                total=frame.loc[frame.ano.eq(year)];part=eligible_population(frame,variable,year,universes)
                states=part[variable+'__estado_salud'];nr=states.isin(['.r','.d'])|states.str.startswith('NR/NS numérico:')
                invalid=states.eq('fuera de dominio documentado');valid=part[variable].notna()
                coverage={'ano':year,'variable':variable,'dimension':dimension,'N_total_60':len(total),
                   'N_elegible':len(part),'N_fuera_universo':len(total)-len(part),'N_valido':int(valid.sum()),
                   'N_NR_NS':int(nr.sum()),'N_fuera_dominio':int(invalid.sum()),
                   'N_otros_faltantes':int((~valid&~nr&~invalid).sum()),
                   'N_pension_ND':int(part.pension_propia_k.isna().sum()),
                   'estados_salud':{str(k):int(v) for k,v in states.value_counts().items()},
                   'nota_elegibilidad':universes[variable][str(year)]['nota'],
                   'estado':'Disponible bajo contrato' if len(part) else 'No disponible: instrumento ausente según contrato'}
                assert coverage['N_elegible']==coverage['N_valido']+coverage['N_NR_NS']+coverage['N_fuera_dominio']+coverage['N_otros_faltantes']
                output['cobertura'].append(coverage)
                if not len(part):continue
                identity={'ano':year,'variable':variable,'dimension':dimension}
                contrast=compare_groups(part,variable,'pension_propia_k',replicates,key=str(year))
                contrast['distribuciones']=group_distributions(part,variable,'pension_propia_k')
                output['principal'].append({**identity,**contrast})
                output['titularidad'].append({**identity,'distribuciones':group_distributions(part,variable,'titularidad_salud'),
                 'nota':'Sin pareja residente no es negativa individual del cónyuge. Antes de 2018 las combinaciones son estados del proveedor con universo de pareja no confirmado, no tasas elegibles. ND permanece explícito.'})
                for receipt in ['apoyo_propio','pension_conyuge_k']:
                    complement=part if receipt=='apoyo_propio' else part.loc[part.titularidad_pareja_estado.eq('puntero_pareja_concordante')]
                    if not len(complement):continue
                    output['complementarios'].append({**identity,'recepcion':receipt,**compare_groups(complement,variable,receipt,499,key=str(year)),
                       'nota':'A agrega donativos dinero/especie, no pensión no contributiva' if receipt=='apoyo_propio' else 'Solo universo confirmado de pareja en 2018/2021; no comparar directamente con universo principal'})
                if set(universes[variable][str(year)]['modalidades'])&{3,4}:
                    direct=part.loc[part.tipent.isin([1,2])]
                    output['sensibilidad_modalidad'].append({**identity,**compare_groups(direct,variable,'pension_propia_k',499,key=str(year)+'directa')})
                for variable_choice,stratifier in TRIVARIATES:
                    if variable_choice!=variable:continue
                    for level,group in part.groupby(stratifier,observed=True,dropna=False):
                        entry={**identity,'estratificador':stratifier,'estrato':str(level)}
                        if str(level)=='Desconocido':
                            # Conservar cobertura y descriptivos, pero no estimar
                            # un contraste como si el perfil estuviera observado.
                            entry.update(compare_groups(group,variable,'pension_propia_k',
                                         min_group=len(group)+1))
                            entry['estado']='No estimado: estratificador desconocido'
                        else:entry.update(compare_groups(group,variable,'pension_propia_k',499,key=str(year)+stratifier+str(level)))
                        output['trivariados'].append(entry)
                if variable in ['diabetes','n_enf','n_sint_depr','recuerdo1','n_aivd','bmi_imp']:
                    output['estandarizados'].append({'ano':year,**standardize(part,variable)})
    output['metodologia']['N_contrastes_principales']=len(output['principal'])
    output['metodologia']['N_contrastes_trivariados']=sum(x.get('efecto') is not None for x in output['trivariados'])
    return output


def verify_frozen_inputs() -> None:
    """Comprueba bases, originales, resultados previos, notebooks y manuscrito por huella."""
    manifest=json.loads((OUTPUT/'manifest.json').read_text())
    changed=[name for name,digest in manifest['archivos_protegidos'].items()
             if sha256((PROJECT_ROOT/name).read_bytes()).hexdigest()!=digest]
    changed += [name for name,digest in manifest.get('entradas_definicion',{}).items()
                if sha256((PROJECT_ROOT/name).read_bytes()).hexdigest()!=digest]
    if changed:raise ValueError(f'Entradas protegidas modificadas: {changed}')
    if sha256((PROJECT_ROOT/'.git/index').read_bytes()).hexdigest()!=manifest['indice_sha256']:
        raise ValueError('Índice cambiado durante el análisis')
