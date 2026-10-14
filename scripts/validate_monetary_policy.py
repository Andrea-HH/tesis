"""Validaciones sustantivas07, sin modificar bases ni resultados anteriores."""

import json
from hashlib import sha256

from tesis_enasem.monetary_policy import OUTPUT, REFERENCE, REFERENCE_INDEX, sources, verify_inputs


def validate() -> None:
    """Conciliación de cantidades, denominadores, umbrales y datos protegidos."""
    r=json.loads((OUTPUT/'resultados.json').read_text())
    a=json.loads((OUTPUT/'auditoria.json').read_text())
    sources()
    assert r['metodologia']['referencia']==REFERENCE and r['metodologia']['inpc_referencia']==REFERENCE_INDEX
    assert not r['metodologia']['valor_presente_actuarial']
    for z in r['montos']:
        assert z['N_monto']+z['N_receptores_sin_monto']==z['N_receptores']
        assert z['N_monto']==z['persona']['nominal']['N']
        assert z['N_eventos']-z['N_eventos_ND']==z['evento']['nominal']['N']
        assert z['N_todos_eventos_capturados']+z['N_parciales']==z['N_monto']
        assert z['persona']['real']['N']<=z['N_monto']
        assert z['persona']['N_lpi']+z['persona']['N_umbral_ND_monto']==z['N_monto']
        assert z['persona']['N_prestacion_inferior_lpi']<=z['persona']['N_lpi']
        for unit in ['nominal','real']:
            s=z['persona'][unit]
            if s['N']:
                assert s['p10']<=s['q25']<=s['mediana']<=s['q75']<=s['p90']<=s['p95']
    for z in r['seleccion']:
        assert sum(z['estados'].values())==z['N_basal']
        assert z['N_pares_conocidos']<=z['N_basal_recepcion_conocida']
        assert z['N_receptores_ambas_monto']==z['cambio_real_receptores_ambas']['N']
    for z in a['geografia']:
        assert z['N_urbana']+z['N_rural']+z['N_indeterminado']==z['N_directas']
        if z['ronda'] in [2001,2003]:assert z['N_rural']==0
    manifest=json.loads((OUTPUT/'manifest.json').read_text())
    assert manifest['sha_resultados']==sha256((OUTPUT/'resultados.json').read_bytes()).hexdigest()
    print('07 validado:',len(r['montos']),'resúmenes;',len(r['brechas']),'brechas;',verify_inputs(),'insumos intactos')


if __name__=='__main__':
    validate()
