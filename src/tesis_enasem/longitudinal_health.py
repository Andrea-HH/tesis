"""Panel descriptivo de pensiones y salud mental; sin causalidad ni imputación nueva."""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import t

from .integration import restore_stata, person_id
from .independent_eda import validate_values
from .pension_health import contracts, YEARS
from .project_paths import PROJECT_ROOT, INTERIM_DIR, PROCESSED_DIR

OUTPUT = INTERIM_DIR / "trayectorias_pensiones_salud"
ITEMS = ("deprimido", "esfuerzo", "intranquilo", "feliz", "solo", "disf_vida", "triste", "cansado", "energia")
POSITIVE = ("feliz", "disf_vida", "energia")
COMPARABLE = {
    (2001, 2003): True,
    (2003, 2012): False,
    (2012, 2015): True,
    (2015, 2018): False,
    (2018, 2021): True,
}
REASONS = {
    (2001, 2003): "Orientación 2001 del proveedor; mismas contingencias, condicionada.",
    (2003, 2012): "Categoría federal/estatal agrupada: ruptura de cobertura institucional.",
    (2012, 2015): "Recepción binaria condicionada; cambia capacidad de slots.",
    (2015, 2018): "Cambios de lista/estructura institucional y donativos: ruptura.",
    (2018, 2021): "Contingencias y estructura semejantes; no toda protección pensionaria.",
}
TRANSITIONS = ("Sí→Sí", "No→No", "No→Sí", "Sí→No")
STRATA = ("sexo_grupo", "edad_inicial", "educacion_grupo", "localidad_grupo", "patrimonio_inicial")


def load_panel() -> pd.DataFrame:
    """Lee maestro y sidecar con LEFT JOIN 1:1; conserva vivos y fallecidos."""
    specs, _, metadata = contracts()
    variables = list(dict.fromkeys([*ITEMS, "n_sint_depr", "n_enf", "n_abvd", "imp_neto"]))
    columns = [
        "id",
        "ronda",
        "mes_ent",
        "fallecido",
        *variables,
        *[metadata[v]["campo_tag"] for v in variables],
    ]
    master = pd.read_parquet(PROCESSED_DIR / "enasem_integrada_provisional.parquet", columns=columns)
    sidecar = pd.read_parquet(PROCESSED_DIR / "armonizacion_economica_v1/personas_ronda.parquet")
    if sidecar[["id", "ronda"]].duplicated().any() or master[["id", "ronda"]].duplicated().any():
        raise ValueError("Duplicados persona-ronda")
    if not sidecar.id.equals(person_id(sidecar)):
        raise ValueError("Formato ID alterado")
    frame = sidecar.merge(master, on=["id", "ronda"], how="left", validate="one_to_one", indicator=True)
    assert len(frame) == 99676 and frame.id.nunique() == 27171 and frame._merge.eq("both").all()
    frame = frame.drop(columns="_merge").sort_values(["id", "ano"]).reset_index(drop=True)
    for variable in variables:
        frame[variable], frame[variable + "__estado"] = validate_values(
            restore_stata(frame[variable], frame[metadata[variable]["campo_tag"]]), specs[variable]
        )
    frame["vivo"] = frame.tipent.isin([1, 2, 3, 4])
    frame["directa"] = frame.tipent.isin([1, 2])
    frame["universo_60"] = frame.vivo & frame.edad.ge(60)
    frame["componentes_completos"], frame["suma_nueve"] = complete_score(frame)
    frame["sintomas_principal"] = frame.n_sint_depr.where(frame.componentes_completos & frame.directa)
    assert not (
        frame.componentes_completos & frame.n_sint_depr.notna() & frame.suma_nueve.ne(frame.n_sint_depr)
    ).any()
    frame["K_estado"] = [receipt(v) for v in frame.pension_propia_k]
    frame["edad_inicial"] = (
        pd.cut(frame.edad, [59, 69, 79, np.inf], labels=["60–69", "70–79", "80+"]).astype(object).fillna("ND")
    )
    frame["edad_amplia"] = np.where(frame.edad.ge(75), "75+", "60–74")
    frame["edu_ajuste"] = (
        pd.cut(frame.educacion, [-0.01, 5, 9, np.inf], labels=["0–5", "6–9", "10+"])
        .astype(object)
        .fillna("ND")
    )
    frame["sintomas_basales"] = (
        pd.cut(frame.sintomas_principal, [-1, 0, 4, 9], labels=["0", "1–4", "5–9"])
        .astype(object)
        .fillna("ND")
    )
    frame["patrimonio_inicial"] = "ND"
    for year in YEARS:
        mask = frame.ano.eq(year) & frame.universo_60 & frame.imp_neto.notna()
        values = frame.loc[mask, "imp_neto"]
        cut = values.quantile([0.25, 0.5, 0.75]).to_numpy()
        if len(set(cut)) == 3:
            frame.loc[mask, "patrimonio_inicial"] = pd.cut(
                values, [-np.inf, *cut, np.inf], labels=["Q1", "Q2", "Q3", "Q4"]
            ).astype(object)
    return frame


