# Entrega de contexto para futuras personas y agentes

## En 90 segundos
- Tema: predicción longitudinal de vulnerabilidad económica futura de personas adultas mayores en México.
- Pregunta principal: ¿qué detectan salud, cognición y funcionalidad antes de que el patrimonio muestre vulnerabilidad? ¿Cuánto afecta la desaparición del seguimiento?
- Base: ENASEMsimple (`simpleMHAS.dta`), longitudinal, 6 rondas 2001-2021. **NO** subir el `.dta` al repositorio público.
- Repositorio: notebooks narrativos bajo `notebooks/`; funciones en `src/tesis_enasem`; pruebas en `tests/`; decisiones en `docs/DECISIONES.md`; resultados probados en `docs/RESULTADOS.md`.
- Estado: CP1 ejecutado localmente, cierre metodológico pendiente; no se han entrenado aún los modelos de tesis. CP0 validado; commit inicial `adfe426` publicado con CI aprobado. Ver docs/CP0_VERIFICACION.md. Se realizó una auditoría estructural preliminar del archivo en `docs/AUDITORIA_INICIAL.md`.
- Acción siguiente: revisar CP1 ejecutado localmente (2026-10-11), anomalías, población candidata y estimando antes de autorizar CP2. Ver CP1_RESULTADOS.md.

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
En esta sesión local sí está disponible data/raw/simpleMHAS.dta y CP1 fue ejecutado. En cloud no asumir disponibilidad. La aceptación metodológica sigue pendiente.

## Handoff CP1 — 2026-10-11
- Objetivo/checkpoint/estado: CP1, auditoría ejecutada; cierre metodológico parcial, pendiente de revisión humana. CP2 y pensiones sin iniciar.
- Rama de trabajo: `feat/cp1-auditoria`; base `a4e10dc`, main remoto comprobado antes de cambios. Se preservaron modificaciones preexistentes en `as.py` y `.vscode/`.
- Archivos: `audit.py` (validación, faltantes, población, participación, consistencia y cronología), `audit_report.py` (narrativa/figuras), `scripts/run_cp1.py`, `tests/test_audit.py`, notebook 02 y documentación CP1. No se modificó el microdato.
- Entorno: `/opt/miniconda3/envs/myenv/bin/python`, Python 3.11.17; agregado pypdf para leer el libro local; registrado kernel Jupyter myenv. No se creó otro entorno.
- Comandos: `python scripts/run_cp1.py`, ejecución con nbclient del notebook 02 en kernel myenv, `python -m pytest -q` (16 pruebas aprobadas) y `python scripts/validate_notebooks.py` (13 notebooks válidos, fuentes sin outputs). El primer intento de nbclient con kernel_cmd explícito falló por argumento duplicado; se resolvió registrando y seleccionando myenv.
- Resultados: seis fichas, siete figuras, tablas agregadas en reports/; cifras y limitaciones en CP1_RESULTADOS.md y RESULTADOS.md. El ejecutado local es reports/notebooks/02_construccion_muestra_ejecutado.ipynb; fuente versionado con outputs vacíos por validación CI existente. CI remoto de esta rama no ejecutado.
- Decisión provisional: universo amplio para observación/atrición; candidato directo 60+ por visita, no balanceado. Balanceado solo sensibilidad. Revisar anomalías de fallecimiento, sexo y edad antes de etiquetas; pesos no aplicados.
- Próxima acción reproducible: ejecutar script y leer las seis fichas del notebook/informe. Pregunta humana pendiente: aprobar estimando y criterio de edad, tratamiento de sustitutos/fallecimiento, regla para anomalías y alcance de ponderación. Solo después autorizar CP2. No hay un nuevo experimento predictivo EXP-###.
