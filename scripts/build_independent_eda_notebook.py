"""Conserva el notebook 03 y amplía su demostración a todas las variables de F20."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text

import argparse
from pathlib import Path
import sys

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]


def build() -> nbformat.NotebookNode:
    """Celdas por variable: objetivo, método, tablas completas, figura e interpretación."""
    import json
    registry = json.loads(read_project_text(project_path('', "docs/eda/contratos_simple.json")))
    review_path = project_path('', "reports/eda_independiente/simple_revision.json")
    reviewed = json.loads(read_project_text(review_path)) if review_path.exists() else None
    nb = nbformat.v4.new_notebook()
    markdown, code = nbformat.v4.new_markdown_cell, nbformat.v4.new_code_cell
    nb.cells = [markdown("# 03 · EDA exhaustivo independiente por bloques\n\n"
                         "B00: prevalidación de las 20 fuentes, sin integrarlas. B01: ENASEMsimple completo, "
                         "91 variables sustantivas/banderas, seis rondas, sin filtros de edad, modalidad ni continuidad. "
                         "No se construye una muestra principal ni se entrenan modelos. "
                         "El EDA de las demás fuentes permanece abierto en el registro de cobertura."),
                markdown("## Metodología y alcance de validación\n\n"
                         "El contrato por variable cita el libro del proveedor y declara códigos, unidad, filtros conocidos y límites. "
                         "Cuando la elegibilidad exacta no se reconstruye, N elegible es ND: se describen valores disponibles. "
                         "N total, N válido y porcentaje sobre ambos denominadores son distintos. "
                         "Los especiales Stata se preservan; 8/9/88/99 solo se excluyen con reglas específicas. "
                         "Ningún identificador, texto libre ni fila individual se muestra.\n\n"
                         "Los datos deben existir en data/raw/; los SHA deben coincidir con el inventario. "
                         "Para regenerar contratos: scripts/prepare_eda_contracts.py --codebook RUTA_PDF. "
                         "La comparación impresa v2/datos v3 se documenta sin modificar fuentes."),
                code("from pathlib import Path\nimport sys\nimport json\nimport pandas as pd\n"
                     "from IPython.display import display, Markdown, Image\n"
                     "ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p/'pyproject.toml').exists())\n"
                     "sys.path.insert(0, str(ROOT/'scripts'))\n"
                     "from run_independent_eda import run\nfrom export_independent_eda import export\n"
                     "pd.set_option('display.max_rows', None)\npd.set_option('display.max_columns', None)\n"
                     "RECALCULAR = False  # revisión desde agregados; True reproduce B00/B01 completo voluntariamente\n"
                     "if RECALCULAR:\n    payload = run()\nelse:\n    payload = json.loads((ROOT/'reports/eda_independiente/simple_resultados.json').read_text())\n"
                     "from review_b01 import review\n"
                     "revision_path = ROOT/'reports/eda_independiente/simple_revision.json'\n"
                     "revision = review() if RECALCULAR or not revision_path.exists() else json.loads(revision_path.read_text())\n"
                     "export()\nresults = {r['contrato']['variable']: r for r in payload['resultados']}\n"
                     "print(f\"{payload['N_registros']:,} registros; {payload['N_personas']:,} personas; {len(results)} variables\")"),
                markdown("## B00 · Cobertura de todas las fuentes\n\n"
                         "Prevalidación no significa análisis sustantivo terminado. Originales, imputados y construidos "
                         "tienen universos distintos; no se suman sus registros. F06/2024 está fuera del periodo principal. "
                         "Cada columna figura exactamente una vez en el JSON de cobertura, incluidas ambas copias de 2018."),
                code("display(pd.DataFrame(payload['cobertura_fuentes']))\n"
                     "ledger = json.loads((ROOT/'docs/eda/cobertura_variables.json').read_text())\n"
                     "assert len(ledger) == 5368\n"
                     "display(pd.DataFrame(ledger).groupby(['fuente','estado']).size().rename('columnas').reset_index())"),
                markdown("## Cotejo de versión documental\n\n"
                         "Se comparan N y medias numéricas impresas extraíbles, con tolerancia de redondeo; "
                         "esto no valida todas las equivalencias. Las diferencias requieren cotejo con el proveedor."),
                code("cotejo = json.loads((ROOT/'docs/eda/cotejo_libro_versiones.json').read_text())\n"
                     "display(pd.DataFrame(cotejo['diferencias']))\n"
                     "investigacion = json.loads((ROOT/'docs/eda/n_res_investigacion.json').read_text())\n"
                     "display(pd.DataFrame(investigacion['cotejos']))\n"
                     "display(Markdown('Causa de n_res aún no identificada. Los libros ES/EN coinciden; véase docs/eda/N_RES_VERSIONES.md.'))")]
    for year in [2001,2003,2012,2015,2018,2021]:
        nb.cells += [markdown(f"## B01 · Ronda {year}: cobertura de las 91 variables\n\n"
                              "El denominador total incluye todas las modalidades. Un cero de disponibilidad "
                              "no es una tasa cero del fenómeno. Los resultados detallados se presentan por variable más adelante."),
                     code(f"rows = [dict(variable=name, **row) for name,r in revision['variables'].items() for row in r['universos'] if row['anio']=={year}]\n"
                          "display(pd.DataFrame(rows)[['variable','N_total','N_elegible','N_valido','N_valido_elegible','pct_valido_elegible','pct_valido_total']])")]
    for contract in registry["contratos"]:
        name = contract["variable"]
        nb.cells += [markdown(f"## {name} · {contract['label']}\n\n"
                              f"Unidad: {contract['unit']}. Libro de códigos, página {contract['page']}.\n\n"
                              f"**Población y filtros:** {contract['eligibility']}\n\n"
                              "**Método:** distribución observada sin ponderar por ronda y modalidad; "
                              "frecuencias con % total y % válido, o cuantiles/histograma; "
                              "partición completa de faltantes y valores fuera de dominio."),
                     code(f"r = results['{name}']\n"
                          "for key,label in [('resumen','Resumen por ronda'),('frecuencias','Categorías válidas'),"
                          "('histograma','Intervalos en escala original'),('estados','Partición exhaustiva'),"
                          "('por_modalidad','Desglose por modalidad'),('frecuencias_modalidad','Categorías por modalidad')]:\n"
                          "    if r[key]:\n        display(Markdown('### '+label))\n"
                          "        display(pd.DataFrame(r[key]).drop(columns=['nota_elegibilidad'], errors='ignore'))\n"
                          f"display(Image(filename=str(ROOT/'reports/eda_independiente/figuras/{name}.png')))\n"
                          f"v = revision['variables']['{name}']\n"
                          "display(Markdown('### Universo documentado del indicador (pregunta bruta pendiente cuando no reconstruible)'))\n"
                          "display(pd.DataFrame(v['universos']))\n"
                          "display(Markdown('### Comparación conjunta: tabla numérica exacta'))\n"
                          "display(pd.DataFrame(v['tabla_comparativa']))\n"
                          f"display(Image(filename=str(ROOT/'reports/eda_independiente/comparativas/{name}.png')))"),
                     markdown("**Interpretación y límites:**\n\n" + (reviewed["variables"][name]["interpretacion"] if reviewed else contract["interpretation"] + " " + contract["temporal"]) +
                              f"\n\nLa [ficha de resultados](../docs/eda/variables/{name}.md) incluye interpretación con cifras calculadas, "
                              "cobertura, categorías modales o cuantiles, comparabilidad y conclusión parcial. "
                              "No se atribuyen efectos económicos ni capacidad predictiva a esta variable.")]
    nb.cells += [markdown("## Reconciliación, conclusiones y próximos bloques\n\n"
                          "Las 91 variables de F20 se describieron; ningún dominio no pensionario fue excluido. "
                          "La [síntesis](../docs/eda/B01_ENASEMSIMPLE.md) presenta conclusiones y diferencias v2/v3. "
                          "El [control de cobertura](../docs/eda/COBERTURA_VARIABLES.md) distingue avances de pendientes. "
                          "Los demás archivos cuentan con perfiles independientes de códigos etiquetados, no con medias monetarias válidas. "
                          "Los siguientes bloques deben cotejar sus filtros y unidades antes de completar sus distribuciones. "
                          "Los enlaces 2001/2003/2015/2018/2021 siguen pendientes; no se integra una base definitiva."),
                 code("assert len(results) == 91\n"
                      "assert sum(len(r['resumen']) for r in results.values()) == 546\n"
                      "assert set(revision['variables']) == set(results)\n"
                      "assert revision['N_figuras_comparativas'] == revision['N_tablas_comparativas'] == 91\n"
                      "for r in results.values():\n    for s in r['resumen']:\n"
                      "        assert sum(x['n'] for x in r['estados'] if x['anio']==s['anio']) == s['N_total']\n"
                      "        key = 'frecuencias' if r['contrato']['kind']=='categorical' else 'histograma'\n"
                      "        assert sum(x['n'] for x in r[key] if x['anio']==s['anio']) == s['N_valido']\n"
                      "print('546 particiones reconciliadas. La validación técnica no cierra la revisión metodológica.')")]
    nb.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nb.metadata.language_info = {"name": "python", "version": "3.11"}
    nbformat.write(nb, project_path('', "notebooks/03_eda_univariado.ipynb"))
    return nb



if __name__ == "__main__":
    import sys
    from build_main_notebooks import build
    build('EDA', execute="--execute" in sys.argv)
