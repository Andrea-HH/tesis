# AGENTS.md — organización permanente de la tesis ENASEM

## Antes de trabajar
Lee README.md, resultados/INFORME_GENERAL.md y los diccionarios pertinentes.
Consulta investigacion/notas/historial_metodologico.json solo como evidencia histórica;
las propuestas predictivas anteriores no gobiernan la etapa vigente.
Identifica rama, commit y cambios preparados/sin preparar; no sobrescribas trabajo ajeno.
Usa el checkout existente. No hagas commit, push, merge, reset, restore ni cambies la
selección preparada sin autorización explícita. No restaures as.py automáticamente.

## Objetivo vigente y restricciones científicas
Explorar ENASEM 2001–2021 con pensiones, titularidad, instituciones y apoyos como eje.
No adoptar pregunta definitiva, hipótesis principal/causal, outcome, vulnerabilidad
ni modelo predictivo. Conservar resultados e interpretaciones previos válidos.
- CP1: universo completo; maestro 99,676 personas-ronda/27,171 personas intacto.
- EDA pensionario: 60+ por visita, PopulationSpec configurable; 56,004/18,754.
  EDA independiente mantiene el universo original de cada fuente. No sumar universos.
- ID exactamente cunicah:np, formatos conservados; id+ronda único, ronda != a_o_ent.
- LEFT JOIN, claves verificadas y puentes 2001/2003; nunca muchos-a-muchos.
- Hogar no es persona; pensión propia != cónyuge; viudez pertenece al beneficiario.
- K no implica contributividad; A no implica pensión no contributiva. ND != negativa.
- Preservar tags Stata, NR/NS específicos y banderas; no completar con cero ni corregir
  J1/2001, punteros discordantes, 33 firmas 2015 o anomalías CP1 automáticamente.
- Slots != número declarado; institución múltiple no distribuye ni replica monto.
  Original/imputado/construido no se suman como ingresos independientes.
- Patrimonio compartido es stock, no ingreso individual; precios/periodicidad pendientes.
- Tasas de recepción != composición. N total, elegible, válido/ND y personas distintos.
- Pesos/diseño no validados: describir muestra; no usar pesos transversales en trayectorias.
- Seguimiento de mismos IDs; muerte, ausencia, reaparición y desconocido separados.
  Rupturas K2003–2012/K2015–2018 y A2001–2003/A2018–2021 no son altas/bajas homologadas.
- Sin causalidad ni significancia no probada. Futuro modelado solo con autorización,
  sin fuga temporal, mismos splits/horizontes y ajuste de imputación solo en train.

## Ubicaciones únicas obligatorias
| Producto | Ubicación |
|---|---|
| Fuente original inalterada | data/raw/ |
| Puente, extracción o agregado intermedio | data/interim/ |
| Base analítica y manifiesto versionado | data/processed/ |
| Definición, códigos, titularidad u homologación | diccionarios/ |
| Integración y sus validaciones | notebooks/01_INTEGRACION.ipynb |
| EDA y trayectorias previamente consolidados | notebooks/02_EDA_COMPLETO.ipynb |
| Nuevos análisis independientes justificados | notebooks/NN_NOMBRE_DESCRIPTIVO.ipynb |
| Informe, tabla e interpretación académica | resultados/INFORME_GENERAL.md |
| Figura académica BrBG/BrBG_r | resultados/figuras/ |
| Fuentes, literatura y notas documentales | investigacion/ |
| Única bibliografía activa | investigacion/referencias.bib |
| Redacción académica | manuscrito/capitulos/ |
| Cuadro LaTeX exportado | manuscrito/tablas/ |
| PDF y auxiliares locales | manuscrito/build/ |
| Lógica reusable / ejecución / tests | src/tesis_enasem/ / scripts/ / tests/ |

