"""Ejecuta exclusivamente la ampliación de cobertura económica06."""

from hashlib import sha256

from tesis_enasem.economic_protection import OUTPUT, analyze, save_json, verify_inputs
from tesis_enasem.project_paths import PROJECT_ROOT

if __name__ == "__main__":
    from tesis_enasem.release_guard import block_legacy_export
    block_legacy_export()
    r = analyze()
    save_json(OUTPUT / "resultados.json", r)
    save_json(
        OUTPUT / "manifest.json",
        {
            "insumos_protegidos": verify_inputs(),
            "sha_resultados": sha256((OUTPUT / "resultados.json").read_bytes()).hexdigest(),
            "codigo": {
                str(p.relative_to(PROJECT_ROOT)): sha256(p.read_bytes()).hexdigest()
                for p in [
                    PROJECT_ROOT / "src/tesis_enasem/economic_protection.py",
                    PROJECT_ROOT / "scripts/run_economic_protection.py",
                ]
            },
        },
    )
    for z in r["rondas"]:
        if z["analisis"] == "principal":
            c = z["cobertura"][0]
            print(z["ronda"], {k: c[k] for k in ["N_60", "N_elegible", "N_KA_conocido", "N_KA_si", "KA_pct"]})
