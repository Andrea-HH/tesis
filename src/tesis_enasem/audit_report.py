"""Narrativa y figuras agregadas de CP1; nunca muestran identificadores."""
from __future__ import annotations
from .project_paths import write_analysis_note

from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

from .audit import AGE_LABELS, CATEGORY_LABELS, age_groups, frequency_table
from .config import ROUND_TO_YEAR
from .missing import numeric_enasem

WAVE_COLORS = {w: plt.cm.BrBG(x) for w, x in zip(ROUND_TO_YEAR, [.08, .25, .4, .6, .75, .92])}


def markdown_table(table: pd.DataFrame) -> str:
    """Tabla Markdown sin dependencia adicional; NaN significa no estimable."""
    def fmt(value: object) -> str:
        if pd.isna(value):
            return '—'
        if isinstance(value, float):
            return f'{value:.2f}'
        return str(value).replace('|', '/')
    header = '| ' + ' | '.join(map(str, table.columns)) + ' |'
    rule = '| ' + ' | '.join(['---'] * len(table.columns)) + ' |'
    rows = ['| ' + ' | '.join(fmt(v) for v in row) + ' |' for row in table.itertuples(index=False, name=None)]
    return '\n'.join([header, rule, *rows])


def wave_interpretation(tables: dict[str, pd.DataFrame], wave: int) -> str:
    """Interpreta toda la población de la ronda; filtros solo en la sección secundaria."""
    r = tables['rondas'].set_index('ronda').loc[wave]
    a = tables['edad'].set_index('ronda').loc[wave]
    edu = tables['educacion'].set_index('ronda').loc[wave]
    e = tables['entradas'].set_index('ronda').loc[wave]
    total = int(r['registros'])
    d = tables['demografia'].loc[tables['demografia'].ronda.eq(wave)]

    def count(variable: str, category: str) -> int:
        return int(d.loc[d.variable.eq(variable) & d.categoria.eq(category), 'n'].sum())

    direct = count('tipent', 'Directa de seguimiento') + count('tipent', 'Directa de nueva persona')
    proxy = count('tipent', 'Sustituto de seguimiento') + count('tipent', 'Sustituto de nueva persona')
    death = count('tipent', 'Sobre fallecido')
    groups = tables['edad_grupos'].loc[tables['edad_grupos'].ronda.eq(wave)].set_index('categoria').n
    young = int(groups['Menores de 50'] + groups['50–59'])
    older = int(groups['80–89'] + groups['90 o más'])
    woman = count('sexo', 'Mujer')
    married = count('est_conyugal', 'Casado o en unión')
    widowed = count('est_conyugal', 'Viudo')
    big = count('urbano', '100 mil residentes o más')
    no_school = count('edu_gru', 'Sin escolaridad')
    high_school = count('edu_gru', '10 años o más')
    n_rounds = tables['participacion_ronda'].loc[tables['participacion_ronda'].ronda.eq(wave)].set_index('rondas_observadas_2001_2021').personas
    weights = tables['pesos'].loc[tables['pesos'].ronda.eq(wave)]
    parts = [
        '### Resultados y modalidades de registro',
        f'La ronda {wave} ({ROUND_TO_YEAR[wave]}) contiene {total:,} registros de {int(r["personas"]):,} personas, '
        f'sin exclusión por edad, entrevista ni continuidad. Las directas suman {direct:,} ({100*direct/total:.2f}%), '
        f'las de sustituto {proxy:,} ({100*proxy/total:.2f}%) y las sobre fallecidos {death:,} ({100*death/total:.2f}%). '
        'El denominador de estos porcentajes es la totalidad de la ronda. Una entrevista sobre fallecido registra '
        'información aportada por un informante; no representa entrevista directa ni observación contemporánea de edad.',
        '### Edad y estructura demográfica',
        f'Hay {young:,} registros con edad menor de 60 ({100*young/total:.2f}% de todos los registros). '
        f'Los menores de 50 son {int(groups["Menores de 50"]):,}, mientras {older:,} tienen 80 o más, '
        f'incluidos {int(groups["90 o más"]):,} con 90 o más ({100*groups["90 o más"]/total:.2f}% del total). '
        f'La edad falta en {int(r["edad_faltante"]):,}/{total:,} registros; el resumen continuo utiliza '
        f'{int(a["n_validos"]):,} valores válidos, con mediana {a["mediana"]:.1f} y cuartiles '
        f'{a["q25"]:.1f}–{a["q75"]:.1f} años. Las siete categorías suman el total original; '
        'los códigos de edad ausente se conservan por separado en la tabla de cobertura.',
        f'Las mujeres representan {woman:,}/{total:,} ({100*woman/total:.2f}%). Los registros de personas '
        f'casadas o en unión son {married:,} ({100*married/total:.2f}%) y los de viudez {widowed:,} '
        f'({100*widowed/total:.2f}%). Las localidades de 100 mil habitantes o más reúnen {big:,} '
        f'({100*big/total:.2f}%). Estas proporciones incluyen los faltantes en el denominador y no describen '
        'exclusivamente participantes vivos o directos. El complemento de cada categoría comprende otras categorías '
        'y, cuando existen, valores ausentes. El corte de localidad no permite identificar todos los asentamientos rurales.',
        '### Educación',
        f'La escolaridad es válida en {int(edu["n_validos"]):,}/{total:,} registros, con '
        f'media {edu["media"]:.2f} y mediana {edu["mediana"]:.1f} años. La ausencia de escolaridad se '
        f'registra para {no_school:,} ({100*no_school/total:.2f}%) y 10 años o más para '
        f'{high_school:,} ({100*high_school/total:.2f}%). La distribución completa muestra años exactos, '
        'categorías del proveedor y causas de faltantes. Según el diccionario, educacion refleja escolaridad '
        'a partir de la primera entrevista; una diferencia entre rondas no demuestra adquisición individual de educación.',
        '### Incorporación y seguimiento',
        f'La primera aparición corresponde a {int(e["primera_aparicion"]):,} personas '
        f'({e["primera_aparicion_porcentaje"]:.2f}% de la ronda), frente a {int(e["ya_observadas"]):,} '
        f'ya registradas ({e["ya_observadas_porcentaje"]:.2f}%). Las reapariciones tras ausencia inmediata '
        f'son {int(e["reaparecen_tras_ausencia"]):,} ({e["reaparecen_tras_ausencia_porcentaje"]:.2f}%); '
        'son un subconjunto de quienes ya participaron. Primera aparición se deriva de la historia de presencia '
        'y no debe equipararse automáticamente a tipent de nueva persona.',
        f'Entre los presentes en esta ronda, {int(n_rounds.loc[1]):,} solo tienen un registro en 2001–2021 '
        f'y {int(n_rounds.loc[6]):,} aparecen en las seis rondas. Esta clasificación describe '
        'la trayectoria retrospectiva observada e incluye todos los modos de entrevista; no es un predictor prospectivo.',
    ]
    if wave > 1:
        follow = tables['seguimiento_ronda'].set_index('ronda').loc[wave]
        previous = tables['edad'].set_index('ronda').loc[wave-1]
        prev_d = tables['demografia'].loc[tables['demografia'].ronda.eq(wave-1)]
        previous_total = int(tables['rondas'].set_index('ronda').loc[wave-1, 'registros'])
        prev_no_school = int(prev_d.loc[prev_d.variable.eq('edu_gru') & prev_d.categoria.eq('Sin escolaridad'), 'n'].sum())
        previous_woman = int(prev_d.loc[prev_d.variable.eq('sexo') & prev_d.categoria.eq('Mujer'), 'n'].sum())
        previous_widowed = int(prev_d.loc[prev_d.variable.eq('est_conyugal') & prev_d.categoria.eq('Viudo'), 'n'].sum())
        previous_big = int(prev_d.loc[prev_d.variable.eq('urbano') & prev_d.categoria.eq('100 mil residentes o más'), 'n'].sum())
        parts += [f'De {int(follow["denominador_anterior"]):,} personas en la ronda anterior, '
                  f'{int(follow["no_observadas_desde_anterior"]):,} no se registran ahora '
                  f'({follow["porcentaje_no_observadas"]:.2f}% sobre el origen): '
                  f'{int(follow["ausentes_con_fallecimiento_previo"]):,} ya tenían entrevista sobre fallecido y '
                  f'{int(follow["ausentes_sin_fallecimiento_previo"]):,} no tenían ese antecedente en la ronda anterior. '
                  'El último grupo no tiene causa de ausencia identificada por esta comparación; una parte '
                  'puede reaparecer después. La primera ronda no tiene referencia anterior dentro del archivo.',
                  '### Comparación con la ronda anterior',
                  f'La mediana de edad cambia {a["mediana"]-previous["mediana"]:+.1f} años y la proporción '
                  f'sin escolaridad cambia {100*no_school/total-100*prev_no_school/previous_total:+.2f} puntos '
                  'porcentuales. Son cambios de composición entre muestras registradas, que combinan '
                  'incorporaciones, envejecimiento y observación selectiva. No se atribuyen a cambios dentro de persona.']
        parts += [f'La proporción de mujeres cambia {100*woman/total-100*previous_woman/previous_total:+.2f} '
                  f'puntos porcentuales; la de viudez {100*widowed/total-100*previous_widowed/previous_total:+.2f} '
                  f'y la de localidades de 100 mil o más {100*big/total-100*previous_big/previous_total:+.2f}. '
                  'Los tres contrastes usan el total de cada ronda. Las diferencias de viudez y localidad '
                  'incluyen cambios en los faltantes por fallecimiento; no se interpretan automáticamente '
                  'como cambios de estado conyugal o residencia entre las mismas personas.']
    else:
        parts += ['Esta es la primera ronda disponible: no se calculan entradas ni ausencias respecto a años '
                  'anteriores no incluidos en el archivo. La distribución por número de rondas usa seguimiento '
                  'posterior únicamente con fines descriptivos.']
    parts += ['### Ponderadores y cobertura']
    for prefix, label in [('factori', 'individual'), ('factorh', 'de hogar')]:
        w = weights.loc[weights.variable.str.startswith(prefix)]
        parts += [f'El factor {label} de la ronda tiene {int(w.validos.sum()):,}/{total:,} valores válidos; '
                  f'{int(w.positivos.sum()):,} positivos, {int(w.ceros.sum()):,} ceros y '
                  f'{int(w.faltantes.sum()):,} faltantes. La tabla separa modalidades de entrevista. '
                  'Disponibilidad numérica no equivale a aplicabilidad a toda la población registrada.']
    missing = tables['faltantes'].loc[tables['faltantes'].ronda.eq(wave)]
    absent_columns = missing.loc[missing.tipo.eq('válido') & missing.n.eq(0), 'variable'].nunique()
    parts += [f'La auditoría de cobertura incluye {missing.variable.nunique()} variables originales; '
              f'{absent_columns} no tienen valores válidos en esta ronda. Cada código especial se cuenta '
              'por variable sobre todos los registros, distinguiendo no formulado, sustituto, fallecimiento y '
              'otras causas. Las tablas agregadas de celdas no son conteos de personas fallecidas ni ausentes.',
              '### Conclusión parcial y límites',
              'La población registrada conserva heterogeneidad de edades y modos de entrevista. Las comparaciones '
              'por edad, educación y localidad deben considerar sus faltantes y cambios de composición. '
              'Todos los resultados son descriptivos sin ponderación; el archivo de entrevistas completadas no '
              'contiene necesariamente toda la población objetivo ni todos los intentos de contacto. '
              'Las subpoblaciones se comparan después, sin reemplazar esta referencia ni excluir datos originales.']
    return '\n\n'.join(parts)


