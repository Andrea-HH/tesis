"""Mortalidad registrada y selección multidimensional; sin fechas de evento inventadas."""

from __future__ import annotations
from hashlib import sha256
import json
import numpy as np
import pandas as pd
from statsmodels.stats.proportion import confint_proportions_2indep
from .longitudinal_health import load_panel, build_pair, summary, YEARS, COMPARABLE
from .pension_health import contracts
from .integration import restore_stata
from .independent_eda import validate_values
from .project_paths import PROJECT_ROOT, PROCESSED_DIR, INTERIM_DIR

OUTPUT = INTERIM_DIR / "pensiones_mortalidad_seleccion"
DIMENSIONS = {
    "Física": ["salud_glob", "diabetes", "n_enf", "bmi_imp"],
    "Mental": ["n_sint_depr", "solo"],
    "Cognición": ["recuerdo1", "recuerdo2", "orientacion", "serial7"],
    "Funcionalidad": ["n_abvd", "n_aivd", "n_mov"],
    "Económica": ["imp_neto", "ocupacion", "est_conyugal"],
}
VARIABLES = [v for names in DIMENSIONS.values() for v in names]
CATEGORICAL = {"ocupacion", "est_conyugal"}
FLAGS = {
    "recuerdo1": "recuerdo1_flag",
    "recuerdo2": "recuerdo2_flag",
    "orientacion": "orientacion_flag",
    "bmi_imp": "bmi_flag",
}


def stats(values: pd.Series) -> dict:
    """Resumen agregado; no serializa filas personales ni frecuencias monetarias individuales."""
    x = summary(values)
    x.pop("frecuencias", None)
    return x


def load_selection_panel() -> tuple[pd.DataFrame, dict]:
    """Amplía lookup del panel existente con contratos y flags; sin modificar fuentes."""
    f = load_panel()
    specs, u, meta = contracts()
    extra = [v for v in VARIABLES if v not in f.columns]
    flags = list(FLAGS.values())
    master = pd.read_parquet(
        PROCESSED_DIR / "enasem_integrada_provisional.parquet",
        columns=[
            "id",
            "ronda",
            *extra,
            *[meta[v]["campo_tag"] for v in extra],
            *flags,
            *[meta[v]["campo_tag"] for v in flags],
        ],
    )
    f = f.merge(master, on=["id", "ronda"], how="left", validate="one_to_one")
    for v in extra + flags:
        f[v], f[v + "__estado"] = validate_values(restore_stata(f[v], f[meta[v]["campo_tag"]]), specs[v])
    for variable, flag in FLAGS.items():
        f.loc[f[variable].notna() & ~f[flag].isin([0,1]),variable+"__estado"]="Válido; bandera de imputación desconocida"
        f.loc[f[variable].notna() & f[flag].eq(1), variable + "__estado"] = "Válido imputado según bandera"
        f.loc[f[variable].notna() & f[flag].eq(0), variable + "__estado"] = "Válido no imputado según bandera"
    f.loc[f.serial7.notna(), "serial7__estado"] = "Válido representado; sin bandera individual verificada"
    f["n_sint_depr"] = f.sintomas_principal
    f.loc[f.n_sint_depr.isna() & f.n_sint_depr__estado.eq("válido observado"), "n_sint_depr__estado"] = (
        "Componentes CES-D incompletos"
    )
    for v in VARIABLES:
        f[v + "__elegible"] = [t in u[v][str(y)]["modalidades"] for t, y in zip(f.tipent, f.ano)]
    seen_dead = f.tipent.eq(5).groupby(f.id).cummax()
    anomalous = set(f.loc[seen_dead & f.vivo, "id"])
    f["inconsistente_vital"] = f.id.isin(anomalous)
    assert len(f) == 99676 and f.id.nunique() == 27171 and not f[["id", "ronda"]].duplicated().any()
    return f.copy(), u


def vital_state(pair: pd.DataFrame) -> pd.Series:
    """Clasifica evidencia registrada; ausente jamás implica vivo o muerto."""
    state = pd.Series("No clasificable", index=pair.index)
    state.loc[~pair.presente] = "Ausente, vital desconocido"
    state.loc[pair.tipent_b.isin([1, 2])] = "Vivo directo"
    state.loc[pair.tipent_b.isin([3, 4])] = "Vivo sustituto"
    state.loc[pair.tipent_b.eq(5)] = "Sobre fallecido registrado"
    return state


