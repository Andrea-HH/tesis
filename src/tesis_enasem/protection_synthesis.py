"""Síntesis de agregados06/07: acceso, valor real y umbral, sin nuevo microanálisis."""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any

from .economic_protection import save_json
from .monetary_policy import QUESTION, sources
from .project_paths import INTERIM_DIR, PROJECT_ROOT

OUTPUT = INTERIM_DIR / "sintesis_proteccion_economica"
PROFILES = (
    ("sexo_grupo", "Hombre", "Mujer"),
    ("edad_06", "70+", "60–64"),
    ("educacion_grupo", "≥10 años", "0 años"),
    ("localidad_grupo", "≥100 mil habitantes", "<100 mil habitantes"),
    ("ocupacion_grupo", "Retirado/incapacitado/no trabaja", "Trabaja"),
)


def verify_inputs() -> int:
    """Verifica archivos anteriores, notebooks01–07, bases, figuras e índice intactos."""
    fingerprints = json.loads((OUTPUT / "insumos_protegidos.json").read_text())
    for name, expected in fingerprints.items():
        if sha256((PROJECT_ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Se modificó un archivo protegido: {name}")
    return len(fingerprints)


def read_inputs() -> tuple[dict, dict]:
    """Lee solo resultados ya calculados; exige conciliación entre fuentes06/07."""
    r6 = json.loads((INTERIM_DIR / "cobertura_proteccion_economica/resultados.json").read_text())
    r7 = json.loads((INTERIM_DIR / "politicas_montos_suficiencia/resultados.json").read_text())
    assert r6["rondas"] == r7["cobertura06"]
    assert r6["seguimiento_principal"] == r7["cotas06"]
    assert r7["pregunta"] == QUESTION
    assert r7["metodologia"]["referencia"] == "2026-09"
    sources()  # integridad de la serie oficial congelada, sin nueva descarga
    return r6, r7


def ratio(numerator: float | None, denominator: float | None) -> float | None:
    """Razón descriptiva; mediana cero o información ausente no producen desigualdad0."""
    return None if numerator is None or denominator in (None, 0) else numerator / denominator


def variation(initial: float | None, final: float | None) -> float | None:
    """Variación de un resumen transversal; nunca un cambio individual inferido."""
    value = ratio(final, initial)
    return None if value is None else 100 * (value - 1)


def gap_change(initial: float, final: float) -> dict:
    """Separa dirección de la brecha, tamaño absoluto e inversión entre grupos."""
    delta = abs(final) - abs(initial)
    return dict(inicial=initial, final=final, cambio_firmado=final-initial,
                cambio_magnitud=delta, cambia_signo=initial*final < 0,
                lectura="Se estrecha" if delta < -1e-10 else "Se amplía" if delta > 1e-10 else "Magnitud igual")


def wave(r6: dict, year: int, sensitivity: bool = False) -> dict:
    """Modalidades mantienen sus denominadores: directas principal, sustitutos sensibilidad."""
    candidates = [x for x in r6["rondas"] if x["ronda"] == year]
    return next(x for x in candidates if (x["analisis"] != "principal") == sensitivity)


def coverage(r6: dict, year: int, dim: str = "General", group: str = "Todas") -> dict:
    """Tasa de cada vía con su N conocido, sin equiparar desconocido y negativa."""
    return next(x for x in wave(r6, year)["cobertura"] if x["dimension"] == dim and x["grupo"] == group)


def money(r7: dict, year: int, via: str, dim: str = "General", group: str = "Todas") -> dict:
    """Recupera la suma personal parcial ya calculada; no sumaK+A ni imputados."""
    return next(x for x in r7["montos"] if (x["ronda"],x["via"],x["dimension"],x["grupo"]) == (year,via,dim,group))


def amount_endpoint(z: dict) -> dict:
    """Solo indicadores robustos existentes; media/DE no gobiernan la interpretación."""
    p = z["persona"]
    result = {k:z[k] for k in ("N_receptores", "N_monto", "N_receptores_sin_monto", "N_eventos", "N_eventos_ND")}
    for unit in ("nominal", "real"):
        result[unit] = {k:p[unit][k] for k in ("N", "mediana", "q25", "q75", "p10", "p90", "iqr")}
        result[unit]["iqr_mediana"] = ratio(p[unit]["iqr"],p[unit]["mediana"])
        result[unit]["p90_p10"] = ratio(p[unit]["p90"],p[unit]["p10"])
    result["umbral"] = dict(N=p["N_lpi"],N_ND=p["N_umbral_ND_monto"],
        mediana_pct=p["lpi_pct"]["mediana"],q25_pct=p["lpi_pct"]["q25"],q75_pct=p["lpi_pct"]["q75"],
        inferior_pct=p["prestacion_inferior_lpi_pct"])
    result["sensibilidad"] = {k:dict(N=p[k]["N"],mediana=p[k]["mediana"]) for k in (
        "sensibilidad_12m", "sensibilidad_ano_entrevista", "real_min_fecha", "real_max_fecha")}
    return result


def synthesize() -> dict:
    """Reproduce y relaciona cifras guardadas, sin ejecutar notebooks o modificar bases."""
    verify_inputs()
    r6,r7=read_inputs()
    endpoints=[]
    for year in (2001,2003,2012,2015,2018,2021):
        c=coverage(r6,year)
        endpoints.append(dict(ronda=year,cobertura=c,K=amount_endpoint(money(r7,year,"K")),
                              A=amount_endpoint(money(r7,year,"A"))))
    anchors=[]
    for via,a,b in (("K",2012,2015),("A",2015,2018)):
        x,y=money(r7,a,via),money(r7,b,via)
        p,q=x["persona"],y["persona"]
        matched=next(z for z in r7["seleccion"] if (z["origen"],z["destino"],z["via"],z["dimension"])==(a,b,via,"General"))
        anchors.append(dict(via=via,origen=a,destino=b,inicial=amount_endpoint(x),final=amount_endpoint(y),
            cambio_nominal_pct=variation(p["nominal"]["mediana"],q["nominal"]["mediana"]),
            cambio_real_pct=variation(p["real"]["mediana"],q["real"]["mediana"]),
            sensibilidad_12m_pct=variation(p["sensibilidad_12m"]["mediana"],q["sensibilidad_12m"]["mediana"]),
            sensibilidad_ano_entrevista_pct=variation(p["sensibilidad_ano_entrevista"]["mediana"],q["sensibilidad_ano_entrevista"]["mediana"]),
            sensibilidad_extremos_min_pct=variation(p["real_max_fecha"]["mediana"],q["real_min_fecha"]["mediana"]),
            sensibilidad_extremos_max_pct=variation(p["real_min_fecha"]["mediana"],q["real_max_fecha"]["mediana"]),
            fecha_precio=[z for z in r7["factores"] if z["ronda"] in (a,b)],
            unidad="Mediana transversal de suma mensual personal observada parcial; no evento ni pensión específica",
            codigo_monto="monto_"+via.lower()+"_propio_mensual_observado_parcial",
            notebook="notebooks/07_POLITICAS_MONTOS_SUFICIENCIA.ipynb",seccion="7",celda_fisica=22,
            pares=matched))
    assert round(anchors[0]["cambio_real_pct"],2)==-11.05
    assert round(anchors[1]["cambio_nominal_pct"],2)==5.45
    assert round(anchors[1]["cambio_real_pct"],2)==-5.84
    periods=[]
    group_periods=[]
    for spec in r7["comparabilidad"]:
        a,b=spec["origen"],spec["destino"]
        for via in ("K","A","KA"):
            ca,cb=coverage(r6,a),coverage(r6,b)
            comparable=spec[via]
            z=dict(origen=a,destino=b,via=via,comparable=comparable,
                   cobertura_inicial=ca[f"{via}_pct"],cobertura_final=cb[f"{via}_pct"],
                   N_cobertura_inicial=ca[f"N_{via}_conocido"],N_cobertura_final=cb[f"N_{via}_conocido"],
                   cambio_cobertura_pp=cb[f"{via}_pct"]-ca[f"{via}_pct"] if comparable else None,
                   moneda_union_identificable=False if via=="KA" else None)
            c1,c2=[coverage(r6,y,"sexo_grupo","Hombre")[f"{via}_pct"]-coverage(r6,y,"sexo_grupo","Mujer")[f"{via}_pct"] for y in (a,b)]
            z["brecha_cobertura_sexo"]=gap_change(c1,c2) if comparable else None
            if comparable and via!="KA":
                x,y=money(r7,a,via),money(r7,b,via)
                z.update(inicial=amount_endpoint(x),final=amount_endpoint(y),
                         cambio_nominal_pct=variation(x["persona"]["nominal"]["mediana"],y["persona"]["nominal"]["mediana"]),
                         cambio_real_pct=variation(x["persona"]["real"]["mediana"],y["persona"]["real"]["mediana"]))
            else:
                z.update(inicial=None,final=None,cambio_nominal_pct=None,cambio_real_pct=None)
            periods.append(z)
            if comparable:
                for dim,g1,g2 in PROFILES:
                    cs=[[coverage(r6,y,dim,g) for g in (g1,g2)] for y in (a,b)]
                    gaps=[p[0][f"{via}_pct"]-p[1][f"{via}_pct"] for p in cs]
                    record=dict(origen=a,destino=b,via_cobertura=via,dimension=dim,grupo1=g1,grupo2=g2,
                        brecha_cobertura=gap_change(*gaps),
                        cobertura_inicial=[{k:p[k] for k in (f"N_{via}_conocido",f"{via}_pct")} for p in cs[0]],
                        cobertura_final=[{k:p[k] for k in (f"N_{via}_conocido",f"{via}_pct")} for p in cs[1]])
                    # Para unión se muestran COMPONENTESK/A por separado, nunca monto unión.
                    for monetary_via in ((via,) if via!="KA" else ("K","A")):
                        ms=[[money(r7,y,monetary_via,dim,g) for g in (g1,g2)] for y in (a,b)]
                        def difference(p: list[dict],unit: str) -> float | None:
                            x,y=[x["persona"][unit]["mediana"] for x in p]
                            return x-y if x is not None and y is not None else None
                        record[monetary_via]=dict(inicial=[amount_endpoint(z) for z in ms[0]],final=[amount_endpoint(z) for z in ms[1]],
                            brecha_nominal_inicial=difference(ms[0],"nominal"),brecha_nominal_final=difference(ms[1],"nominal"),
                            brecha_real_inicial=difference(ms[0],"real"),brecha_real_final=difference(ms[1],"real"),
                            razon_real_inicial=ratio(ms[0][0]["persona"]["real"]["mediana"],ms[0][1]["persona"]["real"]["mediana"]),
                            razon_real_final=ratio(ms[1][0]["persona"]["real"]["mediana"],ms[1][1]["persona"]["real"]["mediana"]))
                    group_periods.append(record)
    profiles=[]
    for dim in ("sexo_grupo","edad_06","educacion_grupo","localidad_grupo","ocupacion_grupo"):
        for c in wave(r6,2021)["cobertura"]:
            if c["dimension"]==dim:
                profiles.append(dict(dimension=dim,grupo=c["grupo"],cobertura=c,
                    K=amount_endpoint(money(r7,2021,"K",dim,c["grupo"])),
                    A=amount_endpoint(money(r7,2021,"A",dim,c["grupo"]))))
    status=[dict(via=z["via"],grupo=z["grupo"],ronda=z["ronda"],**amount_endpoint(z))
            for z in r7["montos"] if z["ronda"]==2021 and z["dimension"]=="grupo_tipologia"]
    norm=r7["norma_programa"]
    official=[]
    for a,b in (("2014","2018"),("2018","2019"),("2019","2020"),("2021 enero–junio","2021 julio–diciembre")):
        x,y=[next(z for z in norm if z["periodo"]==p) for p in (a,b)]
        official.append(dict(origen=a,destino=b,inicial=x,final=y,
            cambio_nominal_pct=variation(x["nominal_mensual"],y["nominal_mensual"]),
            cambio_real_pct=variation(x["real_mensual"],y["real_mensual"])))
    return dict(pregunta=QUESTION,fuente="Solo agregados06/07 ya calculados; no microdatos ni nuevos modelos",
        referencia="2026-09",inpc=146.075,reproduccion=anchors,periodos=periods,brechas_por_perfil=group_periods,
        rondas=endpoints,perfiles2021=profiles,situacion2021=status,
        norma=official,cronologia=json.loads((INTERIM_DIR/"politicas_montos_suficiencia/cronologia_politicas.json").read_text()),
        seleccion=[z for z in r7["seleccion"] if z["dimension"]=="General"],
        seleccion_por_perfil=[z for z in r7["seleccion"] if z["dimension"]!="General"],
        cotas=r6["seguimiento_principal"],modalidad=r7["sustitutos_sensibilidad"],
        A5=r7["comparacion_A5"],comparacion_K_A5=r7["comparacion_K_A5"],
        hipotesis=[dict(clave="H1",estado="Respaldo parcial y condicionado; contradicción de igualación general",
                       motivo="Cierre de brechas específicas; ensanchamiento por edad e inversión escolar sin cierre absoluto"),
            dict(clave="H2",estado="Respaldo descriptivo y temporal robusto para los dos ejemplos",
                 motivo="Cambios reales negativos bajo criterios alternativos; no prueba de caída individual universal"),
            dict(clave="H3",estado="Respaldo descriptivo condicionado en2012–2015; insuficiente para generalizar2001–2021",
                 motivo="Brechas de cobertura seleccionadas menores coexisten con mayores diferencias monetariasK entre receptores"),
            dict(clave="H4",estado="Respaldo descriptivo de negativas propias y recursos parciales bajos",
                 motivo="No identifica protección integral, pobreza ni ausencia de recursos del cónyuge")])


def validate(r: dict[str,Any]) -> None:
    """Comprueba estimandos y vacíos obligatorios; no confirma hipótesis por ejecución."""
    assert r["referencia"]=="2026-09" and r["inpc"]==146.075
    for z in r["periodos"]:
        if not z["comparable"]:
            assert z["cambio_cobertura_pp"] is None and z["cambio_real_pct"] is None
        if z["via"]=="KA":
            assert z["inicial"] is None and z["final"] is None
    for z in r["reproduccion"]:
        assert z["sensibilidad_extremos_max_pct"] < 0
        assert z["inicial"]["N_monto"]+z["inicial"]["N_receptores_sin_monto"]==z["inicial"]["N_receptores"]
    school=next(z for z in r["brechas_por_perfil"] if (z["origen"],z["destino"],z["via_cobertura"],z["dimension"])==(2012,2015,"KA","educacion_grupo"))
    assert school["brecha_cobertura"]["cambia_signo"] and school["brecha_cobertura"]["lectura"]=="Se amplía"
    for z in r["perfiles2021"]:
        c=z["cobertura"]
        assert c["N_KA_si"]+c["N_KA_no"]==c["N_KA_conocido"]
    verify_inputs()