def plot_wave(raw: pd.DataFrame, wave: int, directory: Path | None = None) -> plt.Figure:
    """Ficha con frecuencias demográficas y distribución de edad, N explícitos."""
    group = raw.loc[raw.ronda.eq(wave)]
    fig, axes = plt.subplots(3, 3, figsize=(19, 16), layout='constrained')
    variables = ['tipent', 'sexo', 'est_conyugal', 'urbano', 'edad_cp1', 'edu_gru', 'a_o_ent']
    titles = ['Tipo de entrevista', 'Sexo', 'Estado conyugal', 'Tamaño de localidad',
              'Edad: seis grupos y faltantes', 'Escolaridad (categorías del proveedor)', 'Año efectivo de entrevista']
    for ax, variable, title in zip(axes.flat, variables, titles):
        series = age_groups(group.edad) if variable == 'edad_cp1' else group[variable]
        tab = frequency_table(series, variable)
        if variable == 'edad_cp1':
            tab = tab.set_index('categoria').reindex(AGE_LABELS, fill_value=0).reset_index()
        ax.barh(tab.categoria, tab.n, color=WAVE_COLORS[wave])
        ax.bar_label(ax.containers[0], padding=3, fontsize=9)
        ax.set_xlim(0, max(tab.n.max(), 1)*1.25)
        ax.invert_yaxis()
        ax.set_title(title)
        ax.set_xlabel(f'Frecuencia absoluta (denominador: {len(group):,})')
    age = numeric_enasem(group.edad).dropna()
    axes.flat[7].hist(age, bins=range(0, 121, 5), color=WAVE_COLORS[wave], edgecolor='white')
    axes.flat[7].set(xlabel='Edad en años cumplidos', ylabel='Registros por intervalo de 5 años',
                    title=f'Edad válida: n={len(age):,}; faltantes={len(group)-len(age):,}')
    education = numeric_enasem(group.educacion).dropna()
    axes.flat[8].hist(education, bins=range(0, 24), color=WAVE_COLORS[wave], edgecolor='white', align='left')
    axes.flat[8].set(xlabel='Años de escolaridad', ylabel='Frecuencia absoluta entre válidos',
                    title=f'Escolaridad válida: n={len(education):,}; faltantes={len(group)-len(education):,}')
    fig.suptitle(f'Ronda {wave} ({ROUND_TO_YEAR[wave]}), n={len(group):,} persona-ronda', fontsize=17)
    if directory is not None:
        directory.mkdir(parents=True, exist_ok=True)
        fig.savefig(directory / f'cp1_ronda_{wave}.png', dpi=150)
    return fig


