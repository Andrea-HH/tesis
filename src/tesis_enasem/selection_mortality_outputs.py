"""Visualización integrada de registros de muerte y selección multidimensional."""

from __future__ import annotations
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from .selection_mortality import DIMENSIONS
from .project_paths import RESULTS_DIR

BROWN = plt.get_cmap("BrBG")(0.12)
TEAL = plt.get_cmap("BrBG")(0.88)


def make_figures(r: dict) -> list[dict]:
    """Figuras compactas con denominadores provenientes del mismo agregado."""
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    figures = []
    labels = [f"{z['origen']}–{z['destino']}" for z in r["intervalos"]]

    def save(fig, key, title, note):
        fig.suptitle(title, fontsize=14, y=0.99)
        fig.text(0.02, 0.01, note, fontsize=8, wrap=True)
        fig.tight_layout(rect=[0, 0.09, 1, 0.94])
        name = f"figuras/seleccion_mortalidad__{key}.png"
        fig.savefig(RESULTS_DIR / name, dpi=210)
        plt.close(fig)
        figures.append({"clave": key, "titulo": title, "archivo": name, "nota": note})

    fig, axes = plt.subplots(1, 2, figsize=(9, 5.8))
    for state, color in [("Sí", BROWN), ("No", TEAL)]:
        vals = [next(a for a in z["mortalidad_K"] if a["K_inicial"] == state) for z in r["intervalos"]]
        axes[0].plot(
            range(5), [a["registrado_pct"] for a in vals], "o-", color=color, label=f"K inicial {state}"
        )
    axes[0].set_ylabel("% de cohorte de cada K inicial")
    axes[0].set_title("Registro sobre fallecido")
    axes[0].legend(fontsize=9)
    for j, spec in enumerate(["Demográfico", "Más enfermedades"]):
        vals = [next(a for a in z["ajustes_K"] if a["especificacion"] == spec) for z in r["intervalos"]]
        y = np.array([a["ajustada_pp"] for a in vals])
        err = np.array(
            [[b - a["IC_inf_pp"] for a, b in zip(vals, y)], [a["IC_sup_pp"] - b for a, b in zip(vals, y)]]
        )
        axes[1].errorbar(
            np.arange(5) + (j - 0.5) * 0.08,
            y,
            yerr=err,
            fmt="o",
            capsize=3,
            color=[BROWN, TEAL][j],
            label=spec,
        )
    axes[1].axhline(0, color="gray", ls=":")
    axes[1].set_ylabel("K sí − K no, puntos porcentuales")
    axes[1].set_title("Composición basal común")
    axes[1].legend(fontsize=9)
    for ax in axes:
        ax.set_xticks(range(5), labels, rotation=40)
    save(
        fig,
        "mortalidad_K",
        "Pensión inicial y fallecimiento registrado en los cinco intervalos",
        "No mortalidad completa ni tasas anuales. IC condicionales sin diseño/hogar; soportes en cuadros. N cohortes: "
        + ", ".join(str(z["N_cohorte"]) for z in r["intervalos"])
        + ".",
    )
    fig, ax = plt.subplots(figsize=(8.8, 6))
    bottom = np.zeros(5)
    classes = ["Vivo directo", "Vivo sustituto", "Sobre fallecido registrado", "Ausente, vital desconocido"]
    for k, category in enumerate(classes):
        counts = np.array([z["estado_vital"].get(category, 0) for z in r["intervalos"]])
        pct = counts / np.array([z["N_cohorte"] for z in r["intervalos"]]) * 100
        ax.bar(
            labels, pct, bottom=bottom, color=plt.get_cmap("BrBG")([0.12, 0.35, 0.7, 0.9][k]), label=category
        )
        for i, (n, v, b) in enumerate(zip(counts, pct, bottom)):
            if v > 4:
                ax.text(i, b + v / 2, f"{n:,}", ha="center", va="center", fontsize=9)
        bottom += pct
    ax.set_ylabel("% de cohorte viva60+ en origen")
    ax.legend(fontsize=9, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.09))
    save(
        fig,
        "seguimiento",
        "Seguimiento de cinco cohortes: muerte, modalidad y ausencia",
        "Estados disjuntos; ausencia no indica muerte. La inconsistencia fallecido→vivo se señala sin corregir fuentes.",
    )
    variables = [v for vals in DIMENSIONS.values() for v in vals]
    values = np.array(
        [
            [
                next(x for x in z["indicadores"] if x["variable"] == v)["seleccion"]["N_valido_ambas"]
                / z["N_cohorte"]
                * 100
                for z in r["intervalos"]
            ]
            for v in variables
        ]
    )
    fig, ax = plt.subplots(figsize=(9, 8))
    im = ax.imshow(values, cmap="BrBG", vmin=0, vmax=100, aspect="auto")
    for i in range(len(variables)):
        for j in range(5):
            ax.text(
                j,
                i,
                f"{values[i, j]:.1f}",
                ha="center",
                va="center",
                fontsize=9,
                color="black",
                bbox={"facecolor": "white", "alpha": 0.6, "edgecolor": "none"},
            )
    ax.set_xticks(range(5), labels, rotation=30)
    ax.set_yticks(range(len(variables)), variables)
    fig.colorbar(im, ax=ax, label="% de cohorte inicial con par válido")
    save(
        fig,
        "disponibilidad",
        "Disponibilidad longitudinal por indicador y periodo",
        "Denominador: cohorte viva60+ inicial de cada columna. CES-D nueve completos. Cobertura no certifica comparabilidad; serial2018–2021 solo disponibilidad, patrimonio sin cambios reales.",
    )
    fig, axes = plt.subplots(2, 2, figsize=(9, 7))
    for ax, v in zip(axes.flat, ["n_enf", "n_sint_depr", "recuerdo1", "n_aivd"]):
        data = [next(a for a in z["indicadores"] if a["variable"] == v) for z in r["rondas"]]
        ax.plot(
            [z["ronda"] for z in r["rondas"]],
            [a["estadisticas"]["media"] for a in data],
            "o-",
            color=BROWN,
            label="Disponibles por visita",
        )
        row = next(x for x in r["multivisita"] if x["variable"] == v)
        curves = row["composicion_subgrupo_multimedicion"]
        ax.plot(
            [x["ronda"] for x in curves],
            [x["media"] for x in curves],
            "s--",
            color=TEAL,
            label="Subgrupo ≥2 mediciones",
        )
        ax.set_title(v)
        ax.set_xlabel("Ronda")
        ax.set_ylabel("Media en escala del indicador")
        ax.legend(fontsize=8)
        ax.tick_params(axis="x", rotation=35)
    save(
        fig,
        "composicion",
        "Composición por visita frente a subconjuntos observados repetidamente",
        "Subgrupo definido retrospectivamente, no población basal. N específicos de indicador/ronda en notebook; no causalidad ni equivalencia de calendarios.",
    )
    fig, axes = plt.subplots(1, 2, figsize=(9, 6))
    for ax, v in zip(axes, ["recuerdo1", "n_aivd"]):
        before = []
        retained = []
        standard = []
        for z in r["intervalos"]:
            a = next(a for a in z["indicadores"] if a["variable"] == v)["estandarizacion_composicion_basal"]
            before.append(a["media_basal_target"])
            retained.append(a["media_retenida_cruda_mismo_soporte"])
            standard.append(a["media_retenida_estandarizada_basal"])
        for y, label, c in [
            (before, "Target basal", BROWN),
            (retained, "Retenidos, cruda", TEAL),
            (standard, "Retenidos, estandarizada", plt.get_cmap("BrBG")(0.3)),
        ]:
            ax.plot(range(5), y, "o-", label=label, color=c)
        ax.set_xticks(range(5), labels, rotation=40)
        ax.set_title(v)
        ax.set_ylabel("Media del indicador BASAL")
        ax.legend(fontsize=8)
    save(
        fig,
        "seleccion_basal",
        "Selección: diferencias basales y estandarización de composición",
        "Valores basales observados, no desenlaces después de muerte. Soporte común sexo×edad×escolaridad; no corrección definitiva de sesgo. N específicos en agregado.",
    )
    fig, axes = plt.subplots(1, 2, figsize=(9, 6))
    for ax, v in zip(axes, ["n_sint_depr", "recuerdo1"]):
        for offset, color in zip([-1, 0, 1], [BROWN, plt.get_cmap("BrBG")(0.35), TEAL]):
            vals = []
            for z in r["intervalos"]:
                a = next(a for a in z["indicadores"] if a["variable"] == v)
                vals.append(
                    next(
                        s["cambio_escenario"]
                        for s in a["escenarios_vivos"]
                        if s["supuesto_cambio_no_medido"] == offset
                    )
                )
            ax.plot(range(5), vals, "o-", color=color, label=f"No medidos: Δ={offset:+d}, acotado")
        ax.set_xticks(range(5), labels, rotation=40)
        ax.set_title(v)
        ax.set_ylabel("Cambio medio bajo supuesto")
        ax.legend(fontsize=8)
        ax.axhline(0, color="gray", ls=":")
    save(
        fig,
        "sensibilidad",
        "Sensibilidades de mediciones faltantes entre vivos confirmados",
        "Escenarios agregados, no imputaciones: ±1/0 unidades de escala desde valor basal, acotadas al dominio. Nunca después de fallecimiento. No representan ausentes con vital desconocido.",
    )
    return figures


