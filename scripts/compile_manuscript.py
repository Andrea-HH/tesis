"""Compila el proyecto modular usando un motor disponible; no instala LaTeX."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Usa latexmk, Tectonic o TeX/BibTeX y conserva el PDF local en build/."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', help='Nombre o ruta de latexmk, tectonic, pdflatex o xelatex.')
    args = parser.parse_args()
    engine = args.engine or next((p for name in ['latexmk', 'tectonic', 'pdflatex', 'xelatex']
                                 if (p := shutil.which(name))), None)
    if engine is None:
        print('No hay motor LaTeX disponible. Instalar TeX Live/MacTeX o Tectonic; ver manuscrito/README.md.', file=sys.stderr)
        raise SystemExit(2)
    engine_path = Path(engine)
    name = engine_path.name
    directory = project_path('', 'manuscrito')
    output = directory / 'build'
    output.mkdir(exist_ok=True)
    if name == 'latexmk':
        commands = [[engine, '-pdf', '-interaction=nonstopmode', '-halt-on-error', '-outdir=build', 'main.tex']]
    elif name == 'tectonic':
        commands = [[engine, '--keep-logs', '--keep-intermediates', '--outdir', 'build', 'main.tex']]
    elif name in ['pdflatex', 'xelatex']:
        if not (bibtex := shutil.which('bibtex')):
            raise SystemExit('BibTeX no está disponible: instalarlo o usar latexmk/Tectonic.')
        tex = [engine, '-interaction=nonstopmode', '-halt-on-error', '-output-directory=build', 'main.tex']
        subprocess.run(tex, cwd=directory, check=True)
        environment = dict(os.environ)
        environment['BIBINPUTS'] = str(directory) + os.pathsep + environment.get('BIBINPUTS', '')
        subprocess.run([bibtex, 'main'], cwd=output, env=environment, check=True)
        commands = [tex, tex]
    else:
        raise SystemExit(f'Motor no admitido: {name}')
    for command in commands:
        subprocess.run(command, cwd=directory, check=True)
    if not (output / 'main.pdf').exists():
        raise SystemExit('La compilación no produjo main.pdf.')
    print('PDF local:', output / 'main.pdf')


if __name__ == '__main__':
    main()
