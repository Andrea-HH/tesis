"""Revisión de EDA desde agregados: denominadores y comparación conjunta."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from .independent_eda import MODALITIES


def eligible_summary(result: dict, rules: dict) -> list[dict]:
    """Reconstruye universo del indicador documentado, nunca a partir de N válido.

    Una regla ND preserva el desconocimiento. Se auditan respuestas válidas fuera
    del universo propuesto, en vez de excluirlas silenciosamente.
    """
    out = []
    for s in result["resumen"]:
        rule = rules[str(s["anio"])]
        modes = rule["modalidades"]
        strata = [r for r in result["por_modalidad"] if r["anio"] == s["anio"]]
        assert sum(r["N_total"] for r in strata) == s["N_total"]
        included = None if modes is None else [r for r in strata if r["modalidad"] in [MODALITIES[m] for m in modes]]
        ne = None if included is None else sum(r["N_total"] for r in included)
        nv = None if included is None else sum(r["N_valido"] for r in included)
        out.append({"anio": s["anio"], "N_total": s["N_total"], "N_elegible": ne,
                    "N_valido": s["N_valido"], "N_valido_elegible": nv,
                    "N_valido_fuera_universo": None if nv is None else s["N_valido"]-nv,
                    "N_no_valido_elegible": None if ne is None else ne-nv,
                    "pct_valido_elegible": 100*nv/ne if ne else None,
                    "pct_valido_total": s["pct_valido_total"], "regla": rule["nota"]})
    return out


def comparison_table(result: dict) -> list[dict]:
    """Tabla numérica exacta de la figura: porcentajes categóricos o cuantiles."""
    if result["contrato"]["kind"] == "categorical":
        return result["frecuencias"]
    fields = ["anio", "N_total", "N_valido", "media", "DE", "p05", "p25", "mediana", "p75", "p95", "N_ceros", "N_negativos"]
    return [{k: s[k] for k in fields} for s in result["resumen"]]


def plot_comparison(result: dict, path: Path) -> None:
    """Una escala compartida entre rondas; BrBG; ausencia no representada como cero."""
    spec = result["contrato"]
    summaries = result["resumen"]
    colors = plt.cm.BrBG([.08, .25, .4, .6, .75, .92])
    fig, ax = plt.subplots(figsize=(12, 7))
    # Reserva explícita para título, leyenda, etiquetas y nota; sin superposición.
    fig.subplots_adjust(left=.18 if spec["kind"] != "categorical" else .09,
                        right=.98, bottom=.20, top=.77)
    if spec["kind"] == "categorical":
        codes = list(spec["codes"])
        for i, (s, color) in enumerate(zip(summaries, colors)):
            rows = [r for r in result["frecuencias"] if r["anio"] == s["anio"]]
            vals = [r["pct_valido"] if r["pct_valido"] is not None else np.nan for r in rows]
            ax.bar(np.arange(len(codes))+(i-2.5)*.13, vals, width=.13, color=color,
                   label=f"{s['anio']} (N válido={s['N_valido']:,})")
        labels = [f"{c}: {spec['codes'][c]}" for c in codes]
        import textwrap
        ax.set_xticks(np.arange(len(codes)), [textwrap.fill(t, 24) for t in labels], fontsize=8)
        ax.set_ylabel("Porcentaje entre respuestas válidas (sin ponderar)")
        ax.legend(fontsize=8, ncol=3, loc="upper center", bbox_to_anchor=(.5, 1.14))
    else:
        for i, (s, color) in enumerate(zip(summaries, colors)):
            if s["N_valido"]:
                ax.plot([s["p05"], s["p95"]], [i,i], color=color, lw=2)
                ax.plot([s["p25"], s["p75"]], [i,i], color=color, lw=9, solid_capstyle="butt")
                ax.scatter([s["mediana"]], [i], color="black", s=30, zorder=3)
            else:
                ax.text(.99, i, "Sin instrumento/respuestas válidas", transform=ax.get_yaxis_transform(), ha="right", fontsize=9)
        ax.set_yticks(range(len(summaries)), [f"{s['anio']} · N válido={s['N_valido']:,}" for s in summaries])
        ax.invert_yaxis()
        ax.set_xlabel(spec["unit"] + " · punto: mediana; barra: P25–P75; línea: P05–P95")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(alpha=.15)
    note = "Unidades almacenadas: comparación descriptiva, sin deflactar" if spec["variable"] == "imp_neto" else "Composición por ronda; sin inferencia de cambios individuales"
    fig.suptitle(f"{spec['variable']} · {spec['label']}\n{note}", fontsize=11)
    fig.text(.5, .035, "N total y elegible en la tabla. Cuantiles: dispersión, no intervalos de confianza. Ausencia ≠ cero.", ha="center", fontsize=8)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140)
    plt.close(fig)


def interpret_result(result: dict, eligibility: list[dict]) -> str:
    """Discusión con cifras y categorías propias; no causal ni representativa."""
    spec = result["contrato"]
    available = [s for s in result["resumen"] if s["N_valido"]]
    if not available:
        return "No hay valores válidos; no es posible describir la distribución sustantiva."
    first, last = available[0], available[-1]
    text = []
    if spec["kind"] == "categorical":
        if len(available) == 1:
            rows = [r for r in result["frecuencias"] if r["anio"] == first["anio"]]
            top = max(rows, key=lambda r: r["n"])
            text.append(f"Solo {first['anio']} aporta respuestas válidas. La categoría «{top['respuesta']}» reúne {top['n']:,}/{first['N_valido']:,} ({top['pct_valido']:.2f}%). La gráfica conjunta documenta la falta de cobertura de las otras rondas; no permite estimar una tendencia.")
        else:
            changes = []
            for code in spec["codes"]:
                a = next(r for r in result["frecuencias"] if r["anio"] == first["anio"] and r["codigo"] == code)
                b = next(r for r in result["frecuencias"] if r["anio"] == last["anio"] and r["codigo"] == code)
                changes.append((abs(b["pct_valido"]-a["pct_valido"]), a, b))
            _, a, b = max(changes, key=lambda x: x[0])
            text.append(f"La mayor diferencia absoluta entre {first['anio']} y {last['anio']} corresponde a «{a['respuesta']}»: {a['n']:,}/{a['N_valido']:,} ({a['pct_valido']:.2f}%) frente a {b['n']:,}/{b['N_valido']:,} ({b['pct_valido']:.2f}%), una variación de {b['pct_valido']-a['pct_valido']:+.2f} puntos porcentuales. Los denominadores cambian; esta diferencia es de composición.")
    else:
        text.append(f"En {first['anio']}, la mediana es {first['mediana']:,.2f} y el intervalo intercuartílico [{first['p25']:,.2f}; {first['p75']:,.2f}]; en {last['anio']}, {last['mediana']:,.2f} y [{last['p25']:,.2f}; {last['p75']:,.2f}]. En la última ronda disponible, P05–P95 es [{last['p05']:,.2f}; {last['p95']:,.2f}], frente a extremos [{last['min']:,.2f}; {last['max']:,.2f}]. El contraste entre cuantiles y extremos identifica la amplitud de las colas sin eliminar observaciones.")
        if spec["lower"] == 0 or last["N_ceros"] or last["N_negativos"]:
            text.append(f"En {last['anio']} se conservan {last['N_ceros']:,} ceros ({100*last['N_ceros']/last['N_valido']:.2f}% válido) y {last['N_negativos']:,} negativos. El significado del cero depende de la escala y no sustituye una ausencia.")
    known = [r for r in eligibility if r["N_elegible"]]
    if known:
        weakest = min(known, key=lambda r: r["pct_valido_elegible"])
        text.append(f"La menor cobertura sobre el universo reconstruido ocurre en {weakest['anio']}: {weakest['N_valido_elegible']:,}/{weakest['N_elegible']:,} ({weakest['pct_valido_elegible']:.2f}%). Esto separa falta de respuesta de exclusión por modalidad/disponibilidad; no demuestra que la no respuesta sea aleatoria.")
    text.append(spec["interpretation"] + " " + spec["temporal"])
    if spec["variable"] == "n_res":
        text.append("Las cuatro discrepancias con el libro v2 abarcan media, dispersión y máximo. Véase la investigación específica de versiones; la comparación no identifica su causa.")
    if spec["variable"] == "imp_neto":
        text.append(f"La media de {last['anio']} ({last['media']:,.2f}) supera la mediana ({last['mediana']:,.2f}); una medida central única oculta la asimetría patrimonial. Estas unidades no permiten inferir crecimiento real ni ingresos; el titular incluye al cónyuge y la agregación por personas puede duplicar unidades económicas.")
    if spec["variable"].endswith("flag"):
        text.append("La distribución de esta bandera cuantifica procedencia/calidad del producto; no representa un desenlace de salud ni valida ausencia de fuga temporal.")
    text.append("Resultados sin ponderar: no estimaciones nacionales. No se identifica una trayectoria individual, asociación económica ni efecto causal en este bloque.")
    return "\n\n".join(text)
