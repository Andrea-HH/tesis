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
CATEGORY_LABELS = {
    'tipent': INTERVIEW_LABELS, 'sexo': {1: 'Hombre', 2: 'Mujer'},
    'est_conyugal': {1: 'Casado o en unión', 2: 'Separado o divorciado', 3: 'Viudo', 4: 'Soltero'},
    'urbano': {0: 'Menos de 100 mil residentes', 1: '100 mil residentes o más'},
    'edad_gru': {0: '49 o menos', 1: '50–59', 2: '60–69', 3: '70–79', 4: '80 o más'},
    'fallecido': {0: 'No', 1: 'Sí'},
}


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
    entries, transitions, states, profiles = [], [], [], []
    types = data.assign(tipo=numeric_enasem(data['tipent'])).pivot(index='id', columns='ronda', values='tipo')
    types = types.reindex(columns=ROUND_TO_YEAR)
    for wave in ROUND_TO_YEAR:
        seen = matrix.loc[:, matrix.columns < wave].any(axis=1)
        current = matrix[wave]
        entries.append({'ronda': wave, 'primera_aparicion': int((current & ~seen).sum()),
                        'ya_observadas': int((current & seen).sum()),
                        'reaparecen_tras_ausencia': int((current & seen & ~matrix[wave-1]).sum()) if wave > 1 else 0,
                        'total': int(current.sum())})
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
                            'retencion_porcentaje': 100*retained.sum()/current.sum() if current.sum() else np.nan})
        state = types.loc[current, wave+1].map(INTERVIEW_LABELS).fillna('No observada')
        for source in sorted(types.loc[current, wave].unique()):
            counts = state.loc[types.loc[current, wave].eq(source)].value_counts()
            for target, n in counts.items():
                states.append({'origen': wave, 'destino': wave+1, 'tipo_origen': INTERVIEW_LABELS[source],
                               'estado_destino': target, 'n': n, 'denominador': counts.sum(),
                               'porcentaje': 100*n/counts.sum()})
        # Comparación en t solo entre entrevistados vivos en t; no usa valores futuros.
        for label, ids in [('Observada siguiente', matrix.index[living_origin & retained]),
                           ('No observada siguiente', matrix.index[living_origin & absent])]:
            group = data.loc[data['ronda'].eq(wave) & data['id'].isin(ids)]
            for variable in ['edad', 'educacion']:
                values = numeric_enasem(group[variable])
                profiles.append({'ronda': wave, 'grupo': label, 'variable': variable, 'categoria': 'continua',
                                 'n': int(values.count()), 'denominador': len(group),
                                 'porcentaje': 100*values.count()/len(group) if len(group) else np.nan,
                                 'media': values.mean(), 'mediana': values.median()})
            for variable in ['sexo', 'urbano', 'est_conyugal', 'tipent']:
                for row in frequency_table(group[variable], variable).to_dict('records'):
                    profiles.append({'ronda': wave, 'grupo': label, 'variable': variable, **row})
    intersections = matrix.astype(int).T.dot(matrix.astype(int))
    intersections.columns = [f'R{wave}' for wave in intersections.columns]
    return {'patrones': patterns_table,
            'numero_rondas': pd.DataFrame({'rondas_observadas': lengths.index, 'personas': lengths.values,
                                          'denominador_personas': len(matrix), 'porcentaje': 100*lengths.values/len(matrix)}),
            'entradas': pd.DataFrame(entries), 'transiciones': pd.DataFrame(transitions),
            'estados': pd.DataFrame(states), 'perfiles_seguimiento': pd.DataFrame(profiles),
            'intersecciones': intersections.reset_index()}


def build_audit(raw: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Construye únicamente tablas agregadas; la matriz y las máscaras no se exportan."""
    data = prepare_audit(raw)
    masks = population_masks(data)
    rows, demographics, ages, weights, samples, compositions = [], [], [], [], [], []
    for wave, group in data.groupby('ronda'):
        for variable in ['tipent', 'sexo', 'est_conyugal', 'urbano', 'edad_gru', 'a_o_ent', 'fallecido']:
            tab = frequency_table(group[variable], variable)
            demographics.extend({'ronda': wave, 'variable': variable, **row} for row in tab.to_dict('records'))
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
        for kind in ['factori', 'factorh']:
            col = f'{kind}_{str(ROUND_TO_YEAR[wave])[-2:]}'
            values = numeric_enasem(group[col])
            for interview, part in group.groupby('tipent'):
                v = values.loc[part.index]
                weights.append({'ronda': wave, 'variable': col, 'tipo_entrevista': INTERVIEW_LABELS[interview],
                                'denominador': len(part), 'validos': v.count(), 'positivos': v.gt(0).sum(),
                                'ceros': v.eq(0).sum(), 'negativos': v.lt(0).sum(), 'faltantes': v.isna().sum(),
                                'min': v.min(), 'mediana': v.median(), 'max': v.max()})
        for name, mask in masks.items():
            subset = group.loc[mask.reindex(group.index)]
            samples.append({'ronda': wave, 'muestra': name, 'registros': len(subset),
                            'personas': subset['id'].nunique(), 'denominador_registros': len(group)})
            for variable in ['sexo', 'edad_gru', 'urbano', 'est_conyugal', 'tipent']:
                compositions.extend({'ronda': wave, 'muestra': name, 'variable': variable, **row}
                                    for row in frequency_table(subset[variable], variable).to_dict('records'))
    totals = [{'muestra': name, 'registros': int(mask.sum()), 'personas': data.loc[mask, 'id'].nunique(),
               'denominador_registros': len(data), 'denominador_personas': data['id'].nunique()}
              for name, mask in masks.items()]
    tables = {'rondas': pd.DataFrame(rows), 'demografia': pd.DataFrame(demographics),
              'edad': pd.DataFrame(ages), 'pesos': pd.DataFrame(weights), 'muestras_ronda': pd.DataFrame(samples),
              'muestras': pd.DataFrame(totals), 'composicion_muestras': pd.DataFrame(compositions),
              'faltantes': missing_by_wave(raw), 'flujo': sample_flow(data)}
    tables.update(longitudinal_tables(data))
    tables['consistencia'] = longitudinal_consistency(data)
    tables['intervalos_efectivos'] = effective_intervals(data)
    chronology = []
    for (wave, interview), group in data.groupby(['ronda', 'tipent']):
        for row in frequency_table(group['a_o_ent'], 'a_o_ent').to_dict('records'):
            chronology.append({'ronda': wave, 'tipo_entrevista': INTERVIEW_LABELS[interview], **row})
    tables['cronologia'] = pd.DataFrame(chronology)
    tables['estructura'] = pd.DataFrame([{'registros': len(raw), 'personas': data['id'].nunique(),
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
