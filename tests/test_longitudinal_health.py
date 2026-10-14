"""Pruebas focalizadas de pares, faltantes, seguimiento y soporte longitudinal."""

import numpy as np
import pandas as pd
from tesis_enasem.longitudinal_health import (
    receipt,
    pattern,
    pension_pattern,
    change_summary,
    transition_matrix,
    standardized_contrast,
    build_pair,
)


def test_unknown_is_not_negative():
    assert receipt(pd.NA) == "ND"
    assert receipt(False) == "No"
    assert receipt(True) == "Sí"


def test_paired_changes_and_denominator():
    f = pd.DataFrame({"sintomas_principal_a": [1, 5, np.nan, 4], "sintomas_principal_b": [3, 2, 1, 4]})
    r = change_summary(f)
    assert r["cambio"]["N"] == 3
    assert r["cambio"]["media"] == -1 / 3
    assert r["N_aumenta"] == r["N_disminuye"] == r["N_igual"] == 1


def test_transition_rows_not_total_percentages():
    f = pd.DataFrame({"K_estado_a": ["No", "No", "No", "Sí"], "K_estado_b": ["Sí", "No", "No", "Sí"]})
    r = transition_matrix(f, pd.Series(True, index=f.index))
    cell = next(x for x in r if x["origen"] == "No" and x["destino"] == "Sí")
    assert cell["N"] == 1 and cell["N_origen"] == 3
    assert cell["pct_total"] == 25 and np.isclose(cell["pct_fila"], 100 / 3)


def test_multivisit_patterns_dont_impute_gaps():
    assert pattern([2, 2, 2]) == "Conteo igual en visitas"
    assert pattern([1, 1, 3]) == "No decreciente observado"
    assert pattern([3, 1, 2]) == "Fluctuación observada"
    assert pension_pattern(["Sí", "ND", "Sí"]) == "Incluye desconocidos"
    assert pension_pattern(["No", "Sí", "No"]) == "Múltiples cambios registrados"


def test_standardization_reverses_composition_and_checks_support():
    rows = []
    for cell, ng, nr, gmean, rmean in [("A", 90, 10, 1, 0), ("B", 10, 90, 11, 10)]:
        rows += [{"analitica": True, "transicion": "No→Sí", "sexo_grupo_a": cell, "delta": gmean}] * ng
        rows += [{"analitica": True, "transicion": "No→No", "sexo_grupo_a": cell, "delta": rmean}] * nr
    p = pd.DataFrame(rows)
    r = standardized_contrast(p, "No→Sí", "No→No", ("sexo_grupo",), 10)
    assert r["N_soporte"] == 200 and r["ajustada"] == 1
    assert r["cruda_mismo_soporte"] == -7
    fail = standardized_contrast(p, "No→Sí", "No→No", ("sexo_grupo",), 11)
    assert fail["N_soporte"] == 0 and fail["ajustada"] is None


def test_pair_retains_absence_death_proxy_and_unknown():
    rows = []
    for identifier, mode, state, score in [
        ("a", 1, "Sí", 1),
        ("b", 1, "No", 2),
        ("c", 1, "ND", 3),
        ("d", 1, "Sí", 4),
    ]:
        rows.append(
            dict(
                id=identifier,
                ano=2001,
                universo_60=True,
                tipent=mode,
                directa=True,
                K_estado=state,
                n_sint_depr=score,
                sintomas_principal=score,
                a_o_ent=2001,
                mes_ent=6,
            )
        )
    for identifier, mode, state, score in [("a", 5, "ND", np.nan), ("b", 3, "Sí", np.nan), ("c", 1, "Sí", 4)]:
        rows.append(
            dict(
                id=identifier,
                ano=2003,
                universo_60=mode != 5,
                tipent=mode,
                directa=mode == 1,
                K_estado=state,
                n_sint_depr=score,
                sintomas_principal=score,
                a_o_ent=2003,
                mes_ent=6,
            )
        )
    p = build_pair(pd.DataFrame(rows), 2001, 2003)
    assert len(p) == 4 and p.analitica.sum() == 0
    assert p.loc["a", "seguimiento"] == "Sobre fallecido"
    assert p.loc["b", "seguimiento"] == "Sustituto destino"
    assert p.loc["d", "seguimiento"] == "Ausente"
    assert not p.loc["c", "K_conocida"]


def test_cesd_positive_polarity_and_partial_missing_not_zero():
    from tesis_enasem.longitudinal_health import complete_score, ITEMS, POSITIVE

    frame = pd.DataFrame(
        [
            {v: (1 if v in POSITIVE else 0) for v in ITEMS},
            {v: 1 for v in ITEMS},
            {v: (np.nan if v == "solo" else 0) for v in ITEMS},
        ]
    )
    complete, score = complete_score(frame)
    assert complete.tolist() == [True, True, False]
    assert score.iloc[0] == 0 and score.iloc[1] == 6 and pd.isna(score.iloc[2])
