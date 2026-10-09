# Tesis ENASEM — Alerta temprana de vulnerabilidad económica

> **Estado actual (2026-10-09):** infraestructura local/plantilla reproducible. Los modelos de tesis y resultados científicos **todavía no se han ejecutado**; para el progreso real consultar `docs/ROADMAP.md`.

## Pregunta de investigación
¿Es posible desarrollar un modelo longitudinal de alerta temprana que permita identificar y caracterizar trayectorias de vulnerabilidad económica en adultos mayores en México a partir de señales observables de salud física, salud mental, cognición, funcionalidad y características socioeconómicas, y determinar con cuánta anticipación pueden detectarse dicho riesgo y cómo varía su capacidad predictiva entre distintos perfiles demográficos y socioeconómicos?

## Arquitectura

```text
src/tesis_enasem/  Funciones de carga, validación, panel, cortes y métricas
notebooks/         Narrativa reproducible por checkpoint (00 a 12)
data/raw/          Dataset local, NO versionado
configs/           Configuración declarativa
experiments/       Metadatos de experimentos, sin filas individuales
docs/              Handoff, metodología, fuentes, decisiones, roadmap, resultados
reports/           Figuras y tablas regenerables, NO versionadas
tests/             Pruebas sintéticas que corren sin dataset
.github/workflows/ CI al conectarse a GitHub
```

## Instalación local
Requiere Python 3.11 o 3.12 (idealmente entorno virtual):

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # PowerShell Windows
python -m pip install --upgrade pip
python -m pip install -e ".[notebooks,dev]"
python -m pytest -q
python scripts/validate_notebooks.py
# En cloud con home de solo lectura:
mkdir -p .venv/jupyter-data .venv/jupyter-runtime .venv/jupyter-config .venv/ipython
export JUPYTER_DATA_DIR="$PWD/.venv/jupyter-data"
export JUPYTER_RUNTIME_DIR="$PWD/.venv/jupyter-runtime"
export JUPYTER_CONFIG_DIR="$PWD/.venv/jupyter-config"
export IPYTHONDIR="$PWD/.venv/ipython"
python -m jupyter lab notebooks/ --ip=127.0.0.1 --no-browser
```

En Colab: subir o clonar el repositorio y ejecutar `!pip install -e .`; el microdato debe cargarse por separado en el entorno, nunca hacerle commit.

## Fuentes y datos
Fuente oficial: [ENASEM](https://enasem.org/); diccionario: ENASEMsimple/simpleMHAS, versión 2, enero de 2025. Descarga autorizada por el proveedor de la encuesta. Copiar `simpleMHAS.dta` a `data/raw/` localmente. Ver `docs/FUENTES.md` para codificaciones y advertencias.

**Importante:** `ronda=3` es 2012 nominal, pero algunas entrevistas son 2013. `tipent` distingue entrevista directa, sustituto y sobre fallecido; `.f`, `.p`, `.w` NO equivalen a cero. Algunas pruebas cognitivas solo existen en ciertas rondas. Los intervalos entre rondas no son uniformes.

## Cómo usar los notebooks
Leer 00 (diseño), ejecutar 01 (ingesta y faltantes), 02 (flujo de muestra), 03 (EDA inicial) y 05 (cortes por ronda). Los restantes notebooks son **planes de experimentación**; completar una vez resueltas definiciones y controles de sesgo. No ejecutar CP4+ sin haber cerrado CP1/CP3. Cada resultado validado debe constar en `docs/RESULTADOS.md`.

## Colaboración y agentes
- Contexto para nuevos agentes: `AGENTS.md` y `docs/HANDOFF.md`.
- Checkpoints y criterios: `docs/ROADMAP.md`.
- Cambios metodológicos: `docs/DECISIONES.md`.
- Plan de pruebas: `docs/EXPERIMENTOS.md`.
- Datos públicos, supuestos y diccionario: `docs/FUENTES.md`, `docs/VARIABLES.md`.
- Auditoría preliminar, sin modelos: `docs/AUDITORIA_INICIAL.md`.
- Convención de ramas: `feat/cp1-auditoria`, `feat/cp2-eda`, etc.; abrir PR con pruebas y documentación antes de merge.

## Ética y alcance
Las asociaciones predictivas no prueban causalidad. No tratar los ponderadores transversales como pesos longitudinales por omisión. No registrar información identificable ni subir microdatos ENASEM al repositorio público.
