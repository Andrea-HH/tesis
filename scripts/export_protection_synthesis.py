"""Integra la lectura06/07 en el único informe; no crea notebook o informe paralelo."""

from __future__ import annotations

import json
import re
from hashlib import sha256
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from tesis_enasem.protection_synthesis import (
    OUTPUT, PROFILES, QUESTION, coverage, money, read_inputs, save_json,
    synthesize, validate, verify_inputs, wave,
)
from tesis_enasem.project_paths import INTERIM_DIR, PROJECT_ROOT, RESULTS_DIR
from tesis_enasem.monetary_policy_outputs import readable


def fmt(value: Any, digits: int = 2) -> str:
    """Presenta cifras sin convertir faltantes en cero."""
    return "No identificable" if value is None else f"{value:,.{digits}f}" if isinstance(value,float) else str(value)


def make_figure(r: dict) -> dict:
    """Visualiza solo los dos contrastes ya calculados, con tres escalas separadas."""
    plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False})
    brown,teal=plt.get_cmap("BrBG")(.12),plt.get_cmap("BrBG")(.88)
    fig,axes=plt.subplots(2,3,figsize=(12,7.4))
    for row,z in enumerate(r["reproduccion"]):
        p=next(x for x in r["periodos"] if (x["origen"],x["destino"],x["via"])==(z["origen"],z["destino"],z["via"]))
        labels=[str(z["origen"]),str(z["destino"])]
        values=[p["cobertura_inicial"],p["cobertura_final"]]
        ax=axes[row,0];bars=ax.bar(labels,values,color=[brown,teal],width=.55)
        ax.bar_label(bars,labels=[f"{x:.2f}%" for x in values],padding=4)
        ax.set_ylim(0,100);ax.set_ylabel("Recepción / respuestas conocidas (%)")
        ax.set_title(z["via"]+" propia: cobertura")
        ax.set_xlabel(f"N conocido: {p['N_cobertura_inicial']:,} / {p['N_cobertura_final']:,}",fontsize=9)
        for col,unit in [(1,"nominal"),(2,"real")]:
            vals=[z[k][unit]["mediana"] for k in ("inicial","final")]
            ax=axes[row,col];bars=ax.bar(labels,vals,color=[brown,teal],width=.55)
            ax.bar_label(bars,labels=[f"${x:,.0f}" for x in vals],padding=4)
            ax.set_ylim(0,max(vals)*1.28)
            ax.set_ylabel("Pesos nominales / mes" if unit=="nominal" else "Pesos de septiembre de 2026 / mes")
            ax.set_title(z["via"]+" propia: mediana "+unit)
            ax.set_xlabel(f"N monto: {z['inicial'][unit]['N']:,} / {z['final'][unit]['N']:,}",fontsize=9)
    title="Cobertura y poder adquisitivo: dos contrastes condicionados"
    note="Directas60+ por visita. Cobertura: N con recepción conocida; monto: receptores con suma mensual parcial válida.\nMuestras transversales diferentes, sin pesos. A incluye dinero/especie. Precio principal: año previo a entrevista real."
    fig.suptitle(title,fontsize=14,y=.98)
    fig.text(.02,.015,note.replace("Directas60+","Directas 60+"),fontsize=8)
    fig.tight_layout(rect=[0,.085,1,.94])
    file="figuras/sintesis_proteccion__cobertura_poder_adquisitivo.png"
    fig.savefig(RESULTS_DIR/file,dpi=210);plt.close(fig)
    return dict(titulo=title,archivo=file,nota=note.replace("Directas60+","Directas 60+"),
                sha256=sha256((RESULTS_DIR/file).read_bytes()).hexdigest())


