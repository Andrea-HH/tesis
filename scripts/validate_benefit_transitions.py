"""Cotejo08 de insumos, cardinalidad, estados y cálculos monetarios."""

import json
import argparse
from hashlib import sha256

from tesis_enasem.benefit_transitions import OUTPUT, validate, validate_precision, verify_inputs
from tesis_enasem.monetary_policy import sources


def check() -> None:
    """Valida resultados guardados y su huella, sin recalcular etapas anteriores."""
    r=json.loads((OUTPUT/'resultados.json').read_text())
    validate(r);sources()
    m=json.loads((OUTPUT/'manifest.json').read_text())
    assert m['sha_resultados']==sha256((OUTPUT/'resultados.json').read_bytes()).hexdigest()
    for z in r['analisis']:
        a=next(a for a in r['auditoria']['intervalos'] if (a['origen'],a['destino'],a['via'])==(z['origen'],z['destino'],z['via']))
        assert a['N_pares_todos_capturados']==z['pares']['N']
        assert z['otra_via_previa']['N_nuevos']==sum(x for k,x in z['otra_via_previa'].items() if k!='N_nuevos')
        for g in z['montos_por_perfil']:
            for unit in ['nominal','real']:
                s=g[unit]
                assert s['p10']<=s['q25']<=s['mediana']<=s['q75']<=s['p90']
    print('08 validado:',len(r['transiciones']),'intervalos/vía;',
          [z['pares']['N'] for z in r['analisis']],'pares monetarios íntegros;',verify_inputs(),'archivos intactos')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--precision',action='store_true')
    args=parser.parse_args()
    check()
    if args.precision:
        r=json.loads((OUTPUT/'precision.json').read_text())
        validate_precision(r)
        m=json.loads((OUTPUT/'precision_manifest.json').read_text())
        assert sha256((OUTPUT/'precision.json').read_bytes()).hexdigest()==m['sha_precision']
        for name,expected in m['fuentes'].items():
            assert sha256((OUTPUT/name).read_bytes()).hexdigest()==expected,name
        from tesis_enasem.project_paths import PROJECT_ROOT
        for name,expected in m['codigo'].items():
            assert sha256((PROJECT_ROOT/name).read_bytes()).hexdigest()==expected,name
        print('Precisión validada: puntos previos conciliados; IC por ID y folio;',r['metodologia']['replicas'],'réplicas por escenario; sin modificar01–08.')