def plot_longitudinal(tables: dict[str, pd.DataFrame], directory: Path | None = None) -> plt.Figure:
    """Gráficas de participación e intersecciones de personas, sin claves."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 6), layout='constrained')
    t = tables['numero_rondas']
    axes[0].bar(t.rondas_observadas, t.personas, color=[WAVE_COLORS[w] for w in ROUND_TO_YEAR])
    axes[0].bar_label(axes[0].containers[0])
    axes[0].set(xlabel='Número de rondas observadas', ylabel='Personas únicas', title='Participación (incluye fallecimiento)')
    p = tables['patrones'].head(12).sort_values('personas')
    axes[1].barh(p.patron_2001_a_2021, p.personas, color=plt.cm.BrBG_r(.3))
    axes[1].bar_label(axes[1].containers[0])
    axes[1].set(xlabel='Personas únicas', title='12 patrones más frecuentes; 1=observada')
    axes[1].set_xlim(0, p.personas.max()*1.22)
    m = tables['intersecciones'].set_index('ronda')
    heatmap = axes[2].imshow(m, cmap='BrBG')
    labels = [f'R{w}\n{y}' for w, y in ROUND_TO_YEAR.items()]
    axes[2].set(xticks=range(6), yticks=range(6), xticklabels=labels, yticklabels=labels,
                title='Personas presentes en ambas rondas')
    for i in range(6):
        for j in range(6):
            rgba = heatmap.cmap(heatmap.norm(m.iloc[i,j]))
            luminance = .299*rgba[0] + .587*rgba[1] + .114*rgba[2]
            axes[2].text(j, i, f'{m.iloc[i,j]:,}', ha='center', va='center', fontsize=9,
                         color='white' if luminance < .5 else 'black')
    if directory is not None:
        directory.mkdir(parents=True, exist_ok=True)
        fig.savefig(directory / 'cp1_participacion.png', dpi=150)
    return fig


def followup_interpretation(tables: dict[str, pd.DataFrame]) -> str:
    """Compara perfiles calculados y magnitud de la selección por continuidad."""
    profile = tables['perfiles_seguimiento']
    lines = []
    for wave in range(1, 6):
        sub = profile.loc[profile.ronda.eq(wave) & profile.variable.eq('edad')].set_index('grupo')
        retained = sub.loc['Observada siguiente']
        absent = sub.loc['No observada siguiente']
        lines.append(f"En R{wave} ({ROUND_TO_YEAR[wave]}), en toda la población de origen, la edad media es "
                     f"{retained['media']:.2f} años entre quienes se observan en la ronda siguiente "
                     f"(N válido={int(retained['n']):,}/{int(retained['denominador']):,}) y "
                     f"{absent['media']:.2f} entre quienes no se observan "
                     f"(N válido={int(absent['n']):,}/{int(absent['denominador']):,}). "
                     f"La diferencia observada es {retained['media']-absent['media']:.2f} años.")
    lines.append("La comparación usa toda la población en origen y resume edad solo entre valores válidos. "
                 "Los fallecidos en origen permanecen en el denominador y su edad puede faltar. Una "
                 "restricción de continuidad puede modificar el perfil analítico. La observación posterior "
                 "incluye entrevistas sobre fallecidos; la ausencia posterior también incluye a quienes ya tenían "
                 "ese registro. Los intervalos difieren: estos contrastes no "
                 "estiman supervivencia ni efectos de edad sobre abandono. La selección final exige "
                 "revisión de perfiles por sexo, educación, localidad y entrevista en las tablas.")
    return '\n\n'.join(lines)

CP1_INTRO = """# CP1 — Auditoría de toda la población registrada en ENASEMsimple

