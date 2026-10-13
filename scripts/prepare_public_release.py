"""Prepara una edición pública revisable sin borrar históricos ni transferir datos."""
from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import subprocess

from tesis_enasem.project_paths import PROJECT_ROOT, INTERIM_DIR, RESULTS_DIR
from tesis_enasem.publication import (assert_no_direct_disclosure, sanitize_local_paths,
                                    public_latex, public_notebook, validate_coarse_counts, SECRET_SIGNATURE)
from tesis_enasem.workspace import markdown_table

DESTINATION = INTERIM_DIR / 'publicacion_github'
MANIFEST = INTERIM_DIR / 'propuesta_git.json'
SAFE_FIGURE = '../resultados/figuras/figures__cp1_participacion.png'
SAFE_TABLES = {'cp1_muestras.tex', 'cp1_participacion.tex'}
EXCLUDED_DICTIONARIES = {'fichas_variables.json', 'especificaciones_documentales.json',
                        'reports__tables__pensiones_inventario.json',
                        'eda__proteccion_economica__versiones_fuente.json',
                        'eda__k2021_universos_revision.json',
                        'eda__pensiones_exploratorio_v1__universos_conyuge.json'}


def git(*args: str, input_text: str | None = None) -> str:
    """Ejecuta operaciones explícitas; nunca commit/push ni modificaciones de archivos."""
    return subprocess.check_output(['git', '--no-optional-locks', *args], cwd=PROJECT_ROOT,
                                   input=input_text, text=True).strip()


def write_public(relative: str, content: str | bytes) -> None:
    """Escribe solo en el paquete intermedio; las ediciones locales siguen intactas."""
    target = DESTINATION / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        target.write_bytes(content)
    else:
        if relative.startswith('tests/'):
            # La única coincidencia revisada es el ID ficticio del test de formatos.
            if SECRET_SIGNATURE.search(content):
                raise ValueError('Credencial en tests')
        else:
            assert_no_direct_disclosure(content)
        target.write_text(sanitize_local_paths(content))


def metadata_only(value: object) -> object:
    """Retiene hechos de esquema y reglas propias, sin mediciones ni etiquetas copiadas."""
    if isinstance(value, dict):
        denied = {'etiqueta', 'etiqueta_original', 'etiqueta_archivo', 'etiquetas_valores',
                  'labels', 'label', 'texto', 'texto_conservado', 'cobertura',
                  'estadisticos_impresos_proveedor', 'perdidos_especiales',
                  'sha256_contenido_ordenado', 'mediciones', 'distribuciones'}
        return {k: metadata_only(v) for k, v in value.items()
                if k not in denied and not k.startswith(('N_', 'n_', 'pct_', 'porcentaje_'))}
    if isinstance(value, list):
        return [metadata_only(item) for item in value]
    return value


def table_csv(relative: str, rows: list[dict], counts: list[str]) -> int:
    """Exporta agregados ya calculados tras evaluar categorías y todos sus conteos."""
    minimum = validate_coarse_counts(rows, counts)
    target = DESTINATION / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    # Exportación segura en la ubicación académica, sin tocar el informe completo.
    local = PROJECT_ROOT / relative
    if local.exists() and local.read_bytes() != target.read_bytes():
        raise ValueError(f'Exportación existente distinta: {relative}')
    if not local.exists():
        shutil.copy2(target, local)
    return minimum


