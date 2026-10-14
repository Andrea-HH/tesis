"""Exportación segura, reconciliación y equivalencia con agregados sintéticos."""
import pandas as pd
import pytest
from pathlib import Path
import runpy

from tesis_enasem.audit import build_audit
from tesis_enasem.cp1_review import investigate_anomalies
from tesis_enasem.manuscript import FrequencyCell, build_cp1_latex, render_latex_table


@pytest.mark.parametrize('defined', [False, True])
def test_formal_numeric_reference_cannot_disappear_silently(tmp_path, defined):
    """TeX aceptaría una csname ausente como relax: el control debe detectarla."""
    script = Path(__file__).resolve().parents[1] / 'scripts/validate_manuscript.py'
    validate = runpy.run_path(str(script))['validate_manuscript']
    (tmp_path / 'referencias.bib').write_text('')
    definition = r'\expandafter\def\csname tesisdato:K.contraste\endcsname{-25}' if defined else ''
    (tmp_path / 'main.tex').write_text(definition + r'\dato{K.contraste}')
    if defined:
        assert validate(tmp_path) == (1, 0, 0)
    else:
        with pytest.raises(ValueError, match='Cifras académicas sin agregado'):
            validate(tmp_path)


def synthetic_tables() -> dict[str, pd.DataFrame]:
    """Seis rondas, entrada tardía, sustituto, fallecido y menor de 60."""
    raw = pd.DataFrame({
        'cunicah': [321]*6 + [654]*2 + [987], 'np': [1]*9,
        'ronda': [1, 2, 3, 4, 5, 6, 3, 4, 1],
        'tipent': [2, 1, 1, 1, 1, 1, 4, 5, 2],
        'edad': [60, 62, 71, 74, 77, 80, 59, None, 40],
        'sexo': [1]*6 + [2]*3, 'fallecido': [0]*7 + [1, 0],
        'a_o_ent': [2001, 2003, 2012, 2015, 2018, 2021, 2012, None, 2001],
        'a_o_nac': [1941]*6 + [1953]*2 + [1961], 'mes_nac': [3]*9,
        'urbano': [0]*9, 'est_conyugal': [1]*9, 'educacion': [6]*9,
        'edu_gru': [2]*9, 'imp_neto': [10]*9, 'orientacion': [None]*9, 'serial7': [None]*9,
        'edad_gru': [2, 2, 3, 3, 3, 4, 1, None, 0],
    })
    for year in ['01', '03', '12', '15', '18', '21']:
        raw[f'factori_{year}'] = 1
        raw[f'factorh_{year}'] = 1
    tables = build_audit(raw)
    tables.update({'anomalias_' + name: frame for name, frame in investigate_anomalies(raw).items()})
    return tables


def test_latex_escapes_category_text_and_rejects_identifiers():
    table = pd.DataFrame({'Categoría': ['A&B_50%'], 'Frecuencia': [FrequencyCell(1250, 12.5)]})
    text = render_latex_table(table, 'Título', 'tab:prueba', 'N=10000; sin pesos')
    assert r'A\&B\_50\%' in text
    assert r'1\,250' in text and r'12,50\%' in text
    for identifier in ['id', 'person_id', 'cunicah', 'np']:
        with pytest.raises(ValueError, match='identificadores'):
            render_latex_table(table.assign(**{identifier: 'privado'}), 'Título', 'tab:prueba', '')


def test_cp1_export_matches_counts_and_does_not_mutate_sources():
    tables = synthetic_tables()
    before = {name: frame.copy(deep=True) for name, frame in tables.items()}
    exported = build_cp1_latex(tables)
    assert r'\newcommand{\cpTotalRegistros}{9}' in exported['cp1_cifras.tex']
    assert r'\newcommand{\cpTotalPersonas}{3}' in exported['cp1_cifras.tex']
    assert r'\newcommand{\cpBalancePersonas}{1}' in exported['cp1_cifras.tex']
    assert r'\newcommand{\cpEdadPares}{0}' in exported['cp1_cifras.tex']
    assert r'\begin{longtable}' in exported['cp1_muestras_ronda.tex']
    for wave, n in zip([2001, 2003, 2012, 2015, 2018, 2021], [2, 1, 2, 2, 1, 1]):
        assert f'{wave} & {n} & {n}' in exported['cp1_rondas.tex']
    for name, frame in tables.items():
        pd.testing.assert_frame_equal(frame, before[name])


def test_cp1_export_stops_on_unreconciled_totals_and_distributions():
    tables = synthetic_tables()
    tables['rondas'].loc[0, 'registros'] += 1
    with pytest.raises(ValueError, match='totales'):
        build_cp1_latex(tables)
    tables = synthetic_tables()
    index = tables['demografia'].index[tables['demografia'].variable.eq('tipent')][0]
    tables['demografia'].loc[index, 'n'] += 1
    with pytest.raises(ValueError, match='Distribución incompleta'):
        build_cp1_latex(tables)
