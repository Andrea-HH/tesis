"""Diagnóstico agregado para revisar CP1; no corrige ni exporta casos individuales."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from .audit import prepare_audit
from .config import ROUND_TO_YEAR
from .missing import numeric_enasem


def investigate_anomalies(raw: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Amplía alertas existentes usando pares adyacentes observados, no imputados.

    Devuelve exclusivamente agregados. Un faltante de edad interrumpe la
    comparación: no se salta a una observación válida más antigua. El contraste
    con nacimiento es un intervalo aproximado, no una edad corregida.
    """
    data = prepare_audit(raw).sort_values(['id', 'ronda']).reset_index(drop=True)
    for column in ['edad', 'sexo', 'tipent', 'fallecido', 'a_o_ent', 'a_o_nac', 'mes_nac']:
        data[column] = numeric_enasem(data[column])
    previous = data.groupby('id')[['edad', 'ronda', 'tipent', 'a_o_ent', 'a_o_nac', 'mes_nac']].shift()
    pairs = previous.ronda.notna()
    eligible = pairs & data.edad.notna() & previous.edad.notna()
    declined = eligible & data.edad.lt(previous.edad)
    first_death = data.loc[data.tipent.eq(5)].groupby('id').ronda.min()
    after_death = data.ronda.gt(data.id.map(first_death))
    inconsistent_sex_ids = data.groupby('id').sexo.nunique().loc[lambda x: x.gt(1)].index
    sex_rows = data.id.isin(inconsistent_sex_ids)
    death_twice = data.loc[data.tipent.eq(5)].groupby('id').size().gt(1).sum()
    decline_size = (previous.edad - data.edad).loc[declined]
    year_valid = declined & data.a_o_ent.notna() & previous.a_o_ent.notna()
    birth_valid = declined & data.a_o_nac.notna() & previous.a_o_nac.notna()
    month_valid = declined & data.mes_nac.notna() & previous.mes_nac.notna()
    date_valid = year_valid & birth_valid
    gap_current = data.a_o_ent - data.a_o_nac
    gap_previous = previous.a_o_ent - previous.a_o_nac
    compatible_current = data.edad.ge(gap_current - 1) & data.edad.le(gap_current)
    compatible_previous = previous.edad.ge(gap_previous - 1) & previous.edad.le(gap_previous)

    summary = {
        'registros_originales': len(data), 'personas_originales': data.id.nunique(),
        'pares_observados': int(pairs.sum()), 'pares_edad_evaluables': int(eligible.sum()),
        'pares_edad_no_evaluables': int((pairs & ~eligible).sum()),
        'pares_edad_decreciente': int(declined.sum()),
        'personas_edad_decreciente': data.loc[declined, 'id'].nunique(),
        'pares_descenso_rondas_consecutivas': int((declined & data.ronda.sub(previous.ronda).eq(1)).sum()),
        'pares_descenso_cruzan_60': int((declined & previous.edad.ge(60) & data.edad.lt(60)).sum()),
        'registros_posteriores_fallecimiento': int(after_death.sum()),
        'personas_posteriores_fallecimiento': data.loc[after_death, 'id'].nunique(),
        'personas_fallecimiento_repetido': int(death_twice),
        'discrepancias_tipent_fallecido': int(data.tipent.eq(5).ne(data.fallecido.eq(1)).sum()),
        'personas_sexo_inconsistente': len(inconsistent_sex_ids),
        'registros_personas_sexo_inconsistente': int(sex_rows.sum()),
        'pares_descenso_entrevista_anos_validos': int(year_valid.sum()),
        'pares_descenso_entrevista_ano_creciente': int((year_valid & data.a_o_ent.gt(previous.a_o_ent)).sum()),
        'pares_descenso_nacimiento_anos_validos': int(birth_valid.sum()),
        'pares_descenso_nacimiento_ano_igual': int((birth_valid & data.a_o_nac.eq(previous.a_o_nac)).sum()),
        'pares_descenso_nacimiento_meses_validos': int(month_valid.sum()),
        'pares_descenso_nacimiento_mes_igual': int((month_valid & data.mes_nac.eq(previous.mes_nac)).sum()),
    }

    def frequency(values: pd.Series, name: str, order: list[str] | None = None) -> pd.DataFrame:
        counts = values.value_counts(sort=False).sort_index()
        if order is not None:
            counts = counts.reindex([category for category in order if category in counts.index])
        return pd.DataFrame({name: counts.index, 'n': counts.values,
                             'denominador': len(values),
                             'porcentaje': 100 * counts.values / len(values) if len(values) else []})

    modalities = pd.Series(
        ['Directa' if t in (1, 2) else 'Sustituto' if t in (3, 4) else 'Sobre fallecido'
         for t in data.loc[after_death, 'tipent']], dtype=object)
    pair_types = pd.Series(
        [('Directa' if p in (1, 2) else 'Sustituto') + ' → ' +
         ('Directa' if c in (1, 2) else 'Sustituto')
         for p, c in zip(previous.loc[declined, 'tipent'], data.loc[declined, 'tipent'])], dtype=object)
    compatibility = pd.Series(
        ['Anterior ' + ('compatible' if p else 'incompatible') + '; actual ' +
         ('compatible' if c else 'incompatible')
         for p, c in zip(compatible_previous[date_valid], compatible_current[date_valid])], dtype=object)
    magnitudes = pd.cut(decline_size, [0, 1, 4, 9, float('inf')],
                        labels=['1 año', '2–4 años', '5–9 años', '10 años o más']).astype(object)
    stats = decline_size.describe(percentiles=[.25, .5, .75]).rename_axis('estadistico').reset_index(name='valor')
    return {
        'resumen': pd.DataFrame({'control': summary.keys(), 'n': summary.values()}),
        'posteriores_modalidad': frequency(modalities, 'modalidad'),
        # No se devuelve la trayectoria de los dos casos raros ni sus atributos.
        'edad_destino': frequency(data.loc[declined, 'ronda'].map(ROUND_TO_YEAR), 'ano_destino'),
        'edad_saltos': frequency(data.loc[declined, 'ronda'].sub(previous.loc[declined, 'ronda']).astype(int), 'salto_rondas'),
        'edad_magnitud': frequency(magnitudes, 'descenso', ['1 año', '2–4 años', '5–9 años', '10 años o más']),
        'edad_pares_por_persona': frequency(data.loc[declined].groupby('id').size(), 'pares_decrecientes_por_persona'),
        'edad_modalidad': frequency(pair_types, 'modalidades_par'),
        'edad_compatibilidad': frequency(compatibility, 'compatibilidad_aproximada'),
        'edad_estadisticos': stats,
    }


