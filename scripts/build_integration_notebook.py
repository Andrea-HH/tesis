"""Notebook paso a paso de las 17 uniones, validaciones y primer EDA conjunto."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text

import argparse
import json
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from run_longitudinal_integration import source_kind

ROOT = Path(__file__).resolve().parents[1]


def build() -> nbformat.NotebookNode:
    """Fuentes sin outputs; copia ejecutada privada con agregados, nunca muestras de IDs."""
    audit = json.loads(read_project_text(project_path('', "docs/integracion/validacion.json")))
    md, code = nbformat.v4.new_markdown_cell, nbformat.v4.new_code_cell
    nb = nbformat.v4.new_notebook()
    nb.cells = [md("# 05b · Integración longitudinal provisional ENASEM\n\n"
                   "Autorizada ahora por la autora, sin esperar a terminar el EDA independiente. "
                   "Unidad persona-ronda, `id=cunicah:np`, clave única `id+ronda`. "
                   "ENASEMsimple es maestro: 99,676 registros, todas las modalidades/edades, sin filtros. "
                   "No altera pregunta, CP1 ni decisiones predictivas. Fuentes económicas de hogar son contexto, no ingreso individual por mero enlace."),
                md("## Reproducción y seguridad\n\n"
                   "`RECONSTRUIR=True` genera el Parquet desde todos los originales con el módulo probado. "
                   "Por defecto se conserva el producto calculado y se verifican **otra vez las claves de cada unión paso a paso**; "
                   "no se repiten descriptivos del EDA previo. Requiere datos locales y pyarrow. "
                   "Nunca mostrar `head()` de la base ni publicar filas/IDs. Las salidas visibles son agregados."),
                code("from pathlib import Path\nimport json,sys\nimport numpy as np\nimport pandas as pd\n"
                     "from IPython.display import display,Markdown,Image\n"
                     "ROOT=next(p for p in [Path.cwd(),*Path.cwd().parents] if (p/'pyproject.toml').exists())\n"
                     "sys.path.insert(0,str(ROOT/'scripts'))\n"
                     "from run_longitudinal_integration import run,read_source,source_kind\n"
                     "from tesis_enasem.integration import person_id,economic_link,load_integrated\n"
                     "RECONSTRUIR=False\n"
                     "if RECONSTRUIR:\n    run()\n"
                     "audit=json.loads((ROOT/'docs/integracion/validacion.json').read_text())\n"
                     "sources={s['fuente_id']:s for s in audit['fuentes']}\n"
                     "master,formats=read_source(sources['F20'])\n"
                     "ids=person_id(master)\n"
                     "assert len(master)==99676\n"
                     "assert not pd.DataFrame({'id':ids,'ronda':master.ronda}).duplicated().any()\n"
                     "assert ids.nunique()==27171\n"
                     "display(pd.DataFrame(audit['registros_por_ronda']))\n"
                     "print('Maestro completo: 119 variables originales; identificadores calculados sin mostrar sus valores.')"),
                md("## Puentes históricos y control de versiones\n\n"
                   "2001 se enlaza a F13 por cunicah+codent01 y F13 aporta unhhid para hogar. "
                   "2003 se enlaza a F14 por cunicah+codent03 y F14 aporta cunicah+acthog económico. "
                   "El acthog del maestro no se utiliza para unión directa 2003. "
                   "Los NP originales del maestro permanecen intactos. F05 es copia binaria de F04; F06/2024 separado."),
                code("bridges={year:read_source(sources[fid])[0] for year,fid in [(2001,'F13'),(2003,'F14')]}\n"
                     "assert sources['F04']['sha256']==sources['F05']['sha256']\n"
                     "display(pd.DataFrame(audit['excluidas']))\n"
                     "verified=[]")]
    for s in audit["fuentes"]:
        if "integracion" not in s: continue
        fid = s["fuente_id"]; year = s["anio_nominal_verificado"]; i = s["integracion"]
        nb.cells += [md(f"## Unión {fid} · {year} · {s['archivo']}\n\n"
                       f"Producto: {source_kind(s)}. Clave: `{'+'.join(i['claves'])}`; "
                       f"cardinalidad `{i['cardinalidad']}`; puente `{i['puente'] or 'no requiere puente temprano'}`. "
                       f"Se conservaron {s['n_variables']} columnas con prefijo {fid}__ y sus tags donde existen. "
                       "El índice de unión permite null en no enlazados; jamás se usa -1 como última fila de la fuente."),
                     code(f"source,_=read_source(sources['{fid}'])\n"
                          f"step=economic_link(master,source,{year},{i['claves']!r},{source_kind(s)=='construida_individual'},bridges.get({year}))\n"
                          f"assert step['audit']['n_enlazadas']==sources['{fid}']['integracion']['n_enlazadas']\n"
                          "assert len(step['full_indexer'])==99676\n"
                          f"verified.append({{'fuente':'{fid}',**step['audit']}})\n"
                          "display(pd.DataFrame([verified[-1]]))\n"
                          f"display(pd.DataFrame([r for r in audit['cobertura'] if r['fuente']=='{fid}']))\n"
                          "del source,step")]
    nb.cells += [md("## Comprobación final y diccionario\n\n"
                    "No se multiplican filas. Todas las columnas y tags se verificaron al releer Parquet por grupos de filas. "
                    "La no correspondencia y la no disponibilidad temporal tienen estados distintos. "
                    "Etiquetas/códigos/formatos/procedencia de cada columna están en docs/integracion/diccionario_columnas.json y DICCIONARIO_COLUMNAS.md."),
                 code("assert len(verified)==17\n"
                      "assert all(r['coincide'] for r in audit['reconciliacion_inventario'])\n"
                      "keycheck=load_integrated(ROOT/'data/processed/enasem_integrada_provisional.parquet',['id','ronda'])\n"
                      "assert len(keycheck)==99676 and not keycheck.duplicated().any()\n"
                      "assert keycheck.id.nunique()==27171\n"
                      "del keycheck\n"
                      "display(pd.DataFrame(audit['reconciliacion_inventario']))\n"
                      "print({k:audit[k] for k in ['N_registros','N_personas','N_columnas_finales','N_columnas_fuente_conservadas','roundtrip_todas_columnas']})"),
                 md("## Pensiones y apoyos personales: derivación provisional validada en 2021\n\n"
                    "Se exigen key_21, NP propio/cónyuge igual al NP del maestro, concordancia del puntero con el hogar, "
                    "rama de pareja y ausencia de modalidad sobre fallecido. Se preservan todas las instituciones y montos originales, "
                    "incluidas negativas/desconocidos y varias pensiones. Solo IMSS/ISSSTE identificados dan evidencia contributiva, "
                    "y opción 5 del apoyo público da evidencia de pensión de vejez no contributiva. "
                    "Otro público/privado/persona/INAPAM no se tipifica automáticamente. Montos observados sumados son parciales dentro de K, "
                    "no ingreso total ni suma de versiones. Las demás rondas conservan fuentes y quedan pendientes de homologación; NA no es cero."),
                 code("display(pd.DataFrame(audit['cotejo_punteros_2021']))\n"
                      "display(pd.DataFrame([{'estado':k,'N':v} for k,v in audit['titularidad_2021'].items()]))\n"
                      "display(pd.DataFrame([{'indicador':k,'estado':state,'N':n} for k,counts in audit['pension_2021'].items() for state,n in counts.items()]))"),
                 md("## J01 · Inicio del EDA conjunto\n\n"
                    "42 asociaciones Spearman dentro de seis rondas: patrimonio con salud física/mental, cognición, funcionalidad, educación y edad. "
                    "Se conserva N total y se explicita N de pares válidos; la población analítica de cada par no define la muestra predictiva. "
                    "Perfiles de dos y tres variables de 2021 utilizan únicamente recepción K con titular validado. "
                    "Desconocidos se muestran. Sin ponderar, sin deflactar, sin causalidad ni modelos. Cognición incluye imputación del proveedor."),
                 code("joint=json.loads((ROOT/'docs/integracion/eda_conjunto_inicial.json').read_text())\n"
                      "pd.set_option('display.max_rows',None)\n"
                      "display(pd.DataFrame(joint['asociaciones']))\n"
                      "display(Image(filename=str(ROOT/'manuscrito/figuras/borradores/integracion_spearman.png')))\n"
                      "display(pd.DataFrame(joint['perfiles_bivariados_2021']))\n"
                      "display(pd.DataFrame(joint['perfiles_trivariados_2021']))\n"
                      "display(pd.DataFrame(joint['proteccion_cruzada_2021']))\n"
                      "display(Image(filename=str(ROOT/'manuscrito/figuras/borradores/integracion_perfiles_2021.png')))"),
                 md("## Limitaciones y redacción sincronizada\n\n"
                    "La integración estructural está ejecutada; los contratos de todas las variables no están cerrados. "
                    "Problemas de enlace históricos permanecen documentados. No inferir que un apoyo en dinero/especie sea efectivo, "
                    "ni que un prefijo propio corresponda al sujeto de cada fila. "
                    "Precio/unidad patrimonial, pesos longitudinales, imputaciones temporales, anomalías CP1 y muestra principal pendientes. "
                    "Consultar HOMOLOGACION_PENDIENTE.md. Exportar LaTeX desde agregados con scripts/export_integration_manuscript.py. "
                    "Para recalcular solo el EDA conjunto: python scripts/run_joint_eda_initial.py."),
                 code("display(Markdown((ROOT/'docs/integracion/EDA_CONJUNTO_INICIAL.md').read_text().split('## Interpretación de resultados')[1]))\n"
                      "display(Markdown((ROOT/'docs/integracion/HOMOLOGACION_PENDIENTE.md').read_text()))")]
    nb.metadata.kernelspec = {"display_name":"Python 3","language":"python","name":"python3"}
    nb.metadata.language_info = {"name":"python","version":"3.11"}
    nbformat.write(nb,project_path('', "notebooks/05b_integracion_longitudinal.ipynb"))
    return nb



if __name__ == "__main__":
    import sys
    from build_main_notebooks import build
    build('INTEGRACION', execute="--execute" in sys.argv)
