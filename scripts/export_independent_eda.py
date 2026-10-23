"""Sincroniza síntesis académica y tablas LaTeX a partir del EDA agregado real."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text

import json
from pathlib import Path
import shutil

import pandas as pd

from tesis_enasem.independent_eda import strict_json
from tesis_enasem.manuscript import FrequencyCell, latex_number, render_latex_table
from run_independent_eda import md_table

ROOT = Path(__file__).resolve().parents[1]


def export() -> dict:
    """Solo recibe agregados; nunca carga microdatos ni construye una base integrada."""
    from tesis_enasem.release_guard import block_legacy_export
    block_legacy_export()
    data = json.loads(read_project_text(project_path('', "reports/eda_independiente/simple_resultados.json")))
    registry = json.loads(read_project_text(project_path('', "docs/eda/contratos_simple.json")))
    results = {r["contrato"]["variable"]: r for r in data["resultados"]}
    revision_path = project_path('', "reports/eda_independiente/simple_revision.json")
    revision = json.loads(read_project_text(revision_path)) if revision_path.exists() else None
    actual = {(name, r["anio"]): r for name, item in results.items() for r in item["resumen"]}
    differences = []
    checked = []
    for printed in registry["estadisticos_impresos_proveedor"]:
        row = actual.get((printed["variable"], printed["anio"]))
        if row is None or "media" not in row or row["media"] is None: continue
        # Tolerancia declarada para redondeo de medias impresas; no prueba inferencial.
        tolerance = max(.0001, abs(row["media"]) * .000005)
        different = printed["N_libro"] != row["N_valido"] or abs(printed["media_libro"]-row["media"]) > tolerance
        check = {"variable": printed["variable"], "anio": printed["anio"], "N_libro": printed["N_libro"],
                 "N_datos": row["N_valido"], "media_libro_v2": printed["media_libro"],
                 "media_datos_v3": row["media"], "tolerancia_redondeo": tolerance, "diferencia": different}
        checked.append(check)
        if different: differences.append(check)
    counts = {key: sum(len(r[key]) for r in results.values()) for key in
              ["resumen", "frecuencias", "estados", "histograma", "por_modalidad", "frecuencias_modalidad"]}
    strict_json({"metodo": "Solo medias/N de cuadros numéricos extraíbles: no validación exhaustiva de equivalencia v2/v3.",
                 "comparaciones": checked, "diferencias": differences}, project_path('', "docs/eda/cotejo_libro_versiones.json"))
    figures = len(list((project_path('', "reports/eda_independiente/figuras")).glob("*.png")))
    assert figures == 91 and len(actual) == 546
    selected = ["edad", "educacion", "n_res", "diabetes", "n_sint_depr", "bmi_imp", "horas_trabajadas", "imp_neto", "compras", "serial7"]
    coverage = pd.DataFrame([{ "Variable": name, **{str(year): actual[(name, year)]["N_valido"] for year in [2001,2003,2012,2015,2018,2021]}} for name in selected])
    tables = project_path('', "manuscrito/tablas")
    tables.mkdir(exist_ok=True)
    write_project_text(tables / "eda_simple_cobertura.tex", render_latex_table(
        coverage, "Cobertura válida de variables seleccionadas de ENASEMsimple", "tab:eda-simple-cobertura",
        "N de registros persona-ronda con valores válidos. Cero indica ausencia de respuestas disponibles, no ausencia del fenómeno. Universo completo sin ponderar; reconstrucción de universos en tabla de denominadores y fichas."))
    if revision:
        denominator_rows = []
        for name in ["edad", "diabetes", "n_sint_depr", "autoem"]:
            for row in revision["variables"][name]["universos"]:
                denominator_rows.append({"Variable":name,"Ronda":str(row["anio"]),"N total":row["N_total"],"N elegible":row["N_elegible"] if row["N_elegible"] is not None else "ND","N válido":row["N_valido"]})
        write_project_text(tables / "eda_simple_universos.tex", render_latex_table(pd.DataFrame(denominator_rows),
            "Denominadores de indicadores seleccionados", "tab:eda-simple-universos",
            "Universos del indicador construido documentados por modalidad/disponibilidad, no reconstrucción de todas las preguntas brutas. ND conserva filtro laboral no reconstruido. No respuesta no se excluye del N elegible. Sin ponderar."))
    wealth = pd.DataFrame([{ "Ronda": str(r["anio"]), "N válido": r["N_valido"], "P25": r["p25"],
                            "Mediana": r["mediana"], "P75": r["p75"], "Ceros": r["N_ceros"], "Negativos": r["N_negativos"]}
                          for r in results["imp_neto"]["resumen"]])
    write_project_text(tables / "eda_simple_patrimonio.tex", render_latex_table(
        wealth, "Distribución patrimonial dentro de cada ronda", "tab:eda-simple-patrimonio",
        "Unidades monetarias almacenadas, sin deflactar ni validar comparabilidad real. Titular: entrevistado y cónyuge si existe. Cuantiles entre valores disponibles; no ingreso ni montos de pensión. No sumar estos registros como hogares independientes."))
    health_rows = []
    for year in [2001,2003,2012,2015,2018,2021]:
        row = {"Ronda": str(year)}
        for name, short in [("diabetes", "Diabetes"), ("hipertension", "Hipertensión"), ("cesd_deprimido", "CES-D: 5+ síntomas")]:
            c = next(r for r in results[name]["frecuencias"] if r["anio"] == year and r["codigo"] == "1")
            row[short] = FrequencyCell(c["n"], c["pct_valido"])
        health_rows.append(row)
    denominator_note = "; ".join(name + ": " + ", ".join(str(r["N_valido"]) for r in results[key]["resumen"])
                                  for key, name in [("diabetes", "diabetes"), ("hipertension", "hipertensión"), ("cesd_deprimido", "CES-D")])
    write_project_text(tables / "eda_simple_salud.tex", render_latex_table(
        pd.DataFrame(health_rows), "Respuestas afirmativas en salud y síntomas depresivos", "tab:eda-simple-salud",
        "Frecuencia absoluta y porcentaje del N válido de cada variable/ronda, sin ponderar. N válido " + denominator_note + ". Autorreportes diagnósticos e índice de síntomas; no estimaciones nacionales ni diagnóstico psiquiátrico."))
    version_table = pd.DataFrame([{ "Ronda": str(d["anio"]), "N": d["N_datos"], "Media libro v2": d["media_libro_v2"],
                                   "Media archivo v3": d["media_datos_v3"]} for d in differences if d["variable"] == "n_res"])
    write_project_text(tables / "eda_simple_versiones.tex", render_latex_table(
        version_table, "Diferencias verificadas en la media de residentes del hogar", "tab:eda-simple-versiones",
        "Libro v2 enero 2025, p. 19, frente a archivo etiquetado v3 enero 2025. N coincide en las cuatro rondas. No se identifica automáticamente la causa ni se modifica el archivo."))
    drafts = project_path('', "manuscrito/figuras/borradores")
    drafts.mkdir(exist_ok=True)
    for name in ["bmi_imp", "imp_neto"]:
        shutil.copyfile(project_path('', "reports/eda_independiente/figuras", f"{name}.png"), drafts / f"eda_{name}.png")
        if revision:
            shutil.copyfile(project_path('', "reports/eda_independiente/comparativas", f"{name}.png"), drafts / f"eda_comparativa_{name}.png")
    macros = {"edaVariables": len(results), "edaLaminas": figures, "edaResumenenes": counts["resumen"],
              "edaCotejos": len(checked), "edaDiferencias": len(differences)}
    if revision:
        macros.update(edaComparativas=revision["N_figuras_comparativas"],edaUniversosConocidos=revision["universos_conocidos"],edaUniversosND=revision["universos_ND"])
    for name, label in [("diabetes", "Diabetes"), ("hipertension", "Hipertension"), ("cesd_deprimido", "Cesd")]:
        for year, suffix in [(2001,"Inicial"),(2021,"Final")]:
            c = next(r for r in results[name]["frecuencias"] if r["anio"] == year and r["codigo"] == "1")
            macros["eda"+label+suffix] = latex_number(c["pct_valido"], 2) + r"\%"
    for year in [2001,2021]:
        macros[f"edaMedianaPatrimonio{'Inicial' if year==2001 else 'Final'}"] = latex_number(actual[("imp_neto",year)]["mediana"], 2)
    macro_text = "% Generado desde agregados; no transcribir resultados manualmente.\n"
    for name, value in macros.items():
        macro_text += "\\newcommand{\\"+name+"}{"+(latex_number(value) if isinstance(value,int) else value)+"}\n"
    write_project_text(tables / "eda_simple_cifras.tex", macro_text)
    report = ("# EDA independiente — B01 ENASEMsimple\n\n"
              "**Estado:** primer bloque descriptivo ejecutado; aceptación académica pendiente. "
              "El EDA exhaustivo de las demás fuentes sigue pendiente de validación semántica. "
              "El bloque B00 revisó las 20 fuentes y todas sus 5,368 columnas; sus perfiles de códigos/faltantes no cuentan como EDA concluido.\n\n"
              "## Objetivo y metodología\n\n"
              f"Se caracterizan las {len(results)} variables sustantivas y banderas del archivo completo: "
              f"{data['N_registros']:,} registros de {data['N_personas']:,} personas, seis rondas, 119 columnas. "
              "Las 28 columnas de claves, diseño y pesos se auditan sin publicar sus valores. Se preservan todos los registros, "
              "menores de 60 años y modalidades de entrevista. Los agregados se producen independientemente de los archivos de K, sin unión definitiva.\n\n"
              "El contrato de cada variable cita la página del libro, define dominio/códigos, unidad, filtros documentados y límites de comparación. "
              "Se preservan los tags Stata antes de convertir valores para descriptivos; el índice de síntomas admite 8 y 9 como puntuaciones válidas. "
              "No se aplican reglas globales 8/9/88/99. Cuando el universo exacto de pregunta no se reconstruye, N elegible se declara ND "
              "y se describen únicamente valores disponibles; N válido jamás se presenta como N elegible. "
              "Cada categoría incluye frecuencia, % del total y % de respuestas válidas. Se calculan cuantiles, media, DE, extremos, ceros y negativos "
              "para medidas numéricas; no se promedian códigos nominales u ordinales. No hay imputación adicional, corrección automática ni ponderación.\n\n"
              "## Cobertura por ronda\n\n" + md_table(coverage.to_dict("records")) + "\n")
    for year in [2001,2003,2012,2015,2018,2021]:
        report += f"## Ronda {year}\n\n"
        n = actual[("edad",year)]["N_total"]
        age = actual[("edad",year)]
        report += (f"La ronda contiene {n:,} registros, sin filtros de edad o entrevista. "
                   f"La edad está disponible en {age['N_valido']:,}; su mediana es {age['mediana']:.0f} años. "
                   "Esta composición debe considerarse antes de atribuir diferencias de salud o patrimonio al paso del tiempo.\n\n")
        rows = []
        for name in ["edad", "educacion", "n_res", "n_enf", "n_sint_depr", "n_abvd", "n_aivd", "recuerdo1", "bmi_imp", "horas_trabajadas", "imp_neto"]:
            s = actual[(name,year)]
            rows.append({"Variable": name, "N total": n, "N válido": s["N_valido"], "% válido/total": s["pct_valido_total"],
                         "P25": s["p25"], "Mediana": s["mediana"], "P75": s["p75"], "Media": s["media"]})
        report += md_table(rows) + "\n"
        d = next(c for c in results["diabetes"]["frecuencias"] if c["anio"]==year and c["codigo"]=="1")
        cesd = next(c for c in results["cesd_deprimido"]["frecuencias"] if c["anio"]==year and c["codigo"]=="1")
        w = actual[("imp_neto",year)]
        report += (f"En {year}, diabetes afirmativa reúne {d['n']:,}/{d['N_valido']:,} ({d['pct_valido']:.2f}% válido), "
                   f"mientras que cinco o más síntomas CES-D reúne {cesd['n']:,}/{cesd['N_valido']:,} ({cesd['pct_valido']:.2f}%). "
                   "Estos denominadores difieren por cobertura/modalidad: no se presentan como proporciones de la misma población elegible. "
                   f"El patrimonio tiene mediana {w['mediana']:,.2f} y P25–P75 [{w['p25']:,.2f}; {w['p75']:,.2f}], "
                   f"con {w['N_ceros']:,} ceros y {w['N_negativos']:,} negativos preservados. Son unidades almacenadas, sin validar crecimiento real. ")
        if year in {2003,2012,2015,2018}:
            report += "La media de n_res difiere del libro v2 en esta ronda; no se atribuye su causa ni se corrige la distribución. "
        if year == 2018:
            report += "Compras y médico/farmacia solo se observan en esta ronda: permiten descripción puntual, no una tendencia de seis rondas. "
        if year in {2001,2003}:
            report += "Memoria y la mayoría de participación aún no están instrumentadas: su falta de valores no indica ausencia de participación. "
        report += "Las comparativas conjuntas y las interpretaciones específicas de las 91 variables permanecen en fichas y notebook; no se estima todavía asociación ni capacidad predictiva.\n\n"
    report += "## Salud, síntomas y comparación entre rondas\n\n"
    health_md = []
    for year in [2001,2003,2012,2015,2018,2021]:
        for name in ["diabetes", "hipertension", "cesd_deprimido"]:
            c = next(r for r in results[name]["frecuencias"] if r["anio"] == year and r["codigo"] == "1")
            health_md.append({"Ronda": year, "Variable": name, "Sí": c["n"], "N válido": c["N_valido"], "% sí/válido": c["pct_valido"], "% sí/total": c["pct_total"]})
    report += md_table(health_md) + "\n"
    def affirmative(name: str, year: int) -> float:
        return next(r["pct_valido"] for r in results[name]["frecuencias"] if r["anio"] == year and r["codigo"] == "1")
    report += (f"La proporción observada de diabetes pasa de {affirmative('diabetes',2001):.2f}% a {affirmative('diabetes',2021):.2f}% entre respuestas válidas de 2001 y 2021. "
               f"El indicador de cinco o más síntomas pasa de {affirmative('cesd_deprimido',2001):.2f}% a {affirmative('cesd_deprimido',2021):.2f}%. Son diferencias descriptivas de composición: "
               "no demuestran evolución individual, efecto de programas, deterioro clínico o mejora atribuible a ingreso. "
               "N válidos y modalidades cambian; la comparación exige revisar instrumentos, entradas, fallecimiento y selección por respuesta.\n\n")
    report += "## Patrimonio y estado corporal\n\n" + md_table(wealth.to_dict("records")) + "\n"
    report += ("Se conserva patrimonio negativo y cero, y se muestran todas las colas en histogramas de intervalos compartidos, "
               "sin winsorización ni logaritmo que elimine valores no positivos. Las medias patrimoniales superan las medianas, "
               "compatibles con asimetría hacia valores elevados. El título económico incluye al entrevistado y su cónyuge; "
               "sumar registros podría duplicar unidades económicas. No se estima crecimiento real, pobreza ni un corte de vulnerabilidad. "
               "Las unidades y precios deben validarse antes de comparaciones económicas temporales. El IMC se distribuye en escala original kg/m² "
               "junto con su bandera de imputación y categoría; no se trata como medida clínica directa ni se evalúa su efecto patrimonial.\n\n")
    report += "## Diferencias entre documento y archivo\n\n" + md_table(differences) + "\n"
    report += (f"Se cotejaron automáticamente {len(checked)} pares variable-ronda con cuadros numéricos extraíbles del libro "
               f"y se encontraron {len(differences)} diferencias en medias que exceden la tolerancia de redondeo declarada. "
               "Todas corresponden a n_res en 2003/2012/2015/2018, con N iguales. "
               "Cambios entre versiones, cambios de construcción y error documental son hipótesis **no comprobadas**. "
               "Falta cotejar la definición y la nota de cambios con el proveedor. No se alteran registros. "
               f"El cotejo de {len(checked)} cuadros no valida exhaustivamente todas las columnas ni todos los universos.\n\n")
    report += "## Cobertura instrumental y límites\n\n"
    report += ("Compras y visitas a médico/farmacia como uso del tiempo solo tienen datos en 2018. Serial7 empieza en 2015, "
               "orientacion en 2003, memoria y la mayoría de participación en 2012. Horas_trabajadas no está disponible en 2001. "
               "No representar rondas sin instrumento como tasas cero. Las banderas de imputación se describen por separado; "
               "antes de usar datos construidos como predictores se debe verificar si la imputación utilizó información de rondas posteriores. "
               "El EDA no demuestra ausencia de fuga temporal en productos del proveedor. Filtros laborales y universo exacto de pregunta "
               "son pendientes explícitos, al igual que equivalencias entre originales, imputados y construidos.\n\n")
    report += "## Artefactos y control de cobertura\n\n"
    report += md_table([{"Familia de tabla": key, "Filas agregadas": value} for key,value in counts.items()]) + "\n"
    report += (f"Se generaron {len(results)} fichas completas y {figures} láminas BrBG, con seis paneles por variable. "
               "Cada ficha contiene metodología, resultados por ronda, códigos, partición de ausencia, modalidad, interpretación y límites. "
               "Las frecuencias/histogramas se reconcilian con N válido, y todos los estados con N total. "
               "No se detectaron valores fuera de los dominios declarados; esto no valida veracidad individual ni equivalencia entre versiones.\n\n")
    report += "| Variable | Ficha completa | Página del libro |\n| --- | --- | --- |\n"
    for name, item in results.items():
        report += f"| `{name}` | [{item['contrato']['label']}](variables/{name}.md) | {item['contrato']['page']} |\n"
    if revision:
        report += ("\n## Revisión posterior sin repetir descriptivos\n\n"
                   f"Se añadieron {revision['N_figuras_comparativas']} figuras conjuntas entre rondas y sus 91 tablas, con interpretaciones específicas en cada ficha y notebook. "
                   f"Se reconstruyeron {revision['universos_conocidos']}/546 universos del indicador construido; {revision['universos_ND']} permanecen ND. "
                   "Esto no valida todos los saltos de preguntas originales. **B01 sigue pendiente de aceptación**, especialmente causa de n_res, filtros laborales y hermanos 2012. "
                   "El enunciado inicial sobre N elegible no reconstruido describe la primera ejecución; el estado actualizado y las reglas están en [B01_REVISION.md](B01_REVISION.md) "
                   "y [universos_simple.json](universos_simple.json). Véase [investigación n_res](N_RES_VERSIONES.md), incluidas DE/máximos y cotejos ES/EN/modalidad/unidad.\n")
    write_project_text(project_path('', "docs/eda/B01_ENASEMSIMPLE.md"), report)
    strict_json({"bloque": "B01", "variables": len(results), "figuras": figures, "comparativas_conjuntas": 91 if revision else 0,
                 "universos_reconstruidos": revision["universos_conocidos"] if revision else 0, "filas_tablas": counts,
                 "diferencias_documentales": differences, "estado": "EDA observado ejecutado; validación de universos y revisión académica pendientes"},
                project_path('', "docs/eda/resumen_b01.json"))
    print(f"Exportados: 4 tablas académicas, macros, síntesis B01 y 2 figuras de manuscrito en revisión. Cotejos={len(checked)}, diferencias={len(differences)}.")
    return data


if __name__ == "__main__":
    from tesis_enasem.release_guard import block_legacy_export
    block_legacy_export()
    export()
