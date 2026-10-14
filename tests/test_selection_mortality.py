"""Pruebas focalizadas de incertidumbre vital, soporte y selección por dimensión."""

import numpy as np
import pandas as pd
import pytest
from tesis_enasem.selection_mortality import (
    death_bounds,
    vital_state,
    standardize_binary,
    indicator_selection,
)


def test_absence_is_not_alive_or_death():
    p = pd.DataFrame({"presente": [False, True, True, True], "tipent_b": [np.nan, 1, 3, 5]})
    assert vital_state(p).tolist() == [
        "Ausente, vital desconocido",
        "Vivo directo",
        "Vivo sustituto",
        "Sobre fallecido registrado",
    ]


def test_bounds_and_bad_denominators():
    r = death_bounds(10, 20, 100)
    assert r["limite_inf_pct"] == 10 and r["limite_sup_pct"] == 30
    with pytest.raises(ValueError):
        death_bounds(10, 95, 100)


def test_standardization_handles_composition_and_not_survival():
    records = []
    for cell, ny, nn, py, pn in [("A", 80, 20, 0.1, 0), ("B", 20, 80, 0.6, 0.5)]:
        for flag, n, p in [(True, ny, py), (False, nn, pn)]:
            records += [{"cell": cell, "K": flag, "D": int(i < n * p)} for i in range(n)]
    r = standardize_binary(pd.DataFrame(records), "K", "D", ["cell"], 20)
    assert r["N_soporte"] == 200
    assert np.isclose(r["ajustada_pp"], 10)
    assert np.isclose(r["cruda_mismo_soporte_pp"], -20)
    bad = standardize_binary(pd.DataFrame(records), "K", "D", ["cell"], 21)
    assert bad["ajustada_pp"] is None


def test_proxy_can_remain_present_without_cognitive_measurement():
    p = pd.DataFrame(
        {
            "presente": [True, True, False],
            "tipent_b": [3, 5, np.nan],
            "vivo_destino": [True, False, False],
            "K_conocida": [True, False, False],
            "recuerdo1__elegible_a": [True, True, True],
            "recuerdo1_a": [4.0, 2.0, 3.0],
            "recuerdo1__elegible_b": [False, False, np.nan],
            "recuerdo1_b": [np.nan, np.nan, np.nan],
            "recuerdo1_flag_a": [0, 0, 0],
            "recuerdo1_flag_b": [np.nan] * 3,
        }
    )
    p["estado_vital"] = vital_state(p)
    r, paired, groups = indicator_selection(p, "recuerdo1")
    assert paired.sum() == 0
    assert r["N_valido_origen_muerte"] == 1 and r["N_valido_origen_ausente"] == 1
    assert groups.iloc[0] == "Vivo, modalidad no elegible"
    assert r["N_valido_origen_vivo_no_medicion"] == 1
