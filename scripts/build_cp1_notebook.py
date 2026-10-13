from tesis_enasem.project_paths import project_path, read_project_text, write_project_text
"""Actualiza el notebook CP1: universo completo primero y subpoblaciones al final."""
from pathlib import Path
import sys
import nbformat as nb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_path('', 'src')))
from tesis_enasem.audit_report import CP1_INTRO, CP1_CONCLUSIONS
from tesis_enasem.config import ROUND_TO_YEAR


def main() -> None:
    """Modifica el notebook existente, preservando sus metadatos de entorno."""
    path = project_path('', 'notebooks/02_construccion_muestra.ipynb')
    notebook = nb.read(path, as_version=4)
    cells = [nb.v4.new_markdown_cell(CP1_INTRO), nb.v4.new_code_cell('''import sys
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display, Markdown
from tesis_enasem.config import RAW_DIR, REPORTS_DIR
from tesis_enasem.io import load_stata
from tesis_enasem.audit import build_audit
from tesis_enasem.cp1_review import review_transitions
from tesis_enasem.audit_report import (plot_wave, plot_longitudinal, wave_interpretation,
                                      followup_interpretation, subpopulation_interpretation)
print('Intérprete:', sys.executable)
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
raw = load_stata(RAW_DIR / 'simpleMHAS.dta', preserve_missing=True)
# La referencia general conserva TODAS las filas, edades y modalidades.
POBLACION = None
assert POBLACION is None, 'Este notebook principal audita la población completa.'
tables = build_audit(raw, population=POBLACION)
assert tables['estructura'].registros.iloc[0] == len(raw)
assert tables['estructura'].registros_excluidos_por_seleccion.iloc[0] == 0
# Nunca mostrar raw, claves individuales ni matriz privada de participación.
display(tables['estructura'], tables['consistencia'], tables['rondas'], tables['edad'], tables['educacion'])''')]
    for wave, year in ROUND_TO_YEAR.items():
        cells += [nb.v4.new_markdown_cell(f'''## Ronda {wave} ({year}) — toda la población registrada

**Introducción y objetivo.** Describir la población de esta ronda conservando menores de 60, directas, sustitutos, entrevistas sobre fallecidos y todas las trayectorias.

**Justificación y metodología.** Las frecuencias incluyen edades faltantes y otras causas en el denominador completo de la ronda. Los estadísticos continuos emplean solo información válida. Los grupos de edad se derivan de edad sin alterar edad_gru. La educación utiliza años y categorías del diccionario; el tamaño de localidad usa el corte de 100 mil habitantes.

**Procedimiento.** Se tabulan conteos y porcentajes de entrevista, edad, sexo, estado conyugal, escolaridad y localidad; las entradas y ausencias provienen del panel completo. El número de rondas utiliza toda la historia observada con finalidad descriptiva. La auditoría de cobertura incluye cada columna original y cada código especial. No se aplican filtros en esta ficha.'''), nb.v4.new_code_cell(f'''wave = {wave}
for name in ['rondas', 'edad_grupos', 'edad', 'demografia', 'educacion', 'entradas',
             'seguimiento_ronda', 'participacion_ronda', 'cronologia', 'pesos', 'faltantes']:
    display(Markdown('### ' + name.replace('_', ' ').capitalize()))
    tab = tables[name].loc[tables[name].ronda.eq(wave)]
    if tab.empty:
        display(Markdown('No aplica: no hay ronda previa dentro del archivo.'))
    else:
        display(tab)
fig = plot_wave(raw, wave, REPORTS_DIR / 'figures')
plt.show()
plt.close(fig)
display(Markdown(wave_interpretation(tables, wave)))''')]
    cells += [nb.v4.new_markdown_cell('''## Seguimiento longitudinal de toda la población

**Introducción y objetivo.** Identificar incorporación, continuidad, modalidades, ausencia y reaparición para todas las personas registradas.

**Método y procedimiento.** La presencia es cualquier registro persona-ronda, incluidas entrevistas sobre fallecidos. Las matrices privadas se convierten en intersecciones y patrones agregados sin IDs. Las transiciones usan todo el denominador de origen y separan ausencias tras fallecimiento previo de ausencias sin ese antecedente. Una reaparición requiere historia previa y ausencia en la ronda inmediata anterior. La comparación de composición en origen conserva todos los registros: una media de edad válida no representa a quienes carecen de edad. Los intervalos nominales y efectivos son distintos. No se infiere muerte por ausencia.'''), nb.v4.new_code_cell('''for name in ['numero_rondas', 'entradas', 'seguimiento_ronda', 'patrones', 'intersecciones',
             'transiciones', 'estados', 'intervalos_efectivos', 'perfiles_seguimiento']:
    display(Markdown('### ' + name.replace('_', ' ').capitalize()))
    display(tables[name])
display(Markdown('### Ausencias con y sin reaparición posterior observada'))
display(review_transitions(tables))
display(Markdown('Los porcentajes de reaparición posterior usan el origen completo. '
                 'Ausencia sin retorno registrado hasta 2021 no prueba pérdida definitiva; '
                 'la última transición está limitada por el cierre de observación.'))
fig = plot_longitudinal(tables, REPORTS_DIR / 'figures')
plt.show()
plt.close(fig)
display(Markdown(followup_interpretation(tables)))'''),
              nb.v4.new_markdown_cell('''## Revisión puntual de anomalías — sin corregir registros

**Objetivo y método.** Ampliar las alertas ya calculadas, únicamente con agregados. Después de la primera ronda con tipent=5 se cuentan registros posteriores; sexo se evalúa por número de códigos válidos distintos. Para edad se compara con el registro observado inmediatamente anterior cuando ambas edades son válidas: una edad faltante interrumpe el par. No se publican claves ni historias de los casos raros.

**Interpretación y límites.** El contraste de edad con [año efectivo − año de nacimiento − 1, año efectivo − año de nacimiento] es aproximado y depende de ambos años; no corrige edad ni certifica nacimiento. Revisar modalidad y maestro de seguimiento para fallecimiento, sexo original sex_xx y validación del proveedor (nota ENASEMsimple v2, pp. 6–7), y derivación de edad/fechas. Errores de respuesta, captura, enlace o revisión son hipótesis pendientes, no causas demostradas. La coherencia tipent/fallecido dentro de ronda no valida toda la secuencia. Los incrementos no negativos de edad no quedan validados por esta prueba de descenso.

Ver el desarrollo académico completo en [CP1_INFORME_REVISION.md](../../docs/CP1_INFORME_REVISION.md), sección 4. Las reglas metodológicas permanecen pendientes de aprobación.'''),
              nb.v4.new_code_cell('''from tesis_enasem.cp1_review import investigate_anomalies, plot_anomalies
anomalies = investigate_anomalies(raw)
for name, tab in anomalies.items():
    display(Markdown('### ' + name.replace('_', ' ').capitalize()))
    display(tab)
checks = anomalies['resumen'].set_index('control').n
display(Markdown(
    f"Los {checks['registros_posteriores_fallecimiento']:,} registros posteriores a fallecimiento "
    f"afectan a {checks['personas_posteriores_fallecimiento']:,} persona(s). "
    f"Los {checks['pares_edad_decreciente']:,} descensos de edad afectan a "
    f"{checks['personas_edad_decreciente']:,} personas, entre "
    f"{checks['pares_edad_evaluables']:,} pares evaluables "
    f"({100*checks['pares_edad_decreciente']/checks['pares_edad_evaluables']:.2f}%). "
    f"{checks['pares_descenso_cruzan_60']:,} pares cruzan de 60+ a menos de 60. "
    "Ninguna alerta decide por sí misma qué registro es correcto. Se conservan los originales."
))
fig = plot_anomalies(anomalies, REPORTS_DIR / 'figures')
plt.show()
plt.close(fig)'''),
              nb.v4.new_markdown_cell('''## Sección secundaria — comparación de subpoblaciones

**Introducción y objetivo.** Evaluar filtros después de completar la auditoría general, sin reemplazar la población completa.

**Método y procedimiento.** Cada alternativa se compara independientemente con el original de su ronda: registros/personas conservados + excluidos = total. Los porcentajes tienen denominadores separados para registros y personas. En el periodo completo, una persona solo se excluye si no conserva ninguna visita; las exclusiones de personas por ronda no se suman.

El panel no balanceado conserva todo el universo (1–6 rondas) y el balanceado exige seis rondas de cualquier edad y entrevista. Las versiones seis directas o seis directas 60+ son filtros adicionales. Se conserva un flujo secuencial para la candidata directa 60+, únicamente como sensibilidad posterior. Se compara composición por edad ampliada, sexo, educación, estado conyugal, localidad y modalidad. La definición del estimando predictivo queda pendiente.'''), nb.v4.new_code_cell('''for name in ['muestras', 'muestras_ronda', 'flujo', 'composicion_muestras']:
    display(Markdown('### ' + name.replace('_', ' ').capitalize()))
    display(tables[name])
display(Markdown(subpopulation_interpretation(tables)))'''),
              nb.v4.new_markdown_cell(CP1_CONCLUSIONS),
              nb.v4.new_markdown_cell('''## Correspondencia CP1 → manuscrito LaTeX

**Objetivo.** Mantener escritura y análisis en paralelo. Los resultados de este notebook sustentan el capítulo 3 del manuscrito; el capítulo 1 plantea pregunta, objetivos e hipótesis. Las decisiones pendientes siguen siendo provisionales.

**Método.** Se exportan tablas y macros numéricas desde los mismos agregados en memoria; nunca desde microdatos o historias individuales. El manuscrito selecciona tablas informativas, conservando aquí la auditoría extensa. Se generan dos figuras agregadas en `manuscrito/figuras/borradores/`, pendientes de aprobación editorial. La plantilla UDLAP debe confirmarse antes de adoptar un formato final.

**Reproducción.** El script `scripts/export_cp1_manuscript.py` permite repetir la exportación desde JSON agregados existentes y registrar trazabilidad; `--check` contrasta archivos con esos agregados. El PDF se compila con `scripts/compile_manuscript.py`. La compilación no necesita el microdato si las tablas y figuras exportadas están presentes.'''),
              nb.v4.new_code_cell('''from IPython.display import Image
from tesis_enasem.config import PROJECT_ROOT
from tesis_enasem.manuscript import build_cp1_latex, export_cp1_figures
manuscript_tables = {**tables, **{'anomalias_' + name: tab for name, tab in anomalies.items()}}
latex_exports = build_cp1_latex(manuscript_tables)
manuscript_directory = PROJECT_ROOT / 'manuscrito'
(manuscript_directory / 'tablas').mkdir(parents=True, exist_ok=True)
for name, text in latex_exports.items():
    (manuscript_directory / 'tablas' / name).write_text(text, encoding='utf-8')
figures = export_cp1_figures(manuscript_tables, manuscript_directory / 'figuras' / 'borradores')
display(Markdown(f"Exportados {len(latex_exports)} archivos LaTeX (tablas y cifras). "
                 "Población completa; frecuencia sin ponderación. Figuras para revisión editorial:"))
for path in figures:
    display(Image(filename=str(path)))
display(Markdown('**Conclusión:** las cifras del manuscrito proceden de los agregados de este notebook. '
                 'La exportación no aprueba muestra predictiva, formato institucional ni figuras definitivas.'))'''),
              nb.v4.new_markdown_cell('''## Reproducción y evidencia

Ejecutar `python scripts/run_cp1.py --write-report` en myenv para validar contra el diccionario y regenerar tablas, figuras e informes académicos. Los resultados consolidados y sus denominadores se encuentran en `docs/CP1_RESULTADOS.md` y `docs/CP1_TABLAS_RONDAS.md`. Las pruebas sintéticas comprueban que el predeterminado conserva todos los modos, edades y números de rondas, además de fronteras de edad y reconciliación de exclusiones.

El informe de revisión se genera con `python scripts/build_cp1_review.py`, reutilizando agregados existentes y ampliando solo anomalías. Consultar `docs/CP1_INFORME_REVISION.md`.

El ejecutado local se conserva en `reports/notebooks/02_construccion_muestra_ejecutado.ipynb`. El fuente versionado conserva outputs vacíos según CI. No se publican microdatos ni IDs. Ver HANDOFF para comandos y resultados reales. CP2 y pensiones permanecen sin iniciar.''')]
    notebook.cells = cells
    nb.validate(notebook)
    nb.write(notebook, path)
    print('Notebook 02 actualizado: seis fichas completas; subpoblaciones en sección posterior.')



if __name__ == "__main__":
    import sys
    from build_main_notebooks import build
    build('INTEGRACION', execute="--execute" in sys.argv)
