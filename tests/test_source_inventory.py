"""Auditoría de fuentes con datos sintéticos, sin ENASEM privado."""
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
from pandas.io.stata import StataMissingValue

from tesis_enasem.source_inventory import (
    inspect_stata, inspect_workbook, key_audit, match_audit, missing_mask, normalized_name,
    same_wave_comparisons,
)


def test_missing_and_nonunique_keys_do_not_become_zero() -> None:
    series = pd.Series([0, 1, StataMissingValue(101), None, "", "x"], dtype=object)
    assert missing_mask(series).tolist() == [False, False, True, True, True, False]
    data = pd.DataFrame({"cunicah": [1, 1, 1], "np": [1, 1, None]})
    check = key_audit(data, ["cunicah", "np"])
    assert check["n_incompletas"] == 1 and check["filas_duplicadas"] == 2


def test_matching_reports_cardinality_and_incomplete_denominator() -> None:
    left = pd.DataFrame({"cunicah": [1, 1, 2, None]})
    right = pd.DataFrame({"cunicah": [1, 3]})
    result = match_audit(left, right, ["cunicah"])
    assert result["n_filas_izquierda_emparejadas"] == 2
    assert result["n_izquierda"] == 4 and result["n_claves_izquierda_incompletas"] == 1
    assert result["derecha_unica"] and not result["izquierda_unica"]
    assert "identificadores" not in result


def test_stata_inventory_keeps_every_variable_and_labels(tmp_path: Path) -> None:
    path = tmp_path / "source.dta"
    pd.DataFrame({"cunicah": [1, 2], "np": [1, 1], "k79a_21": [1, 2],
                  "j1_21": [0., float("nan")], "otra": [4, 5]}).to_stata(
        path, write_index=False, variable_labels={"k79a_21": "Public transfer"},
        value_labels={"k79a_21": {1: "Yes", 2: "No"}})
    meta, fields, _ = inspect_stata(path)
    assert meta["n_variables"] == 5 and len(fields) == 5
    assert next(x for x in fields if x["variable"] == "j1_21")["n_perdidos"] == 1
    assert next(x for x in fields if x["variable"] == "k79a_21")["etiquetas_valores"]["1"] == "Yes"
    assert all("valores_individuales" not in x for x in fields)


def test_pair_comparisons_do_not_declare_name_equivalence() -> None:
    frames = {"a": pd.DataFrame({"cunicah": [1], "np": [1], "k_21": [3]}),
              "b": pd.DataFrame({"cunicah": [1], "np": [1], "k_21": [4]}),
              "c": pd.DataFrame({"cunicah": [1], "np": [1]})}
    out = same_wave_comparisons(frames, {"a": 2021, "b": 2021, "c": 2024})
    assert len(out) == 1 and out[0]["discrepancias_por_variable"]["k_21"] == 1
    assert out[0]["variables_equivalentes"] == "No inferidas por nombre"
    assert normalized_name("k59_1_1_21") == "k59_1_1"
    assert normalized_name("k59_1_01_12") != normalized_name("k59_1_1_21")


def test_workbook_inspection_reads_all_sheets_without_editing(tmp_path: Path) -> None:
    path = tmp_path / "inventory.xlsx"
    main = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    with ZipFile(path, "w") as z:
        z.writestr("xl/workbook.xml", f'<workbook xmlns="{main}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Una" sheetId="1" r:id="r1"/><sheet name="Dos" sheetId="2" r:id="r2"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r1" Target="worksheets/sheet1.xml"/><Relationship Id="r2" Target="worksheets/sheet2.xml"/></Relationships>')
        for i in (1, 2):
            z.writestr(f"xl/worksheets/sheet{i}.xml", f'<worksheet xmlns="{main}"><sheetData><row r="1"><c r="A1"><v>{i}</v></c><c r="B1"><f>A1+1</f><v>{i+1}</v></c></row></sheetData></worksheet>')
    before = path.read_bytes()
    result = inspect_workbook(path)
    assert len(result["hojas"]) == 2
    assert result["hojas"][1]["formulas"][0]["formula"] == "A1+1"
    assert path.read_bytes() == before


def test_version_comparison_respects_numeric_equality_and_missing_tags() -> None:
    """Una diferencia de almacenamiento no es una diferencia económica."""
    from tesis_enasem.source_inventory import discrepancy_count
    a = pd.Series([1, 2, StataMissingValue(102), StataMissingValue(103)], dtype=object)
    b = pd.Series([1.0, 2.0, StataMissingValue(102), StataMissingValue(104)], dtype=object)
    assert discrepancy_count(a, b) == 1
