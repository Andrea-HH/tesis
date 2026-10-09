# Protocolo de experimentos

Cada prueba deberá registrar: ID `EXP-NNN`, fecha, commit Git, pregunta, diseño de muestra, horizonte **en años**, predictores, definición de outcome, ponderación, partición temporal/grupos, imputación, seed, métricas, IC y limitaciones. Guardar el resumen sin microdatos en `experiments/EXP-NNN.json` mediante `save_experiment()`.

## Reglas metodológicas

1. No mezclar observaciones de una persona en train/test de forma que haya fuga de información ni utilizar resultados posteriores en predictores. Priorizar evaluación temporal fuera de muestra y, cuando corresponda, agrupación por persona.
2. Comparar **misma muestra, mismo horizonte, mismas filas y misma partición** para baseline económico vs versiones enriquecidas. Medir incertidumbre de diferencias con remuestreo por persona.
3. Aprender transformaciones, imputación y escaladores solo sobre train. Nunca definir cortes empíricos usando todo el test cuando el objetivo sea pronóstico aplicable en el futuro.
4. Los intervalos entre rondas son irregulares: 2001→2003=2; 2003→2012=9; 2012→2015=3; 2015→2018=3; 2018→2021=3 años nominales. No llamar horizonte único a la predicción de una ola.
5. Prevalencia, AUC, PR-AUC, Brier/calibración; para decisión actuarial, tablas de riesgo, falsos positivos/negativos y supuestos de costes. CIs preferentemente agrupados por ID.
6. Distinguir selección por muerte, sustituto y no respuesta. Mostrar el sesgo de trabajar únicamente con 6 rondas directas.
7. La variable objetivo y el target poblacional son **provisionales**, no resultados probados.

## Plantilla mínima

```python
from tesis_enasem.experiment import save_experiment

meta = {
    "id": "EXP-001",
    "objetivo": "Comparar baseline patrimonial y modelo con salud",
    "muestra": "Por definir tras CP1",
    "target": "Q1 de patrimonio siguiente ronda (provisional)",
    "metodo": "Por definir después de validar partición temporal",
    "estado": "planeado",
    "resultados": None,
}
# save_experiment(meta, "experiments")  # Solo cuando se haya ejecutado.
```
