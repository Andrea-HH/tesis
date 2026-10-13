"""Distingue prevalencia de rama cónyuge y tasas en parejas con universo confirmado."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text
import json
import matplotlib.pyplot as plt
import pandas as pd
from run_pension_exploration import PUBLIC,ROOT,FIG,YEARS,inputs,write_json,checked_hashes
from tesis_enasem.pension_exploration import PopulationSpec
from tesis_enasem.protection_eda import reception_rates


def run() -> None:
    p,_,_=inputs();s=PopulationSpec().select(p);r=json.loads(read_project_text(PUBLIC/'resultados.json'));rows=[]
    for y in YEARS:
        z=s.loc[s.ano.eq(y)];explicit=z.titularidad_pareja_estado.eq('sin_pareja_residente_explicita')
        eligible=z.titularidad_pareja_estado.eq('puntero_pareja_concordante') if y>=2018 else None
        fields={'ano':y,'N_total_60':len(z),'N_sin_pareja_residente_explicita':int(explicit.sum()),
          'N_elegible_pareja_confirmado':int(eligible.sum()) if eligible is not None else None,
          'N_universo_pareja_no_confirmado':int((~eligible & ~explicit).sum()) if eligible is not None else None,
          'nota':'Desde2018 puntero doble y filtro de pareja confirmado; temprano ND, no inferirlo de estado conyugal, num_k o un negativo operativo'}
        if eligible is not None:
            rate=reception_rates(z.loc[eligible],['sexo_grupo'])
            fields['recepcion_conyuge_en_parejas_por_sexo']=[x for x in rate if x['variable']=='pension_conyuge_k']
            for x in fields['recepcion_conyuge_en_parejas_por_sexo']:x['N_elegible_pareja_confirmado']=x['N_total']
            data=pd.DataFrame(fields['recepcion_conyuge_en_parejas_por_sexo'])
            fig,ax=plt.subplots(figsize=(8,4));ax.bar(data.sexo_grupo,data.pct_si_conocido,color=plt.get_cmap('BrBG')([.12,.82]))
            ax.set_ylabel('% con pensión del cónyuge entre parejas con respuesta conocida')
            ax.set_title(f'Rama cónyuge: universo pareja confirmado · {y} · N={int(eligible.sum()):,}')
            fig.tight_layout();fig.savefig(FIG/f'U_conyuge_elegible_{y}.png',dpi=150);plt.close(fig)
        rows.append(fields)
    write_json(PUBLIC/'universos_conyuge.json',rows);r['universos_conyuge']=rows;write_json(PUBLIC/'resultados.json',r)
    print('Universo cónyuge separado de prevalencia en toda la muestra; temprano ND.');checked_hashes()


if __name__=='__main__':run()
