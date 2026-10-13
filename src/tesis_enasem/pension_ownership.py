"""Auditoría provisional de beneficiarios; no altera fuentes ni la base integrada."""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Mapping, Sequence

from .integration import response_number


@dataclass(frozen=True)
class WaveContract:
    """Nombres documentados del bloque de pensiones de cada instrumento."""

    year: int
    individual: str
    household: str
    imputed: str | None
    key: str | None
    own_gates: tuple[str, ...]
    spouse_gates: tuple[str, ...]
    couple: str | None
    informant: str | None
    person_code: str
    slots: int


def wave_contract(year: int) -> WaveContract:
    """Selecciona preguntas originales, sin extrapolar nombres entre instrumentos."""
    configs = {
        2001: ("F13", "F12", "F19", "key01", "k55", "abcd", "k61", "abcd", "num_k", None, "codent01", 1),
        2003: ("F14", "F11", "F18", "key03", "k58", "abcd", "k64", "cdef", "k64a", "k96a", "codent03", 1),
        2012: ("F15", "F07", "F01", "key12", "k58", "abcd", "k64", "cdef", None, "k96a_12", "np", 1),
        2015: ("F16", "F08", "F02", "key15", "k58", "abcd", "k64", "cdef", "hog_sc", "k96a_15", "np", 3),
        2018: ("F04", "F09", None, None, "k58", "abcd", "k64", "cdef", "k52a_18", None, "np", 2),
        2021: ("F17", "F10", "F03", "key_21", "k58", "abcd", "k64", "cdef", "k52a_21", None, "np", 2),
    }
    i, h, m, key, og, oc, sg, sc, couple, inf, code, slots = configs[year]
    suffix = f"_{year % 100:02}" if year >= 2012 else ""
    return WaveContract(year, i, h, m, key, tuple(og+c+suffix for c in oc),
                        tuple(sg+c+suffix for c in sc), couple, inf, code, slots)


def receipt(record: Mapping, gates: Sequence[str]) -> bool | None:
    """Sí ante una afirmativa; no solo con cuatro negativas; NR/NS desconocidos."""
    values = [response_number(record.get(g), (8, 9)) for g in gates]
    return True if 1 in values else False if all(v == 2 for v in values) else None


def tri_or(a: bool | None, b: bool | None) -> bool | None:
    """Disyunción con desconocidos, sin convertirlos en cero."""
    return True if a is True or b is True else False if a is False and b is False else None


def orient_person(person: Mapping, individual: Mapping | None, household: Mapping | None,
                  contract: WaveContract) -> tuple[int | None, str]:
    """Determina la rama beneficiaria, conservando límites de la orientación histórica.

    Para 2001 el J1/control original no está en las fuentes suministradas: se
    conserva la orientación publicada con un nivel de evidencia distinto. No se
    reconstruye el orden de entrevista a partir de edad, sexo o NP.
    """
    if individual is None or household is None:
        return None, "sin_fuentes"
    if response_number(person.get("tipent")) == 5:
        return None, "sobre_fallecido_sin_atribucion_actual"
    year = contract.year
    code = response_number(person.get(contract.person_code))
    key = response_number(individual.get(contract.key)) if contract.key else None
    if code is None:
        return None, "codigo_personal_ausente"
    if year >= 2018:
        suffix = f"_{year % 100:02}"
        a, b, pair = "k45d"+suffix, "k52a_1"+suffix, "k52a"+suffix
        own = response_number(individual.get(a)) == code
        spouse = response_number(individual.get(b)) == code
        if own == spouse or (contract.key and (key not in (1, 2) or (key == 1) != own)):
            return None, "orientacion_individual_no_confirmada"
        if response_number(household.get(a)) == code == response_number(household.get(b)):
            return None, "ambos_punteros_mismo_titular"
        if response_number(household.get(a if own else b)) != code:
            return None, "puntero_hogar_individual_discrepante"
        if spouse and (response_number(individual.get(pair)) != 2 or response_number(household.get(pair)) != 2):
            return None, "rama_conyuge_no_confirmada"
        return (1 if own else 2), "puntero_personal_concordante"
    if key not in (1, 2):
        return None, "orientacion_proveedor_ausente"
    if year == 2001:
        return int(key), "orientacion_proveedor_sin_J1_original"
    informant = response_number(household.get(contract.informant))
    if year == 2003:
        if informant == 3 and code in (3, 4):
            return (1, "informante_codigo_3_condicionado_unicidad") if key == 1 else (None, "key_informante_discrepante")
        allowed = (1, 2, 3)
    else:
        allowed = (10, 20, 11, 12, 13, 21, 22, 23)
    if informant not in allowed:
        return None, "informante_externo_o_ausente_orden_no_verificado"
    expected = 1 if informant == code else 2
    if key != expected:
        return None, "key_informante_discrepante"
    if key == 2 and contract.couple and response_number(household.get(contract.couple)) != 2:
        return None, "rama_conyuge_no_confirmada"
    return int(key), "key_informante_concordante"


