"""Genera notebook05 independiente con evidencia multidimensional y ejecución local."""

import json
from hashlib import sha256
import nbformat
from nbclient import NotebookClient
from tesis_enasem.selection_mortality import OUTPUT, verify_inputs
from tesis_enasem.selection_mortality_outputs import make_figures
from tesis_enasem.project_paths import PROJECT_ROOT, INTERIM_DIR

if __name__ == "__main__":
    verify_inputs()
    r = json.loads((OUTPUT / "resultados.json").read_text())
    figures = make_figures(r)
    (OUTPUT / "figuras.json").write_text(json.dumps(figures, ensure_ascii=False, indent=2) + "\n")
    md = nbformat.v4.new_markdown_cell
    code = nbformat.v4.new_code_cell
    cells = [
        md("""# 05 · Pensiones, mortalidad registrada y selección longitudinal, 2001–2021

**Pregunta exploratoria:** ¿cómo se relaciona K inicial con registros posteriores sobre fallecidos y qué selección determina las trayectorias observables de salud física, mental, cognición, funcionalidad y situación económica?

Tres componentes integrados: pensiones y mortalidad registrada; perfiles basales; selección multidimensional. No pregunta definitiva, predicción ni causalidad. No exigir panel balanceado ni repetir el EDA completo. Se reutilizan bases y contratos de01–04, seguimiento04 y antecedentes03.

La mortalidad registrada no es mortalidad completa. Todo resultado distingue personas, aportaciones persona–intervalo, elegibilidad y valores válidos."""),
        code("""import json
import pandas as pd
from IPython.display import display,Markdown,Image
from tesis_enasem.selection_mortality import analyze,verify_inputs,OUTPUT
from tesis_enasem.selection_mortality_outputs import make_figures,conclusions
from tesis_enasem.project_paths import RESULTS_DIR
verify_inputs()
r=analyze()  # ejecución desde cero; no recalcula integración ni EDA anteriores
figuras=make_figures(r)
pd.set_option('display.max_rows',None)
pd.set_option('display.max_columns',None)
pd.set_option('display.float_format',lambda x:f'{x:.3f}')
def tabla(rows):display(pd.json_normalize(rows,sep='.'))
def figura(key):
    f=next(f for f in figuras if f['clave']==key)
    display(Image(filename=str(RESULTS_DIR/f['archivo'])))
    display(Markdown('**Nota:** '+f['nota']))
def interval(z):return f"{z['origen']}–{z['destino']}"
def indicadores():
    return [dict(a,intervalo=interval(z)) for z in r['intervalos'] for a in z['indicadores']]
"""),
    ]

    def section(title, question, source, reading):
        cells.extend(
            [
                md("## " + title + "\n\n" + question),
                code(source),
                md("**Interpretación y límites:** " + reading),
            ]
        )

    section(
        "1. Fuentes, estado vital y auditoría",
        "Maestro99,676/27,171, sidecar económico y lookup LEFT1:1. ID cunicah:np, id+ronda único. tipent1/2 directa,3/4 sustituto,5 sobre fallecido. Se comprueba concordancia con fallecido, sin corregir anomalías.",
        "tabla([r['auditoria']]); tabla([{'intervalo':interval(z),'N':z['N_cohorte'],**z['estado_vital'],'N_inconsistente':z['N_vital_inconsistente'],'N_reaparece':z['N_reaparece_posterior']} for z in r['intervalos']]); figura('seguimiento')",
        "Una inconsistencia fallecido→vivo se conserva y se evalúa aparte. Ausencia no prueba muerte ni supervivencia. Vivo sin medición es estado específico de cada indicador, no pérdida completa de seguimiento.",
    )
    section(
        "2. Seguimiento oficial y supervivencia actuarial",
        "Se revisó archivo oficial Master Follow-up y documentación histórica. No se identificó localmente el archivo completo; la página oficial exige acceso registrado para descargar microdatos. No se usaron credenciales ni se descargaron nuevas bases. Documento2018 incluye no entrevista, razón de sustituto y estado vital; no certificar cobertura2021 con esa versión.",
        "tabla([{'intervalo':interval(z),**{k:v for k,v in z['duracion_vivos'].items() if k!='frecuencias'}} for z in r['intervalos']]); tabla([r['metodologia']])",
        "Fechas de entrevista viva no son fechas de defunción. No inventar evento en punto medio ni censurar automáticamente ausentes en una fecha supuesta. No KM/Cox. Censura por intervalos o modelos agrupados requieren resolver tiempos, estado vital y captura del evento; quedan pendientes. [Master oficial](https://www.mhasweb.org/DataProducts/MasterFollowUp.aspx); [documento2018](https://www.mhasweb.org/resources/DOCUMENTS/2018/MHAS_Master_Follow_up_File_2001_2003_2012_2015_2018.pdf).",
    )
    section(
        "3. K inicial y fallecimiento registrado: cinco intervalos",
        "Cohorte viva60+ en origen, exposición K de esa visita. D=registro sobre fallecido en destino; D/N es proporción registrada, no riesgo completo. ND inicial separado. IC Newcombe de diferencia sí−no, condicional a registros muestrales, sin diseño/hogar.",
        "tabla([{'intervalo':interval(z),**a} for z in r['intervalos'] for a in z['mortalidad_K']]); tabla([{'intervalo':interval(z),**z['contraste_K']} for z in r['intervalos']]); figura('mortalidad_K')",
        "La ausencia no se convierte en sobreviviente: es parte del denominador del registro, con estado vital incierto. Comparar K inicial es defendible dentro de cada periodo; rupturas limitan tendencias entre periodos y cambios K. Nueve años no equivalen a tres ni a una tasa anual.",
    )
    section(
        "4. Diferencias por composición inicial",
        "Estandarización descriptiva de registroD a composición conjunta en soporte con≥20 por cada rama/celda. Demográfico sexo×edad×escolaridad; patrimonio, enfermedades, CES-D, ABVD y aprendizaje se añaden separadamente. No variables finales ni modelo predictivo.",
        "tabla([{k:v for k,v in a.items() if k!='celdas'}|{'intervalo':interval(z)} for z in r['intervalos'] for a in z['ajustes_K']]); tabla([{'intervalo':interval(z),'especificacion':a['especificacion'],**c} for z in r['intervalos'] for a in z['ajustes_K'] for c in a['celdas']])",
        "Contrastar cruda y ajustada en el MISMO soporte. La exclusión de basales faltantes y celdas pequeñas cambia estimando. Pesos internos de composición no son pesos de encuesta. ICnormal condicional, sin incertidumbre del target, diseño ni dependencia por hogar.",
    )
    section(
        "5. Mortalidad registrada según perfiles basales",
        "Perfiles seleccionados: demografía, patrimonio, salud física, mental, memoria, orientación/restas, funcionalidad y categorías económicas. Rangos de memoria son descriptivos, no umbrales clínicos. CES-D exige nueve completos; cinco síntomas no es diagnóstico.",
        "tabla([{'intervalo':interval(z),**a} for z in r['intervalos'] for a in z['perfiles_mortalidad']]); tabla([{k:v for k,v in a.items() if k!='celdas'}|{'intervalo':interval(z)} for z in r['intervalos'] for a in z['ajustes_perfiles']])",
        "Ajustes seleccionados de≥2enfermedades,≥5síntomas,≥1ABVD y aprendizaje≤4 consideran edad/sexo/escolaridad. No efectos ni mecanismos. Resultados de grupos pequeños son descriptivos. Variables directas seleccionan un subuniverso basal distinto de variables con sustituto.",
    )
    section(
        "6. Cónyuge y apoyos: ramas complementarias",
        "K propia no es hogar ni necesariamente contributiva; A no equivale a pensión no contributiva. Cónyuge solo con puntero concordante en2018 como origen; no extrapolar universo a rondas históricas.",
        "tabla([{'intervalo':interval(z),**a} for z in r['intervalos'] for a in z['complementarios']])",
        "Ramas pueden coexistir y tienen universos distintos; no comparar porcentajes como si fueran intervenciones mutuamente excluyentes. Antes2018 pareja no confirmada. Definición inicial evita exposición definida después del desenlace.",
    )
    section(
        "7. Incertidumbre vital y sensibilidades de mortalidad",
        "Límites lógicos D/N a(D+U)/N suponiendo registros correctos y cualquier estado entre ausentes. Intervalo de diferencia entre grupos permite asignaciones extremas distintas. No IC ni mortalidad corregida.",
        "tabla([{'intervalo':interval(z),**z['limites_diferencia_mortalidad'],**z['sensibilidad_inconsistencia']} for z in r['intervalos']])",
        "Los límites no capturan otros errores de registros. Se compara exclusión documentada de inconsistencia sin modificar originales. Ningún valor de síntomas se construye después de muerte.",
    )
    section(
        "8. Disponibilidad por dimensión: seis rondas",
        "Elegibilidad específica de indicador y modalidad. Valores observados/imputados del proveedor conservan tags; CES-D completos y flags de memoria documentados. No asumir misma muestra para16 indicadores.",
        "tabla([{'ronda':z['ronda'],**{k:v for k,v in a.items() if k not in ['estadisticas','categorias','estados']},'estados':a['estados']} for z in r['rondas'] for a in z['indicadores']]); figura('disponibilidad')",
        "Orientación no disponible2001; restas desde2015. Documentación2021 cambia a restas3 desde20: no diferencia2018–2021, aunque exista columna serial7 y rango0–5. No TICS ni índice cognitivo. [Documento cognitivo](https://www.mhasweb.org/resources/DOCUMENTS/Constructed_Imputed/MHAS_2018_2021_Cognitive_Function_Measures_Scoring_and_Classification.pdf).",
    )
    section(
        "9. Selección de pares longitudinales por indicador",
        "Cohorte origen viva60+; elegibilidad y validez basal separadas. Muerte, ausencia, modalidad/instrumento, invalidez y par completo son estados distintos. Sustitutos pueden aportar salud física/economía, aunque no CES-D directo.",
        "tabla([{'intervalo':a['intervalo'],'variable':a['variable'],'dimension':a['dimension'],**a['seleccion']} for a in indicadores()])",
        "Los conteos entre elegibles y entre válidos tienen denominadores diferentes y restricciones superpuestas. Estados de selección de cohorte sí son disjuntos. No sumar universos de indicadores ni considerar ineligibilidad como cero.",
    )
    section(
        "10. ¿Quiénes quedan fuera de cada dimensión?",
        "Comparación de edad, escolaridad, K, sexo, patrimonio relativo y propio indicador basal entre fallecidos, ausentes, vivos sin medición, modalidades y pares válidos.",
        "tabla([{'intervalo':a['intervalo'],'variable':a['variable'],**p} for a in indicadores() for p in a['perfiles_seleccion']]); figura('seleccion_basal')",
        "N basal válido puede ser menor que N de estado. Las muestras cognitivas/directas no representan automáticamente toda cohorte. Patrimonio es stock persona/cónyuge, no ingreso; sus cuartiles basales son relativos a cada ronda.",
    )
    section(
        "11. Trayectorias físicas, mentales, cognitivas y funcionales",
        "La ampliación se centra en selección: comparar medias disponibles por ronda, subgrupo retrospectivo≥2mediciones y cambios pareados elegibles, manteniendo poblaciones distintas. No repetir pruebas transversales03.",
        "tabla([{'intervalo':a['intervalo'],'variable':a['variable'],'dimension':a['dimension'],'N':a['cambios']['N'],'media_inicial':a['cambios']['inicio']['media'],'media_final':a['cambios']['final']['media'],'delta':a['cambios']['delta']['media'],'IC_inf':a['cambios']['delta']['ic95_inf'],'IC_sup':a['cambios']['delta']['ic95_sup']} for a in indicadores() if a['cambios']]); figura('composicion')",
        "Comparabilidad operacional condicionada al indicador, no invariancia clínica. Las pruebas miden dimensiones distintas; cambian disponibilidad e imputación. Serial2018–2021 bloqueado. Medias de ordinales son resumen de códigos, no escala clínica de intervalos iguales. No separar edad/cohorte/periodo sin diseño.",
    )
    section(
        "12. Trayectorias económicas y categorías",
        "Patrimonio conserva negativos y ceros, pero no calcular cambios reales sin unidades y deflactación verificadas. Ocupación/estado conyugal son categorías, no diferencias numéricas. K y A conservan titularidad y rupturas.",
        "tabla([{'intervalo':a['intervalo'],'variable':a['variable'],**a['seleccion'],'restriccion':a['restriccion']} for a in indicadores() if a['dimension']=='Económica']); tabla([{'ronda':z['ronda'],'variable':a['variable'],'N':a['N_valido'],'categorias':a['categorias']} for z in r['rondas'] for a in z['indicadores'] if a['variable'] in ['ocupacion','est_conyugal']])",
        "Se estudia quién permanece disponible para economía, no cambios monetarios artificiales. Disponibilidad no demuestra comparabilidad ni equivale a calidad. Categorías retirado/incapacitado/no trabaja agregadas no son jubilación homologada.",
    )
    section(
        "13. Múltiples mediciones y reconciliación con04",
        "Cada indicador distingue≥2 y≥3mediciones, pares consecutivos y pares conK. Personas entran al60+ en diferentes visitas. Cohortes de pares mantienen destino; multivisita exige60+ por visita.",
        "tabla([{'ronda':z['ronda'],'N60':z['N_vivo_60'],**z['entrada_60']} for z in r['rondas']]); tabla(r['reconciliacion']); tabla([{k:v for k,v in a.items() if k not in ['conteos_mediciones','composicion_subgrupo_multimedicion']} for a in r['multivisita']]); tabla([{'variable':a['variable'],**n} for a in r['multivisita'] for n in a['conteos_mediciones']])",
        "Mental:13,570paresK,14,069multimedición;13,560comunes,10solo pares,509solo multimedición.10discordancias de edad final<60(9en2012–15,1en2015–18) conservadas;509incluye123con par salud sinK y386sin par consecutivo. No diferencias netas interpretadas como pérdidas.",
    )
    section(
        "14. Sensibilidad de asociaciones K al universo retenido",
        "Comparar valores basales porK en elegibles válidos frente a quienes además tienen par válido. Cambia composición, no se estima efecto ni se recalcula todo03.",
        "tabla([{'intervalo':a['intervalo'],'variable':a['variable'],**g} for a in indicadores() for g in a['asociacion_K_basal_seleccion']])",
        "Muestras anidadas, no independientes. Cambio de contraste puede depender de selección, edad y otras características. No atribuirlo específicamente a muerte sin descomposición identificada.",
    )
    section(
        "15. Estandarización de composición basal",
        "Reponderar medias basales de retenidos a composición sexo×edad×escolaridad de target basal válido dentro de soporte con≥20retenidos/celda. Cuantifica composición observable antes del seguimiento.",
        "tabla([{'intervalo':a['intervalo'],'variable':a['variable'],**{k:v for k,v in a['estandarizacion_composicion_basal'].items() if k!='celdas'}} for a in indicadores() if a['estandarizacion_composicion_basal']])",
        "No reconstruye desenlaces futuros de muertos/ausentes. Se muestran target, retenidos crudos y estandarizados en mismo soporte; sin ICiid porque son muestras anidadas. Composición no equivale a descomposición causal.",
    )
    section(
        "16. Sensibilidades de medición y no observación viva",
        "No imputados en ambos extremos frente al producto completo; inconsistencias solo en sensibilidad; escenarios0/±1unidad desde valor basal acotado al dominio para vivos confirmados sin medición. No extender a ausentes de vital desconocido.",
        "tabla([{'intervalo':a['intervalo'],'variable':a['variable'],**s} for a in indicadores() for s in a['sensibilidades']]); tabla([{'intervalo':a['intervalo'],'variable':a['variable'],**s} for a in indicadores() for s in a['escenarios_vivos']]); figura('sensibilidad')",
        "Escenarios no reemplazan ni guardan mediciones individuales ni una base imputada. Incluyen ineligibilidad de modalidad: supuesto fuerte. Cambios de una unidad no son magnitudes clínicas equivalentes entre escalas. Mantener resultados contradictorios y pequeños.",
    )
    section(
        "17. Viabilidad de IPW y síntesis integrada",
        "Evaluar estimando de sobrevivientes observados, no una población donde nadie muere. Estado vital desconocido, basales incompletos y observación estructuralmente distinta por modalidad impiden certificar ignorabilidad/positividad.",
        "tabla(r['IPW_por_dimension']); tabla([r['metodologia']]); display(Markdown('\n\n'.join(conclusions(r))))",
        "No se estimaron pesos, extremos, ESS o balance: no afirmar validación de esos diagnósticos. Se requerirían historial previo, predictores de observación, estado vital y suficiente soporte; dependencia por persona/hogar y pesos de encuesta pendientes. No IPCW para imputar salud después de morir.",
    )
    cells.append(
        md("""## 18. Conclusiones exploratorias y aportación

Los tres componentes se integran sin causalidad: K inicial y registro de muerte, perfiles basales y selección multidimensional. Las diferencias por composición no justifican una pensión protectora/perjudicial; los ajustes usan soportes distintos. Cada dimensión observa subconjuntos distintos por muerte, ausencia, instrumento, modalidad y valores faltantes.

**Aportación actuarial y de Ciencia de Datos:** distinguir supervivencia documentada, seguimiento y proceso de medición; estudiar sensibilidad de conclusiones al universo, con contratos auditables y entrada60+ no balanceada. Próximos pasos: archivo completo de seguimiento/no entrevistas, fechas vitales, concordancia CES-D y resolución de restas2021 antes de supervivencia o ponderación. No pregunta definitiva ni predicción.

## 19. Reproducción

`python scripts/run_selection_mortality.py`; `python scripts/build_selection_mortality_notebook.py`; `python scripts/validate_selection_mortality.py`. Agregados en data/interim/pensiones_mortalidad_seleccion/. Síntesis selectiva en el único informe general; no modificar notebooks01–04, fuentes, resultados anteriores o LaTeX.""")
    )
    n = nbformat.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {"name": "myenv", "display_name": "Python (myenv)", "language": "python"},
            "language_info": {"name": "python", "version": "3.11"},
        },
    )
    # Código de cadena generado: conservar escapes, no introducir saltos dentro de literales.
    for c in n.cells:
        if c.cell_type == "code":
            c.source = c.source.replace("Markdown('\n\n'.join", "Markdown('\\n\\n'.join")
    source = PROJECT_ROOT / "notebooks/05_PENSIONES_MORTALIDAD_SELECCION.ipynb"
    ledger = OUTPUT / "notebook_fuente.json"
    if (
        source.exists()
        and sha256(source.read_bytes()).hexdigest() != json.loads(ledger.read_text())["sha256"]
    ):
        raise ValueError("Notebook05 editado; no sobrescribir")
    nbformat.write(n, source)
    ledger.write_text(json.dumps({"sha256": sha256(source.read_bytes()).hexdigest()}))
    NotebookClient(
        n, timeout=1200, kernel_name="myenv", resources={"metadata": {"path": str(PROJECT_ROOT)}}
    ).execute()
    nbformat.write(n, INTERIM_DIR / "notebooks_ejecutados/05_PENSIONES_MORTALIDAD_SELECCION_ejecutado.ipynb")
    verify_inputs()
    print("Notebook05 ejecutado desde cero:", len(cells), "celdas;", len(figures), "figuras")
