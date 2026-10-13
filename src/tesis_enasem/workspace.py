"""Consulta y consolidación de evidencia ya calculada; no ejecuta análisis estadístico."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from .project_paths import PROJECT_ROOT, INTERIM_DIR, RESULTS_DIR, RESEARCH_DIR, project_path, route_map

SECTIONS = [
    ("fuentes", "Descripción de ENASEM y fuentes"),
    ("integracion", "Procedimiento de integración e identificadores"),
    ("validacion", "Validaciones de las bases y titularidad"),
    ("poblacion", "Descripción de la población: universo completo CP1"),
    ("pensiones", "Pensiones, titularidad y apoyos: definiciones y versiones"),
    ("univariado", "Resultados univariados: fuentes independientes y muestra 60+"),
    ("bivariado", "Resultados bivariados centrados en pensiones"),
    ("trivariado", "Resultados trivariados y complementarios"),
    ("longitudinal", "Trayectorias longitudinales y estados de observación"),
    ("hallazgos", "Hallazgos principales y relaciones complementarias"),
    ("limites", "Limitaciones metodológicas y comparabilidad"),
    ("preguntas", "Posibles preguntas de investigación: ninguna adoptada"),
    ("pendientes", "Pendientes, avances y evidencia de migración"),
]


def load_json(relative: str) -> object:
    """Carga un agregado o diccionario usando rutas centralizadas."""
    return json.loads(project_path(relative).read_text())


def source_text(relative: str) -> str:
    """Recupera una nota conservada íntegramente del respaldo documental."""
    return load_json("data/interim/textos_analisis.json")[relative]["texto"]


def source_anchor(relative: str) -> str:
    return "origen-" + hashlib.sha256(relative.encode()).hexdigest()[:12]


def convert_links(text: str, origin: str) -> str:
    """Inserta figuras junto al resultado y evita enlaces a docs/reports históricos."""
    def convert(match: re.Match) -> str:
        label, target = match.group(1), match.group(2)
        if target.startswith(("http:", "https:", "#", "mailto:")):
            return match.group(0)
        clean = target.split("#")[0]
        path = Path(clean)
        absolute = path if path.is_absolute() else (PROJECT_ROOT / origin).parent / path
        import os
        normalized = Path(os.path.normpath(absolute))
        try:
            key = normalized.relative_to(PROJECT_ROOT).as_posix()
        except ValueError:
            # Algunas notas antiguas usaban rutas relativas desde otra carpeta.
            key = next((name for name in route_map()["archivos"]
                        if clean.lstrip("./") == name), "")
            if not key:
                candidate = PROJECT_ROOT / clean.lstrip("./")
                if candidate.is_file():
                    return f"[{label}]({os.path.relpath(candidate, RESULTS_DIR)})"
                return match.group(0)
        if key in route_map()["archivos"]:
            destination = project_path(key)
            if "textos_virtuales" in destination.parts:
                navigation = {
                    'docs/HANDOFF.md':'../investigacion/notas/historial_metodologico.json',
                    'docs/pensiones/README.md':'#seccion-pensiones',
                    'docs/eda/COBERTURA_VARIABLES.md':'../diccionarios/cobertura_variables.json',
                    'docs/eda/proteccion_economica/README.md':'#seccion-pensiones',
                    'docs/eda/pensiones_exploratorio_v1/HALLAZGOS.md':'#seccion-hallazgos',
                    'docs/integracion/README.md':'#seccion-integracion',
                }
                if key in navigation:
                    return f'[{label}]({navigation[key]})'
                return f"[{label}](#{source_anchor(key)})"
            return f"[{label}]({os.path.relpath(destination, RESULTS_DIR)})"
        if normalized.is_file():
            return f"[{label}]({os.path.relpath(normalized, RESULTS_DIR)})"
        return match.group(0)
    return re.sub(r"\[([^\]]*)\]\(([^)]+)\)", convert, text)


def markdown_table(rows: list[dict]) -> str:
    """Tabla completa de agregados existentes, sin inferir ceros ni recomputar cifras."""
    if not rows:
        return "No hay filas agregadas disponibles para esta combinación."
    columns = list(dict.fromkeys(k for row in rows for k in row))
    def cell(value: object) -> str:
        if value is None:
            return "ND"
        if isinstance(value, float):
            return f"{value:.4f}"
        return str(value).replace("|", " / ").replace("\n", " ")
    return "\n".join(["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"] +
                     ["| " + " | ".join(cell(row.get(k)) for k in columns) + " |" for row in rows])


def preserve_editorial_sections(previous: str, metadata: dict, generated: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    """Mantiene ediciones humanas; el constructor nunca borra narrativa posterior."""
    result = generated.copy()
    protected = []
    matches = list(re.finditer(r'<a id="seccion-([a-z]+)"></a>', previous))
    for i, match in enumerate(matches):
        key = match.group(1)
        end = matches[i+1].start() if i+1 < len(matches) else len(previous)
        actual = previous[match.start():end]
        expected = metadata.get('secciones', {}).get(key, {}).get('sha_generado')
        if expected and hashlib.sha256(actual.encode()).hexdigest() != expected:
            result[key] = actual
            protected.append(key)
    return result, protected


def consolidate_report() -> dict:
    """Organiza por tema; conserva universos/versiones y deduplica bloques exactos."""
    notes = load_json("data/interim/textos_analisis.json")
    buckets = {key: [] for key, _ in SECTIONS}
    selection = {
        "fuentes": ["docs/FUENTES.md", "docs/pensiones/INVENTARIO_CONSOLIDADO.md", "docs/pensiones/nacional/CATALOGO_NACIONAL.md", "docs/pensiones/nacional/IDENTIFICABILIDAD_ENASEM.md"],
        "integracion": ["docs/integracion/COBERTURA.md", "docs/pensiones/PROPUESTA_INTEGRACION.md"],
        "validacion": ["docs/integracion/VALIDACION.md"],
        "poblacion": ["docs/CP1_INFORME_REVISION.md", "docs/CP1_TABLAS_RONDAS.md", "docs/AUDITORIA_INICIAL.md", "docs/CP1_RESULTADOS.md"],
        "pensiones": ["docs/integracion/titularidad/AUDITORIA_TITULARIDAD.md", "docs/eda/proteccion_economica/INFORME_PROTECCION_ECONOMICA.md", "docs/pensiones/REGLAS_CLASIFICACION.md"],
        "univariado": ["docs/eda/B01_ENASEMSIMPLE.md", "docs/eda/B01_REVISION.md", "docs/eda/N_RES_VERSIONES.md", "docs/eda/B02A_K_2021.md"],
        "hallazgos": ["docs/integracion/EDA_CONJUNTO_INICIAL.md", "docs/eda/pensiones_exploratorio_v1/SALUD_COMPLEMENTARIA.md"],
        "limites": ["docs/eda/pensiones_exploratorio_v1/METODOLOGIA.md", "docs/eda/pensiones_exploratorio_v1/PENDIENTES.md", "docs/integracion/HOMOLOGACION_PENDIENTE.md"],
        "preguntas": ["docs/eda/pensiones_exploratorio_v1/PREGUNTAS_POTENCIALES.md"],
        "pendientes": ["docs/eda/pensiones_exploratorio_v1/MATRIZ_CUMPLIMIENTO.md"],
    }
    selection["univariado"] += [key for key in notes if key.startswith(("docs/eda/variables/", "docs/eda/k2021/"))]
    selection["univariado"] += [f"docs/eda/pensiones_exploratorio_v1/UNIVARIADO_{year}.md" for year in (2001, 2003, 2012, 2015, 2018, 2021)]
    selection["bivariado"] = sorted(k for k in notes if k.startswith("docs/eda/pensiones_exploratorio_v1/analisis/B"))
    selection["trivariado"] = sorted(k for k in notes if k.startswith(("docs/eda/pensiones_exploratorio_v1/analisis/T", "docs/eda/pensiones_exploratorio_v1/analisis/C")))
    # Las notas documentales completas también deben poder leerse sin abrir JSON.
    selected = {path for paths in selection.values() for path in paths}
    for path in sorted(set(notes) - selected):
        section = ("hallazgos" if path.endswith(("HALLAZGOS.md", "RESULTADOS.md")) else
                   "fuentes" if path.startswith(("docs/pensiones/nacional/", "docs/recuperacion/")) else
                   "univariado" if "PREVALIDACION" in path else
                   "pensiones" if path.startswith(("docs/pensiones/", "docs/eda/proteccion_economica/")) else
                   "integracion" if path.startswith("docs/integracion/") else "pendientes")
        selection.setdefault(section, []).append(path)
    seen, inventory = {}, []
    for section, paths in selection.items():
        for path in paths:
            if path not in notes:
                continue
            original = notes[path]["texto"]
            converted = convert_links(original, path)
            title = original.splitlines()[0].lstrip("# ")
            chunks = re.split(r"\n\s*\n", converted)
            unique = []
            for chunk in chunks[1:]:
                if not chunk.strip():
                    continue
                digest = hashlib.sha256(re.sub(r"\s+", " ", chunk).strip().encode()).hexdigest()
                # Only exact editorials are deduplicated. Tables/figures stay near their analysis.
                if digest in seen and not chunk.lstrip().startswith(("|", "!", "#", "```")):
                    continue
                seen[digest] = section
                unique.append(chunk)
            context = ("Fuente independiente: todas las edades; no sumar con la submuestra 60+." if path.startswith(("docs/eda/variables/", "docs/eda/k2021/")) else
                       "Universo CP1 completo, sin filtro inicial de edad/modalidad." if section == "poblacion" else
                       "Evidencia previa conservada: revisar población, versión y denominador de cada cuadro; no sumar etapas.")
            if path in {'docs/DECISIONES.md', 'docs/EXPERIMENTOS.md', 'docs/HANDOFF.md',
                        'docs/PREGUNTA_Y_ALCANCE.md', 'docs/ROADMAP.md',
                        'docs/PLAN_EDA_RONDAS_Y_PENSIONES.md'}:
                context += (' Antecedente metodológico fechado: sus propuestas predictivas, '
                            'outcomes o hipótesis no gobiernan la etapa exploratoria vigente.')
            # Source files are evidence, not chapters: normalize their hierarchy and
            # select their distinct methodological contributions under one thematic index.
            contribution = "\n\n".join(unique)
            contribution = re.sub(r'(?m)^(#{1,5}) ', lambda m: '#' * min(6, len(m.group(1)) + 2) + ' ', contribution)
            concept_titles = {
                'docs/CP1_INFORME_REVISION.md':'Universo, rondas, seguimiento y consistencia: población completa',
                'docs/CP1_RESULTADOS.md':'Reconciliaciones y verificaciones complementarias de CP1',
                'docs/AUDITORIA_INICIAL.md':'Diagnóstico inicial y contraste de subpoblaciones: evidencia histórica',
                'docs/CP1_TABLAS_RONDAS.md':'Composición detallada de las seis rondas',
                'docs/integracion/VALIDACION.md':'Cardinalidad, correspondencias y preservación',
                'docs/integracion/COBERTURA.md':'Cobertura económica por fuente y modalidad',
                'docs/integracion/titularidad/AUDITORIA_TITULARIDAD.md':'Beneficiarios, orientación, duplicación y desconocidos',
                'docs/eda/proteccion_economica/INFORME_PROTECCION_ECONOMICA.md':'Armonización J02: recepción propia, pareja y coexistencia',
                'docs/pensiones/PROPUESTA_INTEGRACION.md':'Diseño auditado de enlaces: antecedente previo a ejecución',
            }
            title = concept_titles.get(path, title)
            body = f'<a id="{source_anchor(path)}"></a>\n\n### {title}\n\n*{context}*\n\n' + contribution
            if path.startswith(("docs/eda/variables/", "docs/eda/k2021/")):
                body = f'<details><summary>{title} · fuente independiente</summary>\n\n' + body + "\n\n</details>"
            buckets[section].append(body)
            inventory.append({"origen": path, "seccion": section, "ancla": source_anchor(path), "sha256_original": notes[path]["sha256_original"]})
    results = load_json("docs/eda/pensiones_exploratorio_v1/resultados.json")
    buckets['poblacion'].append('### Muestra exploratoria 60+ por visita: flujo separado de CP1\n\nNo equivale al universo completo ni a una cohorte balanceada. Primera aparición en ENASEM no es primera visita elegible de 60+. Se conservan nuevas incorporaciones, seguimientos y reapariciones como conceptos distintos.\n\n'+markdown_table(results['flujo_muestra'])+'\n\n'+markdown_table(results['modalidades_60'])+'\n\n'+markdown_table(results['rondas_por_persona_60']))
    for variable, result in results.get('comparativos_univariados', {}).items():
        obj = load_json(result['tabla'])
        tables = markdown_table(obj) if isinstance(obj, list) else '\n\n'.join(markdown_table(v) for v in obj.values() if isinstance(v, list) and v and isinstance(v[0], dict))
        fig = project_path(result['figura']).relative_to(RESULTS_DIR).as_posix()
        buckets['univariado'].append(f'### Comparación transversal 60+ entre rondas: {variable}\n\n**Estado: {result["estado"]}.**\n\n{result["interpretacion"]}\n\n{tables}\n\n![{variable}]({fig})')
    flow_figure=project_path('reports/pensiones_exploratorio_v1/figuras/U_modalidades_comparativa.png').relative_to(RESULTS_DIR).as_posix()
    buckets['poblacion'].append(f'![Modalidades de la muestra exploratoria]({flow_figure})')
    buckets["integracion"].insert(0, "### Puentes personales efectivamente utilizados\n\nEn 2001 se enlaza el maestro con `sect_k_ind_2001.dta` por `cunicah` y `codent01`, y de allí con el hogar mediante `unhhid`. En 2003 el puente `sect_k_ind_2003.dta` usa `cunicah` y `codent03`; aporta `cunicah` y `acthog` económico. No se usa `acthog` del maestro como unión directa. `economic_link` y `left_indexer` validan unicidad y rechazan muchos-a-muchos. En 2012–2021 se usan las claves específicas auditadas de subhogar. Identidad final `cunicah:np` y `id+ronda`, sin publicar valores individuales.")
    buckets["longitudinal"].append("Cohorte viva 60+ en origen, sin exigir seis rondas. Edad, sexo, educación y localidad se fijan en origen. Muerte, ausencia temporal, reaparición, desconocimiento y cambio de instrumento tienen estados distintos. Los intervalos nominales son 2/9/3/3/3 años. La comparabilidad sigue condicionada a los contratos existentes; no se recalculan trayectorias durante la migración.\n\n" + markdown_table(results["correspondencias"]))
    for key, result in results["seguimiento"].items():
        rows = load_json(result["tabla"])
        table = markdown_table(rows) if isinstance(rows, list) else "\n\n".join(markdown_table(v) for v in rows.values() if isinstance(v, list) and v and isinstance(v[0], dict))
        fig = project_path(result["figura"]).relative_to(RESULTS_DIR).as_posix()
        buckets["longitudinal"].append(f'### {key} · {result["solicitud"]}\n\n**Estado: {result["estado"]}.**\n\n{result["interpretacion"]}\n\n![{key}]({fig})\n\n<details><summary>Tabla de transición y denominadores completos</summary>\n\n{table}\n\n</details>')
    # The cumulative log contains some evidence not narrated in the themed reports.
    # Integrate only distinct empirical paragraphs, grouped by their original scope;
    # administrative templates stay in the structured historical record.
    log = notes.get('docs/RESULTADOS.md', {}).get('texto', '')
    extra = []
    for chunk in re.split(r'\n\s*\n', convert_links(log, 'docs/RESULTADOS.md')):
        if not re.search(r'\d', chunk) or chunk.lstrip().startswith(('#', '|', '- Fecha', '- N del test')):
            continue
        digest = hashlib.sha256(re.sub(r'\s+', ' ', chunk).strip().encode()).hexdigest()
        if digest not in seen:
            extra.append(chunk)
            seen[digest] = 'hallazgos'
    if extra:
        buckets['hallazgos'].append(f'<a id="{source_anchor("docs/RESULTADOS.md")}"></a>\n\n### Evidencia complementaria conservada de etapas anteriores\n\nCada párrafo conserva el universo, versión y etapa originales. No sumarlos ni interpretarlos como una sola muestra.\n\n'+'\n\n'.join(extra))
        inventory.append({'origen':'docs/RESULTADOS.md','seccion':'hallazgos','ancla':source_anchor('docs/RESULTADOS.md'),'sha256_original':notes['docs/RESULTADOS.md']['sha256_original']})
    buckets["hallazgos"].insert(0, "La migración no redefine la investigación: maestro 99,676 personas-ronda/27,171 personas; muestra exploratoria 60+ 56,004/18,754. K propia no equivale automáticamente a contributividad; A no equivale a pensión no contributiva. En 2021: 3,599 K propias, 5,583 A propias, coexistencia 2,019 y A con negativa K 3,558. Son resultados descriptivos sin ponderación validada. V=0.03756 en 10,396 pares conocidos, no causalidad. El universo confirmado de pareja es 6,071, distinto del denominador de prevalencia general. Las preguntas, outcome, hipótesis principal y modelos permanecen abiertos.")
    migration_path=INTERIM_DIR/'migracion_proyecto.json'
    if migration_path.exists():
        migration=json.loads(migration_path.read_text())
        verified=migration.get('validaciones_finales', {})
        buckets['pendientes'].append('### Organización funcional y conservación de evidencia\n\nLos puntos de entrada activos son 01_INTEGRACION y 02_EDA_COMPLETO; este informe es el registro académico único. Diccionarios y bibliografía están centralizados. Los originales históricos no se han retirado: falta autorización final de la autora. No se publicaron cambios ni microdatos. La migración conserva universos y definiciones; no aprueba homologaciones, ponderación, precios o pregunta definitiva.\n\n'+markdown_table([{'comprobacion':'Tests locales','resultado':verified.get('pytest_local', {}).get('aprobadas'),'estado':'Ejecutado' if verified else 'Pendiente'}, {'comprobacion':'Tests sin docs/reports','resultado':verified.get('pytest_sin_docs_reports', {}).get('aprobadas'),'estado':'Ejecutado' if verified else 'Pendiente'},{'comprobacion':'Bases y agregados','resultado':'Huellas idénticas al respaldo','estado':'Comprobado'},{'comprobacion':'Retiro de históricos','resultado':'Lista exacta en data/interim/migracion_proyecto.json','estado':'Pendiente de aprobación'},{'comprobacion':'GitHub privado','resultado':'Repositorio comprobado público; cambio no disponible en las herramientas actuales','estado':'Pendiente'}]))
    preamble = "# Informe general acumulativo — tesis ENASEM\n\nOrganización vigente: 13 de octubre de 2026. Consolidación de evidencia ya calculada; no nuevos análisis. Los estados provisionales e históricos se conservan. La aceptación metodológica continúa abierta.\n\nLa lectura se organiza por pregunta y alcance: CP1 describe todas las edades y modalidades; B01 y K2021 conservan las poblaciones originales de sus archivos; J02 y la exploración pensionaria utilizan 60+ por visita. Sus cifras no son alternativas intercambiables ni deben sumarse. Las tablas extensas son evidencia consultable, con metadatos completos en diccionarios y agregados en data/interim. Las observaciones operativas de informes previos son históricas: las reglas vigentes están en AGENTS.md.\n\n## Índice navegable\n\n" + "\n".join(f"- [{i}. {title}](#seccion-{key})" for i, (key, title) in enumerate(SECTIONS, 1))
    generated = {key: f'<a id="seccion-{key}"></a>\n\n## {i}. {title}\n\n'+"\n\n".join(buckets[key])+"\n\n" for i,(key,title) in enumerate(SECTIONS,1)}
    protected = []
    current = RESULTS_DIR / 'INFORME_GENERAL.md'
    metadata_path = INTERIM_DIR / 'indice_informe.json'
    prior_metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
    emitted = generated
    if current.exists():
        previous = current.read_text()
        emitted, protected = preserve_editorial_sections(previous, prior_metadata, generated)
        first = previous.find('<a id="seccion-')
        if first >= 0 and prior_metadata.get('sha_preambulo') and hashlib.sha256(previous[:first].encode()).hexdigest()!=prior_metadata['sha_preambulo']:
            preamble = previous[:first].rstrip()
    # Conservar ediciones humanas no debe dejar contribuciones nuevas fuera del informe.
    # Cotejar todos los bloques, incluidos títulos, tablas y notas del registro acumulado.
    def normalized_block(value: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"(?m)^#{1,6}\s+", "", value)).strip()

    emitted = {key: convert_links(value, 'resultados/INFORME_GENERAL.md')
               for key, value in emitted.items()}
    readable = normalized_block("\n\n".join(emitted.values()))
    coverage = []
    for item in inventory:
        path = item['origen']
        converted = convert_links(notes[path]['texto'], path)
        blocks = [block for block in re.split(r"\n\s*\n", converted) if normalized_block(block)]
        missing = [block for block in blocks[1:] if normalized_block(block) not in readable]
        anchor_missing = f'id="{item["ancla"]}"' not in "\n".join(emitted.values())
        if missing or anchor_missing:
            heading = notes[path]['texto'].splitlines()[0].lstrip('# ')
            anchor = f'<a id="{item["ancla"]}"></a>\n\n' if anchor_missing else ''
            extra = (f'\n\n{anchor}<details><summary>{heading} · evidencia documental completa</summary>\n\n'
                     'Antecedente conservado con su fecha, universo y estado originales. '
                     'Las propuestas previas no son decisiones metodológicas vigentes.\n\n' +
                     '\n\n'.join(missing) + '\n\n</details>\n\n')
            emitted[item['seccion']] += extra
            readable += ' ' + normalized_block(extra)
        coverage.append({'origen': path, 'ancla': item['ancla'], 'seccion': item['seccion'],
                         'bloques_cotejados': len(blocks[1:]), 'bloques_recuperados': len(missing)})
    text = preamble + "\n\n"; indices = {}
    for i, (key, title) in enumerate(SECTIONS, 1):
        start = len(text)
        text += emitted[key]
        indices[key] = {"inicio": start, "fin": len(text), "titulo": title, 'sha_generado':hashlib.sha256(generated[key].encode()).hexdigest()}
    RESULTS_DIR.mkdir(exist_ok=True)
    if not current.exists() or current.read_text()!=text:
        current.write_text(text)
    metadata_path.write_text(json.dumps({"secciones": indices, "origenes": inventory, 'cobertura_textos':coverage,'sha_preambulo':hashlib.sha256((preamble+'\n\n').encode()).hexdigest(),'secciones_editoriales_protegidas':protected}, ensure_ascii=False, indent=2) + "\n")
    return {"secciones": len(indices), "fuentes_incorporadas": len(inventory), "bytes": len(text.encode()),'ediciones_humanas_preservadas':protected}


def report_section(key: str) -> str:
    """Obtiene una sección, sin repetir cálculo o cargar microdatos."""
    indices = load_json("data/interim/indice_informe.json")["secciones"]
    text = (RESULTS_DIR / "INFORME_GENERAL.md").read_text()
    item = indices[key]
    return text[item["inicio"]:item["fin"]]


def validate_documentary_coverage() -> dict[str, int]:
    """Coteja los textos íntegros con lectura accesible y enlaces locales vigentes."""
    from collections import Counter
    from urllib.parse import unquote

    notes = load_json('data/interim/textos_analisis.json')
    metadata = load_json('data/interim/indice_informe.json')
    report = (RESULTS_DIR / 'INFORME_GENERAL.md').read_text()
    def normalize(value: str) -> str:
        return re.sub(r'\s+', ' ', re.sub(r'(?m)^#{1,6}\s+', '', value)).strip()
    readable = normalize(report)
    origins = {item['origen'] for item in metadata['origenes']}
    assert origins == set(notes), 'Hay documentos sin procedencia accesible'
    anchors = re.findall(r'<a id="([^"]+)"', report)
    assert all(count == 1 for count in Counter(anchors).values()), 'Anclas duplicadas'
    missing = []
    blocks_checked = 0
    for origin, item in notes.items():
        assert source_anchor(origin) in anchors, origin
        converted = convert_links(item['texto'], origin)
        for block in re.split(r'\n\s*\n', converted)[1:]:
            if normalize(block):
                blocks_checked += 1
                if normalize(block) not in readable:
                    missing.append({'origen': origin, 'bloque': block[:160]})
    assert not missing, f'Contribuciones ausentes: {missing[:8]}'
    broken = []
    markdown_files = [PROJECT_ROOT / 'README.md', RESULTS_DIR / 'INFORME_GENERAL.md']
    markdown_files += list(RESEARCH_DIR.rglob('*.md'))
    markdown_files += list((PROJECT_ROOT / 'manuscrito').rglob('*.md'))
    links_checked = 0
    for path in markdown_files:
        text = path.read_text()
        ids = set(re.findall(r'<a id="([^"]+)"', text))
        for label, target in re.findall(r'!?\[([^\]]*)\]\(([^)]+)\)', text):
            if target.startswith(('http:', 'https:', 'mailto:')):
                continue
            links_checked += 1
            if target.startswith('#'):
                if target[1:] not in ids:
                    broken.append((str(path), target))
                continue
            destination = (path.parent / unquote(target.split('#')[0])).resolve()
            historical = destination.is_relative_to(PROJECT_ROOT / 'docs') or destination.is_relative_to(PROJECT_ROOT / 'reports')
            if not destination.exists() or historical:
                broken.append((str(path), target))
    assert not broken, f'Enlaces locales rotos o históricos: {broken[:8]}'
    for key, item in metadata['secciones'].items():
        section = report[item['inicio']:item['fin']]
        assert section.startswith(f'<a id="seccion-{key}"></a>'), key
    return {'documentos_legibles': len(origins), 'bloques_cotejados': blocks_checked,
            'bloques_ausentes': 0, 'enlaces_locales_cotejados': links_checked,
            'enlaces_rotos_o_historicos': 0, 'secciones_indexadas': len(metadata['secciones'])}


def display_section(key: str, contains: str | None = None) -> None:
    """Muestra evidencia con figuras incrustadas; filtro de lectura opcional, no de datos."""
    from IPython.display import Image, Markdown, display
    text = report_section(key)
    if contains:
        paragraphs = re.split(r"(?m)(?=^### )", text)
        text = "\n\n".join(p for p in paragraphs if contains.lower() in p.lower())
    # Notebook outputs preserve all tables; collapse controls are a browsing aid.
    pieces = re.split(r"(!\[[^\]]*\]\([^)]+\))", text)
    for piece in pieces:
        match = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", piece)
        if match:
            path = RESULTS_DIR / match.group(2)
            if path.is_file():
                display(Image(filename=str(path)))
            else:
                raise FileNotFoundError(path)
        elif piece.strip():
            display(Markdown(piece))


def find_variable(query: str) -> list[dict]:
    """Consulta definición, fuente, onda, categorías, titularidad y comparabilidad."""
    columns = load_json("diccionarios/diccionario_integrado.json")
    conceptual = {r["columna"]: r for r in load_json("diccionarios/mapa_conceptual.json")}
    return [{**r, **conceptual.get(r["columna"], {})} for r in columns
            if query.lower() in str(r.get("columna", "")).lower() or query.lower() in str(r.get("variable_original", "")).lower()]
