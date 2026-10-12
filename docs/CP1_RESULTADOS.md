# CP1 — Integridad y población longitudinal de ENASEMsimple

**Ejecución local: 2026-10-11; datos 2001–2021; estado: auditoría ejecutada, aceptación metodológica pendiente.**

## Introducción y objetivo
La alerta económica prospectiva necesita distinguir envejecimiento, incorporación de participantes y pérdida de observación antes de construir etiquetas. El objetivo de CP1 es establecer un universo persona-ronda auditable y comparar poblaciones candidatas. No se estiman modelos, causalidad ni vulnerabilidad patrimonial en esta etapa.

## Fuente, procedimiento y denominadores
ENASEMsimple, versión 2, enero de 2025: cuadro 1 (p. 3), claves y factores (pp. 3–4), códigos especiales (p. 8), ronda/tipent (p. 10), factores (pp. 11–12), cronología/fallecido (pp. 13–14), sexo/edad (pp. 15–17), localidad (p. 17) y estado conyugal (p. 19). El original se lee con `convert_missing=True`, sin modificarlo. Clave compuesta `cunicah` + `np`, ambos enteros no faltantes; se detiene la ejecución ante claves ausentes, rondas inválidas, entrevistas desconocidas o duplicados. El identificador derivado existe solamente en memoria.

Una observación es un registro persona-ronda; los totales de personas a través del periodo se calculan por unión de claves, nunca sumando personas por ronda. En frecuencias, el denominador es el total del grupo, incluidos faltantes; en estadísticos continuos se indica N válido. `.f`, `.p`, `.w`, `.d`, `.r`, `.s`, `.i`, `.m`, `.e`, `.x` y el perdido general se cuentan por separado si aparecen. `.w` identifica indisponibilidad de ronda en las tabulaciones del apéndice; no es cero. La cobertura empírica no reemplaza el universo de aplicación del cuestionario.

Todos los conteos son observados, sin ponderación. Los factores individuales y de hogar se auditan por ronda y entrevista; la validación de universo, pesos cero y diseño complejo queda pendiente. Un factor de hogar no puede sumarse sobre personas como total de hogares. No se calculan estimaciones ponderadas ni se usan factores transversales como longitudinales.


## Integridad general

| registros | personas | variables_originales | claves_faltantes | duplicados |
| --- | --- | --- | --- | --- |
| 99676 | 27171 | 119 | 0 | 0 |

| control | n |
| --- | --- |
| registros_despues_de_fallecimiento | 3 |
| personas_con_fallecimiento_repetido | 1 |
| personas_con_sexo_valido_inconsistente | 1 |
| pares_con_edad_decreciente | 226 |
| personas_con_ron_pat_inconsistente_entre_registros | 0 |

La auditoría conserva las anomalías. El control de claves y unicidad pasó sin exclusiones; los tipos de entrevista y totales coinciden exactamente con el diccionario.

## Resumen entre rondas

| ronda | ano_nominal | registros | personas | menores_60 | edad_60_mas | edad_faltante | duplicados | discrepancias_fallecido_tipent |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2001 | 15186 | 15186 | 7770 | 7416 | 0 | 0 | 0 |
| 2 | 2003 | 14250 | 14250 | 6002 | 7691 | 557 | 0 | 0 |
| 3 | 2012 | 18465 | 18465 | 5815 | 9886 | 2764 | 0 | 0 |
| 4 | 2015 | 15988 | 15988 | 4359 | 10416 | 1213 | 0 | 0 |
| 5 | 2018 | 18249 | 18249 | 6981 | 10113 | 1155 | 0 | 0 |
| 6 | 2021 | 17538 | 17538 | 5247 | 10482 | 1809 | 0 | 0 |

| ronda | denominador | n_validos | media | de | min | q25 | mediana | q75 | max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 15186 | 15186 | 60.79 | 10.85 | 18.00 | 53.00 | 59.00 | 68.00 | 106.00 |
| 2 | 14250 | 13693 | 62.68 | 10.52 | 21.00 | 55.00 | 61.00 | 69.00 | 108.00 |
| 3 | 18465 | 15701 | 63.97 | 11.08 | 20.00 | 56.00 | 63.00 | 71.00 | 115.00 |
| 4 | 15988 | 14775 | 66.13 | 10.62 | 23.00 | 58.00 | 66.00 | 73.00 | 113.00 |
| 5 | 18249 | 17094 | 64.16 | 11.51 | 17.00 | 55.00 | 63.00 | 72.00 | 107.00 |
| 6 | 17538 | 15729 | 66.20 | 10.89 | 23.00 | 57.00 | 65.00 | 74.00 | 106.00 |

## Ronda 1 — 2001

**Objetivo y método:** caracterizar esta ronda sin mezclar denominadores con otras. La frecuencia incluye faltantes; la edad continua utiliza solo valores válidos. El flujo sigue claves → entrevista directa → edad conocida → edad 60+.

La ronda 1 (2001) contiene 15,186 registros de 15,186 personas. Las entrevistas directas suman 14,154 (93.20% del total de la ronda), las de sustituto 1,032 (6.80%) y las de fallecimiento 0 (0.00%). La primera aparición se registra para 15,186 personas; 0 ya habían sido observadas y 0 reaparecen tras faltar a la ronda inmediatamente anterior. Primera aparición y entrevista de nueva persona son conceptos distintos y se calculan por separado.

La edad es válida en 15,186/15,186 registros: la mediana es 59.0 años y el intervalo intercuartílico 53.0–68.0. Se observan 7,770 registros menores de 60, 7,416 de 60 o más y 0 sin edad válida. El filtro directo 60+ conserva 6,812/15,186 (44.86%) y excluye 8,374. Las tablas de flujo distinguen entrevista, edad ausente y edad insuficiente.

 Se registran 8,683 mujeres (57.18% del total de la ronda).  Se registran 2,535 personas viudas (16.69% del total de la ronda).  Se registran 8,957 registros en localidades de 100 mil o más habitantes (58.98% del total de la ronda). 

Las distribuciones demográficas incluyen códigos especiales en el denominador total; la edad continua se resume únicamente entre valores válidos. Las diferencias entre rondas combinan envejecimiento, incorporaciones y selección por observación. No identifican cambios dentro de la misma persona ni efectos causales. Las entrevistas sobre fallecidos forman parte del seguimiento amplio y no son predictores directos contemporáneos. La tabla de pesos verifica disponibilidad, sin convertir su suma en un tamaño de muestra ni estimar todavía estadísticas poblacionales.

### Frecuencias demográficas, entrevista y año efectivo

| ronda | variable | categoria | n | denominador | porcentaje |
| --- | --- | --- | --- | --- | --- |
| 1 | tipent | Directa de seguimiento | 0 | 15186 | 0.00 |
| 1 | tipent | Directa de nueva persona | 14154 | 15186 | 93.20 |
| 1 | tipent | Sustituto de seguimiento | 0 | 15186 | 0.00 |
| 1 | tipent | Sustituto de nueva persona | 1032 | 15186 | 6.80 |
| 1 | tipent | Sobre fallecido | 0 | 15186 | 0.00 |
| 1 | sexo | Hombre | 6503 | 15186 | 42.82 |
| 1 | sexo | Mujer | 8683 | 15186 | 57.18 |
| 1 | est_conyugal | Casado o en unión | 10512 | 15186 | 69.22 |
| 1 | est_conyugal | Separado o divorciado | 1144 | 15186 | 7.53 |
| 1 | est_conyugal | Viudo | 2535 | 15186 | 16.69 |
| 1 | est_conyugal | Soltero | 539 | 15186 | 3.55 |
| 1 | est_conyugal | .m | 456 | 15186 | 3.00 |
| 1 | urbano | Menos de 100 mil residentes | 6229 | 15186 | 41.02 |
| 1 | urbano | 100 mil residentes o más | 8957 | 15186 | 58.98 |
| 1 | edad_gru | 49 o menos | 1553 | 15186 | 10.23 |
| 1 | edad_gru | 50–59 | 6217 | 15186 | 40.94 |
| 1 | edad_gru | 60–69 | 4207 | 15186 | 27.70 |
| 1 | edad_gru | 70–79 | 2307 | 15186 | 15.19 |
| 1 | edad_gru | 80 o más | 902 | 15186 | 5.94 |
| 1 | a_o_ent | 2001 | 15186 | 15186 | 100.00 |
| 1 | fallecido | No | 15186 | 15186 | 100.00 |
| 1 | fallecido | Sí | 0 | 15186 | 0.00 |

### Año efectivo por tipo de entrevista

| ronda | tipo_entrevista | categoria | n | denominador | porcentaje |
| --- | --- | --- | --- | --- | --- |
| 1 | Directa de nueva persona | 2001 | 14154 | 14154 | 100.00 |
| 1 | Sustituto de nueva persona | 2001 | 1032 | 1032 | 100.00 |

### Exclusiones secuenciales

| ronda | filtro | antes | excluidos | despues | personas | denominador | porcentaje_conservado |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Claves válidas y únicas | 15186 | 0 | 15186 | 15186 | 15186 | 100.00 |
| 1 | Entrevista directa | 15186 | 1032 | 14154 | 14154 | 15186 | 93.20 |
| 1 | Edad conocida | 14154 | 0 | 14154 | 14154 | 15186 | 93.20 |
| 1 | Edad 60+ | 14154 | 7342 | 6812 | 6812 | 15186 | 44.86 |

### Alternativas de población

| ronda | muestra | registros | personas | denominador_registros |
| --- | --- | --- | --- | --- |
| 1 | Universo amplio | 15186 | 15186 | 15186 |
| 1 | 60+ por visita, cualquier entrevista | 7416 | 7416 | 15186 |
| 1 | Directas, cualquier edad | 14154 | 14154 | 15186 |
| 1 | Directas 60+ por visita | 6812 | 6812 | 15186 |
| 1 | 60+ en primera observación, seguimiento amplio | 7416 | 7416 | 15186 |
| 1 | 60+ en primera observación, directas | 6812 | 6812 | 15186 |
| 1 | Desde primera observación 60+, seguimiento amplio | 7416 | 7416 | 15186 |
| 1 | Desde primera observación 60+, directas | 6812 | 6812 | 15186 |
| 1 | Seis rondas, cualquier entrevista/edad | 6305 | 6305 | 15186 |
| 1 | Seis directas, cualquier edad | 3893 | 3893 | 15186 |
| 1 | Seis directas 60+ por visita | 964 | 964 | 15186 |

### Disponibilidad de factores individuales y de hogar

| ronda | variable | tipo_entrevista | denominador | validos | positivos | ceros | negativos | faltantes | min | mediana | max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | factori_01 | Directa de nueva persona | 14154 | 14154 | 12485 | 1669 | 0 | 0 | 0 | 408.00 | 44177 |
| 1 | factori_01 | Sustituto de nueva persona | 1032 | 1032 | 978 | 54 | 0 | 0 | 0 | 519.00 | 25518 |
| 1 | factorh_01 | Directa de nueva persona | 14154 | 14154 | 14154 | 0 | 0 | 0 | 16 | 469.00 | 35360 |
| 1 | factorh_01 | Sustituto de nueva persona | 1032 | 1032 | 1032 | 0 | 0 | 0 | 26 | 526.00 | 22519 |

### Cobertura y causas de faltantes en variables de integridad

| ronda | variable | tipo | n | denominador | porcentaje |
| --- | --- | --- | --- | --- | --- |
| 1 | cunicah | válido | 15186 | 15186 | 100.00 |
| 1 | np | válido | 15186 | 15186 | 100.00 |
| 1 | ronda | válido | 15186 | 15186 | 100.00 |
| 1 | tipent | válido | 15186 | 15186 | 100.00 |
| 1 | a_o_ent | válido | 15186 | 15186 | 100.00 |
| 1 | fallecido | válido | 15186 | 15186 | 100.00 |
| 1 | sexo | válido | 15186 | 15186 | 100.00 |
| 1 | edad | válido | 15186 | 15186 | 100.00 |
| 1 | urbano | válido | 15186 | 15186 | 100.00 |
| 1 | est_conyugal | válido | 14730 | 15186 | 97.00 |
| 1 | est_conyugal | .m | 456 | 15186 | 3.00 |

La figura se regenera en `reports/figures/cp1_ronda_1.png`. La cobertura de las 119 variables y todos sus códigos se muestra íntegra en la ficha correspondiente del notebook ejecutado; no se restringe a las variables anteriores.

## Ronda 2 — 2003

**Objetivo y método:** caracterizar esta ronda sin mezclar denominadores con otras. La frecuencia incluye faltantes; la edad continua utiliza solo valores válidos. El flujo sigue claves → entrevista directa → edad conocida → edad 60+.

