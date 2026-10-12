# Plan metodológico: EDA exhaustivo por ronda e integración futura de pensiones

**Estado:** requisitos de investigación y plan de implementación; NO equivale a un análisis ejecutado o concluido.

## Prioridad y separación de fases

- **CP1 — Auditoría del panel y muestra:** determinar cuántas personas y registros hay por ronda, sus entrevistas, cobertura, elegibilidad, cambios de participación y attrición. Identificar denominadores y validar reglas de inclusión.
- **CP2 — EDA univariado, bivariado y longitudinal por ronda:** describir *todas* las variables seleccionadas, disponibles en cada ola, con tablas, visualizaciones, faltantes, relaciones y comparación entre olas.
- **Fase futura — Integración de archivos completos de ENASEM, comenzando por pensiones:** planificar e inventariar, pero NO fusionar ni redefinir el outcome hasta identificar archivos, claves, universo, codificación y unidad de medida.

Nunca declarar completo un checkpoint con plantillas, código que no corrió con el microdato o resultados supuestos.

## Convenciones para todas las tablas y gráficas

- Rondas nominales: `ronda` = 1 (2001), 2 (2003), 3 (2012), 4 (2015), 5 (2018), 6 (2021). Reportar `a_o_ent` por separado: algunas entrevistas efectivas son de 2013, 2019 o 2022. No igualar las dos variables.
- Una fila corresponde a una persona-ronda/entrevista. Persona única por `cunicah` y `np`, después de validar identificadores, nulos y duplicados. **Registros persona-ronda NO son personas únicas en el periodo completo.**
- `tipent` 1 = directa seguimiento; 2 = directa muestra nueva; 3 = sustituto seguimiento; 4 = sustituto muestra nueva; 5 = sobre fallecido. Especificar categorías y no llamar todas «personas entrevistadas directamente».
- Conteos absolutos (número de personas/registros) primero; proporciones (%) como complemento con el denominador explícito. Mostrar ponderados y no ponderados separados; un total expandido no debe llamarse número de personas observadas.
- Si la variable no fue formulada en una ola, mostrar **no disponible/no formulada**, no cero ni «ausencia clínica». Distinguir `StataMissingValue` de valores numéricos antes de aplicar operaciones, etiquetas, agrupaciones o imputación.
- Gráficas en español, ejes y unidades claros, números absolutos visibles, comparaciones con colores constantes por ola (paleta `BrBG`/`BrBG_r`), etiquetas de categorías legibles y leyenda `Ronda N (año), n=...`. No generar figuras saturadas.
- Cada tabla, figura e interpretación debe identificar población, definición de edad, `tipent`, ronda/año, denominador y exclusiones aplicadas. No publicar identificadores individuales ni microdatos en GitHub.

## CP1 — Desglose obligatorio por ronda

Preparar tablas generales y seis fichas separadas, una para cada ronda:

1. **Estructura de registros**: número de filas, personas únicas y registros con clave ausente, duplicados persona-ronda y discrepancias.
2. **Tipo de entrevista**: totales de `tipent` 1,2,3,4,5; directas (1+2), sustituto (3+4), sobre fallecidos (5); muestra nueva y de seguimiento. Mostrar N y % sobre total de esa ronda.
3. **Cronología efectiva**: distribución de `a_o_ent` y, cuando sea útil, `mes_ent` entre los tipos de entrevista; intervalos desiguales entre mediciones.
4. **Elegibilidad demográfica**: conteos antes/después de edad >=60, por sexo, grupos de edad y demás controles pertinentes. Separar «edad >=60 en la observación» y «cohorte que ingresa con >=60», sin decidir equivalencia.
5. **Flujo de muestra**: N antes/después de cada exclusión (edad, directa, faltantes de claves, etc.), con porcentajes y denominadores, sin perder el universo amplio para estudios de attrición.
6. **Participación longitudinal**: personas nuevas, personas observadas previamente, número de rondas por persona, patrones de participación, retención entre rondas consecutivas observadas, entradas tardías y causas documentables de no observación. No asumir muerte por simple ausencia en la ronda siguiente.
7. **Valores faltantes y cobertura**: por variable y ronda, válidos, tipos especiales de faltantes, no preguntado, sustituto, fallecimiento, negativas/no sabe y disponibilidad definida por cuestionario.
8. **Ponderación**: disponibilidad de factor individual correspondiente a la ronda y advertencia de que ponderadores transversales no son automáticamente adecuados para comparaciones longitudinales.

**Tablas mínimas:** matriz rondas × tipos de entrevista; tabla de flujo de exclusiones por ronda; matriz de participantes por pares de rondas; patrones de participación; elegibilidad y faltantes por ronda.

**Criterio de aceptación CP1:** conteos reconciliados con fuente y categorías; ninguna duplicación accidental; poblaciones comparadas transparentemente; al menos una propuesta justificada de población principal no balanceada y panel completo solo como sensibilidad hasta aprobación. No decidir el estimando sin revisión.

