"""Contratos sintéticos: no requieren microdatos privados."""
import json

import pandas as pd
import pytest
from pandas.io.stata import StataMissingValue

from tesis_enasem.protection_eda import (UNKNOWN, support_contract, binary_receipt,
    support_events, pension_institution_evidence, add_profiles, joint_category,
    protection_crosstab, reception_rates, categorical_association, support_pension_gap,
    longitudinal_transitions)


def sample() -> pd.DataFrame:
    """Una recepción faltante, una muerte y grupos de distinto tamaño."""
    return pd.DataFrame({"id":["a","b","c","d","e"],"ano":[2021]*5,"edad":[60,70,80,90,65],
        "sexo":[1,2,2,1,2],"educacion":[0,6,9,12,4],"urbano":[0,1,0,1,0],"tipent":[1,3,1,5,1],
        "pension_propia_k":pd.array([True,False,False,None,None],dtype="boolean"),
        "pension_conyuge_k":pd.array([False,False,True,None,None],dtype="boolean"),
        "apoyo_propio":pd.array([False,True,False,None,True],dtype="boolean"),
        "apoyo_conyuge":pd.array([False,False,True,None,None],dtype="boolean")})


@pytest.mark.parametrize("value",[8,9,0,3,None,StataMissingValue(101)])
def test_unknown_receipt_is_not_negative(value):
    assert binary_receipt(value) is None


def test_early_and_late_amount_codes_and_multiple_programs():
    c=support_contract(2001)
    events=support_events({"k76a":1,"k77_1":888888},c,1)
    assert events[0]["monto_mensual_observado"] is None
    assert events[0]["programa"]=="Programa no identificado"
    c=support_contract(2021)
    e=support_events({"k79a_21":1,"k79a_1_1_21":5,"k80_1_1_21":9,
        "k79a_1_2_21":4,"k80_1_2_21":9999999},c,1)
    assert len(e)==2 and e[0]["monto_mensual_observado"]==9
    assert e[0]["tipo_documental"]=="Vejez no contributiva identificada"
    assert e[1]["tipo_documental"]=="Apoyo público sin tipo comprobado"
    assert e[1]["monto_mensual_observado"] is None
    assert support_events({"k79a_21":9,"k80_1_1_21":1000},c,1)==[]


def test_institutions_are_not_amount_components():
    e={"instituciones_originales":json.dumps({"k59_1_01_15":1,"k59_1_02_15":1,
        "k59_1_08_15":1,"k59_1_88_15":None}),"alcance_institucion":"seleccion_multiple_por_tipo"}
    r=pension_institution_evidence(e)
    assert r["seguridad_social_identificada"] and r["programa_publico_agrupado"]
    assert not r["monto_separable_por_institucion"]
    e={"instituciones_originales":json.dumps({"k59_1_1_21":4}),"alcance_institucion":"institucion_del_slot"}
    assert pension_institution_evidence(e)["institucion_sin_tipo_comprobado"]
    assert not pension_institution_evidence(e)["seguridad_social_identificada"]
    e={"ano":2021,"instituciones_originales":json.dumps({"k59_1_1_21":8}),"alcance_institucion":"institucion_del_slot"}
    assert pension_institution_evidence(e)["programa_publico_agrupado"]
    e["ano"]=2001
    assert pension_institution_evidence(e)["institucion_sin_tipo_comprobado"]


def test_controls_have_actual_meaning_not_rural_or_current_schooling():
    r=add_profiles(sample())
    assert r.loc[0,"localidad_grupo"]=="<100 mil habitantes"
    assert r.loc[1,"educacion_grupo"]=="6 años"
    assert r.loc[2,"educacion_grupo"]=="7–9 años"
    assert r.loc[3,"edad_grupo"]=="≥90"


def test_joint_partition_preserves_unknown_pension_with_support():
    assert joint_category(None,True)=="Apoyo con pensión desconocida"
    assert joint_category(False,True)=="Apoyo y negativa propia K"
    assert joint_category(False,False)=="Negativas explícitas K y A"
    assert joint_category(False,None)=="Otra situación desconocida"
    f=sample(); rows=protection_crosstab(f,[])
    assert len(rows)==9 and sum(r["N"] for r in rows)==5
    assert {r["N_par_conocido"] for r in rows}=={3}
    assert {r["N_elegible_vivo"] for r in rows}=={4}
    assert sum(r["pct_composicion_apoyados"] or 0 for r in rows)==100


def test_denominators_and_rate_gap_are_separate():
    r=next(r for r in reception_rates(sample(),[]) if r["variable"]=="apoyo_propio")
    assert (r["N_total"],r["N_elegible_vivo"],r["N_conocido"],r["N_desconocido"])==(5,4,4,1)
    assert r["pct_si_total"]==40 and r["pct_si_conocido"]==50
    assert support_pension_gap(sample())["diferencia_pp_no_menos_si"]==50


def test_cramer_only_known_and_constant_is_not_zero_effect():
    f=pd.DataFrame({"x":["a","a","b","b",UNKNOWN],"y":["c","c","d","d","c"]})
    r=categorical_association(f,"x","y")
    assert r["V_cramer"]==pytest.approx(1) and r["N_validos"]==4 and r["N_excluidos"]==1
    assert categorical_association(f.loc[:1],"x","y")["V_cramer"] is None


def test_transitions_discriminate_absence_death_unknown_and_question_change():
    f=pd.DataFrame({"id":["a","b","c","d","a","c","d","b"],
        "ano":[2012]*4+[2015]*3+[2018],"edad":[65]*8,"tipent":[1]*4+[1,5,1,1],
        "pension_propia_k":pd.array([False,True,True,True,True,None,None,True],dtype="boolean")})
    rows=longitudinal_transitions(f,2012,2015,"pension_propia_k",True)
    assert sum(r["N"] for r in rows)==4
    assert any(r["interpretacion"]=="Inicio observado" and r["N"]==1 for r in rows)
    assert any(r["destino"]=="Ausente con reaparición posterior" for r in rows)
    assert any(r["destino"]=="Sobre fallecido" for r in rows)
    assert any(r["destino"]==UNKNOWN for r in rows)
    rows=longitudinal_transitions(f,2012,2015,"pension_propia_k",False)
    assert all(r["interpretacion"].startswith("No interpretable") for r in rows)
