"""Tablas, cifras y figuras LaTeX desde agregados de integración/J01, sin microdatos."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text

import json
from pathlib import Path

import pandas as pd

from tesis_enasem.manuscript import latex_number, render_latex_table

ROOT = Path(__file__).resolve().parents[1]


def export() -> None:
    """Selecciona evidencia académica y conserva el reporte exhaustivo externo."""
    from tesis_enasem.release_guard import block_legacy_export
    block_legacy_export()
    audit = json.loads(read_project_text(project_path('', "docs/integracion/validacion.json")))
    joint = json.loads(read_project_text(project_path('', "docs/integracion/eda_conjunto_inicial.json")))
    output = project_path('', "manuscrito/tablas")
    source_rows = [{"Fuente":r["fuente"],"Año":r["ano"],"N maestro":r["N_maestro_ronda_modalidad"],
                    "Enlazadas":r["N_enlazadas"],"Sin enlace":r["N_sin_enlace"],"Enlace (%)":r["pct_enlace"]}
                   for r in audit["cobertura"] if r["modalidad"] == "Todas"]
    write_project_text(output.joinpath("integracion_cobertura.tex"), render_latex_table(pd.DataFrame(source_rows),
        "Correspondencia económica por archivo y ronda, todas las modalidades", "tab:integracion-cobertura",
        "N: personas-ronda de ENASEMsimple. Porcentaje sobre N maestro de cada ronda, sin ponderar. F01–03/18–19: hogar imputado; F04/13–17: individual construido; F07–12: original de hogar. No sumar N de distintas fuentes. Cobertura por cinco modalidades y motivos en reporte reproducible.",long=True))
    display = {"propio_validado":"Titular propio validado", "conyuge_es_esta_persona_validado":"Cónyuge que es la persona de la fila",
               "sin_fuentes_2021":"Sin una o ambas fuentes", "puntero_hogar_individual_discrepante":"Puntero seleccionado discrepante",
               "orientacion_individual_no_confirmada":"Orientación individual no confirmada"}
    rows = [{"Estado de titularidad":display.get(k,k),"N":v,"% de ronda":100*v/17538} for k,v in audit["titularidad_2021"].items()]
    write_project_text(output.joinpath("integracion_titularidad.tex"), render_latex_table(pd.DataFrame(rows),
        "Asignación conservadora de titularidad económica en 2021", "tab:integracion-titularidad",
        "N total de la ronda: 17,538 personas-ronda. Requiere concordancia de NP del titular en hogar e individual, orientación key_21 y rama de pareja. Sin fuente o discrepante conserva NA en derivados personales. Los originales se mantienen.",column_format=r"p{0.65\linewidth}rr"))
    labels = {"pension_recibe_k_2021":"Recepción de pensión en K", "pension_contributiva_evidencia_2021":"Evidencia IMSS/ISSSTE en K",
              "apoyo_vejez_evidencia_2021":"Apoyo de vejez identificado", "apoyo_publico_recibe_2021":"Algún apoyo público"}
    rows = [{"Indicador 2021":labels[k],"Sí":v.get("True",0),"No en ámbito":v.get("False",0),"Desconocido":v.get("None",0)}
            for k,v in audit["pension_2021"].items()]
    write_project_text(output.joinpath("integracion_pensiones.tex"), render_latex_table(pd.DataFrame(rows),
        "Evidencia personal de pensiones y apoyos en 2021", "tab:integracion-pensiones",
        "Denominador: 17,538 registros de la ronda, sin ponderar. El no pensionario exige cuatro negativas K58/K64; no niega apoyos K79/K82. En la fila IMSS/ISSSTE, No indica negativa de pensión K, no ausencia global de toda pensión contributiva. Desconocido incluye no enlace, titular no validado y respuesta no concluyente. Indicadores auxiliares, no ocho homologaciones definitivas.",column_format=r"p{0.44\linewidth}rrr"))
    labels_joint = {"salud_glob":"Salud global", "n_sint_depr":"Síntomas depresivos", "recuerdo1":"Aprendizaje verbal", "n_abvd":"ABVD",
                    "n_aivd":"AIVD","educacion":"Escolaridad","edad":"Edad"}
    rows = []
    for name,label in labels_joint.items():
        a,b = [next(r for r in joint["asociaciones"] if r["ano"]==year and r["variable_y"]==name) for year in (2001,2021)]
        rows.append({"Variable":label,"ρ 2001":a["rho_spearman"],"N 2001":a["N_pares_validos"],"ρ 2021":b["rho_spearman"],"N 2021":b["N_pares_validos"]})
    write_project_text(output.joinpath("integracion_asociaciones.tex"), render_latex_table(pd.DataFrame(rows),
        "Asociaciones de patrimonio con dimensiones seleccionadas: extremos del periodo", "tab:integracion-asociaciones",
        "Spearman dentro de ronda, pares válidos sin filtros iniciales ni ponderación. Salud global: categoría alta indica peor salud; ABVD/AIVD: limitaciones. Cognición contiene imputación del proveedor. No identifica cambio individual, efecto causal ni representatividad. Todas las seis rondas y sus N están en notebook/reporte.",column_format="lrrrr").replace("ρ",r"$\rho$"))
    macros = {"intRegistros":audit["N_registros"],"intPersonas":audit["N_personas"],"intColumnas":audit["N_columnas_finales"],
              "intColumnasFuente":audit["N_columnas_fuente_conservadas"],"intFuentes":audit["N_fuentes_economicas_integradas"],
              "intPensionSi":audit["pension_2021"]["pension_recibe_k_2021"]["True"],
              "intVejezSi":audit["pension_2021"]["apoyo_vejez_evidencia_2021"]["True"],
              "intPunterosDiscrepantes":audit["titularidad_2021"]["puntero_hogar_individual_discrepante"],
              "intOrientacionPendiente":audit["titularidad_2021"]["orientacion_individual_no_confirmada"]}
    selected_stats = {}
    for name,key in [("n_sint_depr","intRhoDepresion"),("recuerdo1","intRhoCognicion"),("n_abvd","intRhoAbvd")]:
        r = next(a for a in joint["asociaciones"] if a["ano"]==2021 and a["variable_y"]==name)
        selected_stats[key] = latex_number(r["rho_spearman"],3)
        selected_stats[key+"Pares"] = latex_number(r["N_pares_validos"])
    for group,key in [("Sí validado","intMedianaPensionSi"),("Negativa explícita K","intMedianaPensionNo")]:
        r = next(a for a in joint["perfiles_bivariados_2021"] if a["recepcion_pension_K"]==group and a["variable"]=="imp_neto")
        selected_stats[key] = latex_number(r["mediana"],2)
    write_project_text(output.joinpath("integracion_cifras.tex"), "% Generado desde agregados; no editar cifras.\n"+
        "".join("\\newcommand{\\"+name+"}{"+latex_number(value)+"}\n" for name,value in macros.items())+
        "".join("\\newcommand{\\"+name+"}{"+value+"}\n" for name,value in selected_stats.items()))
    print("Integración: cuatro tablas y cifras exportadas desde agregados; dos figuras BrBG de J01 disponibles.")


if __name__ == "__main__":
    from tesis_enasem.release_guard import block_legacy_export
    block_legacy_export()
    export()
