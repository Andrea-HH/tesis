# Manuscrito de tesis en LaTeX — enfoque vigente

**Estado al 23 de octubre de 2026.** El manuscrito adopta la pregunta sobre ampliación de protección propia al incorporarse a K/A, primera vía observada frente a complementariedad, diferencias monetarias y características socioeconómicas. Se conservan las comparaciones de cobertura y recursos reales, incorporación/continuidad y sensibilidad a muerte o ausencia como evidencia complementaria. La pregunta exacta y sus objetivos están en [01_introduccion.tex](capitulos/01_introduccion.tex) y en el [README principal](../README.md). El enfoque predictivo antiguo permanece exclusivamente en [antecedentes históricos](../investigacion/notas/notebooks_historicos/README.md).

Las fuentes de los cinco capítulos han sido actualizadas para revisión académica. **El [PDF local](build/main.pdf) fue recompilado y revisado tras el cierre de la etapa 10. La [validación](build/validacion_pdf.json) registra huellas de las fuentes sin commit; todavía no está publicado en GitHub.** El [Informe General](../resultados/INFORME_GENERAL.md) ofrece evidencia histórica y cifras auditadas, en especial secciones 10.5–10.7. La etapa 09 completa el cruce conjunto basal y posterior (Informe 10.8), con resultados heterogéneos por vía y límites de soporte; no identifica necesidad integral o causalidad. También permanecen pendientes normas UDLAP, datos de portada y aprobación editorial.

## Estructura actual

```text
manuscrito/
  main.tex                                  Documento principal y portada
  configuracion.tex                         Formato y paquetes provisionales
  capitulos/
    01_introduccion.tex                     Pregunta, objetivos, hipótesis y alcance
    02_marco_teorico_antecedentes.tex        Marco teórico y antecedentes
    03_datos_metodologia.tex                Fuentes, integración, métodos y límites
    04_analisis_exploratorio_resultados.tex Resultados centrales contrastados
    05_discusion_conclusiones.tex           Discusión y conclusiones condicionadas
    06_tablas_complementarias_cp1.tex       Anexo de auditoría
    07_estado_redaccion_pendientes_revision.tex Anexo de revisión
  tablas/                                   Cuadros y macros LaTeX
  estilo_cuadros.tex                        Formato de cuadros
  build/main.pdf                            PDF compilado disponible en GitHub
```

## Plantilla UDLAP: confirmación pendiente

