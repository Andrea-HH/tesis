"""Auditoría CP1: tablas agregadas sin exportar claves ni registros individuales."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import ROUND_TO_YEAR
from .missing import numeric_enasem, stata_missing_code
from .panel import make_person_id

INTERVIEW_LABELS = {1: 'Directa de seguimiento', 2: 'Directa de nueva persona',
                    3: 'Sustituto de seguimiento', 4: 'Sustituto de nueva persona',
                    5: 'Sobre fallecido'}
AGE_LABELS = ['Menores de 50', '50–59', '60–69', '70–79', '80–89', '90 o más', 'Edad faltante']
CATEGORY_LABELS = {
    'tipent': INTERVIEW_LABELS, 'sexo': {1: 'Hombre', 2: 'Mujer'},
    'est_conyugal': {1: 'Casado o en unión', 2: 'Separado o divorciado', 3: 'Viudo', 4: 'Soltero'},
    'urbano': {0: 'Menos de 100 mil residentes', 1: '100 mil residentes o más'},
    'edad_gru': {0: '49 o menos', 1: '50–59', 2: '60–69', 3: '70–79', 4: '80 o más'},
    'edu_gru': {0: 'Sin escolaridad', 1: '1–5 años', 2: '6 años', 3: '7–9 años', 4: '10 años o más'},
    'fallecido': {0: 'No', 1: 'Sí'},
}


def age_groups(series: pd.Series) -> pd.Series:
    """Seis bandas derivadas de edad, sin alterar edad_gru original ni imputar faltantes.

    Límites izquierdos incluidos: <50, [50,60), ..., [80,90), >=90.
    Los códigos especiales se agregan como edad faltante aquí y se conservan
    individualmente en la auditoría de la columna original.
    """
    groups = pd.cut(numeric_enasem(series), [-np.inf, 50, 60, 70, 80, 90, np.inf],
                    labels=AGE_LABELS[:-1], right=False)
    return groups.astype(object).fillna('Edad faltante')


def select_population(data: pd.DataFrame, population: str | None = None) -> pd.DataFrame:
    """Selecciona una alternativa explícita; None conserva todos los registros.

    Requiere prepare_audit. No modifica la entrada ni selecciona por edad,
    entrevista o balance por defecto. Los nombres proceden de population_masks.
    """
    if population is None:
        return data.copy()
    masks = population_masks(data)
    if population not in masks:
        raise ValueError(f'Población desconocida: {population}')
    selected = data.loc[masks[population]].copy()
    if selected.empty:
        raise ValueError('La población seleccionada no contiene registros.')
    return selected


def value_category(value: object, labels: dict[int, str] | None = None) -> str:
    """Etiqueta valores conservando cada código especial y NaN por separado."""
    code = stata_missing_code(value)
    if code is not None:
        return code
    if pd.isna(value):
        return 'NaN'
    return (labels or {}).get(value, str(value))


def frequency_table(series: pd.Series, variable: str) -> pd.DataFrame:
    """Frecuencias con denominador de todos los registros, incluidos faltantes."""
    counts = series.map(lambda x: value_category(x, CATEGORY_LABELS.get(variable))).value_counts()
    if len(series) and variable in CATEGORY_LABELS:
        counts = counts.reindex(list(CATEGORY_LABELS[variable].values()) +
                                [c for c in counts.index if c not in CATEGORY_LABELS[variable].values()], fill_value=0)
    return pd.DataFrame({'categoria': counts.index, 'n': counts.values,
                         'denominador': len(series),
                         'porcentaje': counts.values / len(series) * 100 if len(series) else []})


def prepare_audit(raw: pd.DataFrame) -> pd.DataFrame:
    """Valida claves, rondas, entrevistas y unicidad antes de cualquier enlace."""
    data = raw.copy()
    data['id'] = make_person_id(data)
    data['ronda'] = numeric_enasem(data['ronda'])
    if not data['ronda'].isin(ROUND_TO_YEAR).all():
        raise ValueError('Rondas ausentes o fuera del calendario permitido.')
    data['ronda'] = data['ronda'].astype(int)
    if data.duplicated(['id', 'ronda']).any():
        raise ValueError('Pares persona-ronda duplicados; detener auditoría sin deduplicar.')
    if not numeric_enasem(data['tipent']).isin(INTERVIEW_LABELS).all():
        raise ValueError('Tipo de entrevista faltante o desconocido.')
    return data


def participation_matrix(data: pd.DataFrame) -> pd.DataFrame:
    """Matriz PRIVADA de presencia, incluida entrevista sobre fallecido; no exportar."""
    if data.duplicated(['id', 'ronda']).any():
        raise ValueError('Pares persona-ronda duplicados.')
    return pd.crosstab(data['id'], data['ronda']).reindex(columns=ROUND_TO_YEAR, fill_value=0).gt(0)


def population_masks(data: pd.DataFrame) -> dict[str, pd.Series]:
    """Alternativas de edad, entrada y balance; máscaras privadas sin selección automática.

    Entrada original: edad >=60 en primera entrevista registrada. Entrada abierta:
    desde la primera edad >=60 observada, sin exigir ser mayor en la primera ronda.
    No se infiere edad de fallecidos ni se rellena información retrospectivamente.
    """
    age = numeric_enasem(data['edad'])
    direct = numeric_enasem(data['tipent']).isin([1, 2])
    first = data.sort_values('ronda').drop_duplicates('id')
    entry_ids = first.loc[numeric_enasem(first['edad']).ge(60), 'id']
    onset = data.loc[age.ge(60)].groupby('id')['ronda'].min()
    opened = data['ronda'].ge(data['id'].map(onset))
    visit = age.ge(60)
    matrix = participation_matrix(data)
    all_ids = matrix.index[matrix.all(axis=1)]
    direct_counts = data.loc[direct].groupby('id')['ronda'].nunique()
    strict_counts = data.loc[visit & direct].groupby('id')['ronda'].nunique()
    return {
        'Universo amplio': pd.Series(True, index=data.index),
        'Panel no balanceado, todas las edades/entrevistas': pd.Series(True, index=data.index),
        '60+ por visita, cualquier entrevista': visit,
        'Directas, cualquier edad': direct,
        'Directas 60+ por visita': visit & direct,
        '60+ en primera observación, seguimiento amplio': data['id'].isin(entry_ids),
        '60+ en primera observación, directas': data['id'].isin(entry_ids) & direct,
        'Desde primera observación 60+, seguimiento amplio': opened,
        'Desde primera observación 60+, directas': opened & direct,
        'Seis rondas, cualquier entrevista/edad': data['id'].isin(all_ids),
        'Seis directas, cualquier edad': data['id'].isin(direct_counts.index[direct_counts.eq(6)]),
        'Seis directas 60+ por visita': data['id'].isin(strict_counts.index[strict_counts.eq(6)]),
    }


def missing_by_wave(raw: pd.DataFrame) -> pd.DataFrame:
    """Cobertura de TODAS las columnas: válidos y cada causa; conserva denominadores."""
    rows = []
    for wave, group in raw.groupby('ronda'):
        for column in raw.columns:
            categories = group[column].map(lambda x: stata_missing_code(x) or ('NaN' if pd.isna(x) else 'válido'))
            counts = categories.value_counts().to_dict()
            counts.setdefault('válido', 0)
            for category, n in counts.items():
                rows.append({'ronda': wave, 'variable': column, 'tipo': category, 'n': n,
                             'denominador': len(group), 'porcentaje': 100 * n / len(group)})
    return pd.DataFrame(rows)


def sample_flow(data: pd.DataFrame) -> pd.DataFrame:
    """Exclusiones secuenciales por ola: no directa, edad faltante y menor de 60."""
    rows = []
    for wave, group in data.groupby('ronda'):
        current = group
        stages = [('Claves válidas y únicas', pd.Series(True, index=group.index)),
                  ('Entrevista directa', numeric_enasem(group['tipent']).isin([1, 2])),
                  ('Edad conocida', numeric_enasem(group['edad']).notna()),
                  ('Edad 60+', numeric_enasem(group['edad']).ge(60))]
        for stage, mask in stages:
            before = len(current)
            current = current.loc[mask.reindex(current.index)]
            rows.append({'ronda': wave, 'filtro': stage, 'antes': before, 'excluidos': before-len(current),
                         'despues': len(current), 'personas': current['id'].nunique(),
                         'denominador': len(group), 'porcentaje_conservado': 100*len(current)/len(group)})
    return pd.DataFrame(rows)


def longitudinal_tables(data: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Presencia, entradas, reapariciones y transiciones con universo de origen explícito."""
    matrix = participation_matrix(data)
    patterns = matrix.apply(lambda row: ''.join(row.astype(int).astype(str)), axis=1).value_counts()
    lengths = matrix.sum(axis=1).value_counts().reindex(range(1, 7), fill_value=0).sort_index()
    patterns_table = pd.DataFrame({'patron_2001_a_2021': patterns.index, 'personas': patterns.values,
                                  'denominador_personas': len(matrix), 'porcentaje': 100*patterns.values/len(matrix)})
    entries, transitions, states, profiles, wave_followup = [], [], [], [], []
    types = data.assign(tipo=numeric_enasem(data['tipent'])).pivot(index='id', columns='ronda', values='tipo')
    types = types.reindex(columns=ROUND_TO_YEAR)
    for wave in ROUND_TO_YEAR:
        seen = matrix.loc[:, matrix.columns < wave].any(axis=1)
        current = matrix[wave]
        entries.append({'ronda': wave, 'primera_aparicion': int((current & ~seen).sum()),
                        'ya_observadas': int((current & seen).sum()),
                        'reaparecen_tras_ausencia': int((current & seen & ~matrix[wave-1]).sum()) if wave > 1 else 0,
                        'total': int(current.sum())})
        if wave > 1:
            previous = matrix[wave-1]
            missing_now = previous & ~current
            previous_dead = types[wave-1].eq(5)
            prior_n = int(previous.sum())
            wave_followup.append({'ronda': wave, 'ronda_origen': wave-1, 'denominador_anterior': prior_n,
                                  'continuan_desde_anterior': int((current & previous).sum()),
                                  'no_observadas_desde_anterior': int(missing_now.sum()),
                                  'ausentes_con_fallecimiento_previo': int((missing_now & previous_dead).sum()),
                                  'ausentes_sin_fallecimiento_previo': int((missing_now & ~previous_dead).sum()),
                                  'porcentaje_no_observadas': 100*missing_now.sum()/prior_n if prior_n else np.nan})
        if wave == 6:
            continue
        retained = current & matrix[wave+1]
        absent = current & ~matrix[wave+1]
        death_origin = current & types[wave].eq(5)
        living_origin = current & ~types[wave].eq(5)
        transitions.append({'origen': wave, 'destino': wave+1,
                            'intervalo_nominal_anos': ROUND_TO_YEAR[wave+1]-ROUND_TO_YEAR[wave],
                            'denominador_origen': int(current.sum()), 'continuan': int(retained.sum()),
                            'no_observadas': int(absent.sum()),
                            'ausentes_con_fallecimiento_previo': int((absent & death_origin).sum()),
                            'ausentes_sin_fallecimiento_previo': int((absent & living_origin).sum()),
                            'denominador_origen_vivas': int(living_origin.sum()),
                            'fallecimiento_documentado_destino': int((living_origin & types[wave+1].eq(5)).sum()),
                            'no_observadas_porcentaje': 100*absent.sum()/current.sum() if current.sum() else np.nan,
                            'ausentes_con_fallecimiento_previo_porcentaje': 100*(absent & death_origin).sum()/current.sum() if current.sum() else np.nan,
                            'ausentes_sin_fallecimiento_previo_porcentaje': 100*(absent & living_origin).sum()/current.sum() if current.sum() else np.nan,
                            'retencion_porcentaje': 100*retained.sum()/current.sum() if current.sum() else np.nan})
        state = types.loc[current, wave+1].map(INTERVIEW_LABELS).fillna('No observada')
        for source in sorted(types.loc[current, wave].unique()):
            counts = state.loc[types.loc[current, wave].eq(source)].value_counts()
            for target, n in counts.items():
                states.append({'origen': wave, 'destino': wave+1, 'tipo_origen': INTERVIEW_LABELS[source],
                               'estado_destino': target, 'n': n, 'denominador': counts.sum(),
                               'porcentaje': 100*n/counts.sum()})
        # Comparación en t en TODO el universo de origen, incluidos sobre fallecidos.
        for label, ids in [('Observada siguiente', matrix.index[retained]),
                           ('No observada siguiente', matrix.index[absent])]:
            group = data.loc[data['ronda'].eq(wave) & data['id'].isin(ids)]
            for variable in ['edad', 'educacion']:
                values = numeric_enasem(group[variable])
                profiles.append({'ronda': wave, 'grupo': label, 'variable': variable, 'categoria': 'continua',
                                 'n': int(values.count()), 'denominador': len(group),
                                 'porcentaje': 100*values.count()/len(group) if len(group) else np.nan,
                                 'media': values.mean(), 'mediana': values.median()})
            for variable in ['sexo', 'urbano', 'est_conyugal', 'tipent', 'edu_gru']:
                if variable not in group:
                    continue
                for row in frequency_table(group[variable], variable).to_dict('records'):
                    profiles.append({'ronda': wave, 'grupo': label, 'variable': variable, **row})
    intersections = matrix.astype(int).T.dot(matrix.astype(int))
    intersections.columns = [f'R{wave}' for wave in intersections.columns]
    entries_table = pd.DataFrame(entries)
    for column in ['primera_aparicion', 'ya_observadas', 'reaparecen_tras_ausencia']:
        entries_table[f'{column}_porcentaje'] = 100*entries_table[column]/entries_table.total.replace(0, np.nan)
    return {'patrones': patterns_table,
            'numero_rondas': pd.DataFrame({'rondas_observadas': lengths.index, 'personas': lengths.values,
                                          'denominador_personas': len(matrix), 'porcentaje': 100*lengths.values/len(matrix)}),
            'entradas': entries_table, 'seguimiento_ronda': pd.DataFrame(wave_followup),
            'transiciones': pd.DataFrame(transitions),
            'estados': pd.DataFrame(states), 'perfiles_seguimiento': pd.DataFrame(profiles),
            'intersecciones': intersections.reset_index()}


