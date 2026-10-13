"""Amplía B01 desde agregados existentes, sin volver a ejecutar sus descriptivos."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text, read_project_bytes

from copy import deepcopy
import argparse
from hashlib import sha256
import json
from pathlib import Path

from tesis_enasem.eda_review import comparison_table, eligible_summary, interpret_result, plot_comparison
from tesis_enasem.independent_eda import strict_json
from run_independent_eda import md_table, variable_report

ROOT = Path(__file__).resolve().parents[1]


def rules_for(contract: dict) -> dict:
    """Reglas explícitas del indicador; no imputan filtros de la pregunta bruta.

    Fuente: libro oficial v2, definición de especiales p. 8 y tabla individual
    citada. Se preservan como ND filtros laborales y excepción de hermanos 2012.
    """
    name = contract["variable"]
    all_modes = {"fallecido", "sexo", "mes_nac", "a_o_nac", "educacion", "edu_gru"}
    direct = set("salud_glob deprimido esfuerzo intranquilo feliz solo disf_vida triste cansado energia n_sint_depr cesd_deprimido n_aivd aivd_gru n_mov n_img motoras_gruesas motoras_finas recuerdo1 recuerdo1_flag recuerdo2 recuerdo2_flag copiafiguras1 copiafiguras1_flag copiafiguras2 copiafiguras2_flag visualscan visualscan_flag orientacion orientacion_flag serial7 memoria ejer_3_por_sem cuida_adulto cuida_menor voluntario asiste_cursos asiste_club lee cruci_rompe juegos_mesa comu_telef_comp act_mant ve_tv cose compras med_farm".split())
    from2012 = set("memoria cuida_adulto cuida_menor voluntario asiste_cursos asiste_club lee cruci_rompe juegos_mesa comu_telef_comp act_mant ve_tv cose".split())
    out = {}
    for year in [2001,2003,2012,2015,2018,2021]:
        modes = [1,2,3,4,5] if name in all_modes else ([1,2] if name in direct else [1,2,3,4])
        note = f"Universo del indicador construido: modalidades {modes}; definición de .f/.p y cuadro individual del libro v2, p. {contract['page']}. No equivale automáticamente a universo de cada pregunta bruta."
        if (name in from2012 and year < 2012) or (name in {"compras","med_farm"} and year != 2018) or (name in {"orientacion","orientacion_flag"} and year == 2001) or (name == "serial7" and year < 2015):
            modes, note = [], f"Instrumento no disponible según cuadro de {name}, libro v2 p. {contract['page']}; N elegible del indicador = 0, porcentaje ND."
        if name == "n_abvd_wh":
            modes = [1,2,3,4] if year == 2021 else [1,2]
            note = "Libro v2 p. 43: .p en 2001–2018, sin exclusión de sustituto en 2021; universo del índice construido."
        if name == "hermanos_vivos":
            modes = [1,2,3,4] if year in {2001,2003} else [1,2]
            note = "Libro v2 pp. 21–22: .p en 2015–2021, sin .p en 2001/2003."
            if year == 2012:
                modes, note = None, "ND: libro v2 registra 1,172 .p en 2012, menor que el total de sustitutos; no se reconstruye el subfiltro dentro de esa modalidad."
        if name in {"autoem","horas_trabajadas"}:
            modes, note = None, "ND: filtros laborales pp. 58–59 requieren preguntas brutas; ocupacion=1 no reproduce necesariamente la rama, especialmente autoem 2001/2003. No se resta .s para inventar elegibilidad."
            if name == "horas_trabajadas" and year == 2001:
                modes, note = [], "Sin instrumento en 2001, libro v2 p. 59; N elegible = 0."
        out[str(year)] = {"modalidades": modes, "nota": note, "alcance": "universo del indicador, no validación completa de saltos brutos"}
    return out


def review(figures: bool = True) -> dict:
    """Mantiene intacto simple_resultados.json; añade revisión reproducible separada."""
    path = project_path('', "reports/eda_independiente/simple_resultados.json")
    digest = sha256(read_project_bytes(path)).hexdigest()
    data = json.loads(read_project_text(path))
    reviewed, rules = {}, {}
    for original in data["resultados"]:
        name = original["contrato"]["variable"]
        rule = rules_for(original["contrato"])
        eligibility = eligible_summary(original, rule)
        anomalies = [r for r in eligibility if r["N_valido_fuera_universo"] not in {None,0}]
        if anomalies:
            raise ValueError(f"Universo no conciliado: {name}: {anomalies}")
        table = comparison_table(original)
        discussion = interpret_result(original, eligibility)
        reviewed[name] = {"universos": eligibility, "tabla_comparativa": table, "interpretacion": discussion}
        rules[name] = rule
        plot_path = project_path('', f"reports/eda_independiente/comparativas/{name}.png")
        if figures:
            plot_comparison(original, plot_path)
        else:
            assert plot_path.exists(), f"Falta figura comparativa: {name}"
        enriched = deepcopy(original)
        for row, eligible in zip(enriched["resumen"], eligibility):
            row["N_elegible"] = eligible["N_elegible"]
            row["nota_elegibilidad"] = eligible["regla"]
        text = variable_report(enriched).split("## Interpretación estadística y económica")[0]
        text += "## Universos reconstruidos y cobertura\n\n" + md_table(eligibility)
        text += "\nN elegible corresponde al **indicador construido** cuando su disponibilidad por modalidad/ronda está documentada. Los saltos de preguntas originales no reconstruidos permanecen ND. Negativas, desconocimiento y otras ausencias dentro del universo no se eliminan del denominador.\n\n"
        text += "## Comparación conjunta entre rondas\n\n" + md_table(table)
        text += f"\n![Comparación conjunta de {name}](../../../reports/eda_independiente/comparativas/{name}.png)\n\n"
        text += "## Interpretación estadística y económica\n\n" + discussion + "\n"
        write_project_text(project_path('', f"docs/eda/variables/{name}.md"), text)
    assert sha256(read_project_bytes(path)).hexdigest() == digest
    rows = [r for item in reviewed.values() for r in item["universos"]]
    result = {"sha256_agregados_originales": digest, "variables": reviewed,
              "N_figuras_comparativas": len(reviewed), "N_tablas_comparativas": len(reviewed),
              "universos_conocidos": sum(r["N_elegible"] is not None for r in rows),
              "universos_ND": sum(r["N_elegible"] is None for r in rows),
              "alcance": "Universos de indicadores construidos, no reconstrucción integral de preguntas originales; sin ponderar."}
    strict_json(result, project_path('', "reports/eda_independiente/simple_revision.json"))
    strict_json({"fuente": "Libro ENASEMsimple v2, enero 2025; definiciones p. 8 y páginas individuales", "reglas": rules}, project_path('', "docs/eda/universos_simple.json"))
    ledger_path = project_path('', "docs/eda/cobertura_variables.json")
    ledger = json.loads(read_project_text(ledger_path))
    for row in ledger:
        if row["fuente"] == "F20" and row["variable"] in reviewed:
            item = reviewed[row["variable"]]
            row.update(comparativa_conjunta=True, tabla_comparativa=True,
                       universos_por_ronda=item["universos"],
                       pendiente="Causa de n_res, universos de preguntas brutas, ponderación/comparabilidad y aceptación académica; ver ficha")
    strict_json(ledger, ledger_path)
    report = ("# Revisión adicional de B01\n\n**Estado: validación académica abierta.** No se repitieron los descriptivos ni se modificó su JSON original.\n\n"
              f"Se añadieron {len(reviewed)} figuras conjuntas BrBG y {len(reviewed)} tablas numéricas, una por variable. Las 91 láminas de seis paneles se conservan. "
              f"Se reconstruyeron {result['universos_conocidos']}/546 universos de indicadores variable-ronda; {result['universos_ND']} quedan ND. "
              "Este conteo no equivale a reconstruir todos los filtros de las preguntas brutas. En horas trabajadas 2001 y otras rondas sin instrumento N elegible=0, porcentaje ND. "
              "No hubo valores válidos fuera de los universos reconstruidos. La reconstrucción utiliza modalidades documentadas y no N válido, ni resta automáticamente saltos .s.\n\n"
              "Los pendientes específicos son autoem (seis rondas), horas_trabajadas (2003–2021) y hermanos_vivos (2012, exclusión parcial del sustituto). "
              "Las fichas contienen cifras y contrastes propios: cambios de categorías en puntos porcentuales, cuantiles, colas, ceros y cobertura sobre universo elegible. "
              "La figura numérica compara P05/P25/mediana/P75/P95 sobre una escala común; no son intervalos de confianza. "
              "Las categorías se comparan mediante porcentajes válidos con frecuencias y denominadores en la tabla. Rondas sin instrumento no se grafican como tasas cero.\n\n"
              "Los resultados continúan sin ponderar. No son estimaciones nacionales; los pesos transversales no se convierten en longitudinales. "
              "Patrimonio conserva negativos y ceros en unidades almacenadas; comparar cuantiles no demuestra crecimiento real ni equivalencia monetaria.\n\n"
              "Abrir [notebook 03](../../notebooks/03_eda_univariado.ipynb), su copia ejecutada local en reports/notebooks, o las [91 fichas](B01_ENASEMSIMPLE.md). "
              "La investigación de n_res se encuentra en [N_RES_VERSIONES.md](N_RES_VERSIONES.md).\n\n"
              f"SHA-256 de agregados preservados: `{digest}`. Reproducción: `python scripts/review_b01.py`.\n")
    write_project_text(project_path('', "docs/eda/B01_REVISION.md"), report)
    print({k:v for k,v in result.items() if k != "variables"})
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tables-only", action="store_true", help="Actualizar texto/tablas conservando figuras ya verificadas")
    args = parser.parse_args()
    review(figures=not args.tables_only)