## Introducción y objetivo
La referencia descriptiva de CP1 es **toda la población registrada en simpleMHAS.dta**:
todas las edades, entrevistas y trayectorias. No se exige edad mínima, entrevista directa
ni número de rondas. Se caracteriza la integridad y composición del archivo completo antes
de estudiar subpoblaciones para modelos futuros. La población registrada no equivale a toda
la población mexicana ni a todos los casos contactados o elegibles de la encuesta.

## Metodología y fuentes
El original se lee sin modificar con convert_missing=True. Las claves cunicah + np
se validan en memoria; no se exportan. Las seis rondas nominales son 2001, 2003, 2012,
2015, 2018 y 2021; a_o_ent se informa por separado. Se detiene el enlace ante claves
faltantes, duplicados persona-ronda o codificaciones desconocidas, sin deduplicación ni
exclusión silenciosa. La auditoría conserva todas las modalidades de entrevista.

La fuente de codificaciones es ENASEMsimple v2, enero de 2025: cuadro 1 y apéndice 1;
educacion/edu_gru (p. 18) describen escolaridad a partir de la primera entrevista. La
clasificación edad_cp1 se deriva de edad: <50, 50–59, 60–69, 70–79, 80–89 y ≥90, más
edad faltante. No reemplaza edad_gru del proveedor, cuyo último grupo es 80+.
El tamaño de localidad distingue <100 mil de ≥100 mil habitantes; no se reinterpretan
estos códigos como una clasificación exhaustiva de ruralidad.

