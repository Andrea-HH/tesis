"""Figuras y lectura académica06 desde agregados verificados."""

from __future__ import annotations

import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .economic_protection import GROUPS
from .project_paths import RESULTS_DIR


def readable_prose(text: str) -> str:
    """Separa términos/mediciones en prosa sin modificar código ni rutas Markdown."""
    pieces = re.split(r"(\]\([^)]*\)|`[^`]*`)", text)

    def clean(piece: str) -> str:
        piece = re.sub(r"(?<=[A-Za-zÁÉÍÓÚáéíóúñ])(?=\d)", " ", piece)
        piece = re.sub(r"(?<=\d)(?=[A-Za-zÁÉÍÓÚáéíóúñ])", " ", piece)
        return re.sub(r"(?<=[a-záéíóúñ])(?=[KA](?:[^a-z]|$))", " ", piece)

    return "".join(piece if piece.startswith(("](", "`")) else clean(piece) for piece in pieces)


def wave(r: dict, year: int, analysis: str = "principal") -> dict:
    """Recupera una ronda y modalidad, evitando mezclas de universos."""
    return next(x for x in r["rondas"] if x["ronda"] == year and x["analisis"] == analysis)


def conclusions(r: dict) -> list[str]:
    """Interpretación derivada del agregado; la hipótesis no gobierna los resultados."""
    w = wave(r, 2021)
    general = w["cobertura"][0]
    sx = {x["grupo"]: x for x in w["cobertura"] if x["dimension"] == "sexo_grupo"}
    loc = {x["grupo"]: x for x in w["cobertura"] if x["dimension"] == "localidad_grupo"}
    ages = {x["grupo"]: x for x in w["cobertura"] if x["dimension"] == "edad_06"}
    education = {x["grupo"]: x for x in w["cobertura"] if x["dimension"] == "educacion_grupo"}
    occupation = {x["grupo"]: x for x in w["cobertura"] if x["dimension"] == "ocupacion_grupo"}

    def gap(a, b, key):
        return a[key] - b[key]

    money = [x for x in r["montos"] if x["ronda"] == 2021]

    def amount(via, dim, group):
        return next(x for x in money if x["via"] == via and x["dimension"] == dim and x["grupo"] == group)

    allk, alla = amount("K", "General", "Todas"), amount("A", "General", "Todas")
    follow = r["seguimiento_principal"][-1]["grupos"][0]
    c = follow["cotas"]
    initial = r["seguimiento_principal"][-1]
    return [
        readable_prose(x)
        for x in [
            f"**Cobertura y universos.** En2021, {general['N_KA_si']:,}/{general['N_KA_conocido']:,} respuestas directas con uniónK/A conocida reportan al menos una vía propia ({general['KA_pct']:.2f}%). {general['N_KA_no']:,} tienen negativas propiasK/A. Hay {general['N_KA_ND_elegible']:,} directas con uniónND y {general['N_sustituto']:,} sustitutos separados. Una afirmativa basta para conocer la unión aun si la otra vía esND; no basta para clasificar una combinación exclusiva. No equivale a algún ingreso monetario garantizado: A puede ser especie y faltan otras fuentes de protección.",
            f"**Brechas que se estrechan dentro de la ronda.** En2021, sobre el mismo soporte K y A conocido, la diferencia hombres−mujeres pasa de {gap(sx['Hombre'], sx['Mujer'], 'K_soporte_conjunto_pct'):.2f}pp conK a {gap(sx['Hombre'], sx['Mujer'], 'KA_soporte_conjunto_pct'):.2f}pp conK∨A. La diferencia localidad≥100mil−<100mil pasa de {gap(loc['≥100 mil habitantes'], loc['<100 mil habitantes'], 'K_soporte_conjunto_pct'):.2f} a {gap(loc['≥100 mil habitantes'], loc['<100 mil habitantes'], 'KA_soporte_conjunto_pct'):.2f}pp. Se amplía la definición de cobertura en la misma muestra; no se estima efecto de A ni de una reforma. Composición, escolaridad y actividad siguen sin ajustarse.",
            f"**Límites de una igualación general.** En2021, la uniónK/A es {ages['60–64']['KA_pct']:.2f}% entre60–64 (N={ages['60–64']['N_KA_conocido']:,}) y {ages['70+']['KA_pct']:.2f}% entre70+ (N={ages['70+']['N_KA_conocido']:,}); la brecha por edad se amplía respecto deK sola. Las diferencias por escolaridad y ocupación no se resumen con la brecha de sexo/localidad. En2001 la brecha hombres−mujeres de la unión es mayor que la deK; la localidad puede invertir dirección en rondas intermedias. Los cambios de instrumentos y composición impiden afirmar convergencia monotónica2001–2021, incluso comparando brechas.",
            f"**Escolaridad, actividad y ausencia de vía propia identificada.** En2021, en el mismo soporte K/A conocido, quienes tienen0años de escolaridad registran K={education['0 años']['K_soporte_conjunto_pct']:.2f}% y unión={education['0 años']['KA_soporte_conjunto_pct']:.2f}% (N={education['0 años']['N_K_A_conocidas']:,}); con≥10años, K={education['≥10 años']['K_soporte_conjunto_pct']:.2f}% y unión={education['≥10 años']['KA_soporte_conjunto_pct']:.2f}% (N={education['≥10 años']['N_K_A_conocidas']:,}). El gradiente marginal cambia de dirección, no solo de magnitud; edades, cohortes y elegibilidad no ajustadas pueden contribuir. Entre quienes trabajan, unión={occupation['Trabaja']['KA_soporte_conjunto_pct']:.2f}% (N={occupation['Trabaja']['N_K_A_conocidas']:,}), frente a {occupation['Retirado/incapacitado/no trabaja']['KA_soporte_conjunto_pct']:.2f}% en la categoría que agrupa retiro/incapacidad/no trabajo (N={occupation['Retirado/incapacitado/no trabaja']['N_K_A_conocidas']:,}). No es efecto del trabajo ni jubilación homologada. De las3,000negativas propias K/A, {ages['60–64']['N_KA_no']:,} corresponden a60–64 y {ages['70+']['N_KA_no']:,} a70+: conteos por su denominador, no ausencias de toda protección. Conviene comparar composición antes de interpretar estos gradientes como igualación económica.",
            f"**Monto observado y suficiencia pendiente.** En2021 K tiene {allk['N_receptores']:,} receptores directos, {allk['N_personas_monto']:,} con algún monto y {allk['N_eventos_monto']:,}/{allk['N_eventos']:,} eventos con monto; mediana por evento {allk['por_evento']['mediana']:,.0f} pesos. ParaA, {alla['N_receptores']:,} receptores, {alla['N_personas_monto']:,} con algún monto y {alla['N_eventos_monto']:,}/{alla['N_eventos']:,} eventos válidos; mediana {alla['por_evento']['mediana']:,.0f}. La medianaK por evento es {amount('K', 'sexo_grupo', 'Hombre')['por_evento']['mediana']:,.0f} en hombres frente a {amount('K', 'sexo_grupo', 'Mujer')['por_evento']['mediana']:,.0f} en mujeres; por escolaridad, {amount('K', 'educacion_grupo', '0 años')['por_evento']['mediana']:,.0f} con0años frente a {amount('K', 'educacion_grupo', '≥10 años')['por_evento']['mediana']:,.0f} con≥10. A tiene mediana1,550 en esos grupos, pero compartir mediana no equivale a igualdad de distribución. Eventos repetidos por persona no son beneficiarios independientes. No sumarK+A ni declarar suficiencia/pobreza: faltan INPC/umbral confirmados y dinero/especie no separable.",
            f"**Selección y persistencia.** De {follow['N_K_basal_no']:,} personas60+ con negativaK directa en2018, {follow['estados_sin_K_basal']['Sigue con negativa K']:,} conservan negativa observada en2021, {follow['estados_sin_K_basal']['Recepción K observada en destino']:,} reportanK, {follow['estados_sin_K_basal']['Fallecido registrado']:,} tienen registro sobre fallecido, {follow['estados_sin_K_basal']['Ausente; vital desconocido']:,} no aparecen y {follow['estados_sin_K_basal']['Vivo; K desconocida o modalidad excluida']:,} son vivos conK no disponible para el principal. Entre sobrevivientes conK conocido, persistencia={c['persistencia_observados_K_pct']:.2f}%; respecto de toda la cohorte basal, las cotas lógicas de negativa viva en destino son [{c['persistencia_min_pct']:.2f},{c['persistencia_max_pct']:.2f}]%. Son estimandos distintos: la segunda no es una corrección de la primera ni un riesgo competitivo con tiempos. Los fallecidos no reciben un estado pensionario posterior imputado.",
            f"**Sensibilidad de cobertura.** La cobertura basal de la unión en2018 es {initial['cobertura_basal_cohorte']['KA_pct']:.2f}% entre respuestas conocidas de la cohorte y {initial['cobertura_basal_retenidos']['KA_pct']:.2f}% en quienes además tienen unión conocida viva en2021. Esa diferencia describe selección de composición; no reconstruye protección entre fallecidos/ausentes. Las trayectorias deK son condicionadamente comparables en las tres ventanas; la uniónK/A solo en2012–2015, porque A cambia en2001–2003 y2018–2021. 'No→Sí' es inicio observado de respuesta, no fecha efectiva de otorgamiento.",
            "**Aportación y decisión metodológica.** La evidencia respalda estudiar por separado acceso identificado y monto parcial, con tipología exhaustiva de personas, incertidumbre y selección. La hipótesis 'se iguala acceso pero no monto/suficiencia' es parcialmente compatible con los contrastes de sexo/localidad en2021, pero no se sostiene como conclusión general para todos los grupos ni como convergencia temporal validada; la suficiencia todavía no está evaluada. No se ejecutaron modelos opcionales, KM, Cox o IPW. Un modelo futuro requeriría definir si predice negativa viva o un estado multiclase, evitar etiquetar muertos/ausentes como negativas, validar por ventana comparable y mostrar calibración/soporte; no explicaría políticas.",
        ]
    ]