def pension_events(record: Mapping, contract: WaveContract, role: int) -> list[dict]:
    """Una medición por tipo/slot, conservando todas las instituciones.

    En 2012/2015 la lista institucional pertenece al grupo de contingencia:
    nunca se replica el monto por cada institución marcada.
    """
    year, suffix = contract.year, f"_{contract.year % 100:02}"
    gates = contract.own_gates if role == 1 else contract.spouse_gates
    events = []
    for typ, gate in enumerate(gates, 1):
        if response_number(record.get(gate), (8, 9)) != 1:
            continue
        for slot in range(1, contract.slots+1):
            if year == 2001:
                amount = f"k{58 if role == 1 else 64}_{typ}"
                institution = f"k{56 if role == 1 else 62}_{typ}"
                start = f"k{57 if role == 1 else 63}_{typ}"
            elif year == 2003:
                letter = ("abcd" if role == 1 else "cdef")[typ-1]
                amount = f"k{61 if role == 1 else 67}{letter}"
                institution = f"k{59 if role == 1 else 65}{letter}"
                start = f"k{60 if role == 1 else 66}{letter}"
            else:
                slot_part = "" if year == 2012 else f"_{slot}"
                amount = f"k{61 if role == 1 else 67}_{typ}{slot_part}{suffix}"
                institution = f"k{59 if role == 1 else 65}_{typ}_{slot}{suffix}"
                start = f"k{60 if role == 1 else 66}_{typ}{slot_part}{suffix}"
            raw_amount = response_number(record.get(amount))
            missing_codes = (888888, 999999) if year in (2001, 2003) else (8888888, 9999999)
            value = response_number(record.get(amount), missing_codes)
            value = value if value is not None and value >= 0 else None
            if year in (2012, 2015):
                names = [f"k{59 if role == 1 else 65}_{typ}_{n:02}{suffix}" for n in (1,2,3,4,5,6,7,8,88,99)]
                providers = {n: response_number(record.get(n)) for n in names}
                scope = "seleccion_multiple_por_tipo_sin_correspondencia_univoca_slot"
            else:
                providers = {institution: response_number(record.get(institution))}
                scope = "institucion_del_slot"
            if slot > 1 and raw_amount is None and response_number(record.get(start)) is None:
                if year != 2015 and all(v is None for v in providers.values()):
                    continue
                if year == 2015:
                    continue
            events.append({"rama": role, "tipo": typ, "slot": slot, "variable_recepcion": gate,
                           "variable_monto": amount, "monto_codigo_original": raw_amount,
                           "monto_mensual_observado": value, "instituciones_originales": json.dumps(providers, ensure_ascii=False),
                           "alcance_institucion": scope, "variable_inicio": start,
                           "anio_inicio_original": response_number(record.get(start)),
                           "beneficiario_viudez": typ == 2, "version": "original",
                           "imputacion_usada": False})
    return events


def partner_pointer_confirmed(individual: Mapping, household: Mapping,
                              contract: WaveContract, role: int) -> tuple[bool, str]:
    """Coteja el otro beneficiario sin invalidar la pensión propia concordante.

    Un puntero propio seleccionado concordante no resuelve automáticamente el
    puntero del otro integrante. Ausencia de pareja residente explícita se
    documenta aparte de una titularidad de pareja no comprobada.
    """
    if contract.year < 2018:
        return True, 'contexto_pareja_pregunta_historica'
    suffix = f'_{contract.year%100}'
    pair = response_number(household.get('k52a'+suffix))
    pair_ind = response_number(individual.get('k52a'+suffix))
    if pair == 1 and pair_ind == 1 and role == 1:
        return True, 'sin_pareja_residente_explicita'
    if pair != 2 or pair_ind != 2:
        return False, 'rama_pareja_no_confirmada'
    field = ('k52a_1' if role == 1 else 'k45d')+suffix
    h = response_number(household.get(field))
    i = response_number(individual.get(field))
    if h is None or i is None or h != i or h in (0,666,888,999):
        return False, 'puntero_pareja_ausente_o_discrepante'
    selected = response_number(household.get(('k45d' if role == 1 else 'k52a_1')+suffix))
    if h == selected:
        return False, 'ambas_ramas_mismo_beneficiario'
    return True, 'puntero_pareja_concordante'


def unique_events(events: Sequence[Mapping]) -> list[dict]:
    """Elimina solo réplica de un mismo slot fuente; no beneficios de igual monto.

    Una colisión con contenido distinto exige revisión; no elige arbitrariamente.
    La versión forma parte de la clave y se agrega por separado.
    """
    result = {}
    for event in events:
        key = tuple(event[k] for k in ("ano", "hogar_fuente", "fuente", "version", "rama", "tipo", "slot"))
        payload = dict(event)
        if key in result and result[key] != payload:
            raise ValueError("Mismo slot fuente con contenidos discordantes")
        result[key] = payload
    return list(result.values())