def death_bounds(deaths: int, unknown: int, total: int) -> dict:
    """Límites lógicos condicionados a registros correctos y solo incertidumbre de ausentes."""
    if not 0 <= deaths <= deaths + unknown <= total:
        raise ValueError("Estados o denominador incoherentes")
    return {
        "N": total,
        "D": deaths,
        "U": unknown,
        "registrado_pct": deaths / total * 100 if total else None,
        "limite_inf_pct": deaths / total * 100 if total else None,
        "limite_sup_pct": (deaths + unknown) / total * 100 if total else None,
    }


def standardize_binary(
    frame: pd.DataFrame, exposure: str, outcome: str, covariates: list[str], minimum: int = 20
) -> dict:
    """Diferencia de proporciones a composición común; objetivo: registro del evento, no supervivencia."""
    z = frame.loc[frame[exposure].notna() & frame[outcome].notna()].copy()
    n_total = len(z)
    complete = z[covariates].notna().all(axis=1) & ~z[covariates].isin(["ND", "Desconocido"]).any(axis=1)
    z = z.loc[complete]
    cells = []
    for key, g in z.groupby(covariates, observed=True, dropna=False):
        yes = g.loc[g[exposure].eq(True), outcome].astype(float)
        no = g.loc[g[exposure].eq(False), outcome].astype(float)
        if min(len(yes), len(no)) < minimum:
            continue
        key = key if isinstance(key, tuple) else (key,)
        cells.append(
            {
                "estrato": dict(zip(covariates, map(str, key))),
                "N": len(g),
                "N_si": len(yes),
                "N_no": len(no),
                "media_si": float(yes.mean()),
                "media_no": float(no.mean()),
                "varianza": float(yes.var() / len(yes) + no.var() / len(no)),
            }
        )
    support = sum(c["N"] for c in cells)
    ns = sum(c["N_si"] for c in cells)
    nn = sum(c["N_no"] for c in cells)
    base = {
        "variables": covariates,
        "N_total": n_total,
        "N_basales_completos": len(z),
        "N_basales_faltantes": n_total - len(z),
        "N_soporte": support,
        "N_fuera_soporte": len(z) - support,
        "N_si": ns,
        "N_no": nn,
        "minimo_celda": minimum,
        "celdas": cells,
    }
    if min(ns, nn) < 30:
        return base | {
            "cruda_mismo_soporte_pp": None,
            "ajustada_pp": None,
            "IC_inf_pp": None,
            "IC_sup_pp": None,
            "estado": "Soporte insuficiente",
        }
    weights = np.array([c["N"] / support for c in cells])
    delta = sum(w * (c["media_si"] - c["media_no"]) for w, c in zip(weights, cells)) * 100
    half = 1.96 * np.sqrt(sum(w * w * c["varianza"] for w, c in zip(weights, cells))) * 100
    crude = (
        sum(c["N_si"] * c["media_si"] for c in cells) / ns
        - sum(c["N_no"] * c["media_no"] for c in cells) / nn
    ) * 100
    return base | {
        "cruda_mismo_soporte_pp": crude,
        "ajustada_pp": delta,
        "IC_inf_pp": delta - half,
        "IC_sup_pp": delta + half,
        "estado": "Descriptivo condicionado a soporte",
    }


def baseline_groups(pair: pd.DataFrame, variable: str) -> pd.Series:
    """Categorías basales seleccionadas con significado documentado; sin índice nuevo."""
    x = pair[variable + "_a"]
    if variable == "diabetes":
        return x.map({0: "No", 1: "Sí"}).fillna("ND")
    cuts = {
        "salud_glob": ([0, 3, 5], ["Excelente/muy buena/buena", "Regular/mala"]),
        "n_enf": ([-1, 0, 1, 7], ["0", "1", "2+"]),
        "bmi_imp": ([-np.inf, 18.5, 25, 30, np.inf], ["<18.5", "18.5–<25", "25–<30", "30+"]),
        "n_sint_depr": ([-1, 0, 4, 9], ["0", "1–4", "5–9"]),
        "n_abvd": ([-1, 0, 5], ["0", "1+"]),
        "n_aivd": ([-1, 0, 4], ["0", "1+"]),
        "n_mov": ([-1, 0, 5], ["0", "1+"]),
    }
    if variable in cuts:
        edges, labels = cuts[variable]
        return (
            pd.cut(x, edges, labels=labels, right=variable != "bmi_imp", include_lowest=True)
            .astype(object)
            .fillna("ND")
        )
    if variable == "imp_neto":
        return pair.patrimonio_inicial_a
    if variable in CATEGORICAL or variable == "solo":
        return (
            pd.cut(x, [-0.01, 2, 4, 8], labels=["0–2", ">2–4", ">4"]).astype(object).fillna("ND")
            if variable in ["recuerdo1", "recuerdo2"]
            else x.astype(object).where(x.notna(), "ND")
        )
    return (
        pd.cut(x, [-0.01, 2, 4, 8], labels=["0–2", ">2–4", ">4"]).astype(object).fillna("ND")
        if variable in ["recuerdo1", "recuerdo2"]
        else x.astype(object).where(x.notna(), "ND")
    )


