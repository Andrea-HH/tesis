# Roadmap — checkpoints y criterios de aceptación

Estado al 2026-10-11. Un [x] implica artefacto realizado/verificado; no equivale a conclusión científica.

## CP0 — Infraestructura reproducible
- [x] Estructura y paquete Python instalable preparado localmente.
- [x] Archivo AGENTS.md, handoff, protocolo experimental, gitignore y tests.
- [x] Notebooks narrativos para todas las fases; 01, 02, 03 y 05 con código inicial ejecutable.
- [x] Tests locales de funcionalidad y formato de notebooks.
- [x] Subida del commit inicial `adfe426` a GitHub y CI remoto aprobado (Python 3.11 y 3.12).
- [x] CP0 completado: evidencia en [CP0_VERIFICACION.md](CP0_VERIFICACION.md).
**Aceptación:** commit y CI verde en `main`.

## CP1 — Integridad de datos y muestra
- [x] Conteos ejecutados por ronda/persona/tipo, faltantes de 119 variables y anomalías documentadas.
- [x] Once alternativas y composición comparadas; reglas explícitas de edad y balance.
- [x] Flujo reproducible, presencia, estados de entrevista y ausencia sin causa asumida.
- [ ] Aprobación del estimando/población, reglas de anomalías y ponderación; cierre metodológico CP1.
**Evidencia técnica:** CP1_RESULTADOS.md, notebook 02 ejecutado localmente, 16 tests y 13 notebooks válidos. CP1 no se declara completo mientras esté pendiente la aceptación humana.
**Aceptación:** tabla auditable y definición del estimando. Exigir además seis fichas
por ronda con N de registros y personas, `tipent` desglosado, grupos de edad,
fechas efectivas, excluidos, patrones de participación, transición y faltantes.
Protocolo: [PLAN_EDA_RONDAS_Y_PENSIONES.md](PLAN_EDA_RONDAS_Y_PENSIONES.md).

## CP2 — EDA univariado y longitudinal
- [ ] Comparar distribuciones por año/ronda con leyendas etiquetadas, BrBG y conteos.
- [ ] Gráficas de patrimonio e IMC por año; subgrupos; Spearman/Cramér V por ronda.
- [ ] Revisar cobertura por variable/ola, panel desbalanceado, atrición.
**Aceptación:** resumen con figuras, tablas y al menos tres hipótesis falsables.
No limitar el EDA a un gráfico agregado: cada variable y dimensión debe tener
resumen y distribución para cada ronda disponible, más comparación conjunta,
con N y denominador explícitos. Protocolo: [PLAN_EDA_RONDAS_Y_PENSIONES.md](PLAN_EDA_RONDAS_Y_PENSIONES.md).

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

## Integración futura — Pensiones en ENASEM completo (no iniciada)
- [ ] Localizar módulos, archivos y diccionarios originales por ronda.
- [ ] Auditar claves, cardinalidad, cobertura y tasas de emparejamiento por ola.
- [ ] Armonizar conceptos de pensión/ingresos de retiro, periodicidad, unidades, faltantes y cambios de cuestionario.
- [ ] Validar impacto en análisis sin atribuir automáticamente flujos del hogar a una persona.
**No modificar CP3 ni completar este apartado antes de tener los archivos y una decisión aprobada.**
Ver [PLAN_EDA_RONDAS_Y_PENSIONES.md](PLAN_EDA_RONDAS_Y_PENSIONES.md).