La ronda 2 (2003) contiene 14,250 registros de 14,250 personas. Las entrevistas directas suman 12,526 (87.90% del total de la ronda), las de sustituto 1,178 (8.27%) y las de fallecimiento 546 (3.83%). La primera aparición se registra para 277 personas; 13,973 ya habían sido observadas y 0 reaparecen tras faltar a la ronda inmediatamente anterior. Primera aparición y entrevista de nueva persona son conceptos distintos y se calculan por separado.

La edad es válida en 13,693/14,250 registros: la mediana es 61.0 años y el intervalo intercuartílico 55.0–69.0. Se observan 6,002 registros menores de 60, 7,691 de 60 o más y 557 sin edad válida. El filtro directo 60+ conserva 6,970/14,250 (48.91%) y excluye 7,280. Las tablas de flujo distinguen entrevista, edad ausente y edad insuficiente.

 Se registran 8,142 mujeres (57.14% del total de la ronda).  Se registran 2,545 personas viudas (17.86% del total de la ronda).  Se registran 7,927 registros en localidades de 100 mil o más habitantes (55.63% del total de la ronda).  La mediana de edad cambia +2.0 años respecto a la ronda anterior; es una comparación de muestras observadas, no un cambio individual. 

Las distribuciones demográficas incluyen códigos especiales en el denominador total; la edad continua se resume únicamente entre valores válidos. Las diferencias entre rondas combinan envejecimiento, incorporaciones y selección por observación. No identifican cambios dentro de la misma persona ni efectos causales. Las entrevistas sobre fallecidos forman parte del seguimiento amplio y no son predictores directos contemporáneos. La tabla de pesos verifica disponibilidad, sin convertir su suma en un tamaño de muestra ni estimar todavía estadísticas poblacionales.

### Frecuencias demográficas, entrevista y año efectivo

| ronda | variable | categoria | n | denominador | porcentaje |
| --- | --- | --- | --- | --- | --- |
| 2 | tipent | Directa de seguimiento | 12363 | 14250 | 86.76 |
| 2 | tipent | Directa de nueva persona | 163 | 14250 | 1.14 |
| 2 | tipent | Sustituto de seguimiento | 1134 | 14250 | 7.96 |
| 2 | tipent | Sustituto de nueva persona | 44 | 14250 | 0.31 |
| 2 | tipent | Sobre fallecido | 546 | 14250 | 3.83 |
| 2 | sexo | Hombre | 6108 | 14250 | 42.86 |
| 2 | sexo | Mujer | 8142 | 14250 | 57.14 |
| 2 | est_conyugal | Casado o en unión | 9689 | 14250 | 67.99 |
| 2 | est_conyugal | Separado o divorciado | 947 | 14250 | 6.65 |
| 2 | est_conyugal | Viudo | 2545 | 14250 | 17.86 |
| 2 | est_conyugal | Soltero | 522 | 14250 | 3.66 |
| 2 | est_conyugal | .f | 546 | 14250 | 3.83 |
| 2 | est_conyugal | .d | 1 | 14250 | 0.01 |
| 2 | urbano | Menos de 100 mil residentes | 5777 | 14250 | 40.54 |
| 2 | urbano | 100 mil residentes o más | 7927 | 14250 | 55.63 |
| 2 | urbano | .f | 546 | 14250 | 3.83 |
| 2 | edad_gru | 49 o menos | 882 | 14250 | 6.19 |
| 2 | edad_gru | 50–59 | 5120 | 14250 | 35.93 |
| 2 | edad_gru | 60–69 | 4304 | 14250 | 30.20 |
| 2 | edad_gru | 70–79 | 2415 | 14250 | 16.95 |
| 2 | edad_gru | 80 o más | 972 | 14250 | 6.82 |
| 2 | edad_gru | .f | 546 | 14250 | 3.83 |
| 2 | edad_gru | .d | 10 | 14250 | 0.07 |
| 2 | edad_gru | .e | 1 | 14250 | 0.01 |
| 2 | a_o_ent | 2003 | 14250 | 14250 | 100.00 |
| 2 | fallecido | No | 13704 | 14250 | 96.17 |
| 2 | fallecido | Sí | 546 | 14250 | 3.83 |

### Año efectivo por tipo de entrevista

| ronda | tipo_entrevista | categoria | n | denominador | porcentaje |
| --- | --- | --- | --- | --- | --- |
| 2 | Directa de seguimiento | 2003 | 12363 | 12363 | 100.00 |
| 2 | Directa de nueva persona | 2003 | 163 | 163 | 100.00 |
| 2 | Sustituto de seguimiento | 2003 | 1134 | 1134 | 100.00 |
| 2 | Sustituto de nueva persona | 2003 | 44 | 44 | 100.00 |
| 2 | Sobre fallecido | 2003 | 546 | 546 | 100.00 |

### Exclusiones secuenciales

| ronda | filtro | antes | excluidos | despues | personas | denominador | porcentaje_conservado |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | Claves válidas y únicas | 14250 | 0 | 14250 | 14250 | 14250 | 100.00 |
| 2 | Entrevista directa | 14250 | 1724 | 12526 | 12526 | 14250 | 87.90 |
| 2 | Edad conocida | 12526 | 2 | 12524 | 12524 | 14250 | 87.89 |
| 2 | Edad 60+ | 12524 | 5554 | 6970 | 6970 | 14250 | 48.91 |

### Alternativas de población

| ronda | muestra | registros | personas | denominador_registros |
| --- | --- | --- | --- | --- |
| 2 | Universo amplio | 14250 | 14250 | 14250 |
| 2 | 60+ por visita, cualquier entrevista | 7691 | 7691 | 14250 |
| 2 | Directas, cualquier edad | 12526 | 12526 | 14250 |
| 2 | Directas 60+ por visita | 6970 | 6970 | 14250 |
| 2 | 60+ en primera observación, seguimiento amplio | 7140 | 7140 | 14250 |
| 2 | 60+ en primera observación, directas | 6043 | 6043 | 14250 |
| 2 | Desde primera observación 60+, seguimiento amplio | 8147 | 8147 | 14250 |
| 2 | Desde primera observación 60+, directas | 6970 | 6970 | 14250 |
| 2 | Seis rondas, cualquier entrevista/edad | 6305 | 6305 | 14250 |
| 2 | Seis directas, cualquier edad | 3893 | 3893 | 14250 |
| 2 | Seis directas 60+ por visita | 964 | 964 | 14250 |

### Disponibilidad de factores individuales y de hogar

| ronda | variable | tipo_entrevista | denominador | validos | positivos | ceros | negativos | faltantes | min | mediana | max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | factori_03 | Directa de seguimiento | 12363 | 12363 | 11004 | 1359 | 0 | 0 | 0 | 433.00 | 46315 |
| 2 | factori_03 | Directa de nueva persona | 163 | 163 | 84 | 79 | 0 | 0 | 0 | 43.00 | 8794 |
| 2 | factori_03 | Sustituto de seguimiento | 1134 | 1134 | 1059 | 75 | 0 | 0 | 0 | 537.00 | 39865 |
| 2 | factori_03 | Sustituto de nueva persona | 44 | 44 | 17 | 27 | 0 | 0 | 0 | 0.00 | 5489 |
| 2 | factori_03 | Sobre fallecido | 546 | 546 | 0 | 546 | 0 | 0 | 0 | 0.00 | 0 |
| 2 | factorh_03 | Directa de seguimiento | 12363 | 12363 | 11004 | 1359 | 0 | 0 | 0 | 433.00 | 46315 |
| 2 | factorh_03 | Directa de nueva persona | 163 | 163 | 0 | 163 | 0 | 0 | 0 | 0.00 | 0 |
| 2 | factorh_03 | Sustituto de seguimiento | 1134 | 1134 | 1059 | 75 | 0 | 0 | 0 | 537.00 | 39865 |
| 2 | factorh_03 | Sustituto de nueva persona | 44 | 44 | 1 | 43 | 0 | 0 | 0 | 0.00 | 676 |
| 2 | factorh_03 | Sobre fallecido | 546 | 546 | 0 | 546 | 0 | 0 | 0 | 0.00 | 0 |

### Cobertura y causas de faltantes en variables de integridad

| ronda | variable | tipo | n | denominador | porcentaje |
| --- | --- | --- | --- | --- | --- |
| 2 | cunicah | válido | 14250 | 14250 | 100.00 |
| 2 | np | válido | 14250 | 14250 | 100.00 |
| 2 | ronda | válido | 14250 | 14250 | 100.00 |
| 2 | tipent | válido | 14250 | 14250 | 100.00 |
| 2 | a_o_ent | válido | 14250 | 14250 | 100.00 |
| 2 | fallecido | válido | 14250 | 14250 | 100.00 |
| 2 | sexo | válido | 14250 | 14250 | 100.00 |
| 2 | edad | válido | 13693 | 14250 | 96.09 |
| 2 | edad | .f | 546 | 14250 | 3.83 |
| 2 | edad | .d | 10 | 14250 | 0.07 |
| 2 | edad | .e | 1 | 14250 | 0.01 |
| 2 | urbano | válido | 13704 | 14250 | 96.17 |
| 2 | urbano | .f | 546 | 14250 | 3.83 |
| 2 | est_conyugal | válido | 13703 | 14250 | 96.16 |
| 2 | est_conyugal | .f | 546 | 14250 | 3.83 |
| 2 | est_conyugal | .d | 1 | 14250 | 0.01 |

La figura se regenera en `reports/figures/cp1_ronda_2.png`. La cobertura de las 119 variables y todos sus códigos se muestra íntegra en la ficha correspondiente del notebook ejecutado; no se restringe a las variables anteriores.

## Ronda 3 — 2012

**Objetivo y método:** caracterizar esta ronda sin mezclar denominadores con otras. La frecuencia incluye faltantes; la edad continua utiliza solo valores válidos. El flujo sigue claves → entrevista directa → edad conocida → edad 60+.

La ronda 3 (2012) contiene 18,465 registros de 18,465 personas. Las entrevistas directas suman 14,448 (78.25% del total de la ronda), las de sustituto 1,275 (6.90%) y las de fallecimiento 2,742 (14.85%). La primera aparición se registra para 5,912 personas; 12,553 ya habían sido observadas y 357 reaparecen tras faltar a la ronda inmediatamente anterior. Primera aparición y entrevista de nueva persona son conceptos distintos y se calculan por separado.

La edad es válida en 15,701/18,465 registros: la mediana es 63.0 años y el intervalo intercuartílico 56.0–71.0. Se observan 5,815 registros menores de 60, 9,886 de 60 o más y 2,764 sin edad válida. El filtro directo 60+ conserva 8,888/18,465 (48.13%) y excluye 9,577. Las tablas de flujo distinguen entrevista, edad ausente y edad insuficiente.

 Se registran 10,465 mujeres (56.67% del total de la ronda).  Se registran 2,860 personas viudas (15.49% del total de la ronda).  Se registran 9,123 registros en localidades de 100 mil o más habitantes (49.41% del total de la ronda).  La mediana de edad cambia +2.0 años respecto a la ronda anterior; es una comparación de muestras observadas, no un cambio individual. 

Las distribuciones demográficas incluyen códigos especiales en el denominador total; la edad continua se resume únicamente entre valores válidos. Las diferencias entre rondas combinan envejecimiento, incorporaciones y selección por observación. No identifican cambios dentro de la misma persona ni efectos causales. Las entrevistas sobre fallecidos forman parte del seguimiento amplio y no son predictores directos contemporáneos. La tabla de pesos verifica disponibilidad, sin convertir su suma en un tamaño de muestra ni estimar todavía estadísticas poblacionales.

### Frecuencias demográficas, entrevista y año efectivo

| ronda | variable | categoria | n | denominador | porcentaje |
| --- | --- | --- | --- | --- | --- |
| 3 | tipent | Directa de seguimiento | 8868 | 18465 | 48.03 |
| 3 | tipent | Directa de nueva persona | 5580 | 18465 | 30.22 |
| 3 | tipent | Sustituto de seguimiento | 959 | 18465 | 5.19 |
| 3 | tipent | Sustituto de nueva persona | 316 | 18465 | 1.71 |
| 3 | tipent | Sobre fallecido | 2742 | 18465 | 14.85 |
| 3 | sexo | Hombre | 8000 | 18465 | 43.33 |
| 3 | sexo | Mujer | 10465 | 18465 | 56.67 |
| 3 | est_conyugal | Casado o en unión | 10910 | 18465 | 59.08 |
| 3 | est_conyugal | Separado o divorciado | 1231 | 18465 | 6.67 |
| 3 | est_conyugal | Viudo | 2860 | 18465 | 15.49 |
| 3 | est_conyugal | Soltero | 722 | 18465 | 3.91 |
| 3 | est_conyugal | .f | 2742 | 18465 | 14.85 |
| 3 | urbano | Menos de 100 mil residentes | 6600 | 18465 | 35.74 |
| 3 | urbano | 100 mil residentes o más | 9123 | 18465 | 49.41 |
| 3 | urbano | .f | 2742 | 18465 | 14.85 |
| 3 | edad_gru | 49 o menos | 1037 | 18465 | 5.62 |
| 3 | edad_gru | 50–59 | 4778 | 18465 | 25.88 |
| 3 | edad_gru | 60–69 | 5229 | 18465 | 28.32 |
| 3 | edad_gru | 70–79 | 3178 | 18465 | 17.21 |
| 3 | edad_gru | 80 o más | 1479 | 18465 | 8.01 |
| 3 | edad_gru | .f | 2742 | 18465 | 14.85 |
| 3 | edad_gru | .d | 22 | 18465 | 0.12 |
| 3 | a_o_ent | 2012 | 15707 | 18465 | 85.06 |
| 3 | a_o_ent | .f | 2742 | 18465 | 14.85 |
| 3 | a_o_ent | 2013 | 14 | 18465 | 0.08 |
| 3 | a_o_ent | .e | 1 | 18465 | 0.01 |
| 3 | a_o_ent | .i | 1 | 18465 | 0.01 |
| 3 | fallecido | No | 15723 | 18465 | 85.15 |
| 3 | fallecido | Sí | 2742 | 18465 | 14.85 |

