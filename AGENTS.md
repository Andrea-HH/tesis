# AGENTS.md — instrucciones persistentes para agentes de desarrollo e investigación

## Antes de cualquier cambio
Lee `README.md`, `docs/HANDOFF.md`, `docs/ROADMAP.md`, `docs/FUENTES.md`,
`docs/DECISIONES.md`, `docs/RESULTADOS.md` y `docs/EXPERIMENTOS.md`.

## Propósito
Desarrollar y evaluar un modelo longitudinal **prospectivo** de alerta temprana de
vulnerabilidad económica de adultos mayores en México (ENASEM 2001–2021),
comparando un baseline económico sólido contra señales de salud física/mental,
cognición, funcionalidad y participación.

## Restricciones metodológicas no negociables
1. Usar libro de códigos de ENASEMsimple como fuente para nombres, cobertura y codificaciones.
2. Mantener distinción entre ronda nominal (`ronda`), año de onda y entrevista efectiva (`a_o_ent`).
3. Prevenir fuga temporal: variables en t no pueden anticipar etiquetas usando datos t+k.
4. Panel completo de seis entrevistas directas **no** es representativo por defecto;
   evaluar attrición y sesgo por supervivencia con datos no balanceados.
5. Auditar `.f`, `.p`, `.w` y otros perdidos especiales antes de convertirlos a NaN.
6. Patrimonio (`imp_neto`) no es ingreso: validar cambio de precios entre olas y
   cortes estimados con la población y momento correctos.
7. Para comparar modelos: mismos IDs test, mismos splits, mismos horizontes,
   misma imputación fit solo en train, intervalos por remuestreo persona.
8. No llamar "predicción temprana" a una asociación transversal y no afirmar
   causalidad sin diseño causal.
9. No inventar métricas/resultados: apuntar hipótesis en DECISIONES, hallazgos
   medidos en RESULTADOS y configuración en EXPERIMENTOS.
10. No subir ningún `.dta`, identificador individual, `.csv`, parquet ni secreto
    a un repositorio público; dataset solo en `data/raw/` ignorado.

## Normas de ingeniería
- Python >=3.11, funciones type-hinted y documentadas, nombres snake_case.
- Notebooks `notebooks/` explican objetivo→método→resultado→interpretación.
- Lógica reusable en `src/tesis_enasem/`; añade tests a `tests/`.
- Antes de PR: `python -m pytest -q` y `python scripts/validate_notebooks.py`.
- CI sin datos privados: tests sintéticos; notebooks no ejecutados en CI.
- Experimentos: ID `EXP-###`, configuración, commit y bitácora; jamás sobrescribir.
- Las métricas reportadas necesitan muestra, horizonte, definición y limitaciones.
- Registro de progreso: cada checkpoint en `docs/ROADMAP.md` solo si pasó aceptación.

## Handoff rápido
`docs/HANDOFF.md`. CP0 verificado: instalación editable, 9 pruebas sintéticas,
13 notebooks con esquema válido y CI del commit inicial aprobado en GitHub.
Usa el checkout existente; las tareas cloud están aisladas y no necesitan
worktrees salvo solicitud explícita. No confundir CP0 con experimentos ejecutados.

## Protocolo operativo por sesión (VS Code o Cloud)
1. Identificar rama, último commit y archivos modificados antes de tocar nada; no sobrescribir trabajo ajeno.
2. Leer los documentos indicados al inicio y contrastar la petición con el checkpoint abierto.
3. Presentar un plan breve: archivos a modificar, riesgos estadísticos, pruebas y criterio de término.
4. Separar código reusable (src/), demostración e interpretación (notebooks/), pruebas (tests/) y evidencia (docs/).
5. Ejecutar las pruebas relevantes y documentar los comandos y resultados reales; si una prueba no corre, dejarlo escrito.
6. Actualizar HANDOFF, ROADMAP y RESULTADOS cuando corresponda; marcar pendientes, decisiones provisionales y bloqueos.
7. Informar cambios en archivos, tests, commit/rama y próximos pasos. Preferir rama de feature y PR; nunca force-push.

## Siguiente entrega: CP1 — integridad y población analítica
**Meta:** definir un universo longitudinal auditable *antes* de construir etiquetas o modelos.
- Examinar identificadores `cunicah` + `np`, `ronda`, `a_o_ent`, `tipent`, `edad` y `fallecido`; comprobar unicidad persona-ronda.
- Contabilizar entrevistados por ronda y por tipo (directa, sustituto, sobre fallecido), diferencias de cobertura y transición entre olas; respetar intervalos de tiempo desiguales.
- Auditar faltantes especiales de Stata antes de la conversión a NaN; distinguir pregunta no realizada, entrevista por sustituto y fallecimiento.
- Comparar elegibilidad por edad: 60+ en cada visita versus entrada a 60+; documentar cómo cambian IDs y observaciones.
- Conservar el panel **no balanceado** como referencia analítica candidata; usar panel completo de seis rondas solo como sensibilidad hasta que se apruebe el estimando.
- Documentar denominadores (personas únicas vs personas-ronda), exclusiones secuenciales y conteos con y sin pesos cuando aplique; no tratar ponderadores transversales como longitudinales.
- Para la auditoría usar datos locales únicamente; el CI y los tests deben funcionar con datos sintéticos. No almacenar en GitHub microdatos ni IDs individuales.

**Entregables verificables:** `notebooks/02_construccion_muestra.ipynb` legible y reproducible, funciones testeadas en `src/tesis_enasem/panel.py` (o módulos existentes), tablas agregadas de flujo, `docs/AUDITORIA_INICIAL.md` ampliada, decisiones provisionales en `docs/DECISIONES.md` y evidencia de aceptación en `docs/ROADMAP.md`.

**Criterio de aceptación:** reconciliación explícita de conteos por onda y exclusión, pruebas de duplicados y faltantes, justificación de población de referencia y advertencia documentada sobre atrición. No avanzar automáticamente a CP2/CP3 sin revisión metodológica.

## Formato de handoff al cerrar una tarea
- Objetivo / checkpoint / estado (completado, parcial o bloqueado).
- Archivos y funciones editados; comandos ejecutados; resultados de tests.
- Métricas empíricas: solo si fueron calculadas; población, periodo, denominador y supuestos.
- Decisiones nuevas (aprobadas o provisionales) y riesgos metodológicos.
- Próxima acción reproducible y pregunta pendiente para revisión humana.
