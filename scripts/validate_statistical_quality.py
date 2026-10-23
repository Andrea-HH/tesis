"""Revalida fuentes y cálculos sin sobrescribir certificaciones originales09."""
import json
import runpy
from pathlib import Path
from tesis_enasem.statistical_quality import ROOT, OUT, ORIGINAL, digest
from tesis_enasem.economic_protection import save_json


def main():
    state=json.loads((OUT/'instantanea.json').read_text())
    for name,metadata in state['archivos'].items():
        assert digest(ORIGINAL/name)==metadata['sha256'],name
        if name.startswith('data/interim/'):
            assert digest(ROOT/name)==metadata['sha256'],name
    audit=json.loads((OUT/'privado/auditoria.json').read_text())
    for row in audit['embudos_contrastes']:
        previous=row['N_estrato_basal']
        for step in row['embudo']:
            n=step['N_observaciones']
            assert n<=previous and previous-n==step['N_excluidas_en_paso']
            assert n==step['N_personas_unicas']
            previous=n
        assert previous==row['N_monto']
        assert row['N_monto']+row['N_monto_faltante']==row['N_receptores']
    assert len(audit['embudos_contrastes'])==336
    for row in audit['union_robustez']:
        assert row['N_incorporados']==2188 and row['N_observados']==3846
    module=runpy.run_path(str(ROOT/'scripts/validate_central_analysis.py'))
    validate=module['main']
    validate.__globals__['save_json']=lambda path,data:save_json(OUT/'privado/revalidacion_central09.json',data)
    validate()
    result={'estado':'Verificado','embudos':336,'instantanea_original':len(state['archivos']),
            'sha_auditoria':digest(OUT/'privado/auditoria.json'),
            'nota':'Revalidación independiente09 y conservación de agregados originales; no equivale a validar cada variable del proveedor ni el anonimato universal.'}
    save_json(OUT/'validacion_calidad.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