def indicator_selection(
    pair: pd.DataFrame, variable: str, instrument_available: bool = True
) -> tuple[dict, pd.Series, pd.Series]:
    """Cohorte y subuniverso basal; muerte/modalidad/instrumento/valor conservan denominadores distintos."""
    base = pair[variable + "__elegible_a"].eq(True)
    valid_a = base & pair[variable + "_a"].notna()
    eligible_b = pair[variable + "__elegible_b"].eq(True) & pair.vivo_destino
    valid_b = eligible_b & pair[variable + "_b"].notna()
    paired = valid_a & valid_b
    groups = pair["estado_vital"].copy()
    groups.loc[pair.vivo_destino & ~eligible_b] = (
        "Vivo, modalidad no elegible" if instrument_available else "Vivo, instrumento no disponible"
    )
    groups.loc[eligible_b & pair[variable + "_b"].isna()] = "Vivo elegible, medición inválida/incompleta"
    groups.loc[valid_b & ~valid_a] = "Vivo válido destino, sin medición basal válida"
    groups.loc[paired] = "Par válido de indicador"
    counts = groups.value_counts().to_dict()
    assert sum(counts.values()) == len(pair)
    among_base = {
        "N_elegible_origen": int(base.sum()),
        "N_valido_origen": int(valid_a.sum()),
        "N_presente_entre_elegibles": int((base & pair.presente).sum()),
        "N_sobre_fallecido_entre_elegibles": int((base & pair.tipent_b.eq(5)).sum()),
        "N_ausente_entre_elegibles": int((base & ~pair.presente).sum()),
        "N_sustituto_destino_entre_elegibles": int((base & pair.tipent_b.isin([3, 4])).sum()),
        "N_elegible_ambas": int((base & eligible_b).sum()),
        "N_valido_ambas": int(paired.sum()),
        "N_valido_ambas_K": int((paired & pair.K_conocida).sum()),
        "N_valido_origen_muerte": int((valid_a & pair.tipent_b.eq(5)).sum()),
        "N_valido_origen_ausente": int((valid_a & ~pair.presente).sum()),
        "N_valido_origen_vivo_no_medicion": int((valid_a & pair.vivo_destino & ~valid_b).sum()),
        "estados_seleccion_cohorte": counts,
    }
    if variable in FLAGS:
        measured = paired & pair[FLAGS[variable] + "_a"].eq(0) & pair[FLAGS[variable] + "_b"].eq(0)
        among_base["N_no_imputado_ambas"] = int(measured.sum())
    return among_base, paired, groups


