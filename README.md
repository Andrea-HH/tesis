# Tesis ENASEM — proyecto local de trabajo

Investigación de pensiones, titularidad, instituciones y apoyos, 2001–2021.
La redacción integra ocho notebooks sobre cobertura y montos de protección
económica. La hipótesis autorizada es que ampliar cobertura no necesariamente
implica reducir de modo equivalente las desigualdades monetarias o mejorar
uniformemente el poder adquisitivo; no se presenta como conclusión general.
La prioridad vigente es la redacción formal de los cinco capítulos sobre protección
económica, con evidencia de 06–08 y precisión de 10.7. GitHub queda en pausa.

| Necesito | Ubicación |
|---|---|
| Integración, puentes, claves y validaciones | [01_INTEGRACION](notebooks/01_INTEGRACION.ipynb) |
| EDA individual, comparaciones, pensiones y trayectorias | [02_EDA_COMPLETO](notebooks/02_EDA_COMPLETO.ipynb) |
| Ampliación pensiones, salud, cognición y funcionalidad | [03_PENSIONES_SALUD_COGNICION](notebooks/03_PENSIONES_SALUD_COGNICION.ipynb) |
| Seguimiento integral de pensiones y salud mental | [04_TRAYECTORIAS_PENSIONES_SALUD](notebooks/04_TRAYECTORIAS_PENSIONES_SALUD.ipynb) |
| Mortalidad registrada y selección multidimensional | [05_PENSIONES_MORTALIDAD_SELECCION](notebooks/05_PENSIONES_MORTALIDAD_SELECCION.ipynb) |
| Cobertura propia K/A, montos y selección económica | [06_COBERTURA_PROTECCION_ECONOMICA](notebooks/06_COBERTURA_PROTECCION_ECONOMICA.ipynb) |
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
La evidencia exhaustiva conserva las contribuciones de los 610 documentos previos;
el informe presenta una síntesis académica selectiva, sin eliminar sus análisis.
CP1 mantiene 99,676 personas-ronda/27,171 personas; la muestra pensionaria 60+
por visita mantiene 56,004/18,754. No sumar universos ni interpretar diferencias
transversales como cambios individuales. Diseño/ponderadores, homologaciones
pendientes y normas UDLAP limitan el alcance; la etapa 07 resolvió la actualización
INPC y la referencia operativa de LPI, sin acreditar suficiencia integral. K no implica contributividad y A no implica pensión no
contributiva; ND no es negativa. No se recalcularon resultados por limpiar archivos.

## Instalación y uso

Python >=3.11:

```bash
python -m pip install -e ".[notebooks,dev,manuscrito,documentacion]"
python -m pytest -q
python scripts/validate_notebooks.py
python scripts/validate_manuscript.py
python scripts/validate_migration.py
python scripts/build_report_pdf.py
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

## Informe académico selectivo y PDF generado

INFORME_GENERAL.md es la única fuente editable. INFORME_GENERAL.pdf se genera
exclusivamente desde ese Markdown mediante `python scripts/build_report_pdf.py`.
Los notebooks conservan el análisis exhaustivo; el informe reúne los resultados
relevantes con selección razonada, incluidos contrastes nulos o débiles, población,
denominadores, interpretación, límites y procedencia. No incorporar automáticamente
todas las tablas o imágenes ni seleccionar por significancia.

Las tablas seleccionadas son reales y las figuras están insertadas junto a su
análisis, desde resultados/figuras/. Mantener sus escalas, cifras y paleta. Los
resultados no seleccionados permanecen en agregados y evidencia auxiliar.
`tesis_enasem.workspace.report_section` permite consultar las secciones exhaustivas
previas desde los notebooks sin modificar sus archivos. El registro de selección
está en data/interim/informe_general_seleccion.json.

Después de actualizar la síntesis desde un notebook independiente, regenerar el
PDF y verificar la sincronización con `python scripts/build_report_pdf.py --check`; no editarlo manualmente ni crear informes por
análisis. El generador comprueba texto, celdas, figuras, enlaces y límites de página,
y limpia sus temporales. La revisión visual complementa estas comprobaciones.

## Ampliación pensionaria de salud — notebook 03

El nuevo notebook es independiente: 60+ por visita, seis rondas y sin panel
balanceado. Reutiliza las 30 correlaciones anteriores y amplía tamaños de efecto,
distribuciones, trivariados seleccionados, estandarización descriptiva y otras
ramas verificables. No modifica 01/02, bases, resultados previos o capítulos.
TICS queda pendiente por falta de columna/contrato; orientación/2001 y serial7
antes de 2015 no se cruzan. Imputación y diseño limitan los IC; no hay inferencia
nacional, causalidad, selección por significancia ni modelos predictivos.

Reproducción deliberada (no necesaria para leer el notebook):

```bash
python scripts/run_pension_health.py
python scripts/build_pension_health_outputs.py
python scripts/export_pension_health_report.py
python scripts/build_report_pdf.py
python scripts/validate_pension_health.py
python scripts/build_report_pdf.py --check
```

Los resultados exhaustivos están en data/interim/pensiones_salud/resultados.json;
la ejecución local está en data/interim/notebooks_ejecutados/. Los constructores
protegen ediciones manuales del notebook y de sus bloques académicos. El informe
incorpora solo cinco cuadros y seis figuras nuevos, con denominadores y límites.

## Seguimiento de pensiones y salud mental — notebook 04

El notebook 04 integra las seis rondas, los cinco intervalos consecutivos y
trayectorias de múltiples visitas, sin exigir panel balanceado. El criterio principal
exige nueve componentes CES-D completos; los conteos parciales del proveedor se
conservan como sensibilidad y no se rellenan con cero. Comparabilidad operacional
condicionada, sin invariancia psicométrica certificada ni causalidad. Las rupturas K
2003–2012 y 2015–2018 se mantienen como patrones de respuestas no homologados.

Los 30,038 pares corresponden a 13,570 personas; 8,322 participan en más de un
intervalo. No se agrupan como observaciones independientes. La ejecución completa
queda en data/interim/notebooks_ejecutados/ y los agregados en
data/interim/trayectorias_pensiones_salud/. Ocho figuras BrBG; selección académica
en el único informe general. Bases, notebooks 01–03 y capítulos LaTeX intactos.

```bash
python scripts/run_longitudinal_health.py
python scripts/build_longitudinal_health_notebook.py
python scripts/validate_longitudinal_health.py
python scripts/export_longitudinal_health_report.py
python scripts/build_report_pdf.py
python scripts/build_report_pdf.py --check
```

Pendientes: concordancia literal de preguntas brutas CES-D, invariancia, diseño y
ponderación longitudinal. No se construyeron índices cognitivos ni TICS, ni modelos
predictivos. La pregunta del notebook es exploratoria, no una pregunta definitiva
de tesis. La auditoría metodológica está en
[contrato longitudinal de salud mental](diccionarios/contrato_longitudinal_salud_mental.json).

## Pensiones, mortalidad registrada y selección — notebook 05

Integra los cinco intervalos y la disponibilidad de 16 indicadores de salud física,
salud mental, cognición, funcionalidad y economía. Distingue registro sobre fallecido,
ausencia de vital desconocido, sustituto, ineligibilidad de instrumento/modalidad y
medición inválida. D/cohorte no equivale a mortalidad completa ni tasa anual.
La estandarización describe composición basal dentro de soporte, sin causalidad.

No se implementaron Kaplan–Meier, Cox o IPW: estado vital de ausentes y fechas de
defunción no verificados. No se estimaron pesos, ESS, extremos o balance. Los escenarios
se limitan a vivos confirmados, sin reemplazar mediciones ni construir síntomas
posteriores al fallecimiento. No hay cambios monetarios reales sin homologación.
La documentación oficial cambia restas de 7 a 3 en 2021: no calcular diferencias
2018–2021 de serial7; conservar cobertura y perfiles basales del campo.

```bash
python scripts/run_selection_mortality.py
python scripts/build_selection_mortality_notebook.py
python scripts/validate_selection_mortality.py
python scripts/export_selection_mortality_report.py
python scripts/build_report_pdf.py
python scripts/build_report_pdf.py --check
```

Agregados y manifiesto: data/interim/pensiones_mortalidad_seleccion/.
Notebook ejecutado: data/interim/notebooks_ejecutados/. Seis figuras BrBG; cinco
cuadros y cuatro figuras seleccionados en el único informe, ahora de 69 páginas.
143 pruebas satisfactorias; fuentes, bases, notebooks 01–04 y LaTeX intactos.
El [contrato de mortalidad y selección](diccionarios/contrato_mortalidad_seleccion.json)
conserva definiciones, límites y fuentes oficiales. Git/GitHub permanecen sin operaciones.

## Cobertura y monto de protección económica — notebook 06

La pregunta de la autora orienta la exploración de brechas económicas; mortalidad
y selección son sensibilidades. Principal: entrevistas directas de personas vivas
60+ por visita; respuestas válidas por sustituto se muestran separadamente.
Tipología exhaustiva 2018/2021: ocho combinaciones con pareja confirmada, cuatro
propias K/A sin pareja residente, desconocidos y modalidades excluidas separados.
K propia o A propia es una unión de personas, nunca suma de tasas o montos.

Montos mensuales nominales por evento y sumas personales observadas parciales
usan denominadores distintos. Cónyuge es recurso contextual de otra persona.
No se evaluó suficiencia: el [contrato y configuración](diccionarios/contrato_proteccion_economica.json)
mantiene bloqueada la deflactación hasta confirmar fuente INPC y umbral compatibles.
La unión K/A solo admite comparación longitudinal condicionada en 2012–2015;
las rupturas también limitan las tendencias de brechas. No modelos opcionales,
KM, Cox, IPW ni atribución a reformas. No se modifican notebooks 01–05 ni LaTeX.

```bash
python scripts/run_economic_protection.py
python scripts/build_economic_protection_notebook.py
python scripts/validate_economic_protection.py
python scripts/export_economic_protection_report.py
python scripts/build_report_pdf.py
python scripts/build_report_pdf.py --check
```

Agregados completos: data/interim/cobertura_proteccion_economica/resultados.json.
Copia ejecutada: data/interim/notebooks_ejecutados/06_COBERTURA_PROTECCION_ECONOMICA_ejecutado.ipynb.
El informe selecciona resultados sustantivos sin reemplazar contribuciones previas.
Se cotejan por SHA256 1,530 archivos anteriores, incluido el índice Git, sin operaciones Git.

La entrega de la etapa 06 pasó 147 pruebas y la validación de 17 notebooks fuente.
El informe generado tiene 80 páginas, 37 cuadros y 38 figuras; siete cuadros y cinco
figuras corresponden a esta ampliación, en la sección 10.2.

## Políticas, montos y poder adquisitivo — notebook 07

La pregunta central de la autora se conserva. La hipótesis de reducción de brechas
de acceso sin igualación de montos o suficiencia se contrasta por periodo y grupo.
[Notebook independiente](notebooks/07_POLITICAS_MONTOS_SUFICIENCIA.ipynb),
[copia ejecutada con resultados](data/interim/notebooks_ejecutados/07_POLITICAS_MONTOS_SUFICIENCIA_ejecutado.ipynb)
y [contrato monetario](diccionarios/contrato_monetario_politicas.json).

Referencia común: **septiembre de 2026, INPC oficial INEGI 146.075**, base segunda
quincena de julio de 2018=100, serie mensual 865541 enlazada y actualizada en 2024.
Consulta: 14 de octubre de 2026. Se conserva la descarga oficial enero de 2000 a
septiembre de 2026. Las fuentes confirmadas permiten la etapa 07; el bloqueo de 06
describe el estado anterior y no se alteran sus notebooks, contratos o resultados.

K/A preguntan por año pasado y mes normal, sin mes de pago identificado. Se usa el
promedio del año calendario anterior al **año real de entrevista**, con sensibilidades
de doce meses previos, año de entrevista y extremos mensuales. Se conserva el nominal
y se actualiza cada importe antes de resumir. Ronda 2021 incluye entrevistas en 2022.
No se reparten montos por institución, se suman versiones ni se construye ingreso
total o K+A. Cónyuge es contexto separado; sustitutos válidos son sensibilidad.

LPI históricas oficiales mensuales por persona, con corte rural de 2,500 habitantes;
la variable de 100 mil no lo reemplaza. Códigos originales 2012–2021 permiten asignar
umbrales, conservando faltantes/discordancias. En 2001/2003 se utilizan escenarios
para localidades sin clasificación suficiente. Una prestación bajo la LPI no
diagnostica pobreza. INPC mide poder adquisitivo, no valor presente actuarial.

[Fuentes y cronología documental](investigacion/notas/politicas_publicas_envejecimiento.md)
enlazan reglas oficiales y límites de atribución. Los análisis reutilizan cobertura 06
y selección previa; no estiman efectos causales de reformas. Montos, brechas, políticas
y sensibilidad se incorporan al mismo informe acumulativo, sección 10.3.

```bash
python scripts/run_monetary_policy.py
python scripts/document_monetary_contract.py
python scripts/build_monetary_policy_notebook.py
python scripts/validate_monetary_policy.py
python scripts/export_monetary_policy_report.py
python scripts/build_report_pdf.py
python scripts/build_report_pdf.py --check
```

Los agregados y las huellas están en `data/interim/politicas_montos_suficiencia/`.
La fuente del notebook conserva el patrón sin outputs; la copia ejecutada permite
consultar tablas, gráficas e interpretaciones. Bases, notebooks 01–06 y LaTeX siguen
intactos, verificados contra 1,594 archivos protegidos. Sin operaciones Git/GitHub.

La etapa 07 pasó 152 pruebas, validación de 18 notebooks y ejecución de 01/02
en memoria sin recalcular. El informe sincronizado tiene 95 páginas, 45 cuadros y
43 figuras: ocho cuadros y cinco figuras nuevos. La copia ejecutada de 07 contiene
51 celdas; se verificaron todas las páginas nuevas del PDF y los enlaces internos.

## Síntesis de cobertura, poder adquisitivo y referencia económica — 06/07

La sección 10.4 del [informe acumulativo](resultados/INFORME_GENERAL.md) integra
exclusivamente los agregados existentes de 06/07. Conserva septiembre de 2026 como
referencia monetaria y distingue cobertura, mediana personal parcial, comparación
con LPI, cambios individuales y selección de seguimiento. Las rupturas de definición
permanecen explícitas: la unión K/A solo admite comparación condicionada en 2012–2015.
Las evaluaciones H1–H4 son descriptivas; no identifican causalidad, pobreza individual,
ingreso completo ni convergencia general en 2001–2021.

```bash
python scripts/export_protection_synthesis.py
python scripts/build_report_pdf.py
python scripts/build_report_pdf.py --check
```

La evidencia técnica está en `data/interim/sintesis_proteccion_economica/`.
El PDF sincronizado tiene 106 páginas, 50 cuadros y 44 figuras; la síntesis añade
cinco cuadros y una figura, preservando íntegros los once bloques académicos previos.
Pasaron 154 pruebas y las validaciones de notebooks, manuscrito y migración.
Las páginas nuevas del PDF fueron renderizadas y revisadas. Se verifican por SHA256
1,768 archivos anteriores: bases, notebooks 01–07, sus resultados y manuscrito
permanecen intactos. No se crea otro notebook ni se realizan operaciones Git/GitHub.

## Transiciones y montos pensionarios — notebook 08

[Fuente reproducible](notebooks/08_TRANSICIONES_MONTOS_PENSIONARIOS.ipynb) y
[copia ejecutada con tablas y figuras](data/interim/notebooks_ejecutados/08_TRANSICIONES_MONTOS_PENSIONARIOS_ejecutado.ipynb).
La auditoría de viabilidad precede al nuevo análisis: transiciones de recepción en
seis ventanas elegibles; comparación monetaria central K2012–2015/A2015–2018.
Solo se suman eventos captados si todos tienen monto válido. No hay identidad
administrativa de prestación; A general no es A5 longitudinal. Se documentan cambios
personales, puente contable de precios y comparación de distribuciones con composición
basal común, sin interpretación causal ni corrección de mortalidad/ausencia.

La comparación principal utiliza 1,756 pares K y 1,223 A íntegros. Un registro A
con conflicto vital previo se conserva como evidencia original y se separa del
principal; los 1,224 pares sin ese criterio quedan como sensibilidad explícita.
Definiciones: [contrato08](diccionarios/contrato_transiciones_montos_pensionarios.json).
Los agregados completos y validaciones están en `data/interim/transiciones_montos_pensionarios/`.

```bash
python scripts/run_benefit_transitions.py
python scripts/build_benefit_transitions_notebook.py
python scripts/validate_benefit_transitions.py
python scripts/export_benefit_transitions_report.py
python scripts/build_report_pdf.py
python scripts/build_report_pdf.py --check
```

La sección10.5 incorpora siete cuadros y tres figuras. El PDF sincronizado tiene
121 páginas, 57 cuadros y 47 figuras; las páginas nuevas se renderizaron y revisaron.
Pasaron 161 pruebas y las validaciones de19 notebooks fuente, manuscrito y migración.
Se cotejan 1,948 archivos anteriores y doce bloques académicos íntegros: bases,
notebooks01–07, resultados previos y manuscrito intactos. Sin operaciones Git/GitHub.

## Auditoría de aportación científica — 14/10/2026

La sección 10.6 del [informe único](resultados/INFORME_GENERAL.md) incorpora el
diagnóstico de los ocho notebooks, 18 hallazgos seleccionados y 16 antecedentes
contrastados. Se añadieron 15 referencias verificadas a la bibliografía activa,
conservando las 50 anteriores. El PDF sincronizado tiene 147 páginas, 66 cuadros y
47 figuras; la auditoría comienza en la página 120. No se ejecutaron análisis nuevos.

La redacción descriptiva puede comenzar; la originalidad fuerte, la precisión de
los contrastes centrales y cualquier inferencia nacional requieren cierre adicional.
La selección metodológica y editorial es una propuesta; no adopta causalidad,
modelos nuevos o conclusiones predeterminadas. Notebooks, datos, resultados
estadísticos, figuras y capítulos permanecen intactos. Pasaron 161 pruebas y las
validaciones de notebooks, manuscrito, migración y sincronización del PDF.
La evidencia técnica se registra en data/interim/auditoria_aportacion_cientifica.json.
No se realizaron operaciones de Git/GitHub ni cambios de selección.

## Validación final de precisión y diagnóstico del manuscrito — 14/10/2026

La sección 10.7 del [informe único](resultados/INFORME_GENERAL.md) añade intervalos
condicionales para los contrastes priorizados de 06–08: 9,999 réplicas por persona,
sensibilidad por folio `cunicah`, comprobaciones binomiales de medianas, empates,
soporte de composición fijo y cotas externas por montos faltantes. No son IC de
diseño nacional ni una corrección de selección, precios o errores de medición.

El contraste K nuevos−continuos de 2012–2015 es grande y estable; con evidencia
IMSS/ISSSTE incluye cero. A 2015–2018 conserva medianas iguales sin demostrar
igualdad de distribuciones. La caída personal mediana A mantiene signo negativo
bajo los criterios temporales examinados; la pequeña caída K depende de fechas
y faltantes. Por sexo, se precisa la reducción de la brecha de cobertura de unión
K/A, pero el IC del aumento puntual de la brecha monetaria K contiene cero.

El diagnóstico compara los tres antecedentes más próximos de 10.6 y delimita
una contribución empírica incremental, sin reclamar mecanismos causales o
originalidad frente a toda la literatura. Propone cinco cuadros y cuatro figuras
centrales e identifica archivos, secciones y líneas a actualizar en los cinco
capítulos. El manuscrito queda pendiente de revisión de la autora, sin editarlo.

```bash
python scripts/run_benefit_transitions.py --precision
python scripts/validate_benefit_transitions.py --precision
python scripts/export_benefit_transitions_report.py --precision
python scripts/build_report_pdf.py
python scripts/build_report_pdf.py --check
```

Evidencia: `data/interim/transiciones_montos_pensionarios/precision.json`, su
manifiesto y `precision_informe.json`. Las funciones originales de 08 permanecen
equivalentes por AST. Los agregados anteriores no se sobrescriben; no se crea
otro notebook. La bibliografía activa conserva sus 65 entradas y añade dos
fuentes metodológicas. La actualización documentada de la huella bibliográfica
del control 08 admite esas extensiones autorizadas, manteniendo intactos los
otros 1,947 insumos protegidos.

El PDF sincronizado tiene 157 páginas, 72 cuadros y 48 figuras; las páginas nuevas,
el índice, los cuadros y la figura de precisión fueron renderizados y revisados.
Pasaron 168 pruebas
y las validaciones de notebooks, manuscrito y migración. Se cotejan 2,124 archivos
y 14 bloques académicos anteriores intactos. Bases originales/procesadas,
notebooks 01–08, resultados previos y todos los archivos LaTeX permanecen sin
cambios. Sin operaciones Git/GitHub ni cambios de selección.

## Redacción formal integrada — 14/10/2026

Los cinco capítulos de [manuscrito/main.tex](manuscrito/main.tex) desarrollan la
pregunta e hipótesis autorizadas sobre cobertura, montos reales, incorporación,
continuidad y heterogeneidad institucional. El capítulo 4 contiene cinco cuadros
centrales y cuatro figuras existentes; los dos anexos conservan los cuadros CP1
y los pendientes editoriales. Se citan 45 referencias de la bibliografía activa.
La hipótesis se contrasta parcialmente y no se presenta como conclusión general
ni como evaluación causal de políticas.

El PDF compilado tiene 65 páginas. La reducción frente a las 110 páginas previas
responde a la sustitución autorizada del enfoque de predicción/vulnerabilidad y
a la selección de resultados, no a cambios en la evidencia. Los 61 archivos
LaTeX anteriores completos y sus huellas están en
`data/interim/migracion_proyecto.json`, entrada `redaccion_formal`; el PDF previo
permanece en `data/interim/manuscrito_antes_redaccion_20261014.pdf`.

La reproducción editorial utiliza `python scripts/export_protection_manuscript.py
--formal` y el procedimiento de [manuscrito/README.md](manuscrito/README.md).
Solo exporta cifras de agregados existentes. La validación de macros numéricas
evita referencias silenciosamente vacías. Pasaron 170 pruebas y las validaciones
de notebooks, manuscrito, migración y sincronización del informe general.
Se revisaron visualmente el PDF, los cuadros y las cuatro figuras apaisadas;
no quedaron referencias indefinidas ni texto fuera de los márgenes.

Las bases originales/procesadas, notebooks 01–08, resultados estadísticos,
figuras, bibliografía e informe general Markdown/PDF permanecen intactos.
Quedan pendientes la revisión académica de la autora, el título, los datos
institucionales y las normas UDLAP. La defensa debe mantener las restricciones
de comparabilidad, selección, montos parciales e inferencia condicionada a la
muestra. No se realizaron operaciones de Git/GitHub ni cambios de selección.