Cada frecuencia presenta n y porcentaje sobre **todos los registros de la ronda**, incluidos
faltantes. Los estadísticos continuos usan valores válidos y explicitan su N. Los conteos
por ronda son personas y registros equivalentes solo después de verificar unicidad; las
personas únicas del periodo son la unión de claves y no la suma de conteos por ronda.
Los códigos .f, .p, .w y otros se conservan separados en las columnas originales antes
de convertirlas a numérico. Un valor no formulado no se convierte en cero.

Las matrices de presencia y las transiciones usan todo el panel, incluidos sustitutos y
entrevistas sobre fallecidos. Se separan incorporación, continuidad, ausencia y reaparición;
la ausencia no identifica causa. El número de rondas usa la historia completa 2001–2021
solo para descripción, sin incorporarlo a predictores prospectivos. El panel no balanceado
es el universo de referencia y permite 1–6 rondas; el balanceado exige las seis rondas,
independientemente de edad o modalidad, y se analiza únicamente en la sección secundaria.

Todos los conteos son observados sin ponderación. Se auditan factores individuales y de
hogar por ronda y entrevista, incluyendo positivos, ceros y faltantes. Su disponibilidad
no autoriza su uso poblacional ni longitudinal. No se estima vulnerabilidad, no se ejecuta
CP2/CP3 y no se fusionan pensiones.
"""

CP1_CONCLUSIONS = """## Conclusiones y decisiones pendientes

