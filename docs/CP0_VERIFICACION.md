# CP0 — Verificación de infraestructura

Fecha: 2026-10-09. Base: `adfe426e83b29e70cc4c2665fbaf0e5ef18f0ac4`.

- Python 3.12.14 en `/workspace/tesis/.venv`; instalación editable con `python -m pip install -e ".[notebooks,dev]"` completada.
- `python -m pytest -q`: **9 pruebas aprobadas**, sin omisiones.
- `python scripts/validate_notebooks.py`: **13 notebooks válidos**, sin salidas versionadas. Se añadió validación del esquema nbformat e IDs estables de celda.
- `python -m pip check`: sin requisitos incompatibles. Imports de la librería cubiertos por dependencias declaradas; nbformat está en los extras de notebooks/dev. No hay lockfile; versiones aún no congeladas.
- `.gitignore` verificado con rutas representativas: microdatos dta/csv/parquet/sav y data/raw, entornos .venv/venv/env, temporales y cachés. El commit inicial no incluye microdatos ni entornos.
- `origin` ya era `https://github.com/Andrea-HH/tesis.git`.
- Commit inicial confirmado por Git fetch y CI aprobado: https://github.com/Andrea-HH/tesis/actions/runs/37971661745 (matriz Python 3.11/3.12).

CP0 completado con evidencia técnica. Los notebooks se validaron estructuralmente, **no se ejecutaron con microdatos**. No se entrenaron modelos ni se reprodujeron los conteos científicos existentes en la bitácora; estos provienen de documentación previa. CP1–CP9 permanecen pendientes.