### Año efectivo por tipo de entrevista

| ronda | tipo_entrevista | categoria | n | denominador | porcentaje |
| --- | --- | --- | --- | --- | --- |
| 3 | Directa de seguimiento | 2012 | 8854 | 8868 | 99.84 |
| 3 | Directa de seguimiento | 2013 | 13 | 8868 | 0.15 |
| 3 | Directa de seguimiento | .e | 1 | 8868 | 0.01 |
| 3 | Directa de nueva persona | 2012 | 5579 | 5580 | 99.98 |
| 3 | Directa de nueva persona | .i | 1 | 5580 | 0.02 |
| 3 | Sustituto de seguimiento | 2012 | 958 | 959 | 99.90 |
| 3 | Sustituto de seguimiento | 2013 | 1 | 959 | 0.10 |
| 3 | Sustituto de nueva persona | 2012 | 316 | 316 | 100.00 |
| 3 | Sobre fallecido | .f | 2742 | 2742 | 100.00 |

### Exclusiones secuenciales

| ronda | filtro | antes | excluidos | despues | personas | denominador | porcentaje_conservado |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3 | Claves válidas y únicas | 18465 | 0 | 18465 | 18465 | 18465 | 100.00 |
| 3 | Entrevista directa | 18465 | 4017 | 14448 | 14448 | 18465 | 78.25 |
| 3 | Edad conocida | 14448 | 14 | 14434 | 14434 | 18465 | 78.17 |
| 3 | Edad 60+ | 14434 | 5546 | 8888 | 8888 | 18465 | 48.13 |

### Alternativas de población

| ronda | muestra | registros | personas | denominador_registros |
| --- | --- | --- | --- | --- |
| 3 | Universo amplio | 18465 | 18465 | 18465 |
| 3 | 60+ por visita, cualquier entrevista | 9886 | 9886 | 18465 |
| 3 | Directas, cualquier edad | 14448 | 14448 | 18465 |
| 3 | Directas 60+ por visita | 8888 | 8888 | 18465 |
| 3 | 60+ en primera observación, seguimiento amplio | 7123 | 7123 | 18465 |
| 3 | 60+ en primera observación, directas | 4281 | 4281 | 18465 |
| 3 | Desde primera observación 60+, seguimiento amplio | 12171 | 12171 | 18465 |
| 3 | Desde primera observación 60+, directas | 8893 | 8893 | 18465 |
| 3 | Seis rondas, cualquier entrevista/edad | 6305 | 6305 | 18465 |
| 3 | Seis directas, cualquier edad | 3893 | 3893 | 18465 |
| 3 | Seis directas 60+ por visita | 964 | 964 | 18465 |

### Disponibilidad de factores individuales y de hogar

| ronda | variable | tipo_entrevista | denominador | validos | positivos | ceros | negativos | faltantes | min | mediana | max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3 | factori_12 | Directa de seguimiento | 8868 | 8868 | 7509 | 1359 | 0 | 0 | 0 | 412.50 | 50368 |
| 3 | factori_12 | Directa de nueva persona | 5580 | 5580 | 5549 | 31 | 0 | 0 | 0 | 1343.00 | 97546 |
| 3 | factori_12 | Sustituto de seguimiento | 959 | 959 | 892 | 67 | 0 | 0 | 0 | 539.00 | 14822 |
| 3 | factori_12 | Sustituto de nueva persona | 316 | 316 | 313 | 3 | 0 | 0 | 0 | 1621.00 | 35146 |
| 3 | factori_12 | Sobre fallecido | 2742 | 2742 | 2624 | 118 | 0 | 0 | 0 | 529.50 | 42751 |
| 3 | factorh_12 | Directa de seguimiento | 8868 | 8868 | 8338 | 530 | 0 | 0 | 0 | 457.00 | 45701 |
| 3 | factorh_12 | Directa de nueva persona | 5580 | 5580 | 5563 | 17 | 0 | 0 | 0 | 1290.00 | 72628 |
| 3 | factorh_12 | Sustituto de seguimiento | 959 | 959 | 916 | 43 | 0 | 0 | 0 | 521.00 | 13877 |
| 3 | factorh_12 | Sustituto de nueva persona | 316 | 316 | 313 | 3 | 0 | 0 | 0 | 1570.50 | 35146 |
| 3 | factorh_12 | Sobre fallecido | 2742 | 2742 | 2613 | 129 | 0 | 0 | 0 | 494.00 | 39882 |

### Cobertura y causas de faltantes en variables de integridad

| ronda | variable | tipo | n | denominador | porcentaje |
| --- | --- | --- | --- | --- | --- |
| 3 | cunicah | válido | 18465 | 18465 | 100.00 |
| 3 | np | válido | 18465 | 18465 | 100.00 |
| 3 | ronda | válido | 18465 | 18465 | 100.00 |
| 3 | tipent | válido | 18465 | 18465 | 100.00 |
| 3 | a_o_ent | válido | 15721 | 18465 | 85.14 |
| 3 | a_o_ent | .f | 2742 | 18465 | 14.85 |
| 3 | a_o_ent | .e | 1 | 18465 | 0.01 |
| 3 | a_o_ent | .i | 1 | 18465 | 0.01 |
| 3 | fallecido | válido | 18465 | 18465 | 100.00 |
| 3 | sexo | válido | 18465 | 18465 | 100.00 |
| 3 | edad | válido | 15701 | 18465 | 85.03 |
| 3 | edad | .f | 2742 | 18465 | 14.85 |
| 3 | edad | .d | 22 | 18465 | 0.12 |
| 3 | urbano | válido | 15723 | 18465 | 85.15 |
| 3 | urbano | .f | 2742 | 18465 | 14.85 |
| 3 | est_conyugal | válido | 15723 | 18465 | 85.15 |
| 3 | est_conyugal | .f | 2742 | 18465 | 14.85 |

La figura se regenera en `reports/figures/cp1_ronda_3.png`. La cobertura de las 119 variables y todos sus códigos se muestra íntegra en la ficha correspondiente del notebook ejecutado; no se restringe a las variables anteriores.

## Ronda 4 — 2015

**Objetivo y método:** caracterizar esta ronda sin mezclar denominadores con otras. La frecuencia incluye faltantes; la edad continua utiliza solo valores válidos. El flujo sigue claves → entrevista directa → edad conocida → edad 60+.

La ronda 4 (2015) contiene 15,988 registros de 15,988 personas. Las entrevistas directas suman 13,850 (86.63% del total de la ronda), las de sustituto 929 (5.81%) y las de fallecimiento 1,209 (7.56%). La primera aparición se registra para 650 personas; 15,338 ya habían sido observadas y 624 reaparecen tras faltar a la ronda inmediatamente anterior. Primera aparición y entrevista de nueva persona son conceptos distintos y se calculan por separado.

La edad es válida en 14,775/15,988 registros: la mediana es 66.0 años y el intervalo intercuartílico 58.0–73.0. Se observan 4,359 registros menores de 60, 10,416 de 60 o más y 1,213 sin edad válida. El filtro directo 60+ conserva 9,640/15,988 (60.30%) y excluye 6,348. Las tablas de flujo distinguen entrevista, edad ausente y edad insuficiente.

 Se registran 9,249 mujeres (57.85% del total de la ronda).  Se registran 2,829 personas viudas (17.69% del total de la ronda).  Se registran 8,450 registros en localidades de 100 mil o más habitantes (52.85% del total de la ronda).  La mediana de edad cambia +3.0 años respecto a la ronda anterior; es una comparación de muestras observadas, no un cambio individual. 

Las distribuciones demográficas incluyen códigos especiales en el denominador total; la edad continua se resume únicamente entre valores válidos. Las diferencias entre rondas combinan envejecimiento, incorporaciones y selección por observación. No identifican cambios dentro de la misma persona ni efectos causales. Las entrevistas sobre fallecidos forman parte del seguimiento amplio y no son predictores directos contemporáneos. La tabla de pesos verifica disponibilidad, sin convertir su suma en un tamaño de muestra ni estimar todavía estadísticas poblacionales.

### Frecuencias demográficas, entrevista y año efectivo

| ronda | variable | categoria | n | denominador | porcentaje |
| --- | --- | --- | --- | --- | --- |
| 4 | tipent | Directa de seguimiento | 13254 | 15988 | 82.90 |
| 4 | tipent | Directa de nueva persona | 596 | 15988 | 3.73 |
| 4 | tipent | Sustituto de seguimiento | 884 | 15988 | 5.53 |
| 4 | tipent | Sustituto de nueva persona | 45 | 15988 | 0.28 |
| 4 | tipent | Sobre fallecido | 1209 | 15988 | 7.56 |
| 4 | sexo | Hombre | 6739 | 15988 | 42.15 |
| 4 | sexo | Mujer | 9249 | 15988 | 57.85 |
| 4 | est_conyugal | Casado o en unión | 9862 | 15988 | 61.68 |
| 4 | est_conyugal | Separado o divorciado | 1473 | 15988 | 9.21 |
| 4 | est_conyugal | Viudo | 2829 | 15988 | 17.69 |
| 4 | est_conyugal | Soltero | 615 | 15988 | 3.85 |
| 4 | est_conyugal | .f | 1209 | 15988 | 7.56 |
| 4 | urbano | Menos de 100 mil residentes | 6329 | 15988 | 39.59 |
| 4 | urbano | 100 mil residentes o más | 8450 | 15988 | 52.85 |
| 4 | urbano | .f | 1209 | 15988 | 7.56 |
| 4 | edad_gru | 49 o menos | 560 | 15988 | 3.50 |
| 4 | edad_gru | 50–59 | 3799 | 15988 | 23.76 |
| 4 | edad_gru | 60–69 | 5092 | 15988 | 31.85 |
| 4 | edad_gru | 70–79 | 3619 | 15988 | 22.64 |
| 4 | edad_gru | 80 o más | 1705 | 15988 | 10.66 |
| 4 | edad_gru | .f | 1209 | 15988 | 7.56 |
| 4 | edad_gru | .d | 4 | 15988 | 0.03 |
| 4 | a_o_ent | 2015 | 14779 | 15988 | 92.44 |
| 4 | a_o_ent | .f | 1209 | 15988 | 7.56 |
| 4 | fallecido | No | 14779 | 15988 | 92.44 |
| 4 | fallecido | Sí | 1209 | 15988 | 7.56 |

### Año efectivo por tipo de entrevista

| ronda | tipo_entrevista | categoria | n | denominador | porcentaje |
| --- | --- | --- | --- | --- | --- |
| 4 | Directa de seguimiento | 2015 | 13254 | 13254 | 100.00 |
| 4 | Directa de nueva persona | 2015 | 596 | 596 | 100.00 |
| 4 | Sustituto de seguimiento | 2015 | 884 | 884 | 100.00 |
| 4 | Sustituto de nueva persona | 2015 | 45 | 45 | 100.00 |
| 4 | Sobre fallecido | .f | 1209 | 1209 | 100.00 |

### Exclusiones secuenciales

| ronda | filtro | antes | excluidos | despues | personas | denominador | porcentaje_conservado |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 4 | Claves válidas y únicas | 15988 | 0 | 15988 | 15988 | 15988 | 100.00 |
| 4 | Entrevista directa | 15988 | 2138 | 13850 | 13850 | 15988 | 86.63 |
| 4 | Edad conocida | 13850 | 4 | 13846 | 13846 | 15988 | 86.60 |
| 4 | Edad 60+ | 13846 | 4206 | 9640 | 9640 | 15988 | 60.30 |

### Alternativas de población