def review_transitions(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Añade retornos futuros a transiciones existentes usando patrones agregados.

    Un cero tras la última ronda no indica pérdida definitiva: es censura por
    final del archivo. Retorno cuenta cualquier modalidad, incluso fallecido.
    """
    trans = tables['transiciones'].copy()
    trans['ano_origen'] = trans.origen.map(ROUND_TO_YEAR)
    trans['ano_destino'] = trans.destino.map(ROUND_TO_YEAR)
    temporary = []
    for origin, destination in zip(trans.origen, trans.destino):
        temporary.append(sum(int(row.personas) for row in tables['patrones'].itertuples()
                             if row.patron_2001_a_2021[origin - 1] == '1'
                             and row.patron_2001_a_2021[destination - 1] == '0'
                             and '1' in row.patron_2001_a_2021[destination:]))
    trans['ausentes_con_reaparicion_posterior'] = temporary
    trans['ausentes_con_reaparicion_posterior_porcentaje'] = 100 * pd.Series(temporary, index=trans.index) / trans.denominador_origen
    trans['ausentes_sin_reaparicion_observada_hasta_2021'] = trans.no_observadas - trans.ausentes_con_reaparicion_posterior
    return trans


def plot_anomalies(tables: dict[str, pd.DataFrame], directory: Path | None = None) -> plt.Figure:
    """Gráfica agregada de descensos de edad; omite historias de casos raros."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 4), layout='constrained')
    for ax, name, category, title in [
        (axes[0], 'edad_destino', 'ano_destino', 'Ronda de destino'),
        (axes[1], 'edad_magnitud', 'descenso', 'Magnitud del descenso'),
    ]:
        table = tables[name]
        ax.bar(table[category].astype(str), table.n, color=plt.cm.BrBG(.2))
        ax.set_title(title)
        ax.set_ylabel('Pares con edad decreciente')
        for x, n in enumerate(table.n):
            ax.text(x, n, str(n), ha='center', va='bottom')
        ax.set_ylim(0, max(table.n.max() * 1.2, 1) if len(table) else 1)
    fig.suptitle('CP1: diagnóstico de edad — pares adyacentes observados con ambas edades válidas')
    if directory is not None:
        directory.mkdir(parents=True, exist_ok=True)
        fig.savefig(directory / 'cp1_anomalias_edad.png', dpi=150)
    return fig
