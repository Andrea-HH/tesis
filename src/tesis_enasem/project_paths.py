"""Ubicaciones únicas del proyecto y compatibilidad documentada de rutas históricas."""
from __future__ import annotations

import json
from pathlib import Path
from functools import lru_cache

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data/raw"
INTERIM_DIR = PROJECT_ROOT / "data/interim"
PROCESSED_DIR = PROJECT_ROOT / "data/processed"
DICTIONARY_DIR = PROJECT_ROOT / "diccionarios"
RESULTS_DIR = PROJECT_ROOT / "resultados"
FIGURES_DIR = RESULTS_DIR / "figuras"
RESEARCH_DIR = PROJECT_ROOT / "investigacion"
MANUSCRIPT_DIR = PROJECT_ROOT / "manuscrito"


@lru_cache(maxsize=1)
def route_map() -> dict:
    """Lee equivalencias; no altera bases, definiciones o directorios históricos."""
    path = DICTIONARY_DIR / "rutas_migracion.json"
    return json.loads(path.read_text()) if path.exists() else {"archivos": {}, "directorios": {}}


@lru_cache(maxsize=1)
def chapter_sections() -> dict:
    """Localiza bloques históricos dentro de capítulos completos, sin recrearlos."""
    path = INTERIM_DIR / 'migracion_proyecto.json'
    if not path.exists():
        return {}
    return json.loads(path.read_text()).get('consolidacion_capitulos', {}).get('secciones', {})


def chapter_section(path: Path) -> dict | None:
    """Devuelve la ubicación del bloque que solicita un exportador anterior."""
    try:
        key = project_path(path).relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return None
    return chapter_sections().get(key)


def section_bounds(text: str, section: dict) -> tuple[int, int]:
    """Exige marcadores únicos antes de leer o actualizar una sección conservada."""
    start, end = section['inicio'], section['fin']
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError('Marcadores de sección ausentes o duplicados; capítulo intacto.')
    left = text.index(start) + len(start)
    right = text.index(end)
    if right < left:
        raise ValueError('Orden de marcadores inválido; capítulo intacto.')
    return left, right


def project_path(*parts: object) -> Path:
    """Resuelve una ruta actual o histórica a su ubicación única, sin crear nada."""
    value = Path(*[str(p) for p in parts])
    if value.is_absolute():
        try:
            value = value.relative_to(PROJECT_ROOT)
        except ValueError:
            return value
    key = value.as_posix()
    routes = route_map()
    if key in routes["archivos"]:
        return PROJECT_ROOT / routes["archivos"][key]
    # Imported directory constants may already resolve to a new cache directory.
    # Recover a moved metadata file explicitly, without keeping another physical copy.
    for old, new in sorted(routes["directorios"].items(), key=lambda pair: -len(pair[1])):
        if key.startswith(new + "/"):
            historical = old + key[len(new):]
            if historical in routes["archivos"]:
                return PROJECT_ROOT / routes["archivos"][historical]
    if key.startswith('docs/') and value.suffix == '.md':
        return INTERIM_DIR / 'textos_virtuales' / key
    for old, new in sorted(routes["directorios"].items(), key=lambda pair: -len(pair[0])):
        if key == old or key.startswith(old + "/"):
            return PROJECT_ROOT / new / key[len(old):].lstrip("/")
    return PROJECT_ROOT / value


def read_project_text(path: Path, *args: object, **kwargs: object) -> str:
    """Lee archivos reales o textos históricos consolidados, sin cientos de fichas."""
    resolved = project_path(path)
    if section := chapter_section(resolved):
        text = (PROJECT_ROOT / section['capitulo']).read_text(*args, **kwargs)
        left, right = section_bounds(text, section)
        return text[left:right]
    if "textos_virtuales" in resolved.parts:
        key = resolved.relative_to(INTERIM_DIR / "textos_virtuales").as_posix()
        store = json.loads((INTERIM_DIR / "textos_analisis.json").read_text())
        return store[key]["texto"]
    return resolved.read_text(*args, **kwargs)


def read_project_bytes(path: Path) -> bytes:
    """Permite cotejar huellas de notas consolidadas sin recrear archivos antiguos."""
    resolved = project_path(path)
    return read_project_text(resolved).encode() if 'textos_virtuales' in resolved.parts or chapter_section(resolved) else resolved.read_bytes()


def write_project_text(path: Path, text: str, *args: object, **kwargs: object) -> int:
    """Consolida notas generadas; los scripts no recrean informes dispersos."""
    resolved = project_path(path)
    if "textos_virtuales" in resolved.parts:
        key = resolved.relative_to(INTERIM_DIR / "textos_virtuales").as_posix()
        target = INTERIM_DIR / "textos_analisis.json"
        store = json.loads(target.read_text()) if target.exists() else {}
        if key in store and store[key].get('texto') != text:
            store[key].setdefault('texto_original', store[key]['texto'])
        store.setdefault(key, {})["texto"] = text
        target.write_text(json.dumps(store, ensure_ascii=False, indent=2) + "\n")
        if key.startswith(('docs/eda/variables/', 'docs/eda/k2021/')):
            import re
            fiche_path = DICTIONARY_DIR / 'fichas_variables.json'
            fiches = json.loads(fiche_path.read_text())
            fiche = next((r for r in fiches if r['origen'] == key), None)
            if fiche is None:
                fiche = {'variable': Path(key).stem, 'origen': key}
                fiches.append(fiche)
            fiche['texto_conservado'] = text
            fiche['secciones'] = [{'titulo': m.group(1), 'contenido': m.group(2)} for m in re.finditer(r'(?ms)^## ([^\n]+)\n(.*?)(?=^## |\Z)', text)]
            fiche_path.write_text(json.dumps(fiches, ensure_ascii=False, indent=2) + '\n')
        return len(text)
    if resolved.suffix == '.tex':
        import os
        import re
        def image(match: re.Match) -> str:
            target = project_path('manuscrito/' + match.group(1))
            return match.group(0).replace(match.group(1), os.path.relpath(target, MANUSCRIPT_DIR)) if target.exists() else match.group(0)
        text = re.sub(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}', image, text)
        text = text.replace(r'\bibliography{referencias}', r'\bibliography{../investigacion/referencias}')
    if section := chapter_section(resolved):
        target = PROJECT_ROOT / section['capitulo']
        chapter = target.read_text(*args, **kwargs)
        left, right = section_bounds(chapter, section)
        replacement = text if text.endswith('\n') else text + '\n'
        target.write_text(chapter[:left] + replacement + chapter[right:], *args, **kwargs)
        return len(text)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved.write_text(text, *args, **kwargs)


def write_analysis_note(root: Path, historical_key: str, text: str) -> None:
    """Guarda una contribución académica en el registro único, también en tests sintéticos."""
    path = root / 'data/interim/textos_analisis.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    store = json.loads(path.read_text()) if path.exists() else {}
    if historical_key in store and store[historical_key].get('texto') != text:
        store[historical_key].setdefault('texto_original', store[historical_key]['texto'])
    store.setdefault(historical_key, {})['texto'] = text
    path.write_text(json.dumps(store, ensure_ascii=False, indent=2) + '\n')
