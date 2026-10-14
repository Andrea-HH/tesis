"""Verifica la ampliación salud: cobertura, efectos agregados, notebook y entradas intactas."""
from pathlib import Path
from hashlib import sha256
import json
import numpy as np
import nbformat
from tesis_enasem.pension_health import OUTPUT,verify_frozen_inputs,BINARY
from tesis_enasem.project_paths import PROJECT_ROOT


def validate() -> dict:
    """Coteja agregados y frecuencias, sin reconstruir bases o recalcular el EDA."""
    verify_frozen_inputs();r=json.loads((OUTPUT/'resultados.json').read_text())
    assert r['metodologia']['N_persona_ronda']==56004 and r['metodologia']['N_personas']==18754
    assert len(r['principal'])==80 and len(r['reutilizados'])==30
    old=json.loads((PROJECT_ROOT/'data/interim/eda_pensionaria/salud_complementaria.json').read_text())
    assert r['reutilizados']==old,'Correlaciones anteriores cambiadas'
    assert r['calidad']['CESD_bandera_conteo_discordantes']==0
    assert len({(x['ano'],x['variable']) for x in r['principal']})==80
    for c in r['cobertura']:
        if c['N_elegible'] is not None:
            assert c['N_elegible']+c['N_fuera_universo']==c['N_total_60']
            assert c['N_elegible']==c['N_valido']+c['N_NR_NS']+c['N_fuera_dominio']+c['N_otros_faltantes']
    for x in r['principal']:
        assert x['N_pares_validos']==x['N_si_valido']+x['N_no_valido']
        groups={v['grupo']:v for v in x['distribuciones']}
        assert sum(g['N_elegible_grupo'] for g in groups.values())==x['N_elegible']
        assert sum(g['N_valido'] for g in groups.values())==x['N_salud_valido']
        for group in groups.values():assert sum(v['N'] for v in group['frecuencias'])==group['N_valido']
        a={v['valor']:v['N'] for v in groups['True']['frecuencias']}
        b={v['valor']:v['N'] for v in groups['False']['frecuencias']}
        if x['variable'] in BINARY:
            expected=100*(a.get(1,0)/x['N_si_valido']-b.get(1,0)/x['N_no_valido'])
        else:
            support=sorted(set(a)|set(b));left=np.array([a.get(v,0) for v in support]);right=np.array([b.get(v,0) for v in support])
            expected=2*(left*(np.cumsum(right)-.5*right)).sum()/(left.sum()*right.sum())-1
        assert np.isclose(x['efecto'],expected),x['variable']
        bound=100 if x['variable'] in BINARY else 1
        if x['ic95_inferior'] is not None:assert -bound<=x['ic95_inferior']<=x['ic95_superior']<=bound
    for x in r['trivariados']:
        if x.get('efecto') is not None:assert min(x['N_si_valido'],x['N_no_valido'])>=30
        if x['estrato']=='Desconocido':assert x['efecto'] is None
        assert x['N_pares_validos']==x['N_si_valido']+x['N_no_valido']
    for x in r['complementarios']:
        if x['recepcion']=='pension_conyuge_k':assert x['ano'] in [2018,2021]
    for x in r['estandarizados']:
        if x['N_soporte']:
            assert sum(c['N'] for c in x['celdas'])==x['N_soporte']
            assert all(min(c['N_si'],c['N_no'])>=20 for c in x['celdas'])
    source=PROJECT_ROOT/'notebooks/03_PENSIONES_SALUD_COGNICION.ipynb'
    manifest=json.loads((OUTPUT/'manifest.json').read_text())
    assert sha256(source.read_bytes()).hexdigest()==manifest['notebook_fuente_sha256']
    nb=nbformat.read(source,as_version=4);nbformat.validate(nb)
    assert all(not c.get('outputs') and c.get('execution_count') is None for c in nb.cells if c.cell_type=='code')
    executed=nbformat.read(PROJECT_ROOT/'data/interim/notebooks_ejecutados/03_PENSIONES_SALUD_COGNICION_ejecutado.ipynb',as_version=4)
    assert [c.source for c in executed.cells]==[c.source for c in nb.cells]
    assert all(c.execution_count is not None for c in executed.cells if c.cell_type=='code')
    assert not any(o.output_type=='error' for c in executed.cells if c.cell_type=='code' for o in c.outputs)
    evidence={'contrastes_principales':80,'correlaciones_previas_reutilizadas':30,
              'trivariados_estimables':sum(x.get('efecto') is not None for x in r['trivariados']),
              'complementarios':len(r['complementarios']),'cobertura_contratos_verificada':True,
              'efectos_reconciliados_con_frecuencias':True,'notebook_ejecutado_sin_errores':True,
              'entradas_previas_intactas':True,'sin_modelos_predictivos':True}
    (OUTPUT/'validacion.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(evidence,ensure_ascii=False,indent=2));return evidence


if __name__=='__main__':validate()