def build_audit(raw: pd.DataFrame, population: str | None = None) -> dict[str, pd.DataFrame]:
    """Audita TODA la base por defecto; los filtros requieren population explícita.

    Solo devuelve tablas agregadas. Las comparaciones de submuestras son
    secundarias y sus denominadores se refieren al universo auditado. La matriz
    y las máscaras permanecen privadas. Se valida el original antes de filtrar.
    """
    # Índice interno de filas: no deduplicar ni usar un índice de entrada repetido
    # para seleccionar mediante .loc, que podría multiplicar registros.
    full_data = prepare_audit(raw.reset_index(drop=True))
    data = select_population(full_data, population)
    selected_raw = raw.iloc[data.index]
    data['edad_cp1'] = age_groups(data.edad)
    masks = population_masks(data)
    rows, demographics, ages, education, weights, samples, compositions, age_tables, participation = [], [], [], [], [], [], [], [], []
    matrix = participation_matrix(data)
    n_waves = matrix.sum(axis=1)
    for wave, group in data.groupby('ronda'):
        for variable in ['tipent', 'sexo', 'est_conyugal', 'urbano', 'edad_gru', 'a_o_ent', 'fallecido', 'educacion', 'edu_gru']:
            tab = frequency_table(group[variable], variable)
            demographics.extend({'ronda': wave, 'variable': variable, **row} for row in tab.to_dict('records'))
        age_counts = group.edad_cp1.value_counts().reindex(AGE_LABELS, fill_value=0)
        age_tables.extend({'ronda': wave, 'categoria': category, 'n': int(n), 'denominador': len(group),
                           'porcentaje': 100*n/len(group)} for category, n in age_counts.items())
        n_counts = group.id.map(n_waves).value_counts().reindex(range(1, 7), fill_value=0)
        participation.extend({'ronda': wave, 'rondas_observadas_2001_2021': int(k), 'personas': int(n),
                              'denominador_personas_ronda': group.id.nunique(), 'porcentaje': 100*n/len(group)}
                             for k, n in n_counts.items())
        age = numeric_enasem(group['edad'])
        rows.append({'ronda': wave, 'ano_nominal': ROUND_TO_YEAR[wave], 'registros': len(group),
                     'personas': group['id'].nunique(), 'menores_60': int(age.lt(60).sum()),
                     'edad_60_mas': int(age.ge(60).sum()), 'edad_faltante': int(age.isna().sum()),
                     'duplicados': int(group.duplicated(['id', 'ronda']).sum()),
                     'discrepancias_fallecido_tipent': int((numeric_enasem(group['fallecido']).eq(1)
                                                          != numeric_enasem(group['tipent']).eq(5)).sum())})
        ages.append({'ronda': wave, 'denominador': len(group), 'n_validos': age.count(), 'media': age.mean(),
                     'de': age.std(), 'min': age.min(), 'q25': age.quantile(.25), 'mediana': age.median(),
                     'q75': age.quantile(.75), 'max': age.max()})
        edu = numeric_enasem(group.educacion)
        education.append({'ronda': wave, 'denominador': len(group), 'n_validos': edu.count(),
                          'n_faltantes': edu.isna().sum(), 'media': edu.mean(), 'de': edu.std(),
                          'min': edu.min(), 'q25': edu.quantile(.25), 'mediana': edu.median(),
                          'q75': edu.quantile(.75), 'max': edu.max()})
        for kind in ['factori', 'factorh']:
            col = f'{kind}_{str(ROUND_TO_YEAR[wave])[-2:]}'
            values = numeric_enasem(group[col])
            for interview, part in group.groupby('tipent'):
                v = values.loc[part.index]
                weights.append({'ronda': wave, 'variable': col, 'tipo_entrevista': INTERVIEW_LABELS[interview],
                                'denominador': len(part), 'validos': v.count(), 'positivos': v.gt(0).sum(),
                                'ceros': v.eq(0).sum(), 'negativos': v.lt(0).sum(), 'faltantes': v.isna().sum(),
                                'porcentaje_validos': 100*v.count()/len(part),
                                'porcentaje_positivos': 100*v.gt(0).sum()/len(part),
                                'porcentaje_ceros': 100*v.eq(0).sum()/len(part),
                                'porcentaje_faltantes': 100*v.isna().sum()/len(part),
                                'min': v.min(), 'mediana': v.median(), 'max': v.max()})
        for name, mask in masks.items():
            subset = group.loc[mask.reindex(group.index)]
            samples.append({'ronda': wave, 'muestra': name, 'registros': len(subset),
                            'personas': subset['id'].nunique(), 'denominador_registros': len(group),
                            'denominador_personas': group.id.nunique(),
                            'registros_excluidos': len(group)-len(subset),
                            'personas_excluidas': group.id.nunique()-subset.id.nunique(),
                            'porcentaje_registros_conservados': 100*len(subset)/len(group),
                            'porcentaje_personas_conservadas': 100*subset.id.nunique()/group.id.nunique()})
            for variable in ['sexo', 'edad_cp1', 'urbano', 'est_conyugal', 'tipent', 'edu_gru']:
                compositions.extend({'ronda': wave, 'muestra': name, 'variable': variable, **row}
                                    for row in frequency_table(subset[variable], variable).to_dict('records'))
    totals = [{'muestra': name, 'registros': int(mask.sum()), 'personas': data.loc[mask, 'id'].nunique(),
               'denominador_registros': len(data), 'denominador_personas': data['id'].nunique(),
               'registros_excluidos': len(data)-int(mask.sum()),
               'personas_excluidas': data.id.nunique()-data.loc[mask, 'id'].nunique(),
               'porcentaje_registros_conservados': 100*mask.sum()/len(data),
               'porcentaje_personas_conservadas': 100*data.loc[mask, 'id'].nunique()/data.id.nunique()}
              for name, mask in masks.items()]
    tables = {'rondas': pd.DataFrame(rows), 'demografia': pd.DataFrame(demographics),
              'edad': pd.DataFrame(ages), 'pesos': pd.DataFrame(weights), 'muestras_ronda': pd.DataFrame(samples),
              'edad_grupos': pd.DataFrame(age_tables), 'educacion': pd.DataFrame(education),
              'participacion_ronda': pd.DataFrame(participation),
              'muestras': pd.DataFrame(totals), 'composicion_muestras': pd.DataFrame(compositions),
              'faltantes': missing_by_wave(selected_raw), 'flujo': sample_flow(data)}
    tables.update(longitudinal_tables(data))
    tables['consistencia'] = longitudinal_consistency(data)
    tables['intervalos_efectivos'] = effective_intervals(data)
    chronology = []
    for (wave, interview), group in data.groupby(['ronda', 'tipent']):
        for row in frequency_table(group['a_o_ent'], 'a_o_ent').to_dict('records'):
            chronology.append({'ronda': wave, 'tipo_entrevista': INTERVIEW_LABELS[interview], **row})
    tables['cronologia'] = pd.DataFrame(chronology)
    tables['estructura'] = pd.DataFrame([{'poblacion': population or 'Toda la población registrada',
                                         'registros_originales': len(raw), 'personas_originales': full_data.id.nunique(),
                                         'registros_excluidos_por_seleccion': len(raw)-len(data),
                                         'personas_excluidas_por_seleccion': full_data.id.nunique()-data.id.nunique(),
                                         'registros': len(data), 'personas': data['id'].nunique(),
                                         'variables_originales': len(raw.columns), 'claves_faltantes': 0,
                                         'duplicados': 0}])
    return tables


