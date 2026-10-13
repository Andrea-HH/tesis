"""Único constructor de los dos notebooks y del informe acumulativo."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import nbformat
from nbclient import NotebookClient

from tesis_enasem.project_paths import PROJECT_ROOT, INTERIM_DIR
from tesis_enasem.workspace import SECTIONS, consolidate_report


def build(kind: str = "all", execute: bool = False) -> None:
    """Reutiliza agregados y texto; no invoca las 17 uniones ni análisis estadísticos."""
    summary = consolidate_report()
    md = nbformat.v4.new_markdown_cell
    code = nbformat.v4.new_code_cell
    setup = """from pathlib import Path
import json
import pandas as pd
from IPython.display import display
from tesis_enasem.project_paths import project_path, RAW_DIR, PROCESSED_DIR
from tesis_enasem.workspace import display_section, find_variable, load_json
from tesis_enasem.pension_exploration import PopulationSpec
# Configuración de lectura: None muestra toda la evidencia de una sección.
BUSCAR = None
RECALCULAR = False  # No reconstruir bases ni repetir EDA durante la organización.
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
"""
    integration = [md("# 01 · Integración longitudinal ENASEM\n\nDocumento didáctico y reproducible de fuentes, claves, puentes, uniones, titularidad y validaciones. Se reutiliza la base íntegra existente.\n\nÍndice: fuentes → identificadores/puentes → uniones → titularidad → validaciones → resultado."), code(setup),
        md("## 1. Fuentes utilizadas\n\nEl inventario conserva cada fuente, año verificado, unidad, número de filas, claves y duplicados; 2024 permanece separado y la copia 2018 se utiliza una sola vez."),
        code("inventory = load_json('diccionarios/inventario_fuentes.json')\ndisplay(pd.DataFrame(inventory['fuentes']).drop(columns=['sha256'], errors='ignore'))\ndisplay_section('fuentes', BUSCAR)"),
        md("## 2. Identificadores personales\n\n`cunicah` y `np` conservan formatos originales. La función `person_id` concatena con `:` y rechaza componentes ausentes o separadores conflictivos. `ronda` identifica la visita nominal; `a_o_ent` no se sustituye por el año nominal. La misma persona se sigue mediante `id`; la observación única es `id+ronda`. No se imprimen valores individuales."),
        code("from tesis_enasem.integration import person_id, economic_link, left_indexer\nimport inspect\nprint(inspect.getsource(person_id))\nprint(inspect.getsource(economic_link))"),
        md("## 3. Puentes de 2001 y 2003\n\nUna tabla puente aporta claves económicas que el maestro no contiene de forma equivalente. `sect_k_ind_2001.dta`: maestro→individual por cunicah/codent01→hogar por unhhid. `sect_k_ind_2003.dta`: cunicah/codent03→cunicah/acthog económico. No se utiliza acthog del maestro directamente en 2003. Los duplicados o puentes ambiguos detienen el enlace; no se escoge una fila arbitraria."),
        code("display(pd.DataFrame(inventory['puentes_historicos']))\ndisplay_section('integracion', BUSCAR)"),
        md("## 4. Uniones y cardinalidad\n\nLa base maestra se preserva por LEFT JOIN. Fuentes personales: uno-a-uno dentro de ronda; hogar: muchos-a-uno, con claves derechas únicas. Las claves incompletas no se emparejan. El orden original, los tags y todas las variables fuente se conservan; no se suman versiones."),
        code("audit = load_json('docs/integracion/validacion.json')\ndisplay(pd.DataFrame(audit['cobertura']))\ndisplay(pd.DataFrame(audit['reconciliacion_inventario']))"),
        md("## 5. Titularidad y múltiples eventos\n\nEl enlace de hogar no valida propiedad individual. Recepción propia, rama cónyuge y presencia en hogar permanecen distintas. La orientación exige punteros y filtros documentados; discrepancias conservan desconocido. Viudez corresponde al beneficiario efectivo. Slots, instituciones múltiples y número declarado no son equivalentes."),
        code("ownership = load_json('docs/integracion/titularidad/resultados.json')\ndisplay_section('pensiones', BUSCAR)"),
        md("## 6. Validación real de la base existente\n\nLectura selectiva de las claves, sin mostrar IDs. No se ejecuta la integración ni se alteran datos."),
        code("from hashlib import sha256\nbase = PROCESSED_DIR/'enasem_integrada_provisional.parquet'\nassert sha256(base.read_bytes()).hexdigest() == audit['hash_parquet']\nkeys = pd.read_parquet(base, columns=['id','ronda'])\nassert len(keys) == audit['N_registros'] == 99676\nassert keys['id'].nunique() == audit['N_personas'] == 27171\nassert not keys.duplicated(['id','ronda']).any()\ndisplay(pd.DataFrame([{'registros':len(keys),'personas':keys.id.nunique(),'duplicados':0,'sha_preservado':True}]))\ndisplay_section('validacion', BUSCAR)"),
        md("## 7. Resultado y reproducción\n\nLa base es `data/processed/enasem_integrada_provisional.parquet`; el manifiesto privado describe la versión y la procedencia. `python scripts/run_longitudinal_integration.py` reconstruye el producto solo cuando sea necesario y autorizado; la ejecución ordinaria reutiliza la base. J1/2001, punteros, 33 firmas 2015, no enlaces, pesos/precios y homologaciones pendientes permanecen documentados. No es una clasificación pensionaria definitiva.")]
    eda = [md("# 02 · EDA completo ENASEM\n\nTodos los bloques exploratorios existentes, con sus poblaciones independientes, comparaciones, pensiones/apoyos, bivariados, trivariados y seguimiento. Sin modelos, outcomes o preguntas definitivas. La ejecución lee agregados y figuras guardados.\n\n" + "\n".join(f"- [{i}. {title}](#{key})" for i, (key,title) in enumerate(SECTIONS[3:],1))), code(setup),
           md("## Configuración y filtros poblacionales\n\nCP1 conserva todas las edades/modalidades. El EDA pensionario utiliza 60+ por visita; los EDA independientes de ENASEMsimple y K usan sus universos originales. No se suman poblaciones ni se filtra el maestro permanentemente. `PopulationSpec` centraliza la selección."),
           code("sample_spec = PopulationSpec(minimum_age=60)\nexploratory = load_json('docs/eda/pensiones_exploratorio_v1/resultados.json')\nassert exploratory['poblacion']['N_personas_ronda_60'] == 56004\nassert exploratory['poblacion']['N_personas_60'] == 18754\ndisplay(pd.DataFrame([exploratory['poblacion']]))"),
           md("## Disponibilidad y búsqueda de variables\n\nEl diccionario integrado y el mapa conservan 8,668 columnas; no son 8,668 conceptos validados. La búsqueda reúne definición, procedencia, onda, etiquetas, titularidad y comparabilidad. Las 429 fichas independientes están consolidadas, sin perder sus resultados."),
           code("display(pd.DataFrame(find_variable('imp_neto')))\ndisplay(pd.DataFrame(load_json('diccionarios/cobertura_variables.json')))"),
           md("## Comparaciones entre rondas\n\nLa comparación de seis muestras transversales no es una trayectoria individual. Montos nominales no son crecimiento real; la escala de localidad es <100 mil/≥100 mil. Las gráficas BrBG originales se preservan."),
           code("display(pd.DataFrame(exploratory['comparativos_univariados']).T)")]
    for key, title in SECTIONS[3:]:
        eda += [md(f'<a id="{key}"></a>\n\n## {title}\n\nSección independiente: puede ejecutarse después de la configuración sin recalcular otros bloques. `BUSCAR` limita la lectura, no cambia los datos ni denominadores.'), code(f"display_section('{key}', BUSCAR)")]
    for name, cells in [("01_INTEGRACION", integration), ("02_EDA_COMPLETO", eda)]:
        if kind != "all" and kind not in name:
            continue
        notebook = nbformat.v4.new_notebook(cells=cells, metadata={"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"}})
        path = PROJECT_ROOT / "notebooks" / (name + ".ipynb")
        nbformat.write(notebook, path)
        if execute:
            NotebookClient(notebook, timeout=1800, kernel_name="python3", resources={"metadata":{"path":str(PROJECT_ROOT)}}).execute()
            destination = INTERIM_DIR / "notebooks_ejecutados" / (name + "_ejecutado.ipynb")
            destination.parent.mkdir(parents=True, exist_ok=True)
            nbformat.write(notebook, destination)
            print(name + " ejecutado sin errores")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--kind", default="all", choices=["all", "INTEGRACION", "EDA"])
    args = parser.parse_args()
    build(args.kind, args.execute)
