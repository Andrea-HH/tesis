"""Armonización descriptiva provisional de protección económica, sin modificar fuentes.

K significa las cuatro contingencias pensionarias, no toda pensión contributiva.
A significa donativos públicos adicionales, en dinero o especie. No se suman montos K+A.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Mapping

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, spearmanr

from .integration import response_number

UNKNOWN = "Desconocido"
STATES = ("Sí", "No", UNKNOWN)


@dataclass(frozen=True)
class SupportContract:
    """Preguntas originales; la periodicidad almacenada no es frecuencia de entrega legal."""

    year: int
    own_gate: str
    spouse_gate: str
    own_amounts: tuple[str, ...]
    spouse_amounts: tuple[str, ...]
    own_programs: tuple[str, ...]
    spouse_programs: tuple[str, ...]
    missing_amount: tuple[int, int]
    program_labels: Mapping[int, str]
    specificity: str


def support_contract(year: int) -> SupportContract:
    """No extrapola el nombre de una variable ni programa a otra ronda."""
    if year == 2001:
        return SupportContract(year, "k76a", "k79a", ("k77_1",), ("k80_1",), (), (),
                               (888888, 999999), {}, "Donativo público agregado, sin nombre observado")
    if year == 2003:
        return SupportContract(year, "k79a", "k82c", ("k80a",), ("k83c",), (), (),
                               (888888, 999999), {}, "Donativo público agregado, sin nombre observado")
    s = f"_{year % 100}"
    if year in (2012, 2015):
        return SupportContract(year, "k79a"+s, "k82c"+s, ("k80_1"+s,), ("k83_1"+s,), (), (),
                               (8888888, 9999999), {}, "Donativo público agregado, sin nombre observado")
    labels = {1: "PROAGRO Productivo", 2: "PROSPERA", 3: "INAPAM", 4: "Otra institución: tipo no resuelto"}
    if year == 2021:
        labels = {1: "Producción para el Bienestar", 2: "Becas para el Bienestar Benito Juárez",
                  3: "INAPAM", 4: "Otra institución: tipo no resuelto",
                  5: "Programa para el Bienestar de las Personas Adultas Mayores"}
    return SupportContract(year, "k79a"+s, "k82c"+s,
                           tuple(f"k80_1_{i}"+s for i in (1, 2)),
                           tuple(f"k83_1_{i}"+s for i in (1, 2)),
                           tuple(f"k79a_1_{i}"+s for i in (1, 2)),
                           tuple(f"k82c_1_{i}"+s for i in (1, 2)),
                           (8888888, 9999999), labels, "Hasta dos instituciones; dinero o especie sin separación")


def binary_receipt(value: object) -> bool | None:
    """NR/NS y cualquier respuesta ajena al dominio 1/2 quedan desconocidos."""
    v = response_number(value)
    return True if v == 1 else False if v == 2 else None


def receipt_state(value: object) -> str:
    """Boolean anulable a categoría; desconocido no equivale a negativa."""
    return UNKNOWN if value is None or pd.isna(value) else "Sí" if bool(value) else "No"


def support_events(record: Mapping, contract: SupportContract, role: int) -> list[dict]:
    """Conserva cada donativo y su monto nominal mensual, sin imputar ni sumar versiones."""
    gate = contract.own_gate if role == 1 else contract.spouse_gate
    if binary_receipt(record.get(gate)) is not True:
        return []
    amounts = contract.own_amounts if role == 1 else contract.spouse_amounts
    programs = contract.own_programs if role == 1 else contract.spouse_programs
    output = []
    for idx, amount in enumerate(amounts):
        program_field = programs[idx] if programs else None
        raw_program = response_number(record.get(program_field)) if program_field else None
        raw_amount = response_number(record.get(amount))
        if idx and raw_program is None and raw_amount is None:
            continue
        value = response_number(record.get(amount), contract.missing_amount)
        if value is not None and value < 0:
            value = None
        known_program = raw_program in contract.program_labels
        category = ("Vejez no contributiva identificada" if contract.year == 2021 and raw_program == 5 else
                    "Otro apoyo público identificado" if known_program and raw_program in (1, 2) else
                    "Institución de servicios: beneficio no tipificado" if known_program and raw_program == 3 else
                    "Apoyo público sin tipo comprobado")
        output.append({"rama": role, "slot": idx+1, "bloque": "A", "version": "original",
                       "variable_recepcion": gate, "variable_monto": amount,
                       "monto_codigo_original": raw_amount, "monto_mensual_observado": value,
                       "programa_codigo_original": raw_program,
                       "programa": contract.program_labels.get(raw_program, "Programa no identificado"),
                       "tipo_documental": category, "dinero_especie": "No separable",
                       "periodicidad": "Mes normal; no frecuencia normativa de pago"})
    return output


def pension_institution_evidence(event: Mapping) -> dict:
    """Institución del receptor, sin confundir institución pública y contribución.

    IMSS/ISSSTE acreditan familia de seguridad social (incluye derecho derivado).
    Una selección múltiple por tipo no autoriza repartir el monto entre instituciones.
    """
    import json
    institutions = json.loads(event["instituciones_originales"])
    if "seleccion_multiple" in event["alcance_institucion"]:
        codes = [int(k.split("_")[-2]) for k, v in institutions.items() if v == 1]
    else:
        missing = (8, 9) if event.get("ano", 2021) in (2001, 2003) else (88, 99)
        codes = [int(v) for v in institutions.values() if v is not None and v not in missing]
    return {"instituciones_codigos": codes, "seguridad_social_identificada": bool(set(codes) & {1, 2}),
            "programa_publico_agrupado": 8 in codes,
            "institucion_sin_tipo_comprobado": not codes or bool(set(codes) - {1, 2, 8}),
            "alcance_evidencia_institucion": "Contingencia completa; no asignable a slot" if
            "seleccion_multiple" in event["alcance_institucion"] else "Institución del slot",
            "monto_separable_por_institucion": "seleccion_multiple" not in event["alcance_institucion"]}


def add_profiles(frame: pd.DataFrame) -> pd.DataFrame:
    """Controles de ENASEMsimple: educación en primera entrevista, localidad a 100 mil."""
    result = frame.copy()
    result["sexo_grupo"] = result.sexo.map({1: "Hombre", 2: "Mujer"}).fillna(UNKNOWN)
    result["localidad_grupo"] = result.urbano.map({0: "<100 mil habitantes", 1: "≥100 mil habitantes"}).fillna(UNKNOWN)
    result["educacion_grupo"] = pd.cut(result.educacion.where(result.educacion.ge(0)),
        [-.5, .5, 5.5, 6.5, 9.5, np.inf], labels=["0 años", "1–5 años", "6 años", "7–9 años", "≥10 años"])
    result["educacion_grupo"] = result.educacion_grupo.astype(object).fillna(UNKNOWN)
    result["edad_grupo"] = pd.cut(result.edad, [59, 69, 79, 89, np.inf], labels=["60–69", "70–79", "80–89", "≥90"])
    result["edad_grupo"] = result.edad_grupo.astype(object).fillna(UNKNOWN)
    return result


def joint_category(pension: object, support: object) -> str:
    """Partición exhaustiva; apoyo con pensión desconocida no se vuelve apoyo exclusivo."""
    p, a = receipt_state(pension), receipt_state(support)
    return {("Sí", "Sí"): "Pensión K y apoyo", ("Sí", "No"): "Solo pensión K observada",
            ("No", "Sí"): "Apoyo y negativa propia K", ("No", "No"): "Negativas explícitas K y A",
            (UNKNOWN, "Sí"): "Apoyo con pensión desconocida"}.get((p, a), "Otra situación desconocida")


def protection_crosstab(frame: pd.DataFrame, groups: list[str]) -> list[dict]:
    """Conteos incluyendo ceros/desconocidos; tasas en estrato vs composición de receptores."""
    records = []
    data = frame.copy()
    for v in ("pension_propia_k", "apoyo_propio"):
        data[v+"_estado"] = data[v].map(receipt_state)
    grouped = [((), data)] if not groups else data.groupby(groups, dropna=False, observed=True)
    total_receivers = int(data.apoyo_propio.eq(True).sum())
    for levels, part in grouped:
        levels = levels if isinstance(levels, tuple) else (levels,)
        label = dict(zip(groups, levels))
        pknown = part.pension_propia_k.notna()
        aknown = part.apoyo_propio.notna()
        known = pknown & aknown
        for p, a in product(STATES, repeat=2):
            n = int((part.pension_propia_k_estado.eq(p) & part.apoyo_propio_estado.eq(a)).sum())
            records.append({**label, "pension": p, "apoyo": a, "N": n, "N_estrato": len(part),
                "N_elegible_vivo": int(part.tipent.ne(5).sum()), "N_par_conocido": int(known.sum()),
                "N_par_desconocido": int((~known).sum()), "pct_estrato": 100*n/len(part) if len(part) else None,
                "pct_par_conocido": 100*n/known.sum() if p != UNKNOWN and a != UNKNOWN and known.any() else None,
                "pct_composicion_apoyados": 100*n/total_receivers if a == "Sí" and total_receivers else None})
    return records


def reception_rates(frame: pd.DataFrame, groups: list[str]) -> list[dict]:
    """La tasa entre respuestas conocidas se distingue del mínimo observado entre elegibles."""
    output = []
    grouped = [((), frame)] if not groups else frame.groupby(groups, dropna=False, observed=True)
    for levels, part in grouped:
        levels = levels if isinstance(levels, tuple) else (levels,)
        for v in ("pension_propia_k", "pension_conyuge_k", "apoyo_propio", "apoyo_conyuge"):
            yes, no, nd = int(part[v].eq(True).sum()), int(part[v].eq(False).sum()), int(part[v].isna().sum())
            eligible = int(part.tipent.ne(5).sum())
            output.append({**dict(zip(groups, levels)), "variable": v, "N_total": len(part),
                "N_elegible_vivo": eligible, "N_si": yes, "N_no": no, "N_desconocido": nd,
                "N_conocido": yes+no, "pct_si_total": 100*yes/len(part) if len(part) else None,
                "pct_si_elegible": 100*yes/eligible if eligible else None,
                "pct_si_conocido": 100*yes/(yes+no) if yes+no else None,
                "pct_cobertura_elegible": 100*(yes+no)/eligible if eligible else None})
    return output


def categorical_association(frame: pd.DataFrame, x: str, y: str) -> dict:
    """V de Cramér descriptiva dentro de ronda: excluye desconocidos, sin p poblacional."""
    data = frame[[x, y]].dropna()
    data = data.loc[~data.eq(UNKNOWN).any(axis=1)]
    table = pd.crosstab(data[x], data[y])
    if min(table.shape, default=0) < 2:
        return {"N_validos": len(data), "N_excluidos": len(frame)-len(data), "V_cramer": None,
                "N_celdas_esperadas_menor5": None}
    chi, _, _, expected = chi2_contingency(table, correction=False)
    v = np.sqrt(chi/(len(data)*min(table.shape[0]-1, table.shape[1]-1)))
    return {"N_validos": len(data), "N_excluidos": len(frame)-len(data), "V_cramer": float(v),
            "N_celdas_esperadas_menor5": int((expected < 5).sum())}


def support_pension_gap(frame: pd.DataFrame) -> dict:
    """Apoyo entre negativas K frente a receptoras K; no mide impacto o ampliación causal."""
    rates = []
    for state in (False, True):
        part = frame.loc[frame.pension_propia_k.eq(state).fillna(False)]
        known = part.apoyo_propio.notna()
        yes = int(part.apoyo_propio.eq(True).sum())
        rates.append({"pension": "Sí" if state else "No", "N_pension_estado": len(part),
            "N_apoyo_conocido": int(known.sum()), "N_apoyo_si": yes,
            "pct_apoyo_conocido": 100*yes/known.sum() if known.any() else None})
    return {"grupos": rates, "diferencia_pp_no_menos_si":
            rates[0]["pct_apoyo_conocido"]-rates[1]["pct_apoyo_conocido"] if
            all(r["pct_apoyo_conocido"] is not None for r in rates) else None}


def numeric_association(frame: pd.DataFrame, x: str, receipt: str) -> dict:
    """Spearman ordinal/continua contra recepción binaria, solo pares conocidos."""
    part = frame[[x, receipt]].dropna()
    estimable = len(part) >= 3 and part[x].nunique() > 1 and part[receipt].nunique() > 1
    return {"N_validos": len(part), "N_excluidos": len(frame)-len(part),
            "rho_spearman": float(spearmanr(part[x].astype(float), part[receipt].astype(float)).statistic)
            if estimable else None}


def longitudinal_transitions(frame: pd.DataFrame, year_a: int, year_b: int,
                             variable: str, comparable: bool) -> list[dict]:
    """Cohorte de 60+ viva en origen; ausente no equivale a muerte ni pérdida de prestación."""
    start = frame.loc[frame.ano.eq(year_a) & frame.edad.ge(60) & frame.tipent.ne(5)].copy()
    end = frame.loc[frame.ano.eq(year_b)].set_index("id")
    later_ids = set(frame.loc[frame.ano.gt(year_b), "id"])
    rows = []
    for a in start.to_dict("records"):
        origin = receipt_state(a[variable])
        if a["id"] not in end.index:
            destination = "Ausente con reaparición posterior" if a["id"] in later_ids else "Ausente sin reaparición observada"
        else:
            b = end.loc[a["id"]]
            if b.tipent == 5:
                destination = "Sobre fallecido"
            elif pd.isna(b.edad) or b.edad < 60:
                destination = "Edad final no elegible o desconocida"
            else:
                destination = receipt_state(b[variable])
        event = "No interpretable como transición comparable"
        if comparable and origin != UNKNOWN and destination in ("Sí", "No"):
            event = {("No", "Sí"): "Inicio observado", ("Sí", "Sí"): "Continuidad observada",
                     ("Sí", "No"): "Pérdida de recepción observada", ("No", "No"): "Negativas continuas"}[(origin, destination)]
        rows.append({"origen": origin, "destino": destination, "interpretacion": event})
    counts = pd.DataFrame(rows).value_counts(sort=False).reset_index(name="N") if rows else pd.DataFrame()
    return [{"ano_origen": year_a, "ano_destino": year_b, "intervalo_nominal_anos": year_b-year_a,
             "variable": variable, "comparabilidad_condicionada": comparable, **r,
             "N_cohorte_origen": len(start), "pct_cohorte": 100*r["N"]/len(start)} for r in counts.to_dict("records")]
