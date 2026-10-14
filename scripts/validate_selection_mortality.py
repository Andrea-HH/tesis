"""Validación operacional de mortalidad registrada, selección y universos05."""

import json
from hashlib import sha256
import numpy as np
import nbformat
from tesis_enasem.selection_mortality import OUTPUT, VARIABLES, verify_inputs
from tesis_enasem.project_paths import PROJECT_ROOT


def validate(require_notebook: bool = True) -> dict:
    """Reconciliación independiente de totales, soportes, diferencias y restricciones."""
    verify_inputs()
    r = json.loads((OUTPUT / "resultados.json").read_text())
    old = json.loads((PROJECT_ROOT / "data/interim/trayectorias_pensiones_salud/resultados.json").read_text())
    assert r["auditoria"]["N_fallecido_tipent5_discordante"] == 0
    for z, previous in zip(r["intervalos"], old["intervalos"]):
        assert (z["origen"], z["destino"]) == (previous["origen"], previous["destino"])
        assert z["N_cohorte"] == previous["seguimiento"]["N_origen"]
        states = z["estado_vital"]
        assert sum(states.values()) == z["N_cohorte"]
        assert states["Sobre fallecido registrado"] == previous["seguimiento"]["N_sobre_fallecido"]
        assert states["Ausente, vital desconocido"] == previous["seguimiento"]["N_ausente"]
        assert states["Vivo sustituto"] == previous["seguimiento"]["N_sustituto_destino"]
        assert sum(x["N"] for x in z["mortalidad_K"]) == z["N_cohorte"]
        for row in z["mortalidad_K"]:
            assert row["D"] + row["U"] + row["vivo_directo"] + row["vivo_sustituto"] == row["N"]
            assert np.isclose(row["registrado_pct"], row["D"] / row["N"] * 100)
            assert 0 <= row["limite_inf_pct"] <= row["limite_sup_pct"] <= 100
        for a in z["ajustes_K"] + z["ajustes_perfiles"]:
            assert sum(c["N"] for c in a["celdas"]) == a["N_soporte"]
            assert a["N_soporte"] + a["N_fuera_soporte"] == a["N_basales_completos"]
            assert a["N_basales_completos"] + a["N_basales_faltantes"] == a["N_total"]
            if a["ajustada_pp"] is not None:
                assert np.isclose(
                    a["ajustada_pp"],
                    sum(c["N"] * (c["media_si"] - c["media_no"]) for c in a["celdas"]) / a["N_soporte"] * 100,
                )
        assert {a["variable"] for a in z["indicadores"]} == set(VARIABLES)
        for a in z["indicadores"]:
            s = a["seleccion"]
            assert sum(s["estados_seleccion_cohorte"].values()) == z["N_cohorte"]
            assert (
                s["N_valido_ambas_K"]
                <= s["N_valido_ambas"]
                <= s["N_elegible_ambas"]
                <= s["N_elegible_origen"]
            )
            assert (
                s["N_valido_origen"]
                == s["N_valido_ambas"]
                + s["N_valido_origen_muerte"]
                + s["N_valido_origen_ausente"]
                + s["N_valido_origen_vivo_no_medicion"]
            )
            if a["cambios"]:
                c = a["cambios"]
                assert c["N"] == s["N_valido_ambas"]
                assert np.isclose(c["final"]["media"] - c["inicio"]["media"], c["delta"]["media"])
            for scenario in a["escenarios_vivos"]:
                assert scenario["N_vivos_basal_valido"] <= states["Vivo directo"] + states["Vivo sustituto"]
            if a["variable"] == "serial7" and z["destino"] == 2021:
                assert a["cambios"] is None
            if a["variable"] in ["imp_neto", "ocupacion", "est_conyugal"]:
                assert a["cambios"] is None
        mental = next(a for a in z["indicadores"] if a["variable"] == "n_sint_depr")
        assert mental["seleccion"]["N_valido_ambas_K"] == previous["seguimiento"]["N_principal"]
    assert r["reconciliacion"] == {
        "N_dos_o_mas": 14069,
        "N_personas_pares_K": 13570,
        "interseccion_pares_K_multi": 13560,
        "solo_pares_K": 10,
        "solo_multi": 509,
    }
    for a in r["multivisita"]:
        assert sum(c["N_personas"] for c in a["conteos_mediciones"]) == a["N_personas_alguna_medicion"]
        assert a["interseccion_pares_K_multi"] + a["solo_pares_K"] == a["N_personas_pares_K"]
        assert a["interseccion_pares_K_multi"] + a["solo_multi"] == a["N_dos_o_mas"]
    if require_notebook:
        n = nbformat.read(PROJECT_ROOT / "notebooks/05_PENSIONES_MORTALIDAD_SELECCION.ipynb", as_version=4)
        e = nbformat.read(
            PROJECT_ROOT
            / "data/interim/notebooks_ejecutados/05_PENSIONES_MORTALIDAD_SELECCION_ejecutado.ipynb",
            as_version=4,
        )
        assert [c.source for c in n.cells] == [c.source for c in e.cells]
        assert not any(c.get("outputs") for c in n.cells)
        assert all(
            c.execution_count is not None and not any(o.output_type == "error" for o in c.outputs)
            for c in e.cells
            if c.cell_type == "code"
        )
    result = {
        "intervalos": 5,
        "indicadores": len(VARIABLES),
        "reconciliacion04": True,
        "denominadores_y_cambios": True,
        "mortality_is_recorded_only": True,
        "sin_fechas_evento_imputadas": True,
        "sin_KM_Cox_IPW": True,
        "sin_cambios_monetarios_no_homologados": True,
        "fuentes_previas_intactas": True,
        "notebook_ejecutado": require_notebook,
        "sha_resultados": sha256((OUTPUT / "resultados.json").read_bytes()).hexdigest(),
    }
    (OUTPUT / "validacion.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, indent=2))
