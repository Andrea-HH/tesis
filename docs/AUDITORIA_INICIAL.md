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
Ejecutar `notebooks/01_ingesta_y_diccionario.ipynb`, `02_construccion_muestra.ipynb` y `05_definicion_vulnerabilidad.ipynb` con el archivo original en `data/raw/simpleMHAS.dta`. El archivo `.dta` **no** está versionado ni incluido en el archivo .zip del repositorio.
