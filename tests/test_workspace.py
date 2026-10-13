"""Garantías estructurales: sin microdatos y sin repetir fórmulas científicas."""
from pathlib import Path
import json
import pytest

from tesis_enasem import project_paths
from tesis_enasem.workspace import convert_links, markdown_table, preserve_editorial_sections


def test_explicit_route_and_external_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(project_paths, 'PROJECT_ROOT', tmp_path)
    monkeypatch.setattr(project_paths, 'DICTIONARY_DIR', tmp_path/'diccionarios')
    project_paths.DICTIONARY_DIR.mkdir()
    (project_paths.DICTIONARY_DIR/'rutas_migracion.json').write_text(json.dumps({'archivos':{'docs/x.json':'diccionarios/x.json'},'directorios':{'reports/tables':'data/interim/cp1'}}))
    project_paths.route_map.cache_clear()
    assert project_paths.project_path('docs/x.json') == tmp_path/'diccionarios/x.json'
    assert project_paths.project_path('reports/tables','a.json') == tmp_path/'data/interim/cp1/a.json'
    assert project_paths.project_path('/unrelated/data/file') == Path('/unrelated/data/file')
    project_paths.route_map.cache_clear()


def test_unknown_is_not_zero_in_report():
    rendered = markdown_table([{'grupo':'A', 'N':2,'monto':None}, {'grupo':'B','N':0,'monto':-5}])
    assert '| A | 2 | ND |' in rendered
    assert '| B | 0 | -5 |' in rendered


def test_official_links_are_not_rerouted():
    text='[Fuente oficial](https://mhasweb.org/DataProducts/Home.aspx)'
    assert convert_links(text, 'docs/FUENTES.md') == text


def test_manual_interpretation_survives_future_export():
    from hashlib import sha256
    before='<a id="seccion-poblacion"></a>\n\nTabla y límites originales.\n\n'
    edited=before+'Interpretación revisada por la autora.\n'
    proposed={'poblacion':'<a id="seccion-poblacion"></a>\n\nNueva salida automática.'}
    metadata={'secciones':{'poblacion':{'sha_generado':sha256(before.encode()).hexdigest()}}}
    result,protected=preserve_editorial_sections(edited,metadata,proposed)
    assert result['poblacion']==edited and protected==['poblacion']


def test_documentary_validation_rejects_missing_interpretation(monkeypatch, tmp_path):
    from tesis_enasem import workspace

    origin = 'docs/hallazgo.md'
    note = '# Hallazgo\n\nTabla: 2 de 5 observaciones.\n\nEl denominador incluye ND.'
    report = ('<a id="seccion-hallazgos"></a>\n\n'
              f'<a id="{workspace.source_anchor(origin)}"></a>\n\n'
              'Tabla: 2 de 5 observaciones.\n')
    result_dir = tmp_path / 'resultados'
    result_dir.mkdir()
    (tmp_path / 'README.md').write_text('Proyecto sintético')
    target = result_dir / 'INFORME_GENERAL.md'
    target.write_text(report)
    monkeypatch.setattr(workspace, 'PROJECT_ROOT', tmp_path)
    monkeypatch.setattr(workspace, 'RESULTS_DIR', result_dir)
    monkeypatch.setattr(workspace, 'RESEARCH_DIR', tmp_path / 'investigacion')
    def synthetic_json(path):
        if path.endswith('textos_analisis.json'):
            return {origin: {'texto': note}}
        return {'origenes': [{'origen': origin}], 'secciones': {
            'hallazgos': {'inicio': 0, 'fin': len(target.read_text())}}}
    monkeypatch.setattr(workspace, 'load_json', synthetic_json)
    with pytest.raises(AssertionError, match='Contribuciones ausentes'):
        workspace.validate_documentary_coverage()
    target.write_text(report + '\nEl denominador incluye ND.\n')
    evidence = workspace.validate_documentary_coverage()
    assert evidence['documentos_legibles'] == 1
    assert evidence['bloques_ausentes'] == 0
