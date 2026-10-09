# Roadmap — checkpoints y criterios de aceptación

Estado al 2026-10-09. Un [x] implica artefacto realizado/verificado; no equivale a conclusión científica.

## CP0 — Infraestructura reproducible
- [x] Estructura y paquete Python instalable preparado localmente.
- [x] Archivo AGENTS.md, handoff, protocolo experimental, gitignore y tests.
- [x] Notebooks narrativos para todas las fases; 01, 02, 03 y 05 con código inicial ejecutable.
- [x] Tests locales de funcionalidad y formato de notebooks.
- [ ] Subida a GitHub y verificación CI remota (bloqueo 403 por permisos del conector).
**Aceptación:** commit y CI verde en `main`.

## CP1 — Integridad de datos y muestra
- [ ] Conteos por ronda/persona/tipo de entrevista; discrepancias, duplicados, valores .f/.p/.w.
- [ ] Reglas explícitas de edad de entrada, grupos de comparación y panel no balanceado.
- [ ] Flujo reproducible de muestra (directas/sustituto/muerte/no respuesta).
**Aceptación:** tabla auditable y definición del estimando.

## CP2 — EDA univariado y longitudinal
- [ ] Comparar distribuciones por año/ronda con leyendas etiquetadas, BrBG y conteos.
- [ ] Gráficas de patrimonio e IMC por año; subgrupos; Spearman/Cramér V por ronda.
- [ ] Revisar cobertura por variable/ola, panel desbalanceado, atrición.
**Aceptación:** resumen con figuras, tablas y al menos tres hipótesis falsables.

## CP3 — Outcome económico
- [ ] Definir Q1 ponderado o no, población de referencia, transición futura y sensibilidad.
- [ ] Deflactación y conceptos de patrimonio/ingreso distinguidos.
**Aceptación:** función y pruebas de target sin leakage.

## CP4 — Baseline
- [ ] Dataset t→t+k sin cruces indebidos; calendario en años irregulares.
- [ ] Evaluación fuera de muestra, AUC/PR-AUC/Brier/calibración y grupos de riesgo.
**Aceptación:** métricas, ICs, error de alerta e informe EXP-001.

## CP5 — Incrementos de dimensiones
- [ ] Salud física, mental, cognición, funcionalidad, participación y modelo completo.
- [ ] Misma muestra/particiones, ablaciones e IC para Δ métricas.
**Aceptación:** demostración de ganancia incremental o evidencia de su ausencia.

## CP6 — Anticipación
- [ ] Resultados por cada par de años/rondas; horizontes explícitos en años.
**Aceptación:** gráfica desempeño vs años y limitaciones.

## CP7 — Atrición
- [ ] Separar muerte/sustitución/no respuesta y comparar métodos IPCW u otros.
**Aceptación:** magnitud y dirección de cambios comparables.

## CP8 — Heterogeneidad
- [ ] Edad, sexo, educación, estado conyugal y tamaño de localidad.
**Aceptación:** desempeño por subgrupos con incertidumbre y advertencias.

## CP9 — Robustez/conclusión
- [ ] Sensibilidad a target, pesos, muestra, modelos, imputación, especificaciones.
- [ ] Selección final y documentación de resultados/limitaciones.
**Aceptación:** pipeline completo, resultados repetibles y capítulo de tesis.
