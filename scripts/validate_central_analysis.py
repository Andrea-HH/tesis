"""Comprueba09 mediante máscaras directas independientes y huellas privadas."""
from __future__ import annotations
import json
import numpy as np
from tesis_enasem.central_analysis import OUTPUT,load,pair_frame,GATES,FIRST,OTHER,CONT,validate,fingerprint
from tesis_enasem.economic_protection import save_json
from tesis_enasem.project_paths import PROJECT_ROOT as ROOT

def main() -> None:
    r=json.loads((OUTPUT/'resultados.json').read_text());validate(r);f,_=load();checks=0;sets={}
    assert len(f)==99676 and f.id.nunique()==27171
    assert int(f.universo_60.sum())==56004 and f.loc[f.universo_60].id.nunique()==18754
    for w in r['ventanas']:
        a,b,via=w['origen'],w['destino'],w['via'];p=pair_frame(f,a,b);gate=GATES[via];other=GATES['A' if via=='K' else 'K']
        direct=p.tipent_b.isin([1,2])&~(p.vital_discordante_a|p.vital_discordante_b).fillna(False)
        new=direct&p[gate+'_a'].eq(False).fillna(False)&p[gate+'_b'].eq(True).fillna(False)
        first=new&p[other+'_a'].eq(False).fillna(False);extra=new&p[other+'_a'].eq(True).fillna(False)
        masks={FIRST:first,OTHER:extra,CONT:direct&p[gate+'_a'].eq(True).fillna(False)&p[gate+'_b'].eq(True).fillna(False)}
        assert sum(x['N'] for x in w['composicion'])==int(new.sum());checks+=1
        for group,mask in masks.items():
            z=next(g for g in w['grupos'] if g['grupo']==group);assert z['N']==int(mask.sum());checks+=1
            vals=(p['monto_completo_'+via+'_b']*p.factor_b).loc[mask].dropna().to_numpy(dtype=float)
            for key,prob in [('q25',.25),('mediana',.5),('q75',.75)]:
                assert np.isclose(z['monto_real'][key],np.quantile(vals,prob));checks+=1
        risk=p.pension_propia_k_a.eq(False).fillna(False)&p.apoyo_propio_a.eq(False).fillna(False)
        obs=risk&direct&p[gate+'_b'].notna();o=w['riesgo'][0]['observada']
        assert o['N_denominador']==int(obs.sum()) and o['N_incorporados']==int(first.sum());checks+=1
        for c in w['contrastes']:
            if c['estimacion'] is None:continue
            vals=[]
            for g in c['grupos']:
                vals.append(float(p.loc[masks[g],c['campo']].dropna().median()) if c['campo']!='monto_real' else float((p['monto_completo_'+via+'_b']*p.factor_b).loc[masks[g]].dropna().median()))
            assert np.isclose(c['estimacion'],vals[0]-vals[1]);checks+=1
        if (a,b)==(2012,2015):sets[via]=set(p.index[first])
    assert len(sets['K']|sets['A'])==r['union']['N_incorporados']
    assert len(sets['K']&sets['A'])==r['union']['N_inicia_ambas'];checks+=2
    m=json.loads((OUTPUT/'manifest.json').read_text());assert fingerprint(OUTPUT/'resultados.json')==m['sha_resultados']
    for name,h in m.get('agregados_previos',{}).items():assert fingerprint(ROOT/name)==h
    save_json(OUTPUT/'validacion.json',dict(estado='Validado',comprobaciones_independientes=checks,fuentes_originales_verificadas=len(r['metadata']['fuentes_verificadas']),universo_maestro=[99676,27171],universo_60=[56004,18754],doble_conteo_union=False,limitaciones='Sin inferencia nacional, causalidad, pobreza o identidad administrativa',sha_resultados=fingerprint(OUTPUT/'resultados.json')))
    print(checks,'comprobaciones numéricas independientes;379 fuentes intactas; unión sin doble conteo.')
if __name__=='__main__':main()
