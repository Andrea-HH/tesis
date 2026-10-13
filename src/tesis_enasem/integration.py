"""Integración izquierda auditable; no armoniza por semejanza ni atribuye hogares a personas."""
from __future__ import annotations

from collections import Counter
import json
import math
from numbers import Integral, Real
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
from pandas.io.stata import StataMissingValue

YEARS = (2001, 2003, 2012, 2015, 2018, 2021)
MISSING_CODES = {0: "valor almacenado", 1: ".", **{i + 2: f".{chr(97+i)}" for i in range(26)},
                 28: "NaN de lector", 29: "cadena vacía (conservada)"}


def identifier_token(value: object) -> str | None:
    """Conserva cadenas/ceros iniciales; números enteros no se redondean ni rellenan."""
    if isinstance(value, StataMissingValue) or pd.isna(value):
        return None
    if isinstance(value, str):
        if not value.strip():
            return None
        if ":" in value:
            raise ValueError("Un componente contiene el separador reservado ':'")
        return value
    if isinstance(value, (Integral, Real)) and not isinstance(value, bool):
        if not math.isfinite(float(value)) or int(value) != value:
            raise ValueError("Identificador numérico no entero; requiere formato documental explícito")
        return str(int(value))
    raise TypeError("Tipo de identificador no soportado")


def person_id(frame: pd.DataFrame) -> pd.Series:
    """ID estable cunicah:np; aborta si faltan claves, nunca inventa identificadores."""
    a, b = frame.cunicah.map(identifier_token), frame.np.map(identifier_token)
    if a.isna().any() or b.isna().any():
        raise ValueError("El maestro tiene claves personales incompletas")
    return (a + ":" + b).rename("id")