La población completa permanece como **referencia descriptiva de CP1**. Todas sus edades,
modalidades y patrones de seguimiento contribuyen a las fichas por ronda, cobertura,
matrices y transiciones. Ninguna subpoblación reemplaza esa referencia. Las distribuciones
de edad y educación no pueden resumirse solo con mayores de 60 ni con entrevistas directas.

La participación combina incorporación de personas, cambios en el modo de entrevista,
fallecimiento registrado y no observación de causa desconocida. Las reapariciones prueban
que no toda ausencia inmediata es salida definitiva. La falta de registro tras una
entrevista sobre fallecido se distingue de la ausencia sin ese antecedente. Los intervalos
nominales 2, 9, 3, 3 y 3 años no permiten interpretar retención bruta como tasa anual.

La submuestra 60+ y, eventualmente, directa 60+ es únicamente una **candidata para modelos
predictivos posteriores**, pendiente de estimando y aprobación. Exigir seis rondas selecciona
continuidad futura y modifica la composición; no se adopta por defecto. La edad ausente,
incluida .f, no se imputa para forzar elegibilidad. Las alternativas de edad de entrada se
mantienen separadas del criterio por visita; no son intercambiables ante inconsistencias.

Se conservan las anomalías de edad, sexo y fallecimiento registradas en la tabla de
consistencia. Su revisión debe preceder a la construcción de etiquetas. La escolaridad
registrada a partir de primera entrevista y los cambios muestrales limitan una interpretación
de sus diferencias como aprendizaje dentro de persona. No se afirman representatividad,
causalidad ni capacidad de alerta temprana a partir de esta auditoría.