def longitudinal_consistency(data: pd.DataFrame) -> pd.DataFrame:
    """Anomalías agregadas sin corregir sexo, edad ni historia de fallecimiento."""
    ordered = data.sort_values(['id', 'ronda']).copy()
    death_wave = ordered.loc[numeric_enasem(ordered.tipent).eq(5)].groupby('id').ronda.min()
    age = numeric_enasem(ordered.edad)
    previous_age = age.groupby(ordered.id).shift()
    checks = {
        'registros_despues_de_fallecimiento': int(ordered.ronda.gt(ordered.id.map(death_wave)).sum()),
        'personas_con_fallecimiento_repetido': int(ordered.loc[numeric_enasem(ordered.tipent).eq(5)].groupby('id').size().gt(1).sum()),
        'personas_con_sexo_valido_inconsistente': int(ordered.assign(sexo_num=numeric_enasem(ordered.sexo)).groupby('id').sexo_num.nunique().gt(1).sum()),
        'pares_con_edad_decreciente': int(age.lt(previous_age).sum()),
    }
    if 'ron_pat' in ordered:
        checks['personas_con_ron_pat_inconsistente_entre_registros'] = int(ordered.groupby('id').ron_pat.nunique().gt(1).sum())
    return pd.DataFrame({'control': list(checks), 'n': list(checks.values())})


def effective_intervals(data: pd.DataFrame) -> pd.DataFrame:
    """Años efectivos entre rondas nominalmente consecutivas; no imputa .f u otros códigos."""
    ordered = data.sort_values(['id', 'ronda']).copy()
    ordered['efectivo'] = numeric_enasem(ordered.a_o_ent)
    groups = ordered.groupby('id')
    ordered['siguiente_ronda'] = groups.ronda.shift(-1)
    ordered['intervalo_efectivo'] = groups.efectivo.shift(-1)-ordered.efectivo
    pairs = ordered.loc[ordered.siguiente_ronda.eq(ordered.ronda+1)]
    return pairs.groupby('ronda').intervalo_efectivo.agg(
        pares_observados='size', pares_con_anos_validos='count', min='min', mediana='median', max='max').reset_index()
