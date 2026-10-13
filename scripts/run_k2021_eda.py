"""B02a: componentes económicos 2021 independientes; cierre parcial de fuente."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text, read_project_bytes

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pymupdf

from tesis_enasem.economic_eda import component_unit, describe_source_variable, paired_imputation_check, plot_source
from tesis_enasem.independent_eda import VariableSpec, strict_json
from run_independent_eda import md_table

ROOT = Path(__file__).resolve().parents[1]
REPORTS = project_path('', "reports/eda_independiente/k2021")
DOCS = project_path('', "docs/eda/k2021")
IM_URL = "https://www.mhasweb.org/Resources/DOCUMENTS/2021/Imputation_of_Non_Reponse_on_Economic_Variables_in_the_MHAS_ENASEM_2021.pdf"
Q_URL = "https://www.inegi.org.mx/contenidos/programas/enasem/2021/doc/enasem_2021_cuestionario_basico.pdf"


def make_spec(name: str, label: str, codes: dict | None = None, nr: dict | None = None,
              unit: str | None = None, page: int = 13, eligibility: str = "Universo de producto; filtros brutos no reconstruidos") -> VariableSpec:
    """Contrato por familia verificada; montos derivados no son respuestas brutas."""
    base = re.sub(r"^(?:imamk|amk|dumk)", "", name).removesuffix("_21")
    flag = name.startswith("dumk")
    if name.startswith(("amk","imamk","dumk")) and base in {"4_1","4_2","8_1","8_2","20_1","24_1","33_1","33_2","33_3","40","42","44","86","88","101","103","111"}:
        page = 14
    codes = {"0":"No imputado según bandera","1":"Imputado según bandera"} if flag else (codes or {})
    return VariableSpec(name,label,"categorical" if codes else "numeric", "bandera" if flag else (unit or component_unit(base)),
                        codes,nr or {},None,None,False,eligibility,IM_URL if name.startswith(("amk","imamk","dumk")) else Q_URL,
                        page,"2021 independiente; no comparación real ni equivalencia con otra ronda aprobada",
                        "Montos de fuente/titular indicado; ceros pueden ser estructurales o construidos. No identifica por sí sola recepción, derecho ni programa; sin ponderar.")


def nullable_membership(series: pd.Series, yes: list[int], no: list[int]) -> pd.Series:
    """No transforma filtros ausentes/NR no documentados en elegibles o excluidos."""
    out = pd.Series(pd.NA,index=series.index,dtype="boolean")
    out.loc[series.isin(yes)] = True
    out.loc[series.isin(no)] = False
    return out


def run(imputation_doc: Path, questionnaire: Path, figures: bool = True, reuse_figures: bool = False) -> dict:
    """Cada archivo se carga y analiza solo; no une claves de distintas fuentes."""
    inventory = json.loads(read_project_text(project_path('', "docs/pensiones/inventario_fuentes.json")))
    ledger_path = project_path('', "docs/eda/cobertura_variables.json")
    ledger = json.loads(read_project_text(ledger_path))
    metas = {(m["archivo"],m["variable"]):m for m in inventory["variables"]}
    im = pymupdf.open(imputation_doc)
    q = pymupdf.open(questionnaire)
    if "2021" not in q[0].get_text() or "K.1" not in q[55].get_text() or "K.58" not in q[63].get_text():
        raise ValueError("El contrato requiere el cuestionario básico oficial 2021, paginación verificada.")
    tables = im[12].get_text()+im[13].get_text()
    # Todas las 59 correspondencias se verifican contra tablas 4.1–4.3 y 4.6.
    documented = set(re.findall(r"imamk([\w]+)_21",tables))
    assert len(documented) == 59
    provenance = [{"url":IM_URL,"sha256":sha256(read_project_bytes(imputation_doc)).hexdigest(),"paginas":"4–8, 13–14, 24–28, apéndice de construcción", "fecha_consulta":"2026-10-12"},
                  {"url":Q_URL,"sha256":sha256(read_project_bytes(questionnaire)).hexdigest(),"paginas":"PDF 56–75; numeración impresa 62–81","fecha_consulta":"2026-10-12"}]
    contracts, sources, pair_checks, figures_n = [],[],[],0
    for fid in ["F10","F03","F17"]:
        source = next(s for s in inventory["fuentes"] if s["fuente_id"] == fid)
        path = project_path('', "data/raw", source["archivo"])
        assert sha256(read_project_bytes(path)).hexdigest() == source["sha256"]
        frame = pd.read_stata(path,convert_missing=True,convert_categoricals=False)
        selected: dict[str,tuple[VariableSpec,pd.Series | None]] = {}
        whole = pd.Series(True,index=frame.index,dtype="boolean")
        if fid in {"F03","F17"}:
            for name in frame:
                match = re.fullmatch(r"(amk|imamk|dumk)(.+)_21",name)
                if not match: continue
                prefix,base = match.groups()
                assert base in documented
                # Viudez: universo exacto no existe en estos archivos; no deducirlo de .
                spouse = base in {"53a","54a","56a","57a"} or base.startswith(("67_","83_"))
                if base in {"101","103","111"}:
                    eligible, note = None, "ND: falta filtro completo de viudez K97/K100 en esta fuente"
                elif spouse and fid == "F03":
                    eligible, note = None, "ND: componentes del cónyuge requieren pareja; k52a_21 no existe en F03. No se infiere universo de N válido ni de los perdidos."
                elif spouse:
                    eligible = nullable_membership(frame.k52a_21,[2],[1])
                    note = "Cónyuge: k52a_21=2 elegible, 1 excluido, perdido desconocido. Universo del producto de pareja, no pregunta monetaria entre receptores."
                else:
                    eligible, note = whole, "Todos los registros del producto construido; incluye ceros estructurales. No es universo de pregunta bruta."
                selected[name] = (make_spec(name,metas[(source["archivo"],name)]["etiqueta"],eligibility=note),eligible)
            if fid == "F03":
                selected["k1_21"] = (make_spec("k1_21","Propiedad de negocio del informante/cónyuge",codes={"1":"Sí, un negocio","3":"Sí, más de uno","2":"No"},nr={"8":"Negativa","9":"No sabe"},unit="categoría",page=56,eligibility="Pregunta K1 al conjunto de entrevistas económicas"),whole)
            else:
                extras = {"sex_21":({"1":"Hombre","2":"Mujer"},"categoría"),
                          "tipent_hh_21":({"1":"Directa económica del hogar","2":"Sustituto económico del hogar","3":"Sobre fallecido (si estuviera presente)"},"modalidad"),
                          "key_21":({"1":"Ingresos referidos al informante","2":"Ingresos referidos al cónyuge"},"orientación"),
                          "k52a_21":({"1":"Entrevistado único","2":"Pareja en el hogar"},"categoría"),"age_21":({},"años")}
                for name,(codes,unit) in extras.items():
                    spec = make_spec(name,metas[(source["archivo"],name)]["etiqueta"],codes=codes,unit=unit,page=6,eligibility="Universo de registros individuales del producto; no indica modalidad individual en todas las fuentes")
                    spec = VariableSpec(**{**asdict(spec),"reference":IM_URL+"; etiquetas del archivo individual (sexo: cuestionario SA3, PDF p. 76: 1 hombre/2 mujer)"})
                    if name == "age_21":
                        spec = VariableSpec(**{**asdict(spec),"lower":0,"integer":True})
                    selected[name] = (spec,whole)
                # Punteros: solo proporciones agregadas de orientación, nunca niveles de NP.
                orientation = {"N_total":len(frame),"N_propios_np_coincide":int(frame.k45d_21.eq(frame.np).sum()),
                               "N_conyuge_np_coincide":int(frame.k52a_1_21.eq(frame.np).sum()),
                               "N_ambos_coinciden":int((frame.k45d_21.eq(frame.np)&frame.k52a_1_21.eq(frame.np)).sum()),
                               "N_sin_coincidencia":int((~frame.k45d_21.eq(frame.np)&~frame.k52a_1_21.eq(frame.np)).sum())}
        else:
            # Bloque original validado, incluyendo actividad, activos, alimentación y herencia.
            unconditional = {"k1_21":56,"k17_21":59,"k31a_21":61,"k31b_21":61,"k31c_21":61,
                             "k38_21":62,"k46_21":63,"k58a_21":64,"k58b_21":64,"k58c_21":64,"k58d_21":64,
                             "k70_21":65,"k79a_21":66,"k79c_21":66,"k77a_21":69,"k78_21":71,"k78a_21":71,
                             "k85_21":71,"k90_21":71,"k91_21":71,"k93a_21":72,"k97_21":73}
            conditional = {"k3_1_21":(56,nullable_membership(frame.k1_21,[1,3],[2,8,9])),
                           "k92_21":(71,nullable_membership(frame.k91_21,[2,8,9],[1])),
                           "k93b_21":(72,nullable_membership(frame.k93a_21,[1],[2,3,8,9]))}
            for name in ["k64c_21","k64d_21","k64e_21","k64f_21"]:
                conditional[name]=(68,nullable_membership(frame.k52a_21,[2],[1]))
            for name,(page,eligible) in {**{k:(p,whole) for k,p in unconditional.items()},**conditional}.items():
                meta = metas[(source["archivo"],name)]
                nr = {k:("Negativa" if "RF" in label else "No sabe") for k,label in meta["etiquetas_valores"].items() if label.endswith(("RF","DK"))}
                codes = {k:v for k,v in meta["etiquetas_valores"].items() if k not in nr}
                codes = {k:({"1":"Sí","2":"No"}.get(k,v) if set(codes)=={"1","2"} else v) for k,v in codes.items()}
                selected[name]=(make_spec(name,meta["etiqueta"],codes=codes,nr=nr,unit="categoría",page=page,eligibility="Filtro de cuestionario básico 2021: todos los registros económicos" if name in unconditional else "Rama reconstruida con pregunta previa; desconocidos se conservan como ND"),eligible)
            for name,page,eligible in [
                ("k4_1_21",56,nullable_membership(frame.k1_21,[1,3],[2,8,9]) & nullable_membership(frame.k3_1_21,[1],[2,8,9])),
                ("k8_1_21",56,nullable_membership(frame.k1_21,[1,3],[2,8,9])),
                ("k86_21",71,nullable_membership(frame.k85_21,[1],[2,8,9])),("k88_21",71,whole),
                ("k101_21",73,None),("k103_21",73,None),("k111_21",74,None)]:
                unit = component_unit(name[1:].removesuffix("_21"))
                selected[name]=(make_spec(name,metas[(source["archivo"],name)]["etiqueta"],nr={"8888888":"Negativa","9999999":"No sabe"},unit=unit,page=page,eligibility="Rama documentada cuando reconstruible; viudez condicionada permanece ND sin reconstrucción completa de K97/K100"),eligible)
        results = {}
        for name,(spec,eligible) in selected.items():
            result = describe_source_variable(frame[name],spec,eligible)
            assert not any(r["estado"] == "fuera de dominio documentado" for r in result["estados"]), (fid,name)
            contracts.append({"fuente":fid,**asdict(spec)})
            results[name]= {"contrato":asdict(spec),**result}
            if figures:
                figure_path = project_path('reports/eda_independiente/k2021', f"figuras/{fid}/{name}.png")
                if not reuse_figures or not figure_path.exists():
                    plot_source(result,spec,fid,project_path('reports/eda_independiente/k2021', f"figuras/{fid}/{name}.png"))
                figures_n += 1
            s=result["resumen"]
            text=f"# {fid} · {name}\n\n{spec.label}. Fuente: {source['archivo']}. Año 2021; unidad de fila: {source['unidad_fila']}. Unidad: {spec.unit}.\n\n"
            text+=f"## Método, códigos y universo\n\nReferencia: {spec.reference}, p. {spec.page}. {spec.eligibility}. Códigos válidos: {spec.codes or 'Monto numérico derivado/imputado o pregunta monetaria documentada'}. NR/NS numéricos: {spec.numeric_nonresponse or 'No se eliminan números por su magnitud; no respuesta preservada en tags/NaN del producto'}.\n\n"
            text+="## Resultados\n\n"+md_table([s])+"\n"+md_table(result["estados"])+"\n"+md_table(result["distribucion"])
            text+=f"\n![Distribución independiente](../../../reports/eda_independiente/k2021/figuras/{fid}/{name}.png)\n\n## Interpretación específica y límites\n\n"
            if spec.kind=="categorical" and s["N_valido"]:
                top=max(result["distribucion"],key=lambda r:r["n"])
                text+=f"La categoría modal es «{top['respuesta']}», {top['n']:,}/{s['N_valido']:,} ({top['pct_valido']:.2f}% válido). {s['N_no_valido']:,} registros no aportan una respuesta válida. "
            elif s["N_valido"]:
                text+=f"La mediana es {s['mediana']:,.2f}, P25–P75 [{s['p25']:,.2f}; {s['p75']:,.2f}], frente a media {s['media']:,.2f}. Hay {s['N_ceros']:,} ceros y {s['N_negativos']:,} negativos; P95={s['p95']:,.2f}. "
            else: text+="No hay valores válidos; no se interpreta esta ausencia como ausencia del fenómeno. "
            text+="\n\n"+spec.interpretation+" "
            if name.startswith(("amk","imamk")):
                text+="El denominador del producto puede incluir ceros creados por falta de ingreso/activo. No equivale al número de receptores ni al universo de la pregunta sobre monto. "
            if name.startswith("dumk"):
                text+="La bandera mide imputación, no recepción de un ingreso ni calidad clínica. "
            if "61_" in name or "67_" in name or name.startswith(("k58","k64")):
                text+="Se describe un componente/tipo de pensión; no se aprueba una clasificación contributiva/no contributiva ni se suman columnas como personas únicas. "
            text+="La atribución informante/cónyuge requiere punteros internos; el archivo individual puede repetir componentes compartidos. Sin ponderar, sin deflactar, sin sumar fuentes ni extrapolar nacionalmente. Comparaciones entre años y enlace definitivo pendientes.\n"
            target=project_path('docs/eda/k2021', f"{fid}_{name}.md");target.parent.mkdir(parents=True,exist_ok=True);write_project_text(target, text)
            row=next(r for r in ledger if r["fuente"]==fid and r["variable"]==name)
            row.update(estado="EDA independiente observado ejecutado; revisión de filtros/equivalencias pendiente",bloque="B02a",N_elegible=s["N_elegible"],N_valido=s["N_valido"],tabla_generada=True,grafica_generada=figures,pendiente="Universo bruto cuando ND, orientación/titular, comparabilidad y revisión académica; no integración")
        if fid=="F03":
            for base in sorted(documented):
                names=[f"{p}{base}_21" for p in ["amk","imamk","dumk"]]
                assert all(n in frame for n in names)
                pair={"componente":base,"unidad":component_unit(base),**paired_imputation_check(*[frame[n] for n in names])}
                pair_checks.append(pair)
        if fid=="F17":
            for name in ["k45d_21","k52a_1_21"]:
                row=next(r for r in ledger if r["fuente"]==fid and r["variable"]==name)
                row.update(rol="técnica: puntero a persona, sin divulgar niveles",estado="técnica: orientación auditada solo en agregados",bloque="B02a")
        sources.append({"fuente":fid,"archivo":source["archivo"],"sha256":source["sha256"],"N_registros":len(frame),"unidad":source["unidad_fila"],"N_variables_analizadas":len(results),"resultados":results})
        strict_json(sources[-1],project_path('reports/eda_independiente/k2021', f"{fid}_resultados.json"))
        print(f"B02a {fid}: {len(results)} variables efectivamente descritas",flush=True)
    result={"bloque":"B02a","ronda":2021,"fuentes_documentales":provenance,"fuentes":sources,"comparaciones_derivado_imputado":pair_checks,"orientacion_F17":orientation,"N_figuras":figures_n,"estado":"Bloque parcial; resto de K y otras secciones/rondas continúan pendientes"}
    strict_json(result,project_path('reports/eda_independiente/k2021', "resultados.json"))
    strict_json({"fuentes_documentales":provenance,"contratos":contracts},project_path('', "docs/eda/contratos_k2021.json"))
    strict_json(ledger,ledger_path)
    summary=[{"Fuente":s["fuente"],"Registros":s["N_registros"],"Variables EDA":s["N_variables_analizadas"],"Unidad":s["unidad"]} for s in sources]
    report=("# B02a · EDA independiente de componentes K 2021\n\n**Estado: bloque parcial ejecutado, sin integración definitiva.** Se conserva toda la población de cada fuente; no se suman hogares y personas.\n\n"
            "## Documentación y método\n\nSe verificaron las 59 correspondencias monetarias contra las tablas 4.1–4.3 y 4.6 del documento de imputación. "
            "Se conservan derivados `amk`, imputados `imamk` y banderas `dumk` como variables distintas. Las banderas se cotejan dentro del archivo frente a recuperación/cambio del derivado. "
            "Las unidades distinguen montos mensuales documentados, salario de periodicidad pendiente, montos totales recibidos, patrimonio/deuda y gastos totales por fallecimiento del cónyuge. "
            "K101/K103 y los montos ordinarios K61/K67 son mensuales según preguntas y asignaciones del apéndice. ‘Durante el año pasado’ es ventana de recepción, no factor automático de anualización. Los ceros estructurales se conservan sin tratarlos como respuestas al monto. "
            "N elegible del producto es el conjunto de registros al que se aplica la columna; no el universo de receptores. Para viudez sin filtro completo, N elegible=ND. "
            "Las variables originales seleccionadas excluyen RF/NS solo mediante etiquetas/questionario específicos; en montos documentados se excluyen 8888888/9999999. "
            "Filtros ausentes conservan elegibilidad desconocida; no se deduce de N válido ni se sustituye por cero.\n\n"+md_table(provenance)+"\n## Cobertura real del bloque\n\n"+md_table(summary)+
            f"\nSe generaron {sum(s['N_variables_analizadas'] for s in sources)} fichas/tablas independientes y {figures_n} gráficas BrBG, además de 59 cotejos derivados–imputados. "
            "No se declara terminado el archivo combinado G/J/K/SA: este bloque cubre variables K seleccionadas, el resto continúa en el registro exhaustivo. "
            "2024 permanece separado, y las copias de 2018 no se descartan.\n\n## Recuperación de no respuesta y consistencia de banderas\n\n"+md_table(pair_checks)+
            "\nUna recuperación es derivado faltante con imputado disponible; un cambio compara ambos disponibles con tolerancia relativa 1e-7 y absoluta 0.01 pesos. "
            "La bandera no se identifica automáticamente con estas operaciones: divergencias se documentan, sin corregir montos ni banderas. "
            "El aumento de cobertura no demuestra que los montos imputados sean ciertos ni que mejoren una predicción.\n\n## Orientación del archivo construido individual\n\n"+md_table([orientation])+
            "\nEstos conteos comparan internamente los punteros con NP y no publican sus niveles. No constituyen una unión con ENASEMsimple. "
            "‘Propio’ y ‘cónyuge’ son posiciones en la entrevista económica: un prefijo de variable no garantiza que su titular sea la persona de la fila.\n\n"
            "## Limitaciones y siguientes variables\n\nNo se aplican ponderadores ni se estiman parámetros nacionales. No se deflactan ni comparan tendencias reales. "
            "Los productos incluyen componentes económicos ajenos a pensiones: negocios, rentas, capital, trabajo, transferencias, deudas, consumo y gastos por viudez. "
            "La documentación declara diferencias instrumentales 2018–2021 (propiedades, tercera pensión, transferencias y COVID); no se aprueba equivalencia temporal. "
            "Describe uso puntual de información 2018 en construcción 2021, cuya trazabilidad debe revisarse antes de modelos prospectivos; esta descripción no prueba fuga futura. "
            "El mismo documento contiene código heredado con referencias 2015: se documenta y no se ejecuta como si describiera de manera homogénea toda construcción 2021. "
            "Permanecen pendientes los demás montos, intervalos y filtros originales de F10, G/J/SA, las demás rondas/fuentes y los enlaces señalados en 2001, 2003, 2015, 2018 y 2021. "
            "No se modifica la pregunta, CP1, las ocho variables armonizadas ni el catálogo histórico.\n\n"
            "## Reproducción y revisión\n\n`python scripts/run_k2021_eda.py --imputation-doc RUTA_IM --questionnaire RUTA_Q`. "
            "Abrir notebook `04_eda_k_2021_independiente.ipynb`; las fichas están en `docs/eda/k2021/` y los agregados/gráficas locales en `reports/eda_independiente/k2021/`.\n\n")
    report+="| Fuente | Variable | Ficha |\n| --- | --- | --- |\n"
    for s in sources:
        for name in s["resultados"]:report+=f"| {s['fuente']} | {name} | [Resultados](k2021/{s['fuente']}_{name}.md) |\n"
    write_project_text(project_path('', "docs/eda/B02A_K_2021.md"), report)
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--imputation-doc",required=True,type=Path)
    parser.add_argument("--questionnaire",required=True,type=Path)
    parser.add_argument("--reuse-figures",action="store_true",help="Reanudar conservando figuras del mismo contrato/archivo")
    args=parser.parse_args()
    run(args.imputation_doc,args.questionnaire,reuse_figures=args.reuse_figures)
