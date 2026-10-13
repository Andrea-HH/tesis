import pandas as pd

from tesis_enasem.joint_eda import paired_spearman, stratified_descriptions


def test_spearman_pair_denominator_and_constant():
    data = pd.DataFrame({"a":[1,2,3,4],"b":[4,3,2,None]})
    out = paired_spearman(data,"a","b",2021)
    assert out["N_pares_validos"] == 3 and out["N_sin_par"] == 1
    assert out["rho_spearman"] == -1
    data["b"] = 0
    assert paired_spearman(data,"a","b",2021)["rho_spearman"] is None


def test_strata_preserve_unknown_group_and_missing_measure():
    data = pd.DataFrame({"group":["sí","sí",None],"wealth":[100,None,-20]})
    out = stratified_descriptions(data,["group"],["wealth"])
    yes = next(r for r in out if r["group"] == "sí")
    assert yes["N_estrato"] == 2 and yes["N_valido"] == 1 and yes["mediana"] == 100
    assert next(r for r in out if r["group"] == "desconocido")["mediana"] == -20