**No se ha adoptado una plantilla institucional definitiva.** Confirmar con el departamento y la dirección las normas vigentes de tesis: portada, programa/grado, nombres, jurado, márgenes, tipografía, interlineado, numeración, resumen, estilo bibliográfico, entrega digital y permisos de difusión. La [guía pública de documentos de fin de carrera](https://catarina.udlap.mx/u_dl_a/tales/guias/estudiante/index.html), actualizada el 29 de noviembre de 2024, acepta PDF y fuentes LaTeX e indica requisitos de resumen, pero no acredita por sí misma el formato específico vigente del programa. Consultada el 11 de octubre de 2026; no se aplican sus fechas de entrega de 2025 a este proyecto.

El formato actual usa `report`, tamaño carta, 12 puntos, margen de 2.5 cm, interlineado de 1.5 y citas autor-año con natbib/BibTeX. Son elecciones de trabajo reversibles, **no normas UDLAP verificadas**. La portada tiene datos pendientes explícitos. Las figuras incluidas son borradores, no figuras aprobadas.

## Compilar y visualizar

Las fuentes y agregados exportados permiten compilar sin `simpleMHAS.dta` ni `reports/tables/`. Tener instalado TeX Live/MacTeX con latexmk y BibTeX, o Tectonic. No se instala automáticamente ninguna distribución desde los scripts.

Desde la raíz del repositorio:

```bash
python scripts/validate_manuscript.py
python scripts/compile_manuscript.py
```

El compilador detecta latexmk, Tectonic, pdflatex o xelatex; para los dos últimos requiere BibTeX. Se puede indicar un motor:

```bash
python scripts/compile_manuscript.py --engine tectonic
```

Equivalente con latexmk, desde `manuscrito/`:

```bash
mkdir -p build
latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=build main.tex
```

Equivalente con Tectonic:

```bash
mkdir -p build
tectonic --keep-logs --keep-intermediates --outdir build main.tex
```

Abrir `manuscrito/build/main.pdf` en un visor PDF. En macOS puede usarse `open manuscrito/build/main.pdf` desde la raíz. En VS Code, abrir `main.tex` con LaTeX Workshop si está disponible y configurar su motor; el PDF compilado queda en `build/`. También puede abrirse el PDF en un visor externo. No es necesario usar notebooks para compilar una copia que ya contenga las exportaciones.

**Nota histórica de compilación (etapa anterior):** no había una distribución LaTeX instalada; se utilizó un binario temporal oficial Tectonic 0.17.0 para macOS ARM64 en `tectonic`. No es una dependencia permanente del repositorio. La primera ejecución descargó componentes TeX; para recompilar con Tectonic se requiere su caché o acceso de red. Véase la evidencia final de compilación y revisión en `docs/HANDOFF.md`. El PDF se conserva localmente y no se publica.

## Actualizar resultados sin transcripción manual

Con los agregados locales de la auditoría ya ejecutada:

```bash
python scripts/export_cp1_manuscript.py
python scripts/export_cp1_manuscript.py --check
python scripts/validate_manuscript.py
```

El exportador reutiliza JSON agregados, comprueba la huella del microdato cuando está disponible, reconcilia distribuciones y exclusiones y genera las tablas mediante `src/tesis_enasem/manuscript.py`. Las cifras sustantivas del texto se insertan como macros de `tablas/cp1_cifras.tex`. `trazabilidad_cp1.json` registra las huellas de las fuentes y los artefactos. El script no reconstruye la auditoría ni lee filas privadas para tabular. La celda final del notebook 02 también exporta desde sus mismos agregados en memoria.

No editar cifras directamente en tablas generadas. Si cambia una definición, validar primero el análisis, regenerar agregados/exportaciones y revisar la interpretación del capítulo. No atribuir resultados nuevos al commit previo sin documentar la ejecución. Los tests utilizan datos sintéticos y CI comprueba referencias/dependencias del manuscrito sin microdatos; la compilación local y `--check` son verificaciones distintas.

## Referencias verificadas

| Clave BibTeX | Fuente primaria verificada | Uso en el borrador |
| --- | --- | --- |
| `inegi2024enadid` | [INEGI, comunicado 305/24, p. 2](https://www.inegi.org.mx/contenidos/saladeprensa/boletines/2024/ENADID/ENADID2023.pdf) | Cambio de la proporción de 60+ entre 2018 y 2023 |
| `smith1999` | [American Economic Association](https://www.aeaweb.org/articles?id=10.1257/jep.13.2.145) | Motivación de la relación salud-recursos; sin trasladar inferencia causal |
| `ligon2003` | [Oxford, volumen 113(486)](https://academic.oup.com/ej/issue/113/486), [bibliografía del autor](https://are.berkeley.edu/~ligon/papers.html) | Diferencia conceptual entre condición económica y vulnerabilidad; no se implementa su medida |
| `wong2017` | [Artículo original registrado en PubMed](https://pubmed.ncbi.nlm.nih.gov/25626437/) | Diseño y cohorte ENASEM; publicación electrónica 2015, volumen definitivo 2017 |
| `enasem2025simple` | [Documento oficial y apéndice de códigos v2](https://enasem.org/Resources/DATA/Constructed_Imputed/simpleMHAS/ENASEMsimple_Documento_Descriptivo_y_Libro_de_Codigos.pdf) | Archivo 2001–2021, codificaciones y notas del proveedor |
| `udlap2024guia` | [Guía pública UDLAP](https://catarina.udlap.mx/u_dl_a/tales/guias/estudiante/index.html) | Pendiente institucional de formato; confirmar vigencia |

Las referencias motivacionales no sustituyen una revisión de literatura completa ni demuestran novedad del proyecto. Las cifras de CP1 son cálculos propios reconciliados con el archivo local y el diccionario.

## Pendientes vigentes

Revisar con la dirección la contribución empírica y el alcance de la pregunta ya formulada; verificar precisión, fuentes y referencias; decidir si se requieren ponderadores/diseño para afirmaciones nacionales; confirmar título, datos institucionales, resumen y normas UDLAP. Los resultados descriptivos no identifican causalidad, ingreso total ni suficiencia integral. No existe una tarea pendiente de entrenar modelos predictivos de alerta temprana.

## Registro histórico de etapas previas (no describe el estado actual)

Las notas fechadas a continuación se conservan como trazabilidad de versiones anteriores del proyecto. Sus preguntas, rutas `docs/` o `reports/`, referencias a capítulos inexistentes y pendientes predictivos **no sustituyen** el enfoque y las rutas vigentes explicados arriba.

### Complemento pensionario (2026-10-12)

El capítulo 2 incorpora la sección histórica solicitada, con versiones documentales federales y ejemplos locales; el capítulo 3 incorpora inventario, unidades, claves, ocho conceptos y límites; el capítulo 4 contiene el protocolo exploratorio pendiente, no resultados económicos integrados. Fuentes de texto: `capitulos/02_marco_teorico_antecedentes.tex` y `capitulos/03_datos_metodologia.tex`. Los tres cuadros nuevos se generan desde metadatos y catálogo, sin microdatos en LaTeX:

```bash
python scripts/inventory_pension_sources.py
python scripts/export_pension_review.py
python scripts/export_pension_availability.py
python scripts/validate_manuscript.py
python scripts/compile_manuscript.py
```

Solo el primer comando necesita los archivos privados locales. Después de exportar, el manuscrito puede compilarse sin datos ni `reports/`. El catálogo y las matrices están en [docs/pensiones](../resultados/INFORME_GENERAL.md#origen-96509f3d2504). Las fuentes históricas verificables están en el catálogo y BibTeX; no se presupone que cada programa tenga una variable identificable en ENASEM. La plantilla UDLAP, bibliografía ampliada, validación semántica completa, aprobación de figuras y decisiones predictivas siguen pendientes. La ampliación al año 2024 no está aprobada.
## EDA independiente autorizado: primer bloque (12 de octubre de 2026)

El capítulo 3 incorpora `capitulos/03_datos_metodologia.tex`; el capítulo 4 contiene `capitulos/04_analisis_exploratorio_resultados.tex`, con resultados reales de las 91 variables sustantivas/banderas de ENASEMsimple y sus límites. La muestra principal y el cierre CP2 siguen pendientes. K original/imputada/construida y G/J/SA tienen prevalidación; no se presentan como EDA sustantivo concluido.

`python scripts/export_independent_eda.py` regenera cuatro cuadros seleccionados, macros numéricos y dos figuras agregadas en revisión desde `reports/eda_independiente/simple_resultados.json`. Este script no carga ni integra microdatos. Los cuadros son `eda_simple_cobertura.tex`, `eda_simple_patrimonio.tex`, `eda_simple_salud.tex` y `eda_simple_versiones.tex`; las cifras del texto están en `eda_simple_cifras.tex`. Las fichas y distribuciones extensas se conservan en docs/eda y el notebook 03 ejecutado localmente, según [instrucciones de reproducción](../resultados/INFORME_GENERAL.md#origen-f7fba3ac2814). La carpeta manuscrito contiene todas las dependencias de compilación y no necesita acceso a data/ ni reports/ para generar el PDF.

## Revisión B01 y continuación K 2021

La revisión incorpora comparaciones conjuntas de las 91 variables, universos del indicador (534 reconstruidos/12 ND) e investigación n_res con causa abierta. `scripts/review_b01.py` reutiliza agregados; `scripts/export_independent_eda.py` genera cuadros/macros/figuras. B02a describe 338 variables independientes de 2021 y 59 cotejos derivados/imputados; `scripts/export_k2021_eda.py` genera las tablas, cifras y figura seleccionadas desde los mismos agregados del notebook. La selección editorial no excluye variables del EDA ni aprueba las figuras.

Los salarios conservan periodicidad pendiente; los demás montos distinguen mensual/total/stock. La ventana anual de recepción no impone una unidad anual. Las fuentes no se suman ni se integran definitivamente. El resto de K y rondas permanece pendiente; ver docs/eda. CP1/introducción y decisiones abiertas se conservan.

## Integración provisional y primer EDA conjunto

La autorización nueva permite integrar ahora, sin esperar a terminar el EDA independiente. Capítulos 3–4: integración, cobertura, titularidad conservadora 2021 y J01; cuatro tablas/cifras y dos figuras BrBG desde agregados, con homologación global pendiente. Regenerar con `python scripts/export_integration_manuscript.py` después de constructor/J01; comandos y notebook 05b en docs/integracion/README.md. El manuscrito compila sin base privada; las figuras siguen en borradores y normas UDLAP pendientes.


## Recuperación del original y catálogo nacional (12 de octubre de 2026)

La [matriz de conciliación](../resultados/INFORME_GENERAL.md#origen-eece14d800ac) documenta 26 correspondencias con el PDF original, conserva la pregunta y deja explícitas las diferencias de cuartil/quintil, hipótesis y panel. Los módulos `02_recuperacion_conceptual.tex`, `02_catalogo_nacional.tex` y `03_recuperacion_metodologica.tex` están incluidos en los capítulos existentes. Se excluye el resumen ajeno sobre CVA. La portada recupera el nombre de la autora; normas UDLAP y estructura definitiva pendientes.

`estilo_cuadros.tex` establece **Cuadro capítulo.número**, título superior centrado, reglas discretas, encabezados en negritas y notas/fuentes. El exportador compartido divide encabezados extensos y mantiene las cifras. Después de exportadores antiguos ejecutar `scripts/reconcile_manuscript.py`; adapta encabezados existentes sin modificar celdas numéricas. La selección de figuras sigue en revisión.

El [catálogo nacional](../resultados/INFORME_GENERAL.md#origen-d94b156198db) aporta dos cuadros desde inventarios y contratos documentados: cobertura territorial y especificidad de las seis rondas. No identifica beneficiarios ni modifica el EDA. Las 46,495 filas son ocurrencias de intervenciones por territorio/periodo, no programas únicos. Las versiones normativas anteriores permanecen preservadas.

```bash
python scripts/export_national_context.py
python scripts/build_documentary_notebook.py --execute
python scripts/reconcile_manuscript.py
python scripts/export_cp1_manuscript.py --check
python scripts/validate_manuscript.py
python scripts/compile_manuscript.py --engine tectonic
python scripts/review_documentary_artifacts.py
```

Los comandos de esta etapa reutilizan resultados anteriores. Para restaurar las extracciones documentales usar `build_national_catalog.py --download`; no se necesita repetir las 17 uniones. Abrir el notebook 05 eejecutado desde VS Code y el PDF local; consultar la [revisión académica](../resultados/INFORME_GENERAL.md#origen-459ef58882c6) para los límites y decisiones abiertas. El manuscrito compila desde exportaciones agregadas sin microdatos.

Cada capítulo y cada anexo tiene un único archivo completo; los módulos anteriores se incorporaron sin reescritura. No generar archivos independientes por sección.

## Ventanas y compilación en GitHub — 23/10/2026

El capítulo 3 incluye una matriz de los cinco intervalos y ambas vías en `tablas/tesis_comparabilidad_ventanas.tex`. Explica diferencias de preguntas, instituciones, captura y montos, con páginas de las fuentes oficiales. La restricción A 2001–2003 se declara provisional. Los capítulos 4–5 distinguen otra vía basal y coexistencia al destino; las seis rondas descriptivas permanecen.

El flujo `Compilar y verificar tesis` valida las fuentes, compila con LaTeX/BibTeX y verifica texto, referencias y límites de página. Guarda el PDF, `build/validacion_pdf.json` e imágenes en `build/revision/`; estos controles requieren inspección visual adicional. No usa microdatos, no exporta estimaciones nuevas y no valida por sí solo los análisis estadísticos privados de la etapa 09 (Informe 10.8). Los registros históricos de compilación anteriores no describen el PDF de este flujo.


**Verificación del PDF — 23/10/2026.** La compilación en GitHub del commit fuente `d1180574d685e77103f77a4b5d3d1a64fb7e2f8c` produjo un PDF de 75 páginas. El cuadro 3.1 contiene las cinco ventanas y ambas vías en páginas impresas 20–21 (PDF 27–28). Pasaron validación de fuentes, pruebas en Python 3.11/3.12, controles de citas/referencias y límites de página; no se registraron desbordamientos horizontales. Se revisaron visualmente las cuatro láminas de detalle y los siete contactos de todo el documento. Véase `manuscrito/build/validacion_pdf.json` para huella y alcance. Esta verificación editorial no certifica datos de portada pendientes ni completa los cruces socioeconómicos no disponibles en el repositorio público. No se recalcularon estimaciones ni se publicaron archivos privados.











<!-- BEGIN estado09 -->
## Investigación estadística local completada — etapa 09

El contraste central reutiliza379 fuentes verificadas y reproduce la auditoría 08. Incorpora las seis rondas, seis combinaciones vía/ventana, situación basal, probabilidad/composición, perfiles patrimoniales, montos posteriores, incertidumbre y sensibilidad. Véase Informe General10.8 y capítulos 3–5. Código: `central_analysis.py`, `central_supplement.py`; reproducción `python scripts/run_central_analysis.py` y exportación `python scripts/export_central_analysis.py`. Los agregados locales permanecen en `data/interim/incorporacion_proteccion_propia/`, excluidos de Git. No se ha hecho commit ni push. La pobreza, necesidad integral, causalidad, inferencia nacional y cinco ajustes monetarios sin soporte permanecen fuera de conclusión. La tesis compilada tiene 88 páginas y el Informe General 183; se revisaron visualmente las secciones modificadas y seis páginas representativas del informe. Pasaron 176 pruebas y 166 comprobaciones numéricas independientes. Registro de fuentes y revisión: `manuscrito/build/validacion_pdf.json` y agregados09; cifras antiguas de páginas en este archivo describen etapas históricas.
<!-- END estado09 -->







<!-- validacion10 -->
Cierre local de verificación: tesis corregida de **94 páginas** e Informe General de **199 páginas**, 135 cuadros y 50 figuras. Pasan **197 pruebas**, 166 comprobaciones numéricas independientes y 336 embudos; 379 fuentes estadísticas permanecen intactas. Se revisaron visualmente las secciones modificadas. La propuesta autocontenida compila con texto idéntico al manuscrito corregido. Reproducir con `scripts/validate_statistical_quality.py`, `scripts/verify_compiled_thesis.py` y `scripts/prepare_quality_release.py`; este último no publica ni altera Git. La revisión visual queda registrada en `manuscrito/build/validacion_pdf.json`.



<!-- BEGIN estado10 -->
## Auditoría estadística y divulgación — etapa 10

El Informe General10.9 reúne el censo de 126 cuadros/50 figuras originales, la trazabilidad de muestras, las reformulaciones y las limitaciones. Se preserva la versión privada original de 88 páginas y sus resultados; la edición académica actual es la versión pública corregida, con validación separada. El núcleo de incorporación observado se conserva; algunos gradientes y contrastes institucionales se matizan por soporte/estabilidad. Véanse `diccionarios/politica_calidad_divulgacion.json`, `diccionarios/auditoria_calidad_muestras.json` y `python scripts/export_quality_public.py`. Ningún umbral acredita inferencia nacional. No se hizo commit ni push. El historial público previo contiene un detalle T8 de un grupo pequeño: no se ha saneado ni se reescribirá sin autorización. La propuesta local de archivos públicos excluye los originales y agregados privados, así como artefactos históricos no revisados.
<!-- END estado10 -->

<!-- sincronizacion_local_unica -->
## Sincronización del mismo repositorio

Se mantiene únicamente `Andrea-HH/tesis`, con los archivos públicos y privados en sus ubicaciones habituales. `.gitignore` permite solo las392 rutas revisadas de `diccionarios/cierre_publicacion.json`; el resto permanece local. Los archivos excluidos que estaban rastreados se retiran únicamente del índice, sin borrarlos del disco. La versión vigente es el PDF de94 páginas; no se recalculó ni reconstruyó para preparar Git.

Para preparar la selección revisada: `python scripts/prepare_quality_release.py --stage`. Para comprobar lo preparado: `python scripts/validate_quality_release.py --index`. Ninguno hace commit ni push. Los cambios de archivos ya autorizados pueden sincronizarse normalmente; una ruta nueva requiere revisión y actualización del manifiesto y las excepciones de `.gitignore`. No usar incorporación forzada para eludir esta selección. Los notebooks publicables tienen outputs vacíos; las versiones originales siguen privadas.

Una actualización normal puede corregir el árbol vigente de GitHub sin reproducir las estadísticas retiradas. No elimina la mediana patrimonial T8 de un grupo de cinco personas del historial anterior. Ese riesgo sigue identificado y no se autoriza ni se realiza reescritura del historial o force push.
