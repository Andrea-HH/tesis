"""CP1 sintético: denominadores, entrada tardía, reaparición y faltantes Stata."""
import pandas as pd
import pytest
from pandas.io.stata import StataMissingValue
from tesis_enasem.audit import (prepare_audit, population_masks, longitudinal_tables,
                               missing_by_wave, frequency_table, sample_flow)


def synthetic_panel():
    return pd.DataFrame({'cunicah': [1,1,1,2,2,3], 'np': [1]*6, 'ronda': [1,2,4,2,3,1],
                         'tipent': [2,1,5,2,1,4], 'edad': [59,61,StataMissingValue(107),65,68,70],
                         'sexo': [1,1,1,2,2,2], 'urbano': [0,0,0,1,1,0],
                         'est_conyugal': [1]*6, 'educacion': [4]*6, 'edu_gru': [1]*6})


def test_validation_rejects_duplicates_bad_wave_and_missing_key():
    raw = synthetic_panel()
    for bad in [pd.concat([raw,raw.iloc[[0]]]), raw.assign(ronda=7), raw.assign(np=None), raw.assign(tipent=6)]:
        with pytest.raises(ValueError):
            prepare_audit(bad)


def test_entry_rules_do_not_require_baseline_age_and_keep_death_in_followup():
    data = prepare_audit(synthetic_panel())
    masks = population_masks(data)
    assert masks['Directas 60+ por visita'].tolist() == [False,True,False,True,True,False]
    assert masks['60+ en primera observación, seguimiento amplio'].tolist() == [False,False,False,True,True,True]
    assert masks['Desde primera observación 60+, seguimiento amplio'].tolist() == [False,True,True,True,True,True]
    assert not masks['Seis directas 60+ por visita'].any()


def test_transition_reappearance_absence_and_entries_reconcile():
    tables = longitudinal_tables(prepare_audit(synthetic_panel()))
    entries = tables['entradas'].set_index('ronda')
    assert entries.loc[4,'reaparecen_tras_ausencia'] == 1
    assert entries.loc[2,'primera_aparicion'] == 1
    transitions = tables['transiciones']
    assert (transitions.continuan + transitions.no_observadas).equals(transitions.denominador_origen)
    assert transitions.loc[transitions.origen.eq(2),'intervalo_nominal_anos'].iloc[0] == 9
    assert tables['numero_rondas'].personas.sum() == 3
    assert tables['patrones'].personas.sum() == 3


def test_missing_codes_reconcile_without_becoming_zero():
    raw = pd.DataFrame({'ronda':[1]*4, 'value':[0,StataMissingValue(107),StataMissingValue(124),float('nan')]})
    tab = missing_by_wave(raw)
    counts = tab.loc[tab.variable.eq('value')].set_index('tipo')['n'].to_dict()
    assert counts == {'válido':1, '.f':1, '.w':1, 'NaN':1}
    assert tab.groupby(['ronda','variable']).n.sum().eq(4).all()
    freq = frequency_table(raw.value, 'value')
    assert freq.n.sum() == 4
    assert freq.porcentaje.sum() == 100


def test_sequential_flow_distinguishes_proxy_missing_and_age():
    data = prepare_audit(synthetic_panel())
    flow = sample_flow(data)
    assert (flow.antes-flow.excluidos).equals(flow.despues)
    assert flow.loc[flow.filtro.eq('Edad 60+'),'despues'].sum() == 3


def test_consistency_flags_death_then_direct_and_sex_changes():
    from tesis_enasem.audit import longitudinal_consistency, effective_intervals
    raw = synthetic_panel()
    extra = raw.iloc[[2]].copy().assign(ronda=5, tipent=1, edad=60, sexo=2)
    data = prepare_audit(pd.concat([raw,extra], ignore_index=True))
    checks = longitudinal_consistency(data).set_index('control').n
    assert checks['registros_despues_de_fallecimiento'] == 1
    assert checks['personas_con_sexo_valido_inconsistente'] == 1
    data['a_o_ent'] = data.ronda.map({1:2001,2:2003,3:2013,4:2015,5:2019})
    intervals = effective_intervals(data).set_index('ronda')
    assert intervals.loc[2,'mediana'] == 10
    assert intervals.loc[4,'mediana'] == 4


