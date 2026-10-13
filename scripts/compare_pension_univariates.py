"""Comparativos numéricos y BrBG de los indicadores 60+ ya resumidos."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text
import json
import matplotlib.pyplot as plt
import pandas as pd
from run_pension_exploration import ROOT,PUBLIC,FIG,YEARS,write_json,checked_hashes


def run() -> None:
    r=json.loads(read_project_text(PUBLIC/'resultados.json'));comparisons={}
    for var in r['univariados']['2001']['controles']:
        rows=[{'ano':year,**x} for year in YEARS for x in r['univariados'][str(year)]['controles'][var]]
        fig,ax=plt.subplots(figsize=(10,5));t=pd.DataFrame(rows)
        if 'categoria' in t:
            matrix=t.pivot(index='ano',columns='categoria',values='pct_total').fillna(0)
            matrix.plot.bar(stacked=True,colormap='BrBG',ax=ax);ax.set_ylabel('% del total 60+ por visita, incluidos ND')
            ax.legend(fontsize=8,bbox_to_anchor=(1.02,1),loc='upper left')
        else:
            ax.plot(t.ano,t.mediana,marker='o',color=plt.get_cmap('BrBG')(.12),label='Mediana')
            ax.fill_between(t.ano,t.p25,t.p75,color=plt.get_cmap('BrBG')(.72),alpha=.35,label='P25–P75')
            ax.set_xticks(YEARS,[str(y) for y in YEARS],rotation=20);ax.set_ylabel('Estadístico dentro de ronda; ver unidad en contrato');ax.legend()
        ax.set_title(f'{var}: composición transversal de la muestra 60+, 2001–2021')
        fig.text(.01,.01,'Sin ponderar. No representa trayectoria individual, crecimiento real, diagnóstico o efecto de políticas.',fontsize=8)
        fig.tight_layout(rect=[0,.05,1,1]);key=f'U_comparativa_{var}';fig.savefig(FIG/f'{key}.png',dpi=150);plt.close(fig)
        # Diferencia efectivamente calculada, nunca afirmación de evolución personal.
        if 'categoria' in t:
            earlier=t.loc[t.ano.eq(2001)].set_index('categoria');later=t.loc[t.ano.eq(2021)].set_index('categoria')
            common=earlier.index.intersection(later.index).difference(['Desconocido'])
            differences={c:float(later.loc[c,'pct_total']-earlier.loc[c,'pct_total']) for c in common}
            largest=max(differences,key=lambda c:abs(differences[c])) if differences else None
            text=(f'La categoría {largest} cambia descriptivamente de {earlier.loc[largest,"N"]:,}/{earlier.loc[largest,"N_total"]:,} '
                f'({earlier.loc[largest,"pct_total"]:.2f}%) a {later.loc[largest,"N"]:,}/{later.loc[largest,"N_total"]:,} '
                f'({later.loc[largest,"pct_total"]:.2f}%): {differences[largest]:+.2f} pp del total de la muestra por visita.' if largest else 'Sin categorías comunes evaluables.')
        else:
            a=t.loc[t.ano.eq(2001)].iloc[0];b=t.loc[t.ano.eq(2021)].iloc[0]
            text=f'Mediana descriptiva 2001={a.mediana:,.2f} (N válido {a.N_valido:,}), 2021={b.mediana:,.2f} (N válido {b.N_valido:,}); IQR y ND de cada ronda en tabla.'
        text+=' Cambia la composición de personas observadas: no evolución de las mismas personas, incidencia o efecto causal. Los contratos del indicador y su cobertura condicionan comparabilidad.'
        if var=='imp_neto':text+=' Patrimonio compartido, unidades almacenadas nominales: no comparación económica real; deflactor pendiente.'
        comparisons[var]={'tabla':f'docs/eda/pensiones_exploratorio_v1/tablas/{key}.json',
            'figura':f'reports/pensiones_exploratorio_v1/figuras/{key}.png','interpretacion':text,'estado':'Completo provisional'}
        write_json(PUBLIC/'tablas'/f'{key}.json',rows)
    r['comparativos_univariados']=comparisons
    for year in YEARS:
        u=r['univariados'][str(year)];rates=u['recibos_reutilizados']
        t=pd.DataFrame(rates).set_index('variable')[['N_si','N_no','N_desconocido']]
        fig,ax=plt.subplots(figsize=(10,5));t.plot.bar(stacked=True,colormap='BrBG',ax=ax)
        ax.set_ylabel('Personas 60+ de cada rama, incluidos desconocidos');ax.set_title(f'Recepción K/A propia y del cónyuge · {year}')
        ax.tick_params(axis='x',rotation=20);fig.tight_layout();fig.savefig(FIG/f'U_recepcion_{year}.png',dpi=150);plt.close(fig)
        u['interpretaciones']['recepcion_individual']='; '.join(f'{z["variable"]}: sí {z["N_si"]:,}, no {z["N_no"]:,}, ND {z["N_desconocido"]:,}; '
            f'{z["N_si"]:,}/{z["N_conocido"]:,} conocidas ({z["pct_si_conocido"]:.2f}%)' for z in rates)+'. Las ramas no se suman, y desconocimiento de la pareja no invalida una afirmativa propia confirmada. Reutiliza los conteos J02 sin reconstruirlos.'
        write_json(PUBLIC/'tablas'/f'U_{year}.json',u)
    write_json(PUBLIC/'resultados.json',r);checked_hashes();print('Comparativos 60+ y visualización de recepción con ND, desde agregados ya calculados.')


if __name__=='__main__':run()
