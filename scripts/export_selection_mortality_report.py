"""Síntesis selectiva05 dentro del informe acumulativo, sin informes paralelos."""

import json, re
from hashlib import sha256
from tesis_enasem.selection_mortality import OUTPUT, verify_inputs
from tesis_enasem.selection_mortality_outputs import conclusions
from tesis_enasem.project_paths import RESULTS_DIR, INTERIM_DIR


def export() -> None:
    """Inserta evidencia validada y actualiza índice/numeración sin reescribir resultados previos."""
    verify_inputs()
    r = json.loads((OUTPUT / "resultados.json").read_text())
    figures = json.loads((OUTPUT / "figuras.json").read_text())
    products = []
    source = "**Fuente y procedencia:** ENASEM; [05_PENSIONES_MORTALIDAD_SELECCION](../notebooks/05_PENSIONES_MORTALIDAD_SELECCION.ipynb); [agregados](../data/interim/pensiones_mortalidad_seleccion/resultados.json)."

    def fmt(x):
        return "ND" if x is None else f"{x:.3f}" if isinstance(x, float) else str(x).replace("|", "\\|")

    def table(title, rows, cols, objective, note, block):
        products.append(
            {
                "tipo": "tabla",
                "titulo": title,
                "notebook": "notebooks/05_PENSIONES_MORTALIDAD_SELECCION.ipynb",
                "bloque": block,
                "pregunta_aporte": objective,
                "fuente": "data/interim/pensiones_mortalidad_seleccion/resultados.json",
            }
        )
        return (
            f"**Cuadro 0. {title}**\n\n**Objetivo y aporte:** {objective}\n\n| "
            + " | ".join(label for key, label in cols)
            + " |\n| "
            + " | ".join("---" for c in cols)
            + " |\n"
            + "\n".join("| " + " | ".join(fmt(row.get(key)) for key, label in cols) + " |" for row in rows)
            + "\n\n**Nota:** "
            + note
            + "\n\n"
            + source
            + f" Bloque {block}.\n\n"
        )

    def image(key, question, reading, block):
        f = next(a for a in figures if a["clave"] == key)
        products.append(
            {
                "tipo": "figura",
                "titulo": f["titulo"],
                "archivo": "resultados/" + f["archivo"],
                "notebook": "notebooks/05_PENSIONES_MORTALIDAD_SELECCION.ipynb",
                "bloque": block,
                "pregunta_aporte": question,
                "sha256": sha256((RESULTS_DIR / f["archivo"]).read_bytes()).hexdigest(),
            }
        )
        return f"**Figura 0. {f['titulo']}**\n\n**Objetivo y aporte:** {question}\n\n![Figura 0: {f['titulo']}]({f['archivo']})\n\n**Interpretación:** {reading}\n\n**Nota:** {f['nota']}\n\n{source} Bloque {block}.\n\n"

    body = "### Pensiones, mortalidad registrada y selección multidimensional: notebook 05\n\n"
    body += "**Pregunta exploratoria:** ¿cómo se relaciona K inicial con el registro posterior de fallecimiento y quién permanece disponible para estudiar cada dimensión? Se integran los cinco intervalos y las seis rondas, sin población balanceada ni estimación causal global.\n\n"
    body += "**Auditoría vital:** fallecido y tipent5 concuerdan en el maestro; ello no es verificación externa de todas las muertes. Ausencias mantienen estado vital desconocido. Una persona con registro sobre fallecido reaparece viva: se conserva y evalúa como inconsistencia. No se identificó localmente el Master Follow-up completo de no entrevistas; el producto oficial requiere acceso registrado. [Documentación oficial histórica2018](https://www.mhasweb.org/resources/DOCUMENTS/2018/MHAS_Master_Follow_up_File_2001_2003_2012_2015_2018.pdf) describe información adicional de no entrevista, motivo de sustituto y estado vital, sin certificar aquí versión2021.\n\n"
    rows = []
    for z in r["intervalos"]:
        yes = next(a for a in z["mortalidad_K"] if a["K_inicial"] == "Sí")
        no = next(a for a in z["mortalidad_K"] if a["K_inicial"] == "No")
        s = next(a for a in z["ajustes_K"] if a["especificacion"] == "Demográfico")
        rows.append(
            {
                "intervalo": f"{z['origen']}–{z['destino']}",
                "N_si": yes["N"],
                "N_no": no["N"],
                "D_si": yes["D"],
                "D_no": no["D"],
                "pct_si": yes["registrado_pct"],
                "pct_no": no["registrado_pct"],
                "delta": z["contraste_K"]["diferencia_registrada_pp"],
                "cruda_soporte": s["cruda_mismo_soporte_pp"],
                "N_soporte": s["N_soporte"],
                "ajustada": s["ajustada_pp"],
                "IC": f"[{s['IC_inf_pp']:.2f}, {s['IC_sup_pp']:.2f}]",
            }
        )
    body += table(
        "K inicial y registro sobre fallecido: comparación de cinco cohortes",
        rows,
        [
            ("intervalo", "Intervalo"),
            ("N_si", "N K sí"),
            ("N_no", "N K no"),
            ("D_si", "D K sí"),
            ("D_no", "D K no"),
            ("pct_si", "% D K sí"),
            ("pct_no", "% D K no"),
            ("delta", "Bruta cohorte pp"),
            ("cruda_soporte", "Cruda soporte pp"),
            ("N_soporte", "N soporte"),
            ("ajustada", "Demográfica pp"),
            ("IC", "IC95% demográfico"),
        ],
        "Distinguir asociación registrada y cambios al considerar composición basal.",
        "D/N de cohorte basal no es mortalidad completa ni tasa anual. ND inicial separado en notebook. Ajuste sexo×edad×escolaridad; cada comparación cruda/ajustada del mismo soporte se conserva en agregado. IC sin diseño/hogar. K no implica contributividad.",
        "3–4",
    )
    body += image(
        "mortalidad_K",
        "Comparar todos los periodos sin equiparar duraciones.",
        "La dirección ajustada no es uniforme. Más registro de muerte puede combinar composición y captura; no demuestra efecto pensionario. Los nueve años2003–2012 no se anualizan.",
        "3–4",
    )
    rows = []
    for z in r["intervalos"]:
        for a in z["ajustes_perfiles"]:
            rows.append(
                {
                    "intervalo": f"{z['origen']}–{z['destino']}",
                    "variable": a["variable"],
                    "contraste": a["contraste"],
                    "N": a["N_soporte"],
                    "cruda": a["cruda_mismo_soporte_pp"],
                    "ajustada": a["ajustada_pp"],
                    "IC": f"[{a['IC_inf_pp']:.2f}, {a['IC_sup_pp']:.2f}]"
                    if a["ajustada_pp"] is not None
                    else "Soporte insuficiente",
                }
            )
    body += table(
        "Perfiles basales y registro de fallecimiento: diferencias estandarizadas",
        rows,
        [
            ("intervalo", "Intervalo"),
            ("variable", "Indicador basal"),
            ("contraste", "Comparación"),
            ("N", "N soporte"),
            ("cruda", "Cruda mismo soporte pp"),
            ("ajustada", "Demográfica pp"),
            ("IC", "IC95% condicional"),
        ],
        "Examinar salud, memoria y funcionalidad iniciales considerando edad/sexo/escolaridad.",
        "≥2 enfermedades, ≥5 síntomas completos, ≥1 ABVD y aprendizaje≤4 son comparaciones seleccionadas; memoria no es punto de corte clínico. CES-D no diagnóstico. Basales válidos y soportes cambian por indicador.",
        "5",
    )
    body += "**Supervivencia actuarial:** no Kaplan–Meier ni Cox: fechas verificadas de muerte y censura no disponibles, y ausentes no necesariamente vivos. Datos agrupados/censura por intervalos podrían evaluarse tras resolver seguimiento vital y fechas de notificación; no se asignaron eventos a rondas nominales como si fueran fechas exactas.\n\n"
    rows = [
        {"intervalo": f"{z['origen']}–{z['destino']}", **z["limites_diferencia_mortalidad"]}
        for z in r["intervalos"]
    ]
    body += table(
        "Sensibilidad a estado vital desconocido: límites de diferencia K sí−no",
        rows,
        [("intervalo", "Intervalo"), ("inf_pp", "Límite inferior pp"), ("sup_pp", "Límite superior pp")],
        "Mostrar qué parte de la asociación no queda identificada por los registros disponibles.",
        "Límites lógicos: D/N a(D+U)/N por grupo, suponiendo registros correctos y cada ausente vivo o muerto. No IC, ajuste ni corrección de otros errores.",
        "7",
    )
    rows = [
        {
            k: a[k]
            for k in [
                "variable",
                "dimension",
                "N_dos_o_mas",
                "N_tres_o_mas",
                "N_personas_pares_consecutivos",
                "N_personas_pares_K",
            ]
        }
        for a in r["multivisita"]
    ]
    body += table(
        "Universos longitudinales propios de cada indicador",
        rows,
        [
            ("variable", "Indicador"),
            ("dimension", "Dimensión"),
            ("N_dos_o_mas", "≥2 mediciones"),
            ("N_tres_o_mas", "≥3 mediciones"),
            ("N_personas_pares_consecutivos", "Personas con par consecutivo"),
            ("N_personas_pares_K", "Personas con par y K"),
        ],
        "Evitar utilizar la misma muestra para salud, cognición, funcionalidad y economía.",
        "Personas únicas, no suma de pares. CES-D nueve completos. Multimedición60+ por visita; pares mantienen destino de origen60+. Serial2021 cuenta disponibilidad, no comparabilidad con tarea previa.",
        "8–9,13",
    )
    body += image(
        "disponibilidad",
        "Separar elegibilidad, seguimiento y medición de cada indicador.",
        "Las variables que admiten sustituto tienen cobertura distinta de indicadores directos. Ceros por ausencia de instrumento no son pérdidas ni valores cero del indicador.",
        "8–9",
    )
    body += "**Reconciliación04:** se reproducen13,570personas con pares de salud mental/K y14,069con≥2mediciones de síntomas:13,560comunes,10solo pares y509solo multimedición. Las10 tienen edad final<60 registrada, que se conserva; no son exclusiones corregidas automáticamente. No interpretar diferencia neta como pérdidas.\n\n"
    body += image(
        "composicion",
        "Comparar disponibilidad por ronda y subconjuntos retrospectivos multimedición.",
        "La composición del subconjunto repetido difiere del universo disponible. Sus tendencias no separan edad, cohorte y periodo ni describen una población fija representativa.",
        "11,13",
    )
    rows = []
    for z in r["intervalos"]:
        for a in z["indicadores"]:
            if a["variable"] not in ["n_enf", "n_sint_depr", "recuerdo1", "n_aivd"]:
                continue
            c = a["estandarizacion_composicion_basal"]
            rows.append(
                {
                    "intervalo": f"{z['origen']}–{z['destino']}",
                    "variable": a["variable"],
                    "N_target": c["N_target"],
                    "N_ret": c["N_retenido"],
                    "basal": c["media_basal_target"],
                    "cruda": c["media_retenida_cruda_mismo_soporte"],
                    "estandarizada": c["media_retenida_estandarizada_basal"],
                }
            )
    body += table(
        "Composición basal de retenidos frente al target de soporte común",
        rows,
        [
            ("intervalo", "Intervalo"),
            ("variable", "Indicador"),
            ("N_target", "N target basal"),
            ("N_ret", "N retenido"),
            ("basal", "Media target"),
            ("cruda", "Media retenida cruda"),
            ("estandarizada", "Media retenida estandarizada"),
        ],
        "Cuantificar composición observable sin inventar salud posterior de fallecidos.",
        "Todos son valores BASALES observados; target sexo×edad×escolaridad dentro de celdas con≥20retenidos. No ICiid de muestras anidadas. Reponderación no explica causalmente la tendencia posterior.",
        "10,15",
    )
    body += image(
        "sensibilidad",
        "Evaluar cuán sensibles pueden ser los cambios a mediciones no disponibles entre vivos.",
        "Escenarios0/±1unidad desde basal cambian medias según cantidad no medida; son supuestos, no datos imputados ni estimaciones corregidas. Muertos y ausentes de vital desconocido quedan fuera de esos escenarios.",
        "16",
    )
    body += "**Comparabilidad adicional:** [documentación cognitiva oficial](https://www.mhasweb.org/resources/DOCUMENTS/Constructed_Imputed/MHAS_2018_2021_Cognitive_Function_Measures_Scoring_and_Classification.pdf) indica restas3 desde20 en2021 en lugar de restas7 desde100. Se bloquea el cambio2018–2021 de serial7; nombre/rango común no demuestra equivalencia. Orientación falta2001. Aprendizaje/evocación conservan flags y sensibilidad no imputada. No TICS ni índice nuevo.\n\n"
    body += "**Economía:** se estudia cobertura y selección de patrimonio, ocupación y estado conyugal. No cambios monetarios reales por unidades/deflactación pendientes ni diferencias numéricas de categorías. Stock compartido no es ingreso. A y cónyuge se analizan como ramas complementarias de universo propio.\n\n"
    body += "\n\n".join(conclusions(r)) + "\n\n"
    body += "**Estado y próximos pasos:** ejecución y reconciliación operacional verificadas; interpretación exploratoria condicionada. IPW no implementada por incertidumbre vital y selección de modalidad/medición; pesos, extremos, ESS y balance no se declararon validados. Requiere seguimiento completo, historial basal, positividad y dependencia por persona/hogar. No reconstruir síntomas después de muerte. Aportación: distinguir condiciones basales, supervivencia documentada y proceso de medición multidimensional antes de elegir enfoque definitivo.\n"
    path = RESULTS_DIR / "INFORME_GENERAL.md"
    text = path.read_text().replace(
        "**Actualización:** 13 de octubre de 2026.", "**Actualización:** 14 de octubre de 2026."
    )
    begin = "<!-- BEGIN mortalidad_seleccion_05 -->"
    end = "<!-- END mortalidad_seleccion_05 -->"
    ledger = OUTPUT / "informe_contribucion.json"
    if begin in text:
        a = text.index(begin)
        b = text.index(end, a) + len(end)
        if sha256(text[a:b].encode()).hexdigest() != json.loads(ledger.read_text())["sha_bloque"]:
            raise ValueError("Bloque05 editado manualmente")
        text = text[:a] + begin + "\n\n" + body + "\n" + end + text[b:]
    else:
        at = text.index('<a id="seccion-interpretacion"></a>')
        text = text[:at].rstrip() + "\n\n" + begin + "\n\n" + body + "\n" + end + "\n\n" + text[at:]
    text=text.replace("actualizada con los notebooks 03 y 04;", "actualizada con los notebooks 03, 04 y 05;")
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
        h = re.match(r"\*\*Cuadro \d+\. (.*)\*\*$", line)
        if h:
            tables[h[1]] = len(tables) + 1
            lines[i] = f"**Cuadro {tables[h[1]]}. {h[1]}**"
        h = re.match(r"\*\*Figura \d+\. (.*)\*\*$", line)
        if h:
            images[h[1]] = len(images) + 1
            lines[i] = f"**Figura {images[h[1]]}. {h[1]}**"
        h = re.match(r"!\[Figura \d+: (.*?)\]\((.*?)\)", line)
        if h:
            lines[i] = f"![Figura {images[h[1]]}: {h[1]}]({h[2]})"
    text = "\n".join(lines) + "\n"
    path.write_text(text)
    a = text.index(begin)
    b = text.index(end, a) + len(end)
    ledger.write_text(
        json.dumps(
            {"sha_bloque": sha256(text[a:b].encode()).hexdigest(), "productos": products},
            ensure_ascii=False,
            indent=2,
        )
    )
    sp = INTERIM_DIR / "informe_general_seleccion.json"
    d = json.loads(sp.read_text())
    d["productos"] = [
        p for p in d["productos"] if p.get("notebook") != "notebooks/05_PENSIONES_MORTALIDAD_SELECCION.ipynb"
    ] + products
    for p in d["productos"]:
        p["numero"] = (tables if p["tipo"] == "tabla" else images)[p["titulo"]]
    d["cuadros"] = len(tables)
    d["figuras"] = len(images)
    sp.write_text(json.dumps(d, ensure_ascii=False, indent=2))
    ip = INTERIM_DIR / "indice_informe.json"
    d = json.loads(ip.read_text())
    m = list(re.finditer(r'<a id="seccion-([a-z]+)"></a>', text))
    d["secciones_sintesis"] = {
        x[1]: {"inicio": x.start(), "fin": m[i + 1].start() if i + 1 < len(m) else len(text)}
        for i, x in enumerate(m)
    }
    d["sha_sintesis"] = sha256(text.encode()).hexdigest()
    ip.write_text(json.dumps(d, ensure_ascii=False, indent=2))
    verify_inputs()
    print("Síntesis05:", len(tables), "cuadros y", len(images), "figuras totales")


if __name__ == "__main__":
    export()
