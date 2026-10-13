# Tablas y cifras reproducibles

Los `.tex` de esta carpeta se generan desde agregados de CP1 mediante `python scripts/export_cp1_manuscript.py`. Son quince tablas seleccionadas y un archivo de macros numéricas, con denominadores, etiquetas para referencias cruzadas y notas de alcance. El apéndice conserva exclusiones por ronda sin llenar la narración principal con todas las tablas del notebook.

No editar cifras manualmente. `python scripts/export_cp1_manuscript.py --check` comprueba sincronía con agregados locales. La compilación usa los archivos exportados y no necesita microdatos. `trazabilidad_cp1.json` contiene únicamente metadatos/huellas; nunca identificadores individuales. Ninguna alternativa de muestra queda aprobada por aparecer en estas tablas.
