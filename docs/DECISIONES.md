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
