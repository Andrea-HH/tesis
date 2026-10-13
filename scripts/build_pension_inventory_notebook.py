from tesis_enasem.project_paths import project_path, read_project_text, write_project_text
"""Construye notebook de auditoría previa; jamás incluye filas de microdatos."""
from pathlib import Path
import nbformat as nbf
ROOT=Path(__file__).resolve().parents[1]

def build() -> None:
    """Notebook fuente sin outputs; cada archivo conserva su sección independiente."""
    md=nbf.v4.new_markdown_cell; code=nbf.v4.new_code_cell
    cells=[md('''# Inventario exhaustivo de fuentes económicas y pensionarias

**Objetivo.** Revisar por separado todos los archivos suministrados antes del EDA conjunto y de una unión definitiva. Referencia 2001–2021, archivo 2024 separado. No se recalcula ni reemplaza CP1, no se construyen las ocho variables todavía y no se inicia CP2.

**Método.** Lectura completa de cada fuente, etiquetas y códigos del proveedor, faltantes Stata, claves y correspondencias agregadas. Ninguna celda muestra identificadores o filas individuales. El diccionario íntegro conserva todas las variables, no solo las pensionarias. Véase `docs/pensiones/README.md` para la interpretación y las limitaciones.'''),code('''from pathlib import Path
import sys, json
import pandas as pd
from IPython.display import display, Markdown
import matplotlib.pyplot as plt
ROOT = Path.cwd() if (Path.cwd()/"src").exists() else Path.cwd().parent
assert (ROOT/"src").exists(), "Ejecutar desde notebooks/ o raíz del repositorio"
sys.path.insert(0, str(ROOT/"scripts"))
from inventory_pension_sources import run_inventory
from export_pension_review import write_review
from export_pension_availability import export_availability
pd.set_option("display.max_rows", None)
pd.set_option("display.max_colwidth", None)
'''),md('''## Ejecución y exportación reproducible

Se inspeccionan todos los `.dta` de `data/raw/` y todas las hojas del inventario Excel. Las fuentes no se apilan; los puentes son temporales y solo de claves. Cada hash permite comprobar la versión inspeccionada. Los archivos de entrada y el Excel no se modifican.'''),code('''audit = run_inventory(ROOT/"data/raw")
out = ROOT/"reports/tables/pensiones_inventario.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(audit, ensure_ascii=False, indent=2)+"\\n")
write_review()
availability = export_availability()
public = json.loads((ROOT/"docs/pensiones/inventario_fuentes.json").read_text())
sources = public["fuentes"]
assert sum(s["n_variables"] for s in sources) == len(public["variables"])
assert len(availability["disponibilidad"]) == 8*6
summary = pd.DataFrame([{k:s[k] for k in ["fuente_id","archivo","anio_nominal_verificado","n_registros","n_variables","unidad_fila"]} for s in sources])
display(summary)
'''),md('''## Visualización del inventario

El gráfico compara **filas de cada fuente**, no personas independientes. Las entrevistas de hogar y los individuales tienen unidades distintas; fuentes originales y construidas se solapan. El duplicado se mantiene y 2024 se distingue. El total longitudinal de ENASEMsimple se presenta en la tabla y se omite del gráfico para facilitar la lectura de las fuentes económicas.'''),code('''plot = summary.loc[summary.archivo != "simpleMHAS.dta"].copy()
fig, ax = plt.subplots(figsize=(11,8))
colors = ["#a85a30" if y == 2024 else "#2b627d" for y in plot.anio_nominal_verificado]
ax.barh(plot.archivo, plot.n_registros, color=colors)
ax.invert_yaxis()
ax.set_xlabel("Filas de la fuente (unidades y universos distintos)")
ax.set_title("Inventario económico: todas las fuentes inspeccionadas")
fig.tight_layout()
figure_path = ROOT/"reports/figures/pensiones_inventario_fuentes.png"
figure_path.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(figure_path, dpi=160, bbox_inches="tight")
plt.show()
''')]
    import json
    audit=json.loads(read_project_text(project_path('', 'docs/pensiones/inventario_fuentes.json')))
    for source in audit['fuentes']:
        name=source['archivo']
        cells+=[md(f'''## {source['fuente_id']} — {name}

**Objetivo:** documentar esta fuente íntegramente. **Método:** conservar códigos, etiquetas y perdidos; probar claves candidatas sin mostrar sus niveles. La ronda nominal y la fecha de versión no sustituyen el año efectivo de entrevista. El diccionario de todas las columnas aparece a continuación; los códigos numéricos NR/NS aún requieren su cuestionario y no están incluidos automáticamente como faltantes.

**Interpretación:** {source['unidad_fila']}. {"2024 se inspecciona sin incorporarlo a las seis rondas principales." if source['anio_nominal_verificado']==2024 else "La presencia de una columna no acredita equivalencia longitudinal, respuesta aplicable ni titularidad individual."}'''),code(f'''source = next(s for s in sources if s["archivo"] == {name!r})
display(pd.DataFrame(source["claves_candidatas"]))
variables = pd.DataFrame([v for v in public["variables"] if v["archivo"] == source["archivo"]])
assert len(variables) == source["n_variables"]
display(variables[["variable","etiqueta","dtype","n","n_no_perdidos_stata","n_perdidos","pct_perdidos","perdidos_especiales","etiquetas_valores"]])
''')]
    cells += [md('''## Duplicados, versiones y contrastes de la misma ronda

SHA-256 identifica duplicados binarios. Para cada pareja de la misma ronda se auditan claves y columnas compartidas. Solo con claves únicas en ambos lados se comparan versiones por conteos de discrepancia, sin devolver valores individuales. Los nombres iguales no prueban equivalencia semántica.'''),code('''display(Markdown("**Duplicados:** "+str(public["duplicados_binarios"])))
comparisons = public["comparaciones_misma_ronda"]
display(pd.DataFrame([{k:v for k,v in c.items() if k not in ["variables_mismo_nombre","discrepancias_por_variable"]} for c in comparisons]))
for c in comparisons:
    if "discrepancias_por_variable" in c:
        display(Markdown(f"**{c['fuente_a']} ↔ {c['fuente_b']}**: {c['n_comparadas']:,} filas con clave 1:1"))
        display(pd.DataFrame(sorted(c["discrepancias_por_variable"].items()),columns=["Variable","Filas discrepantes/N comparadas"]))
'''),md('''## Correspondencias con ENASEMsimple

Denominador: registros de ENASEMsimple de la ronda y modalidad declaradas. La correspondencia acredita clave, no disponibilidad sustantiva ni que el monto pertenezca a esa persona. El puente 2001/2003 usa solo claves efímeras. La cobertura de directas es un diagnóstico secundario; el universo CP1 conserva todas las modalidades.'''),code('''display(pd.DataFrame(public["correspondencias_simple"]))
display(pd.DataFrame(public["puentes_historicos"]))
'''),md('''## Inventario Excel: todas las hojas

Lectura íntegra, sin editar el libro. Se presentan metadatos y tablas de referencia, nunca valores individuales. El pendiente de lectura de K original 2003 del inventario anterior se resolvió; el archivo de hogar imputado 2018 y los productos separados de ingreso total/patrimonio pertinentes siguen ausentes. El nombre local carece del sufijo `(1)`.'''),code('''for book in public["inventarios_referencia"]:
    for sheet in book["hojas"]:
        display(Markdown(f"### {sheet['hoja']} — {len(sheet['filas'])} filas, incluido encabezado"))
        display(pd.DataFrame([[c["valor"] for c in row] for row in sheet["filas"]]))
        if sheet["formulas"]:
            display(pd.DataFrame(sheet["formulas"]))
'''),md('''## Catálogo histórico y disponibilidad propuesta

El catálogo se basa en fuentes oficiales históricas. Los años individuales de recepción permanecen desconocidos; no se rellenan con el inicio de programas. La matriz de ocho conceptos declara posibilidad de identificación, no cobertura pensionaria calculada. Las matrices de **todas** las variables están en `docs/pensiones/MATRIZ_VARIABLES_FUENTES.md` y `DICCIONARIO_FUENTES.md`; las restricciones por concepto están en `DISPONIBILIDAD_RONDAS.md`.'''),code('''catalogue = json.loads((ROOT/"docs/pensiones/catalogo_programas.json").read_text())
display(pd.DataFrame(catalogue["programas"]))
display(pd.DataFrame(catalogue["relaciones"]))
display(pd.DataFrame(availability["disponibilidad"])[["variable_armonizada","ronda","estado_propuesto","limite","construida"]])
'''),md('''## Conclusiones y decisiones pendientes

Las fuentes tienen unidades, esquemas y versiones diferentes. Las dos copias de 2018 son idénticas; `acthog` no enlaza directamente en 2003; hay pérdidas de correspondencia de originales/imputados aunque algunos individuales enlacen completamente. Ninguna de estas ausencias se interpreta como ingreso cero.

Antes de una integración definitiva se necesita validar titular, universos, unidades y periodos por pregunta, revisar fuentes no tipificables y resolver versiones/productos faltantes. El EDA posterior abarcará todas las variables sustantivas de cada fuente antes de comparar versiones y rondas, con frecuencias, montos y denominadores elegibles. Las ocho variables y sus reglas siguen como especificación; no se aprueba muestra predictiva, etiqueta económica, deflactor ni CP2. La redacción LaTeX explica esta evidencia y el protocolo pendiente.''')]
    notebook=nbf.v4.new_notebook(cells=cells,metadata={'kernelspec':{'display_name':'Python (myenv)','language':'python','name':'myenv'},'language_info':{'name':'python','version':'3.11'}})
    nbf.write(notebook,project_path('', 'notebooks/02b_inventario_fuentes_pensiones.ipynb'))
    print('Notebook fuente:',len(cells),'celdas; sin outputs ni datos individuales.')

if __name__=='__main__':build()
