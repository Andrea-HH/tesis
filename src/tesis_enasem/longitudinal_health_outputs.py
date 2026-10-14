"""Figuras y narrativa académica derivadas del agregado longitudinal validable."""

from __future__ import annotations
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from .project_paths import RESULTS_DIR
from .longitudinal_health import TRANSITIONS

COLORS = [plt.get_cmap("BrBG")(x) for x in [0.12, 0.32, 0.68, 0.88]]
LABELS = ["2001–2003", "2003–2012*", "2012–2015", "2015–2018*", "2018–2021"]
NOTE = "* Ruptura K: patrones de respuestas no homologados. Muestra sin ponderar; no causalidad."


def make_figures(results: dict) -> list[dict]:
    """Dibuja comparaciones integradas con datos idénticos a las tablas del notebook."""
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    figures = []

    def save(fig: plt.Figure, key: str, title: str, note: str) -> None:
        fig.suptitle(title, fontsize=14, y=0.99)
        fig.text(0.02, 0.01, note, fontsize=9, va="bottom", wrap=True)
        fig.tight_layout(rect=[0, 0.075, 1, 0.96])
        relative = f"figuras/trayectorias_salud__{key}.png"
        fig.savefig(RESULTS_DIR / relative, dpi=210, facecolor="white")
        plt.close(fig)
        figures.append({"clave": key, "titulo": title, "archivo": relative, "nota": note})

    waves = results["rondas"]
    years = [r["ronda"] for r in waves]
    fig, axes = plt.subplots(1, 3, figsize=(9.2, 5.5))
    pct = [r["K"].get("Sí", 0) / (r["K"].get("Sí", 0) + r["K"].get("No", 0)) * 100 for r in waves]
    axes[0].plot(years, pct, "o-", color=COLORS[3])
    axes[0].set_ylabel("% entre K conocida")
    axes[0].set_title("Recepción propia K")
    for key, label, color in [
        ("sintomas_principal", "Nueve completos", COLORS[0]),
        ("sintomas_proveedor", "Producto proveedor", COLORS[3]),
    ]:
        axes[1].plot(years, [r[key]["media"] for r in waves], "o-", label=label, color=color)
    axes[1].legend(fontsize=9)
    axes[1].set_ylabel("Media, síntomas 0–9")
    axes[1].set_title("Síntomas CES-D")
    axes[2].plot(years, [r["soledad"]["media"] * 100 for r in waves], "o-", color=COLORS[0])
    axes[2].set_ylabel("% entre soledad válida")
    axes[2].set_title("Soledad en semana pasada")
    for ax in axes:
        ax.set_xticks(years)
        ax.tick_params(axis="x", rotation=45)
        ax.set_xlabel("Ronda nominal")
    denom = "N 60+ vivos: " + ", ".join(str(r["N_60_vivos"]) for r in waves) + "."
    save(
        fig,
        "evolucion",
        "Seis rondas: composición observada, no cambios de las mismas personas",
        denom
        + " Salud mental: directas válidas; K: estados conocidos. Líneas no interpolan mediciones individuales.",
    )
    fig, ax = plt.subplots(figsize=(12, 6))
    categories = [
        "Análisis principal",
        "Vivo fuera de análisis",
        "Sustituto destino",
        "Sobre fallecido",
        "Ausente",
    ]
    bottom = np.zeros(5)
    for k, category in enumerate(categories):
        counts = [
            next((z["N"] for z in r["seleccion"] if z["grupo"] == category), 0) for r in results["intervalos"]
        ]
        values = np.array(
            [n / r["seguimiento"]["N_origen"] * 100 for n, r in zip(counts, results["intervalos"])]
        )
        ax.bar(LABELS, values, bottom=bottom, label=category, color=plt.get_cmap("BrBG")(k / 5 + 0.08))
        for i, (n, v, b) in enumerate(zip(counts, values, bottom)):
            if v > 5:
                ax.text(i, b + v / 2, f"{n:,}", ha="center", va="center", fontsize=9)
        bottom += values
    ax.set_ylabel("% de cohorte viva 60+ en origen")
    ax.legend(ncol=2, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.1))
    save(
        fig,
        "seguimiento",
        "Seguimiento: grupos mutuamente excluyentes hasta la muestra principal",
        NOTE
        + " N origen: "
        + ", ".join(str(r["seguimiento"]["N_origen"]) for r in results["intervalos"])
        + ".",
    )
    fig, axes = plt.subplots(1, 5, figsize=(16, 4))
    for ax, r, label in zip(axes, results["intervalos"], LABELS):
        matrix = r["matriz_K_principal"]
        values = np.array([z["pct_fila"] or 0 for z in matrix]).reshape(2, 2)
        ax.imshow(values, cmap="BrBG", vmin=0, vmax=100)
        for i in range(2):
            for j in range(2):
                z = matrix[i * 2 + j]
                ax.text(
                    j,
                    i,
                    f"N={z['N']:,}\n{z['pct_fila']:.1f}%",
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="black",
                    bbox={"facecolor": "white", "alpha": 0.7, "edgecolor": "none"},
                )
        ax.set_xticks([0, 1], ["No", "Sí"])
        ax.set_yticks([0, 1], ["No", "Sí"])
        ax.set_xlabel("K destino")
        ax.set_title(label + f"\nN={r['seguimiento']['N_principal']:,}", fontsize=10)
    axes[0].set_ylabel("K origen")
    save(
        fig,
        "matrices",
        "Respuestas K entre quienes tienen nueve síntomas válidos en ambas visitas",
        NOTE
        + " Porcentajes por fila; el notebook conserva también matrices de todos los vivos con K conocida.",
    )
    fig, axes = plt.subplots(1, 5, figsize=(16, 5), sharey=True)
    for ax, r, label in zip(axes, results["intervalos"], LABELS):
        for group, color in zip(r["por_transicion"], COLORS):
            freq = group["cambio"]["frecuencias"]
            ax.step(
                [z["valor"] for z in freq],
                np.cumsum([z["N"] for z in freq]) / group["N"],
                where="post",
                label=f"{group['transicion']} N={group['N']}",
                color=color,
            )
        ax.set_title(label, fontsize=10)
        ax.set_xlim(-9, 9)
        ax.set_xlabel("Cambio en síntomas")
        ax.axvline(0, color="gray", ls=":", lw=1)
        ax.legend(fontsize=8, loc="upper left")
    axes[0].set_ylabel("Proporción acumulada, 0–1")
    save(
        fig,
        "distribuciones",
        "Distribuciones de cambios pareados por respuestas K",
        NOTE + " Cambio = destino − origen; curvas normalizadas por N de cada grupo. No son tasas anuales.",
    )
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 6.2))
    for k, state in enumerate(TRANSITIONS):
        means = [
            next(g for g in r["por_transicion"] if g["transicion"] == state)["cambio"]["media"]
            for r in results["intervalos"]
        ]
        axes[0].plot(range(5), means, "o-", label=state, color=COLORS[k])
    axes[0].set_ylabel("Cambio medio, síntomas")
    axes[0].legend(fontsize=9)
    axes[0].set_title("Cuatro patrones observados")
    for j, spec in enumerate(["Demográfico", "Basal y duración"]):
        rows = [
            next(a for a in r["ajustes"] if a["grupo"] == "No→Sí" and a["especificacion"] == spec)
            for r in results["intervalos"]
        ]
        values = np.array([a["ajustada"] if a["ajustada"] is not None else np.nan for a in rows])
        x = np.arange(5) + (j - 0.5) * 0.1
        errors = np.array(
            [
                [v - a["ic95_inf"] if a["ic95_inf"] is not None else np.nan for v, a in zip(values, rows)],
                [a["ic95_sup"] - v if a["ic95_sup"] is not None else np.nan for v, a in zip(values, rows)],
            ]
        )
        axes[1].errorbar(x, values, yerr=errors, fmt="o", capsize=3, color=COLORS[j * 3], label=spec)
    axes[1].set_title("No→Sí menos No→No: estandarización")
    axes[1].set_ylabel("Diferencia de cambios medios, síntomas")
    axes[1].legend(fontsize=9)
    for ax in axes:
        ax.set_xticks(range(5), LABELS, rotation=30)
        ax.axhline(0, color="gray", ls=":")
    save(
        fig,
        "comparacion",
        "Cinco intervalos: cambios observados y sensibilidad a composición basal",
        NOTE
        + " Ajustes sobre soportes diferentes, no eliminación de sesgo. IC95% condicionales, sin diseño/hogar.",
    )
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 6.2))
    for k, n in enumerate(range(2, 7)):
        rows = [r for r in results["multivisita"]["evolucion_por_mediciones"] if r["N_mediciones"] == n]
        color = plt.get_cmap("BrBG")([0.08, 0.25, 0.38, 0.72, 0.92][k])
        axes[0].plot(
            [r["visita_valida"] for r in rows],
            [r["media"] for r in rows],
            "o-",
            color=color,
            label=f"{n} mediciones, N={rows[0]['N_personas']:,}",
        )
    axes[0].set_xlabel("Orden de visita válida, no año")
    axes[0].set_ylabel("Media de síntomas")
    axes[0].legend(fontsize=9)
    axes[0].set_title("Subgrupos retrospectivos por mediciones")
    classes = [
        "Conteo igual en visitas",
        "No decreciente observado",
        "No creciente observado",
        "Fluctuación observada",
    ]
    bottom = np.zeros(5)
    for k, name in enumerate(classes):
        rows = results["multivisita"]["patrones_por_N_mediciones"]
        values = np.array([r["patrones"].get(name, 0) / r["N_personas"] * 100 for r in rows])
        axes[1].bar(
            [str(r["N_mediciones"]) for r in rows], values, bottom=bottom, color=COLORS[k], label=name
        )
        bottom += values
    axes[1].set_xlabel("Número de mediciones completas")
    axes[1].set_ylabel("% de personas de cada subgrupo")
    axes[1].legend(fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.13))
    axes[1].set_title("Patrones entre visitas observadas")
    save(
        fig,
        "multivisita",
        "Panel incompleto: evolución y patrones según número de mediciones",
        "Cada persona contribuye una trayectoria; grupos definidos retrospectivamente. Diferentes calendarios y selección; no interpolación. Dos mediciones no permiten identificar fluctuación.",
    )
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, var, title in zip(
        axes, ["sexo_grupo", "edad_inicial", "educacion_grupo"], ["Sexo", "Edad al origen", "Escolaridad"]
    ):
        allrows = [
            z
            for r in results["intervalos"]
            for z in r["estratos"]
            if z["estratificador"] == var and z["transicion"] == "No→Sí" and z["estimable"]
        ]
        keys = sorted(set(z["estrato"] for z in allrows))
        for k, key in enumerate(keys):
            points = []
            for i, r in enumerate(results["intervalos"]):
                z = next(
                    (
                        z
                        for z in r["estratos"]
                        if z["estratificador"] == var
                        and z["transicion"] == "No→Sí"
                        and z["estrato"] == key
                        and z["estimable"]
                    ),
                    None,
                )
                if z:
                    points.append((i, z["cambio"]["media"]))
            ax.plot(
                [p[0] for p in points],
                [p[1] for p in points],
                "o-",
                color=plt.get_cmap("BrBG")([0.08, 0.25, 0.38, 0.72, 0.92][k % 5]),
                label=key,
            )
        ax.set_xticks(range(5), LABELS, rotation=45)
        ax.set_title(title)
        ax.axhline(0, color="gray", ls=":")
        ax.legend(fontsize=8)
    axes[0].set_ylabel("Cambio medio, síntomas")
    save(
        fig,
        "sociodemografia",
        "No→Sí: heterogeneidad descriptiva del cambio de síntomas",
        NOTE
        + " Solo estratos N>=30; no comparación causal ni prueba de interacción. Denominadores completos en notebook.",
    )
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 5.8))
    categories = [
        "Análisis principal",
        "Sobre fallecido",
        "Ausente",
        "Sustituto destino",
        "Vivo fuera de análisis",
    ]
    for k, category in enumerate(categories):
        rows = [
            next((s for s in r["seleccion"] if s["grupo"] == category), None) for r in results["intervalos"]
        ]
        color = plt.get_cmap("BrBG")([0.08, 0.25, 0.38, 0.72, 0.92][k])
        axes[0].plot(
            range(5), [z["edad"]["media"] if z else np.nan for z in rows], "o-", color=color, label=category
        )
        axes[1].plot(
            range(5),
            [z["sintomas_iniciales"]["media"] if z else np.nan for z in rows],
            "o-",
            color=color,
            label=category,
        )
    for ax, title in zip(axes, ["Edad media basal, años", "Síntomas basales: media 0–9"]):
        ax.set_ylabel(title)
        ax.set_xticks(range(5), LABELS, rotation=30)
    axes[0].legend(fontsize=9)
    save(
        fig,
        "seleccion",
        "Selección longitudinal: perfiles basales según seguimiento",
        NOTE
        + " Síntomas solo cuando disponibles en directas; N válido difiere del N de seguimiento. No corrección del sesgo.",
    )
    return figures


