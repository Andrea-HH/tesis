"""Exporta inventarios completos y cuadros académicos desde metadatos agregados."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text, read_project_bytes
from collections import defaultdict
from pathlib import Path
from hashlib import sha256
import json

from tesis_enasem.manuscript import escape_latex

ROOT = Path(__file__).resolve().parents[1]
OUT = project_path('', "docs/pensiones")


def md_table(headers: list[str], rows: list[list]) -> str:
    """Tabla Markdown sin alterar tipos en las fuentes."""
    def safe(x: object) -> str:
        return str(x).replace("|", "\\|").replace("\n", " ")
    return "| "+" | ".join(headers)+" |\n| "+" | ".join(["---"]*len(headers))+" |\n"+"\n".join("| "+" | ".join(safe(x) for x in r)+" |" for r in rows)+"\n"


def write_review() -> None:
    """Reconciliación y exportación sin microdatos ni tablas de personas."""
    audit = json.loads(read_project_text(project_path('', "reports/tables/pensiones_inventario.json")))
    sources = audit["fuentes"]
    fields = audit["variables"]
    catalogue = json.loads(read_project_text(project_path('docs/pensiones', "catalogo_programas.json")))
    names = {s["archivo"]: f"F{i:02}" for i, s in enumerate(sources, 1)}
    for source in sources:
        source["fuente_id"] = names[source["archivo"]]
        assert len([v for v in fields if v["archivo"] == source["archivo"]]) == source["n_variables"]
        assert sha256(read_project_bytes(project_path('', "data/raw", source["archivo"]))).hexdigest() == source["sha256"], "Fuente cambió desde auditoría"
    # Se verifica cada copia externa. Diferente contenido impide dar por completo el inventario.
    copies = []
    for source in sources + [{"archivo": b["archivo"], "sha256": b["sha256"]} for b in audit["inventarios_referencia"]]:
        p = Path.home() / "Downloads" / source["archivo"]
        if p.is_file():
            same = sha256(read_project_bytes(p)).hexdigest() == source["sha256"]
            copies.append({"archivo": source["archivo"], "ubicacion": "Downloads", "identico_sha256": same})
            if not same: raise ValueError("Existe copia distinta: requiere inspección separada antes de entrega")
    audit["copias_externas"] = copies
    # Toda salida aquí es esquema/etiquetas/conteos, sin niveles de claves observadas.
    write_project_text(project_path('docs/pensiones', "inventario_fuentes.json"), json.dumps(audit, ensure_ascii=False, indent=2)+"\n")
    overview = []
    for s in sources:
        unique = [x for x in s["claves_candidatas"] if not x["n_incompletas"] and not x["exceso_duplicados"]]
        preferred = next((x for x in unique if ("ronda" in x["claves"] or "np" in x["claves"] or "codent01" in x["claves"] or "codent03" in x["claves"])), unique[0] if unique else None)
        s["clave_preferida"] = preferred["claves"] if preferred else []
        overview.append([s["fuente_id"], s["archivo"], s["anio_nominal_verificado"] or "2001–2021", f"{s['n_registros']:,}", s["n_variables"], "+".join(s["clave_preferida"]), "Individual" if "np" in s["columnas"] or "codent01" in s["columnas"] or "codent03" in s["columnas"] else "Hogar/subhogar"])
    text = "# Inventario consolidado de todas las fuentes\n\nInspección del 2026-10-12, sin selección de variables ni descartes por nombre. **20 archivos .dta**, 19 contenidos binarios distintos y **5,368 columnas fuente-variable** (incluye las 125 columnas del duplicado de 2018). 2024 se mantiene separado. No sumar filas de fuentes solapadas para contar personas.\n\n"
    text += md_table(["Fuente", "Archivo", "Ronda nominal", "Filas", "Columnas", "Clave única comprobada", "Unidad de fila"], overview)
    text += "\n## Método y límites de fecha\n\nCada .dta se abrió completo con pandas, sin conversión de categorías y conservando StataMissingValue. Se extrajeron etiquetas, conjuntos de códigos, tipo de columna y todos los faltantes Stata/cadenas vacías. Se auditaron claves candidatas completas y duplicadas. Los años se contrastaron con sufijos, etiquetas, esquemas de preguntas y el inventario. Para los archivos sin año, K55/K56/K58 corresponde al esquema 2001 y K58/K59/K61 al 2003. **La ronda nominal no determina la fecha efectiva de cada entrevista**: esa cronología permanece en CP1 y requiere el vínculo individual. Una fecha de versión/publicación tampoco es una ronda.\n\nLos códigos numéricos NR/NS (8/9, 88/99, 8888888/9999999 y otros según pregunta) permanecen como números. Los conteos de no perdidos no prueban respuestas sustantivas válidas. Para todas las variables, la matriz incluye presencia física; validar aplicabilidad, saltos, titular, moneda y periodicidad antes del EDA.\n\n"
    text += "## Duplicados y versiones\n\n"+"\n".join("- SHA-256 idéntico: "+", ".join(g)+". Ambas copias se inspeccionaron; ninguna se eliminó." for g in audit["duplicados_binarios"])+"\n\n"
    text += f"Se verificaron {len(copies)} copias en Descargas contra data/raw: todas idénticas; no se tomaron como fuentes independientes adicionales. La copia externa simpleMHAS en Documents/tesis también se verifica en la bitácora.\n\n"
    text += "El encabezado del .dta simpleMHAS declara `Version 3, Jan 2025`, mientras el documento proporcionado se denomina versión 2. Se conserva esa diferencia de metadatos: no se declara igualdad de versiones ni se alteran los conteos CP1. `sect_g_j_k_2024.dta` declara versión 1 de marzo de 2026; sus sufijos/etiquetas corresponden a 2024, no a una ronda de 2026.\n\n"
    for s in sources:
        text += f"## {s['fuente_id']} — {s['archivo']}\n\n{s['n_registros']:,} filas; {s['n_variables']} variables. Unidad: {s['unidad_fila']}. Año nominal: {s['anio_nominal_verificado'] or 'seis rondas 2001–2021'}. Evidencia: {s['evidencia_anio']}. Fecha efectiva: {s['anio_entrevista_efectiva']}. Etiqueta de archivo: {s['etiqueta_archivo'] or 'no declarada'}.\n\nSHA-256: `{s['sha256']}`.\n\n"
        text += md_table(["Clave candidata", "Completas", "Incompletas", "Claves distintas", "Filas en grupos duplicados", "Exceso"], [["+".join(k['claves']), k['n_completas'], k['n_incompletas'], k['n_unicas'], k['filas_duplicadas'], k['exceso_duplicados']] for k in s['claves_candidatas']])
        if s.get("equivalencias_claves_internas"):
            text += "\n"+md_table(["Campos internos", "Filas evaluadas", "Discrepantes (igualdad numérica)"], [["+".join(e["columnas"]), e["n_evaluadas"], e["n_diferentes"]] for e in s["equivalencias_claves_internas"]])+"\nCoincidencia interna comprobada, sin reemplazar la definición documental de cada clave.\n"
        text += "\nLas variables y sus etiquetas originales están íntegramente en DICCIONARIO_FUENTES.md; no se seleccionó únicamente el bloque de pensiones.\n\n"
    text += "## Correspondencias con ENASEMsimple, sin unión definitiva\n\nDenominador: filas de simpleMHAS de la ronda y modalidad declaradas. Una coincidencia de clave no significa que haya respuesta sustantiva ni que el monto sea propio.\n\n"
    rows = [[m['archivo'], m.get('universo','Todas'), '+'.join(m.get('claves',[])), m.get('n_izquierda','ND'), m.get('n_filas_izquierda_emparejadas','ND'), m.get('derecha_unica','ND')] for m in audit['correspondencias_simple']]
    text += md_table(["Fuente", "Universo", "Clave", "N referencia", "Emparejadas", "Origen único"], rows)
    text += "\nLas correspondencias directas sobre acthog en 2003 son **cero**: el campo no conserva la misma codificación entre productos. La clave distinta es una evidencia real, no ausencia de ingreso. Se verificó un puente persona→individual construido→hogar únicamente sobre claves, con cardinalidad explícita; no se fusionaron variables económicas.\n\n"
    text += md_table(["Original/imputado", "Puente", "Universo", "N referencia", "Emparejadas"], [[m['archivo'], m['puente'], m['universo'], m['n_izquierda'], m['n_filas_izquierda_emparejadas']] for m in audit['puentes_historicos']])
    text += "\nEl puente recupera 14,099/14,154 directas en 2001 y 12,499/12,526 en 2003; la fuente individual coincide con todas las directas, pero la entrevista original de hogar no. En 2015 el original tiene 9,953 filas y el imputado 9,921: **32 entrevistas económicas menos**, no equivalencia de universos. En 2018 quedan 20 directas sin clave económica de origen; en 2021 hay 18 directas sin coincidencia en original/imputado de hogar aunque todas enlazan al individual construido. Investigar versiones y atribuciones sin rellenar estos casos con cero.\n\n"
    text += "## Comparación de todas las parejas de fuentes de la misma ronda\n\nSe verificaron 18 parejas, incluyendo el duplicado. La comparación por valores solo se ejecuta si la clave común es única en ambos archivos. Para relaciones persona↔hogar se reporta cardinalidad, sin comparar copias de montos como si fueran independientes. Los nombres iguales no prueban equivalencia y am/imam no son dos ingresos distintos.\n\n"
    text += md_table(["A", "B", "Año", "Columnas comunes", "Filas comparadas 1:1", "Columnas con discrepancia"], [[m['fuente_a'], m['fuente_b'], m['anio'], m['n_variables_mismo_nombre'], m.get('n_comparadas','No 1:1'), sum(n>0 for n in m.get('discrepancias_por_variable',{}).values()) if 'discrepancias_por_variable' in m else 'No 1:1'] for m in audit['comparaciones_misma_ronda']])
    text += "\n## Excel de referencia completo\n\nSe inspeccionaron las seis hojas y sus fórmulas/valores; el archivo no se modificó. El nombre disponible no tiene `(1)`.\n\n"
    for book in audit['inventarios_referencia']:
        text += md_table(["Hoja", "Filas con encabezado", "Fórmulas"], [[sh['hoja'],len(sh['filas']),len(sh['formulas'])] for sh in book['hojas']])
    text += "\nLas cifras de archivos y matching individual del Excel se reprodujeron. Se actualiza su pendiente 2003: pandas lee el formato antiguo, 8,895×348. Se incorpora 2024 (14,076×507) en un inventario separado. Se conserva como faltante la versión **imputada a nivel hogar 2018**, que no está suministrada; el individual contiene imputaciones y no sustituye documentalmente ese archivo. Los productos separados de ingreso total/patrimonio 2018 y 2021 tampoco se identificaron entre los proporcionados: la documentación los describe, pero ello no los vuelve disponibles localmente. El Excel era una selección pensionaria; la auditoría nueva incluye todas las columnas.\n\n## Archivo 2024 y posible ampliación\n\nSe inspeccionaron sus 507 variables y su clave única cunicah+subhog_24. No hay ronda 7 en simpleMHAS suministrado. Requiere archivo individual/seguimiento 2024, puente persona-subhogar, cuestionarios y productos imputados correspondientes, revisión de nuevas categorías (incluye apoyo por discapacidad y ONG en las opciones de K79), cronología y aceptación de cambio de periodo. No combinar su código 2 (pensión Bienestar) con el código 2 de 2021 (becas) ni 2018 (PROSPERA). No se incorpora ahora al periodo principal.\n"
    write_project_text(project_path('docs/pensiones', "INVENTARIO_CONSOLIDADO.md"), text)
    # Diccionario completo: categorías son etiquetas del proveedor, no valores observados.
    text = "# Diccionario íntegro de las variables de cada fuente\n\n5,368 columnas fuente-variable, incluyendo archivos duplicados y 2024. No se publican valores individuales ni niveles de identificadores. Los códigos/etiquetas son metadatos del proveedor. ‘No perdidos Stata’ NO descuenta NR/NS numéricos. Unidad, titular y periodo deben cotejarse en cada pregunta antes de armonizar.\n\n"
    for s in sources:
        text += f"## {s['fuente_id']} — {s['archivo']}\n\nN={s['n_registros']:,}; año nominal {s['anio_nominal_verificado'] or '2001–2021'}. {s['unidad_fila']}.\n\n"
        rows=[]
        for v in fields:
            if v['archivo'] != s['archivo']: continue
            codes = '; '.join(f'{c}: {l}' for c,l in v['etiquetas_valores'].items()) or 'Sin etiquetas de valores almacenadas; no inferir códigos'
            miss = '; '.join(f'{c}={n}' for c,n in v['perdidos_especiales'].items()) or 'Ningún perdido Stata observado'
            rows.append([v['variable'],v['etiqueta'] or 'Sin etiqueta',v['dtype'],v['n_no_perdidos_stata'],v['n_perdidos'],v['pct_perdidos'],miss,codes])
        text += md_table(['Variable','Etiqueta original','Tipo','No perdidos Stata','Perdidos','% perdidos/N','Desglose Stata','Códigos etiquetados'],rows)+'\n'
    write_project_text(project_path('docs/pensiones', 'DICCIONARIO_FUENTES.md'), text)
    normalized=defaultdict(lambda: defaultdict(list))
    for v in fields:
        normalized[v['nombre_sin_sufijo']][names[v['archivo']]].append(v['variable'])
    assert sum(len(values) for row in normalized.values() for values in row.values()) == len(fields)
    text = '# Matriz exhaustiva variable × fuente\n\nCada celda presente muestra el nombre original; **ND** significa columna ausente en ese archivo, no cero ni ausencia de pensión. Solo se retira el sufijo de ronda para facilitar búsqueda: la fila NO declara equivalencia semántica. K59 cambia de selección institucional múltiple a fuentes por pensión; se requiere la matriz de conceptos de DISPONIBILIDAD_RONDAS.md. Los nombres antiguos am55/am58 no se homologan mecánicamente.\n\n'
    text += md_table(['Fuente','Archivo','Año'],[[s['fuente_id'],s['archivo'],s['anio_nominal_verificado'] or '2001–2021'] for s in sources])+'\n'
    text += md_table(['Candidato léxico']+list(names.values()),[[key]+['; '.join(matches[fid]) if fid in matches else 'ND' for fid in names.values()] for key,matches in sorted(normalized.items())])
    write_project_text(project_path('docs/pensiones', 'MATRIZ_VARIABLES_FUENTES.md'), text)
    historical = '# Catálogo histórico de programas y versiones\n\n'+catalogue['alcance']+'\n\nUna fila es una versión documental, no un beneficiario. `anio_inicio_programa` se refiere al inicio documentado del programa o denominación (PAM: 2013; Bienestar: 2019); el origen de la familia federal (2007) y cada versión se registran por separado. Para IMSS/ISSSTE y programas locales sin creación cotejada, el origen queda desconocido. El año individual de primera recepción y la primera observación ENASEM quedan **null** en este catálogo porque corresponden a registros individuales futuros. No se deducen a partir del inicio oficial.\n\n'
    historical += md_table(['Versión','Inicio documentado','Nombre oficial','Ámbito / tipo','Institución','Operación/versiones','Elegibilidad y requisitos','Monto MXN / periodicidad','Cambios','Documento'],[[p['programa_version_id'],p['anio_inicio_programa'] if p['anio_inicio_programa'] is not None else 'No verificado',p['programa_nombre_original'],p['programa_ambito']+' / '+p['programa_tipo'],p['institucion_otorgante'],p['operacion_documentada'],str(p['edad_elegibilidad'])+'; '+p['requisitos_relevantes'],str(p['monto_nominal_mxn'])+'; '+p['periodicidad_monto'],p['cambios_historicos'],f"[{p['fuente_localizador']}]({p['fuente_url']})"] for p in catalogue['programas']])
    historical += '\n## Relaciones que NO implican equivalencia de mediciones\n\n'+md_table(['Origen','Destino','Relación','Justificación'],[[r['origen'],r['destino'],r['tipo'],r['justificacion']] for r in catalogue['relaciones']])+'\nSe documenta una selección pertinente, no un censo nacional de apoyos locales. Para asignar programas locales a participantes se necesitan nombre/organismo y geografía autorizada de la ronda; residencia o edad solas no bastan. Las versiones anuales faltantes siguen pendientes; no extender los montos verificados a todos los años. INAPAM/INSEN son instituciones y sus credenciales/servicios no prueban recepción de una pensión monetaria.\n'
    write_project_text(project_path('docs/pensiones', 'CATALOGO_HISTORICO.md'), historical)
    # Cuadros con encabezados sencillos y reglas horizontales como el borrador original.
    latex = '\\begingroup\\small\\singlespacing\n\\setlength{\\tabcolsep}{3pt}\n\\begin{longtable}{>{\\raggedright\\arraybackslash}p{1.1cm}>{\\raggedright\\arraybackslash}p{3.2cm}>{\\raggedright\\arraybackslash}p{1.6cm}>{\\raggedright\\arraybackslash}p{3.5cm}>{\\raggedright\\arraybackslash}p{3.7cm}>{\\raggedright\\arraybackslash}p{1.6cm}}\n\\caption{Programas pensionarios y transferencias: versiones históricas seleccionadas}\\label{tab:pensiones_historia}\\\\\n\\toprule Inicio & Nombre oficial & Ámbito & Requisitos relevantes & Cambios históricos & Fuente \\\\\n\\midrule\\endfirsthead\n\\toprule Inicio & Nombre oficial & Ámbito & Requisitos relevantes & Cambios históricos & Fuente \\\\\n\\midrule\\endhead\n\\bottomrule\\endfoot\n'
    for p in catalogue['programas']:
        scope={'federal':'Federal', 'federal_seguridad_social':'Federal', 'estatal_df':'DF', 'estatal_cdmx':'CDMX', 'estatal_jalisco':'Jalisco', 'municipal_merida':'Mérida'}.get(p['programa_ambito'],p['programa_ambito'])
        age=p['edad_elegibilidad']
        requirements=(f"Edad: {age}+. " if isinstance(age,int) else f"Edad: {age}. " if age is not None else '')+p['requisitos_relevantes']
        cells=[str(p['anio_inicio_programa']) if p['anio_inicio_programa'] is not None else 'ND',p['programa_nombre_original'],scope,requirements,p['version_temporal']+'. '+p['cambios_historicos']]
        # Abreviación institucional y año enlazado: evita autoridades largas en una celda estrecha.
        source_short={'evalua2015':'Evalúa CDMX','cdmx2017':'Gaceta CDMX','jalisco2014':'Jalisco','jalisco2018':'Jalisco','merida2009':'Mérida'}.get(p['bibtex_key'],'DOF')
        latex+=' & '.join(escape_latex(c) for c in cells)+f" & {source_short} \\citeyearpar{{{p['bibtex_key']}}} \\\\\n"
    latex+='\\end{longtable}\n\\noindent\\footnotesize Fuente: elaboración documental, catálogo reproducible. ND: origen no verificado, distinto de ausencia de operación. Versiones y montos son históricos; no identifican recepción individual en ENASEM.\\par\n\\endgroup\n'
    write_project_text(project_path('', 'manuscrito/tablas/pensiones_historia.tex'), latex)
    latex='\\begingroup\\small\\singlespacing\n\\setlength{\\tabcolsep}{3pt}\n\\begin{longtable}{llrrp{4.4cm}}\n\\caption{Inventario de fuentes económicas revisadas}\\label{tab:pensiones_fuentes}\\\\\n\\toprule Fuente & Ronda & Registros & Variables & Clave única comprobada \\\\\n\\midrule\\endfirsthead\n\\toprule Fuente & Ronda & Registros & Variables & Clave única comprobada \\\\\n\\midrule\\endhead\\bottomrule\\endfoot\n'
    for s in sources:
        latex+=f"{s['fuente_id']} & {s['anio_nominal_verificado'] or '2001--2021'} & {s['n_registros']:,} & {s['n_variables']} & "+escape_latex('+'.join(s['clave_preferida']))+' \\\\\n'
    latex+='\\end{longtable}\n\\noindent\\footnotesize Fuentes F01--F20 se identifican por nombre completo en el inventario consolidado y su JSON. Ambas copias idénticas de 2018 se conservan. No sumar registros entre fuentes; existen universos solapados. El archivo 2024 queda separado.\\par\n\\endgroup\n'
    write_project_text(project_path('', 'manuscrito/tablas/pensiones_fuentes.tex'), latex)
    # Guardar el esquema final con claves preferidas y la reconciliación.
    write_project_text(project_path('docs/pensiones', 'inventario_fuentes.json'), json.dumps(audit, ensure_ascii=False, indent=2)+'\n')
    print(f'Exportación: {len(sources)} fuentes, {len(fields)} columnas, {len(normalized)} candidatos léxicos, {len(catalogue["programas"])} versiones históricas; sin filas individuales.')


if __name__ == '__main__':
    write_review()