def prepare() -> dict:
    """Construye una selección acotada, documenta exclusiones y conserva originales."""
    DESTINATION.mkdir(parents=True, exist_ok=True)
    branch, head = git('branch', '--show-current'), git('rev-parse', 'HEAD')
    initial_index = git('ls-files', '--stage') + '\n'
    backup_path = INTERIM_DIR / 'indice_antes_publicacion'
    if not backup_path.exists():
        shutil.copy2(PROJECT_ROOT / '.git/index', backup_path)
        (INTERIM_DIR / 'seleccion_antes_publicacion.txt').write_text(initial_index)
    included: dict[str, dict] = {}

    def record(relative: str, basis: str) -> None:
        public = DESTINATION / relative
        included[relative] = {'ruta': relative, 'bytes': public.stat().st_size,
                             'sha256_publico': sha256(public.read_bytes()).hexdigest(), 'criterio': basis,
                             'version_publica_distinta': (PROJECT_ROOT / relative).is_file() and
                             public.read_bytes() != (PROJECT_ROOT / relative).read_bytes()}

    code = []
    for folder in ['src', 'scripts', 'tests', 'configs', '.github']:
        code.extend(p for p in (PROJECT_ROOT / folder).rglob('*') if p.is_file() and
                    '__pycache__' not in p.parts and '.egg-info' not in str(p) and
                    p.suffix in {'.py', '.yaml', '.yml'})
    for p in code:
        relative = p.relative_to(PROJECT_ROOT).as_posix()
        text = sanitize_local_paths(p.read_text())
        if relative == 'scripts/validate_migration.py':
            # Auditoría del respaldo local, no dependencia de los tests públicos.
            pass
        write_public(relative, text)
        record(relative, 'Código propio; no contiene registros ni credenciales detectadas')
    for name in ['README.md', 'AGENTS.md', '.gitignore', 'pyproject.toml', 'requirements.txt', 'Makefile']:
        p = PROJECT_ROOT / name
        if p.exists():
            write_public(name, p.read_text())
            record(name, 'Configuración/documentación propia sin rutas personales')
    for name in ['raw', 'interim', 'processed']:
        relative = f'data/{name}/.gitkeep'
        write_public(relative, b'')
        record(relative, 'Marcador vacío; ningún dato')

    for p in (PROJECT_ROOT / 'notebooks').glob('*.ipynb'):
        if p.name not in {'01_INTEGRACION.ipynb', '02_EDA_COMPLETO.ipynb'}:
            continue
        relative = p.relative_to(PROJECT_ROOT).as_posix()
        write_public(relative, public_notebook(p.read_text(), principal=True))
        record(relative, 'Código y explicaciones íntegros; outputs/adjuntos vacíos; lectura sin datos')
    for p in (PROJECT_ROOT / 'investigacion/notas/notebooks_historicos').glob('*'):
        if p.suffix not in {'.ipynb', '.md'}:
            continue
        relative = p.relative_to(PROJECT_ROOT).as_posix()
        write_public(relative, public_notebook(p.read_text()) if p.suffix == '.ipynb' else p.read_text())
        record(relative, 'Antecedente propio, sin resultados individuales ni vigencia automática')
    bib = (PROJECT_ROOT / 'investigacion/referencias.bib').read_text()
    bib = re.sub(r'(?m)^\s*file\s*=.*\n', '', bib)
    write_public('investigacion/referencias.bib', bib)
    record('investigacion/referencias.bib', 'Referencias bibliográficas; no PDFs ni adjuntos')

    for p in (PROJECT_ROOT / 'diccionarios').glob('*.json'):
        if p.name in EXCLUDED_DICTIONARIES:
            continue
        obj = json.loads(p.read_text())
        if p.name == 'inventario_fuentes.json':
            fields = ['archivo', 'sha256', 'fuente_id', 'clave_preferida', 'anio_nominal_verificado',
                      'periodo_principal', 'unidad_fila', 'n_registros', 'n_variables', 'columnas']
            obj = {'fuentes': [{k: row[k] for k in fields if k in row} for row in obj['fuentes']],
                   'nota_publica': 'Manifestación de nombres/huellas para obtener fuentes legítimas. '
                   'Regenerar inventario completo localmente antes de integrar; no hay filas ni etiquetas copiadas.'}
        elif p.name == 'diccionario_integrado.json':
            fields = ['columna', 'fuente_id', 'archivo', 'variable_original', 'version', 'producto', 'unidad_fuente', 'ano']
            obj = [{k: row[k] for k in fields if k in row} for row in obj]
        elif p.name == 'mapa_conceptual.json':
            fields = ['columna', 'concepto_candidato', 'dimension', 'dimension_validada', 'variable_fuente',
                      'archivo', 'fuente', 'ronda_ano', 'unidad', 'titularidad', 'comparabilidad', 'periodo', 'producto', 'estado']
            obj = [{k: row[k] for k in fields if k in row} for row in obj]
        else:
            obj = metadata_only(obj)
        relative = p.relative_to(PROJECT_ROOT).as_posix()
        write_public(relative, json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
        record(relative, 'Esquema factual/reglas propias; sin transcripción masiva de etiquetas ni mediciones individuales')

    samples = json.loads((INTERIM_DIR / 'cp1/cp1_muestras.json').read_text())['data']
    sample_fields = ['muestra', 'registros', 'personas', 'denominador_registros', 'denominador_personas',
                     'registros_excluidos', 'personas_excluidas']
    samples = [{k: row[k] for k in sample_fields} for row in samples]
    rounds = json.loads((INTERIM_DIR / 'cp1/cp1_numero_rondas.json').read_text())['data']
    rounds = [{k: row[k] for k in ['rondas_observadas', 'personas', 'denominador_personas', 'porcentaje']} for row in rounds]
    receipt = json.loads((INTERIM_DIR / 'proteccion_economica/resultados.json').read_text())['recepcion']
    receipt = [{k: row[k] for k in ['ano', 'variable', 'N_total', 'N_elegible_vivo', 'N_si', 'N_no',
                                  'N_desconocido', 'N_conocido', 'pct_si_total', 'pct_si_conocido']}
               for row in receipt if row['variable'] in {'pension_propia_k', 'apoyo_propio'}]
    assessments = {}
    for relative, rows, fields in [
        ('resultados/poblacion_muestras.csv', samples, sample_fields[1:]),
        ('resultados/seguimiento_rondas.csv', rounds, ['personas', 'denominador_personas']),
        ('resultados/recepcion_pension_apoyo.csv', receipt, ['N_total', 'N_elegible_vivo', 'N_si', 'N_no', 'N_desconocido', 'N_conocido'])]:
        assessments[relative] = {'minimo_conteo_positivo': table_csv(relative, rows, fields),
                                'desglose': 'Universos amplios; sin ubicación, edad exacta, salud, extremos económicos o claves',
                                'regla': 'Rechazar tabla completa ante frecuencia positiva <5; revisión de márgenes y categorías'}
        record(relative, 'Agregado propio revisado; exportado sin recálculo desde evidencia verificada')
    fig = 'resultados/figuras/figures__cp1_participacion.png'
    # La figura local incluye patrones y solapamientos. Publicar únicamente la
    # distribución amplia evaluada, sin reconstruir desgloses excluidos.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    target = DESTINATION / fig
    target.parent.mkdir(parents=True, exist_ok=True)
    chart, axis = plt.subplots(figsize=(8, 4.5))
    axis.bar([row['rondas_observadas'] for row in rounds], [row['personas'] for row in rounds],
             color=plt.colormaps['BrBG']([0.1, 0.25, 0.4, 0.6, 0.75, 0.9]))
    axis.set(xlabel='Número de rondas observadas', ylabel='Personas únicas',
             title='Participación observada, ENASEM 2001–2021')
    for row in rounds:
        axis.text(row['rondas_observadas'], row['personas'] + 100, f"{row['personas']:,}", ha='center')
    axis.set_ylim(0, max(row['personas'] for row in rounds) * 1.15)
    chart.tight_layout()
    chart.savefig(target, dpi=180)
    plt.close(chart)
    record(fig, 'Gráfica de las seis frecuencias de rondas; conteo mínimo 2025; sin perfiles individuales')
    write_public('resultados/INFORME_GENERAL.md', public_report(samples, rounds, receipt))
    record('resultados/INFORME_GENERAL.md', 'Edición pública de divulgación; informe íntegro local conservado sin cambios')

    for p in (PROJECT_ROOT / 'manuscrito').rglob('*'):
        if not p.is_file() or 'build' in p.parts or p.suffix not in {'.tex', '.md'}:
            continue
        relative = p.relative_to(PROJECT_ROOT).as_posix()
        text = p.read_text()
        if p.suffix == '.tex':
            text = public_latex(text, p.name in SAFE_TABLES, SAFE_FIGURE)
        elif p.name == 'README.md' and p.parent.name == 'manuscrito':
            text = '# Manuscrito modular\n\nCompilar con `python scripts/compile_manuscript.py --engine tectonic`.\nLa edición pública conserva capítulos, referencias y cuadros evaluados; los\ndesgloses reservados muestran una nota y permanecen íntegros localmente.\nEl PDF y auxiliares de build/ no se publican sin aprobación expresa.\n'
        write_public(relative, text)
        record(relative, 'Redacción propia; tablas/figuras no evaluadas reservadas; citas y etiquetas conservadas')
    note = '# Notas propias para la divulgación pública\n\nEl enfoque vigente explora pensiones, titularidad, instituciones y apoyos.\nLos antecedentes prospectivos se conservan sin adoptar pregunta, hipótesis,\noutcome o modelo. La edición íntegra local conserva los 610 documentos,\n29,024 bloques cotejados y toda la investigación. La edición pública no\nredistribuye PDFs de terceros, transcripciones extensas de codebooks ni\nmediciones detalladas cuya divulgación no ha sido evaluada. Referencias\ny enlaces oficiales se conservan en referencias.bib y README.md.\n'
    write_public('investigacion/notas/divulgacion.md', note)
    note_path = PROJECT_ROOT / 'investigacion/notas/divulgacion.md'
    if not note_path.exists():
        note_path.write_text(note)
    record('investigacion/notas/divulgacion.md', 'Síntesis propia; sin fuentes de terceros adjuntas')

    excluded = []
    for p in PROJECT_ROOT.rglob('*'):
        if not p.is_file() or '.git' in p.parts or '__pycache__' in p.parts or p.is_relative_to(DESTINATION):
            continue
        relative = p.relative_to(PROJECT_ROOT).as_posix()
        if relative in included:
            continue
        if relative.startswith('data/'):
            reason = 'Datos/evidencia privada o auxiliar; exclusión completa salvo marcadores vacíos'
        elif relative.startswith(('docs/', 'reports/', 'notebooks/')):
            reason = 'Histórico reemplazado o ejecución auxiliar; local conservado hasta autorización de retiro'
        elif p.suffix.lower() == '.pdf' or relative.startswith('manuscrito/build/'):
            reason = 'Documento local/auxiliar; PDF compilado pendiente de aprobación; terceros sin permiso'
        elif relative.startswith('resultados/figuras/'):
            reason = 'Figura no incluida en la evaluación acotada de divulgación; original local conservado'
        elif relative.startswith('diccionarios/'):
            reason = 'Mediciones/transcripciones voluminosas/duplicados; derechos o divulgación pendientes'
        elif relative.startswith('investigacion/'):
            reason = 'Evidencia técnica/documental o transcripción histórica; síntesis y bibliografía públicas seleccionadas'
        else:
            reason = 'Auxiliar, personal o duplicado fuera de la selección revisada'
        excluded.append({'ruta': relative, 'motivo': reason})
    proposal = {'fecha': '2026-10-13', 'repositorio': 'Andrea-HH/tesis', 'visibilidad': 'public',
                'rama': branch, 'commit_base': head, 'commit_push_merge': 'No realizados',
                'limpieza_fisica': 'Pendiente; no se borraron docs/reports ni archivos históricos',
                'seleccion_inicial_sha256': sha256(initial_index.encode()).hexdigest(),
                'carpeta_revision': str(DESTINATION), 'incluidos': sorted(included.values(), key=lambda x:x['ruta']),
                'excluidos': sorted(excluded, key=lambda x:x['ruta']), 'evaluacion_agregados': assessments,
                'derechos': {'MHAS': 'https://www.mhasweb.org/DataProducts/Home.aspx',
                             'INEGI': 'https://www.inegi.org.mx/inegi/terminos.html',
                             'regla': 'No microdatos ni PDFs de terceros; metadatos factuales y construcción propia, sin transcripciones masivas'},
                'limitaciones': ['El informe público es una selección, no la edición académica íntegra.',
                                 'Desgloses finos y figuras no revisadas no se incluyen; no se certifica anonimato por un umbral solo.',
                                 'El PDF de tesis no está aprobado para publicar.',
                                 'Una reproducción completa requiere fuentes legítimas y evidencia privada regenerada.']}
    MANIFEST.write_text(json.dumps(proposal, ensure_ascii=False, indent=2) + '\n')
    (INTERIM_DIR/'archivos_propuestos_commit.txt').write_text('\n'.join(sorted(included)) + '\n')
    history = INTERIM_DIR / 'historial_publicacion_verificado.json'
    if history.exists():
        proposal['historial'] = json.loads(history.read_text())
        MANIFEST.write_text(json.dumps(proposal, ensure_ascii=False, indent=2) + '\n')
    return proposal


def public_report(samples: list[dict], rounds: list[dict], receipt: list[dict]) -> str:
    """Presenta preguntas, universos, denominadores e interpretaciones de agregados amplios."""
    return '''# Informe general — edición pública de divulgación

Esta edición selecciona resultados amplios evaluados. La edición académica íntegra
local conserva los 610 documentos y todas las tablas, figuras e interpretaciones;
no fue reemplazada. No se distribuyen datos individuales ni detalles de celdas pequeñas.
El umbral de cinco es un filtro conservador de esta preparación, no una regla oficial
ni una certificación de anonimato. Las tablas seleccionadas carecen de claves, edades
exactas, ubicaciones, indicadores de salud y extremos económicos.

## Índice

- [Universos y población](#poblacion)
- [Recepción propia K y A](#recepcion)
- [Seguimiento](#seguimiento)
- [Método y límites](#limites)

<a id="poblacion"></a>
## Universos y población

**Pregunta:** ¿cómo cambian los tamaños de muestra al aplicar filtros distintos?
**Variables:** registros, personas únicas, elegibilidad y exclusiones por filtro.
**Universo:** CP1 completo, 2001–2021; cada filtro se compara por separado.
**Denominadores:** 99,676 personas-ronda y 27,171 personas, no intercambiables.
**Tabla:** [exportación de población](poblacion_muestras.csv).

''' + markdown_table(samples) + '''

**Interpretación:** 60+ por visita conserva 56,004 registros y 18,754 personas;
no es una cohorte balanceada. CP1 no se sustituye por esta submuestra. Los filtros
no se suman. **Límites:** muestra sin ponderación validada; composición cambiante.
**Estado:** descriptivo provisional, sin estimando predictivo aprobado.

<a id="recepcion"></a>
## Recepción propia K y A

**Pregunta:** ¿qué recepción propia se observa por ronda, conservando desconocidos?
**Variables:** ronda, K propia o A propia, N total/elegible/conocido y recepción.
**Universo:** 60+ por visita, personas vivas y ramas orientadas según contratos.
**Denominadores:** N total y N conocido de cada indicador; ND permanece separado.
**Tabla:** [exportación de recepción](recepcion_pension_apoyo.csv).

''' + markdown_table(receipt) + '''

**Interpretación:** en 2021 se registran 3,599 K propias y 5,583 A propias dentro
 de 10,482 observaciones 60+. Sus tasas no son composición entre beneficiarios.
K no acredita contributividad y A no acredita pensión no contributiva. Pensión
propia y del cónyuge no se intercambian. **Límites:** cambios de instrumentos,
elegibilidad y titulares; no interpretar diferencias transversales como altas/bajas
individuales o efectos causales. **Estado:** armonización descriptiva provisional.

<a id="seguimiento"></a>
## Seguimiento

**Pregunta:** ¿cuántas rondas observadas acumulan las mismas personas?
**Variables:** número de rondas observadas y frecuencia de personas.
**Universo:** unión de 27,171 IDs del maestro; no se publican sus valores.
**Denominador:** personas únicas del periodo, no suma de personas por ronda.
**Tabla:** [exportación de seguimiento](seguimiento_rondas.csv).

''' + markdown_table(rounds) + '''

![Número de rondas observadas](figuras/figures__cp1_participacion.png)

**Interpretación:** 6,305 personas tienen seis presencias. Esto no implica seis
entrevistas directas ni elegibilidad 60+ en todas las visitas. **Límites:** muerte,
ausencia, reaparición y desconocimiento se distinguen en el análisis local; los
intervalos son desiguales. **Estado:** descripción del panel no balanceado.

<a id="limites"></a>
## Método, investigación y límites

Identidad `cunicah:np` y unicidad `id+ronda`; formatos preservados. Integración por
LEFT JOIN, puentes históricos y cardinalidad verificada, sin muchos-a-muchos.
Hogar no es persona. Viudez corresponde al beneficiario. Slots e instituciones
múltiples no distribuyen ni replican montos. Original, imputado y construido
no se suman como ingresos independientes. ND no es negativa ni cero.

Los resultados bivariados, trivariados, institucionales, de salud, montos y
trayectorias detalladas permanecen íntegros en la edición local. Su publicación
requiere evaluación específica de celdas, márgenes y reconstrucción; se excluyen
por precaución en esta selección. Las rupturas K2003–2012/K2015–2018 y
A2001–2003/A2018–2021 no son transiciones homologadas.

Pesos/diseño, periodicidad/precios y parte de la documentación histórica siguen
pendientes. Patrimonio compartido es stock, no ingreso individual. No hay
causalidad, significancia no probada, outcome o modelo definitivos. Los protocolos
históricos no gobiernan esta etapa. Validación técnica no es aprobación académica.

Fuentes: elaboración propia con ENASEM/MHAS y contratos documentados. Consultar
las [condiciones oficiales MHAS](https://www.mhasweb.org/DataProducts/Home.aspx),
la [página ENASEM del INEGI](https://www.inegi.org.mx/programas/enasem/2021/) y la
[bibliografía del proyecto](../investigacion/referencias.bib).
'''


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    proposal = prepare()
    print(f"Selección propuesta: {len(proposal['incluidos'])} archivos; índice Git todavía sin modificar.")
