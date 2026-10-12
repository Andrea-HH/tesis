# Bitácora de resultados — NO confundir planes con hallazgos

## CP0 completado (2026-10-09)
Instalación editable verificada, 9 pruebas aprobadas, 13 notebooks válidos y CI del commit inicial aprobado. Evidencia y límites: [CP0_VERIFICACION.md](CP0_VERIFICACION.md). No se ejecutaron experimentos con microdatos en esta verificación.

## Evidencia del estado técnico (2026-10-09)
- Se preparó arquitectura del paquete y plantillas de notebooks.
- Se verifican las pruebas por `pytest` y las notebooks por `scripts/validate_notebooks.py` en el entorno local; CI del commit inicial verificado en GitHub.
- **No hay resultados predictivos ni conclusiones empíricas registradas** de este repositorio.

## Auditoría real de la base ENASEMsimple (datos suministrados, sin publicar)
- **99,676 registros** de **27,171 personas** en seis rondas; 0 duplicados persona-ronda.
- Con entrevistas directas, edad ≥60 en cada ola: **50,841 registros** de **18,158 personas**.
- El panel estricto de seis olas bajo ese filtro contiene **964 personas** (subgrupo seleccionado, NO muestra principal por defecto).
- La desagregación y las advertencias están en `docs/AUDITORIA_INICIAL.md`.

## Plantilla EXP-NNN
- Fecha/commit:
- Notebook y configuración:
- Muestra (IDs, rondas, criterios):
- Target y horizonte en años:
- Pesos, split, imputación:
- N del test, prevalencia:
- Métrica con IC:
- Δ vs baseline con IC:
- Interpretación y límites:
- Archivo reproducible/figuras:
- Decisión siguiente:

## CP1 ejecutado localmente — 2026-10-11

**Estado: implementación y auditoría ejecutadas; aceptación metodológica pendiente.**
Archivo original local, seis rondas nominales 2001–2021, todas las entrevistas: 99,676 registros persona-ronda, 27,171 personas y 119 variables. Cero claves faltantes y duplicados persona-ronda. Los totales y cinco categorías de entrevista de cada ronda coinciden con el cuadro 1/apéndice del libro ENASEMsimple v2 (enero 2025).

La población directa con edad ≥60 por visita contiene 50,841 registros de 18,158 personas. Hay 6,305 personas presentes en seis rondas (cualquier entrevista/edad), 3,893 con seis directas y 964 con seis directas y 60+ en cada visita. No son estimaciones ponderadas ni una población representativa por defecto.

Se calcularon cobertura y códigos especiales de las 119 variables por ronda, demografía, edad, años efectivos, factores individuales/de hogar, exclusiones, once alternativas de muestra, composición por alternativa-ronda, patrones, intersecciones, transiciones, reapariciones y perfiles en t según observación en t+1. Se generaron siete figuras BrBG. No se construyeron etiquetas ni modelos.

**Hallazgos que requieren revisión:** 3 registros posteriores a un fallecimiento registrado (2 directos y 1 sobre fallecido), 1 persona con fallecimiento repetido, 1 con sexo válido inconsistente y 226 pares con edad decreciente. Se conservan los originales. Los pesos presentan ceros y valores positivos en entrevistas sobre fallecidos; no se aplicó ponderación automática.

La cohorte de seis directas 60+ tiene 581 mujeres/964 (60.27%) en cada ronda; la muestra directa 60+ abierta registra 3,667/6,812 mujeres (53.83%) en 2001 y 5,252/9,424 (55.73%) en 2021. La restricción de continuidad cambia la composición observada; no demuestra por sí sola la magnitud del sesgo poblacional.

Evidencia académica, seis fichas y denominadores: [CP1_RESULTADOS.md](CP1_RESULTADOS.md). Reproducción: `/opt/miniconda3/envs/myenv/bin/python scripts/run_cp1.py`; notebook fuente 02 y ejecutado local `reports/notebooks/02_construccion_muestra_ejecutado.ipynb`. Los agregados JSON y figuras están en reports/ ignorado. El diagnóstico patrimonial preliminar de 31,133 pares no fue reproducido ni validado en CP1 y no se usa para aceptar una muestra.