| ronda | muestra | registros | personas | denominador_registros |
| --- | --- | --- | --- | --- |
| 4 | Universo amplio | 15988 | 15988 | 15988 |
| 4 | 60+ por visita, cualquier entrevista | 10416 | 10416 | 15988 |
| 4 | Directas, cualquier edad | 13850 | 13850 | 15988 |
| 4 | Directas 60+ por visita | 9640 | 9640 | 15988 |
| 4 | 60+ en primera observación, seguimiento amplio | 5189 | 5189 | 15988 |
| 4 | 60+ en primera observación, directas | 3857 | 3857 | 15988 |
| 4 | Desde primera observación 60+, seguimiento amplio | 11539 | 11539 | 15988 |
| 4 | Desde primera observación 60+, directas | 9668 | 9668 | 15988 |
| 4 | Seis rondas, cualquier entrevista/edad | 6305 | 6305 | 15988 |
| 4 | Seis directas, cualquier edad | 3893 | 3893 | 15988 |
| 4 | Seis directas 60+ por visita | 964 | 964 | 15988 |

### Disponibilidad de factores individuales y de hogar

| ronda | variable | tipo_entrevista | denominador | validos | positivos | ceros | negativos | faltantes | min | mediana | max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4 | factori_15 | Directa de seguimiento | 13254 | 13254 | 12858 | 396 | 0 | 0 | 0 | 587.00 | 90984 |
| 4 | factori_15 | Directa de nueva persona | 596 | 596 | 517 | 79 | 0 | 0 | 0 | 775.00 | 33725 |
| 4 | factori_15 | Sustituto de seguimiento | 884 | 884 | 867 | 17 | 0 | 0 | 0 | 601.50 | 27354 |
| 4 | factori_15 | Sustituto de nueva persona | 45 | 45 | 40 | 5 | 0 | 0 | 0 | 709.00 | 3879 |
| 4 | factori_15 | Sobre fallecido | 1209 | 1209 | 1185 | 24 | 0 | 0 | 0 | 471.00 | 27925 |
| 4 | factorh_15 | Directa de seguimiento | 13254 | 13254 | 12943 | 311 | 0 | 0 | 0 | 682.00 | 51137 |
| 4 | factorh_15 | Directa de nueva persona | 596 | 596 | 582 | 14 | 0 | 0 | 0 | 615.00 | 22358 |
| 4 | factorh_15 | Sustituto de seguimiento | 884 | 884 | 857 | 27 | 0 | 0 | 0 | 768.50 | 20520 |
| 4 | factorh_15 | Sustituto de nueva persona | 45 | 45 | 44 | 1 | 0 | 0 | 0 | 610.00 | 2774 |
| 4 | factorh_15 | Sobre fallecido | 1209 | 1209 | 1187 | 22 | 0 | 0 | 0 | 654.00 | 38728 |

### Cobertura y causas de faltantes en variables de integridad

| ronda | variable | tipo | n | denominador | porcentaje |
| --- | --- | --- | --- | --- | --- |
| 4 | cunicah | válido | 15988 | 15988 | 100.00 |
| 4 | np | válido | 15988 | 15988 | 100.00 |
| 4 | ronda | válido | 15988 | 15988 | 100.00 |
| 4 | tipent | válido | 15988 | 15988 | 100.00 |
| 4 | a_o_ent | válido | 14779 | 15988 | 92.44 |
| 4 | a_o_ent | .f | 1209 | 15988 | 7.56 |
| 4 | fallecido | válido | 15988 | 15988 | 100.00 |
| 4 | sexo | válido | 15988 | 15988 | 100.00 |
| 4 | edad | válido | 14775 | 15988 | 92.41 |
| 4 | edad | .f | 1209 | 15988 | 7.56 |
| 4 | edad | .d | 4 | 15988 | 0.03 |
| 4 | urbano | válido | 14779 | 15988 | 92.44 |
| 4 | urbano | .f | 1209 | 15988 | 7.56 |
| 4 | est_conyugal | válido | 14779 | 15988 | 92.44 |
| 4 | est_conyugal | .f | 1209 | 15988 | 7.56 |

La figura se regenera en `reports/figures/cp1_ronda_4.png`. La cobertura de las 119 variables y todos sus códigos se muestra íntegra en la ficha correspondiente del notebook ejecutado; no se restringe a las variables anteriores.

## Ronda 5 — 2018

**Objetivo y método:** caracterizar esta ronda sin mezclar denominadores con otras. La frecuencia incluye faltantes; la edad continua utiliza solo valores válidos. El flujo sigue claves → entrevista directa → edad conocida → edad 60+.

La ronda 5 (2018) contiene 18,249 registros de 18,249 personas. Las entrevistas directas suman 15,786 (86.50% del total de la ronda), las de sustituto 1,328 (7.28%) y las de fallecimiento 1,135 (6.22%). La primera aparición se registra para 4,823 personas; 13,426 ya habían sido observadas y 383 reaparecen tras faltar a la ronda inmediatamente anterior. Primera aparición y entrevista de nueva persona son conceptos distintos y se calculan por separado.

La edad es válida en 17,094/18,249 registros: la mediana es 63.0 años y el intervalo intercuartílico 55.0–72.0. Se observan 6,981 registros menores de 60, 10,113 de 60 o más y 1,155 sin edad válida. El filtro directo 60+ conserva 9,107/18,249 (49.90%) y excluye 9,142. Las tablas de flujo distinguen entrevista, edad ausente y edad insuficiente.

 Se registran 10,488 mujeres (57.47% del total de la ronda).  Se registran 3,047 personas viudas (16.70% del total de la ronda).  Se registran 9,524 registros en localidades de 100 mil o más habitantes (52.19% del total de la ronda).  La mediana de edad cambia -3.0 años respecto a la ronda anterior; es una comparación de muestras observadas, no un cambio individual. 

Las distribuciones demográficas incluyen códigos especiales en el denominador total; la edad continua se resume únicamente entre valores válidos. Las diferencias entre rondas combinan envejecimiento, incorporaciones y selección por observación. No identifican cambios dentro de la misma persona ni efectos causales. Las entrevistas sobre fallecidos forman parte del seguimiento amplio y no son predictores directos contemporáneos. La tabla de pesos verifica disponibilidad, sin convertir su suma en un tamaño de muestra ni estimar todavía estadísticas poblacionales.

### Frecuencias demográficas, entrevista y año efectivo

| ronda | variable | categoria | n | denominador | porcentaje |
| --- | --- | --- | --- | --- | --- |
| 5 | tipent | Directa de seguimiento | 11183 | 18249 | 61.28 |
| 5 | tipent | Directa de nueva persona | 4603 | 18249 | 25.22 |
| 5 | tipent | Sustituto de seguimiento | 1122 | 18249 | 6.15 |
| 5 | tipent | Sustituto de nueva persona | 206 | 18249 | 1.13 |
| 5 | tipent | Sobre fallecido | 1135 | 18249 | 6.22 |
| 5 | sexo | Hombre | 7761 | 18249 | 42.53 |
| 5 | sexo | Mujer | 10488 | 18249 | 57.47 |
| 5 | est_conyugal | Casado o en unión | 11838 | 18249 | 64.87 |
| 5 | est_conyugal | Separado o divorciado | 1325 | 18249 | 7.26 |
| 5 | est_conyugal | Viudo | 3047 | 18249 | 16.70 |
| 5 | est_conyugal | Soltero | 904 | 18249 | 4.95 |
| 5 | est_conyugal | .f | 1135 | 18249 | 6.22 |
| 5 | urbano | Menos de 100 mil residentes | 7590 | 18249 | 41.59 |
| 5 | urbano | 100 mil residentes o más | 9524 | 18249 | 52.19 |
| 5 | urbano | .f | 1135 | 18249 | 6.22 |
| 5 | edad_gru | 49 o menos | 895 | 18249 | 4.90 |
| 5 | edad_gru | 50–59 | 6086 | 18249 | 33.35 |
| 5 | edad_gru | 60–69 | 4430 | 18249 | 24.28 |
| 5 | edad_gru | 70–79 | 3839 | 18249 | 21.04 |
| 5 | edad_gru | 80 o más | 1844 | 18249 | 10.10 |
| 5 | edad_gru | .f | 1135 | 18249 | 6.22 |
| 5 | edad_gru | .d | 15 | 18249 | 0.08 |
| 5 | edad_gru | .r | 5 | 18249 | 0.03 |
| 5 | a_o_ent | 2018 | 16705 | 18249 | 91.54 |
| 5 | a_o_ent | .f | 1135 | 18249 | 6.22 |
| 5 | a_o_ent | 2019 | 409 | 18249 | 2.24 |
| 5 | fallecido | No | 17114 | 18249 | 93.78 |
| 5 | fallecido | Sí | 1135 | 18249 | 6.22 |

### Año efectivo por tipo de entrevista

| ronda | tipo_entrevista | categoria | n | denominador | porcentaje |
| --- | --- | --- | --- | --- | --- |
| 5 | Directa de seguimiento | 2018 | 10941 | 11183 | 97.84 |
| 5 | Directa de seguimiento | 2019 | 242 | 11183 | 2.16 |
| 5 | Directa de nueva persona | 2018 | 4488 | 4603 | 97.50 |
| 5 | Directa de nueva persona | 2019 | 115 | 4603 | 2.50 |
| 5 | Sustituto de seguimiento | 2018 | 1079 | 1122 | 96.17 |
| 5 | Sustituto de seguimiento | 2019 | 43 | 1122 | 3.83 |
| 5 | Sustituto de nueva persona | 2018 | 197 | 206 | 95.63 |
| 5 | Sustituto de nueva persona | 2019 | 9 | 206 | 4.37 |
| 5 | Sobre fallecido | .f | 1135 | 1135 | 100.00 |

### Exclusiones secuenciales

| ronda | filtro | antes | excluidos | despues | personas | denominador | porcentaje_conservado |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 5 | Claves válidas y únicas | 18249 | 0 | 18249 | 18249 | 18249 | 100.00 |
| 5 | Entrevista directa | 18249 | 2463 | 15786 | 15786 | 18249 | 86.50 |
| 5 | Edad conocida | 15786 | 19 | 15767 | 15767 | 18249 | 86.40 |
| 5 | Edad 60+ | 15767 | 6660 | 9107 | 9107 | 18249 | 49.90 |

### Alternativas de población

| ronda | muestra | registros | personas | denominador_registros |
| --- | --- | --- | --- | --- |
| 5 | Universo amplio | 18249 | 18249 | 18249 |
| 5 | 60+ por visita, cualquier entrevista | 10113 | 10113 | 18249 |
| 5 | Directas, cualquier edad | 15786 | 15786 | 18249 |
| 5 | Directas 60+ por visita | 9107 | 9107 | 18249 |
| 5 | 60+ en primera observación, seguimiento amplio | 4341 | 4341 | 18249 |
| 5 | 60+ en primera observación, directas | 3063 | 3063 | 18249 |
| 5 | Desde primera observación 60+, seguimiento amplio | 11186 | 11186 | 18249 |
| 5 | Desde primera observación 60+, directas | 9130 | 9130 | 18249 |
| 5 | Seis rondas, cualquier entrevista/edad | 6305 | 6305 | 18249 |
| 5 | Seis directas, cualquier edad | 3893 | 3893 | 18249 |
| 5 | Seis directas 60+ por visita | 964 | 964 | 18249 |

### Disponibilidad de factores individuales y de hogar

| ronda | variable | tipo_entrevista | denominador | validos | positivos | ceros | negativos | faltantes | min | mediana | max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5 | factori_18 | Directa de seguimiento | 11183 | 11183 | 11173 | 10 | 0 | 0 | 0 | 779.00 | 98699 |
| 5 | factori_18 | Directa de nueva persona | 4603 | 4603 | 4584 | 19 | 0 | 0 | 0 | 963.00 | 32372 |
| 5 | factori_18 | Sustituto de seguimiento | 1122 | 1122 | 1122 | 0 | 0 | 0 | 14 | 810.00 | 21919 |
| 5 | factori_18 | Sustituto de nueva persona | 206 | 206 | 205 | 1 | 0 | 0 | 0 | 905.00 | 9821 |
| 5 | factori_18 | Sobre fallecido | 1135 | 1135 | 1135 | 0 | 0 | 0 | 26 | 574.00 | 26017 |
| 5 | factorh_18 | Directa de seguimiento | 11183 | 11183 | 11174 | 9 | 0 | 0 | 0 | 741.00 | 90984 |
| 5 | factorh_18 | Directa de nueva persona | 4603 | 4603 | 4601 | 2 | 0 | 0 | 0 | 668.00 | 18435 |
| 5 | factorh_18 | Sustituto de seguimiento | 1122 | 1122 | 1122 | 0 | 0 | 0 | 19 | 765.00 | 16823 |
| 5 | factorh_18 | Sustituto de nueva persona | 206 | 206 | 206 | 0 | 0 | 0 | 55 | 590.00 | 6430 |
| 5 | factorh_18 | Sobre fallecido | 1135 | 1135 | 1135 | 0 | 0 | 0 | 26 | 568.00 | 26017 |

