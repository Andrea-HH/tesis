"""Incorpora síntesis longitudinal selectiva al único informe general."""

from hashlib import sha256
import json
import re
from tesis_enasem.longitudinal_health import OUTPUT, verify_inputs
from tesis_enasem.longitudinal_health_outputs import conclusions
from tesis_enasem.project_paths import RESULTS_DIR, INTERIM_DIR


def export() -> None:
    """Inserta tablas y figuras desde agregados, manteniendo los resultados anteriores."""
    from tesis_enasem.release_guard import block_legacy_export
    block_legacy_export()
    verify_inputs(allow_report=True)
    r = json.loads((OUTPUT / "resultados.json").read_text())
    figures = json.loads((OUTPUT / "figuras.json").read_text())
    products = []
    source = "**Fuente y procedencia:** ENASEM; [04_TRAYECTORIAS_PENSIONES_SALUD](../notebooks/04_TRAYECTORIAS_PENSIONES_SALUD.ipynb); [agregados completos](../data/interim/trayectorias_pensiones_salud/resultados.json)."

    def fmt(v):
        if v is None:
            return "ND"
        if isinstance(v, float):
            return f"{v:.3f}"
        return str(v).replace("|", "\\|")

    def table(title, rows, columns, question, note, block):
        products.append(
            {
                "tipo": "tabla",
                "titulo": title,
                "notebook": "notebooks/04_TRAYECTORIAS_PENSIONES_SALUD.ipynb",
                "bloque": block,
                "pregunta_aporte": question,
                "fuente": "data/interim/trayectorias_pensiones_salud/resultados.json",
            }
        )
        return (
            f"**Cuadro 0. {title}**\n\n**Objetivo y aporte:** {question}\n\n| "
            + " | ".join(b for a, b in columns)
            + " |\n| "
            + " | ".join("---" for _ in columns)
            + " |\n"
            + "\n".join("| " + " | ".join(fmt(row.get(key)) for key, label in columns) + " |" for row in rows)
            + "\n\n**Nota:** "
            + note
            + "\n\n"
            + source
            + f" Bloque {block}.\n"
        )

    def figure(key, question, interpretation, block):
        f = next(x for x in figures if x["clave"] == key)
        products.append(
            {
                "tipo": "figura",
                "titulo": f["titulo"],
                "notebook": "notebooks/04_TRAYECTORIAS_PENSIONES_SALUD.ipynb",
                "bloque": block,
                "archivo": "resultados/" + f["archivo"],
                "pregunta_aporte": question,
                "sha256": sha256((RESULTS_DIR / f["archivo"]).read_bytes()).hexdigest(),
            }
        )
        return f"**Figura 0. {f['titulo']}**\n\n**Objetivo y aporte:** {question}\n\n![Figura 0: {f['titulo']}]({f['archivo']})\n\n**Interpretación:** {interpretation}\n\n**Nota:** {f['nota']}\n\n{source} Bloque {block}.\n"

    block = "### Seguimiento conjunto de pensiones y salud mental: notebook 04\n\n"
    block += "**Pregunta exploratoria:** ¿cómo se relacionan los cambios de síntomas de las mismas personas con sus respuestas K registradas durante 2001–2021? Se integran población por ronda, los cinco pares consecutivos y trayectorias de múltiples visitas. No se adopta pregunta definitiva, causalidad ni predicción.\n\n"
    block += (
        "**Contrato CES-D y estado:** comparación operacional condicionada de productos construidos. Se verificaron nueve componentes0/1: deprimido, esfuerzo, sueño intranquilo, feliz, solo, disfrute de vida, triste, cansado y energía; los tres componentes positivos se invierten. En casos completos, la suma coincide exactamente con n_sint_depr en todas las rondas. La auditoría60+ detecta "
        + str(sum(a["N_score_valido_componentes_incompletos"] for a in r["auditoria_CESD"]))
        + " conteos válidos del proveedor con componentes incompletos: el análisis principal exige nueve completos y la sensibilidad conserva el proveedor. No se rellenan faltantes ni se altera la base. Literalidad/números de preguntas brutas e invariancia psicométrica no quedan certificados por esta reconciliación; documentación actual ejemplifica2024. [Contrato y evidencia](../diccionarios/contrato_longitudinal_salud_mental.json).\n\n"
    )
    block += "**Pensión:** comparabilidad condicionada2001–2003,2012–2015,2018–2021; rupturas2003–2012 y2015–2018. Sí/sí y no/no solo describen extremos; no/sí no identifica fecha o primer acceso. En rupturas son patrones de respuestas, no altas/bajas homologadas.\n\n"
    block += (
        figure(
            "evolucion",
            "Contextualizar las seis rondas antes del seguimiento de IDs.",
            "Las medias y recepciones por visita corresponden a poblaciones disponibles diferentes; entradas, supervivencia y modalidad cambian composición. No son evolución de una cohorte fija.",
            "4–5",
        )
        + "\n"
    )
    rows = []
    for z in r["intervalos"]:
        f = z["seguimiento"]
        rows.append(
            {
                "intervalo": f"{z['origen']}–{z['destino']}",
                "origen": f["N_origen"],
                "presente": f["N_presente"],
                "fallecido": f["N_sobre_fallecido"],
                "ausente": f["N_ausente"],
                "retorno": f["N_reaparece"],
                "proveedor": f["N_proveedor"],
                "principal": f["N_principal"],
                "pct_principal": f["N_principal"] / f["N_origen"] * 100,
            }
        )
    block += (
        table(
            "Seguimiento de cohortes60+ y selección de pares de salud mental",
            rows,
            [
                ("intervalo", "Intervalo"),
                ("origen", "Cohorte"),
                ("presente", "Presentes"),
                ("fallecido", "Sobre fallecido"),
                ("ausente", "Ausentes"),
                ("retorno", "Retorno posterior"),
                ("proveedor", "Pares proveedor"),
                ("principal", "Pares completos"),
                ("pct_principal", "% cohorte completo"),
            ],
            "Distinguir seguimiento de elegibilidad y criterio de salud.",
            "Presentes incluye sobre fallecido; retornos son subconjunto de ausentes. Pares completos: directas, nueve ítems y K conocidos en ambas. Las restricciones superpuestas no se suman. Retorno tras2021 no observable.",
            "6",
        )
        + "\n"
    )
    block += "Los conteos de la auditoría anterior se reproducen con el proveedor; la reducción del principal deriva de la nueva restricción de componentes completos. Una persona registrada sobre fallecido en2012 reaparece viva después: anomalía preservada. No se interpreta toda ausencia como muerte o pérdida definitiva.\n\n"
    rows = []
    for z in r["intervalos"]:
        c = z["cambios"]
        rows.append(
            {
                "intervalo": f"{z['origen']}–{z['destino']}",
                "meses": z["duracion_analitica"]["mediana"],
                "N": c["cambio"]["N"],
                "inicio": c["inicio"]["media"],
                "final": c["final"]["media"],
                "cambio": c["cambio"]["media"],
                "IC": f"[{c['cambio']['ic95_inf']:.3f}, {c['cambio']['ic95_sup']:.3f}]",
                "aumenta": c["pct_aumenta"],
                "disminuye": c["pct_disminuye"],
                "igual": c["pct_igual"],
                "K": "Condicionada" if z["K_comparable_condicionada"] else "Ruptura",
            }
        )
    block += (
        table(
            "Cinco intervalos: cambios pareados de síntomas y comparabilidad",
            rows,
            [
                ("intervalo", "Intervalo"),
                ("meses", "Mediana meses"),
                ("N", "N pares"),
                ("inicio", "Media inicial"),
                ("final", "Media final"),
                ("cambio", "Cambio medio"),
                ("IC", "IC95%"),
                ("aumenta", "% aumenta"),
                ("disminuye", "% disminuye"),
                ("igual", "% igual"),
                ("K", "Comparabilidad K"),
            ],
            "Comparar magnitud y distribución del cambio de las mismas personas.",
            "Cambio=destino−origen, síntomas0–9. ICt del cambio por persona dentro de cada intervalo; sin diseño/hogar/ponderación. Duraciones distintas, no tasas anuales. Igual conteo no garantiza mismos componentes.",
            "7–9",
        )
        + "\n"
    )
    rows = [
        {
            "intervalo": f"{z['origen']}–{z['destino']}",
            "patron": a["transicion"],
            "N": a["N"],
            "media": a["cambio"]["media"],
            "mediana": a["cambio"]["mediana"],
            "IC": f"[{a['cambio']['ic95_inf']:.3f}, {a['cambio']['ic95_sup']:.3f}]",
        }
        for z in r["intervalos"]
        for a in z["por_transicion"]
    ]
    block += (
        table(
            "Respuestas K y cambios medios de síntomas en cinco intervalos",
            rows,
            [
                ("intervalo", "Intervalo"),
                ("patron", "Patrón K"),
                ("N", "N pares"),
                ("media", "Cambio medio"),
                ("mediana", "Cambio mediano"),
                ("IC", "IC95% del cambio"),
            ],
            "Identificar diferencias entre respuestas económicas observadas sin asumir efecto de recepción.",
            "Los cuatro patrones suman N principal de cada intervalo. Diferencias entre medias no equivalen a efectos. Matrices con % por fila y total están en notebook; rupturas2003–2012 y2015–2018 no homologadas.",
            "8–10",
        )
        + "\n"
    )
    rows = []
    for z in r["intervalos"]:
        for a in z["ajustes"]:
            if a["grupo"] == "No→Sí":
                rows.append(
                    {
                        "intervalo": f"{z['origen']}–{z['destino']}",
                        "ajuste": a["especificacion"],
                        "soporte": a["N_soporte"],
                        "fuera": a["N_fuera_soporte"],
                        "cruda": a["cruda_mismo_soporte"],
                        "ajustada": a["ajustada"],
                        "IC": f"[{a['ic95_inf']:.3f}, {a['ic95_sup']:.3f}]"
                        if a["ajustada"] is not None
                        else "Soporte insuficiente",
                    }
                )
    block += (
        table(
            "No→Sí menos No→No: cambios según composición inicial y soporte",
            rows,
            [
                ("intervalo", "Intervalo"),
                ("ajuste", "Especificación"),
                ("soporte", "N soporte"),
                ("fuera", "Fuera soporte"),
                ("cruda", "Cruda mismo soporte"),
                ("ajustada", "Estandarizada"),
                ("IC", "IC95% condicional"),
            ],
            "Examinar sensibilidad de diferencias longitudinales a composición, síntomas iniciales y duración.",
            "Demográfico: sexo×edad×escolaridad. Basal/duración añade nivel de síntomas y tiempo. Celdas>=10porrama, total>=30. N fuera soporte entre casos completos basales; faltantes adicionales en agregado. No ajustes por variables finales.",
            "17",
        )
        + "\n"
    )
    block += (
        figure(
            "comparacion",
            "Integrar los cinco periodos y visibilizar la sensibilidad del contraste.",
            "No existe una ventaja uniforme de No→Sí en todo el periodo. Considerar síntomas basales y duración puede cambiar signo y soporte; no elimina regresión a la media ni error de medición. La diferencia cruda se compara con ajustada en su mismo soporte.",
            "10,17,20",
        )
        + "\n"
    )
    visits = r["multivisita"]["conteos_visitas"]
    rows = []
    for n in range(2, 7):
        row = {"visitas": n}
        for key in ["N_visitas", "N_sintomas", "N_conjuntas"]:
            row[key] = next(z["N_personas"] for z in visits if z["tipo"] == key and z["visitas"] == n)
        rows.append(row)
    block += (
        table(
            "Personas según visitas observadas y mediciones válidas60+",
            rows,
            [
                ("visitas", "Número"),
                ("N_visitas", "Visitas vivas observadas"),
                ("N_sintomas", "Síntomas completos"),
                ("N_conjuntas", "Síntomas y K conocidos"),
            ],
            "Mostrar que observación y disponibilidad analítica no son lo mismo, sin imponer panel balanceado.",
            "Cada columna cuenta personas por su propio número de visitas. Personas con0/1 mediciones se conservan en cobertura. No sumar columnas ni pares como personas distintas. Universo por visita60+, no cohorte basal única.",
            "3,11–14",
        )
        + "\n"
    )
    retrospective = []
    for key in [
        "Afirmativas repetidas",
        "Negativas repetidas",
        "Cambio único registrado",
        "Múltiples cambios registrados",
        "Incluye desconocidos",
    ]:
        groups = [g for g in r["multivisita"]["relacion_K_sintomas"] if g["patron_K"] == key]
        n = sum(g["N_personas"] for g in groups)
        retrospective.append(
            {
                "patron": key,
                "N": n,
                "cambio": sum(g["N_personas"] * g["cambio_primera_ultima"]["media"] for g in groups) / n,
            }
        )
    block += (
        table(
            "Secuencias K retrospectivas y cambio primera–última medición",
            retrospective,
            [
                ("patron", "Patrón de respuestas"),
                ("N", "N personas con dos o más mediciones"),
                ("cambio", "Cambio medio primera–última"),
            ],
            "Describir evolución conjunta multivisita sin asumir estabilidad real de recepción.",
            "Horizontes y número de visitas distintos. Grupos definidos con todo el seguimiento, no conocidos al inicio; cruzan rupturas K. Descripción retrospectiva, no efecto ni estimación homogénea del periodo. Desagregación por número de mediciones y huecos en notebook.",
            "12–14",
        )
        + "\n"
    )
    block += (
        figure(
            "multivisita",
            "Comprender repetición, estabilidad de conteo y fluctuación en panel incompleto.",
            "La oportunidad de detectar fluctuación aumenta con las visitas. Subgrupos definidos retrospectivamente no son cohortes representativas ni exposiciones conocidas al inicio. No se interpolan años sin entrevista.",
            "11–14",
        )
        + "\n"
    )
    block += "\n\n".join(conclusions(r)) + "\n\n"
    block += "**Selección y diferencias sociodemográficas:** se comparan sexo, edad inicial, escolaridad, localidad y cuartil patrimonial basal dentro de patrones K. Patrimonio es stock persona/cónyuge, no ingreso ni riqueza real homologada entre rondas. Las diferencias pequeñas y grupos conN<30 se conservan como descriptivos; no se prueban interacciones.\n\n"
    demographic = []
    for z in r["intervalos"]:
        row = {"intervalo": f"{z['origen']}–{z['destino']}"}
        for key, label in [("Hombre", "H"), ("Mujer", "M")]:
            a = next(
                a
                for a in z["estratos"]
                if a["transicion"] == "No→Sí" and a["estratificador"] == "sexo_grupo" and a["estrato"] == key
            )
            row["N_" + label] = a["N"]
            row["cambio_" + label] = a["cambio"]["media"]
        demographic.append(row)
    block += (
        table(
            "No→Sí: cambios de síntomas por sexo en los cinco periodos",
            demographic,
            [
                ("intervalo", "Intervalo"),
                ("N_H", "N hombres"),
                ("cambio_H", "Cambio hombres"),
                ("N_M", "N mujeres"),
                ("cambio_M", "Cambio mujeres"),
            ],
            "Examinar si la heterogeneidad por sexo tiene una dirección repetida.",
            "Cambio medio de síntomas, no diferencia de efectos. Los signos varían por periodo; ruptura2003–2012 y2015–2018. IC y demás patrones/estratos en notebook.",
            "16",
        )
        + "\n"
    )
    older = next(
        a
        for a in r["intervalos"][2]["estratos"]
        if a["transicion"] == "No→Sí" and a["estratificador"] == "edad_inicial" and a["estrato"] == "80+"
    )
    block += f"En2012–2015, No→Sí de80+ registra cambio medio{older['cambio']['media']:+.3f} síntomas (N={older['N']}); no permite separar edad, cohorte y periodo. Escolaridad no presenta un gradiente uniforme en los cinco intervalos; conservar inconsistencias es parte del resultado.\n\n"
    baseline = []
    for z in r["intervalos"]:
        for category in ["Análisis principal", "Sobre fallecido", "Sustituto destino"]:
            a = next(a for a in z["seleccion"] if a["grupo"] == category)
            baseline.append(
                {
                    "intervalo": f"{z['origen']}–{z['destino']}",
                    "seguimiento": category,
                    "N_grupo": a["N"],
                    "edad": a["edad"]["media"],
                    "N_sintomas": a["sintomas_iniciales"]["N"],
                    "sintomas": a["sintomas_iniciales"]["media"],
                }
            )
    block += (
        table(
            "Selección: edad y síntomas iniciales según seguimiento",
            baseline,
            [
                ("intervalo", "Intervalo"),
                ("seguimiento", "Seguimiento"),
                ("N_grupo", "N grupo"),
                ("edad", "Edad media basal"),
                ("N_sintomas", "N síntomas válidos basales"),
                ("sintomas", "Media síntomas basales"),
            ],
            "Identificar selección por mortalidad y modalidad frente a quienes completan el análisis.",
            "Síntomas basales aquí: proveedor válido en directa para describir cohorte; no exactamente criterio principal de nueve componentes. Muertes registradas no abarcan todas las muertes de ausentes.",
            "18",
        )
        + "\n"
    )
    block += (
        figure(
            "seleccion",
            "Evaluar cómo se diferencia la muestra analítica de otros estados de seguimiento.",
            "Edad y síntomas basales difieren según seguimiento; las personas observadas repetidamente son seleccionadas. Cada media utiliza su N válido, especialmente síntomas disponibles solo en directas. No se corrige selección con esta figura.",
            "18",
        )
        + "\n"
    )
    solitude = []
    for z in r["intervalos"]:
        a = next(a for a in z["soledad"] if a["transicion_K"] == "No→Sí")
        b = next(a for a in z["soledad"] if a["transicion_K"] == "No→No")
        c = a["cambio_pareado"]
        solitude.append(
            {
                "intervalo": f"{z['origen']}–{z['destino']}",
                "N_entrada": a["N"],
                "pp_entrada": a["cambio_pp"],
                "IC": f"[{c['ic95_inf'] * 100:.2f}, {c['ic95_sup'] * 100:.2f}]",
                "N_no": b["N"],
                "pp_no": b["cambio_pp"],
            }
        )
    block += (
        table(
            "Soledad: cambio pareado entre respuestas No→Sí y No→No K",
            solitude,
            [
                ("intervalo", "Intervalo"),
                ("N_entrada", "N No→Sí"),
                ("pp_entrada", "Cambio soledad pp No→Sí"),
                ("IC", "IC95% pareado No→Sí"),
                ("N_no", "N No→No"),
                ("pp_no", "Cambio soledad pp No→No"),
            ],
            "Examinar si soledad comparte el patrón agregado de síntomas.",
            "Cambio de proporción a partir de diferencia individual0/±1; ICt pareado, no dos proporciones independientes. Denominadores propios. Rupturas K no homologadas; IC puntuales sin diseño/hogar.",
            "15",
        )
        + "\n"
    )
    block += "En No→Sí, la soledad registrada aumenta en los cinco intervalos, aunque el cambio medio de síntomas no tiene esa dirección uniforme. Son estimaciones puntuales; sus IC permiten aumentos pequeños, ausencia de diferencia o disminución en varios periodos. Esto describe un componente específico del mismo conteo y no un efecto de recibir pensión.\n\n"
    block += "**Soledad:** matrices por patrón K y secuencias multivisita usan denominadores propios. Persistencia significa respuesta repetida en visitas, no experiencia continua; es componente CES-D. Los cálculos completos y sensibilidades a proveedor, edad, anomalías y soporte permanecen en notebook04.\n\n"
    block += (
        "**Límites y potencial:** "
        + str(r["metodologia"]["N_pares_principales"])
        + " pares corresponden a "
        + str(r["metodologia"]["N_personas_distintas_pares"])
        + " personas, "
        + str(r["metodologia"]["N_personas_mas_un_intervalo"])
        + " contribuyen más de un intervalo. No poolingiid ni estimación global de periodos incompatibles. Seguir personas distingue cambio individual de composición y permite estudiar selección actuarial; no demuestra causalidad. Próximas etapas: cerrar concordancia bruta, medición, dependencia y diseño antes de inferencia confirmatoria. No TICS ni modelos predictivos.\n"
    )
    text = (RESULTS_DIR / "INFORME_GENERAL.md").read_text()
    marker = "<!-- BEGIN salud_longitudinal_04 -->"
    end = "<!-- END salud_longitudinal_04 -->"
    ledger_path = OUTPUT / "informe_contribucion.json"
    if marker in text:
        a = text.index(marker)
        b = text.index(end, a) + len(end)
        old = text[a:b]
        if sha256(old.encode()).hexdigest() != json.loads(ledger_path.read_text())["sha_bloque"]:
            raise ValueError("Bloque04 editado manualmente; conservar")
        text = text[:a] + marker + "\n\n" + block + "\n" + end + text[b:]
    else:
        position = text.index('<a id="seccion-interpretacion"></a>')
        text = (
            text[:position].rstrip()
            + "\n\n"
            + marker
            + "\n\n"
            + block
            + "\n"
            + end
            + "\n\n"
            + text[position:]
        )
    text = text.replace(
        "Síntesis académica acumulativa, actualizada con la ampliación del notebook 03;",
        "Síntesis académica acumulativa, actualizada con los notebooks 03 y 04;",
    )
    text = text.replace(
        "No se ha ejecutado ese seguimiento de salud ni se adopta una pregunta definitiva.",
        "El seguimiento descriptivo de salud se presenta en el notebook04; no se adopta una pregunta definitiva.",
    )
    text = text.replace(
        "El seguimiento conjunto de salud y pensiones queda como etapa posterior, no ejecutada aquí.",
        "El seguimiento conjunto se amplía en notebook04; este bloque conserva las comparaciones transversales del notebook03.",
    )
    # Renumeración de presentación, sin alterar resultados o títulos originales.
    lines = text.splitlines()
    tables = {}
    images = {}
    section = 0
    sub = 0
    for i, line in enumerate(lines):
        h = re.match(r"## (\d+)\. ", line)
        if h:
            section = int(h[1])
            sub = 0
        elif line.startswith("### "):
            sub += 1
            lines[i] = f"### {section}.{sub} " + re.sub(r"^\d+\.\d+\s+", "", line[4:])
        q = re.match(r"\*\*Cuadro \d+\. (.*)\*\*$", line)
        if q:
            tables[q[1]] = len(tables) + 1
            lines[i] = f"**Cuadro {tables[q[1]]}. {q[1]}**"
        q = re.match(r"\*\*Figura \d+\. (.*)\*\*$", line)
        if q:
            images[q[1]] = len(images) + 1
            lines[i] = f"**Figura {images[q[1]]}. {q[1]}**"
        q = re.match(r"!\[Figura \d+: (.*?)\]\((.*?)\)", line)
        if q:
            lines[i] = f"![Figura {images[q[1]]}: {q[1]}]({q[2]})"
    text = "\n".join(lines) + "\n"
    (RESULTS_DIR / "INFORME_GENERAL.md").write_text(text)
    a = text.index(marker)
    b = text.index(end, a) + len(end)
    ledger_path.write_text(
        json.dumps(
            {"sha_bloque": sha256(text[a:b].encode()).hexdigest(), "productos": products},
            ensure_ascii=False,
            indent=2,
        )
    )
    selection_path = INTERIM_DIR / "informe_general_seleccion.json"
    selection = json.loads(selection_path.read_text())
    selection["productos"] = [
        p
        for p in selection["productos"]
        if p.get("notebook") != "notebooks/04_TRAYECTORIAS_PENSIONES_SALUD.ipynb"
    ] + products
    for p in selection["productos"]:
        p["numero"] = (tables if p["tipo"] == "tabla" else images)[p["titulo"]]
    selection["cuadros"] = len(tables)
    selection["figuras"] = len(images)
    selection_path.write_text(json.dumps(selection, ensure_ascii=False, indent=2))
    index_path = INTERIM_DIR / "indice_informe.json"
    index = json.loads(index_path.read_text())
    matches = list(re.finditer(r'<a id="seccion-([a-z]+)"></a>', text))
    index["secciones_sintesis"] = {
        m[1]: {"inicio": m.start(), "fin": matches[n + 1].start() if n + 1 < len(matches) else len(text)}
        for n, m in enumerate(matches)
    }
    index["sha_sintesis"] = sha256(text.encode()).hexdigest()
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2))
    # Dos frases históricas ahora obsoletas se actualizan; guardar nueva huella del bloque03.
    oldledger = INTERIM_DIR / "pensiones_salud/informe_contribucion.json"
    l = json.loads(oldledger.read_text())
    for key in l["bloques"]:
        start = f"<!-- BEGIN {key} -->"
        stop = f"<!-- END {key} -->"
        a = text.index(start)
        b = text.index(stop, a) + len(stop)
        l["bloques"][key] = sha256(text[a:b].encode()).hexdigest()
    oldledger.write_text(json.dumps(l, ensure_ascii=False, indent=2))
    verify_inputs(allow_report=True)
    print("Síntesis04 incorporada:", len(tables), "cuadros y", len(images), "figuras totales.")


if __name__ == "__main__":
    from tesis_enasem.release_guard import block_legacy_export
    block_legacy_export()
    export()
