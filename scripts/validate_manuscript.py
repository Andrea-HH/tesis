"""Comprueba dependencias/citas del LaTeX sin datos privados ni motor TeX."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text

from collections import Counter
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def validate_manuscript(directory: Path) -> tuple[int, int, int]:
    """Valida enlaces, referencias, macros y claves; no sustituye compilación."""
    files = list(directory.rglob('*.tex'))
    files = [path for path in files if 'build' not in path.relative_to(directory).parts]
    text = '\n'.join(re.sub(r'(?<!\\)%[^\n]*', '', read_project_text(p)) for p in files)
    for relative in re.findall(r'\\(?:input|include)\{([^}]+)\}', text):
        path = directory / relative
        if path.suffix != '.tex':
            path = path.with_suffix('.tex')
        if not path.is_file():
            raise ValueError(f'Dependencia LaTeX inexistente: {relative}')
    for relative in re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}', text):
        if not (directory / relative).is_file():
            raise ValueError(f'Figura inexistente: {relative}')
    labels = re.findall(r'\\label\{([^}]+)\}', text)
    duplicates = [name for name, n in Counter(labels).items() if n > 1]
    if duplicates:
        raise ValueError(f'Etiquetas repetidas: {duplicates}')
    references = set(re.findall(r'\\(?:ref|eqref)\{([^}]+)\}', text))
    if missing := references - set(labels):
        raise ValueError(f'Referencias no definidas: {sorted(missing)}')
    main = read_project_text(directory / 'main.tex') if (directory / 'main.tex').exists() else ''
    chapters_dir = directory / 'capitulos'
    if chapters_dir.exists():
        chapters = list(chapters_dir.rglob('*.tex'))
        for chapter in chapters:
            body = re.sub(r'(?<!\\)%[^\n]*', '', read_project_text(chapter))
            if chapter.parent != chapters_dir or len(re.findall(r'\\chapter\{', body)) != 1:
                raise ValueError(f'Se requiere un capítulo completo por archivo: {chapter.name}')
            if re.search(r'\\(?:input|include)\{capitulos/', body):
                raise ValueError(f'Módulo separado de sección: {chapter.name}')
        included = re.findall(r'\\(?:input|include)\{(capitulos/[^}]+)\}', main)
        expected = {p.relative_to(directory).with_suffix('').as_posix() for p in chapters}
        if len(included) != len(set(included)) or set(included) != expected:
            raise ValueError('main.tex debe incorporar todos los capítulos una sola vez.')
    bibliography_paths = re.findall(r'\\bibliography\{([^}]+)\}', main)
    bibliography = '\n'.join(read_project_text((directory / name).with_suffix('.bib'))
                              for names in bibliography_paths for name in names.split(',')) if bibliography_paths else read_project_text(directory / 'referencias.bib')
    keys = re.findall(r'@\w+\s*\{\s*([^,\s]+)', bibliography)
    if len(keys) != len(set(keys)):
        raise ValueError('Claves bibliográficas repetidas.')
    citations = set()
    for group in re.findall(r'\\cite(?:p|t|author|yearpar|year)?(?:\[[^]]*\]){0,2}\{([^}]+)\}', text):
        citations.update(k.strip() for k in group.split(','))
    if missing := citations - set(keys):
        raise ValueError(f'Citas inexistentes: {sorted(missing)}')
    macro_definitions = set(re.findall(r'\\newcommand\{\\(cp[A-Za-z]+)\}', text))
    macro_uses = set(re.findall(r'\\(cp[A-Za-z]+)\b', text))
    if missing := macro_uses - macro_definitions:
        raise ValueError(f'Cifras sin exportación: {sorted(missing)}')
    # Cada entorno debe abrirse/cerrarse la misma cantidad de veces.
    if Counter(re.findall(r'\\begin\{([^}]+)\}', text)) != Counter(re.findall(r'\\end\{([^}]+)\}', text)):
        raise ValueError('Entornos LaTeX sin cierre.')
    return len(files), len(citations), len(labels)


if __name__ == '__main__':
    n_files, n_citations, n_labels = validate_manuscript(project_path('', 'manuscrito'))
    print(f'Manuscrito validado: {n_files} fuentes, {n_citations} referencias bibliográficas utilizadas, {n_labels} etiquetas; sin dependencia de microdatos.')
