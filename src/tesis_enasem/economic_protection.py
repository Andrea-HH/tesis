"""Cobertura propia K/A, montos nominales y selección; no inferencia causal."""

from __future__ import annotations

import json
from collections.abc import Iterator
from hashlib import sha256
from itertools import combinations, pairwise
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .independent_eda import validate_values
from .integration import person_id, restore_stata
from .pension_health import YEARS, contracts
from .pension_ownership import tri_or, wave_contract
from .project_paths import INTERIM_DIR, PROCESSED_DIR, PROJECT_ROOT
from .protection_eda import support_contract
from .selection_mortality import death_bounds

OUTPUT = INTERIM_DIR / "cobertura_proteccion_economica"
NOTEBOOK = "06_COBERTURA_PROTECCION_ECONOMICA.ipynb"
GROUPS = ("sexo_grupo", "edad_06", "educacion_grupo", "localidad_grupo", "ocupacion_grupo")
WINDOWS = ((2001, 2003), (2012, 2015), (2018, 2021))
PARTNER = "puntero_pareja_concordante"
NO_PARTNER = "sin_pareja_residente_explicita"


def save_json(path: Path, value: Any) -> None:
    """Guarda agregados sin identificadores personales y exige números finitos."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def verify_inputs() -> int:
    """Comprueba la instantánea anterior: fuentes, notebooks, LaTeX e índice intactos."""
    protected = json.loads((OUTPUT / "insumos_protegidos.json").read_text())
    for name, expected in protected.items():
        if sha256((PROJECT_ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Cambió un archivo protegido: {name}")
    return len(protected)


def nullable(value: Any) -> bool | None:
    """Adapta booleanos pandas a lógica trivalente, sin rellenar faltantes."""
    return None if pd.isna(value) else bool(value)


def union_receipt(k: pd.Series, a: pd.Series) -> pd.Series:
    """Una afirmativa basta; una negativa de la unión exige ambas negativas."""
    return pd.Series(
        [tri_or(nullable(x), nullable(y)) for x, y in zip(k, a)],
        index=k.index,
        dtype="boolean",
    )


def load_panel() -> pd.DataFrame:
    """Reutiliza sidecar validado y añade solo ocupación/estado vital/fecha, LEFT 1:1."""
    specs, _, metadata = contracts()
    f = pd.read_parquet(PROCESSED_DIR / "armonizacion_economica_v1/personas_ronda.parquet")
    fields = ["ocupacion", "est_conyugal", "imp_neto"]
    tags = [metadata[v]["campo_tag"] for v in fields]
    m = pd.read_parquet(
        PROCESSED_DIR / "enasem_integrada_provisional.parquet",
        columns=["id", "ronda", "fallecido", "mes_ent", *fields, *tags],
    )
    if f[["id", "ronda"]].duplicated().any() or m[["id", "ronda"]].duplicated().any():
        raise ValueError("Clave persona-ronda duplicada")
    if not f.id.equals(person_id(f)):
        raise ValueError("ID cunicah:np alterado")
    f = f.merge(m, on=["id", "ronda"], how="left", validate="one_to_one", indicator=True)
    assert len(f) == 99676 and f.id.nunique() == 27171 and f._merge.eq("both").all()
    f = f.drop(columns="_merge")
    for v in fields:
        f[v], f[v + "__estado"] = validate_values(restore_stata(f[v], f[metadata[v]["campo_tag"]]), specs[v])
    f["vivo"] = f.tipent.isin([1, 2, 3, 4])
    f["directa"] = f.tipent.isin([1, 2])
    f["universo_60"] = f.vivo & f.edad.ge(60)
    f["edad_06"] = (
        pd.cut(f.edad, [59, 64, 69, np.inf], labels=["60–64", "65–69", "70+"])
        .astype(object)
        .fillna("Desconocido")
    )
    f["ocupacion_grupo"] = f.ocupacion.map(
        {1: "Trabaja", 2: "Busca trabajo", 3: "Labores del hogar", 4: "Retirado/incapacitado/no trabaja"}
    ).fillna("Desconocido")
    assert not (f.fallecido.eq(1) ^ f.tipent.eq(5)).any()
    return f


def receipts(frame: pd.DataFrame, direct_only: bool = True) -> pd.DataFrame:
    """Excluye sustitutos del estimando principal, conservando datos originales."""
    f = frame.copy()
    allowed = f.directa if direct_only else f.vivo
    for variable in ("pension_propia_k", "pension_conyuge_k", "apoyo_propio"):
        f[variable] = f[variable].where(allowed)
    f["union_ka"] = union_receipt(f.pension_propia_k, f.apoyo_propio)
    f["elegible_06"] = allowed
    return f


def typology_row(row: pd.Series) -> tuple[str, str]:
    """Partición completa por contexto: ocho combinaciones con pareja y cuatro sin ella."""
    context = row.titularidad_pareja_estado
    scope = (
        "Pareja confirmada"
        if context == PARTNER
        else "Sin pareja residente"
        if context == NO_PARTNER
        else "Pareja indeterminada"
    )
    if not row.elegible_06:
        return scope, "Sustituto excluido del principal"
    if scope == "Pareja indeterminada":
        return scope, "ND de contexto de pareja"
    own, support, spouse = (
        nullable(row.pension_propia_k),
        nullable(row.apoyo_propio),
        nullable(row.pension_conyuge_k),
    )
    required = [own, support, spouse] if scope == "Pareja confirmada" else [own, support]
    if any(v is None for v in required):
        return scope, "ND de recepción/titularidad"
    labels = []
    if own:
        labels.append("K propia")
    if scope == "Pareja confirmada" and spouse:
        labels.append("K del cónyuge")
    if support:
        labels.append("A propia")
    if labels:
        return scope, ("Solo " if len(labels) == 1 else "") + " + ".join(labels)
    return (
        scope,
        "No reporta ninguna de las vías identificadas"
        if scope == "Pareja confirmada"
        else "Negativas propias K y A; sin pareja residente",
    )


def typology(frame: pd.DataFrame) -> pd.DataFrame:
    """Anota categorías sin cambiar recepción ni interpretar hogar como persona."""
    f = frame.copy()
    f[["contexto_06", "tipo_06"]] = pd.DataFrame([typology_row(r) for _, r in f.iterrows()], index=f.index)
    f["tipologia_conocida"] = ~f.tipo_06.str.startswith(("ND", "Sustituto"))
    return f


def grouped(frame: pd.DataFrame) -> Iterator[tuple[str, str, pd.DataFrame]]:
    """General y cada estratificación por separado, con categoría desconocida conservada."""
    yield "General", "Todas", frame
    for v in GROUPS:
        for label, part in frame.groupby(v, observed=True, dropna=False):
            yield v, str(label), part


def pct(n: int, denominator: int) -> float | None:
    """Porcentaje con denominador explícito; vacío no produce cero."""
    return 100 * n / denominator if denominator else None


def coverage(frame: pd.DataFrame) -> dict:
    """Tasas por su propio N conocido y contraste K/OR en idéntico soporte conjunto."""
    eligible = frame.elegible_06
    result = {
        "N_60": len(frame),
        "N_elegible": int(eligible.sum()),
        "N_sustituto": int(frame.tipent.isin([3, 4]).sum()),
    }
    complete = frame.pension_propia_k.notna() & frame.apoyo_propio.notna()
    result["N_K_A_conocidas"] = int(complete.sum())
    for v, key in [("pension_propia_k", "K"), ("apoyo_propio", "A"), ("union_ka", "KA")]:
        yes = int(frame[v].eq(True).sum())
        known = int(frame[v].notna().sum())
        result.update(
            {
                f"N_{key}_si": yes,
                f"N_{key}_conocido": known,
                f"N_{key}_ND_elegible": int((eligible & frame[v].isna()).sum()),
                f"{key}_pct": pct(yes, known),
            }
        )
    result["N_KA_no"] = int(frame.union_ka.eq(False).sum())
    result["KA_min_elegible_pct"] = pct(result["N_KA_si"], result["N_elegible"])
    result["KA_max_elegible_pct"] = pct(result["N_KA_si"] + result["N_KA_ND_elegible"], result["N_elegible"])
    result["K_soporte_conjunto_pct"] = pct(
        int(frame.loc[complete, "pension_propia_k"].eq(True).sum()), int(complete.sum())
    )
    result["KA_soporte_conjunto_pct"] = pct(
        int(frame.loc[complete, "union_ka"].eq(True).sum()), int(complete.sum())
    )
    return result


def typology_table(frame: pd.DataFrame) -> list[dict]:
    """Personas únicas por ronda/contexto/grupo; categorías disjuntas, con N ND."""
    rows = []
    for dimension, group, part in grouped(frame):
        for context, subset in part.groupby("contexto_06", observed=True):
            known = int(subset.tipologia_conocida.sum())
            for kind, n in subset.tipo_06.value_counts().items():
                rows.append(
                    {
                        "dimension": dimension,
                        "grupo": group,
                        "contexto": str(context),
                        "categoria": str(kind),
                        "N": int(n),
                        "N_grupo": len(part),
                        "N_contexto": len(subset),
                        "N_conocido_contexto": known,
                        "N_ND_contexto": len(subset) - known,
                        "N_sin_pareja_grupo": int(part.contexto_06.eq("Sin pareja residente").sum()),
                        "pct_grupo": pct(int(n), len(part)),
                        "pct_contexto_conocido": pct(int(n), known)
                        if not str(kind).startswith(("ND", "Sustituto"))
                        else None,
                    }
                )
    return rows


def gaps(rows: list[dict]) -> list[dict]:
    """Brechas dirigidas por pares de grupos, sin selección por mayor contraste."""
    result = []
    for dimension in GROUPS:
        known = [x for x in rows if x["dimension"] == dimension and x["grupo"] != "Desconocido"]
        for a, b in combinations(sorted(known, key=lambda x: x["grupo"]), 2):
            entry = {
                "dimension": dimension,
                "grupo_a": a["grupo"],
                "grupo_b": b["grupo"],
                "N_a_KA": a["N_KA_conocido"],
                "N_b_KA": b["N_KA_conocido"],
            }
            for name in ["K_pct", "A_pct", "KA_pct", "K_soporte_conjunto_pct", "KA_soporte_conjunto_pct"]:
                entry[name + "_brecha_pp"] = (
                    b[name] - a[name] if a[name] is not None and b[name] is not None else None
                )
            result.append(entry)
    return result


def monetary_summary(values: pd.Series) -> dict:
    """Cuantiles nominales sin frecuencias individuales ni suma entre vías."""
    x = values.dropna().astype(float)
    return {
        "N": len(x),
        **{
            key: float(x.quantile(q)) if len(x) else None
            for key, q in [("q10", 0.1), ("q25", 0.25), ("mediana", 0.5), ("q75", 0.75), ("q90", 0.9)]
        },
        "media": float(x.mean()) if len(x) else None,
        "N_cero": int(x.eq(0).sum()),
    }


def monetary(frame: pd.DataFrame, block: str) -> tuple[list[dict], dict]:
    """Eventos originales únicos; enlaza beneficiario, no replica instituciones/hogar."""
    name = "eventos_pensionarios" if block == "K" else "eventos_apoyos"
    e = pd.read_parquet(PROCESSED_DIR / f"armonizacion_economica_v1/{name}.parquet")
    keys = ["ano", "hogar_fuente", "fuente", "version", "rama", "slot"] + (["tipo"] if block == "K" else [])
    if e[keys].duplicated().any() or not e.version.eq("original").all():
        raise ValueError("Eventos duplicados o versiones mezcladas")
    frame = frame.copy()
    frame["grupo_tipologia"] = "No aplicable antes de2018"
    recent = frame.ano.isin([2018, 2021])
    typed = typology(frame.loc[recent])
    frame.loc[recent, "grupo_tipologia"] = typed.contexto_06 + " · " + typed.tipo_06
    profile = frame[
        ["id", "ano", "elegible_06", "pension_propia_k", "apoyo_propio", *GROUPS, "grupo_tipologia"]
    ]
    e = e.merge(
        profile,
        left_on=["beneficiario_id", "ano"],
        right_on=["id", "ano"],
        how="left",
        validate="many_to_one",
        indicator=True,
    )
    linked = e._merge.eq("both")
    diagnostic = {
        "N_eventos_fuente": len(e),
        "N_eventos_fuera_60": int((~linked).sum()),
        "N_eventos_60_excluidos_modalidad": int((linked & ~e.elegible_06.eq(True)).sum()),
    }
    e = e.loc[linked & e.elegible_06.eq(True)].copy()
    gate = "pension_propia_k" if block == "K" else "apoyo_propio"
    assert e[gate].eq(True).all()
    out = []
    for year in YEARS:
        f = frame.loc[frame.ano.eq(year)]
        ey = e.loc[e.ano.eq(year)]
        groups = list(grouped(f))
        if year in (2018, 2021):
            groups += [("grupo_tipologia", str(g), z) for g, z in f.groupby("grupo_tipologia", observed=True)]
        for dimension, group, part in groups:
            subset = ey if dimension == "General" else ey.loc[ey[dimension].eq(group)]
            recipient = part[gate].eq(True)
            per_person = subset.groupby("beneficiario_id").monto_mensual_observado.agg(
                N_eventos="size", N_montos="count", suma_parcial=lambda x: x.sum(min_count=1)
            )
            complete = per_person.N_eventos.eq(per_person.N_montos)
            # Comprueba el sidecar existente, sin reemplazarlo ni reinterpretarlo como ingreso.
            original = part.set_index("id")[f"monto_{block.lower()}_propio_mensual_observado_parcial"]
            matched = original.reindex(per_person.index)
            assert np.allclose(
                matched.to_numpy(dtype=float), per_person.suma_parcial.to_numpy(dtype=float), equal_nan=True
            )
            out.append(
                {
                    "ronda": year,
                    "via": block,
                    "dimension": dimension,
                    "grupo": group,
                    "N_receptores": int(recipient.sum()),
                    "N_personas_eventos": len(per_person),
                    "N_personas_monto": int(per_person.suma_parcial.notna().sum()),
                    "N_personas_todos_eventos_capturados_con_monto": int(complete.sum()),
                    "N_personas_eventos_parciales": int((~complete & per_person.suma_parcial.notna()).sum()),
                    "N_receptores_sin_monto": int(recipient.sum())
                    - int(per_person.suma_parcial.notna().sum()),
                    "N_eventos": len(subset),
                    "N_eventos_monto": int(subset.monto_mensual_observado.notna().sum()),
                    "N_eventos_ND": int(subset.monto_mensual_observado.isna().sum()),
                    "por_evento": monetary_summary(subset.monto_mensual_observado),
                    "suma_personal_observada_parcial": monetary_summary(per_person.suma_parcial),
                    "suma_personal_todos_eventos_capturados": monetary_summary(
                        per_person.loc[complete, "suma_parcial"]
                    ),
                }
            )
    return out, diagnostic


def spouse_monetary(frame: pd.DataFrame) -> list[dict]:
    """Monto de cónyuge como recurso contextual, nunca pensión propia del focal."""
    out = []
    for year in (2018, 2021):
        f = frame.loc[frame.ano.eq(year) & frame.titularidad_pareja_estado.eq(PARTNER)]
        for dim, group, part in grouped(f):
            eligible = part.elegible_06
            yes = part.pension_conyuge_k.eq(True).fillna(False)
            values = part.loc[yes, "monto_k_conyuge_mensual_observado_parcial"]
            out.append(
                {
                    "ronda": year,
                    "dimension": dim,
                    "grupo": group,
                    "N_focales_pareja_confirmada": len(part),
                    "N_focales_elegibles": int(eligible.sum()),
                    "N_conyuge_si": int(yes.sum()),
                    "N_conyuge_conocido": int(part.pension_conyuge_k.notna().sum()),
                    "N_conyuge_ND_elegible": int((eligible & part.pension_conyuge_k.isna()).sum()),
                    "N_focales_monto_conyuge": int(values.notna().sum()),
                    "suma_observada_parcial_conyuge": monetary_summary(values),
                    "unidad": "Persona focal con cónyuge confirmado; monto de otra persona, no ingreso propio ni transferencia comprobada",
                }
            )
    return out


def persistence_bounds(no: int, yes: int, dead: int, absent: int, alive_nd: int, other: int = 0) -> dict:
    """Cotas de persistencia/recepción por cohorte: fallecidos nunca pueden recibir al destino."""
    n = no + yes + dead + absent + alive_nd + other
    uncertain = absent + alive_nd + other
    return {
        "N": n,
        "persistencia_min_pct": pct(no, n),
        "persistencia_max_pct": pct(no + uncertain, n),
        "recepcion_min_pct": pct(yes, n),
        "recepcion_max_pct": pct(yes + uncertain, n),
        "persistencia_observados_K_pct": pct(no, no + yes),
        "N_K_destino_conocido_vivo": no + yes,
        "mortalidad": death_bounds(dead, absent + other, n),
    }


def followup(panel: pd.DataFrame, direct_only: bool) -> list[dict]:
    """Cohorte basal60+, LEFT a destino; no condicionar a supervivencia ni edad final."""
    f = receipts(panel, direct_only)
    out = []
    for a, b in WINDOWS:
        origin = f.loc[f.ano.eq(a) & f.universo_60].set_index("id")
        dest = f.loc[f.ano.eq(b)].set_index("id")
        pair = origin.join(dest, how="left", lsuffix="_a", rsuffix="_b", validate="one_to_one")
        present = pair.ano_b.notna()
        alive = pair.tipent_b.isin([1, 2, 3, 4])
        state = pd.Series("Otro estado no clasificable", index=pair.index)
        state.loc[~present] = "Ausente; vital desconocido"
        state.loc[pair.tipent_b.eq(5)] = "Fallecido registrado"
        state.loc[alive] = "Vivo; K desconocida o modalidad excluida"
        state.loc[alive & pair.pension_propia_k_b.eq(False).fillna(False)] = "Sigue con negativa K"
        state.loc[alive & pair.pension_propia_k_b.eq(True).fillna(False)] = "Recepción K observada en destino"
        pair["estado_06"] = state
        pair["KA_conocidas_vivas"] = pair.union_ka_a.notna() & pair.union_ka_b.notna() & alive
        rows = []
        for dimension in ["General", *GROUPS]:
            for group, part in (
                [("Todas", pair)] if dimension == "General" else pair.groupby(dimension + "_a", observed=True)
            ):
                no = part.loc[part.pension_propia_k_a.eq(False).fillna(False)]
                counts = {
                    s: int(no.estado_06.eq(s).sum())
                    for s in [
                        "Sigue con negativa K",
                        "Recepción K observada en destino",
                        "Fallecido registrado",
                        "Ausente; vital desconocido",
                        "Vivo; K desconocida o modalidad excluida",
                        "Otro estado no clasificable",
                    ]
                }
                bounds = persistence_bounds(*counts.values())
                absent_ids = no.index[no.estado_06.eq("Ausente; vital desconocido")]
                later = panel.loc[panel.ano.gt(b) & panel.id.isin(absent_ids)]
                complete = part.KA_conocidas_vivas
                c = part.loc[complete]
                rows.append(
                    {
                        "dimension": dimension,
                        "grupo": str(group),
                        "N_cohorte_60": len(part),
                        "N_K_basal_no": len(no),
                        "N_K_basal_si": int(part.pension_propia_k_a.eq(True).sum()),
                        "N_K_basal_ND": int(part.pension_propia_k_a.isna().sum()),
                        "estados_sin_K_basal": counts,
                        "cotas": bounds,
                        "N_ausentes_reaparecen_vivos_despues": int(later.loc[later.vivo, "id"].nunique())
                        if b < 2021
                        else None,
                        "N_ausentes_registro_fallecido_despues": int(
                            later.loc[later.tipent.eq(5), "id"].nunique()
                        )
                        if b < 2021
                        else None,
                        "N_sustituto_destino_sin_K_basal": int(no.tipent_b.isin([3, 4]).sum()),
                        "N_pares_union_conocida": len(c),
                        "KA_basal_mismos_pares_pct": pct(int(c.union_ka_a.eq(True).sum()), len(c)),
                        "KA_destino_mismos_pares_pct": pct(int(c.union_ka_b.eq(True).sum()), len(c)),
                        "K_A_homologables_intervalo": a == 2012,
                        "N_final_edad_menor_60": int((part.edad_b.lt(60) & alive.reindex(part.index)).sum()),
                    }
                )
        orig_cov = coverage(origin)
        retained = origin.loc[pair.KA_conocidas_vivas]
        months = (12 * (pair.a_o_ent_b - pair.a_o_ent_a) + pair.mes_ent_b - pair.mes_ent_a).where(
            alive & pair.mes_ent_a.between(1, 12) & pair.mes_ent_b.between(1, 12)
        )
        months = months.where(months.gt(0)).dropna()
        out.append(
            {
                "origen": a,
                "destino": b,
                "anios_nominales": b - a,
                "N_cohorte_60": len(origin),
                "N_elegible_basal": int(origin.elegible_06.sum()),
                "cobertura_basal_cohorte": orig_cov,
                "cobertura_basal_retenidos": coverage(retained),
                "meses_N": len(months),
                "meses_mediana": float(months.median()) if len(months) else None,
                "meses_min": float(months.min()) if len(months) else None,
                "meses_max": float(months.max()) if len(months) else None,
                "grupos": rows,
            }
        )
    return out


def analyze() -> dict:
    """Solo ampliación06; tablas agrupadas, tipología completa y sensibilidades separadas."""
    verify_inputs()
    panel = load_panel()
    pop = panel.loc[panel.universo_60]
    assert len(pop) == 56004 and pop.id.nunique() == 18754
    result = {
        "metodologia": {
            "N_personas_ronda_60": len(pop),
            "N_personas_60": int(pop.id.nunique()),
            "principal": "Entrevistas directas; sustitutos excluidos y reportados",
            "sin_pesos": True,
            "sin_causalidad": True,
            "sin_modelos_predictivos": True,
            "deflactacion_ejecutada": False,
        },
        "rondas": [],
        "montos": [],
        "seguimiento_principal": [],
        "seguimiento_sensibilidad_sustitutos": [],
    }
    for direct_only, key in [(True, "principal"), (False, "sensibilidad_sustitutos")]:
        f = receipts(pop, direct_only)
        for year in YEARS:
            part = f.loc[f.ano.eq(year)]
            rows = [{"dimension": dim, "grupo": group, **coverage(z)} for dim, group, z in grouped(part)]
            item = {
                "ronda": year,
                "analisis": key,
                "cobertura": rows,
                "brechas": gaps(rows),
                "tipologia": typology_table(typology(part)) if year in (2018, 2021) else [],
                "N_proxy_K_original_conocida": int(
                    pop.loc[pop.ano.eq(year) & ~pop.directa, "pension_propia_k"].notna().sum()
                ),
            }
            result["rondas"].append(item)
    main = receipts(pop)
    for block in ["K", "A"]:
        rows, diagnostic = monetary(main, block)
        result["montos"].extend(rows)
        result.setdefault("auditoria_eventos", {})[block] = diagnostic
    result["seguimiento_principal"] = followup(panel, True)
    result["seguimiento_sensibilidad_sustitutos"] = followup(panel, False)
    result["montos_conyuge_contextuales"] = spouse_monetary(main)
    result["comparabilidad"] = [
        {
            "origen": a,
            "destino": b,
            "K": (a, b) in WINDOWS,
            "A": (a, b) in [(2003, 2012), (2012, 2015), (2015, 2018)],
            "KA": (a, b) == (2012, 2015),
            "alcance": "Condicionada; ninguna invariancia ni expansión política identificada",
        }
        for a, b in pairwise(YEARS)
    ]
    result["contratos_originales"] = [
        {
            "ronda": y,
            "K_propias": list(wave_contract(y).own_gates),
            "K_conyuge": list(wave_contract(y).spouse_gates),
            "A_propia": support_contract(y).own_gate,
            "fuente": wave_contract(y).household,
        }
        for y in YEARS
    ]
    verify_inputs()
    return result


def evaluate_sufficiency(amounts: pd.Series, years: pd.Series, config: dict) -> pd.DataFrame:
    """Ruta parametrizada desactivada hasta confirmar fuente, precios y umbral mensual.

    Recibe una única vía y unidad (evento o persona); jamás suma K y A. El umbral
    mide esa prestación observada, no ingreso total ni pobreza de la persona.
    """
    if not config.get("fuente_indice_confirmada") or not config.get("fuente_umbral_confirmada"):
        raise ValueError("Deflactación/suficiencia bloqueada: fuentes pendientes de confirmación")
    indices = {int(k): float(v) for k, v in config["INPC_por_ronda"].items()}
    thresholds = {int(k): float(v) for k, v in config["umbral_mensual_nominal_por_ronda"].items()}
    wanted = set(years.dropna().astype(int)) | {int(config["ronda_base"])}
    if not wanted <= set(indices) or not set(years.dropna().astype(int)) <= set(thresholds):
        raise ValueError("Faltan índices o umbrales para las rondas solicitadas")
    if any(v <= 0 or not np.isfinite(v) for v in [*indices.values(), *thresholds.values()]):
        raise ValueError("Índice/umbral debe ser positivo y finito")
    index = years.map(indices)
    threshold = years.map(thresholds)
    return pd.DataFrame(
        {
            "prestacion_pesos_constantes": amounts * indices[int(config["ronda_base"])] / index,
            "razon_prestacion_umbral": amounts / threshold,
        }
    )
