"""Contratos sintéticos de unión izquierda, preservación y titularidad pensionaria."""
import json

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from pandas.io.stata import StataMissingValue

from tesis_enasem.integration import (encode_stata, economic_link, left_indexer, pension_2021_record,
                                    person_id, restore_stata, take_nullable)


def test_id_separator_original_strings_and_integer_formats():
    data = pd.DataFrame({"cunicah": [1,12,"001"], "np": [23.,3.,"02"]})
    assert list(person_id(data)) == ["1:23","12:3","001:02"]
    assert person_id(data).nunique() == 3


@pytest.mark.parametrize("value", [None, float("nan"), "", "a:b", 1.25])
def test_invalid_person_identifier_fails(value):
    with pytest.raises((ValueError,TypeError)):
        person_id(pd.DataFrame({"cunicah": [value], "np": [1]}))


def test_left_join_missing_keys_do_not_match_and_no_rows_multiply():
    l = pd.DataFrame({"cunicah": [1.,1.,2.,None], "sub": [1,1,1,1]})
    r = pd.DataFrame({"cunicah": [1,None], "sub": [1,1]})
    ix, complete, audit = left_indexer(l,r,["cunicah","sub"])
    assert ix.tolist() == [0,0,-1,-1]
    assert complete.tolist() == [True,True,True,False]
    assert audit["cardinalidad"] == "many_to_one"
    assert audit["n_enlazadas"] == 2
    assert take_nullable(pa.array([100,999]),ix).to_pylist() == [100,100,None,None]


def test_duplicate_source_and_person_key_fail_before_join():
    data = pd.DataFrame({"cunicah": [1,1],"np": [1,1]})
    with pytest.raises(ValueError,match="muchos-a-muchos"):
        left_indexer(data,data,["cunicah","np"])
    with pytest.raises(ValueError,match="izquierda no única"):
        left_indexer(data,data.iloc[:1],["cunicah","np"],individual=True)


def test_stata_tags_codes_and_empty_strings_survive_parquet(tmp_path):
    missing = {v.string:v for v in (StataMissingValue(x) for x in StataMissingValue.MISSING_VALUES)}
    s = pd.Series([8,9,8888888,0,missing[".f"],missing[".p"],missing[".w"],missing["."]])
    values,tags,profile = encode_stata(s)
    path = tmp_path / "synthetic.parquet"
    pq.write_table(pa.table({"v":values,"tag":tags}),path)
    read = pq.read_table(path).to_pandas()
    restored = restore_stata(read.v,read.tag)
    assert [str(v) for v in restored.iloc[4:]] == [".f",".p",".w","."]
    assert read.v.iloc[:4].tolist() == [8,9,8888888,0]
    assert profile[".f"] == 1
    strings,_,_ = encode_stata(pd.Series(["", "texto"]))
    assert strings.to_pylist() == ["","texto"]


def pension_sources():
    individual = {"key_21":1,"k45d_21":1,"k52a_1_21":2,"k52a_21":2}
    household = {"k45d_21":1,"k52a_1_21":2,"k52a_21":2,
                 "k58a_21":1,"k58b_21":2,"k58c_21":2,"k58d_21":2,
                 "k59_1_1_21":1,"k61_1_1_21":8, "k59_1_2_21":6,"k61_1_2_21":8888888,
                 "k64c_21":1,"k64d_21":2,"k64e_21":2,"k64f_21":2,
                 "k65_1_1_21":2,"k67_1_1_21":9000,"k79a_21":1,"k79a_1_1_21":5,
                 "k80_1_1_21":1600,"k82c_21":2}
    return individual,household


def test_multiple_pensions_unknown_institution_nonresponse_and_valid_eight():
    i,h = pension_sources()
    result = pension_2021_record(1,1,i,h)
    events = json.loads(result["pension_fuentes_2021"])
    assert len(events) == 2
    assert events[0]["monto_mensual_valido"] == 8
    assert events[1]["monto_mensual_valido"] is None
    assert events[1]["clasificacion_evidencia"] == "desconocida"
    assert result["pension_monto_mensual_observado_parcial_2021"] == 8
    assert result["pension_contributiva_evidencia_2021"] is True
    assert result["apoyo_vejez_evidencia_2021"] is True


def test_spouse_is_assigned_only_to_corresponding_person():
    i,h = pension_sources()
    i["key_21"] = 2
    result = pension_2021_record(2,3,i,h)
    events = json.loads(result["pension_fuentes_2021"])
    assert len(events) == 1
    assert events[0]["institucion"] == "ISSSTE"
    assert result["pension_monto_mensual_observado_parcial_2021"] == 9000
    assert result["apoyo_vejez_evidencia_2021"] is False


@pytest.mark.parametrize("problem", ["missing","dead","pointer","key"])
def test_invalid_owner_or_link_cannot_create_receipt_or_zero(problem):
    i,h = pension_sources()
    mode = 1
    if problem == "missing": h = None
    if problem == "dead": mode = 5
    if problem == "pointer": h["k45d_21"] = 77
    if problem == "key": i["key_21"] = 2
    result = pension_2021_record(1,mode,i,h)
    assert result["pension_recibe_k_2021"] is None
    assert result["pension_monto_mensual_observado_parcial_2021"] is None


def test_partial_negative_answers_are_unknown_not_false():
    i,h = pension_sources()
    for c in "abcd": h[f"k58{c}_21"] = 2
    h["k58d_21"] = 9
    assert pension_2021_record(1,1,i,h)["pension_recibe_k_2021"] is None


def test_historical_bridge_preserves_person_key_and_recovers_household():
    master = pd.DataFrame({"cunicah":[1,1,2],"np":[101,102,101],"codent03":[1,2,1],
                           "acthog":[999,999,999],"ronda":[2,2,2]})
    bridge = pd.DataFrame({"cunicah":[1,1],"codent03":[1,2],"acthog":[4,4]})
    hh = pd.DataFrame({"cunicah":[1],"acthog":[4]})
    with pytest.raises(ValueError,match="requieren puente"):
        economic_link(master,hh,2003,["cunicah","acthog"],False)
    result = economic_link(master,hh,2003,["cunicah","acthog"],False,bridge)
    assert result["indexer"].tolist() == [0,0,-1]
    assert result["states"].tolist() == ["enlazado","enlazado","sin_puente_personal"]
    assert master.np.tolist() == [101,102,101]
    assert master.acthog.tolist() == [999,999,999]


def test_two_household_pointers_for_same_person_are_ambiguous():
    i,h = pension_sources()
    h["k52a_1_21"] = 1
    result = pension_2021_record(1,1,i,h)
    assert result["econ_titular_estado"] == "titular_hogar_ambiguo_ambos_punteros"
    assert result["pension_recibe_k_2021"] is None
