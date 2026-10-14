"""Audita cobertura longitudinal sin calcular asociaciones ni modificar bases."""
import json,hashlib
from pathlib import Path
import pandas as pd
from tesis_enasem.pension_health import contracts,YEARS
from tesis_enasem.integration import restore_stata
from tesis_enasem.independent_eda import validate_values

def main() -> None:
    """Guarda únicamente conteos agregados de viabilidad por intervalo."""
    root=Path(__file__).resolve().parents[1];
    import os
    os.chdir(root); variables=['n_sint_depr','solo','recuerdo1','recuerdo2','orientacion','serial7']
    specs,u,meta=contracts()
    a=pd.read_parquet('data/processed/armonizacion_economica_v1/personas_ronda.parquet')
    fields=['id','ronda','fallecido','mes_ent','recuerdo1_flag','recuerdo2_flag']+variables+[meta[v]['campo_tag'] for v in variables]
    b=pd.read_parquet('data/processed/enasem_integrada_provisional.parquet',columns=fields)
    f=a.merge(b,on=['id','ronda'],validate='one_to_one',how='left')
    assert len(f)==99676 and not f[['id','ronda']].duplicated().any()
    for v in variables:
     f[v],f[v+'__estado']=validate_values(restore_stata(f[v],f[meta[v]['campo_tag']]),specs[v])
     f[v+'__elegible']=[t in u[v][str(y)]['modalidades'] for t,y in zip(f.tipent,f.ano)]
    rows=[];coverage=[]
    for y in YEARS:
     z=f.loc[f.ano.eq(y)&f.edad.ge(60)]
     for v in variables:
      e=z.loc[z[v+'__elegible']]
      coverage.append({'ronda':y,'variable':v,'N_60':len(z),'N_elegible':len(e),'N_valido':int(e[v].notna().sum()),'estados':e[v+'__estado'].value_counts().to_dict()})
    for x,y in zip(YEARS[:-1],YEARS[1:]):
     base=f.loc[f.ano.eq(x)&f.edad.ge(60)&f.tipent.isin([1,2,3,4])].set_index('id')
     dest=f.loc[f.ano.eq(y)].set_index('id')
     p=base.join(dest,lsuffix='_a',rsuffix='_b',how='left',validate='one_to_one')
     present=p.ano_b.notna();alive=p.tipent_b.isin([1,2,3,4]);known=p.pension_propia_k_a.notna()&p.pension_propia_k_b.notna()&alive
     later=set(f.loc[f.ano.gt(y)&f.tipent.isin([1,2,3,4]),'id'])
     delta=p.a_o_ent_b-p.a_o_ent_a
     duration=delta.loc[alive&delta.notna()]
     month_ok=alive&p.mes_ent_a.between(1,12)&p.mes_ent_b.between(1,12)&delta.notna()
     months=(12*delta+p.mes_ent_b-p.mes_ent_a).loc[month_ok]
     row={'origen':x,'destino':y,'N_origen_vivo_60':len(base),'N_presente':int(present.sum()),'N_vivo_destino':int(alive.sum()),'N_sobre_fallecido':int(p.tipent_b.eq(5).sum()),'N_ausente':int((~present).sum()),'N_ausente_reaparece_vivo_despues':int(sum(i in later for i in p.index[~present])),'N_sustituto_origen':int(p.tipent_a.isin([3,4]).sum()),'N_sustituto_destino':int(p.tipent_b.isin([3,4]).sum()),'N_K_conocido_ambas_vivas':int(known.sum()),'N_K_ND_una_o_ambas_vivas':int((alive&~known).sum()),'intervalo_meses_validos':{'N':len(months),'min':float(months.min()),'mediana':float(months.median()),'max':float(months.max())},'intervalo_nominal':y-x,'intervalo_anio_efectivo':duration.value_counts().sort_index().to_dict(),'N_anio_efectivo_faltante_vivos':int((alive&delta.isna()).sum()),'N_edad_destino_no_60_o_ND':int((alive&~p.edad_b.ge(60)).sum()),'variables':{}}
     for v in variables:
      elig=p[v+'__elegible_a'].eq(True)&p[v+'__elegible_b'].eq(True)&alive
      valid=elig&p[v+'_a'].notna()&p[v+'_b'].notna()
      row['variables'][v]={'N_elegible_ambas':int(elig.sum()),'N_valido_ambas':int(valid.sum()),'N_valido_y_K_conocido_ambas':int((valid&known).sum())}
      if v in ['recuerdo1','recuerdo2']:
       observed=valid&p[v+'_flag_a'].eq(0)&p[v+'_flag_b'].eq(0)
       row['variables'][v].update(N_no_imputado_ambas=int(observed.sum()),N_no_imputado_y_K_conocido_ambas=int((observed&known).sum()),N_imputado_una_o_ambas=int((valid&(p[v+'_flag_a'].eq(1)|p[v+'_flag_b'].eq(1))).sum()))
     assert row['N_presente']+row['N_ausente']==len(base)
     assert row['N_vivo_destino']+row['N_sobre_fallecido']==row['N_presente']
     for z in row['variables'].values():
      assert 0 <= z['N_valido_y_K_conocido_ambas'] <= z['N_valido_ambas'] <= z['N_elegible_ambas'] <= row['N_vivo_destino']
     row['N_fallecido_y_reaparicion_viva_posterior']=int(sum(i in later for i in p.index[p.tipent_b.eq(5)]))
     rows.append(row)
    out={'poblacion':'Cohorte por intervalo: viva con 60+ en origen; destino conservado aunque edad falte o disminuya; no panel balanceado','muertes':'tipent=5 identifica registro sobre fallecido, no todas las muertes entre ausentes','reaparicion':'entrevista viva posterior entre ausentes; desconocida despues del cierre2021','pares':rows,'cobertura':coverage}
    Path('data/interim/viabilidad_longitudinal/conteos.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
    for r in rows:print(json.dumps(r,ensure_ascii=False))

if __name__ == "__main__":
    main()
