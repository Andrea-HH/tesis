"""Universos de componentes de cónyuge sin repetir sus distribuciones calculadas."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text, read_project_bytes

from hashlib import sha256
import json
from pathlib import Path
import re

import pandas as pd

from tesis_enasem.economic_eda import plot_source
from tesis_enasem.independent_eda import VariableSpec, strict_json, validate_values
from run_independent_eda import md_table
from run_k2021_eda import nullable_membership, ROOT


def review() -> dict:
    """Reread focalizado sin claves: añade solo denominadores de rama documentada."""
    path=project_path('', 'reports/eda_independiente/k2021/resultados.json')
    data=json.loads(read_project_text(path))
    def measurements(payload: dict) -> str:
        return sha256(json.dumps([{**{k:v for k,v in r['resumen'].items() if k in {'N_total','N_valido','N_no_valido','pct_valido_total','media','DE','min','p01','p05','p25','mediana','p75','p95','p99','max','N_ceros','N_negativos'}},'estados':r['estados'],'distribucion':r['distribucion']} for s in payload['fuentes'] for r in s['resultados'].values()],sort_keys=True).encode()).hexdigest()
    before=measurements(data)
    changed=[]
    for source in data['fuentes']:
        fid=source['fuente']
        if fid not in {'F03','F17'}: continue
        names=[]
        for name in source['resultados']:
            match=re.fullmatch(r'(?:amk|imamk|dumk)(.+)_21',name)
            if match and (match[1] in {'53a','54a','56a','57a'} or match[1].startswith(('67_','83_'))):names.append(name)
        if fid=='F17':
            raw_path=project_path('', 'data/raw', source['archivo'])
            assert sha256(read_project_bytes(raw_path)).hexdigest()==source['sha256']
            frame=pd.read_stata(raw_path,columns=['k52a_21',*names],convert_missing=True,convert_categoricals=False)
            eligible=nullable_membership(frame.k52a_21,[2],[1])
            known=int(eligible.notna().sum());confirmed=int(eligible.fillna(False).sum());unknown=len(frame)-known
        for name in names:
            r=source['resultados'][name];s=r['resumen'];c=r['contrato'];old_note=c['eligibility']
            if fid=='F03':
                c['eligibility']='ND: componentes del cónyuge requieren pareja; k52a_21 no existe en F03. No se infiere universo de N válido ni de los perdidos.'
                s.update(N_elegible=None,N_elegibilidad_desconocida=s['N_total'],N_valido_elegible=None,N_valido_fuera_universo=None,pct_valido_elegible=None)
                s.pop('N_elegible_confirmado',None)
            else:
                c['eligibility']='Cónyuge: k52a_21=2 elegible, 1 excluido, perdido desconocido. Universo del producto de pareja, no pregunta monetaria entre receptores.'
                values,_=validate_values(frame[name],VariableSpec(**c))
                nv=int((eligible.fillna(False)&values.notna()).sum())
                outside=int((eligible.eq(False).fillna(False)&values.notna()).sum())
                s.update(N_elegible=confirmed if not unknown else None,N_elegible_confirmado=confirmed,
                         N_elegibilidad_desconocida=unknown,N_valido_elegible=nv,N_valido_fuera_universo=outside,
                         pct_valido_elegible=100*nv/confirmed if confirmed and not unknown else None)
                assert outside==0
            fiche=project_path('', f'docs/eda/k2021/{fid}_{name}.md')
            text=read_project_text(fiche).replace(old_note,c['eligibility'])
            a,b=text.split('## Resultados\n\n',1);_,tail=b.split('\n\n',1)
            # Solo sustituye la primera tabla: estados/histogramas/interpretación intactos.
            write_project_text(fiche, a+'## Resultados\n\n'+md_table([s])+'\n'+tail)
            plot_source(r,VariableSpec(**c),fid,project_path('', f'reports/eda_independiente/k2021/figuras/{fid}/{name}.png'))
            changed.append({'fuente':fid,'variable':name,**{k:s[k] for k in ['N_total','N_elegible','N_valido','N_elegibilidad_desconocida']}})
        strict_json(source,project_path('', f'reports/eda_independiente/k2021/{fid}_resultados.json'))
    assert measurements(data)==before
    strict_json(data,path)
    contracts_path=project_path('', 'docs/eda/contratos_k2021.json');contracts=json.loads(read_project_text(contracts_path))
    for c in contracts['contratos']:
        if c['fuente'] not in {'F03','F17'}:continue
        c.update(next(s for s in data['fuentes'] if s['fuente']==c['fuente'])['resultados'][c['variable']]['contrato'])
    strict_json(contracts,contracts_path)
    ledger_path=project_path('', 'docs/eda/cobertura_variables.json');ledger=json.loads(read_project_text(ledger_path))
    for item in changed:
        row=next(r for r in ledger if r['fuente']==item['fuente'] and r['variable']==item['variable'])
        row.update(N_elegible=item['N_elegible'],N_elegibilidad_desconocida=item['N_elegibilidad_desconocida'],pendiente='Componentes de cónyuge: filtro ausente F03 o 23 registros F17 de condición desconocida; N válido no es elegible')
    strict_json(ledger,ledger_path)
    result={'variables_revisadas':len(changed),'F17_N_pareja_confirmada':confirmed,'F17_N_condicion_desconocida':unknown,'sha256_mediciones_preservadas':before,'cotejos':changed}
    strict_json(result,project_path('', 'docs/eda/k2021_universos_revision.json'))
    report=project_path('', 'docs/eda/B02A_K_2021.md');text=read_project_text(report).split('\n## Revisión de universos de cónyuge')[0]
    text+='\n## Revisión de universos de cónyuge\n\n'+md_table([{k:v for k,v in result.items() if k!='cotejos'}])+'''
Los 15 componentes del cónyuge y sus versiones requieren pareja. F03 carece de k52a_21: N elegible queda ND, aunque sus imputados tienen 5,199 valores disponibles. No se interpreta el resto como no respuesta ni se iguala válido/elegible. F17 permite confirmar 10,189 registros con pareja, 5,527 únicos y 23 de condición desconocida: N elegible total permanece ND por esos desconocidos; se muestra también N elegible confirmado. No hay valores válidos en la rama documentada como excluida. Las 45 variables F03 y 30 F17 revisadas conservan todos sus descriptivos, estados y histogramas. Solo se añaden denominadores documentados, sin unión entre fuentes.\n'''
    write_project_text(report, text)
    print({k:v for k,v in result.items() if k!='cotejos'})
    return result


if __name__=='__main__':
    review()
