"""Primer bloque conjunto tras validar integración: asociaciones por onda y perfiles 2021."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text, read_project_bytes

import json
from hashlib import sha256
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from tesis_enasem.independent_eda import VariableSpec, validate_values
from tesis_enasem.integration import load_integrated, restore_stata, YEARS
from tesis_enasem.joint_eda import paired_spearman, stratified_descriptions
from run_longitudinal_integration import md_table, write_json

ROOT = Path(__file__).resolve().parents[1]
LABELS = {"salud_glob":"Salud global (alto = peor)", "n_sint_depr":"Síntomas depresivos",
          "recuerdo1":"Aprendizaje verbal imputado", "n_abvd":"Limitaciones ABVD",
          "n_aivd":"Limitaciones AIVD", "educacion":"Escolaridad inicial", "edad":"Edad"}


def run() -> dict:
    """Lee solo columnas validadas, conserva referencia completa y denominadores."""
    audit = json.loads(read_project_text(project_path('', "docs/integracion/validacion.json")))
    if audit["N_registros"] != 99676 or not audit["roundtrip_todas_columnas"]:
        raise ValueError("Se requiere integración validada")
    if sha256(read_project_bytes(project_path('', "data/processed/enasem_integrada_provisional.parquet"))).hexdigest() != audit["hash_parquet"]:
        raise ValueError("Parquet distinto de la base validada")
    specs = {s["variable"]:VariableSpec(**s) for s in json.loads(read_project_text(project_path('', "docs/eda/contratos_simple.json")))["contratos"]}
    selected = ["imp_neto",*LABELS]
    columns = ["ronda","ano","tipent","pension_recibe_k_2021","apoyo_vejez_evidencia_2021"]
    columns += [c for v in selected for c in (v,v+"__stata_tag")]
    frame = load_integrated(project_path('', "data/processed/enasem_integrada_provisional.parquet"), columns)
    clean = frame[["ronda","ano","tipent","pension_recibe_k_2021","apoyo_vejez_evidencia_2021"]].copy()
    for name in selected:
        clean[name],_ = validate_values(restore_stata(frame[name], frame[name+"__stata_tag"]), specs[name])
    associations = []
    for wave,year in enumerate(YEARS,1):
        part = clean.loc[clean.ronda.eq(wave)]
        for name in LABELS:
            associations.append(paired_spearman(part,"imp_neto",name,year))
    part = clean.loc[clean.ronda.eq(6)].copy()
    part["recepcion_pension_K"] = part.pension_recibe_k_2021.map({True:"Sí validado",False:"Negativa explícita K"}).fillna("Desconocida")
    part["apoyo_vejez"] = part.apoyo_vejez_evidencia_2021.map({True:"Sí identificado",False:"No apoyo público confirmado"}).fillna("Desconocido")
    part["sintomas_grupo"] = np.where(part.n_sint_depr.isna(),"No válido",np.where(part.n_sint_depr.ge(5),"5 o más","0 a 4"))
    bivariate = stratified_descriptions(part,["recepcion_pension_K"],["imp_neto",*LABELS])
    trivariate = stratified_descriptions(part,["recepcion_pension_K","sintomas_grupo"],["imp_neto"])
    protection = [{"recepcion_pension_K":a,"apoyo_vejez":b,"N":len(g),"pct_ronda":100*len(g)/len(part)}
                  for (a,b),g in part.groupby(["recepcion_pension_K","apoyo_vejez"],observed=True)]
    payload = {"fecha":"2026-10-12","bloque":"J01 inicial, no exhaustivo", "N_referencia":len(frame),
               "N_variables_sustantivas":10,"N_tablas_asociacion":len(associations),
               "hash_base":audit["hash_parquet"], "asociaciones":associations,"perfiles_bivariados_2021":bivariate,
               "perfiles_trivariados_2021":trivariate,"proteccion_cruzada_2021":protection,
               "limites":"Sin pesos/deflactor, selección por disponibilidad de pares y titular. Patrimonio de pareja no es ingreso individual. Cognición contiene imputación del proveedor. No trayectorias, causalidad, modelos o suficiencia monetaria."}
    write_json(project_path('', "docs/integracion/eda_conjunto_inicial.json"),payload)
    figdir = project_path('', "manuscrito/figuras/borradores")
    fig,ax = plt.subplots(figsize=(10,5.8),layout="constrained")
    pivot = pd.DataFrame(associations).pivot(index="variable_y",columns="ano",values="rho_spearman").reindex(list(LABELS))
    plotted = ax.imshow(pivot.values,cmap="BrBG",vmin=-1,vmax=1,aspect="auto")
    ax.set_xticks(range(6),YEARS); ax.set_yticks(range(len(LABELS)),[LABELS[k] for k in LABELS])
    for i in range(len(LABELS)):
        for j in range(6):
            v = pivot.values[i,j]
            ax.text(j,i,f"{v:.2f}" if pd.notna(v) else "ND",ha="center",va="center",fontsize=10)
    ax.set_title("Asociación con patrimonio dentro de cada ronda · pares válidos\nSpearman sin ponderar; N por celda en tabla numérica")
    fig.colorbar(plotted,ax=ax,label="ρ de Spearman")
    fig.savefig(figdir/"integracion_spearman.png",dpi=150); plt.close(fig)
    fig,ax = plt.subplots(figsize=(9,4.7),layout="constrained")
    colors = {"Sí validado":plt.cm.BrBG(.08),"Negativa explícita K":plt.cm.BrBG(.92),"Desconocida":plt.cm.BrBG(.35)}
    for group,color in colors.items():
        rows = [r for r in trivariate if r["recepcion_pension_K"] == group]
        xpos = {"0 a 4":0,"5 o más":1,"No válido":2}
        offset = {"Sí validado":-.22,"Negativa explícita K":0,"Desconocida":.22}[group]
        for r in rows:
            if r["mediana"] is None: continue
            x = xpos[r["sintomas_grupo"]]+offset
            ax.errorbar(x,r["mediana"],yerr=[[r["mediana"]-r["p25"]],[r["p75"]-r["mediana"]]],fmt="o",color=color,capsize=4,
                        label=group if r == rows[0] else None)
    ax.set_xticks(range(3),["0–4 síntomas","≥5 síntomas","Síntomas no válidos"])
    ax.set_ylabel("Patrimonio almacenado: mediana y RIC\npersona y pareja, unidades monetarias de fuente")
    ax.set_title("2021 · patrimonio, pensión K y síntomas depresivos\nDescriptivo por registros; no estimación de efectos")
    ax.legend(fontsize=9); ax.grid(axis="y",alpha=.15)
    fig.savefig(figdir/"integracion_perfiles_2021.png",dpi=150);plt.close(fig)
    report = "# J01 · Inicio del EDA conjunto\n\nBase provisional validada, universo completo. Nuevos agregados; no se repiten los EDA univariados correctos. "
    report += "Ocho medidas de ENASEMsimple y dos indicadores provisionales 2021; 42 asociaciones por ronda, perfiles bivariados y trivariados, dos figuras BrBG. N total, pares válidos y faltantes explícitos.\n\n"
    report += "## Asociaciones dentro de ronda\n\n" + md_table(associations,["ano","variable_y","N_total_ronda","N_pares_validos","N_sin_par","rho_spearman"])
    report += "\n## Patrimonio, pensión y síntomas: 2021\n\n" + md_table(trivariate,["recepcion_pension_K","sintomas_grupo","N_estrato","N_valido","N_no_valido","mediana","p25","p75"])
    report += "\n## Pensiones K y apoyo de vejez identificado\n\n" + md_table(protection,["recepcion_pension_K","apoyo_vejez","N","pct_ronda"])
    report += "\n## Interpretación de resultados\n\n"
    for name in ["n_sint_depr","recuerdo1","n_abvd"]:
        a = next(r for r in associations if r['ano']==2001 and r['variable_y']==name)
        b = next(r for r in associations if r['ano']==2021 and r['variable_y']==name)
        report += f"{LABELS[name]}: ρ={a['rho_spearman']:.3f} (2001, N={a['N_pares_validos']:,}) y {b['rho_spearman']:.3f} (2021, N={b['N_pares_validos']:,}). "
        report += "La comparación describe asociaciones transversales de distintas composiciones y cobertura; no mide cambios individuales ni efectos de salud sobre recursos.\n\n"
    for r in bivariate:
        if r["variable"] == "imp_neto":
            report += f"2021, pensión K {r['recepcion_pension_K']}: mediana patrimonial {r['mediana']:,.2f}, RIC [{r['p25']:,.2f}, {r['p75']:,.2f}], N válido={r['N_valido']:,} de {r['N_estrato']:,}. "
            report += "El patrimonio incluye a la pareja; no equivale al monto de pensión ni acredita suficiencia.\n\n"
    report += "Los grupos de pensión K y apoyo de vejez se mantienen separados y pueden coexistir. El desconocido se muestra, no se clasifica como no receptor. "
    report += "El grupo Negativa explícita K exige cuatro negativas de K58/K64 orientadas al titular, y no excluye apoyos públicos de K79/K82. "
    report += "Cinco o más síntomas es un indicador de la escala construida, no diagnóstico clínico. No se publican pruebas de significación ni afirmaciones poblacionales: faltan ponderación, dependencia de pareja, diseño y selección.\n\n"
    report += payload["limites"]+"\n\nLas cifras completas de perfiles bivariados están en eda_conjunto_inicial.json y el notebook ejecutado. Las demás variables económicas se conservan en la base, pero su EDA conjunto aún requiere validar contratos.\n"
    write_project_text(project_path('', "docs/integracion/EDA_CONJUNTO_INICIAL.md"), report)
    return payload


if __name__ == "__main__":
    result = run()
    print(f"J01: {result['N_tablas_asociacion']} asociaciones, perfiles 2021 y dos figuras; referencia {result['N_referencia']:,}")
