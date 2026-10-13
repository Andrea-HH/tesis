"""Correspondencias conjuntas K/A y salud complementaria; conserva resultados previos."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text
import json
import matplotlib.pyplot as plt
import pandas as pd
from run_pension_exploration import ROOT,PUBLIC,FIG,YEARS,inputs,write_json,checked_hashes
from run_protection_eda import COMPARABILITY
from tesis_enasem.pension_exploration import stratified_transitions


def run() -> None:
    r=json.loads(read_project_text(PUBLIC/'resultados.json'));p,_,_=inputs();p['recepcion_ka']=p.P+' / '+p.A
    for ya,yb in zip(YEARS[:-1],YEARS[1:]):
        comparable=COMPARABILITY['pension_propia_k'][(ya,yb)] and COMPARABILITY['apoyo_propio'][(ya,yb)]
        key=f'L_conjunta_K_A_{ya}_{yb}'
        rows=stratified_transitions(p,ya,yb,'recepcion_ka','sexo_grupo',comparable)
        write_json(PUBLIC/'tablas'/f'{key}.json',rows)
        table=pd.DataFrame(rows).groupby(['origen','destino']).N.sum().unstack(fill_value=0)
        fig,ax=plt.subplots(figsize=(13,6));ax.imshow(table,aspect='auto',cmap='BrBG')
        ax.set_xticks(range(len(table.columns)),table.columns,rotation=30,ha='right',fontsize=8);ax.set_yticks(range(len(table)),table.index,fontsize=8)
        for i in range(len(table)):
            for j in range(len(table.columns)):ax.text(j,i,str(int(table.iloc[i,j])),ha='center',va='center',fontsize=7)
        ax.set_title(f'K/A propios: origen × destino · {ya}–{yb} · '+('comparabilidad condicionada' if comparable else 'ruptura de instrumento'))
        fig.tight_layout();fig.savefig(FIG/f'{key}.png',dpi=150);plt.close(fig)
        known=[x for x in rows if 'Desconocido' not in x['origen']+x['destino'] and x['destino'] in ['Sí / Sí','Sí / No','No / Sí','No / No']]
        text=f'{sum(z["N"] for z in rows):,} personas 60+ vivas en origen; {sum(z["N"] for z in known):,} pares K/A completos. '
        if comparable:
            both=sum(z['N'] for z in known if z['destino']=='Sí / Sí');text+=f'{both:,} tienen simultáneamente K y A afirmativos en destino entre pares completos. Comparabilidad binaria condicionada 2012–2015, no equivalencia de programas/instituciones. '
        else:text+='La recepción conjunta no admite transiciones homologadas porque cambia al menos uno de los instrumentos. '
        text+='La tabla conserva las nueve combinaciones parciales, muerte y ausencias por sexo de origen. No se suman K+A ni se atribuyen montos del cónyuge.'
        r['seguimiento'][key]={'solicitud':f'Transiciones conjuntas propias K/A {ya}–{yb}',
          'tabla':f'docs/eda/pensiones_exploratorio_v1/tablas/{key}.json','figura':f'reports/pensiones_exploratorio_v1/figuras/{key}.png',
          'interpretacion':text,'estado':'Completo provisional' if comparable else 'No viable con los datos actuales'}
    health=json.loads(read_project_text(PUBLIC/'salud_complementaria.json'))
    report=['# Relaciones complementarias con salud\n\nPersonas 60+ por visita; no ponderadas. Pensión propia K y estado pensionario; cinco indicadores con sus universos del libro ENASEMsimple. Estos cruces complementan los ocho principales y no establecen un modelo, diagnóstico ni efecto de recibir pensión.']
    for year in YEARS:
        rows=[z for z in health if z['ano']==year];fig,ax=plt.subplots(figsize=(9,4));data=pd.DataFrame(rows)
        ax.barh(data.indicador,data.rho_spearman,color=plt.get_cmap('BrBG')(.12));ax.axvline(0,color='black',lw=.5)
        ax.set_xlabel('Spearman: recepción K propia binaria y puntuación/código ordinal conocido');ax.set_title(f'Pensiones y salud · {year}')
        fig.tight_layout();fig.savefig(FIG/f'C_salud_{year}.png',dpi=150);plt.close(fig)
        text='; '.join(f'{z["indicador"]}: ρ={z["rho_spearman"]:.4f}, pares válidos {z["N_validos"]:,}, excluidos {z["N_excluidos"]:,}' for z in rows if z['rho_spearman'] is not None)
        report += [f'## {year}',text+'. Asociaciones contemporáneas de rangos. Edad, selección, modalidad y cobertura pueden condicionar estos contrastes; no hay ajustes ni pruebas confirmatorias.',
            f'![Salud](../../../reports/pensiones_exploratorio_v1/figuras/C_salud_{year}.png)']
        r.setdefault('complementarios_salud',{})[f'CS_{year}']={'solicitud':f'Pensiones y salud complementaria {year}','N_total':int(p.ano.eq(year).mul(p.edad.ge(60)).sum()),
          'tabla':'docs/eda/pensiones_exploratorio_v1/salud_complementaria.json','figura':f'reports/pensiones_exploratorio_v1/figuras/C_salud_{year}.png',
          'interpretacion':text+'. Sin causalidad, diagnóstico ni significancia; codificación y universos del indicador ENASEMsimple.',
          'estado':'Completo provisional'}
    write_project_text(PUBLIC/'SALUD_COMPLEMENTARIA.md', '\n\n'.join(report)+'\n')
    write_json(PUBLIC/'resultados.json',r);checked_hashes();print('K/A conjunto y relaciones de salud conservados como complementos explícitos.')


if __name__=='__main__':run()
