"""Síntesis y escritura del bloque K 2021 a partir de agregados independientes."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from tesis_enasem.independent_eda import strict_json
from tesis_enasem.manuscript import latex_number, render_latex_table
from run_independent_eda import md_table

ROOT=Path(__file__).resolve().parents[1]


def export() -> dict:
    """No carga microdatos; mantiene la trazabilidad y selecciona tablas académicas."""
    from tesis_enasem.release_guard import block_legacy_export
    block_legacy_export()
    payload=json.loads(read_project_text(project_path('', "reports/eda_independiente/k2021/resultados.json")))
    f03=next(s for s in payload["fuentes"] if s["fuente"]=="F03")
    selected=[("4_1","Deuda de negocio 1"),("47a","Salario principal propio"),("61_1_1","Jubilación propia 1"),
              ("80_1_1","Transferencia institucional propia 1"),("77","Apoyo COVID"),("88","Consumo mensual"),("111","Gasto por muerte del cónyuge")]
    pairs={r["componente"]:r for r in payload["comparaciones_derivado_imputado"]}
    table=[]
    for base,label in selected:
        d=f03["resultados"][f"amk{base}_21"]["resumen"]
        i=f03["resultados"][f"imamk{base}_21"]["resumen"]
        table.append({"Componente":label,"N derivado":d["N_valido"],"N imputado":i["N_valido"],"Recuperados":pairs[base]["N_recuperados"],
                      "Mediana derivada":d["mediana"],"Mediana imputada":i["mediana"]})
    write_project_text(project_path('', "manuscrito/tablas/eda_k2021_componentes.tex"), render_latex_table(
        pd.DataFrame(table).rename(columns={"N derivado":"N der.","N imputado":"N imp.","Recuperados":"Recup.","Mediana derivada":"Med. der.","Mediana imputada":"Med. imp."}),
        "Cobertura y medianas de componentes seleccionados K 2021", "tab:eda-k2021-componentes",
        "Der./imp.: derivado/imputado; recup.: faltantes recuperados. Fuente F03; 10,716 registros económicos de hogar/subhogar, sin ponderar. Universos de producto con ceros estructurales; no N de receptores. Jubilación, transferencia institucional y consumo: mensual; salario: periodicidad por confirmar; COVID: monto total; deuda: stock; muerte del cónyuge: gasto total y universo bruto pendiente. Las unidades no se suman.",
        column_format=r"p{0.32\linewidth}rrrrr"))
    coverage=[{"Fuente":s["fuente"],"N registros":s["N_registros"],"Variables descritas":s["N_variables_analizadas"]} for s in payload["fuentes"]]
    write_project_text(project_path('', "manuscrito/tablas/eda_k2021_cobertura.tex"), render_latex_table(pd.DataFrame(coverage),
        "Cobertura del bloque independiente K 2021", "tab:eda-k2021-cobertura",
        "F10 original y F03 imputada/derivada: entrevistas económicas de hogar/subhogar; F17: registros individuales construidos. No sumar N entre fuentes. F10 parcial, resto de columnas y otras rondas pendiente. Los cinco campos técnicos/punteros de F17 no publican niveles."))
    # Figura de recuperación: una proporción de producto, nunca tasa entre receptores.
    fig,ax=plt.subplots(figsize=(10,5),layout="constrained")
    ax.barh([label for _,label in selected],[100*pairs[b]["N_recuperados"]/f03["N_registros"] for b,_ in selected],color=plt.cm.BrBG(.92))
    ax.set_xlabel("Derivado faltante → imputado disponible (% de 10 716 registros del producto)")
    ax.set_title("Recuperación de cobertura en componentes seleccionados · K 2021")
    ax.spines[["top","right"]].set_visible(False)
    ax.grid(axis="x",alpha=.15)
    fig.savefig(project_path('', "manuscrito/figuras/borradores/eda_k2021_recuperacion.png"),dpi=140)
    plt.close(fig)
    measured={"variables":sum(s["N_variables_analizadas"] for s in payload["fuentes"]),
              "figuras":payload["N_figuras"],"pares":len(pairs),
              "componentes_con_recuperacion":sum(p["N_recuperados"]>0 for p in pairs.values()),
              "componentes_con_cambios_observados":sum(p["N_ambos_difieren"]>0 for p in pairs.values()),
              "componentes_con_bandera_discrepante":sum(p["N_recuperado_bandera_no_1"]>0 or p["N_recuperados"]!=p["N_bandera_1"] for p in pairs.values())}
    strict_json(measured,project_path('', "docs/eda/resumen_b02a.json"))
    macros={"edaKVariables":measured["variables"],"edaKPares":measured["pares"],
            "edaKComponentesRecuperados":measured["componentes_con_recuperacion"],
            "edaKConsumoRecuperados":pairs["88"]["N_recuperados"],
            "edaKPensionRecuperados":pairs["61_1_1"]["N_recuperados"],
            "edaKPunterosSinCoincidir":payload["orientacion_F17"]["N_sin_coincidencia"]}
    write_project_text(project_path('', "manuscrito/tablas/eda_k2021_cifras.tex"),
        "% Generado exclusivamente desde agregados K independientes.\n"+
        "".join("\\newcommand{\\"+name+"}{"+latex_number(value)+"}\n" for name,value in macros.items()))
    report_path=project_path('', "docs/eda/B02A_K_2021.md")
    existing_report=read_project_text(report_path)
    universe_suffix="\n## Revisión de universos de cónyuge"+existing_report.split("\n## Revisión de universos de cónyuge",1)[1] if "\n## Revisión de universos de cónyuge" in existing_report else ""
    report=existing_report.split("\n## Síntesis medida para revisión")[0]
    report+="\n## Síntesis medida para revisión\n\n"+md_table([measured])+"\n"+md_table(table)+"\n"
    report+=(f"De los 59 componentes, {measured['componentes_con_recuperacion']} recuperan al menos un valor faltante. "
             f"En {measured['componentes_con_cambios_observados']} componentes se detecta modificación de un derivado observado por encima de la tolerancia; "
             f"{measured['componentes_con_bandera_discrepante']} presentan desacuerdo entre número recuperado y bandera. "
             "Estos resultados se refieren exclusivamente al archivo suministrado, no prueban que su mecanismo de imputación sea ignorable. "
             f"Los {pairs['88']['N_recuperados']} valores recuperados de consumo equivalen a {100*pairs['88']['N_recuperados']/f03['N_registros']:.2f}% de los registros económicos. "
             f"En el primer componente de jubilación propia se recuperan {pairs['61_1_1']['N_recuperados']} montos, pero su denominador de producto no debe usarse como población pensionada. "
             "La mediana frecuentemente cero refleja componentes no recibidos y ceros construidos; describir solo la media ocultaría esa concentración.\n")
    write_project_text(report_path, report+universe_suffix)
    ledger=json.loads(read_project_text(project_path('', "docs/eda/cobertura_variables.json")))
    rows=[]
    for fid in sorted({r["fuente"] for r in ledger}):
        subset=[r for r in ledger if r["fuente"]==fid]
        technical=sum(r["rol"].startswith("técnica") for r in subset)
        done=sum(r["bloque"] in {"B01","B02a"} and not r["rol"].startswith("técnica") and "ejecutado" in r["estado"] for r in subset)
        rows.append({"Fuente":fid,"Columnas":len(subset),"Técnicas/punteros":technical,"Variables descritas":done,"Pendientes EDA":len(subset)-technical-done})
    write_project_text(project_path('', "docs/eda/COBERTURA_VARIABLES.md"),
        "# Control exhaustivo de cobertura\n\n5,368 filas fuente-variable, sin omisiones ni duplicación de entradas. B00 preservado: perfiles no cuentan como EDA semántico. "
        "B01: 91 variables descritas, comparativas conjuntas y universos del indicador revisados; aceptación académica abierta. "
        "B02a: 338 variables descritas de 2021, sin afirmar que K completo ni el resto de rondas estén terminados. "
        "Campos NP y punteros K45d/K52a_1 se auditan sin publicar niveles. F06/2024 separado; F04/F05 conservados ambos.\n\n"+md_table(rows)+
        "\nEl [JSON de cobertura](cobertura_variables.json) contiene cada columna, su estado, N y pendientes. "
        "[B01 revisión](B01_REVISION.md), [B02a resultados](B02A_K_2021.md). Los enlaces 2001/2003/2015/2018/2021 siguen abiertos en el inventario. "
        "Variables descritas no implica universo bruto/equivalencia/ponderación completamente validados. No hay integración definitiva.\n")
    print(measured)
    return measured


if __name__=="__main__":
    from tesis_enasem.release_guard import block_legacy_export
    block_legacy_export()
    export()