def conclusions(r: dict) -> list[str]:
    """Interpretaciones con cifras y restricciones visibles, sin extrapolación causal."""
    out = []
    for z in r["intervalos"]:
        a = next(a for a in z["mortalidad_K"] if a["K_inicial"] == "Sí")
        b = next(a for a in z["mortalidad_K"] if a["K_inicial"] == "No")
        s = next(a for a in z["ajustes_K"] if a["especificacion"] == "Demográfico")
        out.append(
            f"{z['origen']}–{z['destino']}: registros sobre fallecidos {a['D']:,}/{a['N']:,} con K inicial afirmativa ({a['registrado_pct']:.2f}%) y {b['D']:,}/{b['N']:,} con negativa ({b['registrado_pct']:.2f}%). Diferencia bruta {z['contraste_K']['diferencia_registrada_pp']:+.2f}pp; demográfica {s['ajustada_pp']:+.2f}pp en soporte N={s['N_soporte']:,}. No riesgo completo, tasa anual ni efecto causal."
        )
    out.append(
        "Los ajustes cambian magnitud y en algunos periodos dirección de la asociación K–registro de fallecimiento. Especificaciones agregan variables basales por separado, no un modelo con todo; los soportes distintos impiden atribuir diferencias entre especificaciones únicamente al ajuste."
    )
    out.append(
        "Las pruebas cognitivas y los indicadores directos pierden disponibilidad por modalidad además de mortalidad y ausencia. Indicadores que admiten sustituto conservan un universo más amplio; las diferencias de cobertura no equivalen a diferencias de calidad ni permiten sumar muestras."
    )
    out.append(
        "La estandarización de valores basales permite cuantificar cambios de composición observados dentro de soporte. No recupera salud posterior de quienes murieron ni identifica cuánto de una tendencia temporal explica la mortalidad."
    )
    out.append(
        "Sin estado vital de todos los ausentes y fechas de defunción verificadas no se implementan Kaplan–Meier, Cox ni IPW. Los límites lógicos y escenarios son sensibilidades, no estimaciones corregidas. Serial2018–2021 bloqueado por cambio de tarea; patrimonio sin cambios reales por homologación monetaria pendiente."
    )
    for variable, label in [("recuerdo1", "Aprendizaje verbal"), ("n_aivd", "AIVD")]:
        waves = [next(a for a in z["indicadores"] if a["variable"] == variable) for z in r["rondas"]]
        first, last = waves[0]["estadisticas"], waves[-1]["estadisticas"]
        pairs = [
            next(a for a in z["indicadores"] if a["variable"] == variable)["cambios"] for z in r["intervalos"]
        ]
        descriptions = "; ".join(
            f"{z['origen']}–{z['destino']}: {c['delta']['media']:+.3f} (N={c['N']:,})"
            for z, c in zip(r["intervalos"], pairs)
        )
        out.append(
            f"{label}: media disponible {first['media']:.3f} en2001 (N={first['N']:,}) y {last['media']:.3f} en2021 (N={last['N']:,}); cambios pareados del indicador, sin exigirK: {descriptions}. Poblaciones disponibles y pares son distintos; no sumar cambios como trayectoria completa ni atribuir divergencia exclusivamente a mortalidad. Cognición conserva incertidumbre de imputación/instrumento; AIVD mide limitaciones declaradas."
        )
    return out