### Cobertura y causas de faltantes en variables de integridad

| ronda | variable | tipo | n | denominador | porcentaje |
| --- | --- | --- | --- | --- | --- |
| 5 | cunicah | válido | 18249 | 18249 | 100.00 |
| 5 | np | válido | 18249 | 18249 | 100.00 |
| 5 | ronda | válido | 18249 | 18249 | 100.00 |
| 5 | tipent | válido | 18249 | 18249 | 100.00 |
| 5 | a_o_ent | válido | 17114 | 18249 | 93.78 |
| 5 | a_o_ent | .f | 1135 | 18249 | 6.22 |
| 5 | fallecido | válido | 18249 | 18249 | 100.00 |
| 5 | sexo | válido | 18249 | 18249 | 100.00 |
| 5 | edad | válido | 17094 | 18249 | 93.67 |
| 5 | edad | .f | 1135 | 18249 | 6.22 |
| 5 | edad | .d | 15 | 18249 | 0.08 |
| 5 | edad | .r | 5 | 18249 | 0.03 |
| 5 | urbano | válido | 17114 | 18249 | 93.78 |
| 5 | urbano | .f | 1135 | 18249 | 6.22 |
| 5 | est_conyugal | válido | 17114 | 18249 | 93.78 |
| 5 | est_conyugal | .f | 1135 | 18249 | 6.22 |

La figura se regenera en `reports/figures/cp1_ronda_5.png`. La cobertura de las 119 variables y todos sus códigos se muestra íntegra en la ficha correspondiente del notebook ejecutado; no se restringe a las variables anteriores.

## Ronda 6 — 2021

**Objetivo y método:** caracterizar esta ronda sin mezclar denominadores con otras. La frecuencia incluye faltantes; la edad continua utiliza solo valores válidos. El flujo sigue claves → entrevista directa → edad conocida → edad 60+.

La ronda 6 (2021) contiene 17,538 registros de 17,538 personas. Las entrevistas directas suman 14,484 (82.59% del total de la ronda), las de sustituto 1,255 (7.16%) y las de fallecimiento 1,799 (10.26%). La primera aparición se registra para 323 personas; 17,215 ya habían sido observadas y 1,100 reaparecen tras faltar a la ronda inmediatamente anterior. Primera aparición y entrevista de nueva persona son conceptos distintos y se calculan por separado.

La edad es válida en 15,729/17,538 registros: la mediana es 65.0 años y el intervalo intercuartílico 57.0–74.0. Se observan 5,247 registros menores de 60, 10,482 de 60 o más y 1,809 sin edad válida. El filtro directo 60+ conserva 9,424/17,538 (53.73%) y excluye 8,114. Las tablas de flujo distinguen entrevista, edad ausente y edad insuficiente.

 Se registran 10,092 mujeres (57.54% del total de la ronda).  Se registran 3,448 personas viudas (19.66% del total de la ronda).  Se registran 8,803 registros en localidades de 100 mil o más habitantes (50.19% del total de la ronda).  La mediana de edad cambia +2.0 años respecto a la ronda anterior; es una comparación de muestras observadas, no un cambio individual. 

Las distribuciones demográficas incluyen códigos especiales en el denominador total; la edad continua se resume únicamente entre valores válidos. Las diferencias entre rondas combinan envejecimiento, incorporaciones y selección por observación. No identifican cambios dentro de la misma persona ni efectos causales. Las entrevistas sobre fallecidos forman parte del seguimiento amplio y no son predictores directos contemporáneos. La tabla de pesos verifica disponibilidad, sin convertir su suma en un tamaño de muestra ni estimar todavía estadísticas poblacionales.

### Frecuencias demográficas, entrevista y año efectivo

| ronda | variable | categoria | n | denominador | porcentaje |
| --- | --- | --- | --- | --- | --- |
| 6 | tipent | Directa de seguimiento | 14336 | 17538 | 81.74 |
| 6 | tipent | Directa de nueva persona | 148 | 17538 | 0.84 |
| 6 | tipent | Sustituto de seguimiento | 1247 | 17538 | 7.11 |
| 6 | tipent | Sustituto de nueva persona | 8 | 17538 | 0.05 |
| 6 | tipent | Sobre fallecido | 1799 | 17538 | 10.26 |
| 6 | sexo | Hombre | 7446 | 17538 | 42.46 |
| 6 | sexo | Mujer | 10092 | 17538 | 57.54 |
| 6 | est_conyugal | Casado o en unión | 10295 | 17538 | 58.70 |
| 6 | est_conyugal | Separado o divorciado | 1278 | 17538 | 7.29 |
| 6 | est_conyugal | Viudo | 3448 | 17538 | 19.66 |
| 6 | est_conyugal | Soltero | 718 | 17538 | 4.09 |
| 6 | est_conyugal | .f | 1799 | 17538 | 10.26 |
| 6 | urbano | Menos de 100 mil residentes | 6936 | 17538 | 39.55 |
| 6 | urbano | 100 mil residentes o más | 8803 | 17538 | 50.19 |
| 6 | urbano | .f | 1799 | 17538 | 10.26 |
| 6 | edad_gru | 49 o menos | 472 | 17538 | 2.69 |
| 6 | edad_gru | 50–59 | 4775 | 17538 | 27.23 |
| 6 | edad_gru | 60–69 | 4548 | 17538 | 25.93 |
| 6 | edad_gru | 70–79 | 3974 | 17538 | 22.66 |
| 6 | edad_gru | 80 o más | 1960 | 17538 | 11.18 |
| 6 | edad_gru | .f | 1799 | 17538 | 10.26 |
| 6 | edad_gru | .d | 10 | 17538 | 0.06 |
| 6 | a_o_ent | 2021 | 10918 | 17538 | 62.25 |
| 6 | a_o_ent | 2022 | 4821 | 17538 | 27.49 |
| 6 | a_o_ent | .f | 1799 | 17538 | 10.26 |
| 6 | fallecido | No | 15739 | 17538 | 89.74 |
| 6 | fallecido | Sí | 1799 | 17538 | 10.26 |

### Año efectivo por tipo de entrevista

| ronda | tipo_entrevista | categoria | n | denominador | porcentaje |
| --- | --- | --- | --- | --- | --- |
| 6 | Directa de seguimiento | 2021 | 10144 | 14336 | 70.76 |
| 6 | Directa de seguimiento | 2022 | 4192 | 14336 | 29.24 |
| 6 | Directa de nueva persona | 2021 | 87 | 148 | 58.78 |
| 6 | Directa de nueva persona | 2022 | 61 | 148 | 41.22 |
| 6 | Sustituto de seguimiento | 2021 | 683 | 1247 | 54.77 |
| 6 | Sustituto de seguimiento | 2022 | 564 | 1247 | 45.23 |
| 6 | Sustituto de nueva persona | 2021 | 4 | 8 | 50.00 |
| 6 | Sustituto de nueva persona | 2022 | 4 | 8 | 50.00 |
| 6 | Sobre fallecido | .f | 1799 | 1799 | 100.00 |

### Exclusiones secuenciales

| ronda | filtro | antes | excluidos | despues | personas | denominador | porcentaje_conservado |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 6 | Claves válidas y únicas | 17538 | 0 | 17538 | 17538 | 17538 | 100.00 |
| 6 | Entrevista directa | 17538 | 3054 | 14484 | 14484 | 17538 | 82.59 |
| 6 | Edad conocida | 14484 | 0 | 14484 | 14484 | 17538 | 82.59 |
| 6 | Edad 60+ | 14484 | 5060 | 9424 | 9424 | 17538 | 53.73 |

### Alternativas de población

| ronda | muestra | registros | personas | denominador_registros |
| --- | --- | --- | --- | --- |
| 6 | Universo amplio | 17538 | 17538 | 17538 |
| 6 | 60+ por visita, cualquier entrevista | 10482 | 10482 | 17538 |
| 6 | Directas, cualquier edad | 14484 | 14484 | 17538 |
| 6 | Directas 60+ por visita | 9424 | 9424 | 17538 |
| 6 | 60+ en primera observación, seguimiento amplio | 3839 | 3839 | 17538 |
| 6 | 60+ en primera observación, directas | 2394 | 2394 | 17538 |
| 6 | Desde primera observación 60+, seguimiento amplio | 12063 | 12063 | 17538 |
| 6 | Desde primera observación 60+, directas | 9431 | 9431 | 17538 |
| 6 | Seis rondas, cualquier entrevista/edad | 6305 | 6305 | 17538 |
| 6 | Seis directas, cualquier edad | 3893 | 3893 | 17538 |
| 6 | Seis directas 60+ por visita | 964 | 964 | 17538 |

### Disponibilidad de factores individuales y de hogar

| ronda | variable | tipo_entrevista | denominador | validos | positivos | ceros | negativos | faltantes | min | mediana | max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 6 | factori_21 | Directa de seguimiento | 14336 | 14336 | 14336 | 0 | 0 | 0 | 13 | 817.00 | 116633 |
| 6 | factori_21 | Directa de nueva persona | 148 | 148 | 148 | 0 | 0 | 0 | 16 | 396.50 | 21517 |
| 6 | factori_21 | Sustituto de seguimiento | 1247 | 1247 | 1247 | 0 | 0 | 0 | 14 | 753.00 | 33452 |
| 6 | factori_21 | Sustituto de nueva persona | 8 | 8 | 8 | 0 | 0 | 0 | 55 | 261.50 | 2483 |
| 6 | factori_21 | Sobre fallecido | 1799 | 1799 | 1799 | 0 | 0 | 0 | 14 | 649.00 | 32900 |
| 6 | factorh_21 | Directa de seguimiento | 14336 | 14336 | 14336 | 0 | 0 | 0 | 26 | 761.50 | 98872 |
| 6 | factorh_21 | Directa de nueva persona | 148 | 148 | 148 | 0 | 0 | 0 | 34 | 751.00 | 28864 |
| 6 | factorh_21 | Sustituto de seguimiento | 1247 | 1247 | 1247 | 0 | 0 | 0 | 36 | 808.00 | 29714 |
| 6 | factorh_21 | Sustituto de nueva persona | 8 | 8 | 8 | 0 | 0 | 0 | 117 | 574.00 | 6482 |
| 6 | factorh_21 | Sobre fallecido | 1799 | 1799 | 1797 | 2 | 0 | 0 | 0 | 656.00 | 36911 |

### Cobertura y causas de faltantes en variables de integridad

| ronda | variable | tipo | n | denominador | porcentaje |
| --- | --- | --- | --- | --- | --- |
| 6 | cunicah | válido | 17538 | 17538 | 100.00 |
| 6 | np | válido | 17538 | 17538 | 100.00 |
| 6 | ronda | válido | 17538 | 17538 | 100.00 |
| 6 | tipent | válido | 17538 | 17538 | 100.00 |
| 6 | a_o_ent | válido | 15739 | 17538 | 89.74 |
| 6 | a_o_ent | .f | 1799 | 17538 | 10.26 |
| 6 | fallecido | válido | 17538 | 17538 | 100.00 |
| 6 | sexo | válido | 17538 | 17538 | 100.00 |
| 6 | edad | válido | 15729 | 17538 | 89.69 |
| 6 | edad | .f | 1799 | 17538 | 10.26 |
| 6 | edad | .d | 10 | 17538 | 0.06 |
| 6 | urbano | válido | 15739 | 17538 | 89.74 |
| 6 | urbano | .f | 1799 | 17538 | 10.26 |
| 6 | est_conyugal | válido | 15739 | 17538 | 89.74 |
| 6 | est_conyugal | .f | 1799 | 17538 | 10.26 |

La figura se regenera en `reports/figures/cp1_ronda_6.png`. La cobertura de las 119 variables y todos sus códigos se muestra íntegra en la ficha correspondiente del notebook ejecutado; no se restringe a las variables anteriores.

## Participación longitudinal

| rondas_observadas | personas | denominador_personas | porcentaje |
| --- | --- | --- | --- |
| 1 | 2025 | 27171 | 7.45 |
| 2 | 6635 | 27171 | 24.42 |
| 3 | 4445 | 27171 | 16.36 |
| 4 | 5589 | 27171 | 20.57 |
| 5 | 2172 | 27171 | 7.99 |
| 6 | 6305 | 27171 | 23.20 |

| ronda | primera_aparicion | ya_observadas | reaparecen_tras_ausencia | total |
| --- | --- | --- | --- | --- |
| 1 | 15186 | 0 | 0 | 15186 |
| 2 | 277 | 13973 | 0 | 14250 |
| 3 | 5912 | 12553 | 357 | 18465 |
| 4 | 650 | 15338 | 624 | 15988 |
| 5 | 4823 | 13426 | 383 | 18249 |
| 6 | 323 | 17215 | 1100 | 17538 |