def test_full_aggregate_audit_and_report_reconcile_without_exporting_ids():
    from tesis_enasem.audit import build_audit
    from tesis_enasem.audit_report import markdown_table, wave_interpretation, plot_wave, plot_longitudinal
    import matplotlib.pyplot as plt
    raw = synthetic_panel().assign(a_o_ent=[2001,2003,2015,2003,2012,2001], edad_gru=[1,2,2,2,2,3],
                                   fallecido=[0,0,1,0,0,0], ron_pat=['215000']*3+['021000']*2+['400000'])
    for year in ['01','03','12','15','18','21']:
        raw[f'factori_{year}'] = 0
        raw[f'factorh_{year}'] = 1
    tables = build_audit(raw)
    from io import StringIO
    for table in tables.values():
        restored = pd.read_json(StringIO(table.to_json(orient='table')), orient='table')
        assert restored.shape == table.shape
        assert not {'id','cunicah','np'}.intersection(table.columns)
    assert tables['estructura'].iloc[0].personas == 3
    assert tables['demografia'].groupby(['ronda','variable']).n.sum().eq(
        tables['demografia'].groupby(['ronda','variable']).denominador.first()).all()
    assert 'denominador' in markdown_table(tables['edad'])
    assert 'ronda 1 (2001)' in wave_interpretation(tables,1)
    plt.close(plot_wave(raw,1))
    plt.close(plot_longitudinal(tables))


def complete_synthetic_panel() -> pd.DataFrame:
    """Panel pequeño con menores, sustitutos, fallecimiento y presencia no balanceada."""
    raw = synthetic_panel().assign(a_o_ent=[2001,2003,2015,2003,2012,2001],
                                   edad_gru=[1,2,2,2,2,3], fallecido=[0,0,1,0,0,0])
    for year in ['01','03','12','15','18','21']:
        raw[f'factori_{year}'] = 0
        raw[f'factorh_{year}'] = 1
    return raw


def test_default_audit_preserves_every_record_age_interview_and_participation():
    from tesis_enasem.audit import build_audit, select_population
    raw = complete_synthetic_panel()
    raw.index = [0, 0, 1, 1, 2, 2]  # etiquetas repetidas no deben multiplicar filas
    original = raw.copy(deep=True)
    data = prepare_audit(raw)
    pd.testing.assert_frame_equal(select_population(data), data)
    tables = build_audit(raw)
    structure = tables['estructura'].iloc[0]
    assert structure.registros == len(raw)
    assert structure.registros_excluidos_por_seleccion == 0
    assert structure.personas_excluidas_por_seleccion == 0
    assert tables['rondas'].menores_60.sum() == 1
    assert tables['demografia'].loc[tables['demografia'].variable.eq('tipent') &
                                  tables['demografia'].categoria.eq('Sobre fallecido'), 'n'].sum() == 1
    assert tables['demografia'].loc[tables['demografia'].variable.eq('tipent') &
                                  tables['demografia'].categoria.eq('Sustituto de nueva persona'), 'n'].sum() == 1
    assert tables['numero_rondas'].loc[tables['numero_rondas'].rondas_observadas.eq(1),'personas'].iloc[0] == 1
    pd.testing.assert_frame_equal(raw, original)
    sample = tables['muestras'].set_index('muestra')
    assert sample.loc['Panel no balanceado, todas las edades/entrevistas', 'registros_excluidos'] == 0


