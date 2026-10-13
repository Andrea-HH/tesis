"""EDA por fuente con contrato semántico previo y exportación solo de agregados."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pandas.io.stata import StataMissingValue

from .source_inventory import missing_mask

YEARS = {1: 2001, 2: 2003, 3: 2012, 4: 2015, 5: 2018, 6: 2021}
MODALITIES = {1: "Directa seguimiento", 2: "Directa nueva", 3: "Sustituto seguimiento",
              4: "Sustituto nueva", 5: "Sobre fallecido"}
TECHNICAL_SIMPLE = {"cunicah", "np", "codent01", "codent03", "acthog", "ron_pat",
                    "ronda", "tipent", "mes_ent", "a_o_ent"}
MISSING_MEANINGS = {".p": "No incluida en sustituto", ".e": "Valor bruto imposible",
                    ".f": "Fallecimiento", ".r": "Negativa", ".d": "No sabe",
                    ".s": "Salto por respuesta previa", ".i": "Interrupción",
                    ".m": "Pregunta faltante", ".x": "No hace (ABVD/AIVD)",
                    ".w": "No disponible en ronda según tablas del libro",
                    ".": "Perdido sin motivo específico"}


@dataclass(frozen=True)
class VariableSpec:
    """Contrato verificable; la elegibilidad desconocida nunca se estima como N válido."""
    variable: str
    label: str
    kind: str
    unit: str
    codes: dict[str, str]
    numeric_nonresponse: dict[str, str]
    lower: float | None
    upper: float | None
    integer: bool
    eligibility: str
    reference: str
    page: int
    temporal: str
    interpretation: str


def simple_role(name: str) -> str:
    """Separa solo claves, diseño y pesos; conserva banderas y variables no pensionarias."""
    if name in TECHNICAL_SIMPLE or name.startswith(("subhog_", "factorh_", "factori_")):
        return "técnica: cobertura, sin distribución de identificadores"
    return "sustantiva o bandera de calidad"


def code_token(value: object) -> str:
    """Representación numérica estable para códigos, preservando tags Stata."""
    if isinstance(value, StataMissingValue):
        return value.string
    if pd.isna(value):
        return "NaN"
    if isinstance(value, (int, float, np.number)):
        return format(float(value), ".15g")
    return str(value)


def validate_values(series: pd.Series, spec: VariableSpec) -> tuple[pd.Series, pd.Series]:
    """Partición exhaustiva válida/perdida/fuera de dominio; no altera datos originales.

    Los códigos NR/NS son específicos del contrato. 8/9/88/99 jamás se excluyen
    globalmente. Valores fuera de dominio quedan en cuarentena, nunca se corrigen.
    """
    states = pd.Series("válido observado", index=series.index, dtype="str")
    miss = missing_mask(series)
    states.loc[miss] = series.loc[miss].map(
        lambda x: x.string if isinstance(x, StataMissingValue) else "vacío/NaN")
    tokens = series.map(code_token)
    for code, reason in spec.numeric_nonresponse.items():
        states.loc[~miss & tokens.eq(code)] = "NR/NS numérico: " + reason
    candidates = states.eq("válido observado")
    numbers = pd.to_numeric(series.where(candidates), errors="coerce")
    invalid = candidates & (numbers.isna() | ~np.isfinite(numbers))
    if spec.kind == "categorical":
        invalid |= candidates & ~tokens.isin(spec.codes)
    else:
        if spec.lower is not None:
            invalid |= candidates & numbers.lt(spec.lower)
        if spec.upper is not None:
            invalid |= candidates & numbers.gt(spec.upper)
        if spec.integer:
            invalid |= candidates & numbers.notna() & ~np.isclose(numbers.fillna(0) % 1, 0)
    states.loc[invalid] = "fuera de dominio documentado"
    return numbers.where(states.eq("válido observado")), states


def _summary(values: pd.Series, n_total: int) -> dict:
    x = values.dropna().astype(float)
    out = {"N_total": n_total, "N_valido": len(x), "pct_valido_total": 100 * len(x) / n_total,
           "N_no_valido": n_total - len(x)}
    out.update({k: None for k in ["media", "DE", "min", "p01", "p05", "p25", "mediana", "p75", "p95", "p99", "max"]})
    out.update({"N_ceros": int(x.eq(0).sum()), "N_negativos": int(x.lt(0).sum())})
    if len(x):
        out.update(media=float(x.mean()), DE=float(x.std()) if len(x) > 1 else None,
                   min=float(x.min()), max=float(x.max()))
        out.update(zip(["p01", "p05", "p25", "mediana", "p75", "p95", "p99"],
                       map(float, x.quantile([.01, .05, .25, .5, .75, .95, .99]))))
    return out


def analyze_variable(data: pd.DataFrame, spec: VariableSpec) -> dict:
    """Seis rondas y cinco modalidades sin filtro inicial ni deduplicación de personas."""
    if simple_role(spec.variable).startswith("técnica") or spec.variable in {"unhhid", "ps3", "ent2"}:
        raise ValueError("No se exportan distribuciones ni valores de identificadores/diseño/pesos.")
    values, states = validate_values(data[spec.variable], spec)
    summaries, frequencies, missing, histograms, strata = [], [], [], [], []
    all_valid = values.dropna().astype(float)
    edges = None
    if spec.kind != "categorical" and len(all_valid):
        if spec.variable == "imp_neto":
            edges = np.array([-np.inf, 0, 1, 50000, 100000, 250000, 500000, 1000000,
                              2500000, 5000000, 10000000, np.inf], dtype=float)
        elif spec.integer and all_valid.max() - all_valid.min() <= 65:
            edges = np.arange(all_valid.min()-.5, all_valid.max()+1.5)
        elif spec.variable == "bmi_imp":
            edges = np.r_[-np.inf, np.arange(10, 62, 2), np.inf]
        else:
            edges = np.linspace(all_valid.min(), all_valid.max(), 26) if all_valid.nunique() > 1 else np.array([all_valid.iloc[0]-.5, all_valid.iloc[0]+.5])
    for wave, year in YEARS.items():
        mask = data.ronda.eq(wave)
        n = int(mask.sum())
        if not n:
            continue
        s = _summary(values.loc[mask], n)
        # Media de códigos ordinales/nominales no es una medida sustantiva.
        if spec.kind == "categorical":
            s = {k: v for k, v in s.items() if k in ["N_total", "N_valido", "N_no_valido", "pct_valido_total"]}
        summaries.append({"ronda": wave, "anio": year, **s, "N_elegible": None,
                          "nota_elegibilidad": spec.eligibility})
        for state, count in states.loc[mask].value_counts().items():
            missing.append({"anio": year, "estado": state, "significado": MISSING_MEANINGS.get(state, state),
                            "n": int(count), "N_total": n, "pct_total": 100 * count / n})
        if spec.kind == "categorical":
            counts = values.loc[mask].dropna().map(code_token).value_counts()
            for code, label in spec.codes.items():
                count = int(counts.get(code, 0))
                frequencies.append({"anio": year, "codigo": code, "respuesta": label, "n": count,
                                    "N_total": n, "N_valido": s["N_valido"],
                                    "pct_total": 100 * count / n,
                                    "pct_valido": 100 * count / s["N_valido"] if s["N_valido"] else None})
        elif edges is not None:
            counts, _ = np.histogram(values.loc[mask].dropna(), bins=edges)
            for low, high, count in zip(edges[:-1], edges[1:], counts):
                histograms.append({"anio": year, "limite_inferior": code_token(low),
                                   "limite_superior": code_token(high), "n": int(count),
                                   "N_valido": s["N_valido"], "pct_valido": 100*count/s["N_valido"] if s["N_valido"] else None})
            assert int(sum(counts)) == s["N_valido"]
        for mode, label in MODALITIES.items():
            group = mask & data.tipent.eq(mode)
            total = int(group.sum())
            if total:
                strata.append({"anio": year, "modalidad": label, **_summary(values.loc[group], total)})
    # Modalidad también conserva distribuciones, no solo cobertura ni medias.
    modality_frequencies = []
    for wave, year in YEARS.items():
        for mode, label in MODALITIES.items():
            mask = data.ronda.eq(wave) & data.tipent.eq(mode)
            n = int(mask.sum())
            nv = int(values.loc[mask].notna().sum())
            if spec.kind == "categorical":
                counts = values.loc[mask].dropna().map(code_token).value_counts()
                for code, response in spec.codes.items():
                    count = int(counts.get(code, 0))
                    modality_frequencies.append({"anio": year, "modalidad": label, "codigo": code,
                                                 "respuesta": response, "n": count, "N_total": n,
                                                 "N_valido": nv, "pct_total": 100*count/n if n else None,
                                                 "pct_valido": 100*count/nv if nv else None})
    if spec.kind == "categorical":
        strata = [{k: v for k, v in row.items() if k in ["anio", "modalidad", "N_total", "N_valido", "N_no_valido", "pct_valido_total"]} for row in strata]
    return {"contrato": asdict(spec), "resumen": summaries, "frecuencias": frequencies,
            "estados": missing, "histograma": histograms, "por_modalidad": strata,
            "frecuencias_modalidad": modality_frequencies}


def plot_variable(result: dict, path: Path) -> None:
    """Una lámina por variable: seis distribuciones reales, BrBG y N explícitos."""
    spec = result["contrato"]
    categorical = spec["kind"] == "categorical"
    table = pd.DataFrame(result["frecuencias"] if categorical else result["histograma"])
    fig, axes = plt.subplots(2, 3, figsize=(13, 8), layout="constrained")
    colors = plt.cm.BrBG([.08, .25, .4, .6, .75, .92])
    for ax, s, color in zip(axes.flat, result["resumen"], colors):
        year, nv = s["anio"], s["N_valido"]
        if nv:
            t = table.loc[table.anio.eq(year)]
            if categorical:
                labels = t.codigo
            else:
                labels = [f"{a}; {b}" for a, b in zip(t.limite_inferior, t.limite_superior)]
            bars = ax.bar(np.arange(len(t)), t.n, color=color, edgecolor="white", linewidth=.3)
            if categorical or len(t) <= 12:
                ax.set_xticks(np.arange(len(t)), labels, rotation=55, ha="right", fontsize=8)
                if len(t) <= 12:
                    ax.bar_label(bars, labels=[f"{x:,}".replace(",", " ") for x in t.n], fontsize=7, padding=2)
            else:
                step = max(1, len(t)//6)
                ax.set_xticks(np.arange(len(t))[::step], list(labels)[::step], rotation=55, ha="right", fontsize=7)
        else:
            ax.text(.5, .5, "Sin respuestas válidas\n(no equivale a cero)", ha="center", va="center", transform=ax.transAxes)
            ax.set_xticks([])
        ax.set_title(f"{year} · N válido={nv:,} / total={s['N_total']:,}", fontsize=10)
        ax.set_ylabel("Frecuencia absoluta")
        ax.set_xlabel("Código (etiquetas en ficha)" if categorical else "Intervalo [inferior; superior)")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=.18)
        ax.margins(y=.2)
    fig.suptitle(f"{spec['variable']} · {spec['label']}\nValores observados; sin ponderar; composición por ronda", fontsize=12)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140)
    plt.close(fig)


def strict_json(value: object, path: Path) -> None:
    """JSON estándar, sin NaN/Infinity; solo esquemas agregados de este módulo."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
