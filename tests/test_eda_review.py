"""Denominadores documentales y cotejos de imputación; CI sin microdatos."""
import pandas as pd
import pytest
from pandas.io.stata import StataMissingValue

from tesis_enasem.eda_review import eligible_summary, comparison_table, interpret_result
from tesis_enasem.economic_eda import component_unit, describe_source_variable, paired_imputation_check
from tesis_enasem.independent_eda import VariableSpec, analyze_variable


def spec(name: str = "medida", **changes: object) -> VariableSpec:
    values = dict(variable=name,label="Sintética",kind="numeric",unit="pesos",codes={},
                  numeric_nonresponse={},lower=None,upper=None,integer=False,eligibility="Documentada",
                  reference="Sintética",page=1,temporal="Unidades pendientes",interpretation="No causal")
    return VariableSpec(**{**values,**changes})


def test_eligibility_does_not_equal_valid_or_drop_nonresponse() -> None:
    df = pd.DataFrame({"ronda":[1]*4,"tipent":[1,1,3,5],"medida":[1,StataMissingValue(103),7,StataMissingValue(107)]})
    r = analyze_variable(df,spec())
    eligible = eligible_summary(r,{"2001":{"modalidades":[1,2],"nota":"Directas documentadas"}})[0]
    assert eligible["N_total"] == 4 and eligible["N_elegible"] == 2
    assert eligible["N_valido_elegible"] == 1 and eligible["N_no_valido_elegible"] == 1
    assert eligible["N_valido_fuera_universo"] == 1  # auditar, no borrar
    assert eligible["pct_valido_elegible"] == 50


def test_unknown_universe_and_absent_instrument_are_distinct() -> None:
    r = analyze_variable(pd.DataFrame({"ronda":[1],"tipent":[1],"medida":[StataMissingValue(103)]}),spec())
    unknown = eligible_summary(r,{"2001":{"modalidades":None,"nota":"ND"}})[0]
    absent = eligible_summary(r,{"2001":{"modalidades":[],"nota":"Sin instrumento"}})[0]
    assert unknown["N_elegible"] is None and absent["N_elegible"] == 0
    assert absent["pct_valido_elegible"] is None


def test_joint_table_quantiles_and_result_driven_discussion() -> None:
    df = pd.DataFrame({"ronda":[1,1,6,6],"tipent":[1]*4,"medida":[-20,0,10,90]})
    r = analyze_variable(df,spec())
    table = comparison_table(r)
    assert table[0]["mediana"] == -10 and table[1]["mediana"] == 50
    assert table[0]["N_negativos"] == 1
    assert "50.00" in interpret_result(r,[]) and "90.00" in interpret_result(r,[])


def test_economic_nullable_filter_and_question_specific_refusal() -> None:
    result = describe_source_variable(pd.Series([8,8888888,0,12]),
        spec(numeric_nonresponse={"8888888":"Negativa"}),pd.Series([True,True,False,pd.NA],dtype="boolean"))
    s = result["resumen"]
    assert s["N_valido"] == 3  # 8 no es RF global
    assert s["N_elegible"] is None and s["N_elegible_confirmado"] == 2
    assert s["N_elegibilidad_desconocida"] == 1 and s["pct_valido_elegible"] is None
    assert s["N_valido_fuera_universo"] == 1


def test_imputation_recovery_changes_and_flag_are_different() -> None:
    check = paired_imputation_check(pd.Series([None,0,40,50]),pd.Series([8,0,44,50]),pd.Series([1,0,0,1]))
    assert check["N_recuperados"] == 1 and check["N_ambos_difieren"] == 1
    assert check["N_bandera_1"] == 2
    assert check["N_cambio_observado_bandera_no_1"] == 1


def test_reference_window_is_not_automatic_annualization() -> None:
    assert component_unit("61_1_1") == component_unit("88") == "pesos por mes"
    assert "total" in component_unit("77") and "total" in component_unit("111")
    assert "confirmar" in component_unit("47a")
    assert "patrimonial" in component_unit("4_1")
    with pytest.raises(ValueError):
        component_unit("inventado")


@pytest.mark.parametrize("name",["np","cunicah","k45d_21","k52a_1_21","subhog_21"])
def test_economic_identifier_outputs_forbidden(name: str) -> None:
    with pytest.raises(ValueError):
        describe_source_variable(pd.Series([1]),spec(name))
