"""Calcula exclusivamente la ampliación05 con fuentes previamente integradas."""

import json
from tesis_enasem.selection_mortality import OUTPUT, analyze, verify_inputs

if __name__ == "__main__":
    from tesis_enasem.release_guard import block_legacy_export
    block_legacy_export()
    verify_inputs()
    r = analyze()
    (OUTPUT / "resultados.json").write_text(
        json.dumps(r, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    )
    verify_inputs()
    print(r["reconciliacion"])
