# Tesis ENASEM — proyecto local de trabajo

Exploración de pensiones, titularidad, instituciones y apoyos, 2001–2021.
Sin pregunta definitiva, outcome, hipótesis causal ni modelo predictivo adoptados.
La prioridad es la organización local; GitHub queda en pausa.

| Necesito | Ubicación |
|---|---|
| Integración, puentes, claves y validaciones | [01_INTEGRACION](notebooks/01_INTEGRACION.ipynb) |
| EDA individual, comparaciones, pensiones y trayectorias | [02_EDA_COMPLETO](notebooks/02_EDA_COMPLETO.ipynb) |
| Todos los resultados académicos y explicaciones | [INFORME_GENERAL](resultados/INFORME_GENERAL.md) |
| Definiciones, contratos y metadatos | diccionarios/ |
| Fuentes originales intactas | data/raw/ |
| Agregados completos, extracciones y ejecuciones | data/interim/ |
| Bases analíticas y manifiestos | data/processed/ |
| Bibliografía principal | [referencias.bib](investigacion/referencias.bib) |
| Antecedentes únicos | [notebooks históricos](investigacion/notas/notebooks_historicos/README.md) |
| Capítulos, cuadros y PDF local | manuscrito/capitulos/, tablas/ y build/ |
| Lógica, ejecución y tests | src/tesis_enasem/, scripts/ y tests/ |

Los notebooks de trabajo permanecen juntos en notebooks/. Los once antecedentes se
conservan íntegros en investigación y no gobiernan la metodología vigente.
El informe íntegro conserva las contribuciones de los 610 documentos previos.
CP1 mantiene 99,676 personas-ronda/27,171 personas; la muestra pensionaria 60+
por visita mantiene 56,004/18,754. No sumar universos ni interpretar diferencias
transversales como cambios individuales. Pesos, precios, homologaciones y normas
UDLAP siguen pendientes. K no implica contributividad y A no implica pensión no
contributiva; ND no es negativa. No se recalcularon resultados por limpiar archivos.

## Instalación y uso

Python >=3.11:

```bash
python -m pip install -e ".[notebooks,dev,manuscrito,documentacion]"
python -m pytest -q
python scripts/validate_notebooks.py
python scripts/validate_manuscript.py
python scripts/validate_migration.py
python scripts/compile_manuscript.py --engine tectonic
```

Abrir los dos notebooks principales y ejecutar su configuración. Leen evidencia
local guardada sin repetir la integración ni el EDA. BUSCAR filtra lectura, no datos.
Los scripts científicos permanecen disponibles para reproducción deliberada.
Los alias de rutas antiguas son compatibilidad y nunca autorización para recrear
carpetas. Toda figura académica está centralizada en resultados/figuras/.

## Conservación y estado

La limpieza física autorizada retiró los 2,162 históricos inventariados: docs/ y
reports/ ya no existen en el proyecto activo.
Se conservan todas las bases, resultados, capítulos, diccionarios, once notebooks
históricos, capturas de revisión, PDF histórico y nota editorial de figuras.
El respaldo externo original y el archivo adicional de las copias preparadas
para GitHub se verifican en data/interim/migracion_proyecto.json.
La carpeta publicacion_github dejó de ser parte del flujo local.

El índice de Git contiene la selección pública preparada en la tarea anterior:
esta tarea no la modifica. Sus diferencias con las ediciones completas locales
son deliberadas y quedan pendientes de la futura tarea de publicación. No hacer
commit, push, merge ni git add . automáticamente.

## Notebooks futuros e informe único

01_INTEGRACION y 02_EDA_COMPLETO conservan el trabajo ya consolidado. Se corrigen
o actualizan cuando el trabajo les corresponde; no reciben automáticamente todos
los análisis futuros. Cuando un análisis nuevo solicitado justifique independencia,
crear un notebook directamente en notebooks/, con numeración consecutiva desde 03
y nombre descriptivo, sin subcarpetas ni duplicar análisis existentes. Reutilizar src/.

Cada notebook incluye objetivo, datos y variables, metodología, código reproducible,
tablas, gráficas, interpretaciones y limitaciones. Todos contribuyen al único informe
académico, resultados/INFORME_GENERAL.md: incorporar resultados e interpretaciones
por sección, procedencia del notebook, universo, denominadores, límites y estado
validado o provisional. El informe debe entenderse sin ejecutar los notebooks.
No crear informes por notebook ni notebooks de ejemplo durante la organización.

## Capítulos completos y antecedentes experimentales

Cada capítulo completo se conserva en un único archivo .tex, directamente en
manuscrito/capitulos/, sin subcarpetas ni archivos independientes por sección.
manuscrito/main.tex reúne los cinco capítulos y los dos anexos. Los cuadros
exportados permanecen en manuscrito/tablas/ y el PDF en manuscrito/build/.
Los exportadores actualizan bloques dentro del capítulo completo mediante
tesis_enasem.project_paths; no recrean módulos separados.
No volver a crear experiments/. Su única nota se conserva íntegra en
investigacion/notas/antecedente_protocolos_experimentos.md como antecedente,
no como metodología vigente. Los notebooks futuros permanecen independientes
en notebooks/ y todos aportan resultados al único resultados/INFORME_GENERAL.md.

La consolidación de los 23 módulos conserva cinco capítulos y dos anexos completos.
El PDF recompilado mantiene 110 páginas, con texto, imagen y enlaces idénticos
al anterior en todas las páginas. Se validaron 50 claves bibliográficas y
98 etiquetas; pasaron 122 pruebas. Las bases, notebooks, cuadros, figuras y
agregados se cotejaron por huella sin recálculo. La nota histórica puede leerse en
[antecedente de protocolos](investigacion/notas/antecedente_protocolos_experimentos.md);
su referencia antigua a docs/EXPERIMENTOS.md corresponde al texto conservado en
el informe general. No se ejecutaron operaciones Git.
