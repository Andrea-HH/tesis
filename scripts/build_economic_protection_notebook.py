"""Notebook06 independiente, cálculos reproducibles y copia ejecutada local."""

import json
from hashlib import sha256

import nbformat
from nbclient import NotebookClient

from tesis_enasem.economic_protection import NOTEBOOK, OUTPUT, save_json, verify_inputs
from tesis_enasem.economic_protection_outputs import make_figures, readable_prose
from tesis_enasem.project_paths import INTERIM_DIR, PROJECT_ROOT


def build() -> None:
    """Protege ediciones manuales y ejecuta solo06 sin recalcular01–05."""
    verify_inputs()
    r = json.loads((OUTPUT / "resultados.json").read_text())
    save_json(OUTPUT / "figuras.json", make_figures(r))
    md, code = nbformat.v4.new_markdown_cell, nbformat.v4.new_code_cell
    cells = [
        md("""# 06 · Cobertura y monto de vías de protección económica, ENASEM2001–2021

**Pregunta de tesis propuesta por la autora:** ¿qué tanto es consistente la expansión de pensiones/apoyos con reducción de brechas de cobertura/monto, quién permanece sin vía propia identificada y cómo cambia la lectura al considerar muerte y no observación?

La idea 'se iguala acceso pero no monto/suficiencia' es hipótesis por verificar. Este análisis describe muestra, no cobertura nacional ni efecto de políticas. Mortalidad y selección son sensibilidades del eje económico.

**Objetivo independiente:** unión propiaK/A y tipología completa de personas en2018/2021, brechas dentro de ronda, distribución nominal por evento y suma parcial por persona, persistencia de negativasK en ventanas comparables. Reutiliza integración/titularidad y lógica05; no modifica notebooks01–05 ni bases. No panel balanceado.

**Elección de la autora:** principal solo directas; respuestas válidas por sustituto como sensibilidad. Población60+ viva por visita, con N excluido por modalidad reportado. A admite dinero/especie; cobertura identificada no garantiza ingreso monetario."""),
        code("""import json
import pandas as pd
from IPython.display import display, Markdown, Image
from tesis_enasem.economic_protection import analyze, OUTPUT, verify_inputs, GROUPS
from tesis_enasem.economic_protection_outputs import wave, conclusions
from tesis_enasem.project_paths import RESULTS_DIR, PROJECT_ROOT
verify_inputs()
r = analyze()  # reproduce solo06 desde bases verificadas; no rehace01–05
stored = json.loads((OUTPUT/'resultados.json').read_text())
assert r == stored, 'Agregados06 no corresponden al código/insumos actuales'
figuras = json.loads((OUTPUT/'figuras.json').read_text())
pd.set_option('display.max_columns',None)
pd.set_option('display.max_rows',None)
pd.set_option('display.float_format',lambda x:f'{x:.3f}')
def tabla(rows):
    display(pd.json_normalize(rows,sep='.'))
def figura(key):
    f=next(x for x in figuras if x['clave']==key)
    display(Image(filename=str(RESULTS_DIR/f['archivo'])))
    display(Markdown('**Nota:** '+f['nota']))
def principal():return [z for z in r['rondas'] if z['analisis']=='principal']
"""),
    ]

    def section(title: str, question: str, source: str, reading: str) -> None:
        cells.extend(
            [
                md("## " + title + "\n\n" + question),
                code(source),
                md("**Interpretación y límites:** " + reading),
            ]
        )

    section(
        "1. Fuentes, nombres, códigos y poblaciones",
        "Maestro99,676/27,171 intacto. ID cunicah:np, persona+ronda única; LEFT1:1. Edad por visita, escolaridad al inicio, localidad a100mil. Ocupación4 agrega retiro/incapacidad/no trabajo. est_conyugal no acredita pareja residente. imp_neto es stock compartido y no se usa como ingreso.",
        "contrato=json.loads((PROJECT_ROOT/'diccionarios/contrato_proteccion_economica.json').read_text()); tabla([r['metodologia']]); tabla(r['contratos_originales']); tabla([{'variable':k,'definicion':v} for k,v in contrato['variables'].items()]); tabla([{'ronda':z['ronda'],**z['cobertura'][0],'N_proxy_K_original_conocida':z['N_proxy_K_original_conocida']} for z in principal()])",
        "N60=56,004 observaciones/18,754personas; sumas entre rondas no son individuos distintos. Sustitutos no se borran: recepción válida fuera del principal. Elegibilidad operativa exige60+ viva/directa; no certifica elegibilidad legal.",
    )
    section(
        "2. Comparabilidad antes de comparar",
        "K condicionada2001–03,2012–15,2018–21; A condicionada2003–12,2012–15,2015–18. Unión exige ambas: solo2012–15 cumple continuidad condicional conjunta. No extrapolar nombres de programas/monto/modalidad.",
        "tabla(r['comparabilidad'])",
        "Brechas dentro de ronda describen ese instrumento. Cambios de brechas entre rupturas también pueden reflejar medición diferencial/composición; no quedan homologados por restar porcentajes. A2021 incorpora vejez explícita; no atribuir salto exclusivamente a política.",
    )
    section(
        "3. Tipología: conteos generales2018/2021",
        "Ocho combinaciones con pareja confirmada, cuatro propiasK/A sin pareja residente, desconocidos de contexto/recepción y sustitutos aparte. Se agregan cónyuge+A y las tres vías, omitidas inicialmente. SoloA es propia, no A del cónyuge.",
        "tabla([{'ronda':z['ronda'],**a} for z in principal() for a in z['tipologia'] if a['dimension']=='General']); figura('tipologia')",
        "Cada observación pertenece a una categoría/contexto. No pareja residente no es pensión negativa imputada. NegativasK/A sin pareja no son 'ninguna de tres' por defecto. Ninguna vía identificada no equivale a falta de protección integral. Unión conocida puede tener tipologíaND si falta alguna respuesta.",
    )
    section(
        "4. Tipología por sexo, edad, escolaridad, localidad y ocupación",
        "N conocido, NND, Nsinpareja y proporción del grupo/contexto; distribución general y por perfiles.",
        "for dimension in GROUPS:\n    display(Markdown('### '+dimension))\n    df=pd.DataFrame([{'ronda':z['ronda'],**a} for z in principal() for a in z['tipologia'] if a['dimension']==dimension])\n    display(df.pivot_table(index=['grupo','contexto','categoria'],columns='ronda',values='N',fill_value=0))\n    tabla(df[['ronda','grupo','contexto','N_grupo','N_contexto','N_conocido_contexto','N_ND_contexto','N_sin_pareja_grupo']].drop_duplicates().to_dict('records'))",
        "Cero en conteos significa cero personas de esa categoría, nunca respuesta faltante sustituida. No juntar contextos como supuesta pensión de hogar.",
    )
    section(
        "5. Cobertura propia y brechas en seis rondas",
        "K∨A: sí si alguna sí; no solo ambas no; restoND. Tasas usan distintos N conocidos; contrasteK frente a unión exige ambas conocidas, mismo soporte.",
        "for dimension in ['General',*GROUPS]:\n    display(Markdown('### '+dimension))\n    tabla([{'ronda':z['ronda'],**a} for z in principal() for a in z['cobertura'] if a['dimension']==dimension])\nfigura('cobertura2021'); figura('brechas')",
        "ND no es negativa. Límites entre elegibles son extremos lógicos, no IC. Sin pesos/diseño no inferencia nacional. A puede ser especie. Diferencias2021 sexo/localidad se atenúan con unión, pero edad se separa más.",
    )
    section(
        "6. Brechas y sensibilidad por modalidad",
        "Todas las comparaciones dirigidas de pares, no selección por mayor brecha. Principal frente a respuestas válidas por sustituto con cada N conocido.",
        "tabla([{'ronda':z['ronda'],**a} for z in principal() for a in z['brechas']]); tabla([{'ronda':z['ronda'],'analisis':z['analisis'],**a} for z in r['rondas'] for a in z['cobertura'] if a['dimension'] in ['General','sexo_grupo','localidad_grupo']])",
        "Contraste de modalidades puede reflejar composición/selección. No se corrigen directas con sustitutos. Tipologías y cobertura completa de sensibilidad en r['rondas'].",
    )
    section(
        "7. Montos: evento frente a persona y vía",
        "Originales observados de mes normal. Varios eventos por receptor; suma parcial personal no es mediana por evento ni ingreso total. Cotejo exacto sidecar, no reemplazo. No distribuir instituciones, sumarK+A ni imputados.33firmas2015 siguen sin corregir.",
        "tabla([{'via':k,**v} for k,v in r['auditoria_eventos'].items()]); tabla([a for a in r['montos'] if a['dimension']=='General']); figura('montos2021')",
        "Nreceptores/personas con monto/todos eventos capturados con monto/parciales/eventosND separados. Todos capturados no prueba todos los beneficios reales. Cero observado se conserva; faltante no es cero. A dinero/especie no separable.",
    )
    section(
        "8. Montos por perfil y tipología",
        "Cuantiles/medias nominales por vía dentro de ronda; todas las rondas y perfiles en agregados,2018/2021 se muestran detallados.",
        "for dimension in GROUPS:\n    display(Markdown('### '+dimension))\n    tabla([a for a in r['montos'] if a['dimension']==dimension and a['ronda'] in [2018,2021]])\ntabla([a for a in r['montos'] if a['dimension']=='grupo_tipologia']); tabla(r['montos_conyuge_contextuales'])",
        "Cónyuge se presenta como monto contextual de otra persona con pareja confirmada, no ingreso propio/transferencia comprobada. MedianaA común no implica distribución igual o suficiencia. Comparaciones entre años nominales, no reales.",
    )
    section(
        "9. Deflactación/suficiencia: preparada, no ejecutada",
        "Confirmar INPC (fuente/base/frecuencia) y umbral mensual compatible con año/unidad/localidad. evaluate_sufficiency exige fuentes confirmadas y cobertura de índices/umbrales, sin valores supuestos.",
        "from tesis_enasem.economic_protection import evaluate_sufficiency\nconfig=contrato['config_suficiencia']\nassert not config['fuente_indice_confirmada']\nassert not r['metodologia']['deflactacion_ejecutada']\ndisplay(Markdown('**Estado: bloqueada por fuentes y umbral pendientes.**'))\ntabla([config])",
        "No deflactación ni proporción suficiente/insuficiente ejecutadas. Línea de pobreza requiere localidad/unidad; salario diario conversión mensual documentada. Comparar prestación parcial con referencia no diagnostica pobreza del hogar.",
    )
    section(
        "10. Seguimiento de negativaK",
        "Basal60+, negativaK conocida directa.2012–15/2018–21 principales;2001–03 sensibilidad. Destino conserva edad discordante. No panel balanceado; negativaK no excluyeA u otros recursos.",
        "tabla([{'intervalo':f\"{z['origen']}–{z['destino']}\",'N_cohorte':z['N_cohorte_60'],'N_directa_basal':z['N_elegible_basal'],'meses_N':z['meses_N'],'meses_mediana':z['meses_mediana'],'meses_min':z['meses_min'],'meses_max':z['meses_max'],**z['grupos'][0]} for z in r['seguimiento_principal']]); figura('seguimiento')",
        "Estados disjuntos: negativa viva,K observada,muerte registrada,ausencia,vivoKND/modalidad yotro no clasificable. Sustituto no es ausencia. Registro sobre fallecido no fecha/mortalidad completa. Inconsistencia fallecido→vivo del maestro conservada sin reasignar.",
    )
    section(
        "11. Persistencia, cotas y cobertura seleccionada",
        "Negativa entre sobrevivientes conocidos y negativa viva por cohorte basal son estimandos distintos. Cotas no asignan recepción a fallecidos; extremos entre ausentes/medicionesND. Mortalidad registrada D/N a(D+U)/N.",
        "tabla([{'intervalo':f\"{z['origen']}–{z['destino']}\",**a} for z in r['seguimiento_principal'] for a in z['grupos']]); tabla([{'intervalo':f\"{z['origen']}–{z['destino']}\",'cohorte':z['cobertura_basal_cohorte'],'retenidos':z['cobertura_basal_retenidos']} for z in r['seguimiento_principal']]); tabla([{'intervalo':f\"{z['origen']}–{z['destino']}\",**z['grupos'][0]} for z in r['seguimiento_sensibilidad_sustitutos']])",
        "Reaparición viva y registro fallecido posterior separados; pueden solaparse por anomalías, no fechan estado en visita ausente.2021 sin búsqueda posterior dentro de estas rondas. Cotas no son IC ni correcciones. Solo2012–15 lectura conjuntaK/A condicionada.",
    )
    section(
        "12. Síntesis y siguiente decisión",
        "Conservar contradicciones, montos faltantes y rupturas. Entender cobertura antes de precios/umbral; predicción opcional requiere estimando/etiquetas defendibles.",
        "display(Markdown('\\n\\n'.join(conclusions(r)))); verify_inputs()",
        "No modelos opcionales, KM/Cox/IPW, política causal, alerta temprana oQ1. Validar medición/diseño/fuentes; no convertir sobrevivientes en población inicial ni imputar prestaciones a fallecidos.",
    )
    cells.append(
        md("""## 13. Reproducción y productos

`python scripts/run_economic_protection.py`; `python scripts/build_economic_protection_notebook.py`; `python scripts/validate_economic_protection.py`; `python scripts/export_economic_protection_report.py`; `python scripts/build_report_pdf.py`; `python scripts/build_report_pdf.py --check`.

Agregados completos en `data/interim/cobertura_proteccion_economica/resultados.json`, figuras en `resultados/figuras/`, contrato/configuración en `diccionarios/contrato_proteccion_economica.json`. Fuente sin outputs; copia ejecutada en `data/interim/notebooks_ejecutados/`. Único informe acumulativo, sin informes nuevos. Bases, notebooks01–05 y manuscrito intactos; sin Git/GitHub.""")
    )
    for cell in cells:
        if cell.cell_type == "markdown":
            cell.source = readable_prose(cell.source)
    n = nbformat.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {"name": "myenv", "display_name": "Python (myenv)", "language": "python"},
            "language_info": {"name": "python", "version": "3.11"},
        },
    )
    source = PROJECT_ROOT / "notebooks" / NOTEBOOK
    ledger = OUTPUT / "notebook_fuente.json"
    if source.exists() and (
        not ledger.exists()
        or sha256(source.read_bytes()).hexdigest() != json.loads(ledger.read_text())["sha256"]
    ):
        raise ValueError("Notebook06 editado; no sobrescribir")
    nbformat.write(n, source)
    save_json(ledger, {"sha256": sha256(source.read_bytes()).hexdigest()})
    NotebookClient(
        n, timeout=1200, kernel_name="myenv", resources={"metadata": {"path": str(PROJECT_ROOT)}}
    ).execute()
    nbformat.write(n, INTERIM_DIR / "notebooks_ejecutados" / NOTEBOOK.replace(".ipynb", "_ejecutado.ipynb"))
    verify_inputs()
    print("Notebook06 ejecutado:", len(cells), "celdas")


if __name__ == "__main__":
    build()
