"""Divulgación: tests sintéticos, sin datos privados ni mínimos reales transcritos."""
import json
import pytest

from tesis_enasem.publication import (assert_no_direct_disclosure, public_notebook,
                                    public_latex, validate_coarse_counts)


def test_coarse_table_rejects_small_cell_and_its_margin():
    with pytest.raises(ValueError, match='Celda pequeña'):
        validate_coarse_counts([{'grupo': 'Ficticio', 'N': 2, 'total': 100}], ['N', 'total'])
    with pytest.raises(ValueError, match='clave individual'):
        validate_coarse_counts([{'id': 'ficticio', 'N': 100}], ['N'])
    assert validate_coarse_counts([{'grupo': 'Amplio', 'N': 100}], ['N']) == 100


def test_format_specifier_is_not_a_person_identifier():
    assert_no_direct_disclosure('suffix = f"_{year % 100:02}"')


def test_notebook_keeps_code_and_explanations_without_outputs():
    nb = {'nbformat': 4, 'nbformat_minor': 5, 'metadata': {'private': 'value'}, 'cells': [
        {'cell_type': 'markdown', 'metadata': {}, 'source': '# Explicación', 'attachments': {'private': {}}},
        {'cell_type': 'code', 'metadata': {}, 'source': 'print("Ejemplo sintético")',
         'execution_count': 1, 'outputs': [{'output_type': 'stream', 'text': 'privado'}]}]}
    output = json.loads(public_notebook(json.dumps(nb)))
    assert output['cells'][0]['source'] == '# Explicación'
    assert output['cells'][1]['source'] == 'print("Ejemplo sintético")'
    assert output['cells'][1]['outputs'] == []
    assert 'attachments' not in output['cells'][0]


def test_latex_keeps_caption_label_and_explanation_when_reserving_table():
    text = '\\caption{Resultado}\\label{tab:x}\n\\begin{tabular}{lr}A & 2\\\\\\end{tabular}\nInterpretación propia.'
    output = public_latex(text)
    assert '\\label{tab:x}' in output and '\\caption{Resultado}' in output
    assert 'Interpretación propia.' in output
    assert 'A & 2' not in output
