"""Síntesis académica06 en el mismo informe, preservando bloques previos."""

import json
import re
from hashlib import sha256

from validate_economic_protection import validate

from tesis_enasem.economic_protection import GROUPS, NOTEBOOK, OUTPUT, save_json, verify_inputs
from tesis_enasem.economic_protection_outputs import conclusions, readable_prose, wave
from tesis_enasem.project_paths import INTERIM_DIR, RESULTS_DIR


def export() -> None:
    """Selecciona tablas/figuras sustantivas, no todos los productos auxiliares."""
    from tesis_enasem.release_guard import block_legacy_export
    block_legacy_export()
    validate()
    r = json.loads((OUTPUT / "resultados.json").read_text())
    figures = json.loads((OUTPUT / "figuras.json").read_text())
    products = []
    source = f"**Fuente y procedencia:** ENASEM; [{NOTEBOOK.removesuffix('.ipynb')}](../notebooks/{NOTEBOOK}); [agregados06](../data/interim/cobertura_proteccion_economica/resultados.json); [contrato](../diccionarios/contrato_proteccion_economica.json)."

    def fmt(v):
        return (
            "ND"
            if v is None
            else f"{v:,.2f}"
            if isinstance(v, float)
            else f"{v:,}"
            if isinstance(v, int)
            else str(v).replace("|", "/").replace("\n", " ")
        )

    def table(title, rows, cols, question, note, block):
        products.append(
            {
                "tipo": "tabla",
                "titulo": title,
                "notebook": "notebooks/" + NOTEBOOK,
                "bloque": block,
                "pregunta_aporte": question,
                "fuente": "data/interim/cobertura_proteccion_economica/resultados.json",
            }
        )
        return (
            f"**Cuadro 0. {title}**\n\n**Pregunta y aporte:** {question}\n\n| "
            + " | ".join(label for key, label in cols)
            + " |\n| "
            + " | ".join("---" for _ in cols)
            + " |\n"
            + "\n".join("| " + " | ".join(fmt(x.get(key)) for key, label in cols) + " |" for x in rows)
            + f"\n\n**Nota:** {note}\n\n{source} Bloque {block}.\n\n"
        )

    def image(key, question, reading, block):
        f = next(x for x in figures if x["clave"] == key)
        products.append(
            {
                "tipo": "figura",
                "titulo": f["titulo"],
                "archivo": "resultados/" + f["archivo"],
                "notebook": "notebooks/" + NOTEBOOK,
                "bloque": block,
                "pregunta_aporte": question,
                "sha256": sha256((RESULTS_DIR / f["archivo"]).read_bytes()).hexdigest(),
            }
        )
        return f"**Figura 0. {f['titulo']}**\n\n**Pregunta y aporte:** {question}\n\n![Figura 0: {f['titulo']}]({f['archivo']})\n\n**Interpretación:** {reading}\n\n**Nota:** {f['nota']}\n\n{source} Bloque {block}.\n\n"

    main = [wave(r, y) for y in [2001, 2003, 2012, 2015, 2018, 2021]]
    body = "### Cobertura y monto de protección económica: notebook 06\n\n"
    body += "**Pregunta orientadora de la autora:** ¿qué tanto es consistente la expansión de las pensiones y los apoyos públicos con una reducción de las brechas de cobertura y monto de protección económica de personas mayores, qué grupos siguen sin vía propia identificada y cómo cambia la lectura al considerar muerte y no entrevista? La hipótesis de igualación del acceso sin igualación de monto/suficiencia se somete a evidencia. La expansión política no se mide causalmente ni se atribuyen cambios a reformas no verificadas.\n\n"
    body += "**Universo y estimando:** personas vivas de 60+ por visita; 56,004 observaciones/18,754 personas únicas. Por elección expresa de la autora, el principal utiliza solo entrevistas directas, conservando sustitutos como sensibilidad. K propia no es K del hogar; A propia admite dinero o especie y no equivale a pensión no contributiva homologada. La unión K∨A es afirmativa si cualquiera es afirmativa, negativa solo si ambas son negativas, y ND en el resto. Una unión conocida no garantiza una tipología exclusiva conocida.\n\n"
    body += table(
        "Cobertura propia K y unión K/A: principal de entrevistas directas",
        [{"ronda": z["ronda"], **z["cobertura"][0]} for z in main],
        [
            ("ronda", "Ronda"),
            ("N_elegible", "N directas60+"),
            ("N_KA_conocido", "N unión conocida"),
            ("N_KA_ND_elegible", "N unión ND"),
            ("K_pct", "K % conocido"),
            ("KA_pct", "K o A % conocido"),
        ],
        "Distinguir cobertura de respuestas, recepción y cambios de instrumentos.",
        "N de K conocida y N de unión conocida difieren; para comparar K frente a unión en grupos se usa soporte conjunto en el cuadro siguiente. Sustitutos excluidos por ronda: 604,721,998,776,1,006,1,058. Cifras muestrales no ponderadas. K rompe2003–2012/2015–2018; A2001–2003/2018–2021. Solo2012–2015 mantiene comparabilidad condicionada conjunta de la unión.",
        "1,2,5",
    )
    body += "**Comparabilidad:** las brechas de cada ronda son interpretables para su propio cuestionario. Restarlas entre rondas con ruptura no elimina diferencias de medición, composición o selección. La cobertura de la unión no crece de manera monotónica en los registros; los descensos no son bajas de protección homologadas. Tampoco hay una cobertura monetaria comprobada para todos los apoyos A.\n\n"
    a, b = wave(r, 2018), wave(r, 2021)
    keys = sorted(
        {
            (x["contexto"], x["categoria"])
            for z in [a, b]
            for x in z["tipologia"]
            if x["dimension"] == "General"
        }
    )
    rows = []
    for context, category in keys:
        row = {"contexto": context, "categoria": category}
        for z in [a, b]:
            row[str(z["ronda"])] = sum(
                x["N"]
                for x in z["tipologia"]
                if x["dimension"] == "General" and (x["contexto"], x["categoria"]) == (context, category)
            )
        rows.append(row)
    body += table(
        "Tipología exhaustiva de personas por contexto de pareja, 2018 y 2021",
        rows,
        [("contexto", "Contexto"), ("categoria", "Categoría"), ("2018", "N2018"), ("2021", "N2021")],
        "No perder las combinaciones cónyuge+A y las tres vías ni clasificar la ausencia de pareja como negativa.",
        "Partición disjunta de todos los60+ vivos de cada ronda. Pareja confirmada: 6,205/6,071, con tipología conocida directa5,635/5,572; sin pareja residente:3,893/4,312, con tipología conocida directa3,380/3,748. ND de recepción/contexto entre directas92/104; sustitutos1,006/1,058. Escolaridad, sexo, edad60–64/65–69/70+, localidad y ocupación detallados en notebook/agregados.",
        "3,4",
    )
    body += "**Interpretación de la tipología:** en2021, 538 personas directas con pareja confirmada reportan solo K del cónyuge y negativas propias K/A. Son una parte de las 3,000 personas con ambas negativas propias; no deben confundirse con pensión propia ni ausencia de todo recurso. Otras884 tienen negativas propias K/A y ausencia explícita de pareja residente. El recurso del cónyuge es contextual; no demuestra una transferencia ni disponibilidad efectiva de dinero para la persona focal. A del cónyuge permanece fuera de esta tipología solicitada.\n\n"
    body += image(
        "tipologia",
        "Comparar las combinaciones dentro de contextos con diferente elegibilidad.",
        "Las proporciones se condicionan a tipología conocida en cada contexto; los cambios2018–2021 también están afectados por la ruptura de A. No son altas/bajas homogéneas ni evolución de las mismas personas.",
        "3,4",
    )
    labels = {
        "sexo_grupo": "Sexo",
        "edad_06": "Edad por visita",
        "educacion_grupo": "Escolaridad inicial",
        "localidad_grupo": "Localidad",
        "ocupacion_grupo": "Ocupación",
    }
    rows = [
        dict(
            x,
            dimension=labels[x["dimension"]],
            grupo="Retiro, incapacidad o sin trabajo"
            if x["grupo"] == "Retirado/incapacitado/no trabaja"
            else x["grupo"],
        )
        for x in b["cobertura"]
        if x["dimension"] in GROUPS and x["grupo"] != "Desconocido"
    ]
    body += table(
        "Cobertura K y unión K/A en idéntico soporte por grupo, 2021",
        rows,
        [
            ("dimension", "Variable"),
            ("grupo", "Grupo"),
            ("N_K_A_conocidas", "N ambas conocidas"),
            ("K_soporte_conjunto_pct", "K %"),
            ("KA_soporte_conjunto_pct", "K o A %"),
        ],
        "Comparar el alcance de ampliar la definición de cobertura dentro de cada grupo.",
        "Directas60+, N de ambas respuestas conocidas por grupo. La tasa de la unión lógicamente conocida puede incorporar casos adicionales y se informa aparte. Los grupos ND no se asignan a ninguna categoría conocida; completos en notebook. Localidad a100mil no ruralidad estricta; escolaridad al inicio. Ocupación4 no es jubilación exclusiva.",
        "5,6",
    )
    body += image(
        "cobertura2021",
        "Evaluar heterogeneidad de la unión propia sin sumar porcentajes de K y A.",
        "La unión acerca sexo/localidad, pero separa más edades. No implica una convergencia general ni atribuye el contraste a una política.",
        "5",
    )
    body += image(
        "brechas",
        "Conservar rondas con dirección cambiante o contradicción de la hipótesis.",
        "En2001 la unión tiene mayor brecha por sexo que K; localidad cambia de dirección en rondas intermedias. Las rupturas limitan cualquier tendencia de brechas2001–2021, aunque se compare dentro de ronda.",
        "5,6",
    )
    money = []
    for x in r["montos"]:
        if x["ronda"] == 2021 and (
            x["dimension"] == "General"
            or x["dimension"] == "sexo_grupo"
            or x["dimension"] == "educacion_grupo"
            and x["grupo"] in ["0 años", "≥10 años"]
        ):
            money.append(
                {
                    "via": x["via"],
                    "grupo": x["grupo"],
                    "N_rec": x["N_receptores"],
                    "N_personas": x["N_personas_monto"],
                    "N_eventos": x["N_eventos_monto"],
                    "medianas": f"{x['por_evento']['mediana']:,.0f} / {x['suma_personal_observada_parcial']['mediana']:,.0f}",
                }
            )
    general_monetary = {
        x["via"]: x for x in r["montos"] if x["ronda"] == 2021 and x["dimension"] == "General"
    }
    money_note = " ".join(
        f"{via}: {x['N_eventos']:,} eventos ({x['N_eventos_ND']:,} con monto ND)."
        for via, x in general_monetary.items()
    )
    body += table(
        "Montos nominales por vía y perfil: evento frente a suma parcial personal, 2021",
        money,
        [
            ("via", "Vía propia"),
            ("grupo", "Grupo"),
            ("N_rec", "N receptores"),
            ("N_personas", "N personas con monto"),
            ("N_eventos", "N eventos válidos"),
            ("medianas", "Mediana evento / suma parcial"),
        ],
        "Identificar diferencias monetarias sin confundir eventos y beneficiarios ni afirmar suficiencia.",
        "Pesos mensuales nominales, originales observados; los faltantes no son cero. Las sumas parciales incluyen solo eventos capturados con monto. "
        + money_note
        + " Subconjuntos completos/parciales en agregados. No sumar K+A ni montos de cónyuge con propios. A puede representar especie y no es efectivo separado. Eventos de una persona no son observaciones independientes.",
        "7,8",
    )
    body += image(
        "montos2021",
        "Separar distribución de monto e igualdad de recepción.",
        "K mantiene contrastes de mediana por sexo/escolaridad en2021. A comparte mediana en estos perfiles, lo que no prueba igualdad distributiva. Las escalas son propias de cada vía; no interpretar cocientes como suficiencia real.",
        "7,8",
    )
    body += "**Suficiencia pendiente:** el contrato deja preparada una función parametrizada de deflactación y relación prestación/umbral. No se ejecutó: faltan fuente/base/frecuencia del INPC y referencia mensual confirmadas, además de localidad/unidad cuando corresponda. Esta ruta mide una prestación observada; no clasifica pobreza del hogar o ingreso económico total. Los montos del cónyuge solo se describen como recurso contextual en parejas confirmadas.\n\n"
    rows = []
    bounds = []
    retention = []
    for z in r["seguimiento_principal"]:
        x = z["grupos"][0]
        s = x["estados_sin_K_basal"]
        c = x["cotas"]
        label = f"{z['origen']}–{z['destino']}"
        rows.append(
            {
                "intervalo": label,
                "N": x["N_K_basal_no"],
                "no": s["Sigue con negativa K"],
                "si": s["Recepción K observada en destino"],
                "D": s["Fallecido registrado"],
                "U": s["Ausente; vital desconocido"],
                "ND": s["Vivo; K desconocida o modalidad excluida"],
            }
        )
        for estimand, lo, hi, conditional in [
            (
                "Negativa viva / cohorte",
                c["persistencia_min_pct"],
                c["persistencia_max_pct"],
                c["persistencia_observados_K_pct"],
            ),
            (
                "Fallecimiento registrado / cohorte",
                c["mortalidad"]["limite_inf_pct"],
                c["mortalidad"]["limite_sup_pct"],
                None,
            ),
        ]:
            bounds.append(
                {
                    "intervalo": label,
                    "estimando": estimand,
                    "N": x["N_K_basal_no"],
                    "min": lo,
                    "max": hi,
                    "condicional": conditional if conditional is not None else "No aplica",
                }
            )
        retention.append(
            {
                "intervalo": label,
                "N_original": z["cobertura_basal_cohorte"]["N_KA_conocido"],
                "N_retenido": z["cobertura_basal_retenidos"]["N_KA_conocido"],
                "KA_original": z["cobertura_basal_cohorte"]["KA_pct"],
                "KA_retenido": z["cobertura_basal_retenidos"]["KA_pct"],
                "KA_final": x["KA_destino_mismos_pares_pct"],
            }
        )
    body += table(
        "Estados posteriores de cohortes con negativa propia K directa inicial",
        rows,
        [
            ("intervalo", "Intervalo"),
            ("N", "N K negativa basal"),
            ("no", "Negativa viva"),
            ("si", "K afirmativa viva"),
            ("D", "Fallecido registrado"),
            ("U", "Ausente vitalND"),
            ("ND", "Vivo KND/modalidad"),
        ],
        "Evitar que persistencia entre observados o ausencia sustituyan el universo basal.",
        "Cohorte60+ basal, sin filtrar edad final/supervivencia.2001–2003 sensibilidad;2012–2015 y2018–2021 principales. VentanasK comparables de forma condicionada, no fecha efectiva de inicio. Otro estado no clasificable=0 en estas cohortes. Sustitutos con K válido quedan en sensibilidad. NegativaK no prueba ausenciaA ni protección integral.",
        "10,11",
    )
    body += image(
        "seguimiento",
        "Comparar destinos observados sin imputar recepción después de muerte.",
        "El porcentaje entre sobrevivientes conK conocido describe una selección distinta de toda la cohorte inicial. Muerte, ausencia y KND/modalidad cambian el denominador y permanecen separados.",
        "10,11",
    )
    body += table(
        "Cotas de negativa viva y fallecimiento en la cohorte basal sin K",
        bounds,
        [
            ("intervalo", "Intervalo"),
            ("estimando", "Estimando"),
            ("N", "N basal"),
            ("min", "Mínimo % cohorte"),
            ("max", "Máximo % cohorte"),
            ("condicional", "Negativa % vivos K conocidos"),
        ],
        "Distinguir estimandos condicionados de límites lógicos por cohorte.",
        "Negativa viva: Nno/N a(Nno+ausentes+vivosKND)/N; fallecidos excluidos del extremo superior de recepción/negativa futura. Muerte: D/N a(D+U)/N, suponiendo registros correctos. No IC ni tasas anuales/correcciones. Mortalidad no incluye incertidumbre sobre registros mal clasificados.",
        "11",
    )
    body += table(
        "Selección de cobertura propia: cohorte inicial frente a pares observados",
        retention,
        [
            ("intervalo", "Intervalo"),
            ("N_original", "N unión basal conocida"),
            ("N_retenido", "N par unión conocida"),
            ("KA_original", "Basal cohorte %"),
            ("KA_retenido", "Basal retenidos %"),
            ("KA_final", "Destino mismos pares %"),
        ],
        "Cuantificar diferencia descriptiva por selección de quienes quedan observables.",
        "Todas las tasas de retenidos usan los mismos pares vivos/directos con unión conocida. No corrección de sesgo. Unión conjuntamente comparable solo2012–2015; otros intervalos no son transiciones homologadas deK/A. Duración mensual observada de vivos y reapariciones en notebook; ausencia no prueba vida/muerte.",
        "10,11",
    )
    body += "\n\n".join(conclusions(r)) + "\n\n"
    body += "**Estado validado y límites:** cálculos, exclusividad, conteos, eventos/beneficiarios, soporte y reproducción operacional verificados. Permanecen pendientes homologación definitiva, diseño/ponderación, medición económica completa y suficiencia. Sin modelos opcionales; antes de predecir habría que definir negativa viva o estados múltiples y evitar fuga temporal/selección de sobrevivientes. No se modificaron las bases, notebooks01–05 ni el manuscrito.\n"
    # Mejora espaciado en prosa nueva; rutas de productos permanecen literales.
    body = readable_prose(body)
    path = RESULTS_DIR / "INFORME_GENERAL.md"
    text = path.read_text()
    begin, end = "<!-- BEGIN proteccion_economica_06 -->", "<!-- END proteccion_economica_06 -->"
    ledger = OUTPUT / "informe_contribucion.json"
    if begin in text:
        a = text.index(begin)
        b = text.index(end, a) + len(end)
        if sha256(text[a:b].encode()).hexdigest() != json.loads(ledger.read_text())["sha_bloque"]:
            raise ValueError("Bloque06 editado manualmente")
        text = text[:a] + begin + "\n\n" + body + "\n" + end + text[b:]
    else:
        at = text.index('<a id="seccion-limites"></a>')
        text = text[:at].rstrip() + "\n\n" + begin + "\n\n" + body + "\n" + end + "\n\n" + text[at:]
    text = text.replace(
        "actualizada con los notebooks 03, 04 y 05; sin pregunta definitiva adoptada.",
        "actualizada con los notebooks 03–06. La etapa06 examina la pregunta orientadora de la autora sobre brechas de cobertura/monto; la igualación y la suficiencia permanecen hipótesis por contrastar.",
    )
    text = text.replace(
        "Esta síntesis organiza evidencia para desarrollar la tesis; no adopta una pregunta definitiva, outcome, vulnerabilidad o modelo predictivo.",
        "La autora orienta la etapa06 hacia brechas de cobertura y monto, con selección como sensibilidad. Esto no establece una hipótesis confirmada, efecto causal ni modelo predictivo.",
    )
    tables = {}
    images = {}
    lines = text.splitlines()
    section = sub = 0
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
    save_json(ledger, {"sha_bloque": sha256(text[a:b].encode()).hexdigest(), "productos": products})
    p = INTERIM_DIR / "informe_general_seleccion.json"
    d = json.loads(p.read_text())
    d["productos"] = [x for x in d["productos"] if x.get("notebook") != "notebooks/" + NOTEBOOK] + products
    for x in d["productos"]:
        x["numero"] = (tables if x["tipo"] == "tabla" else images)[x["titulo"]]
    d["cuadros"], d["figuras"] = len(tables), len(images)
    save_json(p, d)
    p = INTERIM_DIR / "indice_informe.json"
    d = json.loads(p.read_text())
    matches = list(re.finditer(r'<a id="seccion-([a-z]+)"></a>', text))
    d["secciones_sintesis"] = {
        m[1]: {"inicio": m.start(), "fin": matches[i + 1].start() if i + 1 < len(matches) else len(text)}
        for i, m in enumerate(matches)
    }
    d["sha_sintesis"] = sha256(text.encode()).hexdigest()
    save_json(p, d)
    verify_inputs()
    print("Síntesis06:", len(tables), "cuadros y", len(images), "figuras totales")


if __name__ == "__main__":
    from tesis_enasem.release_guard import block_legacy_export
    block_legacy_export()
    export()