## CP2 — EDA exhaustivo y específico por ola

Trabajar en `notebooks/03_eda_univariado.ipynb` y `notebooks/04_eda_longitudinal.ipynb`; funciones reutilizables en `src/tesis_enasem/` con tests.

**Dimensiones a revisar:** demografía, patrimonio/socioeconomía, salud física, salud mental, funcionalidad, cognición y participación/actividad, según `docs/VARIABLES.md` y libro de códigos. Revisar disponibilidad REAL por ola y tipo de entrevista.

**Para cada variable, por cada ronda donde exista:**
- Definición, codificación, unidad, restricciones de universo y año disponible, tomada del diccionario.
- Número de observaciones elegibles, válidas, ausentes por motivo y porcentaje sobre denominador declarado.
- Categóricas: tabla `categoría × ronda` de frecuencias y proporciones, barras con categorías y N etiquetados; no incluir categorías inexistentes.
- Continuas: N, media, mediana, DE, mínimo, máximo, cuantiles, ceros, negativos cuando apliquen, distribución/histograma o densidad por año/ronda, valores extremos.
- Comparación conjunta entre rondas con paleta BrBG fija y tabla longitudinal; distinguir cambio de composición muestral de cambio dentro de la misma persona.
- Permitir filtros configurables (edad, sexo, estado conyugal, urbano, entrevistas, número de olas, ponderación) aplicados de forma consistente y visible en cada resultado.
- EDA bivariado/por pares: Spearman para variables ordinales/continuas y V de Cramér para categóricas, **dentro de cada ola**, sin apilar personas-ronda para reportar una sola asociación transversal.
- Para `imp_neto`: revisar origen, unidades monetarias, comparabilidad entre olas, negativos y ceros; conservar valor original y evaluar `asinh` como transformación secundaria. No afirmar variaciones reales sin comprobación de deflactación.
- Para IMC y patrimonio: comparar distribuciones, no solo barras de promedio; siempre aclarar población, año, rango y transformación.

**Criterio de aceptación CP2:** tablas/gráficas para cada dimensión según cobertura, comparación por ronda, faltantes explicados, reproducibilidad local y explicación interpretativa cautelosa; al menos tres hipótesis contrastables derivadas del EDA.

## Integración FUTURA de pensiones y archivos originales ENASEM

**Motivación:** `imp_neto` es patrimonio neto; no mide por sí mismo flujos de pensiones, jubilación, transferencias ni suficiencia de ingresos. Una medición complementaria de protección económica y previsional puede fortalecer controles, perfiles y sensibilidad del outcome.

**Antes de cualquier merge:**
1. Identificar y descargar de fuentes autorizadas los archivos originales y libros de códigos de cada ronda que contengan preguntas sobre pensión/jubilación; no asumir que los nombres o conceptos son homogéneos en todos los años.
2. Crear inventario por archivo y ola: nombre original, variable, etiqueta, categorías, población a la que se preguntó, temporalidad, unidad de monto, frecuencia del pago, tipo de pensión y códigos de faltantes; distinguir pensión propia, de cónyuge, supervivencia, ocupacional, pública/no contributiva u otras únicamente cuando los archivos lo permitan.
3. Verificar claves por fuente y ola. `cunicah`+`np` se mantienen en simpleMHAS y posibilitan vinculación, **pero** las claves reales y la cardinalidad de cada archivo completo deben auditarse antes de unir. Si la fuente es persona-ola, añadir ola/año; si es hogar, no adjudicarla a un individuo sin justificación.
4. Validar unicidad y cardinalidad explícitamente (`validate='one_to_one'` o `many_to_one` según fuente); detectar duplicación de registros, no vinculados y discrepancias. Generar tabla de tasas de emparejamiento por ronda.
5. Armonizar disponibilidad temporal, tipo de respuesta, unidad monetaria, periodicidad, precios, cambios de preguntas y faltantes no estructurales; jamás convertir indisponible en «no tiene pensión».
6. Mantener variables originales trazables y nuevas variables derivadas con prefijo `pension_` o nomenclatura documentada; separar monto, recepción, cobertura y tipo. Evaluar sensibilidad de resultados y evitar fuga temporal de información.
7. Ejecutar la integración en entorno autorizado con datos locales. No publicar archivos ENASEM originales ni bases fusionadas en el repositorio público.

**Estado:** propuesta futura pendiente de inventario de fuentes y decisión metodológica; no se ha realizado integración alguna.

## Entrega a Codex y GitHub

- Trabajar localmente con `data/raw/simpleMHAS.dta`, solo lectura.
- Solicitar primero CP1; CP2 después de revisar conteos, muestra y cobertura.
- Entregar notebooks narrativos con tablas/figuras visibles, funciones en `src`, pruebas con datos sintéticos, documentación de decisiones, `git status` claro y reporte de qué se ejecutó realmente.
- Registrar resultados empíricos solo como agregados en `docs/RESULTADOS.md` y pendientes en `docs/HANDOFF.md`.
