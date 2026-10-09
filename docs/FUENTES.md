# Fuentes y criterios de trazabilidad

**Fuente primaria de datos**: Estudio Nacional de Salud y Envejecimiento en México (ENASEM): https://enasem.org/

**Diccionario de referencia**: ENASEMsimple/simpleMHAS, Documento del Proyecto y Libro de Códigos, versión 2, enero de 2025 (PDF oficial aportado al proyecto, no versionado).

**Rondas nominales**: 2001, 2003, 2012, 2015, 2018 y 2021. `ronda` es la ola; `a_o_ent` es el año real de entrevista (algunas entrevistas son en 2013, 2019 o 2022). Nunca confundir ambos.

**`imp_neto`** es patrimonio neto de persona y cónyuge, si lo hay; no es ingreso anual ni mide por sí solo pobreza monetaria. Para comparaciones intertemporales comprobar deflactación antes de establecer un umbral absoluto.

**Ponderaciones**: `factori_01`, `factori_03`, ... `factori_21` son factores individuales por ola; los pesos de hogar son `factorh_XX`. La ponderación de una muestra longitudinal y el ajuste por attrición no equivalen a aplicar factores transversales sin más.

**Variables sin cobertura homogénea**: `orientacion` no está en la ronda 1 (2001); `serial7` solo en rondas 4 a 6 (2015+); gran parte de las actividades `asiste_cursos`, `cruci_rompe`, etc. tienen datos desde ronda 3 (2012+). Asegurarse de no confundir *no formulado* (`.w`) con *no* (=0).

**Entrevistas**: `tipent` 1/2 son directas (seguimiento/nueva); 3/4 sustituto; 5 sobre fallecido. Excluir 3/4/5 de la muestra de predictores directos puede sesgar selección. Conservar un panel amplio para atrición.

**Faltantes especiales**: `.p` sustituto, `.f` fallecimiento, `.w` no preguntado en esa ronda, además de `.d`, `.r`, `.s`, `.i`, `.m`, etc. Conviene cargar con `convert_missing=True` para auditar códigos; convertir luego a NaN para funciones numéricas.

**Prioridad**: contrastar todo cambio de definición con el libro de códigos; no inventar cobertura ni supuestos.
