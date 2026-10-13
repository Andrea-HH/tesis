"""Notebook legible y exhaustivo del bloque independiente K 2021 ya ejecutado."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text

import argparse
import json
from pathlib import Path
import sys

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]


def build() -> nbformat.NotebookNode:
    """Revisión de agregados; la recalculación por fuente es una acción explícita."""
    data = json.loads(read_project_text(project_path('', "reports/eda_independiente/k2021/resultados.json")))
    md,code=nbformat.v4.new_markdown_cell,nbformat.v4.new_code_cell
    nb=nbformat.v4.new_notebook()
    nb.cells=[md("# 04 · K 2021: EDA exhaustivo independiente, bloque B02a parcial\n\n"
                 "Original F10, imputado/derivado F03 y construido individual F17 se conservan separados. "
                 "No hay unión con ENASEMsimple ni selección de muestra principal. "
                 "338 variables efectivamente descritas; las restantes columnas/rondas figuran como pendientes en el registro completo. "
                 "No se restringe el EDA a variables pensionarias."),
              md("## Método y reproducción\n\n"
                 "Se validan dominios por variable, NR/NS y periodicidad contra cuestionario e imputación 2021. "
                 "Un N elegible de producto construido no es N de receptores de la pregunta monetaria. "
                 "N válido no sustituye N elegible. Filtros parcialmente conocidos usan estados elegible/excluido/desconocido; viudez conserva ND. "
                 "Ceros estructurales e imputados se preservan. Sin ponderar, sin deflactar, sin comparar poder adquisitivo. "
                 "En terminal: `python scripts/run_k2021_eda.py --imputation-doc RUTA_IM --questionnaire RUTA_Q`. "
                 "Este notebook abre agregados, no repite lecturas/descriptivos ni muestra identificadores."),
              code("from pathlib import Path\nimport json\nimport pandas as pd\nfrom IPython.display import display, Markdown, Image\n"
                   "ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p/'pyproject.toml').exists())\n"
                   "payload = json.loads((ROOT/'reports/eda_independiente/k2021/resultados.json').read_text())\n"
                   "pd.set_option('display.max_rows',None)\npd.set_option('display.max_columns',None)\n"
                   "display(pd.DataFrame(payload['fuentes_documentales']))\n"
                   "display(pd.DataFrame([{k:s[k] for k in ['fuente','archivo','N_registros','unidad','N_variables_analizadas']} for s in payload['fuentes']]))"),
              md("## Cotejo derivado–imputado: 59 componentes\n\n"
                 "Se compara dentro de F03; recuperación, cambio del monto observado y bandera son operaciones distintas. "
                 "No hay emparejamiento de fuentes ni deflación; no se interpreta la imputación como mejora de predicción."),
              code("display(pd.DataFrame(payload['comparaciones_derivado_imputado']))\n"
                   "display(pd.DataFrame([payload['orientacion_F17']]))\n"
                   "display(Markdown('Orientación: conteos agregados de punteros; un prefijo propio/cónyuge no atribuye automáticamente el monto a la persona de la fila.'))")]
    for source in data["fuentes"]:
        fid=source["fuente"]
        nb.cells.append(md(f"## {fid} · {source['archivo']}\n\n"
                           f"N={source['N_registros']:,}, {source['N_variables_analizadas']} variables descritas. Unidad: {source['unidad']}. "
                           "No sumar registros de las otras fuentes ni interpretar esta modalidad económica de hogar como modalidad individual de CP1."))
        for name,result in source["resultados"].items():
            c=result["contrato"]
            nb.cells += [md(f"### {name} · {c['label']}\n\nUnidad: {c['unit']}. {c['eligibility']}. Referencia: {c['reference']}, p. {c['page']}.\n\n"
                            f"Códigos válidos: {c['codes'] or 'Medida numérica documentada'}. NR/NS: {c['numeric_nonresponse'] or 'Sin regla numérica global; especiales conservados'}."),
                         code(f"r = next(s for s in payload['fuentes'] if s['fuente']=='{fid}')['resultados']['{name}']\n"
                              "display(pd.DataFrame([r['resumen']]))\n"
                              "display(pd.DataFrame(r['estados']))\n"
                              "display(pd.DataFrame(r['distribucion']))\n"
                              f"display(Image(filename=str(ROOT/'reports/eda_independiente/k2021/figuras/{fid}/{name}.png')))\n"
                              f"ficha = (ROOT/'docs/eda/k2021/{fid}_{name}.md').read_text()\n"
                              "display(Markdown(ficha.split('## Interpretación específica y límites')[1]))")]
    nb.cells += [md("## Cobertura y límites del bloque\n\n"
                    "F03: 178 variables (59 derivados, 59 imputados, 59 banderas y propiedad de negocio). "
                    "F17: 124 variables; cinco claves/punteros auditados sin divulgar niveles. "
                    "F10: 36 variables originales; el resto permanece pendiente, incluidos intervalos y secciones G/J/SA. "
                    "Los demás archivos/años y los problemas de enlace 2001/2003/2015/2018/2021 siguen abiertos. "
                    "La documentación declara uso puntual de 2018 para algunos productos 2021; no demuestra por sí solo fuga de información futura. "
                    "No se modifican pregunta, CP1, catálogo de programas ni las ocho variables armonizadas acordadas."),
                 code("assert sum(s['N_variables_analizadas'] for s in payload['fuentes']) == 338\n"
                      "for s in payload['fuentes']:\n"
                      "    for r in s['resultados'].values():\n"
                      "        assert sum(x['n'] for x in r['estados']) == r['resumen']['N_total']\n"
                      "        assert sum(x['n'] for x in r['distribucion']) == r['resumen']['N_valido']\n"
                      "assert len(payload['comparaciones_derivado_imputado']) == 59\n"
                      "print('338 variables conciliadas; bloque parcial, aceptación académica abierta.')")]
    nb.metadata.kernelspec={"display_name":"Python 3","language":"python","name":"python3"}
    nb.metadata.language_info={"name":"python","version":"3.11"}
    nbformat.write(nb,project_path('', "notebooks/04_eda_k_2021_independiente.ipynb"))
    return nb


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute",action="store_true")
    args=parser.parse_args()
    nb=build()
    if args.execute:
        from jupyter_client import KernelManager
        manager=KernelManager(kernel_name="python3")
        manager.kernel_spec.argv=[sys.executable,"-m","ipykernel_launcher","-f","{connection_file}"]
        client=NotebookClient(nb,timeout=900,resources={"metadata":{"path":str(ROOT)}},kernel_name="python3")
        client.km=manager
        client.execute()
        path=project_path('', "reports/notebooks/04_eda_k_2021_independiente_ejecutado.ipynb")
        path.parent.mkdir(exist_ok=True,parents=True)
        nbformat.write(nb,path)
        print(f"Notebook K ejecutado: {sum(c.cell_type=='code' for c in nb.cells)} celdas; {path}")
