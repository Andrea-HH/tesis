"""Casos sintéticos para la investigación puntual de anomalías de CP1."""
import pandas as pd

from tesis_enasem.cp1_review import investigate_anomalies, review_transitions


def test_adjacent_observation_missing_interrupts_and_gap_is_allowed():
    raw = pd.DataFrame({
        'cunicah': [10]*4 + [20]*2, 'np': [1]*6, 'ronda': [1, 2, 3, 4, 1, 3],
        'tipent': [2, 1, 1, 1, 2, 3], 'edad': [70, None, 68, 67, 65, 59],
        'sexo': [1]*6, 'fallecido': [0]*6, 'a_o_ent': [2001, 2003, 2012, 2015, 2001, 2012],
        'a_o_nac': [1931]*4 + [1936]*2, 'mes_nac': [5]*6,
    })
    original = raw.copy(deep=True)
    tables = investigate_anomalies(raw)
    checks = tables['resumen'].set_index('control').n
    assert checks['pares_observados'] == 4
    assert checks['pares_edad_evaluables'] == 2
    assert checks['pares_edad_no_evaluables'] == 2
    assert checks['pares_edad_decreciente'] == 2
    assert checks['pares_descenso_rondas_consecutivas'] == 1
    assert checks['pares_descenso_cruzan_60'] == 1
    assert checks['pares_descenso_entrevista_ano_creciente'] == 2
    assert tables['edad_modalidad'].n.sum() == 2
    # La vista aproximada solo marca incompatibilidad: no sustituye las edades.
    assert tables['edad_compatibilidad'].n.sum() == 2
    pd.testing.assert_frame_equal(raw, original)


def test_death_repetition_sex_tie_and_outputs_have_no_individual_attributes():
    raw = pd.DataFrame({
        'cunicah': [42]*3 + [99]*2, 'np': [1]*5, 'ronda': [1, 3, 6, 2, 4],
        'tipent': [5, 1, 5, 2, 1], 'edad': [None, 60, None, 62, 64],
        'sexo': [1, 1, 1, 1, 2], 'fallecido': [1, 0, 1, 0, 0],
        'a_o_ent': [None, 2012, None, 2003, 2015], 'a_o_nac': [1952]*3 + [1941]*2,
        'mes_nac': [1]*5,
    })
    tables = investigate_anomalies(raw)
    checks = tables['resumen'].set_index('control').n
    assert checks['registros_posteriores_fallecimiento'] == 2
    assert checks['personas_posteriores_fallecimiento'] == 1
    assert checks['personas_fallecimiento_repetido'] == 1
    assert checks['discrepancias_tipent_fallecido'] == 0
    assert checks['personas_sexo_inconsistente'] == 1
    assert checks['registros_personas_sexo_inconsistente'] == 2
    assert tables['posteriores_modalidad'].set_index('modalidad').n.to_dict() == {'Directa': 1, 'Sobre fallecido': 1}
    for table in tables.values():
        assert not {'id', 'cunicah', 'np', 'sexo', 'edad', 'a_o_nac', 'mes_nac', 'ronda'}.intersection(table.columns)
    assert tables['edad_destino'].empty


def test_return_is_subset_of_absence_and_end_of_observation_is_not_permanent_loss():
    tables = {
        'patrones': pd.DataFrame({'patron_2001_a_2021': ['101001', '100000', '111110'], 'personas': [2, 3, 1]}),
        'transiciones': pd.DataFrame({'origen': [1, 5], 'destino': [2, 6],
                                     'denominador_origen': [6, 1], 'no_observadas': [5, 1]}),
    }
    reviewed = review_transitions(tables)
    assert reviewed.ausentes_con_reaparicion_posterior.tolist() == [2, 0]
    assert reviewed.ausentes_sin_reaparicion_observada_hasta_2021.tolist() == [3, 1]
    assert reviewed.ausentes_con_reaparicion_posterior_porcentaje.iloc[0] == 100 * 2 / 6
    assert not any('definitiva' in column for column in reviewed.columns)
