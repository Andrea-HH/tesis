"""Ejecuta solo la ampliación autorizada de pensiones y salud; no reconstruye bases."""
import argparse
import json
import time

from tesis_enasem.pension_health import OUTPUT,analyze,verify_frozen_inputs

if __name__=='__main__':
    from tesis_enasem.release_guard import block_legacy_export
    block_legacy_export()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bootstrap',type=int,default=999)
    args=parser.parse_args()
    verify_frozen_inputs();start=time.monotonic()
    results=analyze(args.bootstrap)
    OUTPUT.mkdir(exist_ok=True,parents=True)
    (OUTPUT/'resultados.json').write_text(json.dumps(results,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    verify_frozen_inputs()
    print(f"Ampliación ejecutada en {time.monotonic()-start:.1f}s: {len(results['principal'])} contrastes principales; anteriores intactos.")
