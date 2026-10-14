"""Crea el notebook04 académico independiente desde resultados reproducibles."""

from hashlib import sha256
import json
import nbformat
from nbclient import NotebookClient
from tesis_enasem.longitudinal_health import OUTPUT, verify_inputs
from tesis_enasem.longitudinal_health_outputs import make_figures
from tesis_enasem.project_paths import PROJECT_ROOT, INTERIM_DIR


def build() -> None:
    """Protege ediciones manuales y conserva la ejecución en data/interim."""
    verify_inputs(allow_report=True)
    r = json.loads((OUTPUT / "resultados.json").read_text())
    figures = make_figures(r)
    (OUTPUT / "figuras.json").write_text(json.dumps(figures, ensure_ascii=False, indent=2) + "\n")
    md = nbformat.v4.new_markdown_cell
    code = nbformat.v4.new_code_cell
    cells = [
        md("""# 04 · Trayectorias de pensiones y salud mental en ENASEM, 2001–2021

**Pregunta de esta exploración, sin adoptar una pregunta definitiva de tesis:** ¿cómo evolucionan las respuestas pensionarias y los síntomas de las mismas personas durante las seis rondas, considerando composición, periodos y selección?

Se integran tres niveles: población disponible por ronda, pares consecutivos y trayectorias de múltiples visitas. Panel incompleto con entrada al universo60+ en diferentes rondas. Sin modelos predictivos, causalidad ni nuevas variables cognitivas.

**Antecedente03:** diferencia transversal de síntomas2021 cruda−0.434 y estandarizada−0.071 en el mismo soporte. No presupone cambio individual. La fuente de este notebook son las bases existentes, no outputs o variables de una sesión previa."""),
        code("""import json
import pandas as pd
from IPython.display import display, Markdown, Image
from tesis_enasem.project_paths import PROJECT_ROOT, RESULTS_DIR
from tesis_enasem.longitudinal_health import analyze, verify_inputs, OUTPUT
from tesis_enasem.longitudinal_health_outputs import make_figures, conclusions
verify_inputs(allow_report=True)
# Ejecución desde cero: calcula únicamente la nueva ampliación, no integración ni EDA previo.
r = analyze()
figuras = make_figures(r)
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.float_format', lambda value: f'{value:.3f}')
def tabla(rows):
    display(pd.DataFrame(rows))
def figura(key):
    f = next(f for f in figuras if f['clave'] == key)
    display(Markdown('**'+f['titulo']+'**'))
    display(Image(filename=str(RESULTS_DIR/f['archivo'])))
    display(Markdown('**Nota:** '+f['nota']))
def cambio_fila(intervalo, group):
    s=group['cambio']; a=group['inicio']; b=group['final']
    return {'intervalo':intervalo,'N':s['N'],'media_inicial':a['media'],'mediana_inicial':a['mediana'],
        'media_final':b['media'],'mediana_final':b['mediana'],'cambio_medio':s['media'],
        'cambio_mediano':s['mediana'],'DE_cambio':s['DE'],'q25':s['q25'],'q75':s['q75'],
        'IC_inf':s['ic95_inf'],'IC_sup':s['ic95_sup'],'pct_aumenta':group['pct_aumenta'],
        'pct_disminuye':group['pct_disminuye'],'pct_igual':group['pct_igual']}
display(pd.DataFrame([r['metodologia']]).T)
"""),
    ]

    def section(title, text, source, interpretation):
        cells.extend(
            [md("## " + title + "\n\n" + text), code(source), md("**Lectura y límites:** " + interpretation)]
        )

    section(
        "1. Fuentes y definición pensionaria",
        "Maestro99,676/27,171 y sidecar económico se enlazan LEFT1:1 por id+ronda; se valida cunicah:np. K propia no es cónyuge ni hogar, ni automáticamente contributiva. ND no es negativa. Cada resultado distingue muestra y personas.",
        "tabla([{'intervalo':f\"{z['origen']}–{z['destino']}\",'K_condicionada':z['K_comparable_condicionada'],'restriccion':z['restriccion']} for z in r['intervalos']])",
        "Sí/sí no demuestra continuidad ininterrumpida; no/sí no identifica primera pensión ni fecha. Las rupturas2003–2012 y2015–2018 permanecen visibles; no homologar altas/bajas.",
    )
    section(
        "2. Auditoría CES-D: nueve componentes y faltantes",
        "Componentes: deprimido, esfuerzo, sueño intranquilo, feliz, soledad, disfrute de vida, tristeza, cansancio y energía. Codificación construida0/1; feliz/disfrute/energía invierten su polaridad. Conteo0–9 y periodo semana pasada. Fuente: diccionarios/contrato_longitudinal_salud_mental.json; libro oficial de variables creadas y ENASEMsimple. Solo directas1/2.",
        "tabla(r['auditoria_CESD'])",
        "En completos, suma de nueve coincide con proveedor en cada ronda. Existen conteos válidos con componentes incompletos que empíricamente coinciden con suma disponible. No rellenamos ceros: principal exige nueve completos, proveedor es sensibilidad. El diagrama oficial ejemplifica2024, no certifica todos los números brutos2001–2021. Comparabilidad de productos construidos condicionada, sin invariancia psicométrica demostrada.",
    )
    section(
        "3. Panel individual y poblaciones",
        "Ronda nominal distinta de año/mes efectivo. Cohorte viva60+ en origen para pares; destino se conserva aunque falte edad o disminuya. Multivisita usa visitas vivas60+ de cada persona; no seis rondas obligatorias.",
        "tabla(r['multivisita']['conteos_visitas']); tabla(r['multivisita']['patrones_observacion'])",
        "Visitas observadas no equivalen a mediciones válidas. Patrones de seis dígitos corresponden2001/2003/2012/2015/2018/2021; cero indica ausencia del universo vivo60+, que también puede ser edad aún menor60, no necesariamente pérdida.",
    )
    section(
        "4. Evolución de población y K en seis rondas",
        "Describe composición por visita; denominador de K afirmativa/negativa/ND es toda la muestra viva60+. Tasas entre estados conocidos se distinguen del porcentaje sobre total.",
        "tabla([{'ronda':z['ronda'],'N_todas_edades_modalidades':z['N_todas_edades_modalidades'],'N_vivos_todas_edades':z['N_vivos_todas_edades'],'N_60':z['N_60_vivos'],'N_directas_60':z['N_directas_60'],**z['K']} for z in r['rondas']]); figura('evolucion')",
        "Cambios de nivel entre rondas pueden reflejar entrada al60+, reemplazo, supervivencia, modalidad y medición; no son cambios de las mismas personas.",
    )
    section(
        "5. Síntomas y soledad por ronda",
        "Descriptivos de directas60+, principal nueve completos frente a producto del proveedor. Cinco o más síntomas es umbral documental, no diagnóstico. Soledad es componente del conteo, no validación independiente.",
        "tabla([{'ronda':z['ronda'],'criterio':k,**{a:b for a,b in z[k].items() if a!='frecuencias'}} for z in r['rondas'] for k in ['sintomas_principal','sintomas_proveedor','soledad']]); tabla([{'ronda':z['ronda'],'estado_K':a['estado_K'],'N_rama':a['N_rama'],'N_sintomas':a['sintomas']['N'],'media_sintomas':a['sintomas']['media'],'mediana_sintomas':a['sintomas']['mediana']} for z in r['rondas'] for a in z['por_K']]); tabla([{'ronda':z['ronda'],'variable':k,**f} for z in r['rondas'] for k in ['sintomas_principal','soledad'] for f in z[k]['frecuencias']])",
        "No generalizar estas distribuciones a México sin diseño/ponderación. Una respuesta válida no elimina selección. La comparación con03 no comparte exactamente criterio por la nueva restricción de componentes completos.",
    )
    section(
        "6. Seguimiento y atrición de cinco cohortes",
        "Presentes incluye sobre fallecido. Grupos de seguimiento mutuamente excluyentes se distinguen de restricciones superpuestas de salud/K. Todos los porcentajes de la tabla usan cohorte inicial.",
        "tabla([{'intervalo':f\"{z['origen']}–{z['destino']}\",**z['seguimiento']} for z in r['intervalos']]); tabla([{'intervalo':f\"{z['origen']}–{z['destino']}\",'grupo':s['grupo'],'N':s['N'],'pct_cohorte':s['pct_cohorte']} for z in r['intervalos'] for s in z['seleccion']]); figura('seguimiento')",
        "Ausencia no significa muerte ni pérdida definitiva. Reapariciones son subconjunto de ausentes; después2021 no son observables. Anomalía fallecido→vivo conservada. Muestra final seleccionada por supervivencia, modalidad, ítems y K.",
    )
    section(
        "7. Duración individual efectiva",
        "Meses =12×diferencia de año+ diferencia de mes; solo fechas mensuales válidas y positivas de entrevistas vivas. Se describe tanto seguimiento vivo como muestra final.",
        "tabla([{'intervalo':f\"{z['origen']}–{z['destino']}\",'universo':k,**{a:b for a,b in z[k].items() if a!='frecuencias'}} for z in r['intervalos'] for k in ['duracion_vivos','duracion_analitica']]); tabla([{'intervalo':f\"{z['origen']}–{z['destino']}\",**f} for z in r['intervalos'] for f in z['duracion_vivos']['frecuencias']])",
        "2003–2012 es mucho más largo. No dividir síntomas por años: no son acumulación. Año efectivo, calendario y edad son dimensiones distintas; fechas sin día no permiten precisión diaria.",
    )
    section(
        "8. Matrices de respuestas pensionarias",
        "Dos universos: todos los vivos con K conocida en extremos y muestra principal con síntomas completos. Frecuencias, porcentajes por fila y del total; denominadores explícitos.",
        "tabla([{'intervalo':f\"{z['origen']}–{z['destino']}\",'universo':k,'K_comparable':z['K_comparable_condicionada'],**a} for z in r['intervalos'] for k in ['matriz_K_vivos','matriz_K_principal'] for a in z[k]]); figura('matrices')",
        "Matrices suman su propioN, no toda cohorte. No/no tampoco demuestra ausencia durante todos los años intermedios. Rupturas solo patrones de respuesta.",
    )
    section(
        "9. Cambios pareados de síntomas",
        "Cambio =destino−origen para cada persona. Se resumen inicio/final, media/mediana, DE, cuartiles, frecuencias y aumentos/disminuciones/igualdad. ICt de media del cambio por personas dentro de intervalo.",
        "tabla([cambio_fila(f\"{z['origen']}–{z['destino']}\",z['cambios']) for z in r['intervalos']]); tabla([{'intervalo':f\"{z['origen']}–{z['destino']}\",**f} for z in r['intervalos'] for f in z['cambios']['cambio']['frecuencias']])",
        "La incertidumbre usa cambios pareados, no dos muestras independientes. Media pequeña puede coexistir con muchos cambios opuestos. Igual conteo no garantiza mismos síntomas; sin umbral de cambio clínicamente importante.",
    )
    section(
        "10. Relación entre patrones K y cambios",
        "Cuatro patrones de respuestas en cada intervalo. Contrastes predefinidos No→Sí menos No→No y Sí→No menos Sí→Sí, conservando estado inicial semejante de K. Ambos son descriptivos; no grupos de tratamiento/control.",
        "tabla([cambio_fila(f\"{z['origen']}–{z['destino']} {a['transicion']}\",a) for z in r['intervalos'] for a in z['por_transicion']]); tabla([{'intervalo':f\"{z['origen']}–{z['destino']}\",**a} for z in r['intervalos'] for a in z['contrastes_brutos']]); figura('distribuciones')",
        "Contraste de cambios no demuestra efecto de inicio/pérdida de pensión. Incluye condiciones anteriores, selección y cambios no medidos. En rupturas K no se homologan cambios reales.",
    )
    section(
        "11. Trayectorias individuales de múltiples visitas",
        "Personas con>=2 mediciones completas, ordenadas por ronda. Categorías: conteo igual, no decreciente, no creciente, fluctuación; empates permitidos en tendencias monótonas. No interpolación.",
        "tabla(r['multivisita']['patrones_por_N_mediciones']); tabla([{'patron':k,'N_personas':v} for k,v in r['multivisita']['patrones_sintomas'].items()]); figura('multivisita')",
        "Dos visitas no permiten detectar cambios de dirección. Mayor número de visitas ofrece más oportunidades de fluctuar. Las tendencias por orden de visita mezclan calendarios y duraciones; no son pendientes anuales.",
    )
    section(
        "12. Secuencias pensionarias de múltiples visitas",
        "Patrones retrospectivos de K en visitas vivas60+: afirmativas/negativas repetidas, cambio único, múltiples cambios, ND. Las secuencias que cruzan rupturas se marcan como no homologadas.",
        "tabla([{'patron':k,'N_personas':v} for k,v in r['multivisita']['patrones_K'].items()]); print('Trayectorias que atraviesan rupturas:',r['multivisita']['N_trayectorias_atraviesan_ruptura']); print('Personas con huecos en universo60+:',r['multivisita']['N_con_huecos'])",
        "No llamar estabilidad pensionaria verdadera a afirmativas repetidas. Secuencias conND permanecen desconocidas. Patrones de observación no distinguen automáticamente ausencia, menor60 o muerte; el seguimiento individual por intervalo sí separa esos estados.",
    )
    section(
        "13. Relación retrospectiva entre trayectorias",
        "Resumen de cambio primera–última medición por secuencia K, cantidad de mediciones y observación intermitente. Cada persona aparece una vez en el resumen; los grupos usan información de todo el seguimiento y se reconocen retrospectivos.",
        "tabla([{'patron_K':z['patron_K'],'N_mediciones':z['N_mediciones'],'hueco':z['hueco_observacion'],'N_personas':z['N_personas'],'cambio_medio_primera_ultima':z['cambio_primera_ultima']['media'],'cambio_mediano':z['cambio_primera_ultima']['mediana'],**z['patrones_sintomas']} for z in r['multivisita']['relacion_K_sintomas']]); tabla(r['multivisita']['evolucion_calendario_subgrupos_retrospectivos'])",
        "No interpretar diferencias basales de grupos definidos con futuro como predicción o exposición conocida al inicio. Horizontes heterogéneos y rupturas permanecen; no contraste causal global entre secuencias.",
    )
    section(
        "14. Comparación composición, repetición y cambios",
        "La media disponible por ronda se contrasta con subgrupos retrospectivos por cantidad de mediciones, y con diferencias pareadas. Son tres estimandos distintos. Una persona puede aportar múltiples intervalos.",
        "tabla(r['multivisita']['evolucion_por_mediciones']); tabla(r['multivisita']['pares_consecutivos_intermitentes']); print('Pares/personas/repetidas:',r['metodologia']['N_pares_principales'],r['metodologia']['N_personas_distintas_pares'],r['metodologia']['N_personas_mas_un_intervalo'])",
        "No sumar intervalos como personas independientes. Pares intermitentes pueden atravesar rupturas y mayor tiempo; se muestran descriptivos sin ICiid combinado. Panel completo no es requisito ni población principal.",
    )
    section(
        "15. Soledad: transiciones y multivisita",
        "No/no, no/sí, sí/no, sí/sí de soledad dentro de cada patrón K. Denominador propio: directas con soledad/K válida en extremos, distinto de nueve síntomas completos.",
        "tabla([{'intervalo':f\"{z['origen']}–{z['destino']}\",'K':g['transicion_K'],'N_grupo':g['N'],'cambio_soledad_pp':g['cambio_pp'],'IC_inf_pp':g['cambio_pareado']['ic95_inf']*100,'IC_sup_pp':g['cambio_pareado']['ic95_sup']*100,**a} for z in r['intervalos'] for g in z['soledad'] for a in g['matriz']]); tabla([{'patron':k,'N_personas':v} for k,v in r['multivisita']['patrones_soledad'].items()])",
        "Persistencia solo en visitas observadas; no experiencia continua entre ellas. Soledad es componente CES-D y no prueba independiente de salud mental.",
    )
    section(
        "16. Sexo, edad, escolaridad, localidad y patrimonio basal",
        "Estratificación dentro de cada patrón K y periodo. Edad al origen60–69/70–79/80+; escolaridad del proveedor; localidad<100mil/≥100mil no ruralidad estricta; patrimonio compartido en cuartil basal de ronda60+.",
        "tabla([{'intervalo':f\"{z['origen']}–{z['destino']}\",'K':a['transicion'],'variable':a['estratificador'],'estrato':a['estrato'],'N':a['N'],'cambio_medio':a['cambio']['media'],'cambio_mediano':a['cambio']['mediana'],'estimable_N30':a['estimable']} for z in r['intervalos'] for a in z['estratos']]); figura('sociodemografia'); tabla(r['multivisita']['sociodemografia'])",
        "No prueba de interacción. No separar automáticamente edad, periodo y cohorte. Patrimonio no es ingreso, conserva negativos/ceros; cuartiles relativos no implican igual riqueza real entre rondas.",
    )
    section(
        "17. Comparaciones ajustadas: estimando y soporte",
        "Estandarización de diferencias medias del cambio a distribución conjunta del mismo soporte. Demográfico: sexo×edad×escolaridad basal. Basal/duración añade síntomas iniciales0/1–4/5–9 y duración efectiva relativa a nominal. Celdas>=10 por rama, total>=30. No covariables finales de salud/patrimonio.",
        "tabla([{k:v for k,v in a.items() if k!='celdas'}|{'intervalo':f\"{z['origen']}–{z['destino']}\"} for z in r['intervalos'] for a in z['ajustes']]); tabla([{'intervalo':f\"{z['origen']}–{z['destino']}\",'grupo':a['grupo'],'especificacion':a['especificacion'],**c} for z in r['intervalos'] for a in z['ajustes'] for c in a['celdas']]); figura('comparacion')",
        "Ajustar síntomas basales pregunta por cambios a composición inicial semejante, distinto del marginal; regresión a la media y error de medición permanecen. Soportes diferentes cambian población. ICnormal condicional a composición fija, sin diseño/hogar; no corrección causal.",
    )
    section(
        "18. Selección longitudinal: características basales",
        "Comparar edad, sexo, escolaridad, K, síntomas, enfermedades y ABVD iniciales entre seguimiento analítico, otros vivos, sustitutos, sobre fallecido y ausentes. Cada variable conserva N válido propio.",
        "tabla([{'intervalo':f\"{z['origen']}–{z['destino']}\",'grupo':a['grupo'],'N_grupo':a['N'],'variable':k,'N_valido':a[k]['N'],'media':a[k]['media'],'mediana':a[k]['mediana']} for z in r['intervalos'] for a in z['seleccion'] for k in ['edad','escolaridad','sintomas_iniciales','enfermedades','ABVD']]); tabla([{'intervalo':f\"{z['origen']}–{z['destino']}\",**a} for z in r['intervalos'] for a in z['seleccion_K']]); figura('seleccion')",
        "Características de incluidos no representan toda cohorte. Síntomas basales pueden faltar precisamente en quienes terminan excluidos. Comparaciones no corrigen sesgo; muerte no es cero síntomas ni ausencia de K.",
    )
    section(
        "19. Sensibilidades seleccionadas",
        "Principal nueve completos vs proveedor; restricciones de edad descendente/ND y sexo discordante solo como sensibilidad documentada; edad60–74/75+; soporte>=5/10/20 por rama. No modificar anomalías en originales.",
        "tabla([{'intervalo':f\"{z['origen']}–{z['destino']}\",'criterio':a['criterio'],'N':a.get('N',a.get('N_soporte')),'cambio_medio':a.get('cambio',{}).get('media'),'ajustada':a.get('ajustada'),'grupo':a.get('grupo')} for z in r['intervalos'] for a in z['sensibilidades']])",
        "Conservar resultados pequeños/nulos/contrarios; criterios alteran muestra y estimando. No usar sensibilidad para seleccionar signo deseado. Descriptivos de grupos pequeños no sostienen comparación inferencial.",
    )
    section(
        "20. Síntesis integrada de cinco intervalos",
        "Integra seguimiento, tiempo y cambios individuales sin una estimación global única. Todos los periodos reciben cobertura; rupturas K claramente separadas.",
        "tabla([{'intervalo':f\"{z['origen']}–{z['destino']}\",'meses_mediana':z['duracion_analitica']['mediana'],'N_cohorte':z['seguimiento']['N_origen'],'N_principal':z['seguimiento']['N_principal'],'cambio_medio':z['cambios']['cambio']['media'],'pct_aumenta':z['cambios']['pct_aumenta'],'pct_disminuye':z['cambios']['pct_disminuye'],'K_condicionada':z['K_comparable_condicionada']} for z in r['intervalos']]); display(Markdown('\\n\\n'.join(conclusions(r))))",
        "Misma persona observada permite diferenciar cambios de composición. No demuestra causalidad, incidencia clínica ni continuidad económica no observada.",
    )
    cells.append(
        md("""## 21. Limitaciones, conclusiones exploratorias y siguientes preguntas

Los conteos completos tienen comparabilidad operacional condicionada al producto construido, no invariancia psicométrica. Documentación actual usa diagramas2024 como ejemplo; números y literalidad de preguntas originales2001–2021 no se dan por certificados. Se conserva la advertencia v2/v3. Soledad y CES-D no son diagnósticos. Muestra sin diseño/ponderación validada; mortalidad, sustitutos, faltantes y ND seleccionan las trayectorias. IC puntuales sin agrupación por hogar ni multiplicidad. No inferencia global con pares repetidos.

La pregunta transversal03 no equivale a cambio individual. Las medias de cambio pequeñas deben leerse junto a fluctuaciones y distribución. Los ajustes por composición, síntomas basales y soporte no son equivalentes ni eliminan regresión a la media.

**Potencial para Ciencia de Datos y Actuaría:** distinguir heterogeneidad entre personas de variación dentro de personas; estudiar selección y estados de observación, y construir contratos longitudinales auditables. Preguntas futuras: persistencia de síntomas según respuestas económicas observadas; diferencias por escolaridad/sexo; influencia de mortalidad y modalidad en lo que puede medirse. No se adopta pregunta definitiva, predicción ni TICS.

## 22. Reproducibilidad y validación

`python scripts/run_longitudinal_health.py` calcula exclusivamente esta ampliación. `python scripts/build_longitudinal_health_notebook.py` genera este notebook y copia ejecutada local. `python scripts/validate_longitudinal_health.py` verifica denominadores, signos, matrices, auditoría y protección. Resultados completos en `data/interim/trayectorias_pensiones_salud/`; interpretación selectiva en el único informe general. Bases, notebooks01–03 y LaTeX intactos.""")
    )
    notebook = nbformat.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {"display_name": "Python (myenv)", "language": "python", "name": "myenv"},
            "language_info": {"name": "python", "version": "3.11"},
        },
    )
    path = PROJECT_ROOT / "notebooks/04_TRAYECTORIAS_PENSIONES_SALUD.ipynb"
    ledger = OUTPUT / "notebook_fuente.json"
    if path.exists():
        expected = json.loads(ledger.read_text())["sha256"] if ledger.exists() else None
        if sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("Notebook04 editado manualmente; no sobrescribir")
    nbformat.write(notebook, path)
    ledger.write_text(json.dumps({"sha256": sha256(path.read_bytes()).hexdigest()}, indent=2))
    NotebookClient(
        notebook, timeout=1200, kernel_name="myenv", resources={"metadata": {"path": str(PROJECT_ROOT)}}
    ).execute()
    execution = INTERIM_DIR / "notebooks_ejecutados/04_TRAYECTORIAS_PENSIONES_SALUD_ejecutado.ipynb"
    nbformat.write(notebook, execution)
    verify_inputs(allow_report=True)
    print("Notebook04 generado y ejecutado desde cero:", len(cells), "celdas; figuras", len(figures))


if __name__ == "__main__":
    build()
