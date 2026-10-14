"""Ejecuta08 desde fuentes locales existentes, sin recalcular01–07."""

from hashlib import sha256
import argparse

from tesis_enasem.benefit_transitions import OUTPUT, analyze, analyze_precision, validate_precision, save_json, verify_inputs
from tesis_enasem.project_paths import PROJECT_ROOT

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--precision',action='store_true',help='Validación seleccionada sin sobrescribir resultados08.')
    parser.add_argument('--replicas',type=int,default=9999)
    parser.add_argument('--seed',type=int,default=20261014)
    args=parser.parse_args()
    if args.precision:
        import platform
        import numpy as np
        import scipy
        r=analyze_precision(replicas=args.replicas,seed=args.seed)
        validate_precision(r)
        save_json(OUTPUT/'precision.json',r)
        save_json(OUTPUT/'precision_manifest.json',dict(
            sha_precision=sha256((OUTPUT/'precision.json').read_bytes()).hexdigest(),
            python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,
            replicas=args.replicas,seed=args.seed,
            fuentes={name:sha256((OUTPUT/name).read_bytes()).hexdigest() for name in ['resultados.json','auditoria.json','insumos_protegidos.json']},
            codigo={str(p.relative_to(PROJECT_ROOT)):sha256(p.read_bytes()).hexdigest() for p in
                    [PROJECT_ROOT/'src/tesis_enasem/benefit_transitions.py',PROJECT_ROOT/'scripts/run_benefit_transitions.py']}))
        for z in r['ventanas']:
            for x in z['principal']['estimaciones']:
                if x['id'] in ['new_minus_cont_real','median_change_principal','ss_new_minus_cont_real','adjusted_new_minus_cont_real']:
                    print(z['via'],x['id'],round(x['estimacion'],3),[round(v,3) for v in x['ic95']],flush=True)
        raise SystemExit(0)
    r=analyze()
    save_json(OUTPUT/'resultados.json',r)
    save_json(OUTPUT/'manifest.json',dict(insumos_protegidos=verify_inputs(),
        sha_resultados=sha256((OUTPUT/'resultados.json').read_bytes()).hexdigest(),
        codigo={str(p.relative_to(PROJECT_ROOT)):sha256(p.read_bytes()).hexdigest() for p in
                [PROJECT_ROOT/'src/tesis_enasem/benefit_transitions.py',PROJECT_ROOT/'scripts/run_benefit_transitions.py']}))
    for z in r['analisis']:
        print(z['origen'],z['destino'],z['via'],'pares íntegros',z['pares']['N'],
              'mediana cambio real',z['pares']['cambio_individual_real']['mediana'],
              'ajuste viable',z['ajuste']['viable'])

