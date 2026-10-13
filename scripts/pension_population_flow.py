"""Flujo de selección 60+ y continuidad, sin recomputar CP1."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text
import json
import matplotlib.pyplot as plt
import pandas as pd
from run_pension_exploration import PUBLIC,FIG,YEARS,inputs,write_json,checked_hashes
from tesis_enasem.pension_exploration import PopulationSpec


def run() -> None:
    p,_,_=inputs();s=PopulationSpec().select(p);first=p.groupby('id').ano.min();first_sixty=s.groupby('id').ano.min()
    flow=[];modal=[]
    labels={1:'Directa seguimiento',2:'Directa incorporación',3:'Sustituto seguimiento',4:'Sustituto incorporación',5:'Sobre fallecido'}
    for j,y in enumerate(YEARS):
        master=p.loc[p.ano.eq(y)];q=s.loc[s.ano.eq(y)]
        new=q.id.map(first).eq(y);previous=q.id.map(first).lt(y)
        newly_eligible=q.id.map(first_sixty).eq(y)&previous
        prev_ids=set(p.loc[p.ano.eq(YEARS[j-1]),'id']) if j else set()
        returned=previous&~q.id.isin(prev_ids)
        flow.append({'ano':y,'N_maestro':len(master),'N_60':len(q),'N_personas_60':q.id.nunique(),
          'N_menores60':int(master.edad.lt(60).sum()),'N_edad_ND':int(master.edad.isna().sum()),
          'N_fallecidos_maestro':int(master.tipent.eq(5).sum()),'N_fallecidos_60':int(q.tipent.eq(5).sum()),
          'N_primera_aparicion_maestro_60':int(new.sum()),'N_previamente_registradas_60':int(previous.sum()),
          'N_primera_visita_60_con_antecedente':int(newly_eligible.sum()),'N_reaparecen_60':int(returned.sum())})
        assert len(master)==len(q)+int(master.edad.lt(60).sum())+int(master.edad.isna().sum())
        assert int(new.sum())+int(previous.sum())==len(q)
        for mode,label in labels.items():modal.append({'ano':y,'modalidad':label,'N':int(q.tipent.eq(mode).sum()),'N_total_60':len(q),
          'pct_60':100*q.tipent.eq(mode).sum()/len(q)})
    n_rounds=s.groupby('id').ronda.nunique().value_counts().sort_index()
    rounds=[{'rondas_60_observadas':n,'N_personas':int(n_rounds.get(n,0)),'N_total_personas_60':s.id.nunique()} for n in range(1,7)]
    assert sum(z['N_personas'] for z in rounds)==18754
    assert sum(z['rondas_60_observadas']*z['N_personas'] for z in rounds)==56004
    r=json.loads(read_project_text(PUBLIC/'resultados.json'));r['flujo_muestra']=flow;r['modalidades_60']=modal;r['rondas_por_persona_60']=rounds
    write_json(PUBLIC/'flujo_muestra.json',{'flujo':flow,'modalidades':modal,'rondas_por_persona':rounds})
    fig,ax=plt.subplots(figsize=(10,5));pd.DataFrame(modal).pivot(index='ano',columns='modalidad',values='pct_60').plot.bar(stacked=True,colormap='BrBG',ax=ax)
    ax.set_title('Modalidades en la muestra de 60+ por visita');ax.set_ylabel('% de N total 60+ por visita');ax.legend(fontsize=8)
    fig.tight_layout();fig.savefig(FIG/'U_modalidades_comparativa.png',dpi=150);plt.close(fig)
    write_json(PUBLIC/'resultados.json',r);checked_hashes();print('Flujo 60+, primera aparición, entrada a60, reaparición y continuidad reconciliados.')


if __name__=='__main__':run()
