"""Exportación de agregados CP1 al manuscrito; nunca recibe ni exporta microdatos."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .audit import AGE_LABELS, INTERVIEW_LABELS
from .config import ROUND_TO_YEAR
from .cp1_review import review_transitions


@dataclass(frozen=True)
class FrequencyCell:
    """Frecuencia y porcentaje que comparten un denominador declarado."""

    count: int
    percentage: float


def escape_latex(value: str) -> str:
    """Escapa texto externo; no acepta comandos LaTeX como datos."""
    replacements = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$',
                    '#': r'\#', '_': r'\_', '{': r'\{', '}': r'\}',
                    '~': r'\textasciitilde{}', '^': r'\textasciicircum{}',
                    '–': '--', '—': '---', '≥': r'$\geq$', '→': r'$\rightarrow$'}
    return ''.join(replacements.get(character, character) for character in value)


def latex_number(value: int | float, decimals: int = 0) -> str:
    """Número con espacio fino para millares y coma decimal en español."""
    if pd.isna(value):
        return '---'
    number = f'{value:,.{decimals}f}'
    integer, _, fraction = number.partition('.')
    return integer.replace(',', r'\,') + (',' + fraction if decimals else '')


def _cell(value: object) -> str:
    if isinstance(value, FrequencyCell):
        return (r'\shortstack[r]{' + latex_number(value.count) + r'\\(' +
                latex_number(value.percentage, 2) + r'\%)}')
    if isinstance(value, (int, np.integer)):
        return latex_number(value)
    if isinstance(value, (float, np.floating)):
        return latex_number(value, 2)
    return escape_latex(str(value))


def render_latex_table(table: pd.DataFrame, caption: str, label: str, note: str,
                       column_format: str | None = None, long: bool = False) -> str:
    """Tabla agregada con nota y referencia; rechaza columnas identificadoras.

    El exportador CP1 selecciona esquemas agregados explícitos. Esta barrera
    adicional evita exportar claves accidentales desde una tabla de datos.
    """
    forbidden = {'id', 'person_id', 'cunicah', 'np', 'unhhid', 'codent01', 'codent03'}
    if forbidden.intersection(str(column).lower() for column in table.columns):
        raise ValueError('El manuscrito solo admite agregados sin identificadores.')
    if not re.fullmatch(r'[a-z][a-z0-9:-]*', label):
        raise ValueError('Etiqueta LaTeX inválida.')
    alignment = column_format or ('l' + 'r' * (len(table.columns) - 1))
    def heading(column: object) -> str:
        """Divide encabezados largos; conserva el texto y todas las cifras."""
        title = str(column)
        words = title.split()
        if len(title) > 13 and len(words) > 1:
            split = min(range(1, len(words)),
                        key=lambda i: abs(len(' '.join(words[:i])) - len(' '.join(words[i:]))))
            return (r'\shortstack[c]{\textbf{' + escape_latex(' '.join(words[:split])) +
                    r'}\\\textbf{' + escape_latex(' '.join(words[split:])) + '}}')
        return r'\textbf{' + escape_latex(title) + '}'

    header = ' & '.join(heading(column) for column in table.columns) + r' \\'
    rows = [' & '.join(_cell(value) for value in row) + r' \\'
            for row in table.itertuples(index=False, name=None)]
    source = escape_latex(note)
    if long:
        return '\n'.join([
            '% Generado: no editar cifras manualmente.', r'\begingroup\small',
            r'\setlength{\tabcolsep}{4pt}', r'\begin{longtable}{' + alignment + '}',
            r'\caption{' + escape_latex(caption) + r'}\label{' + label + r'}\\',
            r'\toprule', header, r'\midrule\endfirsthead',
            r'\multicolumn{' + str(len(table.columns)) + r'}{l}{\textit{Continuación}}\\',
            r'\toprule', header, r'\midrule\endhead', r'\bottomrule\endfoot', *rows,
            r'\end{longtable}', r'\noindent{\footnotesize ' + source + '}', r'\endgroup', ''])
    return '\n'.join([
        '% Generado: no editar cifras manualmente.', r'\begin{table}[!htbp]', r'\centering',
        r'\caption{' + escape_latex(caption) + r'}\label{' + label + '}',
        r'\small\setlength{\tabcolsep}{4pt}', r'\renewcommand{\arraystretch}{1.15}',
        r'\begin{tabular}{' + alignment + '}', r'\toprule', header, r'\midrule', *rows,
        r'\bottomrule', r'\end{tabular}', r'\par\medskip',
        r'\parbox{\linewidth}{\footnotesize ' + source + '}', r'\end{table}', ''])


SAMPLE_LABELS = {
    'Universo amplio': 'Universo completo',
    'Panel no balanceado, todas las edades/entrevistas': 'No balanceado',
    '60+ por visita, cualquier entrevista': '60+ por visita',
    'Directas, cualquier edad': 'Directas',
    'Directas 60+ por visita': 'Directas 60+',
    'Seis rondas, cualquier entrevista/edad': 'Seis presencias',
    'Seis directas, cualquier edad': 'Seis directas',
    'Seis directas 60+ por visita': 'Seis directas 60+',
}


def build_cp1_latex(tables: dict[str, pd.DataFrame]) -> dict[str, str]:
    """Selecciona tablas de CP1 y genera tablas/macros sin transcribir cifras."""
    structure = tables['estructura'].iloc[0]
    rounds = tables['rondas'].sort_values('ronda')
    if int(rounds.registros.sum()) != int(structure.registros):
        raise ValueError('Los totales por ronda no reconcilian con el universo.')
    if not rounds.personas.eq(rounds.registros).all() or rounds.duplicados.any():
        raise ValueError('La equivalencia registros/personas por ronda requiere unicidad.')
    output: dict[str, str] = {}
    source = 'Fuente: elaboración propia con agregados de CP1, ENASEMsimple v2 (2001--2021). Frecuencias sin ponderación.'

    def add(name: str, frame: pd.DataFrame, caption: str, note: str,
            alignment: str | None = None, long: bool = False) -> None:
        if 'Año' in frame:
            frame = frame.copy()
            frame['Año'] = frame['Año'].astype(str)
        output[name + '.tex'] = render_latex_table(frame, caption, 'tab:' + name.replace('_', '-'),
                                                  source + ' ' + note, alignment, long)

    add('cp1_rondas', rounds[['ano_nominal', 'registros', 'personas', 'menores_60', 'edad_60_mas', 'edad_faltante']].rename(
        columns={'ano_nominal': 'Año', 'registros': 'Registros', 'personas': 'Personas',
                 'menores_60': 'Menores de 60', 'edad_60_mas': '60+', 'edad_faltante': 'Edad faltante'}),
        'Población registrada en las seis rondas',
        'N de personas dentro de cada ronda; no se suman para obtener personas únicas del periodo. Todas las edades y modalidades.')

    def cross_frequency(name: str, data: pd.DataFrame, caption: str, categories: list[str] | None = None) -> None:
        categories = categories or data.categoria.drop_duplicates().tolist()
        frame = pd.DataFrame({'Categoría': categories})
        for wave, year in ROUND_TO_YEAR.items():
            selected = data.loc[data.ronda.eq(wave)].set_index('categoria')
            denominator = int(rounds.loc[rounds.ronda.eq(wave), 'registros'].iloc[0])
            if int(selected.n.sum()) != denominator:
                raise ValueError(f'Distribución incompleta: {name}, ronda {wave}.')
            frame[str(year)] = [FrequencyCell(int(selected.loc[c, 'n']) if c in selected.index else 0,
                                             100 * int(selected.loc[c, 'n']) / denominator if c in selected.index else 0)
                                for c in categories]
        add(name, frame, caption,
            'Cada celda: n y (%). Denominador: todos los registros de la ronda de la tabla de población, incluidos faltantes. Las categorías suman N; un código ausente tiene frecuencia cero.',
            r'p{0.28\linewidth}rrrrrr')

    cross_frequency('cp1_entrevistas', tables['demografia'].loc[tables['demografia'].variable.eq('tipent')],
                    'Modalidades de entrevista por ronda', list(INTERVIEW_LABELS.values()))
    cross_frequency('cp1_edades', tables['edad_grupos'], 'Distribución por grupos de edad', AGE_LABELS)
    for variable, title in [('sexo', 'Sexo registrado'), ('edu_gru', 'Escolaridad agrupada'),
                            ('est_conyugal', 'Estado conyugal'), ('urbano', 'Tamaño de localidad')]:
        cross_frequency('cp1_' + variable, tables['demografia'].loc[tables['demografia'].variable.eq(variable)],
                        title + ' por ronda')
    entries = tables['entradas'].copy()
    frame = pd.DataFrame({'Año': entries.ronda.map(ROUND_TO_YEAR), 'N': entries.total})
    for key, label in [('primera_aparicion', 'Primera presencia'), ('ya_observadas', 'Presencia previa'),
                       ('reaparecen_tras_ausencia', 'Reaparición')]:
        frame[label] = [FrequencyCell(int(n), 100*n/total) for n, total in zip(entries[key], entries.total)]
    add('cp1_entradas', frame, 'Incorporación y seguimiento por ronda',
        'Porcentajes sobre N de la ronda. Primera presencia + presencia previa = N. Reaparición es un subconjunto de presencia previa; primera presencia en el archivo no equivale automáticamente a modalidad de muestra nueva.')
    counts = tables['numero_rondas']
    if int((counts.rondas_observadas * counts.personas).sum()) != int(structure.registros):
        raise ValueError('Personas por número de rondas no reconcilian con registros.')
    add('cp1_participacion', counts[['rondas_observadas', 'personas', 'porcentaje']].rename(
        columns={'rondas_observadas': 'Rondas observadas', 'personas': 'Personas', 'porcentaje': 'Porcentaje'}),
        'Número de rondas observadas por persona',
        f'Denominador: {int(structure.personas):,} personas únicas de 2001--2021. Presencia incluye cualquier modalidad; no equivale a entrevista directa.')
    transitions = review_transitions(tables)
    pairs = transitions.ano_origen.astype(str) + '–' + transitions.ano_destino.astype(str)
    frame = transitions[['intervalo_nominal_anos', 'denominador_origen', 'continuan', 'retencion_porcentaje', 'no_observadas']].rename(
        columns={'intervalo_nominal_anos': 'Años', 'denominador_origen': 'N origen', 'continuan': 'Continúan',
                 'retencion_porcentaje': 'Retención (%)', 'no_observadas': 'Ausentes'})
    frame.insert(0, 'Transición', pairs)
    add('cp1_transiciones', frame, 'Continuidad entre rondas nominales consecutivas',
        'Continúan + ausentes = N origen. La retención usa cualquier modalidad en destino, incluidas entrevistas sobre fallecidos. Los intervalos no son iguales y los porcentajes no son tasas anuales.')
    frame = transitions[['ausentes_con_fallecimiento_previo', 'ausentes_sin_fallecimiento_previo',
                         'ausentes_con_reaparicion_posterior', 'ausentes_sin_reaparicion_observada_hasta_2021']].rename(
        columns={'ausentes_con_fallecimiento_previo': 'Con fallecimiento',
                 'ausentes_sin_fallecimiento_previo': 'Sin fallecimiento',
                 'ausentes_con_reaparicion_posterior': 'Retorno posterior',
                 'ausentes_sin_reaparicion_observada_hasta_2021': 'Sin retorno registrado'})
    frame.insert(0, 'Transición', pairs)
    add('cp1_ausencias', frame, 'Descomposición de las ausencias y retornos posteriores',
        'Las dos primeras columnas de conteos dividen las ausencias según tipent=5 en la ronda inmediatamente anterior. Las dos últimas dividen esas mismas ausencias según retorno posterior observado; no sumar las cuatro. Sin retorno registrado no significa pérdida definitiva; 2021 es el cierre del archivo.',
        r'lrrrr')
    coverage_variables = ['edad', 'sexo', 'educacion', 'est_conyugal', 'urbano', 'a_o_ent', 'imp_neto', 'orientacion', 'serial7']
    valid = tables['faltantes'].loc[tables['faltantes'].tipo.eq('válido') & tables['faltantes'].variable.isin(coverage_variables)]
    frame = pd.DataFrame({'Variable': coverage_variables})
    for wave, year in ROUND_TO_YEAR.items():
        selected = valid.loc[valid.ronda.eq(wave)].set_index('variable')
        frame[str(year)] = [FrequencyCell(int(selected.loc[v, 'n']), float(selected.loc[v, 'porcentaje'])) for v in coverage_variables]
    add('cp1_cobertura', frame, 'Cobertura numérica de variables seleccionadas',
        'Cada celda: n válido y (% sobre el total de la ronda). Se refiere a cobertura empírica, no a universo elegible ni respuesta entre vivos. El resto conserva sus motivos de faltante en los notebooks; cero valores válidos no equivale a ausencia del atributo.',
        r'p{0.20\linewidth}rrrrrr')
    selected_samples = tables['muestras'].set_index('muestra').loc[list(SAMPLE_LABELS)].reset_index()
    frame = selected_samples[['muestra', 'registros', 'personas', 'porcentaje_personas_conservadas', 'registros_excluidos', 'personas_excluidas']].copy()
    frame.muestra = frame.muestra.map(SAMPLE_LABELS)
    frame.columns = ['Alternativa', 'Registros', 'Personas', '% personas', 'Reg. excluidos', 'Pers. excluidas']
    add('cp1_muestras', frame, 'Alternativas de muestra en todo el periodo',
        f'Denominadores: {int(structure.registros):,} registros y {int(structure.personas):,} personas únicas. Personas conservadas: unión de claves con al menos una observación elegible. Cada filtro se compara independientemente con el universo; no hay una muestra predictiva aprobada.',
        r'p{0.24\linewidth}rrrrr')
    by_round = tables['muestras_ronda'].loc[tables['muestras_ronda'].muestra.isin(SAMPLE_LABELS)].copy()
    by_round['orden'] = by_round.muestra.map({name: i for i, name in enumerate(SAMPLE_LABELS)})
    by_round = by_round.sort_values(['ronda', 'orden'])
    if not (by_round.registros + by_round.registros_excluidos).eq(by_round.denominador_registros).all():
        raise ValueError('Exclusiones por ronda no reconcilian.')
    frame = pd.DataFrame({'Año': by_round.ronda.map(ROUND_TO_YEAR), 'Alternativa': by_round.muestra.map(SAMPLE_LABELS),
                          'N original': by_round.denominador_registros, 'Conservados': by_round.registros,
                          'Excluidos': by_round.registros_excluidos, '% conservado': by_round.porcentaje_registros_conservados})
    add('cp1_muestras_ronda', frame, 'Conservados y excluidos por alternativa y ronda',
        'Cada conteo por ronda es tanto de registros como de personas, por unicidad persona-ronda. Conservados + excluidos = N original. Porcentaje sobre N original. No sumar personas entre rondas; las doce alternativas y composición están en el notebook.',
        r'rp{0.26\linewidth}rrrr', long=True)
    checks = tables['anomalias_resumen'].set_index('control').n
    check_labels = {
        'registros_posteriores_fallecimiento': 'Registros posteriores a primer fallecimiento',
        'personas_posteriores_fallecimiento': 'Personas con registros posteriores',
        'personas_sexo_inconsistente': 'Personas con códigos de sexo distintos',
        'pares_observados': 'Pares adyacentes observados',
        'pares_edad_evaluables': 'Pares con ambas edades válidas',
        'pares_edad_decreciente': 'Pares con edad decreciente',
        'personas_edad_decreciente': 'Personas con edad decreciente',
        'pares_descenso_cruzan_60': 'Pares que pasan de 60+ a menos de 60',
    }
    add('cp1_anomalias', pd.DataFrame({'Control': check_labels.values(), 'n': [int(checks[k]) for k in check_labels]}),
        'Alertas de consistencia y denominadores',
        'Conteos agregados sin historias individuales. No se corrigen ni eliminan observaciones; una alerta no identifica cuál valor es correcto.',
        r'p{0.72\linewidth}r')
    macros: dict[str, str] = {
        'cpTotalRegistros': latex_number(structure.registros), 'cpTotalPersonas': latex_number(structure.personas),
        'cpTotalVariables': latex_number(structure.variables_originales),
    }
    for name, suffix in [('Seis rondas, cualquier entrevista/edad', 'Balance'),
                         ('60+ por visita, cualquier entrevista', 'Mayores'),
                         ('Directas, cualquier edad', 'Directas'), ('Directas 60+ por visita', 'DirectasMayores'),
                         ('Seis directas, cualquier edad', 'BalanceDirectas'), ('Seis directas 60+ por visita', 'BalanceDirectasMayores')]:
        row = selected_samples.set_index('muestra').loc[name]
        for column, ending in [('registros', 'Registros'), ('personas', 'Personas')]:
            macros['cp' + suffix + ending] = latex_number(row[column])
        macros['cp' + suffix + 'Porcentaje'] = latex_number(row.porcentaje_personas_conservadas, 2) + r'\%'
    for key, name in [('pares_edad_decreciente', 'cpEdadPares'), ('personas_edad_decreciente', 'cpEdadPersonas'),
                      ('pares_edad_evaluables', 'cpEdadEvaluables'), ('pares_observados', 'cpParesObservados'),
                      ('pares_edad_no_evaluables', 'cpEdadNoEvaluables'), ('pares_descenso_cruzan_60', 'cpEdadCruce'),
                      ('pares_descenso_rondas_consecutivas', 'cpEdadConsecutivos'),
                      ('registros_posteriores_fallecimiento', 'cpMuerteRegistros'),
                      ('personas_posteriores_fallecimiento', 'cpMuertePersonas'),
                      ('personas_sexo_inconsistente', 'cpSexoPersonas'),
                      ('registros_personas_sexo_inconsistente', 'cpSexoRegistros')]:
        macros[name] = latex_number(checks[key])
    posterior = tables['anomalias_posteriores_modalidad'].set_index('modalidad').n
    macros['cpMuerteDirectas'] = latex_number(posterior.get('Directa', 0))
    macros['cpMuerteRepetidas'] = latex_number(posterior.get('Sobre fallecido', 0))
    compatibility = tables['anomalias_edad_compatibilidad'].set_index('compatibilidad_aproximada').n
    for category, name in [
        ('Anterior incompatible; actual compatible', 'cpEdadAnteriorIncompatible'),
        ('Anterior compatible; actual incompatible', 'cpEdadActualIncompatible'),
        ('Anterior incompatible; actual incompatible', 'cpEdadAmbasIncompatibles'),
    ]:
        macros[name] = latex_number(compatibility.get(category, 0))
    macros['cpEdadHuecos'] = latex_number(checks.pares_edad_decreciente - checks.pares_descenso_rondas_consecutivas)
    macros['cpEdadPorcentaje'] = latex_number(100*checks.pares_edad_decreciente/checks.pares_edad_evaluables, 2) + r'\%'
    for wave, word in zip(ROUND_TO_YEAR, ['Uno', 'Dos', 'Tres', 'Cuatro', 'Cinco', 'Seis']):
        row = entries.set_index('ronda').loc[wave]
        macros['cpEntradas' + word] = latex_number(row.primera_aparicion)
        macros['cpReapariciones' + word] = latex_number(row.reaparecen_tras_ausencia)
    for wave, word in [(1, 'Uno'), (6, 'Seis')]:
        row = rounds.set_index('ronda').loc[wave]
        macros['cpMenores' + word] = latex_number(row.menores_60)
        macros['cpMenoresPorcentaje' + word] = latex_number(100*row.menores_60/row.registros, 2) + r'\%'
    output['cp1_cifras.tex'] = '% Cifras derivadas de agregados: no editar manualmente.\n' + '\n'.join(
        '\\newcommand{\\' + name + '}{' + value + '}' for name, value in macros.items()) + '\n'
    return output


def export_cp1_figures(tables: dict[str, pd.DataFrame], directory: Path) -> list[Path]:
    """Dos figuras agregadas para revisión editorial, sin clasificar aprobación."""
    directory.mkdir(parents=True, exist_ok=True)
    totals = tables['rondas'].set_index('ronda').registros
    demo = tables['demografia'].loc[tables['demografia'].variable.eq('tipent')]
    groups = [('Directas', [1, 2]), ('Por sustituto', [3, 4]), ('Sobre fallecidos', [5])]
    fig, ax = plt.subplots(figsize=(10, 4.5), layout='constrained')
    bottom = np.zeros(6)
    for (label, codes), color in zip(groups, plt.cm.BrBG([.15, .4, .85])):
        counts = [demo.loc[demo.ronda.eq(wave) & demo.categoria.isin([INTERVIEW_LABELS[c] for c in codes]), 'n'].sum()
                  for wave in ROUND_TO_YEAR]
        ax.bar([str(y) for y in ROUND_TO_YEAR.values()], counts, bottom=bottom,
               label=label, color=color, edgecolor='white', linewidth=.7)
        bottom += counts
    for x, n in enumerate(totals):
        ax.text(x, n+300, f'{n:,}'.replace(',', ' '), ha='center', fontsize=10)
    ax.set(ylim=(0, 21500), xlabel='Año nominal de la ronda', ylabel='Registros persona-ronda')
    ax.legend(ncol=3, loc='upper center', bbox_to_anchor=(.5, 1.18), frameon=False)
    ax.spines[['top', 'right']].set_visible(False)
    path1 = directory / 'cp1_modalidades.png'
    fig.savefig(path1, dpi=220)
    plt.close(fig)
    counts = tables['numero_rondas']
    fig, ax = plt.subplots(figsize=(8, 4.5), layout='constrained')
    ax.bar(counts.rondas_observadas, counts.personas, color=plt.cm.BrBG(.2))
    for x, n in zip(counts.rondas_observadas, counts.personas):
        ax.text(x, n+100, f'{n:,}'.replace(',', ' '), ha='center', fontsize=10)
    ax.set(xlabel='Número de rondas con registro (2001--2021)', ylabel='Personas únicas',
           ylim=(0, 7600), xticks=list(range(1, 7)))
    ax.spines[['top', 'right']].set_visible(False)
    path2 = directory / 'cp1_participacion.png'
    fig.savefig(path2, dpi=220)
    plt.close(fig)
    return [path1, path2]
