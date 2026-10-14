"""Pruebas sintéticas de desconocidos, partición y cotas de selección06."""

from itertools import product

import pandas as pd
import pytest

from tesis_enasem.economic_protection import (
    NO_PARTNER,
    PARTNER,
    evaluate_sufficiency,
    persistence_bounds,
    typology_row,
    union_receipt,
)


def test_union_unknown_is_not_negative():
    k = pd.Series([True, False, pd.NA, pd.NA, False], dtype="boolean")
    a = pd.Series([pd.NA, pd.NA, True, False, False], dtype="boolean")
    result = union_receipt(k, a)
    assert result.iloc[0] and result.iloc[2]
    assert pd.isna(result.iloc[1]) and pd.isna(result.iloc[3])
    assert not result.iloc[4]


def test_typology_is_exhaustive_and_partner_context_matters():
    row = pd.Series({"titularidad_pareja_estado": PARTNER, "elegible_06": True})
    categories = []
    for k, s, a in product([True, False], repeat=3):
        row["pension_propia_k"], row["pension_conyuge_k"], row["apoyo_propio"] = k, s, a
        categories.append(typology_row(row)[1])
    assert len(set(categories)) == 8
    row["titularidad_pareja_estado"] = NO_PARTNER
    row["pension_propia_k"], row["apoyo_propio"] = False, False
    row["pension_conyuge_k"] = pd.NA
    assert typology_row(row)[1] == "Negativas propias K y A; sin pareja residente"
    row["titularidad_pareja_estado"] = "puntero_pareja_ausente_o_discreprante"
    assert typology_row(row)[1].startswith("ND")
    row["elegible_06"] = False
    assert typology_row(row)[1].startswith("Sustituto")


def test_bounds_do_not_assign_future_pensions_to_registered_dead():
    r = persistence_bounds(40, 20, 15, 10, 15)
    assert r["persistencia_observados_K_pct"] == pytest.approx(100 * 40 / 60)
    assert r["persistencia_min_pct"] == 40
    assert r["persistencia_max_pct"] == 65
    assert r["recepcion_max_pct"] == 45
    assert r["mortalidad"]["limite_sup_pct"] == 25


def test_deflation_blocks_unconfirmed_sources():
    with pytest.raises(ValueError, match="bloqueada"):
        evaluate_sufficiency(pd.Series([1000.0]), pd.Series([2021]), {"fuente_indice_confirmada": False})
    config = {
        "fuente_indice_confirmada": True,
        "fuente_umbral_confirmada": True,
        "ronda_base": 2021,
        "INPC_por_ronda": {2021: 100},
        "umbral_mensual_nominal_por_ronda": {},
    }
    with pytest.raises(ValueError, match="Faltan"):
        evaluate_sufficiency(pd.Series([1000.0]), pd.Series([2021]), config)