def export() -> None:
    """Verifica primero, escribe después y preserva todos los bloques previos."""
    from tesis_enasem.release_guard import block_legacy_export
    block_legacy_export()
    r=synthesize();validate(r);save_json(OUTPUT/"resultados.json",r)
    r6,r7=read_inputs()
    fig=make_figure(r)
    save_json(OUTPUT/"figuras.json",[fig])
    products=[]
    source="**Fuente y procedencia:** ENASEM; [notebook 06](../notebooks/06_COBERTURA_PROTECCION_ECONOMICA.ipynb), bloques 5–12; [notebook 07](../notebooks/07_POLITICAS_MONTOS_SUFICIENCIA.ipynb), bloques 4–15; [agregados 06](../data/interim/cobertura_proteccion_economica/resultados.json), [agregados 07](../data/interim/politicas_montos_suficiencia/resultados.json) y [cotejo de esta síntesis](../data/interim/sintesis_proteccion_economica/resultados.json)."
    def table(title: str, rows: list[dict], columns: list[tuple[str,str]], purpose: str, note: str) -> str:
        title=readable(title)
        products.append(dict(tipo="tabla",titulo=title,notebook="notebooks/07_POLITICAS_MONTOS_SUFICIENCIA.ipynb",
            notebooks=["notebooks/06_COBERTURA_PROTECCION_ECONOMICA.ipynb","notebooks/07_POLITICAS_MONTOS_SUFICIENCIA.ipynb"],
            bloque="Síntesis06/07",pregunta_aporte=purpose,fuente="data/interim/sintesis_proteccion_economica/resultados.json",contribucion="sintesis06_07"))
        def cell(z: dict,k: str) -> str:
            return fmt(z.get(k)).replace("|","/").replace("\n"," ")
        return f"**Cuadro 0. {title}**\n\n**Pregunta y aporte:** {purpose}\n\n| "+" | ".join(t for k,t in columns)+" |\n| "+" | ".join("---" for _ in columns)+" |\n"+"\n".join("| "+" | ".join(cell(z,k) for k,t in columns)+" |" for z in rows)+f"\n\n**Nota:** {note}\n\n{source}\n\n"
    def period(a: int,b: int,via: str) -> dict:
        return next(x for x in r["periodos"] if (x["origen"],x["destino"],x["via"])==(a,b,via))
    body=f"""### 10.4 Síntesis de acceso, poder adquisitivo y prestación frente al umbral

**Pregunta central:** {QUESTION}

**Respuesta integrada.** Las dimensiones evolucionaron de manera diferente en las ventanas que permiten comparación condicionada. En 2012–2015 aumenta la recepción identificada K, A y su unión, pero las medianas reales de las sumas personales parciales K y A disminuyen. En 2015–2018 aumenta la recepción A y disminuye su mediana real. En 2018–2021 K ofrece el contraste opuesto: su tasa muestral baja ligeramente y su mediana real aumenta. El acceso y el monto entre receptores miden poblaciones y resultados distintos; no constituyen un único indicador de bienestar. Las brechas se estrechan en algunos perfiles y se amplían o invierten en otros. La evidencia respalda una respuesta específica por vía, periodo y grupo, sin identificar una convergencia general de protección económica entre 2001 y 2021.

Esta síntesis utiliza exclusivamente los resultados ya calculados en 06/07 y la cronología oficial documentada. Conserva septiembre de 2026 como referencia común, con INPC 146.075. No añade notebook, microanálisis, imputación, modelo ni hipótesis causal. Las cifras no ponderadas describen la muestra. A incluye dinero y especie; K no acredita contributividad. La unión de recepción K/A no significa un ingreso monetario total ni tiene un monto que pueda obtenerse sumando medianas.

**Reproducción de los dos ejemplos.** Ambos cambios solicitados se recuperan de la sección 7 de 07, celda física 22: variación porcentual de la mediana transversal de la suma mensual personal observada parcial. El denominador del cambio porcentual es la mediana inicial; el N de observaciones válidas se documenta aparte. Las personas de ambas rondas no tienen que ser las mismas. No son montos por evento ni una prestación identificada como PAM, Bienestar o una pensión contributiva.

"""
    for z in r["reproduccion"]:
        a,b,via=z["origen"],z["destino"],z["via"]
        x,y=z["inicial"],z["final"]
        c0,c1=coverage(r6,a),coverage(r6,b)
        body+=f"**{via} propia, {a}–{b}.** Se incluyen personas vivas de 60+ por visita, con entrevista directa, recepción propia afirmativa y al menos un monto observado válido de esa vía. En {a}: {x['N_monto']:,} personas con monto de {x['N_receptores']:,} receptoras, entre {c0['N_elegible']:,} directas elegibles; en {b}: {y['N_monto']:,}/{y['N_receptores']:,}, entre {c1['N_elegible']:,} directas elegibles. Quedan {x['N_receptores_sin_monto']:,}/{y['N_receptores_sin_monto']:,} receptoras sin monto, respectivamente. El campo `{z['codigo_monto']}` suma solo los eventos captados válidos; no acredita todas las prestaciones ni ingreso total.\n\n"
        body+=f"Las medianas nominales son ${x['nominal']['mediana']:,.2f} y ${y['nominal']['mediana']:,.2f}: `100 × ({y['nominal']['mediana']:.2f}/{x['nominal']['mediana']:.2f} − 1)` = **{z['cambio_nominal_pct']:+.2f}%**. Las medianas constantes son ${x['real']['mediana']:,.6f} y ${y['real']['mediana']:,.6f}: `100 × ({y['real']['mediana']:.6f}/{x['real']['mediana']:.6f} − 1)` = **{z['cambio_real_pct']:+.6f}%**, que se presenta como **{z['cambio_real_pct']:+.2f}%**. Son pesos por mes de septiembre de 2026. Las cantidades ya estaban mensualizadas como mes normal; no se vuelven a dividir por dos debido a la entrega bimestral de determinados programas.\n\n"
        facts=[]
        for p in z["fecha_precio"]:
            facts.append(f"ronda {p['ronda']}, entrevista {p['ano_entrevista']}: año de precios {p['ano_precio_principal']}, INPC medio {p['inpc_original']:.6f}, factor {p['factor']:.6f} (N de directas {p['N']:,})")
        body+="**Fechas y deflactor:** "+"; ".join(facts)+". Se actualizó cada importe antes de calcular los cuantiles. El mes de pago no está identificado; año calendario previo a la entrevista real es un criterio explícito para interpretar año pasado. En 2012 hay además una directa sin año válido, conservada sin actualización; los N con fecha válida pueden diferir de los nominales.\n\n"
        paired=z["pares"]
        body+=f"**Sensibilidad y personas seguidas:** con doce meses anteriores al mes real el cambio de mediana es {z['sensibilidad_12m_pct']:+.2f}%; con promedio del año de entrevista, {z['sensibilidad_ano_entrevista_pct']:+.2f}%. Los extremos de meses posibles del año previo dan un rango descriptivo de {z['sensibilidad_extremos_min_pct']:+.2f}% a {z['sensibilidad_extremos_max_pct']:+.2f}%, siempre negativo. No es un intervalo de confianza. Entre {paired['N_receptores_ambas_monto']:,} receptoras con monto válido en ambas visitas, la **mediana del cambio individual** es ${paired['cambio_nominal_receptores_ambas']['mediana']:+,.2f} nominal y ${paired['cambio_real_receptores_ambas']['mediana']:+,.2f} real: otro estimando y una selección distinta. El resultado transversal no demuestra una pérdida para cada individuo.\n\n"
    body+="El ejemplo K agrega jubilación, viudez, invalidez y otras pensiones captadas por K. Cambian los slots y la composición de instituciones entre 2012 y 2015; el aumento de registros de programas agrupados puede coexistir con una menor mediana entre receptores. El ejemplo A agrega distintos donativos propios, sin identificar PAM individualmente en ambas rondas; 2018 pasa a captar eventos y programas. La comparabilidad es condicionada, no una invariancia completa de medición. Estos ejemplos respaldan H2, pero no bastan por sí solos para validar las restantes proposiciones.\n\n"
    integration=[]
    policies={
        (2001,2003):"Apoyos diversos y antecedentes locales; la ley DF de noviembre2003 es posterior a las entrevistas2003.",
        (2003,2012):"70 y Más desde2007; expansión territorial2008/2009/2012. A no identifica el programa individual.",
        (2012,2015):"PAM:65+ desde2013; $525 y $580 desde2014. K/A incluyen otras instituciones o programas.",
        (2015,2018):"PAM mantiene $580; A incluye otros apoyos, dinero/especie y cambios de captación.",
        (2018,2021):"Bienestar: cambios de edad e importe; A incorpora código5. No adjudicar el cambioK a esa reforma.",
    }
    defended={
        (2001,2003,"K"):"Cobertura y mediana real K mayores; brecha por sexo mayor. No igualación general.",
        (2003,2012,"A"):"Cobertura y mediana real A mayores; no identifica efecto federal ni convergencia de umbral total.",
        (2012,2015,"K"):"Más recepción K y menor mediana real; determinadas brechas de acceso menores, brechas monetarias mayores.",
        (2012,2015,"A"):"Más recepción A; mediana nominal mayor y real ligeramente menor; proporción mediana de LPI menor.",
        (2012,2015,"KA"):"La unión crece y la brecha por sexo se estrecha; edad, escolaridad y localidad no convergen uniformemente.",
        (2015,2018,"A"):"Más recepción A y menor mediana real; no se puede extender al conjunto K/A.",
        (2018,2021,"K"):"Tasa K ligeramente menor, mediana real mayor y brecha monetaria por sexo mayor.",
    }
    for z in r["periodos"]:
        if not z["comparable"]:continue
        a,b,via=z["origen"],z["destino"],z["via"]
        item=dict(periodo=f"{a}–{b}",via=via,politica=policies[(a,b)],
            cobertura=f"{z['cobertura_inicial']:.2f}% → {z['cobertura_final']:.2f}% ({z['cambio_cobertura_pp']:+.2f}pp); N={z['N_cobertura_inicial']:,}/{z['N_cobertura_final']:,}",
            brecha_cov=f"H−M: {z['brecha_cobertura_sexo']['inicial']:.2f} → {z['brecha_cobertura_sexo']['final']:.2f}pp",
            poblacion="60+ directas por visita; recepción conocida por vía.",conclusion=defended[(a,b,via)])
        if via=="KA":
            item.update(nominal="No identificable: no monto de unión",real="No identificable: no sumar K+A",brecha_real="No identificable para unión; componentes K/A separados",umbral="No identificable para unión",comparabilidad="Solo esta ventana tiene continuidad conjunta condicionada K y A.")
        else:
            x,y=z["inicial"],z["final"]
            item.update(nominal=f"${x['nominal']['mediana']:,.0f} → ${y['nominal']['mediana']:,.0f} ({z['cambio_nominal_pct']:+.2f}%)",
                real=f"${x['real']['mediana']:,.0f} → ${y['real']['mediana']:,.0f} ({z['cambio_real_pct']:+.2f}%)",
                poblacion=item["poblacion"]+f" Montos: N={x['real']['N']:,}/{y['real']['N']:,} entre receptores.",
                comparabilidad="Condicionada por instrumento, composición y fecha; no efecto causal ni cambios de las mismas personas.")
            g=next(g for g in r["brechas_por_perfil"] if (g["origen"],g["destino"],g["via_cobertura"],g["dimension"])==(a,b,via,"sexo_grupo"))[via]
            item["brecha_real"]=f"H−M: ${g['brecha_real_inicial']:,.0f} → ${g['brecha_real_final']:,.0f}; razónH/M {g['razon_real_inicial']:.2f} → {g['razon_real_final']:.2f}"
            if (a,b)==(2003,2012):item["umbral"]="No identificable globalmente: geografía asignable2003 selecciona ciudades grandes;2012 incluye otras localidades."
            else:
                item["umbral"]=f"Mediana prestación/LPI {x['umbral']['mediana_pct']:.2f}% → {y['umbral']['mediana_pct']:.2f}%; N={x['umbral']['N']:,}/{y['umbral']['N']:,}"+ ("; solo≥100mil" if a==2001 else "")
        integration.append(item)
    integration.append(dict(periodo="2001–2021",via="Conjunto",politica="Expansión normativa documentada; cambios de instrumentos.",cobertura="No identificable como serie homogénea.",brecha_cov="No identificable como cierre uniforme.",nominal="No monto único de protección propia.",real="No serie agregada K+A defendible.",brecha_real="No identificable de forma homogénea.",umbral="No suficiencia integral de persona/hogar.",poblacion="Los universos de cada vía y de montos válidos son distintos.",comparabilidad="Rupturas K2003–12/K2015–18 y A2001–03/A2018–21.",conclusion="Respuesta parcial por ventanas y perfiles; no estimar un único efecto o cierre2001–2021."))
    body+=table("Integración de cobertura, monto y referencia económica en periodos defendibles",integration,
        [("periodo","Periodo"),("via","Vía"),("politica","Cambio de política documentado"),("cobertura","Recepción y denominador"),("brecha_cov","Brecha cobertura sexo"),
         ("nominal","Mediana nominal mensual"),("real","Mediana real mensual"),("brecha_real","Brecha monetaria real"),("umbral","Referencia de LPI"),
         ("poblacion","Población de cada indicador"),("comparabilidad","Comparabilidad"),("conclusion","Conclusión defendible")],
        "Determinar si mayor acceso coincide con mayores recursos centrales y menores brechas.",
        "Montos: sumas personales mensuales observadas parciales, pesos de septiembre2026. Cada vía de cobertura usa su N conocido; no sumar porcentajes. La unión exige ambas negativas para no, una afirmativa basta para sí; restantes ND. Brecha H−M firmada: hombres menos mujeres. N de cobertura no es N monetario. LPI mensual por persona del periodo original, rural/urbana2500; no pobreza ni ingreso completo. Los campos no identificables permanecen explícitos. Los cambios a través de rupturas no se interpretan como tendencias homologadas.")
    products.append(dict(tipo="figura",titulo=fig["titulo"],notebook="notebooks/07_POLITICAS_MONTOS_SUFICIENCIA.ipynb",
        notebooks=["notebooks/06_COBERTURA_PROTECCION_ECONOMICA.ipynb","notebooks/07_POLITICAS_MONTOS_SUFICIENCIA.ipynb"],bloque="Síntesis06/07",
        pregunta_aporte="Distinguir el acceso del poder adquisitivo con escalas y poblaciones explícitas.",archivo="resultados/"+fig["archivo"],sha256=fig["sha256"],contribucion="sintesis06_07"))
    body+=f"**Figura 0. {fig['titulo']}**\n\n**Pregunta y aporte:** Distinguir acceso, pesos nominales y pesos constantes en los dos ejemplos.\n\n![Figura 0: {fig['titulo']}]({fig['archivo']})\n\n**Nota:** {fig['nota']}\n\nLas barras reutilizan resultados ya calculados. Las escalas monetarias son separadas; los N indican poblaciones diferentes. No se interpreta el aumento del número de receptores como incremento de recursos de cada persona.\n\n{source}\n\n"
    body+="**Desigualdades: dirección, magnitud y composición.** Una brecha firmada describe qué grupo tiene más recepción; su valor absoluto describe la distancia entre grupos. Pasar de una ventaja positiva a una negativa no basta para hablar de convergencia. Se usan medianas, diferencias de medianas, razones e IQR ya disponibles, que reducen el dominio de importes extremos sobre la lectura. No se calcula Gini con seis cuantiles, se recortan valores ni se inventan intervalos de confianza. IQR/mediana es dispersión relativa robusta entre receptores, no desigualdad total en toda la población.\n\n"
    contrasts=[]
    for dim,g1,g2 in PROFILES:
        z=next(z for z in r["brechas_por_perfil"] if (z["origen"],z["destino"],z["via_cobertura"],z["dimension"])==(2012,2015,"KA",dim))
        kk=next(z for z in r["brechas_por_perfil"] if (z["origen"],z["destino"],z["via_cobertura"],z["dimension"])==(2012,2015,"K",dim))
        m=z["K"];c=z["brecha_cobertura"];k=kk["brecha_cobertura"]
        contrasts.append(dict(perfil=f"{g1} / {g2}",gapK=f"{k['inicial']:.2f} → {k['final']:.2f}",
            gapKA=f"{c['inicial']:.2f} → {c['final']:.2f}",lectura=c["lectura"]+(" e invierte dirección" if c["cambia_signo"] else ""),
            Ncov="2012:"+"/".join(f"{p['N_KA_conocido']:,}" for p in z['cobertura_inicial'])+";2015:"+"/".join(f"{p['N_KA_conocido']:,}" for p in z['cobertura_final']),
            Nmoney="2012:"+"/".join(f"{p['N_monto']:,}" for p in m['inicial'])+";2015:"+"/".join(f"{p['N_monto']:,}" for p in m['final']),
            gapNom=f"${m['brecha_nominal_inicial']:,.0f} → ${m['brecha_nominal_final']:,.0f}",
            gapReal=f"${m['brecha_real_inicial']:,.0f} → ${m['brecha_real_final']:,.0f}",ratioReal=f"{m['razon_real_inicial']:.2f} → {m['razon_real_final']:.2f}"))
    body+=table("Brechas de acceso y del componente K entre perfiles en2012–2015",contrasts,
        [("perfil","Grupo1 / grupo2"),("gapK","Brecha K en pp"),("gapKA","Brecha unión en pp"),("lectura","Magnitud de brecha unión"),("Ncov","N unión conocidos g1/g2"),
         ("Nmoney","N monto K g1/g2"),("gapNom","Diferencia nominal K"),("gapReal","Diferencia real K"),("ratioReal","Razón real K g1/g2")],
        "Contrastar H1/H3 sin confundir cierre, inversión de brecha y monto de la unión.",
        "Periodo conjunto condicionadamente comparable. Cobertura: cada vía y grupo con su denominador conocido; comparación K frente a unión dentro de2021 en soporte común está en cuadro33, y para otras rondas en bloque5 de06. Aquí se compara la evolución de cada definición, no se resta K a unión con denominadores distintos. MontosK solo receptores válidos, nunca monto total de personas con unión. Razón g1/g2, diferencias g1−g2, mediana personal parcial. Edad70+/60–64, escolaridad inicial, localidad100mil y ocupación4 agrupada; no ajuste multivariado.")
    body+="En 2012–2015 la brecha de unión por sexo baja de12.43 a9.24pp, mientras la razón de medianas reales K hombres/mujeres sube de1.13 a1.20 y su diferencia de$504 a$685. En escolaridad, la brecha K se reduce de32.54 a18.34pp, pero la razón monetaria K ≥10/0 años aumenta de4.21 a15.00. La brecha de unión escolar pasa de+5.92 a−9.13pp: favorece después al grupo sin escolaridad, y su magnitud crece3.21pp. La brecha de unión por localidad ya favorecía a las menores de100mil y aumenta en valor absoluto; la brecha por edad aumenta de31.52 a50.50pp. Por tanto, mayor incorporación de ciertos grupos no es igualación de todas las tasas. En ocupación, la brecha de unión se estrecha de30.47 a26.95pp y la razón K permanece1.25: no toda evidencia monetaria indica ampliación.\n\n"
    body+="La distinción también aparece fuera de esa ventana conjunta: K2018–2021 reduce la brecha de cobertura por sexo de17.17 a13.73pp, pero la razón de medianas reales hombres/mujeres pasa de1.20 a1.29. A2015–2018 aumenta su recepción total, mientras la brecha firmada hombres−mujeres pasa de−4.21 a−8.12pp, una ampliación de la ventaja femenina; las medianas A de ambos sexos coinciden dentro de cada ronda. No se extiende esa lectura a la unión K/A porque K presenta ruptura2015–2018.\n\n"
    k12,k15=money(r7,2012,"K"),money(r7,2015,"K")
    a15,a18=money(r7,2015,"A"),money(r7,2018,"A")
    body+=f"**Distribución, más allá de la mediana.** K2012–2015 tiene cuartiles reales ${k12['persona']['real']['q25']:,.0f}/${k12['persona']['real']['q75']:,.0f} y ${k15['persona']['real']['q25']:,.0f}/${k15['persona']['real']['q75']:,.0f}; IQR/mediana pasa de1.45 a1.55, con N={k12['N_monto']:,}/{k15['N_monto']:,}. A2015–2018 tiene cuartiles ${a15['persona']['real']['q25']:,.0f}/${a15['persona']['real']['q75']:,.0f} y ${a18['persona']['real']['q25']:,.0f}/${a18['persona']['real']['q75']:,.0f}; IQR/mediana pasa de0.18 a0.78, con N={a15['N_monto']:,}/{a18['N_monto']:,}. Son señales de cambios en la distribución captada entre receptores; no una descomposición del efecto de inflación, composición y programas. Una mediana igual entre sexos tampoco prueba igualdad de todos los cuantiles.\n\n"
    profile_rows=[]
    selected=[("edad_06","60–64"),("edad_06","70+"),("educacion_grupo","0 años"),("educacion_grupo","≥10 años"),
              ("ocupacion_grupo","Trabaja"),("ocupacion_grupo","Labores del hogar"),("sexo_grupo","Mujer")]
    for dim,label in selected:
        z=next(x for x in r["perfiles2021"] if (x["dimension"],x["grupo"])==(dim,label));c=z["cobertura"];k,a=z["K"],z["A"]
        profile_rows.append(dict(perfil=label,Nknown=c['N_KA_conocido'],none=c['N_KA_no'],nonepct=100*c['N_KA_no']/c['N_KA_conocido'],ND=c['N_KA_ND_elegible'],
            union=c['KA_pct'],nk=k['N_monto'],na=a['N_monto'],Kn=k['nominal']['mediana'],Kr=k['real']['mediana'],An=a['nominal']['mediana'],Ar=a['real']['mediana'],
            Klpi=k['umbral']['mediana_pct'],Alpi=a['umbral']['mediana_pct']))
    body+=table("Perfiles con negativas propias o prestaciones parciales bajas en2021",profile_rows,
        [("perfil","Perfil"),("Nknown","N unión conocida"),("none","N negativas K y A"),("nonepct","Negativas % conocidas"),("ND","Unión ND"),("union","Unión propia %"),
         ("nk","N monto K"),("na","N monto A"),("Kn","Mediana K nominal $"),("Kr","Mediana K real $"),("An","Mediana A nominal $"),("Ar","Mediana A real $"),
         ("Klpi","Mediana K/LPI %"),("Alpi","Mediana A/LPI %")],
        "Localizar ausencia declarada de las dos vías propias y distinguirla de montos bajos entre receptores.",
        "Directas60+, denominadores de unión y montos separados. Los grupos de diferentes dimensiones se solapan: no sumar sus N. Unión ND no es negativa. LPI asignable cubre todos los montos de estos perfiles2021, usando periodo original y geografía2500. Perfil de localidad del cuadro previo corta100mil. Las cifras A valoran dinero/especie y no son todas A5. La ausencia propia no excluye cónyuge, transferencias familiares, patrimonio u otros ingresos. Ningún porcentaje es prevalencia de pobreza.")
    body+="**Situación pensionaria y alcance de suficiencia.** En2021 hay3000negativas explícitas K/A entre9366respuestas directas con unión conocida (32.03%),58uniones desconocidas y1058sustitutos fuera del principal. De la tipología,538personas con pareja confirmada reportan solo K del cónyuge: no tienen K/A propia identificada, pero tampoco se puede afirmar ausencia de recurso contextual.884personas sin pareja residente tienen negativas K/A. Entre quienes solo reportan A propia, las medianas son1550nominales y2108reales: N con monto1291de1304con pareja confirmada y1313de1320sin pareja residente. Ambos componentes representan una mediana de43.66% de su LPI asignada. No se convierten las negativas en monto cero ni se suman la pensión del cónyuge y el apoyo propio.\n\n"
    body+="La situación de recepción también distingue montos del mismo componente entre personas diferentes. En2021, comparando soloK propia frente aK propia+A propia, dentro del mismo contexto de pareja:\n\n"
    for context in ("Pareja confirmada", "Sin pareja residente"):
        only=next(x for x in r['situacion2021'] if x['via']=='K' and x['grupo']==context+" · Solo K propia")
        both=next(x for x in r['situacion2021'] if x['via']=='K' and x['grupo']==context+" · K propia + A propia")
        body+=f"- **{context}:** mediana parcial K de ${only['nominal']['mediana']:,.0f} nominales/${only['real']['mediana']:,.0f} reales en solo K (N monto={only['N_monto']:,} de {only['N_receptores']:,} receptoras), frente a ${both['nominal']['mediana']:,.0f}/${both['real']['mediana']:,.0f} entre quienes también reportan A propia (N={both['N_monto']:,}/{both['N_receptores']:,}). La mediana K/LPI es {only['umbral']['mediana_pct']:.2f}% frente a {both['umbral']['mediana_pct']:.2f}%, con esos mismos N válidos.\n"
    body+="\nLa coexistencia de dos vías propias se asocia aquí con un componente K central menor. No permite concluir que A reduzca K, que el importe total K+A sea menor ni que exista una compensación diseñada por el programa: las categorías tienen composiciones diferentes y no se ajustaron sus perfiles. El importe del cónyuge no entra en estas cifras. Los grupos con contexto o recepción indeterminados permanecen separados en los agregados y cuadros previos.\n\n"
    a5=next(x for x in r['A5'] if x['dimension']=='General')
    kk5=next(x for x in r['comparacion_K_A5'] if x['dimension']=='General')
    body+=f"**K, A y A5 son distintos.** A5 de vejez se identifica solo en2021 en{a5['N_eventos']:,}eventos/{a5['N_personas']:,}personas directas60+, con{a5['declarado']['nominal']['N']:,}montos válidos. No existe una serie A5 homologada desde2001 ni se estima aquí cobertura A5 completa sin un denominador de conocimiento del programa validado. La comparación monetaria entre vías se restringe a ese componente con norma monetaria verificada: por evento, K tiene mediana nominal${kk5['K_evento']['nominal']['mediana']:,.0f}/real${kk5['K_evento']['real']['mediana']:,.0f} (N={kk5['K_evento']['nominal']['N']:,}) y A5 ${kk5['A5_evento']['nominal']['mediana']:,.0f}/${kk5['A5_evento']['real']['mediana']:,.0f} (N={kk5['A5_evento']['nominal']['N']:,}), razón real{kk5['razon_real']:.2f}. Son eventos entre receptores distintos, no ingresos personales completos ni un contraste de todos los apoyos como efectivo.\n\n"
    body+="La razón prestación/LPI es una referencia para el componente observado, no diagnóstico de pobreza o suficiencia integral. En A general2015–2018 su mediana pasa de20.76% a20.47% (N=2582/2699); el ligero descenso de esa razón no tiene que igualar−5.84%, porque la línea cambia con su canasta y geografía, no solo con el índice general. En2021 A5 tiene mediana43.66% de la LPI y97.33% de los importes están bajo ella; con el criterio de doce meses previos la mediana de razón es41.38%. No permite afirmar que esas personas sean pobres o que carezcan de otros ingresos. Un monto por encima de la línea tampoco acredita protección integral.\n\n"
    policy_rows=[
        dict(politica="70 y Más: ampliaciones territoriales2008–2012 y PAM65+ desde2013",indicador="A propia; K con programas agrupados; edad y localidad100mil",resultado="En2012–2015 crecen K, A y unión; sube más el acceso de ciertos grupos de menor escolaridad/localidad.",limite="Programa individual no identificado en A histórica; corte100mil no reproduce20/30mil; slots y composición cambian."),
        dict(politica="PAM $580 mensuales2014–2018, sin aumento nominal",indicador="Monto normativo separado; monto parcial A2015–2018",resultado=f"Norma real disminuye {abs(r['norma'][0]['cambio_real_pct']):.2f}% en2014–2018; A mediana real −5.84% en2015–2018, con recepción +2.91pp.",limite="Periodos y recursos distintos: coincidencia compatible con erosión por precios, sin atribuir todaA a PAM."),
        dict(politica="Bienestar2018–2019:580 a1275 mensuales; edad68general/65indígena",indicador="Importe normativo mensual oficial",resultado=f"Norma nominal+{r['norma'][1]['cambio_nominal_pct']:.2f}%; equivalente real+{r['norma'][1]['cambio_real_pct']:.2f}% según precios de sus periodos.",limite="No hay rondas anuales2019/2020; A2018–2021 rompe definición. No estima efecto de la reforma sobre hogares."),
        dict(politica="Bienestar2021:1350 a1550 mensuales y ampliación65+ desde julio",indicador="A5 identificada2021; perfiles por edad; fecha real de entrevista",resultado=f"Norma nominal+{r['norma'][3]['cambio_nominal_pct']:.2f}%, real+{r['norma'][3]['cambio_real_pct']:.2f}%; mediana A5declarada1550; unión propia mucho mayor en70+ que60–64.",limite="Inscripción escalonada, recuerdo incierto y2630directas en2022. Coincidencia no es causalidad ni certificación de cobro."),
    ]
    body+=table("Política, indicador, resultado y límite de interpretación",policy_rows,
        [("politica","Política documentada"),("indicador","Indicador disponible"),("resultado","Resultado observado"),("limite","Límite metodológico")],
        "Vincular cronología y datos sin atribuir efectos por coincidencia temporal.",
        "Importes normativos y respuestasENASEM conservan sus diferentes periodos. Norma usa precio medio del periodo indicado; ENASEM, año calendario previo a entrevista real. Beneficio bimestral convertido a equivalente mensual normativo; no rescalar automáticamente lo declarado mensual. Fechas, condiciones y fuentes oficiales en cuadro43 y nota documental de políticas. La reforma2021 entra en vigor8julio, sin reconstruir pagos diarios; ampliación legal no equivale a incorporación efectiva.")
    body+="**Sensibilidad actuarial: qué cambia y qué no queda demostrado.** El crecimiento de unión2012–2015 también aparece en7196pares vivos/directos con unión conocida:46.55% al inicio y72.40% al destino, frente a47.42%/65.79% en las muestras transversales60+. El aumento no desaparece al seleccionar pares, pero su magnitud cambia y el destino de una cohorte basal no es la población60+ completa de2015. La brecha de unión por sexo entre esos pares pasa de12.53 a7.93pp (N hombres3266, mujeres3930), compatible con estrechamiento; no es corrección de mortalidad o sesgo. Hay25edades finales discordantes menores de60 en la cohorte2012–2015, conservadas en el estimando de seguimiento.\n\n"
    body+="En la cohorte basal directa de2012, el seguimiento K separa738fallecimientos registrados,388ausencias con estado vital desconocido,381sustitutos vivos,88directas con K desconocida y7293directas con K conocida. El universo basal de negativas K es5919:70.08% de los4909sobrevivientes con K conocida mantienen negativa, pero la proporción de negativa viva sobre toda la cohorte basal está acotada entre58.12% y67.34%;464fallecidos no reciben una prestación futura imputada. No son intervalos de confianza. En2018–2021 la cohorte directa registra1069muertes,395ausencias y599sustitutos; esos destinos tampoco se convierten en negativas K/A.\n\n"
    seguimiento=next(x for x in r['cotas'] if x['origen']==2012)
    basal_no=next(x for x in seguimiento['grupos'] if x['dimension']=='General')
    body+=f"Entre las {basal_no['estados_sin_K_basal']['Ausente; vital desconocido']:,} personas inicialmente sin K y ausentes en2015, {basal_no['N_ausentes_reaparecen_vivos_despues']:,} reaparecen vivas y {basal_no['N_ausentes_registro_fallecido_despues']:,} tienen un registro de fallecimiento en rondas posteriores. Reaparición y defunción posterior no reconstruyen automáticamente el estado vital, la recepción o el monto en la visita ausente. No se equipara ausencia con muerte ni con negativa pensionaria.\n\n"
    body+="Los montos basales de retenidos pueden cambiar las brechas. En K2018–2021 la brecha real basal por sexo permanece aproximadamente$764, mientras la de localidad aumenta de$764 a$1070 y la escolar≥10/0 de$12004 a$12541 al restringir a observables. Por tanto, la selección no altera todas las dimensiones por igual y puede ampliar ciertas diferencias. Estos estimandos basales no prueban que las brechas transversales finales hayan sido corregidas. Con respuestas válidas por sustituto, la unión2021 es68.81% (N conocido10410), frente a67.97% (N9366) en directas; las medianas generales K/A permanecen4000/1550nominales y5439/2108reales, aunque los N monetarios se amplían a3347/5530. La estabilidad de esas medianas no prueba ausencia de selección en todos los grupos o cuantiles.\n\n"
    hrows=[
        dict(H="H1",veredicto="Respaldo descriptivo parcial",evidencia="En2012–2015 unión: brecha sexo12.43→9.24pp; K: brecha escolar32.54→18.34pp. También hay ventanas con menor brechaK por sexo.",contraste="Edad amplía31.52→50.50pp; unión escolar invierte+5.92→−9.13pp y amplía magnitud; localidad no converge.",alcance="Determinados grupos/periodos; contradice igualación general. No prueba efecto de una política."),
        dict(H="H2",veredicto="Respaldada para casos verificados",evidencia="K2012–15 nominal0%, real−11.05%; A2015–18 nominal+5.45%, real−5.84%.",contraste="Dirección negativa bajo fechas alternativas; K2018–21 y cambios normativos específicos sí muestran aumentos reales.",alcance="Medianas transversales parciales; no caída universal del ingreso individual ni prueba inferencial."),
        dict(H="H3",veredicto="Respaldo descriptivo condicionado",evidencia="2012–15: brecha unión por sexo menor y razón K H/M1.13→1.20; cobertura K escolar menor brecha, razón de montos4.21→15.00.",contraste="Ocupación: razón K1.25 estable y brecha absoluta menor. No existe monto agregado de unión validado.",alcance="Acceso y componente K en poblaciones distintas; no desigualdad total de protección o ingreso. Generalización2001–21 insuficiente."),
        dict(H="H4",veredicto="Respaldada descriptivamente",evidencia="2021:3000negativas propias/9366conocidas; ciertos perfiles de alto acceso reciben componentes bajos respecto de LPI.",contraste="538reportan solo pensión del cónyuge; otros recursos no evaluados. A5 solo identificable2021.",alcance="No cobertura integral, pobreza, suficiencia del hogar ni ausencia de otros ingresos.")]
    body+=table("Balance de las proposiciones de la tesis",hrows,
        [("H","H"),("veredicto","Evaluación"),("evidencia","Evidencia favorable"),("contraste","Contrastes o evidencia insuficiente"),("alcance","Alcance defendible")],
        "Contrastar las hipótesis sin convertirlas en conclusiones predeterminadas.",
        "Evaluaciones descriptivas, no pruebas de significancia. Sensibilidades de fechas, modalidad y observación son análisis de robustez o cambios de estimando, no IC, ajuste causal ni corrección automática. Todos los N y unidades en los cuadros previos y los agregados06/07. La hipótesis de trabajo es parcialmente compatible con ciertos contrastes, no confirmada como ley general.")
    body+="**Contribución a la pregunta central.** El resultado académico es distinguir expansión del acceso, valor central de los componentes y referencia económica cubierta, con una evaluación explícita de comparabilidad y selección. Es defendible afirmar que más recepción puede coexistir con menor poder adquisitivo de la prestación parcial mediana y con brechas monetarias persistentes; también existen aumentos reales y contrastes que se estrechan. No es defendible afirmar que toda protección se igualó, que todos los receptores perdieron ingreso, que una reforma causó las diferencias o que una prestación inferior a la línea identifica pobreza. La magnitud de la expansión homogénea y de la suficiencia total2001–2021 sigue sin identificarse con estos productos.\n\n"
    body+="Las figuras35–36 del informe permiten consultar cobertura por perfil; las figuras39–40 muestran nominal/real y componentes monetarios; la figura41 distingue referencia geográfica y la43 selección. Se utilizan con sus propios N, definiciones y notas. Esta síntesis aporta la comparación conjunta y el balance de proposiciones; no sustituye los resultados anteriores ni crea otra investigación.\n"
    # Normalizar solo espacios de la prosa nueva; nunca editar código, enlaces o bloques previos.
    body=readable(body)
    pieces=re.split(r"(\]\([^)]*\)|`[^`]*`)",body)
    for i,piece in enumerate(pieces):
        if piece.startswith(("](","`")):continue
        piece=re.sub(r"\bA 5\b","A5",piece)
        piece=re.sub(r"(?<=[A-Za-záéíóúñ)])([,;])(?=\d)",r"\1 ",piece)
        piece=re.sub(r"(?<=:)(?=\d)"," ",piece)
        piece=re.sub(r"(?<=[A-Za-záéíóúñ])(?=[$+−-]\d)"," ",piece)
        piece=re.sub(r"(?<=[a-záéíóúñ])(?=ENASEM\b)"," ",piece)
        pieces[i]=piece
    body="".join(pieces)
    # Mantener códigos de hipótesis compactos en etiquetas y preguntas.
    for h in ("H1","H2","H3","H4"):
        body=body.replace(h[0]+" "+h[1],h)
    path=RESULTS_DIR/"INFORME_GENERAL.md";text=path.read_text()
    begin,end="<!-- BEGIN sintesis06_07 -->","<!-- END sintesis06_07 -->"
    ledger=OUTPUT/"informe_contribucion.json"
    if begin in text:
        a=text.index(begin);b=text.index(end,a)+len(end)
        assert sha256(text[a:b].encode()).hexdigest()==json.loads(ledger.read_text())["sha_bloque"],"Síntesis editada manualmente"
        text=text[:a]+begin+"\n\n"+body+"\n"+end+text[b:]
    else:
        a=text.index('<a id="seccion-limites"></a>')
        text=text[:a].rstrip()+"\n\n"+begin+"\n\n"+body+"\n"+end+"\n\n"+text[a:]
    tables,figures={},{};lines=text.splitlines()
    for i,line in enumerate(lines):
        match=re.match(r"\*\*Cuadro \d+\. (.*)\*\*$",line)
        if match:tables[match[1]]=len(tables)+1;lines[i]=f"**Cuadro {tables[match[1]]}. {match[1]}**"
        match=re.match(r"\*\*Figura \d+\. (.*)\*\*$",line)
        if match:figures[match[1]]=len(figures)+1;lines[i]=f"**Figura {figures[match[1]]}. {match[1]}**"
        match=re.match(r"!\[Figura \d+: (.*?)\]\((.*?)\)",line)
        if match:lines[i]=f"![Figura {figures[match[1]]}: {match[1]}]({match[2]})"
    text="\n".join(lines)+"\n"
    baseline=json.loads((OUTPUT/"bloques_previos.json").read_text())
    for key,expected in baseline.items():
        start,finish=f"<!-- BEGIN {key} -->",f"<!-- END {key} -->"
        a=text.index(start);b=text.index(finish,a)+len(finish)
        assert sha256(text[a:b].encode()).hexdigest()==expected,"Cambió bloque anterior: "+key
    path.write_text(text)
    a=text.index(begin);b=text.index(end,a)+len(end)
    save_json(ledger,dict(sha_bloque=sha256(text[a:b].encode()).hexdigest(),productos=products))
    p=INTERIM_DIR/"informe_general_seleccion.json";d=json.loads(p.read_text())
    d["productos"]=[z for z in d["productos"] if z.get("contribucion")!="sintesis06_07"]+products
    for z in d["productos"]:z["numero"]=(tables if z["tipo"]=="tabla" else figures)[z["titulo"]]
    d["cuadros"],d["figuras"]=len(tables),len(figures);save_json(p,d)
    p=INTERIM_DIR/"indice_informe.json";d=json.loads(p.read_text())
    matches=list(re.finditer(r'<a id="seccion-([a-z]+)"></a>',text))
    d["secciones_sintesis"]={m[1]:dict(inicio=m.start(),fin=matches[i+1].start() if i+1<len(matches) else len(text)) for i,m in enumerate(matches)}
    d["sha_sintesis"]=sha256(text.encode()).hexdigest();save_json(p,d)
    save_json(OUTPUT/"manifest.json",dict(insumos_protegidos=verify_inputs(),
        resultados_sha256=sha256((OUTPUT/"resultados.json").read_bytes()).hexdigest(),
        codigo={str(p.relative_to(PROJECT_ROOT)):sha256(p.read_bytes()).hexdigest() for p in
            [PROJECT_ROOT/"src/tesis_enasem/protection_synthesis.py",PROJECT_ROOT/"scripts/export_protection_synthesis.py"]},
        fuente_informe_sha256=sha256(path.read_bytes()).hexdigest(),bloques_previos_preservados=len(baseline)))
    print("Síntesis06/07:",len(tables),"cuadros,",len(figures),"figuras;",len(baseline),"bloques anteriores intactos")


if __name__=="__main__":
    from tesis_enasem.release_guard import block_legacy_export
    block_legacy_export()
    export()
