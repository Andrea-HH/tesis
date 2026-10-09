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
