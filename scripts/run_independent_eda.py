"""EDA independiente por bloques: prevalidación de todas las fuentes y ENASEMsimple."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text, read_project_bytes

import argparse
from hashlib import sha256
import html
import json
from pathlib import Path
import re

import pandas as pd

from tesis_enasem.independent_eda import (
    VariableSpec, analyze_variable, code_token, plot_variable, simple_role, strict_json,
)
from tesis_enasem.source_inventory import missing_mask

ROOT = Path(__file__).resolve().parents[1]
DOCS = project_path('', "docs/eda")
REPORTS = project_path('', "reports/eda_independiente")


def md_table(rows: list[dict]) -> str:
    """Tabla Markdown sin dependencias opcionales ni redondeo de los agregados fuente."""
    if not rows:
        return "Sin observaciones en este apartado.\n"
    headers = list(rows[0])
    def fmt(x: object, column: str) -> str:
        if x is None: return "ND"
        if column.lower() in {"anio", "año", "ronda", "anio_nominal", "año_nominal"}:
            return str(x)
        if isinstance(x, float): return f"{x:,.2f}"
        if isinstance(x, int): return f"{x:,}"
        return str(x).replace("|", "/").replace("\n", " ")
    return "\n".join(["| " + " | ".join(headers) + " |",
                       "| " + " | ".join(["---"] * len(headers)) + " |",
                       *["| " + " | ".join(fmt(r[k], k) for k in headers) + " |" for r in rows]]) + "\n"


def preflight(inventory: dict) -> tuple[pd.DataFrame, list[dict]]:
    """Lee las 20 fuentes, coteja hashes y audita códigos etiquetados sin asumir validez."""
    fields = {(v["archivo"], v["variable"]): v for v in inventory["variables"]}
    ledger, source_profiles, summary = [], [], []
    simple = None
    report = ("# Prevalidación independiente de las 20 fuentes\n\n"
              "Este bloque revisa códigos almacenados y cobertura; **no equivale a EDA semánticamente validado**. "
              "Los conteos por código corresponden exclusivamente a categorías etiquetadas por el proveedor; "
              "no se exportan niveles de claves, texto libre ni valores numéricos individuales. "
              "Los números no etiquetados pueden contener NR/NS: sus medias no se calculan. "
              "No hay integración de bases ni filtros de edad, modalidad o continuidad.\n\n")
    for source in inventory["fuentes"]:
        name, fid = source["archivo"], source["fuente_id"]
        path = project_path('', "data/raw", name)
        if sha256(read_project_bytes(path)).hexdigest() != source["sha256"]:
            raise ValueError(f"Fuente cambió desde inventario: {fid}")
        frame = pd.read_stata(path, convert_missing=True, convert_categoricals=False)
        assert list(frame) == source["columnas"] and len(frame) == source["n_registros"]
        if fid == "F20": simple = frame
        keys = set(source["clave_preferida"]) | {"cunicah", "np", "unhhid", "ent2", "ps3", "codent01", "codent03"}
        entries = []
        for col in frame:
            meta = fields[(name, col)]
            role = simple_role(col) if fid == "F20" else ("técnica: clave" if col in keys or col.startswith("subhog_") else "sustantiva/auxiliar por revisar")
            status = "técnica: auditada sin divulgar niveles" if role.startswith("técnica") else "prevalidación ejecutada; EDA sustantivo pendiente"
            item = {"fuente": fid, "archivo": name, "ronda": source["anio_nominal_verificado"] or "2001–2021",
                    "variable": col, "rol": role, "estado": status,
                    "bloque": "B01" if fid == "F20" else "B00",
                    "N_total": len(frame), "N_elegible": None,
                    "pendiente": "Universo exacto de pregunta y cotejo entre versiones" if fid == "F20" else "Cuestionario individual: filtros, códigos no etiquetados, unidad, titular, referencia temporal",
                    "periodo_principal": source["periodo_principal"]}
            ledger.append(item)
            if role.startswith("técnica"): continue
            s = frame[col]
            miss = missing_mask(s)
            observed_tokens = s.loc[~miss].map(code_token)
            counts = observed_tokens.value_counts()
            labels = meta["etiquetas_valores"]
            coded = []
            for code, label in labels.items():
                candidate = bool(re.search(r"no sabe|don.?t know|refus|reh[uú]s|no respon|negativa", label, re.I))
                coded.append({"codigo": code, "etiqueta_proveedor": label, "n": int(counts.get(code, 0)),
                              "pct_total": 100 * counts.get(code, 0) / len(s),
                              "posible_NR_NS_por_cotejar": candidate})
            unlabelled = int((~observed_tokens.isin(labels)).sum())
            entry = {"variable": col, "etiqueta": meta["etiqueta"], "N_total": len(s),
                     "N_perdido_Stata_o_vacio": int(miss.sum()), "N_no_perdido_sin_etiqueta_valor": unlabelled,
                     "perdidos_especiales": meta["perdidos_especiales"], "codigos_etiquetados": coded,
                     "N_valido": None, "N_elegible": None,
                     "estado": "No interpretar como respuesta válida hasta cotejar instrumento"}
            entries.append(entry)
        source_profiles.append({"fuente": fid, "archivo": name, "sha256": source["sha256"],
                                "unidad_fila": source["unidad_fila"], "variables": entries})
        summary.append({"Fuente": fid, "Ronda": source["anio_nominal_verificado"] or "2001–2021",
                        "Columnas": len(frame.columns), "Claves/diseño/pesos": len(frame.columns)-len(entries),
                        "Sustantivas/auxiliares": len(entries), "EDA observado": 0,
                        "Pendientes EDA": len(entries)})
        report += f"## {fid} — {name}\n\nUnidad: {source['unidad_fila']}. N={len(frame):,}. Año: {source['anio_nominal_verificado'] or '2001–2021'}.\n\n"
        for entry in entries:
            report += f"### {entry['variable']}\n\n{entry['etiqueta'] or 'Sin etiqueta'}. "
            report += f"N total={entry['N_total']:,}; perdidos Stata/vacíos={entry['N_perdido_Stata_o_vacio']:,}; no perdidos sin etiqueta de valor={entry['N_no_perdido_sin_etiqueta_valor']:,}. N válido y elegible pendientes.\n\n"
            report += md_table(entry["codigos_etiquetados"]) + "\n"
        print(f"B00 {fid}: {len(frame.columns)} columnas cotejadas; {len(entries)} sustantivas/auxiliares", flush=True)
    assert simple is not None and len(ledger) == 5368
    strict_json(ledger, project_path('docs/eda', "cobertura_variables.json"))
    strict_json(source_profiles, project_path('reports/eda_independiente', "prevalidacion_fuentes.json"))
    write_project_text(project_path('docs/eda', "PREVALIDACION_FUENTES.md"), report)
    write_project_text(project_path('docs/eda', "COBERTURA_VARIABLES.md"),
        "# Control exhaustivo de cobertura\n\nB00: prevalidación de códigos y faltantes de todas las fuentes. "
        "B01: ENASEMsimple en ejecución; solo se cuenta terminado después de reconciliar todos sus agregados. "
        "Las 28 columnas técnicas también se auditan, sin divulgar claves. "
        "Los estados pendientes son explícitos: **no se declara terminado el EDA de K ni de los productos construidos**. "
        "No hay variable ausente del registro de control: 5,368 filas fuente-variable, incluyendo copias y 2024.\n\n" +
        md_table(summary) + "\nEl [JSON de cobertura](cobertura_variables.json) contiene una fila por columna original. "
        "‘Auxiliar por revisar’ conserva rangos, banderas, ponderadores e indicadores de enlace no clasificados; no se descartan silenciosamente. "
        "F04/F05 se conservan separados; F06 (2024) es un bloque fuera del periodo principal. "
        "Los problemas de enlace 2001, 2003, 2015, 2018 y 2021 siguen en [el inventario](../pensiones/INVENTARIO_CONSOLIDADO.md).\n")
    return simple, summary


def variable_report(result: dict) -> str:
    """Ficha completa: contrato, seis rondas, modalidad, interpretación y limitaciones."""
    c = result["contrato"]
    name = c["variable"]
    output = f"# {name} — {c['label']}\n\n## Propósito y metodología\n\n"
    output += (f"Se describe **{c['label']}**, relevante para caracterizar la composición y los recursos de la población registrada, "
               "sin seleccionar una muestra predictiva. Unidad de fila: persona-ronda; fuente independiente F20. "
               f"Unidad de medición: {c['unit']}. Libro de códigos, p. {c['page']}; {c['reference']}.\n\n"
               f"**Población y filtros:** {c['eligibility']}\n\n"
               "Los porcentajes de cada categoría se calculan sobre N total y N válido por separado. "
               "Los especiales .f/.p/.w/.s y otros se conservan; no son categorías válidas ni ceros. "
               "8, 9, 88 y 99 no son códigos universales de no respuesta. "
               f"Dominio numérico documentado: inferior={c['lower']}, superior={c['upper']}; "
               "None indica que no se impuso un límite sin sustento. No se eliminan atípicos automáticamente.\n\n")
    output += "## Resultados por ronda\n\n" + md_table([{k:v for k,v in row.items() if k != "nota_elegibilidad"} for row in result["resumen"]])
    output += "\n### Respuestas válidas\n\n" + md_table(result["frecuencias"] if c["kind"] == "categorical" else result["histograma"])
    output += "\n### Partición completa y motivos de ausencia\n\n" + md_table(result["estados"])
    output += "\n### Desglose por modalidad\n\n" + md_table(result["por_modalidad"])
    if result["frecuencias_modalidad"]:
        output += "\n### Distribución de respuestas por modalidad\n\n" + md_table(result["frecuencias_modalidad"])
    output += f"\n## Distribuciones gráficas\n\n![Distribuciones de {name} por ronda](../../../reports/eda_independiente/figuras/{name}.png)\n\n"
    output += "## Interpretación estadística y económica\n\n"
    available = [r for r in result["resumen"] if r["N_valido"]]
    if available:
        output += "La cobertura válida es " + "; ".join(f"{r['anio']}: {r['N_valido']:,}/{r['N_total']:,} ({r['pct_valido_total']:.2f}%)" for r in result["resumen"]) + ". "
        if c["kind"] == "categorical":
            for year in dict.fromkeys([available[0]["anio"], available[-1]["anio"]]):
                rows = [r for r in result["frecuencias"] if r["anio"] == year]
                top = max(rows, key=lambda r:r["n"])
                output += f"En {year}, la categoría modal es «{top['respuesta']}», con {top['n']:,} registros ({top['pct_valido']:.2f}% de las respuestas válidas). "
        else:
            first, last = available[0], available[-1]
            for r in ([first, last] if first["anio"] != last["anio"] else [first]):
                output += f"En {r['anio']}, la mediana es {r['mediana']:,.2f}, el intervalo intercuartílico [{r['p25']:,.2f}; {r['p75']:,.2f}] y la media {r['media']:,.2f}. "
        output += c["interpretation"] + "\n\n"
    output += "## Comparabilidad y conclusión parcial\n\n" + c["temporal"] + " "
    output += ("No se estimó una transición individual ni una asociación entre esta variable y el patrimonio. "
               "La figura compara distribuciones de conjuntos de registros que cambian entre rondas; ausencia de instrumento no es ausencia del fenómeno. "
               "Los porcentajes son descriptivos sin ponderar y no prevalencias nacionales. "
               "La validación del dominio no resuelve por sí sola equivalencia de instrumentos ni selección por observación.\n")
    return output


def run(figures: bool = True) -> dict:
    """Ejecuta B00 y B01, separando universo completo de cada población válida."""
    DOCS.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    inventory = json.loads(read_project_text(project_path('', "docs/pensiones/inventario_fuentes.json")))
    simple, coverage = preflight(inventory)
    registry = json.loads(read_project_text(project_path('docs/eda', "contratos_simple.json")))
    analyzed = []
    for i, contract in enumerate(registry["contratos"], 1):
        spec = VariableSpec(**contract)
        result = analyze_variable(simple, spec)
        for row in result["resumen"]:
            states = [x["n"] for x in result["estados"] if x["anio"] == row["anio"]]
            assert sum(states) == row["N_total"]
        analyzed.append(result)
        directory = project_path('docs/eda', "variables")
        directory.mkdir(exist_ok=True)
        write_project_text(directory / f"{spec.variable}.md", variable_report(result))
        if figures:
            plot_variable(result, project_path('reports/eda_independiente', "figuras", f"{spec.variable}.png"))
        if i % 15 == 0: print(f"B01: {i}/91 variables descritas", flush=True)
    substantive = {name for name in simple if not simple_role(name).startswith("técnica")}
    assert substantive == {r["contrato"]["variable"] for r in analyzed}
    payload = {"fecha": "2026-10-12", "fuente": "F20", "archivo": "simpleMHAS.dta",
               "sha256": inventory["fuentes"][-1]["sha256"], "N_registros": len(simple),
               "N_personas": len(simple[["cunicah", "np"]].drop_duplicates()),
               "N_variables_analizadas": len(analyzed), "N_rondas": 6,
               "cobertura_fuentes": coverage, "resultados": analyzed}
    strict_json(payload, project_path('reports/eda_independiente', "simple_resultados.json"))
    # Marcar progreso solo después del cálculo y de todas las reconciliaciones.
    old_summary = md_table(coverage)
    final_source = next(s for s in coverage if s["Fuente"] == "F20")
    final_source["EDA observado"], final_source["Pendientes EDA"] = len(analyzed), 0
    ledger = json.loads(read_project_text(project_path('docs/eda', "cobertura_variables.json")))
    for entry in ledger:
        if entry["fuente"] == "F20" and not entry["rol"].startswith("técnica"):
            entry["estado"] = "EDA observado ejecutado, elegibilidad limitada"
    strict_json(ledger, project_path('docs/eda', "cobertura_variables.json"))
    coverage_doc = read_project_text(project_path('docs/eda', "COBERTURA_VARIABLES.md")).replace(old_summary, md_table(coverage))
    coverage_doc = coverage_doc.replace("B01: ENASEMsimple en ejecución; solo se cuenta terminado después de reconciliar todos sus agregados.",
                                        "B01: 91 variables de ENASEMsimple descritas en seis rondas, con elegibilidad limitada.")
    write_project_text(project_path('docs/eda', "COBERTURA_VARIABLES.md"), coverage_doc)
    strict_json(payload, project_path('reports/eda_independiente', "simple_resultados.json"))
    index = ("<!doctype html><html lang='es'><meta charset='utf-8'><title>EDA independiente F20</title>"
             "<style>body{font:16px system-ui;max-width:1250px;margin:auto;padding:24px}img{width:100%}section{margin-bottom:50px}</style>"
             "<h1>ENASEMsimple: 91 distribuciones por las seis rondas</h1><p>Sin filtros iniciales ni ponderación. "
             "N elegible no reconstruido. Figuras en revisión editorial.</p>")
    for result in analyzed:
        c = result["contrato"]
        index += f"<section id='{c['variable']}'><h2>{html.escape(c['label'])} ({c['variable']})</h2>"
        index += f"<p>{html.escape(c['temporal'])}</p><img loading='lazy' src='figuras/{c['variable']}.png' alt='{html.escape(c['label'])}'>"
        index += f"<a href='../../docs/eda/variables/{c['variable']}.md'>Ficha, tablas y metodología</a></section>"
    write_project_text(project_path('reports/eda_independiente', "index.html"), index + "</html>")
    print(f"B01 terminado técnicamente: {len(analyzed)} fichas, {len(analyzed)*6} resúmenes variable-ronda; universo={len(simple):,}.")
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sin-figuras", action="store_true")
    run(not parser.parse_args().sin_figuras)
