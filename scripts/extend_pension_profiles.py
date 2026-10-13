"""Complementos de perfiles y transiciones condicionadas sin repetir bloques existentes."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text
import json
import matplotlib.pyplot as plt
import pandas as pd
from run_pension_exploration import ROOT,PUBLIC,FIG,YEARS,inputs,write_json,checked_hashes
from run_protection_eda import COMPARABILITY,COMPARABILITY_REASONS
from tesis_enasem.pension_exploration import PopulationSpec,stratified_transitions
from tesis_enasem.protection_eda import numeric_association


def run() -> None:
    r=json.loads(read_project_text(PUBLIC/'resultados.json'));p,_,_=inputs();s=PopulationSpec().select(p)
    universe=json.loads(read_project_text(project_path('', 'docs/eda/universos_simple.json')))['reglas']
    for year in YEARS:
        part=s.loc[s.ano.eq(year)];u=r['univariados'][str(year)]
        for var,rows in u['controles'].items():
            raw=var.replace('_grupo','');contract=universe.get(raw,{}).get(str(year),{})
            modalities=contract.get('modalidades')
            for x in rows:
                x['N_elegible']=int(part.tipent.isin(modalities).sum()) if modalities is not None else None
                x['nota_elegibilidad']=contract.get('nota','No reconstruida; no sustituir por N válido')
        write_json(PUBLIC/'tablas'/f'U_{year}.json',u)
    for key,x in r['analisis'].items():
        b=json.loads(read_project_text(project_path('', x['tabla'])));part=s.loc[s.ano.eq(b['ano'])]
        extra=[]
        if b.get('tasas'):
            for row in b['tasas']:
                row['N_personas_estrato']=row['N_total']
                denominator=int(part[row['variable']].eq(True).sum())
                row['pct_composicion_receptores']=100*row['N_si']/denominator if denominator else None
            if key.startswith('B'):
                groups=b['grupos']
                for row in b['tasas']:
                    if row['variable'] in ('pension_propia_k','pension_conyuge_k') and all(row[g]!='Desconocido' for g in groups):
                        extra.append(' / '.join(str(row[g]) for g in groups)+': '+row['variable']+
                            f' {row["N_si"]:,}/{row["N_conocido"]:,} conocidas ({row["pct_si_conocido"]:.2f}%), '
                            f'{row["pct_composicion_receptores"]:.2f}% de todos los receptores de esa rama en la ronda.')
            if key.startswith('B2'):
                b['asociacion_edad_continua']=[{'variable':'Pensión propia',**numeric_association(part,'edad','pension_propia_k')},
                    {'variable':'Apoyo propio',**numeric_association(part,'edad','apoyo_propio')}]
                extra+= [f'Edad continua y {z["variable"]}: Spearman ρ={z["rho_spearman"]:.4f}, N={z["N_validos"]:,}.' for z in b['asociacion_edad_continua'] if z['rho_spearman'] is not None]
        if key.startswith('T8'):
            rows=[]
            from tesis_enasem.joint_eda import paired_spearman
            for level,z in part.groupby('educacion_grupo',dropna=False):
                rows.append({'educacion_grupo':level,'recepcion_vs_patrimonio':numeric_association(z,'imp_neto','pension_propia_k'),
                  'monto_vs_patrimonio':paired_spearman(z,'imp_neto','monto_k_propio_mensual_observado_parcial',b['ano'])})
            b['asociaciones_patrimonio_condicionadas_educacion']=rows
            text='Asociación condicionada entre recepción propia y patrimonio por escolaridad: '+'; '.join(
                f'{z["educacion_grupo"]}: Spearman ρ={z["recepcion_vs_patrimonio"]["rho_spearman"]:.4f}, N={z["recepcion_vs_patrimonio"]["N_validos"]:,}'
                for z in rows if z['recepcion_vs_patrimonio']['rho_spearman'] is not None)+'. Patrimonio compartido y composición; no efecto causal ni outcome.'
            if '\n\nAsociación condicionada' not in b['interpretacion']:b['interpretacion']+='\n\n'+text
        if key.startswith('B8'):
            valid=b['salario_recepcion'];eligible=b['N_elegible_salario_confirmado']
            extra.append(f'Recepción salarial se observa en un universo confirmado de {eligible:,} personas con trabajo principal asalariado; '
                         f'{b["N_sin_elegibilidad_salario_confirmada"]:,} carecen de ese filtro confirmado, no son ceros salariales.')
            for z in valid:
                if z['variable']=='pension_propia_k':extra.append(f'Salario {z["salario_principal_estado"]}: '
                    f'K propia {z["N_si"]:,}/{z["N_conocido"]:,} ({z["pct_si_conocido"]:.2f}%), K ND {z["N_desconocido"]:,}.')
            # Segunda figura responde directamente al componente ingresos, sin fingir montos homologados.
            t=pd.DataFrame([z for z in valid if z['variable']=='pension_propia_k'])
            fig,ax=plt.subplots(figsize=(8,4))
            if len(t):ax.bar(t.salario_principal_estado,t.pct_si_conocido,color=plt.get_cmap('BrBG')(.12))
            ax.set_ylabel('% K propia entre respuestas conocidas');ax.set_xlabel('Recepción de salario principal; filtro asalariado confirmado')
            ax.set_title(f'Pensión × recepción salarial · {b["ano"]} · N elegible={eligible:,}')
            fig.tight_layout();fig.savefig(FIG/f'{key}_salario.png',dpi=150);plt.close(fig)
            b['figura_salario']=f'reports/pensiones_exploratorio_v1/figuras/{key}_salario.png'
        if extra and '\n\nDetalles de respaldo:' not in b['interpretacion']:
            b['interpretacion']+='\n\nDetalles de respaldo: '+'; '.join(extra)
        r['analisis'][key]['interpretacion']=b['interpretacion'];write_json(project_path('', x['tabla']),b)
    # Descripción por perfil de las matrices ya calculadas: no recomputar transiciones.
    for key,x in r['seguimiento'].items():
        rows=json.loads(read_project_text(project_path('', x['tabla'])));field=next(c for c in rows[0] if c.endswith('_grupo') or c=='edad_quinquenal')
        details=[]
        for level in sorted({str(z[field]) for z in rows}):
            z=[v for v in rows if str(v[field])==level]
            n=sum(v['N'] for v in z);nd=sum(v['N'] for v in z if v['destino']=='Desconocido')
            death=sum(v['N'] for v in z if v['destino']=='Sobre fallecido');absence=sum(v['N'] for v in z if v['destino'].startswith('Ausente'))
            starts=sum(v['N'] for v in z if v['evento']=='Inicio observado')
            den=sum(v['N'] for v in z if v['origen']=='No' and v['destino'] in ['Sí','No'])
            detail=f'{level}: N origen {n:,}, fallecidos {death:,}, ausentes {absence:,}, recepción final ND {nd:,}'
            if rows[0]['comparabilidad_condicionada'] and rows[0]['variable'] in ('P','S','A'):
                detail+=f', inicios {starts:,}/{den:,} negativas iniciales con final conocido'+(f' ({100*starts/den:.2f}%)' if den else ' (ND)')
            details.append(detail)
        if '\n\nPerfil de origen:' not in x['interpretacion']:x['interpretacion']+='\n\nPerfil de origen: '+'; '.join(details)+'.'
    # Inicio A entre negativas K de origen: la comparabilidad requerida es A, no el K posterior.
    for ya,yb in zip(YEARS[:-1],YEARS[1:]):
        negative_ids=set(s.loc[s.ano.eq(ya)&s.pension_propia_k.eq(False),'id'])
        cohort=p.loc[p.id.isin(negative_ids)].copy()
        key=f'L_A_entre_negativas_K_{ya}_{yb}';comparable=COMPARABILITY['apoyo_propio'][(ya,yb)]
        rows=stratified_transitions(cohort,ya,yb,'A','sexo_grupo',comparable)
        write_json(PUBLIC/'tablas'/f'{key}.json',rows)
        plot=pd.DataFrame(rows);table=plot.groupby(['origen','destino']).N.sum().unstack(fill_value=0)
        fig,ax=plt.subplots(figsize=(10,4));im=ax.imshow(table,aspect='auto',cmap='BrBG')
        ax.set_xticks(range(len(table.columns)),table.columns,rotation=20,fontsize=8);ax.set_yticks(range(len(table)),table.index)
        for i in range(len(table)):
            for j in range(len(table.columns)):ax.text(j,i,str(int(table.iloc[i,j])),ha='center',va='center',fontsize=8)
        ax.set_title(f'A entre negativas K en origen · {ya}–{yb} · N={sum(z["N"] for z in rows):,}');fig.tight_layout()
        fig.savefig(FIG/f'{key}.png',dpi=150);plt.close(fig)
        starts=sum(z['N'] for z in rows if z['evento']=='Inicio observado');den=sum(z['N'] for z in rows if z['origen']=='No' and z['destino'] in ('Sí','No'))
        text=f'Cohorte con negativa K en {ya}, 60+ viva: {sum(z["N"] for z in rows):,} personas. '
        text+=(f'Inicio A observado {starts:,}/{den:,} con negativa A inicial y respuesta final conocida ({100*starts/den:.2f}%). ' if comparable and den else 'Cambio documental impide interpretar un inicio A homogéneo. ')
        text+=COMPARABILITY_REASONS[('apoyo_propio',ya)]+'. No equivale a personas sin toda pensión, ni implica que el apoyo haya causado ampliación de cobertura.'
        r['seguimiento'][key]={'solicitud':f'Apoyo futuro entre negativas K de origen {ya}–{yb}',
            'tabla':f'docs/eda/pensiones_exploratorio_v1/tablas/{key}.json','figura':f'reports/pensiones_exploratorio_v1/figuras/{key}.png',
            'interpretacion':text,'estado':'Completo provisional' if comparable else 'No viable con los datos actuales'}
    # Salud complementaria sin desplazar pensionario: asociaciones y distribuciones por rama.
    from tesis_enasem.pension_exploration import continuous_table
    from tesis_enasem.protection_eda import categorical_association
    health=[]
    for year in YEARS:
        part=s.loc[s.ano.eq(year)]
        for var in ['diabetes','salud_glob','n_sint_depr','n_abvd','recuerdo1']:
            q=part.copy();q['pension_binaria']=q.pension_propia_k.astype(float)
            health.append({'ano':year,'indicador':var,'unidad':'Persona-ronda 60+',
                **numeric_association(q,var,'pension_propia_k'),
                'distribuciones':continuous_table(q,var,['titularidad_grupo']),
                'nota':'Síntomas, funcionalidad y cognición no son equivalentes; no diagnóstico ni efecto pensionario. Universo original de cada indicador según contratos B01.'})
    write_json(PUBLIC/'salud_complementaria.json',health)
    write_json(PUBLIC/'resultados.json',r);checked_hashes();print('Detalles condicionados, elegibilidad univariada y apoyo futuro entre negativas K documentados.')


if __name__=='__main__':run()