def make_figures(r: dict) -> list[dict]:
    """Figuras compactas BrBG con unidades y denominadores explícitos."""
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    brown, teal = plt.get_cmap("BrBG")(0.12), plt.get_cmap("BrBG")(0.88)
    figures = []

    def save(fig, key, title, note):
        note = readable_prose(note)
        fig.suptitle(title, fontsize=13, y=0.99)
        fig.text(0.02, 0.014, note, fontsize=8, wrap=True)
        fig.tight_layout(rect=[0, 0.09, 1, 0.95])
        filename = f"figuras/proteccion_economica__{key}.png"
        fig.savefig(RESULTS_DIR / filename, dpi=210)
        plt.close(fig)
        figures.append({"clave": key, "titulo": title, "archivo": filename, "nota": note})

    w = wave(r, 2021)
    rows = [x for x in w["cobertura"] if x["dimension"] in GROUPS and x["grupo"] != "Desconocido"]
    fig, ax = plt.subplots(figsize=(9, 9))
    y = np.arange(len(rows))
    ax.hlines(
        y,
        [x["K_soporte_conjunto_pct"] for x in rows],
        [x["KA_soporte_conjunto_pct"] for x in rows],
        color="0.75",
    )
    ax.plot([x["K_soporte_conjunto_pct"] for x in rows], y, "o", color=brown, label="K propia")
    ax.plot([x["KA_soporte_conjunto_pct"] for x in rows], y, "s", color=teal, label="K propia o A propia")
    ax.set_yticks(y, [x["grupo"] + f" · N={x['N_K_A_conocidas']:,}" for x in rows], fontsize=9)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("% entre K y A conocidas en cada grupo")
    ax.legend(loc="lower right")
    save(
        fig,
        "cobertura2021",
        "Cobertura propia K y unión K/A por perfil, 2021",
        "Directas60+. Cada grupo usa idéntico soporte K/A para ambas tasas. Grupos ND en tablas; sin pesos ni causalidad.",
    )
    fig, axes = plt.subplots(1, 2, figsize=(10, 5.8))
    for ax, dim, a, b, title in [
        (axes[0], "sexo_grupo", "Mujer", "Hombre", "Hombres − mujeres"),
        (
            axes[1],
            "localidad_grupo",
            "<100 mil habitantes",
            "≥100 mil habitantes",
            "Localidad ≥100mil − <100mil",
        ),
    ]:
        allwaves = [wave(r, y) for y in [2001, 2003, 2012, 2015, 2018, 2021]]
        for offset, key, c, label in [
            (-0.16, "K_soporte_conjunto_pct_brecha_pp", brown, "K"),
            (0.16, "KA_soporte_conjunto_pct_brecha_pp", teal, "K o A"),
        ]:
            vals = []
            for z in allwaves:
                aa = next(x for x in z["cobertura"] if x["dimension"] == dim and x["grupo"] == a)
                bb = next(x for x in z["cobertura"] if x["dimension"] == dim and x["grupo"] == b)
                field = key.replace("_brecha_pp", "")
                vals.append(bb[field] - aa[field])
            ax.bar(np.arange(6) + offset, vals, width=0.3, color=c, label=label)
        ax.axhline(0, color="0.4", lw=0.7)
        ax.set_title(title)
        ax.set_xticks(np.arange(6), [2001, 2003, 2012, 2015, 2018, 2021], rotation=40)
        ax.set_ylabel("Brecha en puntos porcentuales")
        ax.legend()
    save(
        fig,
        "brechas",
        "Brechas dentro de cada ronda: K frente a unión K/A",
        "Directas60+, mismo soporte K/A por grupo. No serie homogénea: K rompe2003–2012/2015–2018; A2001–2003/2018–2021.",
    )
    fig, axes = plt.subplots(2, 2, figsize=(11, 10))
    for j, year in enumerate([2018, 2021]):
        for i, context in enumerate(["Pareja confirmada", "Sin pareja residente"]):
            data = [
                x
                for x in wave(r, year)["tipologia"]
                if x["dimension"] == "General"
                and x["contexto"] == context
                and x["pct_contexto_conocido"] is not None
            ]
            data = sorted(data, key=lambda x: x["categoria"])
            labels = [
                x["categoria"]
                .replace("No reporta ninguna de las vías identificadas", "Negativas de las tres vías")
                .replace("Negativas propias K y A; sin pareja residente", "Negativas propias K/A")
                .replace("K del cónyuge", "K cónyuge")
                for x in data
            ]
            ax = axes[i, j]
            ax.barh(
                labels,
                [x["pct_contexto_conocido"] for x in data],
                color=plt.get_cmap("BrBG")(np.linspace(0.12, 0.88, len(data))),
            )
            for n, x in enumerate(data):
                ax.text(x["pct_contexto_conocido"] + 0.4, n, str(x["N"]), va="center", fontsize=10)
            ax.set_xlim(0, 55)
            ax.invert_yaxis()
            ax.set_title(f"{year} · {context}\nN conocido={data[0]['N_conocido_contexto']:,}")
            ax.set_xlabel("% del contexto con tipología conocida", fontsize=11)
            ax.tick_params(axis="y", labelsize=11)
    save(
        fig,
        "tipologia",
        "Combinaciones de vías identificadas, con y sin pareja residente",
        "Directas60+. N y % por contexto, no composición de todos los60+. ND, pareja indeterminada y sustitutos separados en tabla.",
    )
    fig, axes = plt.subplots(1, 2, figsize=(10, 6))
    for ax, block, c in [(axes[0], "K", brown), (axes[1], "A", teal)]:
        data = [
            x
            for x in r["montos"]
            if x["ronda"] == 2021
            and x["via"] == block
            and x["dimension"] in ["sexo_grupo", "educacion_grupo"]
            and x["grupo"] != "Desconocido"
        ]
        y = np.arange(len(data))
        med = np.array([x["por_evento"]["mediana"] for x in data])
        lo = np.array([x["por_evento"]["q25"] for x in data])
        hi = np.array([x["por_evento"]["q75"] for x in data])
        ax.errorbar(med, y, xerr=[med - lo, hi - med], fmt="o", color=c, capsize=4)
        ax.set_yticks(y, [x["grupo"] + f" · n={x['N_eventos_monto']:,}" for x in data], fontsize=8)
        ax.invert_yaxis()
        ax.set_title(block + " propia · mediana y Q25–Q75")
        ax.set_xlabel("Pesos nominales mensuales por evento")
        ax.set_xlim(left=0)
    save(
        fig,
        "montos2021",
        "Montos por evento según sexo y escolaridad, 2021",
        "Directas60+, eventos originales con monto. n=eventos válidos, no beneficiarios; escalas monetarias por vía. Sin deflactación ni umbral.",
    )
    fig, ax = plt.subplots(figsize=(9, 6))
    states = [
        "Sigue con negativa K",
        "Recepción K observada en destino",
        "Fallecido registrado",
        "Ausente; vital desconocido",
        "Vivo; K desconocida o modalidad excluida",
    ]
    data = [z["grupos"][0] for z in r["seguimiento_principal"]]
    labels = [
        f"{z['origen']}–{z['destino']}\nN={x['N_K_basal_no']:,}"
        for z, x in zip(r["seguimiento_principal"], data)
    ]
    bottom = np.zeros(3)
    for state, color in zip(states, plt.get_cmap("BrBG")(np.linspace(0.12, 0.88, 5))):
        vals = np.array([x["estados_sin_K_basal"][state] / x["N_K_basal_no"] * 100 for x in data])
        ax.bar(labels, vals, bottom=bottom, color=color, label=state)
        for j, (v, base) in enumerate(zip(vals, bottom)):
            if v > 4:
                ax.text(j, base + v / 2, f"{v:.1f}%", ha="center", va="center", fontsize=9)
        bottom += vals
    ax.set_ylim(0, 100)
    ax.set_ylabel("% de cohorte basal con negativa K directa")
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=2)
    save(
        fig,
        "seguimiento",
        "Destino de quienes reportan negativa propia K al inicio",
        "Estados observados disjuntos. ND/modalidad viva no es ausencia; fallecimiento registrado no es mortalidad completa. Sin tiempos de evento.",
    )
    return figures
