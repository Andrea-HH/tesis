"""Exportación pública conservadora; nunca modifica microdatos ni resultados privados."""
from __future__ import annotations

import json
import re
from collections.abc import Iterable
from typing import Any

SECRET_SIGNATURE = re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|sk-[A-Za-z0-9_-]{30,}|AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)")
PERSON_ID = re.compile(r"(?<![\w:])\d{3,12}:\d{1,4}(?![\w:}])")
IDENTIFIER_FIELDS = frozenset({'id', 'cunicah', 'np', 'unhhid', 'acthog', 'person_id', 'key_21'})


def sanitize_local_paths(text: str) -> str:
    """Sustituye rutas de máquinas personales; conserva sintaxis y contenidos propios."""
    text = re.sub(r"/(?:Users|home)/[A-Za-z0-9._-]+(?:/[A-Za-z0-9._ ()-]+)*", 'data/raw/archivo_local', text)
    text = re.sub(r"/workspace/tesis(?=/|[\s\"'`]|$)(?:/[A-Za-z0-9._ ()-]+)*", '.', text)
    text = re.sub(r"/opt/miniconda3/envs/[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*", 'python', text)
    text = re.sub(r"/tmp/tesis-tectonic-[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*", 'tectonic', text)
    return text


def assert_no_direct_disclosure(text: str) -> None:
    """Rechaza firmas de secretos e identificadores personales numéricos completos."""
    if SECRET_SIGNATURE.search(text):
        raise ValueError('Firma de credencial: no exportar el archivo')
    if PERSON_ID.search(text):
        raise ValueError('Posible identificador personal: requiere revisión')


def validate_coarse_counts(rows: Iterable[dict[str, Any]], count_fields: Iterable[str], minimum: int = 10) -> int:
    """Evalúa frecuencias de una tabla previamente delimitada a agregados amplios.

    Diez es el criterio conservador de revisión10, no una norma universal de ENASEM.
    Rechazar la tabla completa evita reconstruir una celda mediante sus márgenes.
    No transforma códigos, no imputa ND y no promete anonimato por el umbral solo.
    """
    smallest: int | None = None
    for row in rows:
        if IDENTIFIER_FIELDS.intersection(row):
            raise ValueError('La tabla contiene una clave individual o de hogar')
        for field in count_fields:
            value = row[field]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0 or value != int(value):
                raise ValueError(f'Conteo inválido: {field}')
            if 0 < value < minimum:
                raise ValueError('Celda pequeña: excluir tabla y márgenes de la edición pública')
            if value:
                smallest = int(value) if smallest is None else min(smallest, int(value))
    if smallest is None:
        raise ValueError('No hay frecuencias positivas evaluables')
    return smallest


def public_notebook(text: str, principal: bool = False) -> str:
    """Preserva todas las celdas de código y explicación sin outputs ni adjuntos.

    Los principales funcionan como lectura pública sin evidencia privada. Su código
    analítico íntegro se ejecuta cuando esa evidencia fue regenerada legítimamente.
    """
    notebook = json.loads(text)
    notebook['metadata'] = {'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}}
    code_count = 0
    for cell in notebook['cells']:
        cell.pop('attachments', None)
        cell['metadata'] = {}
        source = sanitize_local_paths(''.join(cell['source']) if isinstance(cell['source'], list) else cell['source'])
        if cell['cell_type'] == 'code':
            cell['execution_count'] = None
            cell['outputs'] = []
            code_count += 1
            if principal:
                if code_count == 1:
                    source += "\nfrom tesis_enasem.project_paths import INTERIM_DIR\nfrom IPython.display import Markdown\nEVIDENCIA_LOCAL = (INTERIM_DIR/'textos_analisis.json').is_file() and (PROCESSED_DIR/'enasem_integrada_provisional.parquet').is_file()\nif not EVIDENCIA_LOCAL:\n    display(Markdown('Lectura pública: consultar resultados/INFORME_GENERAL.md. El cálculo completo requiere fuentes obtenidas legítimamente y evidencia local regenerada.'))"
                else:
                    source = 'if EVIDENCIA_LOCAL:\n' + '\n'.join('    ' + line for line in source.splitlines())
        cell['source'] = source
    assert_no_direct_disclosure(json.dumps(notebook, ensure_ascii=False))
    return json.dumps(notebook, ensure_ascii=False, indent=1) + '\n'


def public_latex(text: str, keep_tables: bool = False, safe_figure: str = '') -> str:
    """Mantiene narrativa, etiquetas y citas; retiene tablas/figuras solo si evaluadas."""
    text = sanitize_local_paths(text)
    text = text.replace('El informe general permite consultar las contribuciones de los 610 documentos',
                        'El informe general local permite consultar las contribuciones de los 610 documentos')
    paragraphs = re.split(r'(\n\s*\n)', text)
    for index, paragraph in enumerate(paragraphs):
        if re.search(r'\bN\s*=\s*[1-9](?![\d\\,.])', paragraph):
            paragraphs[index] = r'\par\emph{Interpretación detallada conservada localmente; estrato pequeño pendiente de revisión de divulgación.}\par'
        elif (re.search(r'\bN\s*=\s*\d', paragraph) and
              re.search(r'patrimonio|ingreso|monto|salario', paragraph, re.I) and
              re.search(r'median|extrem|máxim|mínim|percentil|cuantil', paragraph, re.I)):
            paragraphs[index] = r'\par\emph{Distribución económica detallada conservada localmente; divulgación de cuantiles y extremos pendiente.}\par'
    text = ''.join(paragraphs)
    if not keep_tables:
        def reserve_table(match: re.Match[str]) -> str:
            labels = ''.join(re.findall(r'\\label\{[^}]+\}', match.group(0)))
            note = r'\par\smallskip\emph{Detalle numérico reservado en la edición local; revisión de divulgación pendiente.}\par'
            if match.group('kind') == 'longtable':
                return r'\begin{table}[!htbp]\centering\caption{Cuadro conservado localmente; edición pública}' + labels + note + r'\end{table}'
            return labels + note
        text = re.sub(r'\\begin\{(?P<kind>tabular\*?|longtable|tabularx)\}.*?\\end\{(?P=kind)\}',
                      reserve_table, text, flags=re.S)
    def figure(match: re.Match[str]) -> str:
        if safe_figure and match.group(1).endswith('cp1_participacion.png'):
            return match.group(0).replace(match.group(1), safe_figure)
        return r'\fbox{\parbox{0.85\linewidth}{\centering Figura conservada localmente; no incluida en la edición pública por revisión de divulgación.}}'
    text = re.sub(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}', figure, text)
    def safe_caption(match: re.Match[str]) -> str:
        block = match.group(0)
        if safe_figure and safe_figure in block:
            block = re.sub(r'\\caption\{[^}]*\}',
                           r'\\caption{Número de rondas observadas por persona; edición pública}', block)
        return block
    text = re.sub(r'\\begin\{figure\}.*?\\end\{figure\}', safe_caption, text, flags=re.S)
    # Una macro de conteo pequeño no debe revelar lo que se retiró de su tabla.
    text = re.sub(r'(\\newcommand\{\\cp[A-Za-z]+\}\{)[1-4](\})', r'\1ND público\2', text)
    text = re.sub(r'(\\newcommand\{\\cp[A-Za-z]*(?:Max|Min|Median|Q[0-9]|P[0-9])[A-Za-z0-9]*\}\{)[^}]*\}',
                  r'\1ND público}', text)
    assert_no_direct_disclosure(text)
    return text
