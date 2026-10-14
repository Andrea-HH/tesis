"""Reconciliación de matrices, cambios pareados, panel incompleto y archivos previos."""

import json
from hashlib import sha256
import numpy as np
import nbformat
from tesis_enasem.longitudinal_health import OUTPUT, verify_inputs
from tesis_enasem.project_paths import PROJECT_ROOT


def validate() -> dict:
    """Verifica todas las sumas y fuentes/ejecución, sin inferencia añadida."""
    verify_inputs(allow_report=True)
    r = json.loads((OUTPUT / "resultados.json").read_text())
    assert [(z["origen"], z["destino"]) for z in r["intervalos"]] == [
        (2001, 2003),
        (2003, 2012),
        (2012, 2015),
        (2015, 2018),
        (2018, 2021),
    ]
    for a in r["auditoria_CESD"]:
        assert a["N_discordancias_completos"] == 0
        assert a["N_score_valido_componentes_incompletos"] == a["N_parciales_igual_suma_disponible"]
        assert a["N_nueve_completos"] + a["N_score_valido_componentes_incompletos"] == a["N_score_proveedor"]
    for z in r["intervalos"]:
        f = z["seguimiento"]
        assert f["N_presente"] + f["N_ausente"] == f["N_origen"]
        assert f["N_vivo_destino"] + f["N_sobre_fallecido"] == f["N_presente"]
        assert sum(x["N"] for x in z["seleccion"]) == f["N_origen"]
        assert f["N_principal"] <= f["N_proveedor"] <= f["N_K_conocida_ambas_vivas"]
        assert f["N_principal"] <= f["N_sintomas_nueve_validos_ambas"] <= f["N_directas_ambas"]
        for key, n in [
            ("matriz_K_vivos", f["N_K_conocida_ambas_vivas"]),
            ("matriz_K_principal", f["N_principal"]),
        ]:
            assert sum(x["N"] for x in z[key]) == n
            for origin in ["No", "Sí"]:
                rows = [x for x in z[key] if x["origen"] == origin]
                assert sum(x["N"] for x in rows) == rows[0]["N_origen"]
                if rows[0]["N_origen"]:
                    assert np.isclose(sum(x["pct_fila"] for x in rows), 100)
        changes = [z["cambios"], *z["por_transicion"]]
        for c in changes:
            n = c["cambio"]["N"]
            frequencies = c["cambio"]["frecuencias"]
            assert sum(v["N"] for v in frequencies) == n
            assert np.isclose(sum(v["N"] * v["valor"] for v in frequencies) / n, c["cambio"]["media"])
            assert np.isclose(c["final"]["media"] - c["inicio"]["media"], c["cambio"]["media"])
            assert c["N_aumenta"] + c["N_disminuye"] + c["N_igual"] == n
        assert sum(g["N"] for g in z["por_transicion"]) == f["N_principal"]
        for a in z["ajustes"]:
            assert sum(c["N"] for c in a["celdas"]) == a["N_soporte"]
            assert a["N_soporte"] + a["N_fuera_soporte"] == a["N_casos_completos"]
            assert a["N_casos_completos"] + a["N_basales_faltantes"] == a["N_total_dos_ramas"]
            assert all(min(c["N_grupo"], c["N_referencia"]) >= a["minimo_celda"] for c in a["celdas"])
            if a["ajustada"] is not None:
                assert np.isclose(
                    sum(c["N"] * c["diferencia"] for c in a["celdas"]) / a["N_soporte"], a["ajustada"]
                )
        for a in z["soledad"]:
            assert sum(c["N"] for c in a["matriz"]) == a["N"]
    m = r["multivisita"]
    assert m["N_personas_60"] == 18754
    for variable in ["N_visitas", "N_sintomas", "N_conjuntas", "N_solo"]:
        assert sum(x["N_personas"] for x in m["conteos_visitas"] if x["tipo"] == variable) == 18754
    n = sum(x["N_personas"] for x in m["conteos_visitas"] if x["tipo"] == "N_sintomas" and x["visitas"] >= 2)
    assert sum(m["patrones_sintomas"].values()) == n
    assert sum(x["N_personas"] for x in m["relacion_K_sintomas"]) == n
    assert sum(x["N_personas"] for x in m["patrones_observacion"]) == 18754
    source = nbformat.read(PROJECT_ROOT / "notebooks/04_TRAYECTORIAS_PENSIONES_SALUD.ipynb", as_version=4)
    executed = nbformat.read(
        PROJECT_ROOT / "data/interim/notebooks_ejecutados/04_TRAYECTORIAS_PENSIONES_SALUD_ejecutado.ipynb",
        as_version=4,
    )
    assert [c.source for c in source.cells] == [c.source for c in executed.cells]
    assert not any(c.get("outputs") for c in source.cells)
    code = [c for c in executed.cells if c.cell_type == "code"]
    assert all(c.execution_count is not None for c in code)
    assert not any(o.output_type == "error" for c in code for o in c.outputs)
    result = {
        "intervalos": 5,
        "auditoria_nueve_componentes": True,
        "matrices_y_cambios_reconciliados": True,
        "panel_incompleto_validado": True,
        "notebook_desde_cero": True,
        "N_pares": r["metodologia"]["N_pares_principales"],
        "N_personas_pares": r["metodologia"]["N_personas_distintas_pares"],
        "archivos_previos_intactos": True,
        "sha_resultados": sha256((OUTPUT / "resultados.json").read_bytes()).hexdigest(),
    }
    (OUTPUT / "validacion.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, indent=2))
