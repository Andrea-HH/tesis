"""Distribuciones faltantes 60+; no repite cruces ni auditorías previas."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text

import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from run_pension_exploration import ROOT,PUBLIC,FIG,YEARS,inputs,write_json,checked_hashes
from tesis_enasem.pension_exploration import PopulationSpec


def run() -> None:
    """Amplía solamente las tablas univariadas nuevas y su trazabilidad."""
    p,k,a=inputs();s=PopulationSpec().select(p)
    r=json.loads(read_project_text(PUBLIC/'resultados.json'));contracts={c['variable']:c for c in json.loads(read_project_text(project_path('', 'docs/eda/contratos_simple.json')))['contratos']}
    for year in YEARS:
        part=s.loc[s.ano.eq(year)]
        saved=json.loads(read_project_text(PUBLIC/'tablas'/f'U_{year}.json'))
        if saved.get('interpretaciones') and saved.get('tipos_prestacion'):
            r['univariados'][str(year)]=saved
            continue
        u=r['univariados'][str(year)];u['interpretaciones']={};u['figuras_controles']={}
        for var,rows in u['controles'].items():
            fig,ax=plt.subplots(figsize=(9,4));c=plt.get_cmap('BrBG')(.12)
            if var.endswith('_grupo') or var in ('salud_glob','diabetes'):
                t=pd.DataFrame(rows);ax.bar(t.categoria,t.N,color=c);ax.tick_params(axis='x',rotation=20)
                valid=[x for x in rows if x['categoria']!='Desconocido']
                top=max(valid,key=lambda x:x['N']) if valid else None
                prose=(f'Categoría modal {top["categoria"]}: {top["N"]:,}/{top["N_valido"]:,} respuestas conocidas '
                       f'({top["pct_validos"]:.2f}%), {top["N_desconocido"]:,} ND entre {top["N_total"]:,} registros.' if top else 'No hay respuestas conocidas.')
                if var in contracts:
                    labels=contracts[var]['codes'];prose+=' Códigos: '+str(labels)+'.'
            else:
                values=part[var].dropna();t=rows[0]
                numeric=values.to_numpy(dtype=float)
                if var=='imp_neto':
                    numeric=np.sign(numeric)*np.log1p(np.abs(numeric));ax.set_xlabel('signo(x) × log(1+|x|); ceros y negativos conservados')
                else:ax.set_xlabel(contracts.get(var,{}).get('unit',var))
                counts,edges=np.histogram(numeric,bins=25)
                ax.hist(numeric,bins=edges,color=c)
                u[f'histograma_{var}']=[{'limite_inferior':float(lo),'limite_superior':float(hi),'N':int(n)} for n,lo,hi in zip(counts,edges[:-1],edges[1:])]
                prose=(f'Mediana {t["mediana"]:,.2f}, IQR [{t["p25"]:,.2f},{t["p75"]:,.2f}]; '
                       f'N válido {t["N_valido"]:,}/{t["N_total"]:,}, ND {t["N_desconocido"]:,}, '
                       f'extremos [{t["min"]:,.2f},{t["max"]:,.2f}], ceros {t["N_ceros"]:,}, negativos {t["N_negativos"]:,}.') if t['N_valido'] else 'Sin observaciones válidas; no se obtiene distribución.'
            ax.set_title(f'{var} · {year} · personas 60+');ax.set_ylabel('Frecuencia absoluta de respuestas válidas' if not var.endswith('_grupo') and var not in ('salud_glob','diabetes') else 'Frecuencia absoluta, incluidos ND')
            fig.tight_layout();key=f'U_control_{var}_{year}';fig.savefig(FIG/f'{key}.png',dpi=150);plt.close(fig)
            u['figuras_controles'][var]=f'reports/pensiones_exploratorio_v1/figuras/{key}.png'
            u['interpretaciones'][var]=prose+' Descriptivo de la muestra por visita, sin pesos. No cambio individual ni diagnóstico o causalidad. Escolaridad inicial, ocupación no profesión y patrimonio compartido; consultar contrato según variable.'
        e=k.loc[k.ano.eq(year)&k.beneficiario_id.isin(part.id)];ae=a.loc[a.ano.eq(year)&a.beneficiario_id.isin(part.id)]
        types=[]
        for typ,label in [(1,'Jubilación/retiro'),(2,'Viudez/supervivencia'),(3,'Invalidez'),(4,'Otra pensión')]:
            z=e.loc[e.tipo.eq(typ)];types.append({'tipo':label,'N_eventos':len(z),'N_beneficiarios':z.beneficiario_id.nunique(),
                 'N_receptores_propios_K':int(part.pension_propia_k.eq(True).sum()),
                 'N_monto_valido':int(z.monto_mensual_observado.notna().sum()),'N_monto_ND':int(z.monto_mensual_observado.isna().sum())})
        u['tipos_prestacion']=types
        fig,ax=plt.subplots(figsize=(9,4));df=pd.DataFrame(types);df.plot.bar(x='tipo',y='N_beneficiarios',ax=ax,color=plt.get_cmap('BrBG')(.12),legend=False)
        ax.set_ylabel('Personas beneficiarias; tipos pueden solaparse');ax.set_title(f'Tipo de prestación K · {year}');ax.tick_params(axis='x',rotation=15)
        fig.tight_layout();fig.savefig(FIG/f'U_tipos_{year}.png',dpi=150);plt.close(fig)
        u['interpretaciones']['tipos_prestacion']='; '.join(f'{x["tipo"]}: {x["N_beneficiarios"]:,} personas y {x["N_eventos"]:,} eventos, {x["N_monto_ND"]:,} montos ND' for x in types)+'. Viudez identifica al beneficiario efectivo del evento, no a quien generó el derecho. Las contingencias no son regímenes contributivos ni grupos mutuamente excluyentes.'
        programs=[]
        for name,z in ae.groupby('programa',dropna=False):
            programs.append({'programa':str(name) if pd.notna(name) else 'Donativo agregado sin programa identificado',
                'N_eventos':len(z),'N_beneficiarios':z.beneficiario_id.nunique(),'N_monto_valido':int(z.monto_mensual_observado.notna().sum()),
                'N_monto_ND':int(z.monto_mensual_observado.isna().sum()),'unidad':'Evento orientado a beneficiario 60+; dinero/especie sin separación'})
        u['programas_observados']=programs
        fig,ax=plt.subplots(figsize=(10,4));df=pd.DataFrame(programs)
        if len(df):ax.barh(df.programa,df.N_beneficiarios,color=plt.get_cmap('BrBG')(.72))
        ax.set_xlabel('Personas con programa/categoría observado; selección múltiple');ax.set_title(f'Programas/categorías A · {year}')
        fig.tight_layout();fig.savefig(FIG/f'U_programas_{year}.png',dpi=150);plt.close(fig)
        u['interpretaciones']['programas_observados']='; '.join(f'{x["programa"]}: {x["N_beneficiarios"]:,} beneficiarios, {x["N_monto_ND"]:,}/{x["N_eventos"]:,} montos ND' for x in programs)+'. Categorías son las observadas en ENASEM; no corresponden al número de programas del catálogo nacional ni a un padrón de beneficiarios. Dinero y especie no separables.'
        for block in ['K','A']:
            z=next(x for x in json.loads(read_project_text(project_path('', 'docs/eda/proteccion_economica/resultados.json')))['montos'] if x['ano']==year and x['bloque']==block)
            u['interpretaciones'][f'montos_{block}']=f'Monto mensual nominal por evento {block}: mediana {z["mediana_nominal_mensual"]:,.2f}, IQR [{z["p25"]:,.2f},{z["p75"]:,.2f}], válido {z["N_monto_observado"]:,}/{z["N_eventos"]:,}, desconocido {z["N_monto_desconocido"]:,}. No representa ingreso total ni poder adquisitivo comparable entre rondas. El histograma usa log(1+monto), conserva cero y muestra la cola sin truncar valores válidos.'
        u['interpretaciones']['titularidad']='; '.join(f'{x["categoria"]}: {x["N"]:,}/{x["N_total"]:,} ({x["pct_total"]:.2f}%)' for x in u['titularidad'])+'. La clasificación conjunta exige dos ramas conocidas; ND incluye casos de titularidad o respuesta incompleta, no es ausencia. 2001 sigue provisional por J1.'
        write_json(PUBLIC/'tablas'/f'U_{year}.json',u)
    d=json.loads(read_project_text(PUBLIC/'mapa_columnas.json'));b01=json.loads(read_project_text(project_path('', 'reports/eda_independiente/simple_resultados.json')))['resultados']
    coverage={}
    for x in b01:
        coverage[x['contrato']['variable']]=x['resumen']
    kcontracts={(x['fuente'],x['variable']):x for x in json.loads(read_project_text(project_path('', 'docs/eda/contratos_k2021.json')))['contratos']}
    for x in d:
        if x['producto']=='maestra_ENASEMsimple' and x['variable_fuente'] in coverage:
            x['cobertura_B01_por_ronda']=coverage[x['variable_fuente']];x['ambito_cobertura_B01']='Todas las edades, no la selección 60+'
        contract=kcontracts.get((x['fuente'],x['variable_fuente']))
        if contract:
            x['contrato_eda_independiente']=contract;x['estado']='Contrato B02a parcial; filtros y titularidad según contrato, no armonización definitiva'
    write_json(PUBLIC/'mapa_columnas.json',d)
    write_json(PUBLIC/'mapa_armonizadas.json',json.loads(read_project_text(project_path('', 'docs/eda/proteccion_economica/contratos_armonizacion.json'))))
    write_json(PUBLIC/'resultados.json',r);checked_hashes();print('Univariados 60+ ampliados con figuras, respaldo de distribución e interpretaciones específicas.')


if __name__=='__main__':run()
