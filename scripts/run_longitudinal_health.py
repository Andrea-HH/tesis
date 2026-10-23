"""Ejecuta el análisis longitudinal descriptivo autorizado, sin modificar bases."""

import json
from tesis_enasem.longitudinal_health import analyze, OUTPUT, verify_inputs

if __name__ == "__main__":
    from tesis_enasem.release_guard import block_legacy_export
    block_legacy_export()
    verify_inputs(allow_report=True)
    results = analyze()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "resultados.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    )
    verify_inputs(allow_report=True)
    print(results["metodologia"])
