"""Reconciliación de personas, lógica trivalente, eventos y estimandos06."""

import json
from hashlib import sha256

import nbformat
import numpy as np

from tesis_enasem.economic_protection import GROUPS, NOTEBOOK, OUTPUT, save_json, verify_inputs
from tesis_enasem.project_paths import PROJECT_ROOT


def validate(require_notebook: bool = True) -> dict:
    """Valida agregados completos y ejecución sin asumir que ND sea negativa."""
    protected = verify_inputs()
    r = json.loads((OUTPUT / "resultados.json").read_text())
    assert r["metodologia"]["N_personas_ronda_60"] == 56004
    assert r["metodologia"]["N_personas_60"] == 18754
    assert not r["metodologia"]["deflactacion_ejecutada"]
    for z in r["rondas"]:
        general = z["cobertura"][0]
        for c in z["cobertura"]:
            assert c["N_KA_si"] + c["N_KA_no"] == c["N_KA_conocido"]
            assert c["N_KA_conocido"] + c["N_KA_ND_elegible"] == c["N_elegible"]
            assert c["N_K_A_conocidas"] <= c["N_KA_conocido"]
            assert c["N_KA_si"] >= max(c["N_K_si"], c["N_A_si"])
            for key in ["K", "A", "KA"]:
                assert c[f"N_{key}_conocido"] + c[f"N_{key}_ND_elegible"] == c["N_elegible"]
            assert np.isclose(c["KA_pct"], 100 * c["N_KA_si"] / c["N_KA_conocido"])
            if z["analisis"] == "principal":
                assert c["N_elegible"] + c["N_sustituto"] == c["N_60"]
            else:
                assert c["N_elegible"] == c["N_60"]
        for dim in GROUPS:
            assert sum(x["N_60"] for x in z["cobertura"] if x["dimension"] == dim) == general["N_60"]
        if z["ronda"] in [2018, 2021]:
            for dim in ["General", *GROUPS]:
                rows = [x for x in z["tipologia"] if x["dimension"] == dim]
                assert sum(x["N"] for x in rows) == general["N_60"]
                if z["analisis"] == "principal":
                    assert (
                        sum(x["N"] for x in rows if x["categoria"].startswith("Sustituto"))
                        == general["N_sustituto"]
                    )
            known = [
                x
                for x in z["tipologia"]
                if x["dimension"] == "General"
                and x["contexto"] == "Pareja confirmada"
                and x["pct_contexto_conocido"] is not None
            ]
            assert len(known) == 8
            assert np.isclose(sum(x["pct_contexto_conocido"] for x in known), 100)
    for x in r["montos"]:
        assert x["N_eventos_monto"] + x["N_eventos_ND"] == x["N_eventos"]
        assert x["N_personas_monto"] + x["N_receptores_sin_monto"] == x["N_receptores"]
        assert x["N_personas_eventos"] == x["N_receptores"]
        assert (
            x["N_personas_todos_eventos_capturados_con_monto"] + x["N_personas_eventos_parciales"]
            == x["N_personas_monto"]
        )
        for key in [
            "por_evento",
            "suma_personal_observada_parcial",
            "suma_personal_todos_eventos_capturados",
        ]:
            a = x[key]
            if a["N"]:
                assert a["q10"] <= a["q25"] <= a["mediana"] <= a["q75"] <= a["q90"]
    old = json.loads((PROJECT_ROOT / "data/interim/trayectorias_pensiones_salud/resultados.json").read_text())
    for mode in ["seguimiento_principal", "seguimiento_sensibilidad_sustitutos"]:
        for z in r[mode]:
            previous = next(v for v in old["intervalos"] if v["origen"] == z["origen"])
            assert z["N_cohorte_60"] == previous["seguimiento"]["N_origen"]
            for x in z["grupos"]:
                s = x["estados_sin_K_basal"]
                c = x["cotas"]
                assert sum(s.values()) == x["N_K_basal_no"] == c["N"]
                assert x["N_K_basal_no"] + x["N_K_basal_si"] + x["N_K_basal_ND"] == x["N_cohorte_60"]
                assert (
                    c["N_K_destino_conocido_vivo"]
                    == s["Sigue con negativa K"] + s["Recepción K observada en destino"]
                )
                if c["N"]:
                    assert 0 <= c["persistencia_min_pct"] <= c["persistencia_max_pct"] <= 100
                    assert (
                        c["persistencia_max_pct"]
                        <= 100 * (c["N"] - s["Fallecido registrado"]) / c["N"] + 1e-9
                    )
            for dim in GROUPS:
                assert (
                    sum(x["N_K_basal_no"] for x in z["grupos"] if x["dimension"] == dim)
                    == z["grupos"][0]["N_K_basal_no"]
                )
    if require_notebook:
        source = nbformat.read(PROJECT_ROOT / "notebooks" / NOTEBOOK, as_version=4)
        executed = nbformat.read(
            PROJECT_ROOT
            / "data/interim/notebooks_ejecutados"
            / NOTEBOOK.replace(".ipynb", "_ejecutado.ipynb"),
            as_version=4,
        )
        assert [c.source for c in source.cells] == [c.source for c in executed.cells]
        assert all(not c.get("outputs") for c in source.cells)
        assert all(
            c.execution_count is not None and all(o.output_type != "error" for o in c.outputs)
            for c in executed.cells
            if c.cell_type == "code"
        )
    result = {
        "fuentes_protegidas": protected,
        "rondas": 6,
        "tipologia_exhaustiva": True,
        "denominadores_reconciliados": True,
        "montos_separados_evento_persona": True,
        "ventanas": 3,
        "sin_deflactacion": True,
        "sin_modelos_opcionales": True,
        "notebook_ejecutado": require_notebook,
        "sha_resultados": sha256((OUTPUT / "resultados.json").read_bytes()).hexdigest(),
    }
    save_json(OUTPUT / "validacion.json", result)
    return result


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, indent=2))