**Estado:** análisis descriptivo ampliado ejecutado; aprobación de resultados, reglas de
anomalías y estimando predictivo pendiente. Antes de CP2 se requiere revisión humana.
Los cambios permanecen locales en feat/cp1-auditoria, sin publicación ni merge a main.
"""


def subpopulation_interpretation(tables: dict[str, pd.DataFrame]) -> str:
    """Explica pérdidas absolutas y denominadores del periodo sin reemplazar referencia."""
    summary = tables['muestras'].set_index('muestra')
    base = summary.loc['Universo amplio']
    parts = ['### Interpretación de la comparación secundaria']
    for name in ['60+ por visita, cualquier entrevista', 'Directas, cualquier edad',
                 'Directas 60+ por visita', 'Seis rondas, cualquier entrevista/edad']:
        row = summary.loc[name]
        parts.append(f'{name}: conserva {int(row.registros):,}/{int(base.registros):,} registros '
                     f'({row.porcentaje_registros_conservados:.2f}%) y {int(row.personas):,}/'
                     f'{int(base.personas):,} personas ({row.porcentaje_personas_conservadas:.2f}%). '
                     f'Excluye {int(row.registros_excluidos):,} registros y '
                     f'{int(row.personas_excluidas):,} personas del periodo.')
    parts.append('Las personas excluidas del periodo no se obtienen sumando exclusiones por ronda: '
                 'una persona puede perder algunas visitas y conservar otras. Cada filtro de la tabla '
                 'muestras_ronda se compara de manera independiente con la ronda completa; el flujo '
                 'directas → edad conocida → 60+ es una alternativa secuencial adicional. El panel no '
                 'balanceado conserva todo el universo y no significa excluir a quienes tienen seis rondas.')
    return '\n\n'.join(parts)


def write_cp1_report(tables: dict[str, pd.DataFrame], root: Path) -> None:
    """Regenera informe académico y tablas comparativas agregadas completas en docs/."""
    parts = [CP1_INTRO, '## Resultados de integridad general', markdown_table(tables['estructura']),
             markdown_table(tables['consistencia']),
             'Los totales y categorías de entrevista se contrastan con el diccionario mediante run_cp1.py. '
             'Las anomalías permanecen en el universo; no se aplica una depuración automática.',
             '## Comparación inicial entre rondas (población completa)',
             markdown_table(tables['rondas']), markdown_table(tables['edad']), markdown_table(tables['educacion'])]
    for wave, year in ROUND_TO_YEAR.items():
        parts += [f'## Ronda {wave} — {year}: toda la población registrada',
                  '**Introducción y método.** Se describe esta ronda con todas sus edades y modalidades. '
                  'La frecuencia absoluta y su porcentaje incluyen faltantes en el denominador de la ronda. '
                  'La historia de presencia se calcula a partir del panel completo. No se aplican filtros '
                  'de subpoblación en esta ficha. La cobertura muestra todas las columnas originales.',
                  wave_interpretation(tables, wave)]
        for name, title in [('rondas', 'Registros y personas'), ('edad_grupos', 'Grupos de edad solicitados'),
                            ('edad', 'Edad continua entre valores válidos'), ('demografia', 'Frecuencias demográficas y entrevista'),
                            ('educacion', 'Estadísticos de escolaridad'), ('entradas', 'Primera aparición, participación previa y reaparición'),
                            ('seguimiento_ronda', 'Ausencias respecto a la ronda anterior'),
                            ('participacion_ronda', 'Número de rondas de quienes están presentes'),
                            ('cronologia', 'Año efectivo según modalidad'), ('pesos', 'Disponibilidad de ponderadores'),
                            ('faltantes', 'Cobertura y códigos de todas las variables')]:
            selected = tables[name].loc[tables[name].ronda.eq(wave)]
            if selected.empty:
                parts += [f'### {title}', 'No aplica: no existe una ronda anterior dentro del archivo.']
            else:
                parts += [f'### {title}', markdown_table(selected)]
        parts += [f'Figura reproducible: `reports/figures/cp1_ronda_{wave}.png`. '
                  'Incluye edad ampliada, educación y todas las modalidades de entrevista.']
    parts += ['## Seguimiento longitudinal de toda la población',
              '**Objetivo y metodología.** Describir presencia y cambios de composición sin restricciones de '
              'edad, modalidad o continuidad. Los estados incluyen entrevistas sobre fallecidos. Los perfiles '
              'en origen incluyen todos los registros; las medias usan solo valores válidos, con N y '
              'denominador original explícitos. El grupo observado después puede incluir entrevista de fallecimiento.']
    for name, title in [('numero_rondas', 'Personas según número de rondas'), ('entradas', 'Entradas y reapariciones'),
                        ('intersecciones', 'Matriz de personas compartidas'), ('patrones', 'Patrones de participación'),
                        ('transiciones', 'Transiciones entre rondas consecutivas'), ('estados', 'Cambios de modalidad y ausencia'),
                        ('intervalos_efectivos', 'Intervalos de entrevista efectiva'),
                        ('perfiles_seguimiento', 'Composición en origen según presencia posterior')]:
        parts += [f'### {title}', markdown_table(tables[name])]
    parts += [followup_interpretation(tables),
              '## Sección secundaria: comparación de subpoblaciones',
              '**Introducción y método.** Solo tras auditar el universo se comparan edad, modalidad y '
              'balance. El panel no balanceado es la población completa y admite cualquier número de '
              'rondas; el balanceado exige las seis, sin filtros de edad ni de entrevista. Las versiones '
              'directas o 60+ son criterios adicionales explícitos, no condiciones del análisis general. '
              'Conservados + excluidos = original, por registros y personas, en cada ronda y en el periodo.']
    for name, title in [('muestras', 'Comparación global'), ('muestras_ronda', 'Conservados y excluidos en cada ronda'),
                        ('flujo', 'Ejemplo de exclusiones secuenciales de una candidata 60+ directa'),
                        ('composicion_muestras', 'Composición completa de cada alternativa por ronda')]:
        parts += [f'### {title}', markdown_table(tables[name])]
    parts += [subpopulation_interpretation(tables), CP1_CONCLUSIONS,
              '## Reproducción y evidencia',
              '`/opt/miniconda3/envs/myenv/bin/python scripts/run_cp1.py --write-report` reconstruye '
              'las tablas JSON y siete figuras agregadas locales y este informe. '
              '`scripts/build_cp1_notebook.py` actualiza el notebook fuente conservando la arquitectura. '
              'La ejecución con kernel myenv genera `reports/notebooks/02_construccion_muestra_ejecutado.ipynb`; '
              'el fuente versionado tiene outputs vacíos según CI. No se publican claves ni microdatos.']
    write_analysis_note(root, 'docs/CP1_RESULTADOS.md', '\n\n'.join(parts)+'\n')
    # Vista compacta entre rondas, íntegra por categoría; celdas n (porcentaje%).
    comparison = [CP1_INTRO.split('## Metodología')[0],
                  'Cada celda expresa n (porcentaje sobre todos los registros de la ronda). '
                  'Los códigos especiales permanecen separados. Las tablas completas por ronda, '
                  'ponderadores, cobertura de 119 variables y todas las alternativas están en CP1_RESULTADOS.md.',
                  '## Totales por ronda', markdown_table(tables['rondas'])]
    items = [('Grupos de edad', tables['edad_grupos'])]
    for variable, label in [('sexo', 'Sexo'), ('est_conyugal', 'Estado conyugal'), ('edu_gru', 'Educación agrupada'),
                            ('educacion', 'Educación: años exactos'), ('urbano', 'Localidad'),
                            ('tipent', 'Cinco modalidades de entrevista'), ('a_o_ent', 'Año efectivo'),
                            ('fallecido', 'Fallecimiento registrado')]:
        items.append((label, tables['demografia'].loc[tables['demografia'].variable.eq(variable)]))
    for title, table in items:
        table = table.copy()
        table['n_porcentaje'] = table.apply(lambda row: f'{int(row.n):,} ({row.porcentaje:.2f}%)', axis=1)
        wide = table.pivot(index='categoria', columns='ronda', values='n_porcentaje')
        if title == 'Grupos de edad':
            wide = wide.reindex(AGE_LABELS)
        elif len(table) and 'variable' in table:
            variable = table.variable.iloc[0]
            if variable in CATEGORY_LABELS:
                categories = list(CATEGORY_LABELS[variable].values())
                wide = wide.reindex(categories + [c for c in wide.index if c not in categories])
            else:
                def category_key(category: str) -> tuple[int, float | str]:
                    try:
                        return (0, float(category))
                    except ValueError:
                        return (1, category)
                wide = wide.reindex(sorted(wide.index, key=category_key))
        wide = wide.reindex(columns=ROUND_TO_YEAR).fillna('0 (0.00%)')
        wide.columns = [str(year) for year in ROUND_TO_YEAR.values()]
        comparison += [f'## {title}', markdown_table(wide.reset_index())]
    comparison += ['## Incorporación y seguimiento', markdown_table(tables['entradas']),
                   markdown_table(tables['seguimiento_ronda']), '## Distribución del número de rondas',
                   markdown_table(tables['numero_rondas']), '## Conservados y excluidos por subpoblación y ronda',
                   markdown_table(tables['muestras_ronda']), subpopulation_interpretation(tables), CP1_CONCLUSIONS]
    write_analysis_note(root, 'docs/CP1_TABLAS_RONDAS.md', '\n\n'.join(comparison)+'\n')