| origen | destino | intervalo_nominal_anos | denominador_origen | continuan | no_observadas | ausentes_con_fallecimiento_previo | ausentes_sin_fallecimiento_previo | denominador_origen_vivas | fallecimiento_documentado_destino | retencion_porcentaje |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2 | 2 | 15186 | 13973 | 1213 | 0 | 1213 | 15186 | 542 | 92.01 |
| 2 | 3 | 9 | 14250 | 12196 | 2054 | 546 | 1508 | 13704 | 2685 | 85.59 |
| 3 | 4 | 3 | 18465 | 14714 | 3751 | 2741 | 1010 | 15723 | 1085 | 79.69 |
| 4 | 5 | 3 | 15988 | 13043 | 2945 | 1209 | 1736 | 14779 | 1091 | 81.58 |
| 5 | 6 | 3 | 18249 | 16115 | 2134 | 1135 | 999 | 17114 | 1616 | 88.31 |

| ronda | pares_observados | pares_con_anos_validos | min | mediana | max |
| --- | --- | --- | --- | --- | --- |
| 1 | 13973 | 13973 | 2.00 | 2.00 | 2.00 |
| 2 | 12196 | 9510 | 9.00 | 9.00 | 10.00 |
| 3 | 14714 | 13626 | 2.00 | 3.00 | 3.00 |
| 4 | 13043 | 11952 | 3.00 | 3.00 | 4.00 |
| 5 | 16115 | 14499 | 2.00 | 3.00 | 4.00 |

### Matriz agregada de personas compartidas

| ronda | R1 | R2 | R3 | R4 | R5 | R6 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 15186 | 13973 | 12336 | 9825 | 8127 | 7429 |
| 2 | 13973 | 14250 | 12196 | 9697 | 8044 | 7352 |
| 3 | 12336 | 12196 | 18465 | 14714 | 12581 | 11900 |
| 4 | 9825 | 9697 | 14714 | 15988 | 13043 | 12467 |
| 5 | 8127 | 8044 | 12581 | 13043 | 18249 | 16115 |
| 6 | 7429 | 7352 | 11900 | 12467 | 16115 | 17538 |

### Patrones de participación (1=observada, 0=ausente; orden 2001–2021)

| patron_2001_a_2021 | personas | denominador_personas | porcentaje |
| --- | --- | --- | --- |
| 111111 | 6305 | 27171 | 23.20 |
| 000011 | 4440 | 27171 | 16.34 |
| 001111 | 4134 | 27171 | 15.21 |
| 111000 | 2852 | 27171 | 10.50 |
| 110000 | 1408 | 27171 | 5.18 |
| 111100 | 1136 | 27171 | 4.18 |
| 111110 | 1078 | 27171 | 3.97 |
| 100000 | 811 | 27171 | 2.98 |
| 111101 | 433 | 27171 | 1.59 |
| 001101 | 426 | 27171 | 1.57 |
| 001100 | 404 | 27171 | 1.49 |
| 000111 | 396 | 27171 | 1.46 |
| 000010 | 383 | 27171 | 1.41 |
| 001000 | 376 | 27171 | 1.38 |
| 001110 | 370 | 27171 | 1.36 |
| 000001 | 323 | 27171 | 1.19 |
| 110111 | 270 | 27171 | 0.99 |
| 110100 | 172 | 27171 | 0.63 |
| 101111 | 159 | 27171 | 0.59 |
| 001011 | 135 | 27171 | 0.50 |
| 111011 | 117 | 27171 | 0.43 |
| 011111 | 115 | 27171 | 0.42 |
| 000101 | 95 | 27171 | 0.35 |
| 000100 | 89 | 27171 | 0.33 |
| 101000 | 81 | 27171 | 0.30 |
| 000110 | 70 | 27171 | 0.26 |
| 110101 | 63 | 27171 | 0.23 |
| 110110 | 61 | 27171 | 0.22 |
| 111010 | 52 | 27171 | 0.19 |
| 011000 | 49 | 27171 | 0.18 |
| 001010 | 48 | 27171 | 0.18 |
| 010000 | 43 | 27171 | 0.16 |
| 101100 | 41 | 27171 | 0.15 |
| 101110 | 36 | 27171 | 0.13 |
| 101101 | 29 | 27171 | 0.11 |
| 001001 | 19 | 27171 | 0.07 |
| 011100 | 19 | 27171 | 0.07 |
| 011110 | 17 | 27171 | 0.06 |
| 100100 | 14 | 27171 | 0.05 |
| 100111 | 14 | 27171 | 0.05 |
| 011101 | 12 | 27171 | 0.04 |
| 110011 | 12 | 27171 | 0.04 |
| 100110 | 9 | 27171 | 0.03 |
| 010111 | 8 | 27171 | 0.03 |
| 101011 | 7 | 27171 | 0.03 |
| 111001 | 6 | 27171 | 0.02 |
| 100101 | 5 | 27171 | 0.02 |
| 110001 | 5 | 27171 | 0.02 |
| 010100 | 4 | 27171 | 0.01 |
| 110010 | 3 | 27171 | 0.01 |
| 101010 | 3 | 27171 | 0.01 |
| 010101 | 3 | 27171 | 0.01 |
| 011010 | 3 | 27171 | 0.01 |
| 011011 | 2 | 27171 | 0.01 |
| 100001 | 2 | 27171 | 0.01 |
| 010110 | 1 | 27171 | 0.00 |
| 101001 | 1 | 27171 | 0.00 |
| 100011 | 1 | 27171 | 0.00 |
| 010001 | 1 | 27171 | 0.00 |

### Estados de entrevista en la siguiente ronda

| origen | destino | tipo_origen | estado_destino | n | denominador | porcentaje |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 2 | Directa de nueva persona | Directa de seguimiento | 11728 | 14154 | 82.86 |
| 1 | 2 | Directa de nueva persona | No observada | 1102 | 14154 | 7.79 |
| 1 | 2 | Directa de nueva persona | Sustituto de seguimiento | 888 | 14154 | 6.27 |
| 1 | 2 | Directa de nueva persona | Sobre fallecido | 435 | 14154 | 3.07 |
| 1 | 2 | Directa de nueva persona | Sustituto de nueva persona | 1 | 14154 | 0.01 |
| 1 | 2 | Sustituto de nueva persona | Directa de seguimiento | 580 | 1032 | 56.20 |
| 1 | 2 | Sustituto de nueva persona | Sustituto de seguimiento | 234 | 1032 | 22.67 |
| 1 | 2 | Sustituto de nueva persona | No observada | 111 | 1032 | 10.76 |
| 1 | 2 | Sustituto de nueva persona | Sobre fallecido | 107 | 1032 | 10.37 |
| 2 | 3 | Directa de seguimiento | Directa de seguimiento | 7983 | 12363 | 64.57 |
| 2 | 3 | Directa de seguimiento | Sobre fallecido | 2339 | 12363 | 18.92 |
| 2 | 3 | Directa de seguimiento | No observada | 1272 | 12363 | 10.29 |
| 2 | 3 | Directa de seguimiento | Sustituto de seguimiento | 769 | 12363 | 6.22 |
| 2 | 3 | Directa de nueva persona | Directa de seguimiento | 103 | 163 | 63.19 |
| 2 | 3 | Directa de nueva persona | No observada | 30 | 163 | 18.40 |
| 2 | 3 | Directa de nueva persona | Sobre fallecido | 18 | 163 | 11.04 |
| 2 | 3 | Directa de nueva persona | Sustituto de seguimiento | 12 | 163 | 7.36 |
| 2 | 3 | Sustituto de seguimiento | Directa de seguimiento | 481 | 1134 | 42.42 |
| 2 | 3 | Sustituto de seguimiento | Sobre fallecido | 322 | 1134 | 28.40 |
| 2 | 3 | Sustituto de seguimiento | No observada | 194 | 1134 | 17.11 |
| 2 | 3 | Sustituto de seguimiento | Sustituto de seguimiento | 137 | 1134 | 12.08 |
| 2 | 3 | Sustituto de nueva persona | Directa de seguimiento | 21 | 44 | 47.73 |
| 2 | 3 | Sustituto de nueva persona | No observada | 12 | 44 | 27.27 |
| 2 | 3 | Sustituto de nueva persona | Sobre fallecido | 6 | 44 | 13.64 |
| 2 | 3 | Sustituto de nueva persona | Sustituto de seguimiento | 5 | 44 | 11.36 |
| 2 | 3 | Sobre fallecido | No observada | 546 | 546 | 100.00 |
| 3 | 4 | Directa de seguimiento | Directa de seguimiento | 7417 | 8868 | 83.64 |
| 3 | 4 | Directa de seguimiento | Sobre fallecido | 714 | 8868 | 8.05 |
| 3 | 4 | Directa de seguimiento | Sustituto de seguimiento | 370 | 8868 | 4.17 |
| 3 | 4 | Directa de seguimiento | No observada | 367 | 8868 | 4.14 |
| 3 | 4 | Directa de nueva persona | Directa de seguimiento | 4833 | 5580 | 86.61 |
| 3 | 4 | Directa de nueva persona | No observada | 525 | 5580 | 9.41 |
| 3 | 4 | Directa de nueva persona | Sustituto de seguimiento | 126 | 5580 | 2.26 |
| 3 | 4 | Directa de nueva persona | Sobre fallecido | 96 | 5580 | 1.72 |
| 3 | 4 | Sustituto de seguimiento | Directa de seguimiento | 370 | 959 | 38.58 |
| 3 | 4 | Sustituto de seguimiento | Sustituto de seguimiento | 264 | 959 | 27.53 |
| 3 | 4 | Sustituto de seguimiento | Sobre fallecido | 255 | 959 | 26.59 |
| 3 | 4 | Sustituto de seguimiento | No observada | 70 | 959 | 7.30 |
| 3 | 4 | Sustituto de nueva persona | Directa de seguimiento | 183 | 316 | 57.91 |
| 3 | 4 | Sustituto de nueva persona | Sustituto de seguimiento | 65 | 316 | 20.57 |
| 3 | 4 | Sustituto de nueva persona | No observada | 48 | 316 | 15.19 |
| 3 | 4 | Sustituto de nueva persona | Sobre fallecido | 20 | 316 | 6.33 |
| 3 | 4 | Sobre fallecido | No observada | 2741 | 2742 | 99.96 |
| 3 | 4 | Sobre fallecido | Directa de seguimiento | 1 | 2742 | 0.04 |
| 4 | 5 | Directa de seguimiento | Directa de seguimiento | 10241 | 13254 | 77.27 |
| 4 | 5 | Directa de seguimiento | No observada | 1444 | 13254 | 10.89 |
| 4 | 5 | Directa de seguimiento | Sobre fallecido | 825 | 13254 | 6.22 |
| 4 | 5 | Directa de seguimiento | Sustituto de seguimiento | 744 | 13254 | 5.61 |
| 4 | 5 | Directa de nueva persona | Directa de seguimiento | 395 | 596 | 66.28 |
| 4 | 5 | Directa de nueva persona | No observada | 165 | 596 | 27.68 |
| 4 | 5 | Directa de nueva persona | Sustituto de seguimiento | 24 | 596 | 4.03 |
| 4 | 5 | Directa de nueva persona | Sobre fallecido | 12 | 596 | 2.01 |
| 4 | 5 | Sustituto de seguimiento | Sustituto de seguimiento | 285 | 884 | 32.24 |
| 4 | 5 | Sustituto de seguimiento | Sobre fallecido | 252 | 884 | 28.51 |
| 4 | 5 | Sustituto de seguimiento | Directa de seguimiento | 233 | 884 | 26.36 |
| 4 | 5 | Sustituto de seguimiento | No observada | 114 | 884 | 12.90 |
| 4 | 5 | Sustituto de nueva persona | Directa de seguimiento | 21 | 45 | 46.67 |
| 4 | 5 | Sustituto de nueva persona | No observada | 13 | 45 | 28.89 |
| 4 | 5 | Sustituto de nueva persona | Sustituto de seguimiento | 9 | 45 | 20.00 |
| 4 | 5 | Sustituto de nueva persona | Sobre fallecido | 2 | 45 | 4.44 |
| 4 | 5 | Sobre fallecido | No observada | 1209 | 1209 | 100.00 |
| 5 | 6 | Directa de seguimiento | Directa de seguimiento | 8873 | 11183 | 79.34 |
| 5 | 6 | Directa de seguimiento | Sobre fallecido | 1122 | 11183 | 10.03 |
| 5 | 6 | Directa de seguimiento | Sustituto de seguimiento | 649 | 11183 | 5.80 |
| 5 | 6 | Directa de seguimiento | No observada | 539 | 11183 | 4.82 |
| 5 | 6 | Directa de nueva persona | Directa de seguimiento | 4012 | 4603 | 87.16 |
| 5 | 6 | Directa de nueva persona | No observada | 355 | 4603 | 7.71 |
| 5 | 6 | Directa de nueva persona | Sobre fallecido | 128 | 4603 | 2.78 |
| 5 | 6 | Directa de nueva persona | Sustituto de seguimiento | 108 | 4603 | 2.35 |
| 5 | 6 | Sustituto de seguimiento | Directa de seguimiento | 364 | 1122 | 32.44 |
| 5 | 6 | Sustituto de seguimiento | Sobre fallecido | 352 | 1122 | 31.37 |
| 5 | 6 | Sustituto de seguimiento | Sustituto de seguimiento | 322 | 1122 | 28.70 |
| 5 | 6 | Sustituto de seguimiento | No observada | 84 | 1122 | 7.49 |
| 5 | 6 | Sustituto de nueva persona | Directa de seguimiento | 125 | 206 | 60.68 |
| 5 | 6 | Sustituto de nueva persona | Sustituto de seguimiento | 46 | 206 | 22.33 |
| 5 | 6 | Sustituto de nueva persona | No observada | 21 | 206 | 10.19 |
| 5 | 6 | Sustituto de nueva persona | Sobre fallecido | 14 | 206 | 6.80 |
| 5 | 6 | Sobre fallecido | No observada | 1135 | 1135 | 100.00 |

