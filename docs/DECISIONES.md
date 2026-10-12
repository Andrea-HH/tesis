# Registro de decisiones metodológicas

Cada entrada indica estado: **aprobada**, **provisional** o **por verificar**; cambiarla exige nota y justificación.

## 2026-10-09 — Arquitectura src + notebooks
**Estado:** aprobada para scaffold.  
**Motivo:** separar código reusable de explicación y facilitar pruebas.  
**Decisión:** `src/tesis_enasem` contiene lógica; `notebooks/` contiene narrativa, evaluación y ejemplos.  
**Impacto:** cada nueva función pública tendrá test y documentación.

## 2026-10-09 — Definición de población
**Estado:** provisional.  
**Alternativas:** edad >=60 en cada ola, elegibilidad inicial, cohorte basal, panel no balanceado.  
**Riesgo:** condicionar a seis entrevistas introduce selección por supervivencia.  
**Pendiente:** tabla de muestra CP1; establecer población elegible y estimando.

## 2026-10-09 — Vulnerabilidad patrimonial Q1
**Estado:** provisional.  
**Motivo:** variable `imp_neto` disponible, incluso valores negativos.  
**Pendiente:** determinar población que define Q1, pesos, cortes estimados sin leakage, comparabilidad monetaria intertemporal y sensibilidad a otras definiciones.

## 2026-10-09 — Tratamiento de faltantes Stata
**Estado:** aprobada para diagnóstico.  
**Decisión:** cargar con `convert_missing=True` para identificar `.f/.p/.w`; convertir a numérico solo para variables que vayan a análisis.  
**Riesgo:** reemplazar temprano por NaN confunde muerte, sustituto y no formulado.

## 2026-10-11 — CP1, población candidata y anomalías
**Estado:** provisional, pendiente de aprobación humana.
**Propuesta:** referencia amplia no balanceada para estudiar observación; predictores directos en visitas con edad ≥60, entrada abierta sin condicionar a seis rondas. Comparadores: 60+ en primera observación original, seguimiento desde primera edad 60+ y paneles de seis rondas (sensibilidad).
**Evidencia:** 50,841 registros/18,158 personas frente a 5,784/964 en seis directas 60+; composición distinta por sexo. Ver CP1_RESULTADOS.md.
**Anomalías:** conservar, sin corregir ni excluir automáticamente, fallecimiento seguido de observación, sexo inconsistente y descensos de edad. Requieren contraste con fuente antes de definir etiquetas.
**Ponderación:** auditoría separada individual/hogar, sin estimaciones ponderadas hasta confirmar población objetivo, pesos cero, diseño y manejo longitudinal. La presencia de un peso no autoriza su uso.
**Cronología:** intervalos nominales y efectivos separados; no imputar año efectivo de entrevistas sobre fallecidos.
**Privacidad:** fuentes de notebooks sin outputs según validación vigente; notebook ejecutado y agregados extensos locales ignorados; documentación pública exclusivamente agregada. No se integraron pensiones ni se ejecutó CP2/CP3.