def conclusions(results: dict) -> list[str]:
    """Redacta evidencia específica desde cifras, evitando hipótesis causal automática."""
    sentences = []
    for r in results["intervalos"]:
        c = r["cambios"]
        g = r["por_transicion"]
        entry = next(z for z in g if z["transicion"] == "No→Sí")
        negative = next(z for z in g if z["transicion"] == "No→No")
        sentences.append(
            f"{r['origen']}–{r['destino']}: N principal={r['seguimiento']['N_principal']:,}, frente a {r['seguimiento']['N_proveedor']:,} con conteo del proveedor. Cambio medio={c['cambio']['media']:+.3f} síntomas; aumenta {c['pct_aumenta']:.1f}%, disminuye {c['pct_disminuye']:.1f}% y permanece igual {c['pct_igual']:.1f}%. No→Sí: N={entry['N']:,}, cambio {entry['cambio']['media']:+.3f}; No→No: N={negative['N']:,}, cambio {negative['cambio']['media']:+.3f}. "
            + (
                "Comparabilidad K condicionada."
                if r["K_comparable_condicionada"]
                else "Ruptura K: son patrones de respuestas, no altas/bajas homologadas."
            )
        )
    first = results["rondas"][0]["sintomas_principal"]
    last = results["rondas"][-1]["sintomas_principal"]
    positive = sum(z["cambios"]["cambio"]["media"] > 0 for z in results["intervalos"])
    sentences.append(
        f"Composición y cambio individual: la media disponible de nueve síntomas completos pasa de {first['media']:.3f} en2001 (N={first['N']:,}) a {last['media']:.3f} en2021 (N={last['N']:,}), mientras {positive} de cinco intervalos tienen cambios pareados medios positivos pequeños. Universos de visitas disponibles y pares conK conocida son diferentes. El descenso agregado no demuestra mejoría de las mismas personas; entrada, selección, supervivencia y criterio de disponibilidad pueden intervenir, sin identificar aquí su contribución causal."
    )
    m = results["multivisita"]
    n = sum(m["patrones_sintomas"].values())
    sentences.append(
        f"Multivisita: {n:,} personas tienen al menos dos mediciones completas; {m['patrones_sintomas'].get('Fluctuación observada', 0):,} muestran cambios de dirección y {m['patrones_sintomas'].get('Conteo igual en visitas', 0):,} el mismo conteo en sus visitas. La media pequeña del cambio no demuestra estabilidad de todas las personas. Las categorías son retrospectivas y el número de oportunidades para fluctuar aumenta con las mediciones."
    )
    sentences.append(
        "Los cambios de síntomas entre patrones K no presentan una ventaja uniforme de No→Sí durante todo el periodo. La estandarización modifica algunas magnitudes y signos; los soportes y la inclusión de síntomas basales cambian el estimando. Regresión a la media, selección y error de medición impiden interpretar el ajuste como efecto causal."
    )
    sentences.append(
        "La comparación transversal del notebook03 y los cambios pareados responden preguntas distintas. Todos los resultados son muestrales sin ponderación validada; intervalos con diferente duración y rupturas no se combinan en una estimación global."
    )
    return sentences