Antes de crear un archivo, busca una ubicación y producto existente para actualizar.
No crear docs/, reports/ ni informes independientes por variable, ronda o notebook.
Los nuevos análisis que justifiquen un notebook independiente se crean directamente
en notebooks/, con numeración consecutiva y nombre descriptivo, sin subcarpetas.
No fusionarlos automáticamente con 01_INTEGRACION ni 02_EDA_COMPLETO: estos conservan
los trabajos consolidados y se actualizan cuando corresponda específicamente a ellos.
No duplicar análisis existentes; reutilizar funciones de src/. Cada notebook incluye
objetivo, datos/variables, metodología, código reproducible, tablas, gráficas,
interpretaciones y limitaciones. No crear notebooks de ejemplo sin solicitud.
Rutas mediante tesis_enasem.project_paths; los alias históricos son compatibilidad,
no autorización para recrear carpetas. No escribir informes académicos en caches.

## Reproducibilidad y escritura
Python >=3.11, nombres snake_case, funciones documentadas y con tipos.
Reutilizar bases y agregados verificados; no repetir 17 uniones, titularidad o EDA
por organizar archivos. Scripts coordinan; src calcula; notebooks explican.
Cada resultado incluye pregunta, variables, universo, denominadores, tabla, figura,
interpretación específica, límites y estado. Tres variables simultáneas en trivariados.
Actualizar el informe acumulativo por sección, sin reescribir resultados únicos.
Todos los notebooks contribuyen a resultados/INFORME_GENERAL.md: incorporar tablas,
figuras e interpretaciones, notebook de procedencia, población, denominadores,
limitaciones y estado validado/provisional. El informe debe ser comprensible sin
ejecutar notebooks; no sustituir resultados por una lista de enlaces ni duplicarlos.
Actualizar a la vez el capítulo LaTeX pertinente; no copiar todo el informe a la tesis.
Mantener índice académico, citas, etiquetas, Cuadro por capítulo, título superior,
reglas horizontales y notas/fuentes. Normas UDLAP y aprobación editorial pendientes.
Exportar cifras desde agregados; jamás transcribir cientos de números manualmente.
Matrices de cumplimiento y validaciones se conservan como datos estructurados;
no confundir ejecución técnica con cierre académico.

## Validación y privacidad
Antes de entrega: python -m pytest -q; python scripts/validate_notebooks.py;
python scripts/validate_manuscript.py. Migración: python scripts/validate_migration.py.
Ejecutar los dos notebooks sin recalcular, compilar y revisar el PDF cuando exista motor.
CI usa tests sintéticos y no necesita datos privados. No compilar globalmente módulos
históricos defectuosos ni afirmar que se corrigieron sin comprobarlo.
Repositorios privados no autorizan transferencia. Verificar visibilidad, condiciones,
permisos, tamaños/LFS, secretos y lista exacta antes de cualquier subida de microdatos.
Repositorio público por decisión de la autora: publicar solo código, notas propias y
agregados evaluados. Mantener data/ privada/ignorada; no redistribuir microdatos,
documentos de terceros sin permiso ni celdas pequeñas sin evaluación de divulgación.
No enviar credenciales, identificadores individuales ni documentos de terceros no autorizados.

## Estado de migración y cierre de sesión
Los históricos reemplazados del inventario auditado se retiraron por autorización
expresa de la autora; se conservan las excepciones y el respaldo externo verificado.
Todo retiro adicional exige autorización, inventario y equivalencia comprobada.
No modificar los históricos para ocultar información ni actualizar el índice Git solo
por mover archivos. Resumir cambios/validaciones/pendientes en README e informe;
evidencia técnica en data/interim/migracion_proyecto.json, sin nuevos informes paralelos.


## Prioridad local vigente (13/10/2026)
La autora autorizó la limpieza física conforme al manifiesto auditado y sus
excepciones. No recrear docs/ ni reports/. Conservar los once antecedentes en
investigacion/notas/notebooks_historicos/, las bases completas y un único informe
y notebooks de trabajo independientes en una sola carpeta. GitHub está en pausa: no preparar ediciones
públicas ni modificar el índice durante la organización local. Los respaldos
verificados son históricos externos, nunca otro flujo académico activo.

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