### Perfiles de quienes continúan o no se observan

Se comparan variables medidas en la ronda de origen entre participantes vivos en esa ronda. «Observada siguiente» puede incluir fallecimiento documentado. Las medias y medianas tienen N válido; las frecuencias incluyen faltantes y denominador del grupo.

| ronda | grupo | variable | categoria | n | denominador | porcentaje | media | mediana |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Observada siguiente | edad | continua | 13973 | 13973 | 100.00 | 61.19 | 60.00 |
| 1 | Observada siguiente | educacion | continua | 13954 | 13973 | 99.86 | 4.49 | 3.00 |
| 1 | Observada siguiente | sexo | Hombre | 5952 | 13973 | 42.60 | — | — |
| 1 | Observada siguiente | sexo | Mujer | 8021 | 13973 | 57.40 | — | — |
| 1 | Observada siguiente | urbano | Menos de 100 mil residentes | 5865 | 13973 | 41.97 | — | — |
| 1 | Observada siguiente | urbano | 100 mil residentes o más | 8108 | 13973 | 58.03 | — | — |
| 1 | Observada siguiente | est_conyugal | Casado o en unión | 9623 | 13973 | 68.87 | — | — |
| 1 | Observada siguiente | est_conyugal | Separado o divorciado | 1044 | 13973 | 7.47 | — | — |
| 1 | Observada siguiente | est_conyugal | Viudo | 2419 | 13973 | 17.31 | — | — |
| 1 | Observada siguiente | est_conyugal | Soltero | 484 | 13973 | 3.46 | — | — |
| 1 | Observada siguiente | est_conyugal | .m | 403 | 13973 | 2.88 | — | — |
| 1 | Observada siguiente | tipent | Directa de seguimiento | 0 | 13973 | 0.00 | — | — |
| 1 | Observada siguiente | tipent | Directa de nueva persona | 13052 | 13973 | 93.41 | — | — |
| 1 | Observada siguiente | tipent | Sustituto de seguimiento | 0 | 13973 | 0.00 | — | — |
| 1 | Observada siguiente | tipent | Sustituto de nueva persona | 921 | 13973 | 6.59 | — | — |
| 1 | Observada siguiente | tipent | Sobre fallecido | 0 | 13973 | 0.00 | — | — |
| 1 | No observada siguiente | edad | continua | 1213 | 1213 | 100.00 | 56.22 | 55.00 |
| 1 | No observada siguiente | educacion | continua | 1213 | 1213 | 100.00 | 6.35 | 6.00 |
| 1 | No observada siguiente | sexo | Hombre | 551 | 1213 | 45.42 | — | — |
| 1 | No observada siguiente | sexo | Mujer | 662 | 1213 | 54.58 | — | — |
| 1 | No observada siguiente | urbano | Menos de 100 mil residentes | 364 | 1213 | 30.01 | — | — |
| 1 | No observada siguiente | urbano | 100 mil residentes o más | 849 | 1213 | 69.99 | — | — |
| 1 | No observada siguiente | est_conyugal | Casado o en unión | 889 | 1213 | 73.29 | — | — |
| 1 | No observada siguiente | est_conyugal | Separado o divorciado | 100 | 1213 | 8.24 | — | — |
| 1 | No observada siguiente | est_conyugal | Viudo | 116 | 1213 | 9.56 | — | — |
| 1 | No observada siguiente | est_conyugal | Soltero | 55 | 1213 | 4.53 | — | — |
| 1 | No observada siguiente | est_conyugal | .m | 53 | 1213 | 4.37 | — | — |
| 1 | No observada siguiente | tipent | Directa de seguimiento | 0 | 1213 | 0.00 | — | — |
| 1 | No observada siguiente | tipent | Directa de nueva persona | 1102 | 1213 | 90.85 | — | — |
| 1 | No observada siguiente | tipent | Sustituto de seguimiento | 0 | 1213 | 0.00 | — | — |
| 1 | No observada siguiente | tipent | Sustituto de nueva persona | 111 | 1213 | 9.15 | — | — |
| 1 | No observada siguiente | tipent | Sobre fallecido | 0 | 1213 | 0.00 | — | — |
| 2 | Observada siguiente | edad | continua | 12189 | 12196 | 99.94 | 62.79 | 61.00 |
| 2 | Observada siguiente | educacion | continua | 12122 | 12196 | 99.39 | 4.32 | 3.00 |
| 2 | Observada siguiente | sexo | Hombre | 5186 | 12196 | 42.52 | — | — |
| 2 | Observada siguiente | sexo | Mujer | 7010 | 12196 | 57.48 | — | — |
| 2 | Observada siguiente | urbano | Menos de 100 mil residentes | 5394 | 12196 | 44.23 | — | — |
| 2 | Observada siguiente | urbano | 100 mil residentes o más | 6802 | 12196 | 55.77 | — | — |
| 2 | Observada siguiente | est_conyugal | Casado o en unión | 8680 | 12196 | 71.17 | — | — |
| 2 | Observada siguiente | est_conyugal | Separado o divorciado | 820 | 12196 | 6.72 | — | — |
| 2 | Observada siguiente | est_conyugal | Viudo | 2251 | 12196 | 18.46 | — | — |
| 2 | Observada siguiente | est_conyugal | Soltero | 444 | 12196 | 3.64 | — | — |
| 2 | Observada siguiente | est_conyugal | .d | 1 | 12196 | 0.01 | — | — |
| 2 | Observada siguiente | tipent | Directa de seguimiento | 11091 | 12196 | 90.94 | — | — |
| 2 | Observada siguiente | tipent | Directa de nueva persona | 133 | 12196 | 1.09 | — | — |
| 2 | Observada siguiente | tipent | Sustituto de seguimiento | 940 | 12196 | 7.71 | — | — |
| 2 | Observada siguiente | tipent | Sustituto de nueva persona | 32 | 12196 | 0.26 | — | — |
| 2 | Observada siguiente | tipent | Sobre fallecido | 0 | 12196 | 0.00 | — | — |
| 2 | No observada siguiente | edad | continua | 1504 | 1508 | 99.73 | 61.83 | 59.50 |
| 2 | No observada siguiente | educacion | continua | 1492 | 1508 | 98.94 | 6.44 | 6.00 |
| 2 | No observada siguiente | sexo | Hombre | 641 | 1508 | 42.51 | — | — |
| 2 | No observada siguiente | sexo | Mujer | 867 | 1508 | 57.49 | — | — |
| 2 | No observada siguiente | urbano | Menos de 100 mil residentes | 383 | 1508 | 25.40 | — | — |
| 2 | No observada siguiente | urbano | 100 mil residentes o más | 1125 | 1508 | 74.60 | — | — |
| 2 | No observada siguiente | est_conyugal | Casado o en unión | 1009 | 1508 | 66.91 | — | — |
| 2 | No observada siguiente | est_conyugal | Separado o divorciado | 127 | 1508 | 8.42 | — | — |
| 2 | No observada siguiente | est_conyugal | Viudo | 294 | 1508 | 19.50 | — | — |
| 2 | No observada siguiente | est_conyugal | Soltero | 78 | 1508 | 5.17 | — | — |
| 2 | No observada siguiente | tipent | Directa de seguimiento | 1272 | 1508 | 84.35 | — | — |
| 2 | No observada siguiente | tipent | Directa de nueva persona | 30 | 1508 | 1.99 | — | — |
| 2 | No observada siguiente | tipent | Sustituto de seguimiento | 194 | 1508 | 12.86 | — | — |
| 2 | No observada siguiente | tipent | Sustituto de nueva persona | 12 | 1508 | 0.80 | — | — |
| 2 | No observada siguiente | tipent | Sobre fallecido | 0 | 1508 | 0.00 | — | — |
| 3 | Observada siguiente | edad | continua | 14696 | 14713 | 99.88 | 64.23 | 64.00 |
| 3 | Observada siguiente | educacion | continua | 14657 | 14713 | 99.62 | 5.47 | 6.00 |
| 3 | Observada siguiente | sexo | Hombre | 6148 | 14713 | 41.79 | — | — |
| 3 | Observada siguiente | sexo | Mujer | 8565 | 14713 | 58.21 | — | — |
| 3 | Observada siguiente | urbano | Menos de 100 mil residentes | 6351 | 14713 | 43.17 | — | — |
| 3 | Observada siguiente | urbano | 100 mil residentes o más | 8362 | 14713 | 56.83 | — | — |
| 3 | Observada siguiente | est_conyugal | Casado o en unión | 10209 | 14713 | 69.39 | — | — |
| 3 | Observada siguiente | est_conyugal | Separado o divorciado | 1111 | 14713 | 7.55 | — | — |
| 3 | Observada siguiente | est_conyugal | Viudo | 2717 | 14713 | 18.47 | — | — |
| 3 | Observada siguiente | est_conyugal | Soltero | 676 | 14713 | 4.59 | — | — |
| 3 | Observada siguiente | tipent | Directa de seguimiento | 8501 | 14713 | 57.78 | — | — |
| 3 | Observada siguiente | tipent | Directa de nueva persona | 5055 | 14713 | 34.36 | — | — |
| 3 | Observada siguiente | tipent | Sustituto de seguimiento | 889 | 14713 | 6.04 | — | — |
| 3 | Observada siguiente | tipent | Sustituto de nueva persona | 268 | 14713 | 1.82 | — | — |
| 3 | Observada siguiente | tipent | Sobre fallecido | 0 | 14713 | 0.00 | — | — |
| 3 | No observada siguiente | edad | continua | 1005 | 1010 | 99.50 | 60.22 | 58.00 |
| 3 | No observada siguiente | educacion | continua | 1002 | 1010 | 99.21 | 8.36 | 8.00 |
| 3 | No observada siguiente | sexo | Hombre | 447 | 1010 | 44.26 | — | — |
| 3 | No observada siguiente | sexo | Mujer | 563 | 1010 | 55.74 | — | — |
| 3 | No observada siguiente | urbano | Menos de 100 mil residentes | 249 | 1010 | 24.65 | — | — |
| 3 | No observada siguiente | urbano | 100 mil residentes o más | 761 | 1010 | 75.35 | — | — |
| 3 | No observada siguiente | est_conyugal | Casado o en unión | 701 | 1010 | 69.41 | — | — |
| 3 | No observada siguiente | est_conyugal | Separado o divorciado | 120 | 1010 | 11.88 | — | — |
| 3 | No observada siguiente | est_conyugal | Viudo | 143 | 1010 | 14.16 | — | — |
| 3 | No observada siguiente | est_conyugal | Soltero | 46 | 1010 | 4.55 | — | — |
| 3 | No observada siguiente | tipent | Directa de seguimiento | 367 | 1010 | 36.34 | — | — |
| 3 | No observada siguiente | tipent | Directa de nueva persona | 525 | 1010 | 51.98 | — | — |
| 3 | No observada siguiente | tipent | Sustituto de seguimiento | 70 | 1010 | 6.93 | — | — |
| 3 | No observada siguiente | tipent | Sustituto de nueva persona | 48 | 1010 | 4.75 | — | — |
| 3 | No observada siguiente | tipent | Sobre fallecido | 0 | 1010 | 0.00 | — | — |
| 4 | Observada siguiente | edad | continua | 13041 | 13043 | 99.98 | 66.50 | 66.00 |
| 4 | Observada siguiente | educacion | continua | 12915 | 13043 | 99.02 | 5.50 | 6.00 |
| 4 | Observada siguiente | sexo | Hombre | 5411 | 13043 | 41.49 | — | — |
| 4 | Observada siguiente | sexo | Mujer | 7632 | 13043 | 58.51 | — | — |
| 4 | Observada siguiente | urbano | Menos de 100 mil residentes | 5862 | 13043 | 44.94 | — | — |
| 4 | Observada siguiente | urbano | 100 mil residentes o más | 7181 | 13043 | 55.06 | — | — |
| 4 | Observada siguiente | est_conyugal | Casado o en unión | 8705 | 13043 | 66.74 | — | — |
| 4 | Observada siguiente | est_conyugal | Separado o divorciado | 1250 | 13043 | 9.58 | — | — |
| 4 | Observada siguiente | est_conyugal | Viudo | 2558 | 13043 | 19.61 | — | — |
| 4 | Observada siguiente | est_conyugal | Soltero | 530 | 13043 | 4.06 | — | — |
| 4 | Observada siguiente | tipent | Directa de seguimiento | 11810 | 13043 | 90.55 | — | — |
| 4 | Observada siguiente | tipent | Directa de nueva persona | 431 | 13043 | 3.30 | — | — |
| 4 | Observada siguiente | tipent | Sustituto de seguimiento | 770 | 13043 | 5.90 | — | — |
| 4 | Observada siguiente | tipent | Sustituto de nueva persona | 32 | 13043 | 0.25 | — | — |
| 4 | Observada siguiente | tipent | Sobre fallecido | 0 | 13043 | 0.00 | — | — |
| 4 | No observada siguiente | edad | continua | 1734 | 1736 | 99.88 | 63.35 | 62.00 |
| 4 | No observada siguiente | educacion | continua | 1691 | 1736 | 97.41 | 7.83 | 7.00 |
| 4 | No observada siguiente | sexo | Hombre | 731 | 1736 | 42.11 | — | — |
| 4 | No observada siguiente | sexo | Mujer | 1005 | 1736 | 57.89 | — | — |
| 4 | No observada siguiente | urbano | Menos de 100 mil residentes | 467 | 1736 | 26.90 | — | — |
| 4 | No observada siguiente | urbano | 100 mil residentes o más | 1269 | 1736 | 73.10 | — | — |
| 4 | No observada siguiente | est_conyugal | Casado o en unión | 1157 | 1736 | 66.65 | — | — |
| 4 | No observada siguiente | est_conyugal | Separado o divorciado | 223 | 1736 | 12.85 | — | — |
| 4 | No observada siguiente | est_conyugal | Viudo | 271 | 1736 | 15.61 | — | — |
| 4 | No observada siguiente | est_conyugal | Soltero | 85 | 1736 | 4.90 | — | — |
| 4 | No observada siguiente | tipent | Directa de seguimiento | 1444 | 1736 | 83.18 | — | — |
| 4 | No observada siguiente | tipent | Directa de nueva persona | 165 | 1736 | 9.50 | — | — |
| 4 | No observada siguiente | tipent | Sustituto de seguimiento | 114 | 1736 | 6.57 | — | — |
| 4 | No observada siguiente | tipent | Sustituto de nueva persona | 13 | 1736 | 0.75 | — | — |
| 4 | No observada siguiente | tipent | Sobre fallecido | 0 | 1736 | 0.00 | — | — |
| 5 | Observada siguiente | edad | continua | 16098 | 16115 | 99.89 | 64.37 | 63.00 |
| 5 | Observada siguiente | educacion | continua | 15980 | 16115 | 99.16 | 6.44 | 6.00 |
| 5 | Observada siguiente | sexo | Hombre | 6774 | 16115 | 42.04 | — | — |
| 5 | Observada siguiente | sexo | Mujer | 9341 | 16115 | 57.96 | — | — |
| 5 | Observada siguiente | urbano | Menos de 100 mil residentes | 7306 | 16115 | 45.34 | — | — |
| 5 | Observada siguiente | urbano | 100 mil residentes o más | 8809 | 16115 | 54.66 | — | — |
| 5 | Observada siguiente | est_conyugal | Casado o en unión | 11147 | 16115 | 69.17 | — | — |
| 5 | Observada siguiente | est_conyugal | Separado o divorciado | 1224 | 16115 | 7.60 | — | — |
| 5 | Observada siguiente | est_conyugal | Viudo | 2919 | 16115 | 18.11 | — | — |
| 5 | Observada siguiente | est_conyugal | Soltero | 825 | 16115 | 5.12 | — | — |
| 5 | Observada siguiente | tipent | Directa de seguimiento | 10644 | 16115 | 66.05 | — | — |
| 5 | Observada siguiente | tipent | Directa de nueva persona | 4248 | 16115 | 26.36 | — | — |
| 5 | Observada siguiente | tipent | Sustituto de seguimiento | 1038 | 16115 | 6.44 | — | — |
| 5 | Observada siguiente | tipent | Sustituto de nueva persona | 185 | 16115 | 1.15 | — | — |
| 5 | Observada siguiente | tipent | Sobre fallecido | 0 | 16115 | 0.00 | — | — |
| 5 | No observada siguiente | edad | continua | 996 | 999 | 99.70 | 60.77 | 58.00 |
| 5 | No observada siguiente | educacion | continua | 980 | 999 | 98.10 | 9.17 | 9.00 |
| 5 | No observada siguiente | sexo | Hombre | 424 | 999 | 42.44 | — | — |
| 5 | No observada siguiente | sexo | Mujer | 575 | 999 | 57.56 | — | — |
| 5 | No observada siguiente | urbano | Menos de 100 mil residentes | 284 | 999 | 28.43 | — | — |
| 5 | No observada siguiente | urbano | 100 mil residentes o más | 715 | 999 | 71.57 | — | — |
| 5 | No observada siguiente | est_conyugal | Casado o en unión | 691 | 999 | 69.17 | — | — |
| 5 | No observada siguiente | est_conyugal | Separado o divorciado | 101 | 999 | 10.11 | — | — |
| 5 | No observada siguiente | est_conyugal | Viudo | 128 | 999 | 12.81 | — | — |
| 5 | No observada siguiente | est_conyugal | Soltero | 79 | 999 | 7.91 | — | — |
| 5 | No observada siguiente | tipent | Directa de seguimiento | 539 | 999 | 53.95 | — | — |
| 5 | No observada siguiente | tipent | Directa de nueva persona | 355 | 999 | 35.54 | — | — |
| 5 | No observada siguiente | tipent | Sustituto de seguimiento | 84 | 999 | 8.41 | — | — |
| 5 | No observada siguiente | tipent | Sustituto de nueva persona | 21 | 999 | 2.10 | — | — |
| 5 | No observada siguiente | tipent | Sobre fallecido | 0 | 999 | 0.00 | — | — |