def normalized_keys(frame: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Normaliza equivalencias numéricas 1/1.0 sin perder formatos de texto."""
    return pd.DataFrame({c: frame[c].map(identifier_token) for c in keys}, index=frame.index)


def left_indexer(left: pd.DataFrame, right: pd.DataFrame, keys: list[str],
                 individual: bool = False) -> tuple[np.ndarray, np.ndarray, dict]:
    """Índices de unión validada; claves faltantes jamás se emparejan entre sí.

    -1 significa sin correspondencia. Rechaza duplicados derechos y, en fuentes
    personales, duplicados izquierdos. No resuelve conflictos tomando la primera fila.
    """
    l, r = normalized_keys(left, keys), normalized_keys(right, keys)
    lc, rc = l.notna().all(axis=1), r.notna().all(axis=1)
    if r.loc[rc].duplicated(keys).any():
        raise ValueError("Fuente derecha no única: unión muchos-a-muchos prohibida")
    if individual and l.loc[lc].duplicated(keys).any():
        raise ValueError("Clave personal izquierda no única")
    a = l.loc[lc].reset_index(drop=True).assign(_left=np.flatnonzero(lc))
    b = r.loc[rc].reset_index(drop=True).assign(_right=np.flatnonzero(rc))
    joined = a.merge(b, how="left", on=keys, validate="one_to_one" if individual else "many_to_one",
                     sort=False)
    ix = np.full(len(left), -1, dtype=np.int64)
    found = joined._right.notna()
    ix[joined.loc[found, "_left"].to_numpy(dtype=int)] = joined.loc[found, "_right"].to_numpy(dtype=int)
    audit = {"n_izquierda": len(left), "n_derecha": len(right), "n_enlazadas": int((ix >= 0).sum()),
             "n_claves_izquierda_incompletas": int((~lc).sum()),
             "n_claves_derecha_incompletas": int((~rc).sum()), "duplicados_derecha": 0,
             "n_derecha_utilizadas": len(set(ix[ix >= 0])),
             "cardinalidad": "one_to_one" if individual else "many_to_one"}
    return ix, lc.to_numpy(), audit


def economic_link(master: pd.DataFrame, source: pd.DataFrame, year: int, keys: list[str],
                  individual: bool, bridge: pd.DataFrame | None = None) -> dict:
    """Paso reproducible de enlace económico en una ronda, con puente temprano obligatorio."""
    wave = YEARS.index(year) + 1
    rows = np.flatnonzero(master.ronda.eq(wave))
    target = master.iloc[rows]
    bridge_missing = np.zeros(len(target), dtype=bool)
    if not individual and year in (2001, 2003):
        if bridge is None:
            raise ValueError("2001/2003 requieren puente individual, no unión directa de hogar")
        pkeys = ["cunicah", f"codent{str(year)[-2:]}"]
        bix, _, _ = left_indexer(target, bridge, pkeys, individual=True)
        bridge_missing = bix < 0
        target_keys = pd.DataFrame({c: [bridge.iloc[j][c] if j >= 0 else None for j in bix] for c in keys})
        ix, complete, audit = left_indexer(target_keys, source, keys)
    else:
        ix, complete, audit = left_indexer(target, source, keys, individual=individual)
    full_ix = np.full(len(master), -1, dtype=np.int64)
    full_ix[rows] = ix
    states = np.where(ix >= 0, "enlazado", np.where(bridge_missing, "sin_puente_personal",
                      np.where(complete, "clave_sin_correspondencia", "clave_incompleta")))
    return {"rows": rows, "indexer": ix, "full_indexer": full_ix, "states": states, "audit": audit}


def encode_stata(series: pd.Series) -> tuple[pa.Array, pa.Array, dict[str, int]]:
    """Codifica valor y tag por separado; preserva RF/DK numéricos sin recodificarlos.

    Las cadenas vacías permanecen cadenas vacías. Los null de una unión se distinguen
    por estado de fuente; el tag solo describe un valor presente en el archivo original.
    """
    values, tags = [], []
    for value in series:
        if isinstance(value, StataMissingValue):
            tag = 1 if value.string == "." else ord(value.string[1]) - 97 + 2
            values.append(None)
        elif pd.isna(value):
            tag = 28
            values.append(None)
        else:
            tag = 29 if isinstance(value, str) and not value.strip() else 0
            values.append(value)
        tags.append(tag)
    # Columnas enteramente faltantes siguen siendo numéricas, evitando esquema null.
    array = pa.array(values) if any(v is not None for v in values) else pa.array(values, type=pa.float64())
    tag_array = pa.array(tags, type=pa.uint8())
    return array, tag_array, {MISSING_CODES[k]: n for k, n in Counter(tags).items()}


def take_nullable(array: pa.Array, indexer: np.ndarray) -> pa.Array:
    """Take con null para no enlazados; -1 no selecciona accidentalmente la última fila."""
    return pc.take(array, pa.array(indexer, mask=indexer < 0, type=pa.int64()))


def restore_stata(values: pd.Series, tags: pd.Series) -> pd.Series:
    """Recupera objetos de faltante Stata; null de unión conserva NA sin inventar tags."""
    lookup = {x.string: x for x in (StataMissingValue(v) for v in StataMissingValue.MISSING_VALUES)}
    out = values.astype(object).copy()
    for code, label in MISSING_CODES.items():
        if label in lookup:
            out.loc[tags.eq(code).fillna(False)] = lookup[label]
    return out


def load_integrated(path: Path | str, columns: list[str] | None = None) -> pd.DataFrame:
    """Carga selectiva de Parquet para Python; usar columns evita materializar miles de campos."""
    return pd.read_parquet(path, columns=columns)


def response_number(value: object, excluded: tuple[int, ...] = ()) -> float | None:
    """Valor numérico de una pregunta validada; excluye solo sus códigos documentados."""
    if isinstance(value, StataMissingValue) or pd.isna(value) or isinstance(value, str):
        return None
    number = float(value)
    return None if number in excluded or not math.isfinite(number) else number


def pension_2021_record(master_np: object, mode: int, individual: dict | None,
                        household: dict | None) -> dict:
    """Pensiones/apoyos 2021 propios: orientación doble, códigos y montos originales.

    No instancia las ocho armonizaciones definitivas. Devuelve mínimos de slots y
    sumas observadas parciales, nunca ingreso total. No usa montos imputados para
    inferir recepción. La modalidad de fallecido no acredita recepción actual.
    """
    out = {"econ_titular_estado": "sin_fuentes_2021", "pension_recibe_k_2021": None,
           "pension_fuentes_2021": None, "pension_num_declaradas_min_2021": None,
           "pension_monto_mensual_observado_parcial_2021": None,
           "pension_contributiva_evidencia_2021": None, "apoyo_vejez_evidencia_2021": None,
           "apoyo_publico_recibe_2021": None, "apoyo_publico_fuentes_2021": None}
    if not individual or not household:
        return out
    if mode == 5:
        out["econ_titular_estado"] = "sobre_fallecido_no_atribuir_recepcion_actual"
        return out
    np_value = response_number(master_np)
    key = response_number(individual.get("key_21"))
    own = response_number(individual.get("k45d_21")) == np_value
    spouse = response_number(individual.get("k52a_1_21")) == np_value
    if own == spouse or key not in (1, 2) or (key == 1) != own:
        out["econ_titular_estado"] = "orientacion_individual_no_confirmada"
        return out
    pointer = "k45d_21" if own else "k52a_1_21"
    hh_own = response_number(household.get("k45d_21")) == np_value
    hh_spouse = response_number(household.get("k52a_1_21")) == np_value
    if hh_own and hh_spouse:
        out["econ_titular_estado"] = "titular_hogar_ambiguo_ambos_punteros"
        return out
    if response_number(household.get(pointer)) != np_value:
        out["econ_titular_estado"] = "puntero_hogar_individual_discrepante"
        return out
    if not own and (response_number(household.get("k52a_21")) != 2
                    or response_number(individual.get("k52a_21")) != 2):
        out["econ_titular_estado"] = "rama_conyuge_no_confirmada"
        return out
    out["econ_titular_estado"] = "propio_validado" if own else "conyuge_es_esta_persona_validado"
    flags = [f"k58{c}_21" for c in "abcd"] if own else [f"k64{c}_21" for c in "cdef"]
    answers = [response_number(household.get(c), (8, 9)) for c in flags]
    received = True if 1 in answers else False if all(v == 2 for v in answers) else None
    out["pension_recibe_k_2021"] = received
    institution_names = {1: "IMSS", 2: "ISSSTE", 3: "Otra institución pública agrupada",
                         4: "Privada", 5: "Seguridad Social EUA", 6: "Otra institución", 7: "Persona"}
    types = ["jubilacion", "viudez", "invalidez_accidente", "otra"]
    events, amounts = [], []
    for t, answer in enumerate(answers, 1):
        if answer != 1:
            continue
        for slot in (1, 2):
            provider_name = f"k{59 if own else 65}_{t}_{slot}_21"
            amount_name = f"k{61 if own else 67}_{t}_{slot}_21"
            start_name = f"k{60 if own else 66}_{t}_{slot}_21"
            raw_provider = response_number(household.get(provider_name))
            raw_amount = response_number(household.get(amount_name))
            # No afirmar una segunda pensión porque el slot exista en el esquema.
            if slot == 2 and raw_provider is None and raw_amount is None:
                continue
            provider = response_number(household.get(provider_name), (88, 99))
            amount = response_number(household.get(amount_name), (8888888, 9999999))
            if amount is not None and amount < 0:
                amount = None
            classification = "contributiva_identificada" if provider in (1, 2) else "desconocida"
            events.append({"tipo_declarado": types[t-1], "slot": slot,
                           "institucion_codigo_original": raw_provider,
                           "institucion": institution_names.get(provider, "desconocida"),
                           "clasificacion_evidencia": classification,
                           "monto_original_codigo": raw_amount, "monto_mensual_valido": amount,
                           "anio_inicio": response_number(household.get(start_name), (8888, 9999)),
                           "fuente": "F10_original", "variable_institucion": provider_name,
                           "variable_monto": amount_name, "imputacion_usada": False})
            if amount is not None:
                amounts.append(amount)
    out["pension_fuentes_2021"] = json.dumps(events, ensure_ascii=False, allow_nan=False)
    out["pension_num_declaradas_min_2021"] = len(events) if received is not None else None
    out["pension_monto_mensual_observado_parcial_2021"] = sum(amounts) if amounts else None
    out["pension_contributiva_evidencia_2021"] = (True if any(e["clasificacion_evidencia"] == "contributiva_identificada"
                                                              for e in events) else False if received is False else None)
    gate_name = "k79a_21" if own else "k82c_21"
    gate = response_number(household.get(gate_name), (8, 9))
    out["apoyo_publico_recibe_2021"] = True if gate == 1 else False if gate == 2 else None
    supports = []
    if gate == 1:
        for slot in (1, 2):
            program_name = f"k{'79a' if own else '82c'}_1_{slot}_21"
            amount_name = f"k{80 if own else 83}_1_{slot}_21"
            program = response_number(household.get(program_name), (8, 9))
            raw_program = response_number(household.get(program_name))
            amount = response_number(household.get(amount_name), (8888888, 9999999))
            if slot == 2 and raw_program is None and amount is None:
                continue
            classification = ("no_contributiva_vejez_identificada" if program == 5 else
                              "otro_apoyo_publico_identificado" if program in (1, 2) else
                              "INAPAM_dinero_o_especie_sin_pension_identificable" if program == 3 else "desconocida")
            supports.append({"programa_codigo_original": raw_program, "clasificacion_evidencia": classification,
                             "monto_mensual_valido": amount if amount is not None and amount >= 0 else None,
                             "fuente": "F10_original", "variable_programa": program_name,
                             "variable_monto": amount_name, "dinero_o_especie_no_desagregado": True,
                             "imputacion_usada": False})
    out["apoyo_publico_fuentes_2021"] = json.dumps(supports, ensure_ascii=False, allow_nan=False)
    out["apoyo_vejez_evidencia_2021"] = True if any(e["programa_codigo_original"] == 5 for e in supports) else False if gate == 2 else None
    return out
