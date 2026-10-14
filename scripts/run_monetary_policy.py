"""Calcula solamente07 desde insumos auditados; no recalcula notebooks anteriores."""

from hashlib import sha256

from tesis_enasem.monetary_policy import OUTPUT, analyze, save_json, verify_inputs
from tesis_enasem.project_paths import PROJECT_ROOT

if __name__ == "__main__":
    r=analyze()
    save_json(OUTPUT / "resultados.json",r)
    save_json(OUTPUT / "manifest.json",dict(insumos_protegidos=verify_inputs(),
        sha_resultados=sha256((OUTPUT/"resultados.json").read_bytes()).hexdigest(),
        codigo={str(p.relative_to(PROJECT_ROOT)):sha256(p.read_bytes()).hexdigest() for p in
                [PROJECT_ROOT/"src/tesis_enasem/monetary_policy.py",PROJECT_ROOT/"scripts/run_monetary_policy.py"]}))
    for z in r["montos"]:
        if z["dimension"]=="General":
            print(z["ronda"],z["via"],z["N_monto"],z["persona"]["nominal"]["mediana"],z["persona"]["real"]["mediana"],z["persona"]["lpi_pct"]["mediana"])
