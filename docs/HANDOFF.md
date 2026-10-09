# Entrega de contexto para futuras personas y agentes

## En 90 segundos
- Tema: predicción longitudinal de vulnerabilidad económica futura de personas adultas mayores en México.
- Pregunta principal: ¿qué detectan salud, cognición y funcionalidad antes de que el patrimonio muestre vulnerabilidad? ¿Cuánto afecta la desaparición del seguimiento?
- Base: ENASEMsimple (`simpleMHAS.dta`), longitudinal, 6 rondas 2001-2021. **NO** subir el `.dta` al repositorio público.
- Repositorio: notebooks narrativos bajo `notebooks/`; funciones en `src/tesis_enasem`; pruebas en `tests/`; decisiones en `docs/DECISIONES.md`; resultados probados en `docs/RESULTADOS.md`.
- Estado: scaffold programático; no se han entrenado aún los modelos de tesis. CP0 validado; commit inicial `adfe426` publicado con CI aprobado. Ver docs/CP0_VERIFICACION.md. Se realizó una auditoría estructural preliminar del archivo en `docs/AUDITORIA_INICIAL.md`.
- Acción siguiente: CP1, auditar persona/ronda, entrevistas directas vs sustituto, fallecimiento y las diferentes muestras. Construir flujo de muestra antes de filtrar panel completo.

## Lecturas de ingreso
`README.md` → `AGENTS.md` → `docs/PREGUNTA_Y_ALCANCE.md` → `docs/ROADMAP.md` → `docs/FUENTES.md` → `docs/DECISIONES.md` → `docs/RESULTADOS.md`.

## Cómo trabajar
1. Crear rama `feat/cpX-nombre`, no publicar microdatos.
2. Agregar prueba para cada nueva función; `python -m pytest -q`.
3. No duplicar lógica entre notebooks. Los notebooks deben demostrar funciones reales, sin placeholders opacos.
4. Editar `docs/ROADMAP.md` al completar checkpoint y añadir cifras solo después de ejecutarlas en datos reales.
5. Registrar compromisos analíticos y decisiones *antes* de mirar resultados que podrían sesgarlos.
6. PR con: qué cambió, cómo verificarlo, tablas/figuras reproducibles, limitaciones.

## Riesgos de sesgo y datos
- Edad >=60 aplicada a todas las rondas no equivale a >=60 en la primera observación.
- Panel de 6 entrevistas directas condiciona a supervivencia y continuidad; no adoptar como muestra principal sin justificación.
- `orientacion` no existe en ronda 1; `serial7` solo desde 2015; actividades en su mayoría desde 2012.
- Patrimonio puede ser negativo: transformar con `asinh`; comparar a precios constantes antes de afirmar variaciones reales.
- Evitar leakage por persona, por año y por cálculo de umbral Q1 con el test.

## Infraestructura cloud
Activar `.venv` y ejecutar la instalación y pruebas de README.md.
En este entorno el home no es escribible: antes de iniciar Jupyter aplicar las
rutas locales de configuración, datos y runtime documentadas en README.md.

## Bloqueos conocidos
No hay bloqueo de lectura GitHub: el commit inicial y su CI están disponibles.
Los microdatos no están presentes en este entorno; no ejecutar ni marcar CP1+
como completos hasta contar con los datos autorizados y evidencia real.
