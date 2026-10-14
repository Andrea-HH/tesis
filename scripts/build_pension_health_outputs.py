"""Construye figuras y el notebook independiente desde los agregados de salud."""
from pathlib import Path
from hashlib import sha256
import json
import nbformat
from tesis_enasem.pension_health import OUTPUT,verify_frozen_inputs
from tesis_enasem.pension_health_outputs import make_figures,conclusions
from tesis_enasem.project_paths import PROJECT_ROOT

if __name__=='__main__':
    verify_frozen_inputs()
    r=json.loads((OUTPUT/'resultados.json').read_text())
    figures=make_figures(r);narrative=conclusions(r)
    (OUTPUT/'figuras.json').write_text(json.dumps(figures,ensure_ascii=False,indent=2)+'\n')
    md=nbformat.v4.new_markdown_cell;code=nbformat.v4.new_code_cell
    cells=[md('''# 03 · Pensiones, salud, cognición y funcionalidad en ENASEM

**Objetivo:** ampliar comparaciones faltantes y profundizar los contrastes descriptivos, conservando el EDA previo.

**Población:** 60+ en cada visita; seis rondas 2001–2021, 56,004 personas-ronda/18,754 personas; sin panel balanceado. No combinar con J01/2021, cuyo universo incluye todas las edades.

**Índice:** definición y contratos → disponibilidad → comparación principal → distribuciones → trivariados → estandarización → otras ramas → sensibilidad → interpretación y límites.

Este notebook es independiente de 01 y 02; por defecto lee agregados verificados. No expone IDs ni escribe bases.'''),code('''from pathlib import Path
import json
import pandas as pd
from IPython.display import display, Markdown, Image
from tesis_enasem.project_paths import PROJECT_ROOT, INTERIM_DIR, RESULTS_DIR
from tesis_enasem.pension_health import analyze, verify_frozen_inputs
RECALCULAR = False
DESTINO = INTERIM_DIR/'pensiones_salud'
# Para recalcular deliberadamente: python scripts/run_pension_health.py
resultados = analyze() if RECALCULAR else json.loads((DESTINO/'resultados.json').read_text())
figuras = json.loads((DESTINO/'figuras.json').read_text())
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
display(pd.DataFrame([resultados['metodologia']]).T)
'''),md(f'''## 1. Definición pensionaria y variables

K propia conserva la rama orientada auditada; negativa explícita no equivale a ausencia de toda pensión. Cónyuge exige universo confirmado en 2018/2021; sin pareja residente queda separado. Ambas ramas, desconocimiento y A se conservan. K no acredita contributividad y A no identifica automáticamente pensión no contributiva.

La bandera CES-D de cinco o más síntomas deriva del conteo, no es corroboración independiente ni diagnóstico. Se verificaron {r["calidad"]["CESD_pares_validos"]:,} pares bandera/conteo sin discordancias.

Se usan dominios y universos del indicador de los contratos ENASEMsimple, no una reconstrucción completa de cada salto bruto. Cognición y BMI son productos imputados; no se imputan valores nuevos ni se mezclan escalas. `tics` queda pendiente por ausencia de columna y contrato. Los pesos/diseño no están validados para esta selección.'''),code("display(pd.DataFrame(resultados['contratos'])[['variable','dimension','label','unit','kind','page','imputado','nota_comparabilidad']])"),md('''## 2. Disponibilidad, elegibilidad y faltantes

La selección 60+ se realiza por edad en cada visita. Elegibilidad del indicador depende de modalidad: directa (1/2) o directa/sustituto (1–4) según contrato. NR/NS conserva `.r/.d` y códigos específicos. No formulado, salto, sustituto o fallecimiento no se convierten en cero.

Orientación no está disponible en 2001; serial7 comienza en 2015. TICS no se reconstruye sumando pruebas. Los números válidos incluyen la representación imputada del proveedor cuando la variable así se define; no es posible contar imputaciones individuales sin su bandera documentada.'''),code("cobertura=pd.DataFrame(resultados['cobertura'])\ndisplay(cobertura.drop(columns=['estados_salud'],errors='ignore'))\ndisplay(pd.DataFrame(resultados['cuartiles_patrimonio']))"),md('''## 3. Comparación principal y metodología

Comparación: afirmativa propia K frente a negativa explícita propia K dentro de la población elegible del indicador. Recepción ND y salud no válida quedan fuera del contraste, pero en los denominadores.

- Binarias: diferencia de proporciones en puntos porcentuales e IC 95% Newcombe/Wilson, sin p-valores.
- Ordinales, conteos y continuas asimétricas: delta de Cliff = P(valor con K > valor sin K propia) − P(valor con K < valor sin K propia), con empates. Bootstrap de personas dentro de rama y ronda (999 réplicas; semillas deterministas), sin combinar rondas. Se muestran medianas, cuartiles y distribuciones.
- Delta positivo significa valor mayor: peor autopercibido o más síntomas/limitaciones, mayor puntuación cognitiva, o IMC mayor sin juicio clínico automático.
- ≥30 valores válidos por rama para estimar efecto. IC puntuales condicionados a muestra observada/representación imputada; no diseño complejo, incertidumbre MI ni IC simultáneos. Un IC que excluya cero no se convierte en conclusión confirmatoria entre múltiples contrastes.

Referencias de implementación: [Newcombe en statsmodels](https://www.statsmodels.org/stable/generated/statsmodels.stats.proportion.confint_proportions_2indep.html), [estadístico de rangos con empates](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.mannwhitneyu.html).

Las 30 correlaciones de Spearman previas se leen como antecedentes; no se recalculan.'''),code("principal=pd.DataFrame([{k:v for k,v in x.items() if k not in ['si','no','distribuciones']}|{'mediana_si':x['si']['mediana'],'mediana_no':x['no']['mediana']} for x in resultados['principal']])\ndisplay(principal)\nprint('Correlaciones previas reutilizadas:',len(resultados['reutilizados']))"),code("for figura in figuras[:4]:\n    display(Markdown('### '+figura['titulo']))\n    display(Image(filename=str(RESULTS_DIR/figura['archivo'])))"),md('''## 4. Distribuciones y titularidad

Las frecuencias completas, incluidos ceros válidos, permiten contrastar formas y no solo medianas. Categorías de titularidad conservan ambas, solo propia, solo cónyuge, ambas negativas, desconocido y sin pareja residente separado. Los grupos no deben sumar una persona en varias ramas ni atribuir montos del hogar.

Antes de 2018 las categorías combinadas son estados del proveedor con universo de pareja no confirmado; no son tasas de elegibilidad del cónyuge.

Las frecuencias y los cuantiles exhaustivos están en el mismo agregado, no en cientos de archivos.'''),code("filas=[]\nfor analisis in resultados['titularidad']:\n    for grupo in analisis['distribuciones']:\n        filas.append({k:v for k,v in analisis.items() if k not in ['distribuciones','nota']}|{k:v for k,v in grupo.items() if k!='frecuencias'})\ndisplay(pd.DataFrame(filas))\ndisplay(Image(filename=str(RESULTS_DIR/figuras[4]['archivo'])))"),md('''## 5. Trivariados seleccionados: tres variables simultáneas

Prioridades: síntomas × sexo; salud global × edad; aprendizaje/evocación × escolaridad; AIVD/movilidad × edad; diabetes/enfermedades × sexo; aprendizaje × cuartil de patrimonio. Se complementa síntomas × tamaño de localidad (<100 mil/≥100 mil, no ruralidad estricta).

Todos contrastan K propia dentro de cada estrato, en las seis rondas disponibles. Se registran celdas pequeñas y estratificadores desconocidos sin reemplazarlos por un grupo conocido. Los cuartiles de patrimonio son relativos a la ronda, usan stock persona/cónyuge y no constituyen umbrales de pobreza. No se ha probado interacción formal ni efecto causal.'''),code("trivariados=pd.DataFrame([{k:v for k,v in x.items() if k not in ['si','no']} for x in resultados['trivariados']])\ndisplay(trivariados)\nfor figura in figuras[5:]:\n    display(Markdown('### '+figura['titulo']))\n    display(Image(filename=str(RESULTS_DIR/figura['archivo'])))"),md('''## 6. Estandarización descriptiva y soporte común

Medias/proporciones de seis indicadores se estandarizan a la misma composición sexo × edad (60–69/70–79/80+) × escolaridad (0–5/6–9/10+) × modalidad (directa/sustituto) de los casos completos en celdas con ≥20 por rama.

Se muestran diferencia cruda en ese mismo soporte y estandarizada. El soporte es un subuniverso; no todo 60+. Pesos son proporciones internas fijas de composición, no factores de encuesta. IC normal de medias/proporciones estratificadas, condicional a esas celdas. No se entrenó modelo predictivo ni regresión. Los deltas de rangos y diferencias medias son medidas diferentes; agrupación y asimetría pueden producir lecturas distintas.'''),code("ajustados=pd.DataFrame([{k:v for k,v in x.items() if k!='celdas'} for x in resultados['estandarizados']])\ndisplay(ajustados)"),md('''## 7. Apoyos propios y cónyuge confirmado

A conserva donativos públicos en dinero/especie, con cambios de opciones. La pensión del cónyuge se contrasta solo dentro de universo confirmado (2018/2021). Los tamaños de efecto no se comparan como si los tres universos fueran iguales; ramas pueden coexistir. No se reclasifica ND como no receptor.'''),code("complementarios=pd.DataFrame([{k:v for k,v in x.items() if k not in ['si','no']} for x in resultados['complementarios']])\ndisplay(complementarios)"),md('''## 8. Sensibilidad a modalidades

Para indicadores elegibles también en sustitutos, se repite únicamente el nuevo contraste restringido a entrevistas directas; no se reejecuta integración ni EDA previo. Diferencias pueden reflejar composición y medición, no error a corregir. Los productos imputados no ofrecen por sí solos una separación individual observada/imputada; incertidumbre entre imputaciones y diseño permanece pendiente.'''),code("sensibilidad=pd.DataFrame([{k:v for k,v in x.items() if k not in ['si','no']} for x in resultados['sensibilidad_modalidad']])\ndisplay(sensibilidad)"),md('## 9. Interpretación integrada y límites\n\n'+'\n\n'.join(narrative)),md('''## 10. Reproducción y validación

1. `python scripts/run_pension_health.py` calcula solo esta ampliación.
2. `python scripts/build_pension_health_outputs.py` genera figuras y notebook desde agregados.
3. Incorporar una selección justificada al único informe, sin volcar todas las tablas.
4. `python scripts/build_report_pdf.py` y `--check` regeneran y verifican su PDF.

La validación específica contrasta cobertura, claves, dominios, tamaños de efecto, ramas, hashes y denominadores. Bases, notebooks 01/02, capítulos y resultados previos permanecen intactos. No se hacen cambios en Git/GitHub.'''),code("from tesis_enasem.pension_health import verify_frozen_inputs\nverify_frozen_inputs()\nassert len(resultados['principal'])==80\nassert all(x['N_pares_validos']==x['N_si_valido']+x['N_no_valido'] for x in resultados['principal'])\nassert all(-1<=x['efecto']<=1 for x in resultados['principal'] if x.get('medida')=='Delta de Cliff')\nprint('80 contrastes principales; denominadores y huellas verificados; sin modelos ni causalidad.')")]
    nb=nbformat.v4.new_notebook(cells=cells,metadata={'kernelspec':{'name':'python3','language':'python','display_name':'Python 3'}})
    path=PROJECT_ROOT/'notebooks/03_PENSIONES_SALUD_COGNICION.ipynb'
    manifest_path=OUTPUT/'manifest.json'
    manifest=json.loads(manifest_path.read_text())
    if path.exists():
        if sha256(path.read_bytes()).hexdigest()!=manifest.get('notebook_fuente_sha256'):
            raise ValueError('Notebook existente editado: no sobrescribir')
    nbformat.write(nb,path)
    manifest['notebook_fuente_sha256']=sha256(path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    verify_frozen_inputs()
    print('Notebook independiente y',len(figures),'figuras de síntesis generados.')