def complete_score(frame: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Invierte ítems positivos y exige los nueve: faltante no equivale a cero."""
    items = frame[list(ITEMS)].where(frame[list(ITEMS)].isin([0, 1]))
    complete = items.notna().all(axis=1)
    items[list(POSITIVE)] = 1 - items[list(POSITIVE)]
    return complete, items.sum(axis=1, min_count=9)


def receipt(value: Any) -> str:
    """Estado anulable: desconocido nunca se convierte en negativa."""
    return "ND" if pd.isna(value) else "Sí" if bool(value) else "No"


def summary(values: pd.Series) -> dict:
    """Descriptivos con denominador válido, frecuencias e IC de media iid por persona."""
    x = values.dropna().astype(float)
    if x.empty:
        return {
            "N": 0,
            "media": None,
            "mediana": None,
            "DE": None,
            "q25": None,
            "q75": None,
            "ic95_inf": None,
            "ic95_sup": None,
            "frecuencias": [],
        }
    sd = float(x.std()) if len(x) > 1 else None
    half = float(t.ppf(0.975, len(x) - 1) * sd / np.sqrt(len(x))) if sd is not None else None
    return {
        "N": len(x),
        "media": float(x.mean()),
        "mediana": float(x.median()),
        "DE": sd,
        "q25": float(x.quantile(0.25)),
        "q75": float(x.quantile(0.75)),
        "ic95_inf": float(x.mean() - half) if half is not None else None,
        "ic95_sup": float(x.mean() + half) if half is not None else None,
        "frecuencias": [{"valor": float(k), "N": int(v)} for k, v in x.value_counts().sort_index().items()],
    }


def change_summary(frame: pd.DataFrame) -> dict:
    """Cambio destino-origen calculado sobre pares, nunca sobre grupos independientes."""
    z = frame.loc[frame.sintomas_principal_a.notna() & frame.sintomas_principal_b.notna()]
    delta = z.sintomas_principal_b - z.sintomas_principal_a
    result = {
        "inicio": summary(z.sintomas_principal_a),
        "final": summary(z.sintomas_principal_b),
        "cambio": summary(delta),
    }
    for name, mask in [("aumenta", delta.gt(0)), ("disminuye", delta.lt(0)), ("igual", delta.eq(0))]:
        result["N_" + name] = int(mask.sum())
        result["pct_" + name] = float(mask.mean() * 100) if len(z) else None
    return result


def build_pair(frame: pd.DataFrame, origin: int, destination: int) -> pd.DataFrame:
    """Cohorte viva 60+ en origen; destino no se filtra por edad final o salud."""
    base = frame.loc[frame.ano.eq(origin) & frame.universo_60].set_index("id")
    dest = frame.loc[frame.ano.eq(destination)].set_index("id")
    pair = base.join(dest, how="left", lsuffix="_a", rsuffix="_b", validate="one_to_one")
    pair["presente"] = pair.ano_b.notna()
    pair["vivo_destino"] = pair.tipent_b.isin([1, 2, 3, 4])
    pair["directas_ambas"] = pair.directa_a.eq(True) & pair.directa_b.eq(True)
    pair["K_conocida"] = pair.K_estado_a.ne("ND") & pair.K_estado_b.isin(["Sí", "No"]) & pair.vivo_destino
    pair["proveedor_valido"] = (
        pair.directas_ambas & pair.n_sint_depr_a.notna() & pair.n_sint_depr_b.notna() & pair.K_conocida
    )
    pair["analitica"] = (
        pair.directas_ambas
        & pair.sintomas_principal_a.notna()
        & pair.sintomas_principal_b.notna()
        & pair.K_conocida
    )
    pair["transicion"] = pair.K_estado_a + "→" + pair.K_estado_b.fillna("Ausente")
    pair["delta"] = pair.sintomas_principal_b - pair.sintomas_principal_a
    dates = (
        pair.a_o_ent_a.notna()
        & pair.a_o_ent_b.notna()
        & pair.mes_ent_a.between(1, 12)
        & pair.mes_ent_b.between(1, 12)
        & pair.vivo_destino
    )
    months = 12 * (pair.a_o_ent_b - pair.a_o_ent_a) + pair.mes_ent_b - pair.mes_ent_a
    pair["meses"] = months.where(dates & months.gt(0))
    pair["duracion_grupo"] = (
        pd.cut(
            pair.meses,
            [-np.inf, (destination - origin) * 12, np.inf],
            labels=["Hasta nominal", "Mayor a nominal"],
        )
        .astype(object)
        .fillna("ND")
    )
    pair["seguimiento"] = "Vivo fuera de análisis"
    pair.loc[pair.analitica, "seguimiento"] = "Análisis principal"
    pair.loc[pair.tipent_b.isin([3, 4]), "seguimiento"] = "Sustituto destino"
    pair.loc[pair.tipent_b.eq(5), "seguimiento"] = "Sobre fallecido"
    pair.loc[~pair.presente, "seguimiento"] = "Ausente"
    assert pair.seguimiento.value_counts().sum() == len(base)
    return pair


def transition_matrix(pair: pd.DataFrame, mask: pd.Series, variable: str = "K_estado") -> list[dict]:
    """Frecuencias, porcentajes de fila y de pares válidos con denominadores explícitos."""
    z = pair.loc[mask]
    a, b = variable + "_a", variable + "_b"
    states = ["No", "Sí"] if variable == "K_estado" else [0, 1]
    rows = []
    for origin in states:
        denominator = int(z[a].eq(origin).sum())
        for destination in states:
            n = int((z[a].eq(origin) & z[b].eq(destination)).sum())
            rows.append(
                {
                    "origen": origin,
                    "destino": destination,
                    "N": n,
                    "N_origen": denominator,
                    "N_pares": len(z),
                    "pct_fila": n / denominator * 100 if denominator else None,
                    "pct_total": n / len(z) * 100 if len(z) else None,
                }
            )
    assert sum(r["N"] for r in rows) == len(z)
    return rows


def standardized_contrast(
    pair: pd.DataFrame, group: str, reference: str, covariates: tuple[str, ...], minimum: int = 10
) -> dict:
    """Diferencia media de cambios a composición común, sin ajustar por covariables finales."""
    z = pair.loc[pair.analitica & pair.transicion.isin([group, reference])].copy()
    columns = [v + "_a" if v != "duracion_grupo" else v for v in covariates]
    valid = ~z[columns].isin(["ND", "Desconocido"]).any(axis=1) & z[columns].notna().all(axis=1)
    z = z.loc[valid]
    cells = []
    for key, cell in z.groupby(columns, observed=True, dropna=False):
        left = cell.loc[cell.transicion.eq(group), "delta"]
        right = cell.loc[cell.transicion.eq(reference), "delta"]
        if min(len(left), len(right)) < minimum:
            continue
        keys = key if isinstance(key, tuple) else (key,)
        cells.append(
            {
                "estrato": dict(zip(covariates, map(str, keys))),
                "N": len(cell),
                "N_grupo": len(left),
                "N_referencia": len(right),
                "diferencia": float(left.mean() - right.mean()),
                "varianza": float(left.var() / len(left) + right.var() / len(right)),
                "suma_grupo": float(left.sum()),
                "suma_referencia": float(right.sum()),
            }
        )
    support = sum(c["N"] for c in cells)
    total_group = sum(c["N_grupo"] for c in cells)
    total_ref = sum(c["N_referencia"] for c in cells)
    result = {
        "grupo": group,
        "referencia": reference,
        "variables": list(covariates),
        "minimo_celda": minimum,
        "N_casos_completos": len(z),
        "N_soporte": support,
        "N_fuera_soporte": len(z) - support,
        "N_total_dos_ramas": int((pair.analitica & pair.transicion.isin([group, reference])).sum()),
        "N_basales_faltantes": int((~valid).sum()),
        "N_grupo": total_group,
        "N_referencia": total_ref,
        "celdas": cells,
    }
    if min(total_group, total_ref) < 30 or not cells:
        return result | {
            "estado": "Soporte insuficiente",
            "ajustada": None,
            "cruda_mismo_soporte": None,
            "ic95_inf": None,
            "ic95_sup": None,
        }
    weights = np.array([c["N"] / support for c in cells])
    estimate = float(sum(w * c["diferencia"] for w, c in zip(weights, cells)))
    half = 1.96 * np.sqrt(sum(w * w * c["varianza"] for w, c in zip(weights, cells)))
    crude = (
        sum(c["suma_grupo"] for c in cells) / total_group
        - sum(c["suma_referencia"] for c in cells) / total_ref
    )
    return result | {
        "estado": "Descriptivo condicionado al soporte",
        "ajustada": estimate,
        "cruda_mismo_soporte": crude,
        "ic95_inf": float(estimate - half),
        "ic95_sup": float(estimate + half),
    }


def pattern(values: list[float]) -> str:
    """Clasifica valores observados; no interpola ni presume continuidad entre visitas."""
    changes = np.diff(values)
    if len(changes) == 0:
        return "Una medición"
    if np.all(changes == 0):
        return "Conteo igual en visitas"
    if np.all(changes >= 0):
        return "No decreciente observado"
    if np.all(changes <= 0):
        return "No creciente observado"
    return "Fluctuación observada"


def pension_pattern(states: list[str]) -> str:
    """Secuencia retrospectiva descriptiva, no estabilidad real de una prestación."""
    if "ND" in states:
        return "Incluye desconocidos"
    if len(set(states)) == 1:
        return "Afirmativas repetidas" if states[0] == "Sí" else "Negativas repetidas"
    changes = sum(a != b for a, b in zip(states[:-1], states[1:]))
    return "Cambio único registrado" if changes == 1 else "Múltiples cambios registrados"


def analyze_multivisit(frame: pd.DataFrame) -> dict:
    """Resume personas una vez por trayectoria; todas las clases son retrospectivas."""
    people = []
    profiles = []
    edges = []
    sequences = Counter()
    for identifier, person in frame.loc[frame.universo_60].groupby("id", sort=False):
        observed = person.sort_values("ano")
        valid = observed.loc[observed.sintomas_principal.notna()]
        joint = valid.loc[valid.K_estado.ne("ND")]
        solitude = observed.loc[observed.directa & observed.solo.notna()]
        years = observed.ano.astype(int).tolist()
        bits = "".join("1" if y in years else "0" for y in YEARS)
        sequences[bits] += 1
        row = {
            "N_visitas": len(observed),
            "N_sintomas": len(valid),
            "N_conjuntas": len(joint),
            "N_solo": len(solitude),
            "hueco_observacion": any(
                YEARS.index(b) - YEARS.index(a) > 1 for a, b in zip(years[:-1], years[1:])
            ),
            "sexo": str(observed.iloc[0].sexo_grupo),
            "edad": str(observed.iloc[0].edad_inicial),
            "educacion": str(observed.iloc[0].educacion_grupo),
        }
        if len(valid) >= 2:
            row |= {
                "patron_sintomas": pattern(valid.sintomas_principal.tolist()),
                "cambio_primera_ultima": float(
                    valid.sintomas_principal.iloc[-1] - valid.sintomas_principal.iloc[0]
                ),
            }
            for position, value in enumerate(valid.sintomas_principal):
                profiles.append(
                    {
                        "N_mediciones": len(valid),
                        "visita_valida": position + 1,
                        "ronda": int(valid.ano.iloc[position]),
                        "valor": float(value),
                    }
                )
            vyears = valid.ano.astype(int).tolist()
            values = valid.sintomas_principal.tolist()
            for a, b, va, vb in zip(vyears[:-1], vyears[1:], values[:-1], values[1:]):
                edges.append(
                    {
                        "tipo": "Consecutivas"
                        if YEARS.index(b) - YEARS.index(a) == 1
                        else "Con hueco de medición",
                        "delta": float(vb - va),
                    }
                )
        if len(solitude) >= 2:
            states = solitude.solo.astype(int).tolist()
            row["patron_solo"] = (
                "Siempre sí observado"
                if all(states)
                else "Siempre no observado"
                if not any(states)
                else "Cambia en visitas"
            )
        if len(observed) >= 2:
            row["patron_K"] = pension_pattern(observed.K_estado.tolist())
            row["atraviesa_ruptura"] = any(
                a < boundary <= b for a, b in zip(years[:-1], years[1:]) for boundary in [2012, 2018]
            )
        people.append(row)
    persons = pd.DataFrame(people)
    counts = [
        {"tipo": column, "visitas": int(k), "N_personas": int(v)}
        for column in ["N_visitas", "N_sintomas", "N_conjuntas", "N_solo"]
        for k, v in persons[column].value_counts().sort_index().items()
    ]
    joint = []
    for keys, z in persons.loc[persons.N_sintomas.ge(2) & persons.N_visitas.ge(2)].groupby(
        ["patron_K", "N_sintomas", "hueco_observacion"], dropna=False
    ):
        joint.append(
            {
                "patron_K": keys[0],
                "N_mediciones": int(keys[1]),
                "hueco_observacion": bool(keys[2]),
                "N_personas": len(z),
                "cambio_primera_ultima": summary(z.cambio_primera_ultima),
                "patrones_sintomas": z.patron_sintomas.value_counts().to_dict(),
            }
        )
    by_count = [
        {
            "N_mediciones": int(n),
            "N_personas": len(g),
            "patrones": g.patron_sintomas.value_counts().to_dict(),
            "cambio_primera_ultima": summary(g.cambio_primera_ultima),
        }
        for n, g in persons.loc[persons.N_sintomas.ge(2)].groupby("N_sintomas")
    ]
    demographic = []
    for col in ["sexo", "edad", "educacion"]:
        for key, z in persons.loc[persons.N_sintomas.ge(2)].groupby(col):
            demographic.append(
                {
                    "estratificador": col,
                    "estrato": key,
                    "N_personas": len(z),
                    "patrones": z.patron_sintomas.value_counts().to_dict(),
                    "cambio_primera_ultima": summary(z.cambio_primera_ultima),
                }
            )
    # Per-person summaries only: no pooled iid interval CI for repeated edges/profiles.
    profile = pd.DataFrame(profiles)
    grouped = [
        {
            "N_mediciones": int(n),
            "visita_valida": int(v),
            "N_personas": len(z),
            "media": float(z.valor.mean()),
            "mediana": float(z.valor.median()),
        }
        for (n, v), z in profile.groupby(["N_mediciones", "visita_valida"])
    ]
    calendar = [
        {"N_mediciones": int(n), "ronda": int(y), "N_personas": len(g), "media": float(g.valor.mean())}
        for (n, y), g in profile.groupby(["N_mediciones", "ronda"])
    ]
    edge_counts = []
    e = pd.DataFrame(edges)
    for key, z in e.groupby("tipo"):
        s = summary(z.delta)
        s["ic95_inf"] = None
        s["ic95_sup"] = None
        edge_counts.append(
            {
                "tipo": key,
                "N_pares_repetidos": len(z),
                "cambio": s,
                "nota": "Descriptivo; pares de misma persona dependientes, sin IC iid.",
            }
        )
    return {
        "N_personas_60": len(persons),
        "conteos_visitas": counts,
        "patrones_observacion": [{"patron": k, "N_personas": v} for k, v in sequences.most_common()],
        "patrones_sintomas": persons.loc[persons.N_sintomas.ge(2), "patron_sintomas"]
        .value_counts()
        .to_dict(),
        "patrones_K": persons.loc[persons.N_visitas.ge(2), "patron_K"].value_counts().to_dict(),
        "patrones_soledad": persons.loc[persons.N_solo.ge(2), "patron_solo"].value_counts().to_dict(),
        "N_con_huecos": int(persons.hueco_observacion.sum()),
        "N_trayectorias_atraviesan_ruptura": int(persons.atraviesa_ruptura.eq(True).sum()),
        "evolucion_por_mediciones": grouped,
        "evolucion_calendario_subgrupos_retrospectivos": calendar,
        "patrones_por_N_mediciones": by_count,
        "relacion_K_sintomas": joint,
        "sociodemografia": demographic,
        "pares_consecutivos_intermitentes": edge_counts,
    }


def analyze() -> dict:
    """Calcula los tres niveles sin pooling inferencial de intervalos incompatibles."""
    frame = load_panel()
    audit = []
    waves = []
    for year in YEARS:
        allwave = frame.loc[frame.ano.eq(year)]
        z = allwave.loc[allwave.universo_60]
        direct = z.loc[z.directa]
        complete = direct.componentes_completos
        partial = direct.n_sint_depr.notna() & ~complete
        components = direct[list(ITEMS)].copy()
        components[list(POSITIVE)] = 1 - components[list(POSITIVE)]
        audit.append(
            {
                "ronda": year,
                "N_directas_60": len(direct),
                "N_score_proveedor": int(direct.n_sint_depr.notna().sum()),
                "N_nueve_completos": int(complete.sum()),
                "N_score_valido_componentes_incompletos": int(partial.sum()),
                "N_discordancias_completos": int((complete & direct.n_sint_depr.ne(direct.suma_nueve)).sum()),
                "N_parciales_igual_suma_disponible": int(
                    (partial & direct.n_sint_depr.eq(components.sum(axis=1))).sum()
                ),
                "estados_score": direct.n_sint_depr__estado.value_counts().to_dict(),
                "componentes_faltantes": {v: int(direct[v].isna().sum()) for v in ITEMS},
            }
        )
        by_k = [
            {
                "estado_K": k,
                "N_rama": len(g),
                "sintomas": summary(g.sintomas_principal),
                "solo": summary(g.solo.where(g.directa)),
            }
            for k, g in z.groupby("K_estado")
        ]
        waves.append(
            {
                "ronda": year,
                "N_todas_edades_modalidades": len(allwave),
                "N_vivos_todas_edades": int(allwave.vivo.sum()),
                "N_60_vivos": len(z),
                "N_directas_60": len(direct),
                "K": z.K_estado.value_counts().to_dict(),
                "sintomas_principal": summary(direct.sintomas_principal),
                "sintomas_proveedor": summary(direct.n_sint_depr),
                "soledad": summary(direct.solo),
                "por_K": by_k,
            }
        )
    seen_dead = frame.tipent.eq(5).groupby(frame.id).cummax()
    anomaly_ids = set(frame.loc[seen_dead & frame.vivo, "id"])
    frame["antecedente_fallecido_vivo"] = frame.id.isin(anomaly_ids)
    intervals = []
    allids = []
    old = json.loads((INTERIM_DIR / "viabilidad_longitudinal/conteos.json").read_text())
    for origin, destination in zip(YEARS[:-1], YEARS[1:]):
        pair = build_pair(frame, origin, destination)
        later_ids = set(frame.loc[frame.ano.gt(destination) & frame.vivo, "id"])
        mask = pair.analitica
        analytic = pair.loc[mask]
        eligible = pair.directas_ambas & pair.vivo_destino
        healthvalid = eligible & pair.sintomas_principal_a.notna() & pair.sintomas_principal_b.notna()
        ref = next(r for r in old["pares"] if r["origen"] == origin)
        assert (
            int(pair.proveedor_valido.sum()) == ref["variables"]["n_sint_depr"]["N_valido_y_K_conocido_ambas"]
        )
        allids.extend(analytic.index)
        follow = {
            "N_origen": len(pair),
            "N_presente": int(pair.presente.sum()),
            "N_vivo_destino": int(pair.vivo_destino.sum()),
            "N_sobre_fallecido": int(pair.tipent_b.eq(5).sum()),
            "N_ausente": int((~pair.presente).sum()),
            "N_reaparece": int(sum(i in later_ids for i in pair.index[~pair.presente]))
            if destination < 2021
            else None,
            "N_directas_ambas": int(eligible.sum()),
            "N_sintomas_nueve_validos_ambas": int(healthvalid.sum()),
            "N_K_conocida_ambas_vivas": int(pair.K_conocida.sum()),
            "N_principal": int(mask.sum()),
            "N_proveedor": int(pair.proveedor_valido.sum()),
            "N_sustituto_origen": int(pair.tipent_a.isin([3, 4]).sum()),
            "N_sustituto_destino": int(pair.tipent_b.isin([3, 4]).sum()),
            "N_fallecido_reaparece": int(sum(i in later_ids for i in pair.index[pair.tipent_b.eq(5)])),
            "N_edad_destino_no60_ND": int((pair.vivo_destino & ~pair.edad_b.ge(60)).sum()),
        }
        by_transition = []
        for state in TRANSITIONS:
            group = analytic.loc[analytic.transicion.eq(state)]
            by_transition.append(
                {
                    "transicion": state,
                    "N": len(group),
                    "estado": "Estimable descriptivamente"
                    if len(group) >= 30
                    else "Solo descriptivo, N pequeño",
                    **change_summary(group),
                }
            )
        contrasts = []
        for group, reference in [("No→Sí", "No→No"), ("Sí→No", "Sí→Sí")]:
            a = analytic.loc[analytic.transicion.eq(group), "delta"]
            b = analytic.loc[analytic.transicion.eq(reference), "delta"]
            estimate = float(a.mean() - b.mean())
            half = 1.96 * np.sqrt(a.var() / len(a) + b.var() / len(b)) if min(len(a), len(b)) >= 30 else None
            contrasts.append(
                {
                    "grupo": group,
                    "referencia": reference,
                    "N_grupo": len(a),
                    "N_referencia": len(b),
                    "diferencia": estimate,
                    "ic95_inf": float(estimate - half) if half is not None else None,
                    "ic95_sup": float(estimate + half) if half is not None else None,
                }
            )
        strata = []
        for variable in STRATA:
            for (state, key), group in analytic.groupby(
                ["transicion", variable + "_a"], observed=True, dropna=False
            ):
                strata.append(
                    {
                        "transicion": state,
                        "estratificador": variable,
                        "estrato": str(key),
                        "N": len(group),
                        "cambio": summary(group.delta),
                        "estimable": len(group) >= 30,
                    }
                )
        adjusted = []
        for group, reference in [("No→Sí", "No→No"), ("Sí→No", "Sí→Sí")]:
            for name, covs in [
                ("Demográfico", ("sexo_grupo", "edad_inicial", "edu_ajuste")),
                (
                    "Basal y duración",
                    ("sexo_grupo", "edad_inicial", "edu_ajuste", "sintomas_basales", "duracion_grupo"),
                ),
            ]:
                adjusted.append(
                    {"especificacion": name, **standardized_contrast(pair, group, reference, covs)}
                )
        selection = []
        for key, g in pair.groupby("seguimiento"):
            selection.append(
                {
                    "grupo": key,
                    "N": len(g),
                    "pct_cohorte": len(g) / len(pair) * 100,
                    "edad": summary(g.edad_a),
                    "escolaridad": summary(g.educacion_a),
                    "sintomas_iniciales": summary(g.n_sint_depr_a.where(g.directa_a.eq(True))),
                    "enfermedades": summary(g.n_enf_a),
                    "ABVD": summary(g.n_abvd_a),
                    "sexo": g.sexo_grupo_a.value_counts().to_dict(),
                    "K": g.K_estado_a.value_counts().to_dict(),
                }
            )
        selection_k = []
        for state, g in pair.groupby("K_estado_a"):
            selection_k.append(
                {
                    "K_origen": state,
                    "N": len(g),
                    "seguimiento": g.seguimiento.value_counts().to_dict(),
                    "pct_principal": float(g.analitica.mean() * 100),
                    "pct_sobre_fallecido": float(g.tipent_b.eq(5).mean() * 100),
                    "pct_ausente": float((~g.presente).mean() * 100),
                }
            )
        solitude_mask = pair.directas_ambas & pair.solo_a.notna() & pair.solo_b.notna() & pair.K_conocida
        solitude = []
        for state, g in pair.loc[solitude_mask].groupby("transicion"):
            solitude.append(
                {
                    "transicion_K": state,
                    "N": len(g),
                    "matriz": transition_matrix(g, pd.Series(True, index=g.index), "solo"),
                    "cambio_pp": float((g.solo_b - g.solo_a).mean() * 100),
                    "cambio_pareado": summary(g.solo_b - g.solo_a),
                }
            )
        sensitivity = []
        provider = pair.loc[pair.proveedor_valido].copy()
        provider["sintomas_principal_a"] = provider.n_sint_depr_a
        provider["sintomas_principal_b"] = provider.n_sint_depr_b
        sensitivity.append(
            {
                "criterio": "Conteo válido del proveedor, admite componentes incompletos",
                "N": len(provider),
                **change_summary(provider),
            }
        )
        clean = analytic.loc[
            analytic.edad_b.ge(60)
            & analytic.edad_b.ge(analytic.edad_a)
            & analytic.sexo_a.eq(analytic.sexo_b)
            & ~analytic.antecedente_fallecido_vivo_a
        ]
        sensitivity.append(
            {
                "criterio": "Sin edad descendente/ND, sexo discordante ni antecedente fallecido→vivo",
                "N": len(clean),
                **change_summary(clean),
            }
        )
        for state in TRANSITIONS:
            pp = provider.loc[provider.transicion.eq(state)]
            sensitivity.append(
                {"criterio": "Proveedor por patrón " + state, "N": len(pp), **change_summary(pp)}
            )
        for minimum in [5, 20]:
            for group, reference in [("No→Sí", "No→No"), ("Sí→No", "Sí→Sí")]:
                sensitivity.append(
                    {
                        "criterio": f"Soporte >= {minimum} por rama/celda",
                        **standardized_contrast(
                            pair, group, reference, ("sexo_grupo", "edad_inicial", "edu_ajuste"), minimum
                        ),
                    }
                )
        for key, g in analytic.groupby("edad_amplia_a"):
            sensitivity.append(
                {"criterio": "Edad inicial alternativa " + key, "N": len(g), **change_summary(g)}
            )
        intervals.append(
            {
                "origen": origin,
                "destino": destination,
                "K_comparable_condicionada": COMPARABLE[origin, destination],
                "restriccion": REASONS[origin, destination],
                "seguimiento": follow,
                "duracion_vivos": summary(pair.meses),
                "duracion_analitica": summary(analytic.meses),
                "matriz_K_vivos": transition_matrix(pair, pair.K_conocida),
                "matriz_K_principal": transition_matrix(pair, mask),
                "cambios": change_summary(analytic),
                "por_transicion": by_transition,
                "contrastes_brutos": contrasts,
                "estratos": strata,
                "ajustes": adjusted,
                "seleccion": selection,
                "seleccion_K": selection_k,
                "soledad": solitude,
                "sensibilidades": sensitivity,
            }
        )
    multivisit = analyze_multivisit(frame)
    frequencies = Counter(allids)
    return {
        "metodologia": {
            "rondas": list(YEARS),
            "ponderado": False,
            "criterio_principal": "Nueve componentes CES-D válidos y directas en ambos extremos, K conocida",
            "N_pares_principales": len(allids),
            "N_personas_distintas_pares": len(frequencies),
            "N_personas_mas_un_intervalo": sum(n > 1 for n in frequencies.values()),
            "IC": "t de media del cambio por personas dentro de intervalo; normal de estandarización condicional. Sin diseño/hogar/pesos ni IC simultáneos.",
            "ajuste": "Composición conjunta en celdas basales con >=10 por rama; no causal, soporte restringido.",
            "periodos_incompatibles": "Sin estimación global que mezcle rupturas K; secuencias multirronda retrospectivas.",
        },
        "auditoria_CESD": audit,
        "rondas": waves,
        "intervalos": intervals,
        "multivisita": multivisit,
    }


def verify_inputs(allow_report: bool = False) -> None:
    """Comprueba entradas congeladas e índice sin ejecutar comandos Git."""
    manifest = json.loads((OUTPUT / "manifest.json").read_text())
    changed = [
        name
        for name, digest in manifest["protegidos"].items()
        if not (allow_report and name in ["resultados/INFORME_GENERAL.md", "resultados/INFORME_GENERAL.pdf"])
        and sha256((PROJECT_ROOT / name).read_bytes()).hexdigest() != digest
    ]
    if changed:
        raise ValueError("Archivos protegidos alterados: " + str(changed))
    assert sha256((PROJECT_ROOT / ".git/index").read_bytes()).hexdigest() == manifest["indice_sha256"]
