"""Descriptivos de una fuente económica independiente, sin integración de bases."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .independent_eda import VariableSpec, _summary, code_token, validate_values


def component_unit(base: str) -> str:
    """Periodicidad documentada: ventana de recepción anual ≠ monto anual.

    Cuestionario K 2021 y asignaciones del documento de imputación. Los salarios
    con periodo mes/año no disponible permanecen pendientes de validación.
    """
    if base == "111":
        return "pesos, gasto total por fallecimiento del cónyuge"
    if base in {"77","80_3","83_2"}:
        return "pesos, monto total recibido en el periodo previo"
    if base in {"4_1","4_2","8_1","8_2","20_1","24_1","33_1","33_2","33_3","40","42","44","86"}:
        return "pesos, valor patrimonial/deuda al momento de entrevista"
    if base in {"47a","50a","53a","56a"}:
        return "pesos, periodicidad salarial por confirmar"
    documented_monthly = {"88","101","103","48a","51a","54a","57a","27_1","29_1"}
    documented_monthly |= {f"{q}_{i}" for q in ["11","13","15","36"] for i in ([1,2,3] if q=="36" else [1,2])}
    documented_monthly |= {f"{q}_{t}_{i}" for q in ["61","67"] for t in range(1,5) for i in [1,2]}
    documented_monthly |= {"80_1_1","80_1_2","83_1_1","83_1_2"}
    if base not in documented_monthly:
        raise ValueError(f"Componente sin periodicidad documentada: {base}")
    return "pesos por mes"


def describe_source_variable(series: pd.Series, spec: VariableSpec,
                             eligible: pd.Series | None = None) -> dict:
    """Conserva todos los registros; elegibilidad nullable admite filtros desconocidos.

    El universo no se reconstruye con los perdidos. No publica valores individuales
    ni barras para claves. Los histogramas agrupan medidas, incluso sus extremos.
    """
    if spec.variable in {"cunicah", "np", "unhhid", "k45d_21", "k52a_1_21"} or spec.variable.startswith("subhog_"):
        raise ValueError("No se describen identificadores ni punteros individuales.")
    values, states = validate_values(series, spec)
    summary = _summary(values, len(series))
    if spec.kind == "categorical":
        summary = {k:v for k,v in summary.items() if k in {"N_total","N_valido","N_no_valido","pct_valido_total"}}
    if eligible is None:
        summary.update(N_elegible=None, N_elegibilidad_desconocida=len(series),
                       N_valido_elegible=None, N_valido_fuera_universo=None, pct_valido_elegible=None)
    else:
        eligible = eligible.reindex(series.index).astype("boolean")
        yes = eligible.fillna(False)
        unknown = int(eligible.isna().sum())
        ne = int(yes.sum())
        nv = int((yes & values.notna()).sum())
        summary.update(N_elegible=ne if not unknown else None, N_elegible_confirmado=ne,
                       N_elegibilidad_desconocida=unknown, N_valido_elegible=nv,
                       N_valido_fuera_universo=int((eligible.eq(False).fillna(False) & values.notna()).sum()),
                       pct_valido_elegible=100*nv/ne if ne and not unknown else None)
    absence = [{"estado": str(k), "n":int(v), "pct_total":100*v/len(series)} for k,v in states.value_counts().items()]
    frequencies = []
    if spec.kind == "categorical":
        counts = values.dropna().map(code_token).value_counts()
        for c,label in spec.codes.items():
            n = int(counts.get(c,0))
            frequencies.append({"codigo":c,"respuesta":label,"n":n,"N_total":len(series),
                                "N_valido":summary["N_valido"],"pct_total":100*n/len(series),
                                "pct_valido":100*n/summary["N_valido"] if summary["N_valido"] else None})
    elif summary["N_valido"]:
        x = values.dropna().astype(float)
        # Intervalos comunes explícitos para montos de esta ronda; no RF/NS válidos.
        edges = np.array([-np.inf,0,1,1000,5000,10000,25000,50000,100000,250000,500000,1000000,5000000,np.inf])
        if spec.unit == "años":
            edges = np.arange(0,121,10).astype(float)
            edges = np.r_[-np.inf,edges,np.inf]
        counts,_ = np.histogram(x, bins=edges)
        frequencies = [{"inferior":code_token(a),"superior":code_token(b),"n":int(n),
                        "pct_valido":100*n/len(x)} for a,b,n in zip(edges[:-1],edges[1:],counts)]
    assert sum(r["n"] for r in absence) == len(series)
    assert sum(r["n"] for r in frequencies) == summary["N_valido"]
    return {"resumen":summary,"estados":absence,"distribucion":frequencies}


def plot_source(result: dict, spec: VariableSpec, source: str, path: Path) -> None:
    """Gráfica independiente por variable y fuente, BrBG, denominadores explícitos."""
    s = result["resumen"]
    rows = result["distribucion"]
    fig,ax = plt.subplots(figsize=(10,5.5), layout="constrained")
    if rows:
        labels = [f"{r['codigo']}: {r['respuesta']}" if "codigo" in r else f"[{r['inferior']}; {r['superior']})" for r in rows]
        import textwrap
        ax.bar(range(len(rows)), [r["n"] for r in rows], color=plt.cm.BrBG(.92))
        ax.set_xticks(range(len(rows)), [textwrap.fill(t,20) for t in labels], rotation=40, ha="right", fontsize=8)
    else:
        ax.text(.5,.5,"Sin valores válidos; no equivale a cero",ha="center",transform=ax.transAxes)
    ax.set_ylabel("Frecuencia absoluta, sin ponderar")
    ax.set_title(f"{source} · 2021 · {spec.variable}\nN total={s['N_total']:,}; elegible={s['N_elegible'] if s['N_elegible'] is not None else 'ND'}; válido={s['N_valido']:,}",fontsize=10)
    ax.set_xlabel(spec.unit)
    ax.spines[["top","right"]].set_visible(False)
    path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path,dpi=110)
    plt.close(fig)


def paired_imputation_check(derived: pd.Series, imputed: pd.Series, flag: pd.Series) -> dict:
    """Cotejo dentro del mismo archivo; no confunde bandera con cambio de monto."""
    from .source_inventory import missing_mask
    d = pd.to_numeric(derived.where(~missing_mask(derived)), errors="coerce")
    i = pd.to_numeric(imputed.where(~missing_mask(imputed)), errors="coerce")
    f = pd.to_numeric(flag.where(~missing_mask(flag)), errors="coerce")
    both = d.notna() & i.notna()
    changed = both & ~pd.Series(np.isclose(d.fillna(0),i.fillna(0),rtol=1e-7,atol=.01),index=d.index)
    return {"N_total":len(d),"N_derivado":int(d.notna().sum()),"N_imputado":int(i.notna().sum()),
            "N_recuperados":int((d.isna() & i.notna()).sum()),"N_ambos":int(both.sum()),
            "N_ambos_difieren":int(changed.sum()),"N_bandera_1":int(f.eq(1).sum()),
            "N_recuperado_bandera_no_1":int((d.isna() & i.notna() & ~f.eq(1)).sum()),
            "N_cambio_observado_bandera_no_1":int((changed & ~f.eq(1)).sum())}
