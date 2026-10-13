"""EDA pensionario incremental: selección explícita y agregados sin identificadores."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd

from .protection_eda import receipt_state, categorical_association

UNKNOWN = 'Desconocido'


@dataclass(frozen=True)
class PopulationSpec:
    """Filtros por visita; ninguna selección altera el maestro."""
    minimum_age: int | None = 60
    interview_types: tuple[int, ...] | None = None
    sex: int | None = None

    def select(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Devuelve una copia y comprueba la clave persona-ronda."""
        if frame[['id', 'ronda']].duplicated().any():
            raise ValueError('Clave persona-ronda duplicada')
        mask = pd.Series(True, index=frame.index)
        if self.minimum_age is not None:
            mask &= frame.edad.ge(self.minimum_age).fillna(False)
        if self.interview_types is not None:
            mask &= frame.tipent.isin(self.interview_types)
        if self.sex is not None:
            mask &= frame.sexo.eq(self.sex)
        return frame.loc[mask].copy()


def ownership_category(own: object, spouse: object) -> str:
    """Partición de estados auditados; No estructural se distingue en el universo."""
    if pd.isna(own) or pd.isna(spouse):
        return UNKNOWN
    return {(True, True): 'Ambas', (True, False): 'Solo propia',
            (False, True): 'Solo cónyuge', (False, False): 'Ambas negativas K'}[(bool(own), bool(spouse))]


def age_groups(age: pd.Series) -> pd.Series:
    """Grupos quinquenales solicitados, sin trasladar edades faltantes a 80+."""
    return pd.cut(age, [59, 64, 69, 74, 79, np.inf],
                  labels=['60–64', '65–69', '70–74', '75–79', '80+']).astype(object).fillna(UNKNOWN)


def categorical_table(frame: pd.DataFrame, variable: str, groups: Sequence[str] = ()) -> list[dict]:
    """Frecuencias, elegibles y composición; se retienen estratos ND."""
    rows: list[dict] = []
    groupings = frame.groupby(list(groups), dropna=False, observed=True, sort=True) if groups else [((), frame)]
    overall = frame[variable].value_counts(dropna=False)
    for keys, part in groupings:
        keys = keys if isinstance(keys, tuple) else (keys,)
        prefix = dict(zip(groups, keys))
        counts = part[variable].fillna(UNKNOWN).value_counts()
        known = len(part) - int(counts.get(UNKNOWN, 0))
        for category, n in counts.items():
            denominator = int(overall.get(category, 0))
            rows.append({**prefix, 'categoria': str(category), 'N': int(n),
                         'N_total': len(part), 'N_personas': part.id.nunique(),
                         'N_elegible': int(part.tipent.ne(5).sum()), 'N_valido': known,
                         'N_desconocido': len(part)-known, 'pct_total': 100*n/len(part),
                         'pct_validos': 100*n/known if known and category != UNKNOWN else None,
                         'pct_composicion_categoria': 100*n/denominator if denominator else None})
    return rows


def continuous_table(frame: pd.DataFrame, variable: str, groups: Sequence[str] = ()) -> list[dict]:
    """Distribuciones de montos o stocks por grupos, sin sumas entre titulares."""
    rows = []
    parts = frame.groupby(list(groups), dropna=False, observed=True, sort=True) if groups else [((), frame)]
    for keys, part in parts:
        keys = keys if isinstance(keys, tuple) else (keys,)
        values = pd.to_numeric(part[variable], errors='coerce').dropna()
        rows.append({**dict(zip(groups, keys)), 'variable': variable, 'N_total': len(part),
                     'N_personas': part.id.nunique(), 'N_valido': len(values),
                     'N_desconocido': len(part)-len(values), 'N_negativos': int(values.lt(0).sum()),
                     'N_ceros': int(values.eq(0).sum()), 'min': float(values.min()) if len(values) else None,
                     'p25': float(values.quantile(.25)) if len(values) else None,
                     'mediana': float(values.median()) if len(values) else None,
                     'p75': float(values.quantile(.75)) if len(values) else None,
                     'max': float(values.max()) if len(values) else None})
    return rows


def conditional_associations(frame: pd.DataFrame, group: str, strata: Sequence[str] = ()) -> list[dict]:
    """V dentro de la tercera dimensión, nunca V para un código ordinal arbitrario."""
    parts = frame.groupby(list(strata), dropna=False, observed=True) if strata else [((), frame)]
    results = []
    for keys, part in parts:
        keys = keys if isinstance(keys, tuple) else (keys,)
        valid = part.loc[part[group].ne(UNKNOWN) & part.P.ne(UNKNOWN)]
        results.append({**dict(zip(strata, keys)), 'grupo': group,
                        **categorical_association(valid, 'P', group),
                        'N_estrato': len(part), 'N_excluido_estrato': len(part)-len(valid)})
    return results


