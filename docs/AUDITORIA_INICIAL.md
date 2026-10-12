## CP1 ejecutado localmente — 2026-10-11

**Estado: implementación y auditoría ejecutadas; aceptación metodológica pendiente.**
Archivo original local, seis rondas nominales 2001–2021, todas las entrevistas: 99,676 registros persona-ronda, 27,171 personas y 119 variables. Cero claves faltantes y duplicados persona-ronda. Los totales y cinco categorías de entrevista de cada ronda coinciden con el cuadro 1/apéndice del libro ENASEMsimple v2 (enero 2025).

La población directa con edad ≥60 por visita contiene 50,841 registros de 18,158 personas. Hay 6,305 personas presentes en seis rondas (cualquier entrevista/edad), 3,893 con seis directas y 964 con seis directas y 60+ en cada visita. No son estimaciones ponderadas ni una población representativa por defecto.

Se calcularon cobertura y códigos especiales de las 119 variables por ronda, demografía, edad, años efectivos, factores individuales/de hogar, exclusiones, once alternativas de muestra, composición por alternativa-ronda, patrones, intersecciones, transiciones, reapariciones y perfiles en t según observación en t+1. Se generaron siete figuras BrBG. No se construyeron etiquetas ni modelos.

**Hallazgos que requieren revisión:** 3 registros posteriores a un fallecimiento registrado (2 directos y 1 sobre fallecido), 1 persona con fallecimiento repetido, 1 con sexo válido inconsistente y 226 pares con edad decreciente. Se conservan los originales. Los pesos presentan ceros y valores positivos en entrevistas sobre fallecidos; no se aplicó ponderación automática.

La cohorte de seis directas 60+ tiene 581 mujeres/964 (60.27%) en cada ronda; la muestra directa 60+ abierta registra 3,667/6,812 mujeres (53.83%) en 2001 y 5,252/9,424 (55.73%) en 2021. La restricción de continuidad cambia la composición observada; no demuestra por sí sola la magnitud del sesgo poblacional.

Evidencia académica, seis fichas y denominadores: [CP1_RESULTADOS.md](CP1_RESULTADOS.md). Reproducción: `/opt/miniconda3/envs/myenv/bin/python scripts/run_cp1.py`; notebook fuente 02 y ejecutado local `reports/notebooks/02_construccion_muestra_ejecutado.ipynb`. Los agregados JSON y figuras están en reports/ ignorado. El diagnóstico patrimonial preliminar de 31,133 pares no fue reproducido ni validado en CP1 y no se usa para aceptar una muestra.

---

## Registro histórico de auditoría preliminar (2026-10-09)

Los conteos patrimoniales de esta sección son históricos y no constituyen aceptación de CP3. Para reproducir CP1 utilizar únicamente el script y notebook 02 indicados arriba; no ejecutar notebook 05 en esta fase.

# Auditoría preliminar — base ENASEMsimple suministrada

**Fecha de comprobación:** 2026-10-09  
**Fuente:** archivo `simpleMHAS.dta` aportado por la autora, analizado localmente sin subir microdatos.  
**Estado:** resultados de auditoría estructural, **no** resultados de un modelo predictivo ni estimaciones representativas.

## Conteos comprobados

| Criterio | Resultado |
|---|---:|
| Registros persona-ronda originales, todas las entrevistas | 99,676 |
| Identificadores únicos `cunicah` + `np` | 27,171 |
| Duplicados por par `id`, `ronda` en la base original | 0 |
| Registros directos (tipent 1/2) con edad ≥60 en **cada ronda observada** | 50,841 |
| Personas distintas en el filtro anterior | 18,158 |
| Personas que tienen las seis rondas directas con edad ≥60 en **cada** ronda | 964 |
| Pares con un estado Q1 futuro no nulo en ronda siguiente observada (diagnóstico provisional) | 31,133 |

### Conteos persona-ronda del filtro directo edad ≥60

| Ola nominal | Registros |
|---:|---:|
| 2001 | 6,812 |
| 2003 | 6,970 |
| 2012 | 8,888 |
| 2015 | 9,640 |
| 2018 | 9,107 |
| 2021 | 9,424 |

## Interpretación y cautelas

- Que solo **964** personas cumplan el panel completo bajo estos filtros *no* demuestra attrición total de la encuesta. Se trata de una definición estricta que exige edad ≥60 en TODAS las olas observadas, entrevistas directas en las seis y presencia en todas las olas; excluye a quienes cumplen 60 más tarde y quienes pasan a entrevista por sustituto/fallecen.
- Un análisis longitudinal abierto debe definir la **edad de elegibilidad** y el **estimando** antes de imponer panel balanceado.
- `31,133` es un conteo exploratorio de pares con estado patrimonial futuro calculado usando el Q1 de cada submuestra, todavía no una cohorte de eventos incidentes ni estimación libre de leakage.
- Los factores muestrales y cortes monetarios deben validarse metodológicamente, no asumir que estas cifras son representativas de México.

## Reproducción
Reproducción vigente de CP1: ejecutar `scripts/run_cp1.py` y `notebooks/02_construccion_muestra.ipynb` con el archivo original en `data/raw/simpleMHAS.dta`. El diagnóstico histórico de Q1 no se reproduce en esta fase. El archivo `.dta` **no** está versionado ni incluido en el archivo .zip del repositorio.
