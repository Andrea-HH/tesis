"""Verifica conservación de celdas, sincronización y sustitución segura del PDF."""
from pathlib import Path

import pytest

pytest.importorskip('reportlab')
pytest.importorskip('markdown_it')
pytest.importorskip('pymupdf')
from tesis_enasem import report_pdf as report


def configure(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(report,'PROJECT_ROOT',tmp_path)
    monkeypatch.setattr(report,'RESULTS_DIR',tmp_path/'resultados')
    monkeypatch.setattr(report,'INTERIM_DIR',tmp_path/'data/interim')
    (tmp_path/'resultados').mkdir()
    (tmp_path/'data/interim').mkdir(parents=True)
    return tmp_path/'resultados/INFORME_GENERAL.md'


def test_panels_preserve_every_column_and_two_keys():
    panels=report.table_panels([list(range(13))])
    assert all(p[:2]==[0,1] for p in panels)
    assert [c for p in panels for c in p[2:]]==list(range(2,13))
    assert all(len(p)<=6 for p in panels)


def test_pdf_cells_and_stale_markdown(tmp_path,monkeypatch):
    source=configure(tmp_path,monkeypatch)
    source.write_text('# Informe sintético\n\n## Índice\n\n- [Población](#seccion-poblacion)\n\n<a id="seccion-poblacion"></a>\n\n## 1. Población\n\n**Cuadro 1. Conteos**\n\n| Ronda | Grupo | N | ND | Mediana | P25 | P75 |\n| --- | --- | --- | --- | --- | --- | --- |\n| 2021 | K | 91 | 3 | 42 | 17 | 68 |\n\nInterpretación: 91 observaciones; ND no es negativa.\n')
    evidence=report.generate_report_pdf()
    assert evidence['tablas']==1 and evidence['celdas']==14
    assert evidence['paneles_tabla']==2 and evidence['textos_ausentes']==0
    report.validate_report_sync()
    source.write_text(source.read_text()+'\nResultado nuevo.\n')
    with pytest.raises(AssertionError,match='pendiente de regenerar'):
        report.validate_report_sync()
    assert not list(source.parent.glob('.informe_pdf_*'))


def test_missing_image_preserves_previous_pdf(tmp_path,monkeypatch):
    source=configure(tmp_path,monkeypatch)
    source.write_text('# Informe\n\n## 1. Hallazgo\n\n![Ausente](figuras/ausente.png)\n')
    output=source.with_suffix('.pdf');output.write_bytes(b'PDF anterior')
    with pytest.raises(FileNotFoundError):report.generate_report_pdf()
    assert output.read_bytes()==b'PDF anterior'
