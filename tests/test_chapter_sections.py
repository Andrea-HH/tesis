"""Una actualización exportada conserva el resto del capítulo completo."""
from pathlib import Path

import pytest

from tesis_enasem import project_paths as paths


def setup_section(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """Construye un capítulo sintético con texto anterior y posterior al bloque."""
    monkeypatch.setattr(paths, 'PROJECT_ROOT', tmp_path)
    monkeypatch.setattr(paths, 'route_map', lambda: {'archivos': {}, 'directorios': {}})
    key = 'manuscrito/capitulos/04_seccion_historica.tex'
    target = tmp_path / 'manuscrito/capitulos/04_resultados.tex'
    target.parent.mkdir(parents=True)
    target.write_text('Antes\n% INICIO\nOriginal\n% FIN\nDespués\n')
    monkeypatch.setattr(paths, 'chapter_sections', lambda: {
        key: {'capitulo': str(target.relative_to(tmp_path)),
              'inicio': '% INICIO\n', 'fin': '% FIN\n'}})
    return tmp_path / key, target


def test_export_updates_only_embedded_section(tmp_path, monkeypatch):
    historical, chapter = setup_section(tmp_path, monkeypatch)
    assert paths.read_project_text(historical) == 'Original\n'
    paths.write_project_text(historical, 'Actualización\n')
    assert chapter.read_text() == 'Antes\n% INICIO\nActualización\n% FIN\nDespués\n'
    assert paths.read_project_bytes(historical) == 'Actualización\n'.encode()
    assert not historical.exists()


def test_missing_marker_never_overwrites_chapter(tmp_path, monkeypatch):
    historical, chapter = setup_section(tmp_path, monkeypatch)
    chapter.write_text('Texto académico sin marcadores\n')
    with pytest.raises(ValueError, match='Marcadores'):
        paths.write_project_text(historical, 'Sustitución')
    assert chapter.read_text() == 'Texto académico sin marcadores\n'
    assert not historical.exists()