def stratified_transitions(frame: pd.DataFrame, year_a: int, year_b: int,
                           variable: str, group: str, comparable: bool) -> list[dict]:
    """Sigue IDs reales; muerte, ausencias y ND no son pérdidas de prestación.

    Los perfiles se fijan en origen. Una edad menor a 60 en destino no elimina
    retrospectivamente a un miembro de la cohorte ni corrige la edad original.
    """
    start = PopulationSpec(60, (1, 2, 3, 4)).select(frame.loc[frame.ano.eq(year_a)])
    end = frame.loc[frame.ano.eq(year_b)].set_index('id')
    if not end.index.is_unique:
        raise ValueError('ID duplicado en ronda de destino')
    later = set(frame.loc[frame.ano.gt(year_b), 'id'])
    rows = []
    for a in start.to_dict('records'):
        origin = str(a[variable])
        if a['id'] not in end.index:
            destination = 'Ausente con reaparición' if a['id'] in later else 'Ausente sin retorno observado'
        else:
            b = end.loc[a['id']]
            destination = 'Sobre fallecido' if b.tipent == 5 else str(b[variable])
        event = 'Estado no interpretable'
        if not comparable:
            event = 'Cambio de instrumento: transición no homologada'
        elif origin in ('Sí', 'No') and destination in ('Sí', 'No'):
            event = {('No','Sí'):'Inicio observado', ('Sí','Sí'):'Continuidad observada',
                     ('Sí','No'):'Pérdida observada', ('No','No'):'Negativas continuas'}[(origin,destination)]
        elif variable in ('titularidad_grupo', 'recepcion_ka') and UNKNOWN not in origin and UNKNOWN not in destination and destination not in (
                'Sobre fallecido', 'Ausente con reaparición', 'Ausente sin retorno observado'):
            event = 'Cambio/continuidad de ramas observado'
        rows.append({group: a[group], 'origen': origin, 'destino': destination, 'evento': event})
    if not rows:
        return []
    data = pd.DataFrame(rows)
    counts = data.groupby([group, 'origen', 'destino', 'evento'], dropna=False).size().reset_index(name='N')
    denominators = data.groupby([group, 'origen'], dropna=False).size()
    totals = data.groupby(group, dropna=False).size()
    output = []
    for r in counts.to_dict('records'):
        n_origin = int(denominators.loc[(r[group], r['origen'])])
        output.append({**r, 'ano_origen': year_a, 'ano_destino': year_b,
                       'intervalo_anos': year_b-year_a, 'variable': variable,
                       'comparabilidad_condicionada': comparable, 'N_origen_estado': n_origin,
                       'N_estrato_origen': int(totals.loc[r[group]]),
                       'pct_origen_estado': 100*r['N']/n_origin})
    assert sum(r['N'] for r in output) == len(start)
    return output


def institutional_people(events: pd.DataFrame, profiles: pd.DataFrame, groups: Sequence[str] = ()) -> list[dict]:
    """Instituciones múltiples: personas por institución, sin repetir montos.

    No sustituye desconocida por institución 'otra'. Porcentajes de instituciones
    no son una partición y pueden sumar más de 100.
    """
    e = events.loc[events.beneficiario_id.notna()].merge(
        profiles[['id', 'ano', 'tipent', *groups]], left_on=['beneficiario_id','ano'],
        right_on=['id','ano'], how='inner', validate='many_to_one')
    rows = []
    split = e.groupby(list(groups), dropna=False, observed=True) if groups else [((), e)]
    for keys, part in split:
        keys = keys if isinstance(keys, tuple) else (keys,)
        expanded = []
        for r in part.to_dict('records'):
            codes = list(r['instituciones_codigos']) if r['instituciones_codigos'] is not None else []
            for code in codes:
                expanded.append((r['id'], int(code)))
        known_ids = {x[0] for x in expanded}
        eligible = profiles
        for g, k in zip(groups, keys):
            eligible = eligible.loc[eligible[g].eq(k)]
        recipients = part.id.nunique()
        for code in sorted({x[1] for x in expanded}):
            n = len({i for i, c in expanded if c == code})
            rows.append({**dict(zip(groups, keys)), 'institucion_codigo': code,
                         'N_personas': n, 'N_receptoras_evento': recipients,
                         'N_receptoras_institucion_identificada': len(known_ids),
                         'N_receptoras_institucion_ND': recipients-len(known_ids),
                         'N_total_estrato': len(eligible),
                         'pct_receptoras_con_institucion': 100*n/len(known_ids) if known_ids else None,
                         'pct_total_estrato': 100*n/len(eligible) if len(eligible) else None})
    return rows