def test_age_group_boundaries_and_special_missing_are_exhaustive():
    from tesis_enasem.audit import age_groups, AGE_LABELS
    values = pd.Series([17,49,50,59,60,69,70,79,80,89,90,115,
                        StataMissingValue(107),StataMissingValue(124),float('nan')])
    assert age_groups(values).tolist() == [label for label in AGE_LABELS[:-1] for _ in range(2)] + ['Edad faltante']*3
    assert age_groups(pd.Series([49.9,50.0,89.9,90.0])).tolist() == ['Menores de 50','50–59','80–89','90 o más']


def test_optional_population_is_explicit_and_keeps_original_denominators():
    from tesis_enasem.audit import build_audit, select_population
    raw = complete_synthetic_panel()
    filtered = build_audit(raw, population='Directas 60+ por visita')
    structure = filtered['estructura'].iloc[0]
    assert structure.registros_originales == 6
    assert structure.registros == 3
    assert structure.registros_excluidos_por_seleccion == 3
    with pytest.raises(ValueError, match='desconocida'):
        select_population(prepare_audit(raw), 'Población inventada')
    with pytest.raises(ValueError, match='no contiene'):
        select_population(prepare_audit(raw), 'Seis directas 60+ por visita')


def test_subpopulation_exclusions_reconcile_by_person_and_record_in_every_wave():
    from tesis_enasem.audit import build_audit
    tables = build_audit(complete_synthetic_panel())
    for name in ['muestras','muestras_ronda']:
        sample = tables[name]
        assert (sample.registros+sample.registros_excluidos).equals(sample.denominador_registros)
        assert (sample.personas+sample.personas_excluidas).equals(sample.denominador_personas)
    assert tables['edad_grupos'].groupby('ronda').n.sum().tolist() == [2,2,1,1]
    assert tables['edad_grupos'].groupby('ronda').categoria.nunique().eq(7).all()
    assert tables['participacion_ronda'].groupby('ronda').personas.sum().tolist() == [2,2,1,1]


def test_followup_profiles_include_deceased_in_origin_not_only_living():
    from tesis_enasem.audit import build_audit
    tables = build_audit(complete_synthetic_panel())
    profile = tables['perfiles_seguimiento']
    age = profile.loc[profile.ronda.eq(4) & profile.variable.eq('edad')]
    assert age.denominador.sum() == 1  # única observación en origen es sobre fallecido
    assert age.n.sum() == 0  # edad .f no se inventa
    modes = profile.loc[profile.ronda.eq(4) & profile.variable.eq('tipent') & profile.categoria.eq('Sobre fallecido')]
    assert modes.n.sum() == 1


def test_report_and_notebook_keep_subpopulations_after_full_audit(tmp_path):
    from tesis_enasem.audit import build_audit
    from tesis_enasem.audit_report import write_cp1_report, wave_interpretation
    import nbformat
    from pathlib import Path
    # Prueba de reporte usa las seis rondas para cubrir todas las fichas.
    raw = complete_synthetic_panel()
    extras = raw.iloc[[2,2]].copy()
    extras['ronda'] = [5,6]
    extras['a_o_ent'] = [2018,2021]
    raw = pd.concat([raw,extras],ignore_index=True)
    tables = build_audit(raw)
    write_cp1_report(tables,tmp_path)
    import json
    text = json.loads((tmp_path/'data/interim/textos_analisis.json').read_text())['docs/CP1_RESULTADOS.md']['texto']
    assert not (tmp_path/'docs').exists()
    assert text.index('Ronda 6 — 2021') < text.index('## Sección secundaria')
    assert 'filtro directo 60+' not in wave_interpretation(tables,1)
    source = nbformat.read(Path(__file__).resolve().parents[1]/'notebooks/02_EDA_COMPLETO.ipynb',as_version=4)
    cells = '\n'.join(c.source for c in source.cells)
    assert 'CP1 conserva todas las edades/modalidades' in cells
    assert cells.index("display_section('poblacion'") < cells.index("display_section('pensiones'")
    assert all(not c.get('outputs') for c in source.cells if c.cell_type == 'code')
