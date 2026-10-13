"""Barreras semánticas y de privacidad del EDA; solo datos sintéticos."""
from pathlib import Path
import json

import pandas as pd
from pandas.io.stata import StataMissingValue
import pytest

from tesis_enasem.independent_eda import VariableSpec, analyze_variable, simple_role, validate_values


def spec(name: str = "n_sint_depr", **changes: object) -> VariableSpec:
    args = dict(variable=name, label="Sintética", kind="numeric", unit="conteo", codes={},
                numeric_nonresponse={}, lower=0, upper=9, integer=True, eligibility="Pendiente",
                reference="Datos sintéticos", page=0, temporal="Sin equivalencia inferida",
                interpretation="Sintética")
    args.update(changes)
    return VariableSpec(**args)


def test_numeric_nonresponse_is_specific_not_global() -> None:
    values = pd.Series([0, 8, 9, 99, StataMissingValue(103)])  # .b
    validated, states = validate_values(values, spec())
    assert validated.notna().tolist() == [True, True, True, False, False]
    assert states.iloc[4] == ".b"
    original = pd.Series([1, 8, 9, 99])
    validated, states = validate_values(original, spec("k_monto", upper=None, numeric_nonresponse={"99": "No sabe"}))
    assert validated.notna().tolist() == [True, True, True, False]
    assert states.iloc[3] == "NR/NS numérico: No sabe"
    assert original.iloc[3] == 99  # no corrección del dato original


def test_labeled_categories_quarantine_new_codes() -> None:
    validated, states = validate_values(pd.Series([0, 1, 2, StataMissingValue(106)]),
                                       spec("indicador", kind="categorical", codes={"0": "No", "1": "Sí"}))
    assert validated.notna().sum() == 2
    assert states.iloc[2] == "fuera de dominio documentado"
    assert states.iloc[3] == ".e"


def test_full_partition_denominators_and_negative_wealth() -> None:
    data = pd.DataFrame({"ronda": [1, 1, 1, 1, 2, 2], "tipent": [1, 3, 5, 1, 1, 5],
                         "imp_neto": [-200, 0, StataMissingValue(107), 100, 300, StataMissingValue(107)]})
    result = analyze_variable(data, spec("imp_neto", lower=None, upper=None, integer=False))
    r = result["resumen"][0]
    assert r["N_total"] == 4 and r["N_valido"] == 3 and r["N_elegible"] is None
    assert r["N_negativos"] == 1 and r["N_ceros"] == 1 and r["min"] == -200
    assert sum(x["n"] for x in result["estados"] if x["anio"] == 2001) == 4
    assert sum(x["n"] for x in result["histograma"] if x["anio"] == 2001) == 3
    assert any(x["modalidad"] == "Sobre fallecido" for x in result["por_modalidad"])
    assert not any(x["modalidad"] == "Sobre fallecido" and x["N_valido"] for x in result["por_modalidad"])


def test_frequency_denominators_and_no_nominal_means() -> None:
    data = pd.DataFrame({"ronda": [1, 1, 1, 1], "tipent": [1, 1, 3, 5],
                         "indicador": [1, 1, 0, StataMissingValue(107)]})
    result = analyze_variable(data, spec("indicador", kind="categorical", codes={"0": "No", "1": "Sí"}))
    yes = next(r for r in result["frecuencias"] if r["codigo"] == "1")
    assert yes["pct_total"] == 50 and yes["pct_valido"] == pytest.approx(200/3)
    assert "media" not in result["resumen"][0]
    assert "media" not in result["por_modalidad"][0]


def test_roles_preserve_nonpension_variables_and_forbid_ids() -> None:
    for name in ["diabetes", "nietos", "visualscan_flag", "bmi_flag", "compras"]:
        assert not simple_role(name).startswith("técnica")
    for name in ["cunicah", "np", "codent01", "factori_21", "subhog_15"]:
        with pytest.raises(ValueError):
            analyze_variable(pd.DataFrame(), spec(name))


def test_registry_covers_all_simple_columns_once() -> None:
    root = Path(__file__).resolve().parents[1]
    registry = json.loads((root / "diccionarios/contratos_enasemsimple.json").read_text())["contratos"]
    inventory = json.loads((root / "diccionarios/inventario_fuentes.json").read_text())
    simple = next(s for s in inventory["fuentes"] if s["fuente_id"] == "F20")
    expected = {c for c in simple["columnas"] if not simple_role(c).startswith("técnica")}
    assert len(registry) == len(expected) == 91
    assert {c["variable"] for c in registry} == expected
    assert all(c["page"] >= 14 and c["reference"] and c["eligibility"] for c in registry)


def test_ledger_has_every_source_variable_without_duplicates() -> None:
    root = Path(__file__).resolve().parents[1]
    inventory = json.loads((root / "diccionarios/inventario_fuentes.json").read_text())
    ledger = json.loads((root / "diccionarios/cobertura_variables.json").read_text())
    expected = {(s["fuente_id"], col) for s in inventory["fuentes"] for col in s["columnas"]}
    actual = [(row["fuente"], row["variable"]) for row in ledger]
    assert len(actual) == len(set(actual)) == len(expected) == 5368
    assert set(actual) == expected
    assert all(row["estado"] and row["rol"] and row["bloque"] for row in ledger)
    assert sum(row["fuente"] == "F06" for row in ledger) == 507  # 2024 separado
    assert sum(row["fuente"] in {"F04", "F05"} for row in ledger) == 250  # ambas copias