En R1 (2001), entre vivos en origen, la edad media es 61.19 años entre quienes se observan en la ronda siguiente (N válido=13,973/13,973) y 56.22 entre quienes no se observan (N válido=1,213/1,213). La diferencia observada es 4.97 años.

En R2 (2003), entre vivos en origen, la edad media es 62.79 años entre quienes se observan en la ronda siguiente (N válido=12,189/12,196) y 61.83 entre quienes no se observan (N válido=1,504/1,508). La diferencia observada es 0.96 años.

En R3 (2012), entre vivos en origen, la edad media es 64.23 años entre quienes se observan en la ronda siguiente (N válido=14,696/14,713) y 60.22 entre quienes no se observan (N válido=1,005/1,010). La diferencia observada es 4.01 años.

En R4 (2015), entre vivos en origen, la edad media es 66.50 años entre quienes se observan en la ronda siguiente (N válido=13,041/13,043) y 63.35 entre quienes no se observan (N válido=1,734/1,736). La diferencia observada es 3.14 años.

En R5 (2018), entre vivos en origen, la edad media es 64.37 años entre quienes se observan en la ronda siguiente (N válido=16,098/16,115) y 60.77 entre quienes no se observan (N válido=996/999). La diferencia observada es 3.60 años.

La composición por edad difiere entre grupos en cada transición; por ello una restricción de continuidad puede modificar el perfil analítico. La observación posterior incluye entrevistas sobre fallecidos y los intervalos difieren: estos contrastes no estiman supervivencia ni efectos de edad sobre abandono. La selección final exige revisión de perfiles por sexo, educación, localidad y entrevista en las tablas.

## Comparación global de poblaciones

| muestra | registros | personas | denominador_registros | denominador_personas |
| --- | --- | --- | --- | --- |
| Universo amplio | 99676 | 27171 | 99676 | 27171 |
| 60+ por visita, cualquier entrevista | 56004 | 18754 | 99676 | 27171 |
| Directas, cualquier edad | 85248 | 26572 | 99676 | 27171 |
| Directas 60+ por visita | 50841 | 18158 | 99676 | 27171 |
| 60+ en primera observación, seguimiento amplio | 35048 | 9079 | 99676 | 27171 |
| 60+ en primera observación, directas | 26450 | 8751 | 99676 | 27171 |
| Desde primera observación 60+, seguimiento amplio | 62522 | 18754 | 99676 | 27171 |
| Desde primera observación 60+, directas | 50904 | 18158 | 99676 | 27171 |
| Seis rondas, cualquier entrevista/edad | 37830 | 6305 | 99676 | 27171 |
| Seis directas, cualquier edad | 23358 | 3893 | 99676 | 27171 |
| Seis directas 60+ por visita | 5784 | 964 | 99676 | 27171 |

### Composición y magnitud de la restricción de balance
La muestra de seis directas 60+ conserva 964/18,158 personas (5.31% de las personas del candidato directo 60+ no balanceado). Incluye 581 mujeres/964 (60.27%). En la muestra abierta, las mujeres son 3,667/6,812 (53.83%) en 2001 y 5,252/9,424 (55.73%) en 2021: el panel estricto tiene 6.44 y 4.54 puntos porcentuales más, respectivamente. Esto evidencia selección de composición, sin cuantificar representatividad ni causalidad. Las otras dimensiones y once alternativas se comparan con denominadores específicos en composicion_muestras.

## Comparación y recomendación provisional

Se propone conservar el universo amplio no balanceado para estudiar observación, sustitución y fallecimiento, y usar **entrevistas directas con edad ≥60 en cada visita** como candidata para predictores medidos directamente. Su entrada es abierta: admite a quienes cumplen 60 en rondas posteriores y no exige seis visitas. El seguimiento comienza en la elegibilidad observada; ninguna condición retrospectiva utiliza supervivencia futura. La disponibilidad de outcomes y pares temporales se definirá en CP3, sin asumir que todos estos registros producen una etiqueta.

La cohorte con 60+ en la primera observación original responde a una pregunta distinta: excluye a quienes ingresaron más jóvenes, aunque después envejecieran dentro del estudio. La alternativa «desde primera observación 60+» permite conservar el seguimiento sobre fallecidos y visitas con edad faltante, pero no atribuye edad ni predictores directos a esos registros. Las diferencias con 60+ por visita requieren revisar inconsistencias de edad y faltantes, sin relleno automático. Los paneles balanceados condicionan a continuidad, modo de entrevista y supervivencia; se reservan a sensibilidad. Su composición se tabula por muestra y ronda en el notebook y en los agregados locales.

La retención se mide entre rondas nominalmente consecutivas con denominador en la ronda de origen. La presencia incluye entrevistas sobre fallecidos: la tabla separa los ausentes ya registrados como fallecidos de los ausentes sin ese antecedente. Estos últimos no son necesariamente no respuesta definitiva ni muerte. Una reaparición exige presencia previa, ausencia inmediatamente anterior y presencia actual. El número total de primeras apariciones no equivale a categorías de muestra nueva del cuestionario.

**Limitaciones y revisión humana.** Hay registros después de un fallecimiento y variación de sexo válido; se mantienen sin rectificar. También se auditan descensos de edad entre observaciones válidas. Resolverlos requiere consultar fuente original o documentación del proveedor; no se eliminan personas por iniciativa del análisis. La no observación no identifica su causa, y las comparaciones de perfiles en t describen selección sin identificar causalidad. Los intervalos nominales 2, 9, 3, 3 y 3 años impiden comparar porcentajes brutos de salida como tasas anuales. Los intervalos efectivos tienen denominador de pares con ambos años válidos; entrevistas sobre fallecidos pueden carecer de año efectivo. No hay evidencia aquí de anticipación predictiva.

**Conclusión parcial.** Los conteos y tipos de entrevista concuerdan con la fuente; la restricción de seis entrevistas reduce fuertemente la población. La muestra abierta preserva diversidad de trayectorias, pero requiere definir estimando, tratamiento de sustitutos, fallecimiento y observación selectiva. La aprobación de la muestra, las anomalías y la ponderación sigue pendiente; CP2 no se inicia y no se realiza unión de pensiones.


## Reproducción y artefactos

`/opt/miniconda3/envs/myenv/bin/python scripts/run_cp1.py` reconstruye tablas JSON agregadas y siete figuras en reports/ (ignorado). Ejecutar el notebook 02 genera todas las tablas y narrativas. El ejecutado se conserva localmente en `reports/notebooks/02_construccion_muestra_ejecutado.ipynb`; el fuente versionado tiene outputs vacíos por política vigente de CI. No se publican claves, observaciones individuales ni el original.