def analyze() -> dict:
    """Integra mortalidad registrada, selección por dimensión y sensibilidad sin nuevos modelos."""
    f, u = load_selection_panel()
    old = json.loads((INTERIM_DIR / "trayectorias_pensiones_salud/resultados.json").read_text())
    old03 = json.loads((INTERIM_DIR / "pensiones_salud/resultados.json").read_text())
    results = {
        "auditoria": {
            "N_maestro": len(f),
            "N_personas": f.id.nunique(),
            "N_fallecido_tipent5_discordante": int((f.fallecido.eq(1) != f.tipent.eq(5)).sum()),
            "N_ids_fallecido_luego_vivo": int(f.loc[f.inconsistente_vital, "id"].nunique()),
            "Master_followup_local": "No identificado entre las fuentes actuales; SimpleMHAS no sustituye archivo completo de no entrevista.",
            "fechas_defuncion": "No verificadas; no KM/Cox ni tiempos de evento imputados.",
            "IPW": "No implementada: vital desconocido entre ausentes y elegibilidad estructural/directa; sin estimar pesos/ESS/balance.",
        },
        "rondas": [],
        "intervalos": [],
        "multivisita": [],
        "reconciliacion": {},
        "antecedentes04": old["metodologia"],
        "antecedentes03": old03["metodologia"],
    }
    for year in YEARS:
        z = f.loc[f.ano.eq(year) & f.universo_60]
        row = {"ronda": year, "N_vivo_60": len(z), "indicadores": []}
        for dim, variables in DIMENSIONS.items():
            for v in variables:
                eligible = z[v + "__elegible"]
                valid = eligible & z[v].notna()
                row["indicadores"].append(
                    {
                        "variable": v,
                        "dimension": dim,
                        "N_elegible": int(eligible.sum()),
                        "N_valido": int(valid.sum()),
                        "estadisticas": stats(z.loc[valid, v]) if v not in CATEGORICAL else None,
                        "categorias": z.loc[valid, v].value_counts().to_dict() if v in CATEGORICAL else None,
                        "estados": z.loc[eligible, v + "__estado"].value_counts().to_dict(),
                    }
                )
        past = f.loc[f.ano.lt(year) & f.vivo]
        past_ids = set(past.id)
        past_60 = set(past.loc[past.edad.ge(60), "id"])
        past_under = set(past.loc[past.edad.lt(60), "id"])
        ids = set(z.id)
        row["entrada_60"] = {
            "primera_visita_viva_observada_ya60": len(ids - past_ids),
            "ingreso60_con_antecedente_menor60": len((ids & past_under) - past_60),
            "edad_previa_desconocida": len((ids & past_ids) - past_60 - past_under),
            "ya_observado60": len(ids & past_60),
        }
        assert sum(row["entrada_60"].values()) == len(z)
        results["rondas"].append(row)
    pair_ids = {v: set() for v in VARIABLES}
    kpair_ids = {v: set() for v in VARIABLES}
    all_origin_ids = []
    for origin, destination in zip(YEARS[:-1], YEARS[1:]):
        p = build_pair(f, origin, destination)
        all_origin_ids.extend(p.index)
        p["estado_vital"] = vital_state(p)
        p["D_reg"] = p.tipent_b.eq(5).astype(float)
        ref = next(z for z in old["intervalos"] if z["origen"] == origin)
        assert (
            len(p) == ref["seguimiento"]["N_origen"]
            and int(p.analitica.sum()) == ref["seguimiento"]["N_principal"]
        )
        mortal = []
        for key, g in p.groupby("K_estado_a"):
            mortal.append(
                {
                    "K_inicial": key,
                    **death_bounds(int(g.D_reg.sum()), int((~g.presente).sum()), len(g)),
                    "vivo_directo": int(g.tipent_b.isin([1, 2]).sum()),
                    "vivo_sustituto": int(g.tipent_b.isin([3, 4]).sum()),
                }
            )
        yes = p.loc[p.K_estado_a.eq("Sí")]
        no = p.loc[p.K_estado_a.eq("No")]
        lo, hi = confint_proportions_2indep(
            int(yes.D_reg.sum()), len(yes), int(no.D_reg.sum()), len(no), method="newcomb", compare="diff"
        )
        contrast = {
            "diferencia_registrada_pp": (yes.D_reg.mean() - no.D_reg.mean()) * 100,
            "IC_inf_pp": float(lo * 100),
            "IC_sup_pp": float(hi * 100),
            "N_si": len(yes),
            "N_no": len(no),
            "nota": "Evento de registro tipent5 / cohorte; no riesgo completo de muerte, sin diseño/hogar.",
        }
        specs = [
            ("Demográfico", ["sexo_grupo_a", "edad_inicial_a", "edu_ajuste_a"]),
            ("Más patrimonio", ["sexo_grupo_a", "edad_inicial_a", "edu_ajuste_a", "patrimonio_inicial_a"]),
        ]
        p["enfermedades_grupo"] = baseline_groups(p, "n_enf")
        p["CESD_grupo"] = baseline_groups(p, "n_sint_depr")
        p["ABVD_grupo"] = baseline_groups(p, "n_abvd")
        p["memoria_grupo"] = (
            pd.cut(p.recuerdo1_a, [-0.01, 4, 6, 8], labels=["0–4", ">4–6", ">6–8"])
            .astype(object)
            .fillna("ND")
        )
        for label, var in [
            ("Más enfermedades", "enfermedades_grupo"),
            ("Más CES-D", "CESD_grupo"),
            ("Más ABVD", "ABVD_grupo"),
            ("Más aprendizaje", "memoria_grupo"),
        ]:
            specs.append((label, ["sexo_grupo_a", "edad_inicial_a", "edu_ajuste_a", var]))
        adjusted = [
            {"especificacion": label, **standardize_binary(p, "pension_propia_k_a", "D_reg", cov)}
            for label, cov in specs
        ]
        adjusted_profiles = []
        for variable, threshold, reverse in [
            ("n_enf", 1, False),
            ("n_sint_depr", 4, False),
            ("n_abvd", 0, False),
            ("recuerdo1", 4, True),
        ]:
            values = p[variable + "_a"].where(p[variable + "__elegible_a"].eq(True))
            exposure = values.le(threshold) if reverse else values.gt(threshold)
            p["perfil_binario"] = exposure.astype(object).where(values.notna())
            adjusted_profiles.append(
                {
                    "variable": variable,
                    "contraste": f"<= {threshold} frente a > {threshold}"
                    if reverse
                    else f"> {threshold} frente a <= {threshold}",
                    **standardize_binary(
                        p, "perfil_binario", "D_reg", ["sexo_grupo_a", "edad_inicial_a", "edu_ajuste_a"]
                    ),
                }
            )
        profiles = []
        profile_vars = [
            "edad_inicial_a",
            "sexo_grupo_a",
            "educacion_grupo_a",
            "patrimonio_inicial_a",
            "enfermedades_grupo",
            "CESD_grupo",
            "ABVD_grupo",
            "memoria_grupo",
        ]
        for v in [
            "salud_glob",
            "diabetes",
            "bmi_imp",
            "solo",
            "recuerdo2",
            "orientacion",
            "serial7",
            "n_aivd",
            "n_mov",
            "ocupacion",
            "est_conyugal",
        ]:
            p["perfil_" + v] = baseline_groups(p, v)
            profile_vars.append("perfil_" + v)
        for variable in profile_vars:
            for key, g in p.groupby(variable, observed=True, dropna=False):
                profiles.append(
                    {
                        "variable_basal": variable,
                        "estrato": str(key),
                        **death_bounds(int(g.D_reg.sum()), int((~g.presente).sum()), len(g)),
                        "N_K_si": int(g.K_estado_a.eq("Sí").sum()),
                    }
                )
        indicators = []
        for dim, variables in DIMENSIONS.items():
            for v in variables:
                selection, paired, groups = indicator_selection(
                    p, v, bool(u[v][str(destination)]["modalidades"])
                )
                pair_ids[v].update(p.index[paired])
                kpair_ids[v].update(p.index[paired & p.K_conocida])
                source = p.loc[p[v + "__elegible_a"].eq(True) & p[v + "_a"].notna()]
                changes = None
                if (
                    v not in CATEGORICAL
                    and v != "imp_neto"
                    and paired.any()
                    and not (v == "serial7" and destination == 2021)
                ):
                    z = p.loc[paired]
                    delta = z[v + "_b"] - z[v + "_a"]
                    changes = {
                        "N": len(z),
                        "inicio": stats(z[v + "_a"]),
                        "final": stats(z[v + "_b"]),
                        "delta": stats(delta),
                        "pct_mayor": float(delta.gt(0).mean() * 100) if len(z) else None,
                        "pct_menor": float(delta.lt(0).mean() * 100) if len(z) else None,
                    }
                composition = []
                if v not in CATEGORICAL and v != "imp_neto":
                    cells = []
                    for key, g in p.loc[p[v + "__elegible_a"].eq(True) & p[v + "_a"].notna()].groupby(
                        ["sexo_grupo_a", "edad_inicial_a", "edu_ajuste_a"], observed=True
                    ):
                        retained = g.loc[paired.reindex(g.index)]
                        if len(retained) < 20:
                            continue
                        cells.append(
                            {
                                "N_basal": len(g),
                                "N_retenido": len(retained),
                                "media_basal": float(g[v + "_a"].mean()),
                                "media_retenida": float(retained[v + "_a"].mean()),
                            }
                        )
                    n_target = sum(c["N_basal"] for c in cells)
                    n_ret = sum(c["N_retenido"] for c in cells)
                    if n_target and n_ret:
                        composition = {
                            "N_target": n_target,
                            "N_retenido": n_ret,
                            "N_basal_fuera_soporte": len(source) - n_target,
                            "media_basal_target": sum(c["N_basal"] * c["media_basal"] for c in cells)
                            / n_target,
                            "media_retenida_cruda_mismo_soporte": sum(
                                c["N_retenido"] * c["media_retenida"] for c in cells
                            )
                            / n_ret,
                            "media_retenida_estandarizada_basal": sum(
                                c["N_basal"] * c["media_retenida"] for c in cells
                            )
                            / n_target,
                            "nota": "Reponderación de valores basales observados, no desenlaces después de morir; sin IC por muestras anidadas. Soporte sexo×edad×escolaridad con>=20retenidos/celda.",
                            "celdas": cells,
                        }
                profiles_selection = []
                for state, g in p.groupby(groups, observed=True):
                    profiles_selection.append(
                        {
                            "estado": state,
                            "N_cohorte": len(g),
                            "edad": stats(g.edad_a),
                            "escolaridad": stats(g.educacion_a),
                            "indicador_basal": stats(g.loc[g[v + "__elegible_a"].eq(True), v + "_a"])
                            if v not in CATEGORICAL
                            else None,
                            "K": g.K_estado_a.value_counts().to_dict(),
                            "sexo": g.sexo_grupo_a.value_counts().to_dict(),
                            "patrimonio_grupos": g.patrimonio_inicial_a.value_counts().to_dict(),
                        }
                    )
                association = []
                for sample, mask in [
                    ("Basal válido", p[v + "__elegible_a"].eq(True) & p[v + "_a"].notna()),
                    ("Retenido con par válido", paired),
                ]:
                    for state in ["Sí", "No", "ND"]:
                        g = p.loc[mask & p.K_estado_a.eq(state)]
                        association.append(
                            {
                                "muestra": sample,
                                "K_inicial": state,
                                "N": len(g),
                                "basal": stats(g[v + "_a"]) if v not in CATEGORICAL else None,
                            }
                        )
                sensitivity = []
                if v in FLAGS and changes is not None:
                    z = p.loc[paired & p[FLAGS[v] + "_a"].eq(0) & p[FLAGS[v] + "_b"].eq(0)]
                    sensitivity.append(
                        {
                            "criterio": "No imputado en ambos extremos",
                            "N": len(z),
                            "delta": stats(z[v + "_b"] - z[v + "_a"]),
                        }
                    )
                z = p.loc[
                    paired
                    & p.edad_b.ge(60)
                    & p.edad_b.ge(p.edad_a)
                    & p.sexo_a.eq(p.sexo_b)
                    & ~p.inconsistente_vital_a
                ]
                if changes is not None:
                    sensitivity.append(
                        {
                            "criterio": "Sin edad/sexo discordantes ni antecedente fallecido→vivo",
                            "N": len(z),
                            "delta": stats(z[v + "_b"] - z[v + "_a"]),
                        }
                    )
                # Escenarios entre vivos confirmados, basal válido, sin medición final; nunca después de muerte.
                scenarios = []
                if changes is not None and v in [
                    "salud_glob",
                    "n_sint_depr",
                    "recuerdo1",
                    "recuerdo2",
                    "n_abvd",
                    "n_aivd",
                    "n_mov",
                ]:
                    lower, upper = {
                        "salud_glob": (1, 5),
                        "n_sint_depr": (0, 9),
                        "recuerdo1": (0, 8),
                        "recuerdo2": (0, 8),
                        "n_abvd": (0, 5),
                        "n_aivd": (0, 4),
                        "n_mov": (0, 5),
                    }[v]
                    alive_target = p.loc[
                        p[v + "__elegible_a"].eq(True) & p[v + "_a"].notna() & p.vivo_destino
                    ]
                    observed = alive_target[v + "_b"].where(alive_target[v + "__elegible_b"].eq(True))
                    N = len(alive_target)
                    for offset in [-1, 0, 1]:
                        missing = observed.isna()
                        knownsum = (observed - alive_target[v + "_a"]).sum()
                        hypothetical = (alive_target.loc[missing, v + "_a"] + offset).clip(lower, upper)
                        delta = (
                            (knownsum + (hypothetical - alive_target.loc[missing, v + "_a"]).sum()) / N
                            if N
                            else None
                        )
                        scenarios.append(
                            {
                                "supuesto_cambio_no_medido": offset,
                                "N_vivos_basal_valido": N,
                                "N_no_medidos_vivos": int(missing.sum()),
                                "cambio_escenario": float(delta) if delta is not None else None,
                                "nota": "Escenario agregado, no valores imputados; incluye ineligibilidad de modalidad, supuesto fuerte.",
                            }
                        )
                indicators.append(
                    {
                        "variable": v,
                        "dimension": dim,
                        "seleccion": selection,
                        "cambios": changes,
                        "perfiles_seleccion": profiles_selection,
                        "asociacion_K_basal_seleccion": association,
                        "sensibilidades": sensitivity,
                        "escenarios_vivos": scenarios,
                        "estandarizacion_composicion_basal": composition,
                        "restriccion": "Restas seriadas2021 cambia tarea; sin diferencias2018–2021."
                        if v == "serial7" and destination == 2021
                        else "Patrimonio: sin cambios monetarios por deflactación/unidades pendientes."
                        if v == "imp_neto"
                        else "Categorías: no diferencias numéricas."
                        if v in CATEGORICAL
                        else "Comparabilidad operacional condicionada; no invariancia certificada.",
                    }
                )
        complement = []
        for branch in ["apoyo_propio_a", "pension_conyuge_k_a"]:
            mask = pd.Series(True, index=p.index)
            if branch.startswith("pension_conyuge"):
                if origin not in [2018]:
                    continue
                mask = p.titularidad_pareja_estado_a.eq("puntero_pareja_concordante")
                # Usar contrato del proveedor exacto; no inferir parejas por rama válida.
                if not mask.any():
                    complement.append(
                        {
                            "rama": branch,
                            "estado": "Universo de pareja confirmado no reconstruido con esta etiqueta; consultar contrato03, sin contraste.",
                        }
                    )
                    continue
            for state, g in p.loc[mask & p[branch].notna()].groupby(branch):
                complement.append(
                    {
                        "rama": branch,
                        "recepcion": str(state),
                        **death_bounds(int(g.D_reg.sum()), int((~g.presente).sum()), len(g)),
                    }
                )
        clean = p.loc[~p.inconsistente_vital_a]
        bounds_si = next(g for g in mortal if g["K_inicial"] == "Sí")
        bounds_no = next(g for g in mortal if g["K_inicial"] == "No")
        bounddiff = {
            "inf_pp": bounds_si["limite_inf_pct"] - bounds_no["limite_sup_pct"],
            "sup_pp": bounds_si["limite_sup_pct"] - bounds_no["limite_inf_pct"],
            "supuesto": "Registros de muerte correctos; cada ausente puede vivo/muerto; no identifica fecha.",
        }
        results["intervalos"].append(
            {
                "origen": origin,
                "destino": destination,
                "N_cohorte": len(p),
                "estado_vital": p.estado_vital.value_counts().to_dict(),
                "N_vital_inconsistente": int(p.inconsistente_vital_a.sum()),
                "N_reaparece_posterior": ref["seguimiento"]["N_reaparece"],
                "N_fallecido_reaparece": ref["seguimiento"]["N_fallecido_reaparece"],
                "duracion_vivos": ref["duracion_vivos"],
                "K_comparable_cambio": COMPARABLE[origin, destination],
                "mortalidad_K": mortal,
                "contraste_K": contrast,
                "ajustes_K": adjusted,
                "perfiles_mortalidad": profiles,
                "ajustes_perfiles": adjusted_profiles,
                "indicadores": indicators,
                "complementarios": complement,
                "limites_diferencia_mortalidad": bounddiff,
                "sensibilidad_inconsistencia": {
                    "N_cohorte_sin_inconsistentes": len(clean),
                    "D_reg": int(clean.D_reg.sum()),
                },
            }
        )
    valid = f.loc[f.universo_60]
    for dim, variables in DIMENSIONS.items():
        for v in variables:
            counts = valid.loc[valid[v + "__elegible"] & valid[v].notna()].groupby("id").size()
            multi = set(counts.index[counts >= 2])
            multi3 = set(counts.index[counts >= 3])
            row = {
                "variable": v,
                "dimension": dim,
                "N_personas_alguna_medicion": len(counts),
                "N_dos_o_mas": len(multi),
                "N_tres_o_mas": len(multi3),
                "nota_comparabilidad_multivisita": "Conteos de disponibilidad del campo, no serie comparable: restas2021 cambia tarea."
                if v == "serial7"
                else "Comparabilidad operacional condicionada",
                "N_personas_pares_consecutivos": len(pair_ids[v]),
                "N_personas_pares_K": len(kpair_ids[v]),
                "interseccion_pares_K_multi": len(kpair_ids[v] & multi),
                "solo_pares_K": len(kpair_ids[v] - multi),
                "solo_multi": len(multi - kpair_ids[v]),
                "conteos_mediciones": [
                    {"N_mediciones": int(n), "N_personas": int(k)}
                    for n, k in counts.value_counts().sort_index().items()
                ],
            }
            if v not in CATEGORICAL and v != "imp_neto":
                curves = []
                subset = valid.loc[valid.id.isin(multi) & valid[v + "__elegible"] & valid[v].notna()]
                for y, z in subset.groupby("ano"):
                    curves.append({"ronda": int(y), "N": len(z), "media": float(z[v].mean())})
                row["composicion_subgrupo_multimedicion"] = curves
            results["multivisita"].append(row)
    mental = next(x for x in results["multivisita"] if x["variable"] == "n_sint_depr")
    results["reconciliacion"] = {
        key: mental[key]
        for key in [
            "N_dos_o_mas",
            "N_personas_pares_K",
            "interseccion_pares_K_multi",
            "solo_pares_K",
            "solo_multi",
        ]
    }
    assert results["reconciliacion"] == {
        "N_dos_o_mas": 14069,
        "N_personas_pares_K": 13570,
        "interseccion_pares_K_multi": 13560,
        "solo_pares_K": 10,
        "solo_multi": 509,
    }
    results["IPW_por_dimension"] = [
        {
            "dimension": dim,
            "variables": names,
            "estimando_propuesto": "Media/cambio entre sobrevivientes de cohorte basal definida, con observación documentada",
            "vital_desconocido": "No resuelto para ausentes",
            "positividad": "No certificada; soporte de medición/modalidad debe auditarse",
            "pesos_extremos_ESS_balance": "No calculados: no pesos estimados",
            "limite_especifico": {
                "Física": "Salud global directa; diabetes/enfermedades/BMI admiten sustitutos. Diagnóstico y modalidad no equivalentes.",
                "Mental": "Solo directa; nueve componentes y basales disponibles seleccionan target.",
                "Cognición": "Solo directa; productos imputados/flags y cambios de instrumento. IPW no armoniza restas2021.",
                "Funcionalidad": "ABVD admite sustitutos; AIVD/movilidad directas. No único modelo de observación para toda funcionalidad.",
                "Económica": "Más cobertura en sustitutos; K propia/cónyuge/A distintos, stock compartido y unidades pendientes.",
            }[dim],
            "decision": "No implementar con evidencia actual",
        }
        for dim, names in DIMENSIONS.items()
    ]
    results["metodologia"] = {
        "N_personas_cohortes_distintas": len(set(all_origin_ids)),
        "N_aportaciones_cohortes": len(all_origin_ids),
        "mortality_estimand": "Registro sobre fallecido en destino / cohorte viva60+ en origen; no mortalidad completa ni tasa anual.",
        "ajuste": "Estandarización directa de registroD a composición conjunta del soporte; covariables basales, >=20porrama/celda; sin diseño/hogar.",
        "IPW": "No se estimaron pesos; ESS/extremos/balance no evaluados, por prerequisitos no resueltos.",
        "supervivencia": "No Kaplan–Meier/Cox: sin fechas fiables de muerte/censura; ausentes con vital desconocido.",
        "economia": "Stock compartido, negativos/ceros conservados; sin cambios monetarios reales ni diferencias de códigos categóricos.",
    }
    return results


def verify_inputs() -> None:
    """Verifica fuentes y resultados previos sin comandos Git."""
    d = json.loads((OUTPUT / "manifest.json").read_text())
    bad = [
        name
        for name, h in d["protegidos"].items()
        if sha256((PROJECT_ROOT / name).read_bytes()).hexdigest() != h
    ]
    if bad:
        raise ValueError("Archivos protegidos cambiados: " + str(bad))
    assert sha256((PROJECT_ROOT / ".git/index").read_bytes()).hexdigest() == d["indice_sha256"]
