"""Precisa unidades K sin recalcular descriptivos: entradas exclusivamente agregadas."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text

from hashlib import sha256
import json
from pathlib import Path
import re

from tesis_enasem.economic_eda import plot_source
from tesis_enasem.independent_eda import VariableSpec, strict_json
from run_k2021_eda import component_unit, ROOT


def refresh() -> None:
    """Corrige solo metadatos académicos; verifica inmutabilidad de todas las cifras."""
    path=project_path('', "reports/eda_independiente/k2021/resultados.json")
    data=json.loads(read_project_text(path))
    def numbers(payload: dict) -> str:
        return sha256(json.dumps([{k:v for k,v in r.items() if k!='contrato'} for s in payload['fuentes'] for r in s['resultados'].values()],sort_keys=True).encode()).hexdigest()
    before=numbers(data)
    units={}
    changed=0
    for s in data['fuentes']:
        for name,r in s['resultados'].items():
            c=r['contrato']
            old_page=c['page']
            if name.startswith(('amk','imamk','dumk')):
                base=re.sub(r'^(?:amk|imamk|dumk)','',name).removesuffix('_21')
                c['page']=14 if base in {'4_1','4_2','8_1','8_2','20_1','24_1','33_1','33_2','33_3','40','42','44','86','88','101','103','111'} else 13
            elif name in {'k1_21','k3_1_21','k4_1_21','k8_1_21'}:
                c['page']=56
            elif name in {'k31a_21','k31b_21','k31c_21'}:
                c['page']=61
            elif name=='k38_21':
                c['page']=62
            if old_page!=c['page']:
                fiche=project_path('', f"docs/eda/k2021/{s['fuente']}_{name}.md")
                write_project_text(fiche, read_project_text(fiche).replace(f', p. {old_page}.',f", p. {c['page']}."))
            match=re.fullmatch(r'(?:imamk|amk)(.+)_21',name)
            if not match: continue
            old=c['unit']; new=component_unit(match[1]); c['unit']=new
            units[(s['fuente'],name)]=new
            if old!=new:
                changed+=1
                fiche=project_path('', f"docs/eda/k2021/{s['fuente']}_{name}.md")
                write_project_text(fiche, read_project_text(fiche).replace(old,new))
                plot_source(r,VariableSpec(**c),s['fuente'],project_path('', f"reports/eda_independiente/k2021/figuras/{s['fuente']}/{name}.png"))
        strict_json(s,project_path('', f"reports/eda_independiente/k2021/{s['fuente']}_resultados.json"))
    for pair in data['comparaciones_derivado_imputado']:
        pair['unidad']=component_unit(pair['componente'])
    assert numbers(data)==before
    strict_json(data,path)
    contracts_path=project_path('', 'docs/eda/contratos_k2021.json')
    contracts=json.loads(read_project_text(contracts_path))
    for c in contracts['contratos']:
        result=next(s for s in data['fuentes'] if s['fuente']==c['fuente'])['resultados'][c['variable']]
        c.update(result['contrato'])
    strict_json(contracts,contracts_path)
    report_path=project_path('', 'docs/eda/B02A_K_2021.md')
    text=read_project_text(report_path).replace('flujo anual construido, consumo mensual','montos mensuales documentados, salario de periodicidad pendiente, montos totales recibidos, consumo mensual')
    text=text.replace('Los montos K101/K103 son mensuales; no se confunden con flujos anuales de las pensiones ordinarias.',
        'K101/K103 y los montos ordinarios K61/K67 son mensuales según preguntas y asignaciones del apéndice. “Durante el año pasado” es ventana de recepción, no factor automático de anualización.')
    # Actualiza la columna de unidades del cotejo, preservando números y texto restante.
    for base in [p['componente'] for p in data['comparaciones_derivado_imputado']]:
        text=text.replace(f'| {base} | pesos, flujo anual construido |',f'| {base} | {component_unit(base)} |')
    write_project_text(report_path, text)
    print(f'Precisados {changed} metadatos/figuras; SHA de todas las tablas numéricas invariable: {before}')


if __name__=='__main__':
    refresh()
