"""Presenta tablas existentes de CP1 y amplía solo el diagnóstico de anomalías."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text, read_project_bytes

import hashlib
import json
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_path('', 'src')))

from tesis_enasem.audit_report import markdown_table, wave_interpretation, followup_interpretation
from tesis_enasem.config import ROUND_TO_YEAR
from tesis_enasem.cp1_review import investigate_anomalies, plot_anomalies, review_transitions
from tesis_enasem.io import load_stata


def render_review(tables: dict[str, pd.DataFrame], anomalies: dict[str, pd.DataFrame],
                  metadata: dict[str, object]) -> str:
    """Redacta evidencia medida y límites; no modifica decisiones metodológicas."""
    sections: list[str] = []

    def add_table(title: str, table: pd.DataFrame, explanation: str = '') -> None:
        sections.extend([f'### {title}', markdown_table(table), explanation])

    sections.append('''# CP1 — informe académico de revisión

**Estado:** evidencia descriptiva para revisión humana; sin aprobación de una muestra predictiva ni avance a CP2. Fecha: 2026-10-11. Rama local: `feat/cp1-auditoria`.

## 1. Descripción general y alcance

**Introducción.** CP1 examina la integridad y la población longitudinal disponible antes de definir etiquetas, horizontes o modelos de vulnerabilidad económica. La referencia descriptiva es toda la población registrada en `simpleMHAS.dta`: no se filtra por edad, entrevista o número de rondas. Esta referencia responde a la instrucción de la autora y no equivale a seleccionar una muestra principal para predicción.

**Fuente y método.** Se reutilizan las tablas agregadas de la auditoría ya ejecutada, cuya huella SHA-256 se coteja con el archivo local antes de construir este informe. La única ampliación analítica corresponde al diagnóstico solicitado de anomalías. El libro ENASEMsimple v2 (enero de 2025), cuadro 1 y apéndice 1, respalda nombres, codificaciones y totales por ronda; sus notas de las páginas 6–8 documentan la revisión de sexo y los faltantes especiales. Véase [inventario de fuentes](FUENTES.md). Ningún registro original se modifica o elimina.

**Denominadores.** Un registro es una persona-ronda. Una persona única se identifica mediante `cunicah` + `np`; la clave compuesta con `ronda` es única en este archivo. Los porcentajes demográficos incluyen todos los registros de su ronda, también los faltantes. Los estadísticos continuos usan únicamente valores numéricos válidos y declaran su N. En las transiciones, el denominador es la ronda de origen o su modalidad, según indique la tabla. Los porcentajes se redondean a dos decimales y pueden sumar 99.99 o 100.01.

**Alcance inferencial.** Se presentan frecuencias observadas sin ponderación, no estimaciones representativas de la población mexicana. El universo registrado no contiene necesariamente todos los intentos de contacto ni toda la población objetivo. Una entrevista sobre fallecido es información sobre una persona fallecida aportada por un informante, y se conserva como registro; no se denomina entrevista directa. La ausencia de un registro no prueba fallecimiento ni pérdida definitiva.''')
    add_table('Estructura verificada', tables['estructura'],
              'Se conservan 99,676 registros de 27,171 personas y 119 columnas originales. No hay claves faltantes ni duplicados persona-ronda. Esta verificación no garantiza que todos los valores de una historia individual sean correctos.')
    add_table('Identificadores y tiempo', pd.DataFrame([
        ['cunicah + np', 'Clave de persona', 'Enlace longitudinal interno; nunca se publica su contenido'],
        ['ronda', 'Onda nominal 1–6', 'Calendario nominal: 2001, 2003, 2012, 2015, 2018 y 2021'],
        ['a_o_ent', 'Año efectivo de entrevista', 'Puede diferir del nominal y tener faltantes especiales'],
        ['tipent / fallecido', 'Modalidad / indicador', 'Coinciden en la clasificación contemporánea de fallecimiento'],
        ['ron_pat', 'Patrón del proveedor', 'Complemento de la matriz de presencia calculada; no es identificador'],
    ], columns=['Variable', 'Función', 'Interpretación']),
              'La organización es longitudinal en formato largo, con 1–6 registros por persona. Los intervalos nominales son 2, 9, 3, 3 y 3 años; no deben confundirse con duración efectiva ni con tasas anuales de retención.')
    add_table('Conteos generales por ronda', tables['rondas'])
    sections.append('''**Variables disponibles y cobertura.** Las 119 columnas incluyen identificadores y seguimiento, demografía, educación, locality, factores individuales/de hogar, salud física y mental, cognición, funcionalidad, participación, empleo y patrimonio (`imp_neto`). El inventario exhaustivo por nombre y causa de faltante está en las tablas `faltantes` del notebook y en [CP1_RESULTADOS.md](CP1_RESULTADOS.md). Tener una columna no implica que se haya preguntado en todas las rondas o modalidades; no se anticipa aquí la integración futura de pensiones.

**Tratamiento de faltantes.** Se carga Stata conservando códigos especiales: `.f` (reportado fallecido), `.p` (información no incluida en entrevista por sustituto), `.w` (pregunta no incluida en esa ronda), además de `.d`, `.r`, `.s`, `.i`, `.m`, `.e`, `.x` y otros códigos presentes. Se conservan como categorías en las tablas. Solo para resúmenes numéricos se genera una vista con faltantes, sin sustituir el original. Un número de celdas `.f` no es un número de personas fallecidas.

**Conclusión parcial.** La base permite describir la totalidad registrada y contrastar subpoblaciones posteriormente. La unicidad de claves facilita el seguimiento, pero las alertas de consistencia exigen verificación antes de convertir las trayectorias en ejemplos predictivos.'''.replace('locality', 'localidad'))

    sections.append('## 2. Análisis exhaustivo por ronda')
    for wave, year in ROUND_TO_YEAR.items():
        r = tables['rondas'].set_index('ronda').loc[wave]
        n = int(r.registros)
        sections.append(f'''## 2.{wave}. Ronda {wave}: {year}

**Introducción y metodología.** Esta sección describe los {n:,} registros y {int(r.personas):,} personas de {year}, sin restricciones de edad o modalidad. Cada distribución categórica conserva su denominador completo N={n:,}; las categorías especiales señalan causas de ausencia de información. Las tablas son agregados reales reutilizados de CP1. Los resultados se interpretan como composición de la población registrada y no como cambios causales o exclusivamente dentro de las mismas personas.''')
        add_table('Registros y personas', tables['rondas'].loc[tables['rondas'].ronda.eq(wave)])
        demo = tables['demografia'].loc[tables['demografia'].ronda.eq(wave)]
        labels = [('tipent', 'Tipos de entrevista'), ('sexo', 'Sexo'),
                  ('est_conyugal', 'Estado conyugal'), ('edu_gru', 'Educación: categorías del proveedor'),
                  ('educacion', 'Educación: años exactos y faltantes'), ('urbano', 'Localidad')]
        for variable, label in labels:
            add_table(label, demo.loc[demo.variable.eq(variable), ['categoria', 'n', 'denominador', 'porcentaje']])
        add_table('Edad: grupos ampliados', tables['edad_grupos'].loc[tables['edad_grupos'].ronda.eq(wave)])
        add_table('Edad: estadísticos de valores válidos', tables['edad'].loc[tables['edad'].ronda.eq(wave)])
        add_table('Escolaridad: estadísticos de valores válidos', tables['educacion'].loc[tables['educacion'].ronda.eq(wave)])
        add_table('Primera aparición, seguimiento y reaparición', tables['entradas'].loc[tables['entradas'].ronda.eq(wave)],
                  'Primera aparición + ya observadas = total. Las reapariciones pertenecen a ya observadas y no deben sumarse otra vez. La primera aparición en este archivo no es necesariamente un nuevo ingreso al estudio ni coincide siempre con tipent de nueva persona.')
        if wave > 1:
            add_table('Ausencias respecto a la ronda anterior', tables['seguimiento_ronda'].loc[tables['seguimiento_ronda'].ronda.eq(wave)],
                      'El denominador es el total de la ronda anterior: continuadas + ausentes = origen. Ausencia con fallecimiento previo se identifica aquí por la entrevista sobre fallecido en la ronda inmediatamente anterior; no expresa todos los antecedentes históricos posibles.')
        add_table('Participación total de los presentes: 1–6 rondas', tables['participacion_ronda'].loc[tables['participacion_ronda'].ronda.eq(wave)],
                  'Es una descripción retrospectiva de presencia en 2001–2021, incluidas modalidades sobre fallecidos. No se usa como variable predictora en una fecha anterior.')
        add_table('Año efectivo de entrevista por modalidad', tables['cronologia'].loc[tables['cronologia'].ronda.eq(wave)],
                  'Los porcentajes de esta tabla usan como denominador cada modalidad, no el total de la ronda. Un código .f en el año no proporciona la fecha de muerte.')
        coverage = tables['faltantes'].loc[tables['faltantes'].ronda.eq(wave)]
        key_vars = ['edad', 'sexo', 'est_conyugal', 'educacion', 'edu_gru', 'urbano', 'a_o_ent', 'a_o_nac', 'imp_neto']
        add_table('Cobertura de variables demográficas, tiempo y patrimonio', coverage.loc[coverage.variable.isin(key_vars)],
                  'Cada variable reconcilia válido + causas de faltante = N de la ronda. La auditoría completa de las 119 variables permanece visible en la celda de esta ronda del notebook ejecutado y en CP1_RESULTADOS.md.')
        weights = tables['pesos'].loc[tables['pesos'].ronda.eq(wave)]
        add_table('Disponibilidad de ponderadores por modalidad', weights.drop(columns=['min', 'mediana', 'max']),
                  'Un factor numérico, incluso positivo, no prueba aplicabilidad a todas las modalidades. Los ceros se conservan y ninguna tabla demográfica de este informe se pondera automáticamente. No se tratan factores transversales como pesos longitudinales.')
        sections.append(f'![Distribuciones de la ronda {year}](../reports/figures/cp1_ronda_{wave}.png)')
        sections.append(wave_interpretation(tables, wave).replace('### Resultados y modalidades de registro', '### Interpretación académica: resultados y modalidades'))

    sections.append('''## 3. Comparación longitudinal de toda la población

**Introducción y metodología.** Se sigue a todas las claves únicas, cualquiera que sea edad o modalidad. Una presencia es cualquier registro persona-ronda. Las intersecciones muestran claves compartidas sin publicarlas. Las transiciones consecutivas parten de todo el origen; la información sobre fallecidos permanece visible. Las incorporaciones se identifican por primera presencia y las reapariciones por presencia previa, ausencia inmediata anterior y nuevo registro. No se infiere causa de ausencia a partir de ese patrón.''')
    add_table('Cantidad de rondas por persona', tables['numero_rondas'],
              'Las seis categorías suman 27,171 personas y, al multiplicar cada frecuencia por su número de rondas, se recuperan 99,676 registros. Las 6,305 personas con seis rondas son 23.20% del universo, no necesariamente seis entrevistas directas. Tener pocas rondas puede reflejar entrada tardía, fallecimiento, ausencia o cierre de observación, no únicamente abandono.')
    add_table('Entradas y reapariciones por ronda', tables['entradas'],
              'Después de 2001 se observan 11,985 primeras apariciones. Las incorporaciones de 2012 y 2018 contribuyen a cambios de composición. Las 357, 624, 383 y 1,100 reapariciones de 2012, 2015, 2018 y 2021 prueban que al menos algunas ausencias son temporales en términos de registro; no establecen la razón del intervalo ausente.')
    trans = review_transitions(tables)
    patterns = tables['patrones']
    add_table('Retención, ausencias y retornos posteriores', trans[[
        'ano_origen', 'ano_destino', 'intervalo_nominal_anos', 'denominador_origen', 'continuan',
        'retencion_porcentaje', 'no_observadas', 'no_observadas_porcentaje',
        'ausentes_con_fallecimiento_previo', 'ausentes_sin_fallecimiento_previo',
        'ausentes_con_reaparicion_posterior', 'ausentes_con_reaparicion_posterior_porcentaje',
        'ausentes_sin_reaparicion_observada_hasta_2021']],
        'Las tasas 92.01%, 85.59%, 79.69%, 81.58% y 88.31% describen intervalos de distinta longitud, por lo que no se comparan como tasas anuales. Los retornos posteriores son un subconjunto de las ausencias, calculado con los patrones agregados; contar cero después de 2021 refleja el límite de observación, no ausencia definitiva. Los ausentes sin fallecimiento previo no tienen causa identificada: no se renombran como abandonos comprobados.')
    add_table('Fallecimiento documentado en destino entre quienes no tenían entrevista sobre fallecido en origen', trans[[
        'ano_origen', 'ano_destino', 'denominador_origen_vivas', 'fallecimiento_documentado_destino']],
        'El denominador identifica registros no clasificados sobre fallecidos en el origen, no una certificación externa de supervivencia. Los 542, 2,685, 1,085, 1,091 y 1,616 registros documentados en destino no son el total de entrevistas sobre fallecidos de cada ronda, pues ese total puede incluir entradas o reapariciones. No se estima una tasa de mortalidad.')
    add_table('Matriz agregada de participación: personas compartidas', tables['intersecciones'],
              'La diagonal es el total de cada ronda; cada celda externa cuenta personas con registros en ambas rondas, cualquiera que sea modalidad. Por ejemplo, 7,429 personas aparecen en 2001 y 2021, pero solo 6,305 aparecen en todas las rondas. No se publica la matriz individual.')
    add_table('Todos los patrones de presencia, 2001 → 2021', patterns,
              'Cada posición corresponde a una de las seis rondas; 1 indica presencia y 0 ausencia. Son patrones agregados de participación, no identificadores. Un patrón con huecos distingue ausencia temporal de presencia continua. No informa por sí mismo modalidad o causa de ausencia.')
    for origin, destination in zip(trans.origen, trans.destino):
        state = tables['estados'].loc[tables['estados'].origen.eq(origin)]
        add_table(f'Transición de modalidades: {ROUND_TO_YEAR[origin]} → {ROUND_TO_YEAR[destination]}',
                  state.drop(columns=['origen', 'destino']),
                  'Cada porcentaje se calcula entre personas de la modalidad de origen indicada. No observada incluye ausencias; sobre fallecido es una presencia de tipo distinto a directa o sustituto. Las entradas sin registro en origen están en la tabla de primeras apariciones y no se mezclan en este denominador.')
    sections.append('![Seguimiento longitudinal agregado](../reports/figures/cp1_participacion.png)')
    sections.append(followup_interpretation(tables))
    sections.append('''**Conclusión parcial.** La composición entre rondas combina envejecimiento, entradas y observación selectiva. La diferencia entre presentes y ausentes exige sensibilidad a atrición y supervivencia; el panel completo condiciona a información futura. Estos resultados sustentan la auditoría del universo antes de elegir una población predictiva, y no aprueban todavía esa elección.''')

    sections.append('''## 4. Investigación de anomalías

**Introducción y metodología.** Las alertas originales se reproducen en memoria con el archivo local intacto, se examinan indicadores complementarios y se publican solo agregados. No se muestran claves, fechas de nacimiento ni historias individuales de los casos raros. La detección indica contradicción observable, no adjudica automáticamente error a una fila ni demuestra su causa.''')
    add_table('Reconciliación y denominadores del diagnóstico', anomalies['resumen'])
    sections.append('''### 4.1. Tres registros posteriores a un fallecimiento registrado

**Detección exacta.** Por persona se obtiene la primera ronda con `tipent = 5`; se marcan los registros de rondas estrictamente posteriores a esa primera ronda. Se detectan **3 registros de una sola persona**. Esa misma persona aporta la alerta de fallecimiento repetido. No se trata de tres personas ni de duplicados persona-ronda.

**Resultado comprobado e interpretación.** Dos registros posteriores son directos y uno es nuevamente sobre fallecido. En el archivo completo hay cero discrepancias contemporáneas entre `tipent = 5` y `fallecido = 1`: la contradicción reside en la secuencia temporal, aunque ambas variables concuerden en cada ronda. El año efectivo ausente de una entrevista sobre fallecido no permite reconstruir una fecha exacta de muerte.''')
    add_table('Modalidad de los registros posteriores; sin trayectoria individual', anomalies['posteriores_modalidad'],
              '**Hipótesis, no causas comprobadas.** Podría existir una clasificación incorrecta en el maestro de seguimiento, un problema de enlace de identidad o una revisión de estatus no reflejada uniformemente. También debe verificarse el significado de la repetición de entrevista sobre fallecido. **Verificaciones pendientes:** contrastar las claves internamente con el maestro, modalidades originales, versiones/fe de erratas y documentación de fecha/estatus de muerte. Esta tarea no integra archivos completos ni corrige o elimina los registros.')
    sections.append('''### 4.2. Una persona con sexo inconsistente

**Detección exacta.** Se cuentan códigos numéricos válidos distintos de `sexo` dentro de cada persona, ignorando faltantes. Una persona tiene más de uno: su historia contiene dos registros directos, con códigos 1 y 2. No hay mayoría que permita elegir un valor mediante moda.

**Interpretación y fuente.** La nota de ENASEMsimple v2, páginas 6–7, explica que el proveedor revisó sexo mediante validación de discrepancias de las variables originales `sex_xx` del maestro de seguimiento. El caso residual medido justifica revisar la versión y trazabilidad de esa validación; no prueba cuál registro es incorrecto ni permite inferir una causa individual. **Verificaciones pendientes:** comparar `sexo` construido con las variables originales de ambas entrevistas y su validación, revisar versiones y enlace de claves. No se sustituye un código por el otro ni se publica la secuencia individual.

### 4.3. Doscientos veintiséis pares con edad decreciente

**Detección exacta.** Se ordena cada persona por ronda y se resta la edad del registro observado inmediatamente anterior. Se evalúa el par solo si ambas edades son numéricas válidas. Una ronda sin registro puede saltarse; una edad faltante en un registro presente interrumpe la comparación y no se reemplaza por una edad válida más antigua. Entre 72,505 pares observados, 65,031 son evaluables y 7,474 no. Hay **226 pares decrecientes (0.35% de los evaluables), correspondientes a 225 personas (0.83% de las 27,171)**: 224 personas aportan un par y una aporta dos.

**Resultados comprobados.** Los 212 pares entre rondas nominales consecutivas y 14 separados por una ronda ausente muestran que la alerta no se limita al seguimiento continuo. Todos los 226 pares tienen año efectivo creciente y año de nacimiento válido sin cambios. El código de nacimiento puede variar entre rondas según el diccionario; su igualdad en estos pares es un resultado empírico, no una validación independiente de su veracidad.''')
    for name, title in [('edad_destino', 'Descensos por año nominal de destino'),
                        ('edad_saltos', 'Separación en rondas observadas'),
                        ('edad_magnitud', 'Magnitud del descenso'),
                        ('edad_estadisticos', 'Estadísticos de la magnitud, en años'),
                        ('edad_pares_por_persona', 'Número de pares decrecientes por persona afectada'),
                        ('edad_modalidad', 'Modalidades de los pares decrecientes'),
                        ('edad_compatibilidad', 'Compatibilidad aproximada con nacimiento y año efectivo')]:
        add_table(title, anomalies[name])
    sections.append('''**Interpretación estadística.** El descenso mediano es 3 años y el máximo 66. De los pares, 178 son directa → directa, 16 directa → sustituto, 26 sustituto → directa y 6 sustituto → sustituto; por ello no puede atribuirse toda la anomalía al informante sustituto. En 48 pares se pasa de edad registrada ≥60 a <60, lo que puede modificar la elegibilidad por visita si no se valida antes.

Para explorar la coherencia se contrasta cada edad con el intervalo aproximado `[a_o_ent − a_o_nac − 1, a_o_ent − a_o_nac]`, sin imputar ni usarlo como corrección. En 169 pares la edad anterior es incompatible y la actual compatible; en 48 sucede lo contrario, y en 9 ambas son incompatibles. Ningún par tiene ambas compatibles. Este contraste depende de la exactitud de los años declarados y no certifica una fecha de nacimiento. Con años efectivos crecientes y nacimiento estable, un cumpleaños por sí solo no explica una disminución de edad.

**Hipótesis y verificaciones pendientes.** Son posibles errores de respuesta, captura, derivación de `edad`, revisiones históricas o enlace. Deben cotejarse edad creada, año/mes efectivos y nacimiento con las variables y reglas originales; no se identifica aquí cuál valor debe prevalecer. No se impone monotonicidad, ni se reemplaza edad por una reconstrucción de nacimiento, ni se excluyen casos. La prueba de descenso tampoco valida todos los incrementos no negativos: no descarta aumentos implausibles o errores de edad que mantengan el orden.

![Diagnóstico agregado de edad](../reports/figures/cp1_anomalias_edad.png)

**Conclusión parcial.** Las alertas son reproducibles y sus denominadores están precisados. Sus causas y reglas de tratamiento siguen pendientes de validación documental y aprobación de la autora. Las cifras descriptivas conservan los registros originales.''')

    sections.append('''## 5. Comparación de muestras sin selección principal

**Introducción y metodología.** Cada alternativa se aplica independientemente al universo completo, después de describirlo. Edad ≥60 por visita no equivale a entrada a 60+. Directa corresponde solo a códigos 1–2. El panel no balanceado permite 1–6 rondas y coincide aquí con todo el universo; el panel completo exige seis presencias de cualquier edad/modalidad, salvo que se explicite una restricción adicional. Esta comparación no aprueba una muestra principal.

En el periodo, las personas conservadas son la unión de las claves que mantienen al menos un registro: no se suman personas por ronda. En una ronda, por la unicidad verificada, registros y personas coinciden también en cada alternativa; ambas columnas se conservan para que el denominador sea explícito. Los filtros por visita pueden conservar una persona en una ronda y excluirla en otra.''')
    add_table('Alternativas: registros y personas únicos de todo el periodo', tables['muestras'],
              'Los denominadores globales son 99,676 registros y 27,171 personas. Directas 60+ conserva 50,841 registros/18,158 personas; seis presencias conserva 37,830/6,305, mientras seis directas conserva 23,358/3,893 y seis directas 60+ conserva 5,784/964. No son alternativas metodológicamente equivalentes.')
    for wave, year in ROUND_TO_YEAR.items():
        add_table(f'Conservados y excluidos en {year}: todas las alternativas',
                  tables['muestras_ronda'].loc[tables['muestras_ronda'].ronda.eq(wave)].drop(columns='ronda'),
                  'En cada fila: conservados + excluidos = denominador original, tanto para registros como para personas. Los porcentajes corresponden a ese denominador original de la ronda.')
    sections.append('''**Interpretación estadística y conclusión parcial.** La alternativa de 60+ por visita conserva 56,004 registros y 18,754 personas; el filtro de directas conserva 85,248 registros y 26,572 personas. Exigir seis presencias reduce a 23.20% las personas del periodo y excluye tanto entradas tardías como historias incompletas. Exigir seis directas 60+ reduce aún más el universo y condiciona a continuidad futura, supervivencia y modalidad. La selección puede alterar edad, escolaridad, viudez y localidad; las tablas completas de composición por alternativa están en `composicion_muestras` del notebook y en CP1_RESULTADOS.md. Ninguna alternativa se interpreta como representativa por defecto. Para una tesis prospectiva, pertenecer al panel balanceado futuro no puede usarse sin reconocer esa selección.

## 6. Conclusiones para revisión y puntos pendientes

**Conclusiones comprobadas.** CP1 preserva todo el universo local y reconcilia claves, rondas y modalidades. La magnitud de los menores de 60, las entradas tardías, las ausencias temporales y las entrevistas sobre fallecidos descarta interpretar todas las filas como entrevistas directas de adultos de 60+. La variación entre rondas refleja composición y seguimiento además de envejecimiento. Los faltantes estructurales y la cobertura desigual deben distinguirse de falta de respuesta antes de imputar. Se han precisado las alertas; sus causas no se han probado.

**Revisión humana pendiente, sin modificar decisiones vigentes:**

1. Validar las conclusiones descriptivas y considerar suficiente la evidencia para cerrar CP1.
2. Definir estimando, criterio de entrada/edad y modalidad admisible para la muestra predictiva; 60+ permanece una candidata posterior.
3. Aprobar un protocolo de verificación y tratamiento de anomalías después de contrastarlas con fuentes originales; no aprobar correcciones por intuición.
4. Definir cómo se tratarán sustitutos, fallecimiento, ausencia temporal y atrición en etiquetas/horizontes y análisis de sensibilidad.
5. Resolver el alcance de ponderación y representatividad, distinguiendo factores transversales de seguimiento longitudinal.

La eventual autorización de CP2 es una decisión posterior. Este informe no crea etiquetas, integra pensiones, entrena modelos, publica cambios ni realiza merge.

## 7. Consulta en VS Code y reproducción

Abrir `docs/CP1_INFORME_REVISION.md` y usar **Markdown: Open Preview to the Side** para leer este informe y sus figuras locales. Abrir `reports/notebooks/02_construccion_muestra_ejecutado.ipynb` con el visor de Jupyter: contiene todas las tablas de cada ronda, cobertura de las 119 variables, transiciones, muestras/composición, ocho figuras y el diagnóstico agregado de anomalías. La configuración permite mostrar todas las filas; si VS Code contrae una salida grande, expandirla o abrir su visor de datos. No mostrar el objeto `raw` ni matrices individuales.

El fuente reproducible es `notebooks/02_construccion_muestra.ipynb`, con salidas vacías según CI; usar kernel **myenv** y **Run All**. El generador de este informe es `scripts/build_cp1_review.py`: reutiliza JSON agregados existentes y verifica la huella del original antes de ampliar las anomalías. No reconstruye la auditoría general. Los reportes y figuras bajo `reports/` son artefactos locales ignorados por Git; los enlaces de figuras requieren esos artefactos. También puede consultarse [CP1_TABLAS_RONDAS.md](CP1_TABLAS_RONDAS.md) para comparación compacta, y [CP1_RESULTADOS.md](CP1_RESULTADOS.md) para todas las tablas agregadas originales.

Comando del informe: `/opt/miniconda3/envs/myenv/bin/python scripts/build_cp1_review.py`. Comprobaciones: `python -m pytest -q` y `python scripts/validate_notebooks.py`. La bitácora de ejecución y resultados de validación está en [HANDOFF.md](HANDOFF.md). No se publican identificadores o microdatos.''')
    sections.append(f'**Trazabilidad:** SHA-256 local verificado: `{metadata["sha256_datos"]}`. Tablas originales de la ejecución de {metadata["fecha"]}.')
    return '\n\n'.join(sections) + '\n'


def main() -> None:
    """Verifica procedencia, reutiliza agregados y genera el informe de revisión."""
    directory = project_path('', 'reports/tables')
    metadata = json.loads(read_project_text(directory / 'cp1_ejecucion.json'))
    raw_path = project_path('', 'data/raw/simpleMHAS.dta')
    digest = hashlib.sha256(read_project_bytes(raw_path)).hexdigest()
    if digest != metadata['sha256_datos']:
        raise ValueError('El archivo local no coincide con la ejecución auditada; no reutilizar cifras.')
    tables = {path.stem.removeprefix('cp1_'): pd.read_json(path, orient='table')
              for path in directory.glob('cp1_*.json')
              if path.name != 'cp1_ejecucion.json' and not path.name.startswith('cp1_anomalias_')}
    raw = load_stata(raw_path, preserve_missing=True)
    anomalies = investigate_anomalies(raw)
    measured = anomalies['resumen'].set_index('control').n
    for new, old in [('registros_posteriores_fallecimiento', 'registros_despues_de_fallecimiento'),
                     ('personas_sexo_inconsistente', 'personas_con_sexo_valido_inconsistente'),
                     ('pares_edad_decreciente', 'pares_con_edad_decreciente')]:
        if measured[new] != metadata['consistencia'][old]:
            raise ValueError(f'No se reconcilia la alerta original: {old}')
    for name, table in anomalies.items():
        table.to_json(directory / f'cp1_anomalias_{name}.json', orient='table', indent=2, force_ascii=False)
    plt.close(plot_anomalies(anomalies, project_path('', 'reports/figures')))
    target = project_path('', 'docs/CP1_INFORME_REVISION.md')
    write_project_text(target, render_review(tables, anomalies, metadata), encoding='utf-8')
    print(f'Informe generado con tablas existentes: {target.relative_to(ROOT)}')
    print(anomalies['resumen'].to_string(index=False))


if __name__ == '__main__':
    main()
