"""Montos07: precios oficiales, prestaciones parciales y selección descriptiva."""

from __future__ import annotations

import json
from hashlib import sha256
from itertools import combinations
from typing import Iterator

import numpy as np
import pandas as pd

from .economic_protection import GROUPS, PARTNER, coverage, load_panel, pct, receipts, save_json, typology
from .pension_health import YEARS
from .pension_ownership import wave_contract
from .project_paths import INTERIM_DIR, PROCESSED_DIR, PROJECT_ROOT

OUTPUT = INTERIM_DIR / "politicas_montos_suficiencia"
NOTEBOOK = "07_POLITICAS_MONTOS_SUFICIENCIA.ipynb"
REFERENCE = "2026-09"
REFERENCE_INDEX = 146.075
DIMENSIONS = (*GROUPS, "conyugal_grupo", "grupo_tipologia")
QUESTION = "¿Qué tanto es consistente la expansión de las pensiones y los apoyos públicos con una reducción de las brechas de cobertura y de monto de la protección económica de los adultos mayores en México (ENASEM 2001–2021), qué grupos siguen sin vía propia de protección y cómo cambia esta lectura al considerar a quienes mueren o dejan de ser entrevistados?"


def verify_inputs() -> int:
    """Verifica todas las huellas anteriores07, incluido índice Git sin operarlo."""
    protected = json.loads((OUTPUT / "insumos_protegidos.json").read_text())
    for name, expected in protected.items():
        if sha256((PROJECT_ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Cambió un archivo protegido: {name}")
    return len(protected)


def sources() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Exige serie mensual oficial íntegra, base única y referencia publicada."""
    manifest = json.loads((OUTPUT / "fuentes.json").read_text())
    indices = pd.DataFrame(json.loads((OUTPUT / "inpc_mensual.json").read_text())).set_index("periodo")
    lines = pd.DataFrame(json.loads((OUTPUT / "lineas_mensuales.json").read_text())).set_index("periodo")
    assert indices.index.tolist() == pd.period_range("2000-01", REFERENCE, freq="M").astype(str).tolist()
    assert indices.loc[REFERENCE, "inpc"] == REFERENCE_INDEX == manifest["inpc_referencia"]
    assert indices.inpc.gt(0).all() and not lines.index.duplicated().any()
    for doc in manifest["documentos"]:
        assert sha256((OUTPUT / doc["archivo"]).read_bytes()).hexdigest() == doc["sha256"]
    for filename, key in [("inpc_inegi_exportacion.csv", "inpc_sha256"),
                          ("Líneas_de_Pobreza_por_Ingresos_mar2025.xlsx", "lpi_sha256")]:
        assert sha256((OUTPUT / "fuentes" / filename).read_bytes()).hexdigest() == manifest[key]
    return indices, lines, manifest


def constant_pesos(nominal: pd.Series, index: pd.Series, reference: float) -> pd.Series:
    """Actualiza poder adquisitivo; cero válido preservado, ND no se vuelve cero."""
    if reference <= 0 or index.dropna().le(0).any() or nominal.dropna().lt(0).any():
        raise ValueError("Monto o índice inválido")
    return nominal * reference / index


def rural_urban(code: pd.Series, valid: pd.Series, conflict: pd.Series) -> pd.Series:
    """Corte2500 verificado; códigos no válidos/discordantes no asignan umbral."""
    result = code.map({1: "Urbana", 2: "Urbana", 3: "Urbana", 4: "Rural"})
    return result.where(valid & ~conflict).fillna("Indeterminado")


def panel() -> pd.DataFrame:
    """Añade geografía original por LEFT1:1; mantiene todos los insumos intactos."""
    f = load_panel()
    metadata = json.loads((PROJECT_ROOT / "diccionarios/diccionario_integrado.json").read_text())
    metadata = {m["columna"]: m for m in metadata}
    fields = [f"F{n:02}__tam_loc_{year % 100:02}" for n, year in zip(range(7, 11), YEARS[2:])]
    tags = [metadata[v]["campo_tag"] for v in fields if metadata[v].get("campo_tag")]
    m = pd.read_parquet(PROCESSED_DIR / "enasem_integrada_provisional.parquet", columns=["id", "ronda", *fields, *tags])
    f = f.merge(m, on=["id", "ronda"], how="left", validate="one_to_one")
    assert len(f) == 99676 and not f[["id", "ronda"]].duplicated().any()
    f["localidad_lpi"] = "Indeterminado"
    f["geo_discordante"] = False
    f["geo_variable"] = "Solo corte100mil; <100mil indeterminado"
    # Una localidad>=100mil sí es urbana; no se llama rural a las menores100mil.
    early = f.ano.isin([2001, 2003]) & f.urbano.eq(1)
    f.loc[early, "localidad_lpi"] = "Urbana"
    for year, v in zip(YEARS[2:], fields):
        mask = f.ano.eq(year)
        valid = f[v].isin([1, 2, 3, 4])
        if metadata[v].get("campo_tag"):
            valid &= f[metadata[v]["campo_tag"]].eq(0)
        conflict = valid & f.urbano.isin([0, 1]) & f[v].eq(1).ne(f.urbano.eq(1))
        f.loc[mask, "geo_discordante"] = conflict.loc[mask]
        f.loc[mask, "localidad_lpi"] = rural_urban(f[v], valid, conflict).loc[mask]
        f.loc[mask, "geo_variable"] = v
    f["conyugal_grupo"] = f.est_conyugal.map({1: "Casado/unión", 2: "Separado/divorciado", 3: "Viudo", 4: "Nunca unido"}).fillna("Desconocido")
    f["grupo_tipologia"] = "Contexto no confirmado antes de2018"
    recent = f.ano.isin([2018, 2021])
    typed = typology(receipts(f.loc[recent]))
    f.loc[recent, "grupo_tipologia"] = typed.contexto_06 + " · " + typed.tipo_06
    return f


def load_events(f: pd.DataFrame, via: str) -> tuple[pd.DataFrame, dict]:
    """Enlaza evento a beneficiario real; varias prestaciones no multiplican personas."""
    name = "eventos_pensionarios" if via == "K" else "eventos_apoyos"
    e = pd.read_parquet(PROCESSED_DIR / f"armonizacion_economica_v1/{name}.parquet")
    keys = ["ano", "hogar_fuente", "fuente", "version", "rama", "slot"] + (["tipo"] if via == "K" else [])
    assert not e[keys].duplicated().any() and e.version.eq("original").all()
    if via == "K":
        assert not e.imputacion_usada.any()
    n = len(e)
    e = e.merge(f, left_on=["beneficiario_id", "ano"], right_on=["id", "ano"], how="left", validate="many_to_one", indicator=True)
    assert len(e) == n
    diagnostic = dict(N_eventos_fuente=n, N_enlazados=int(e._merge.eq("both").sum()),
                      N_sin_beneficiario=int(e.beneficiario_id.isna().sum()),
                      N_enlazados_60=int(e.universo_60.eq(True).sum()))
    return e, diagnostic


def audit() -> dict:
    """Auditoría previa a comparaciones: nombres, periodicidad, ND y fechas."""
    verify_inputs()
    _, _, manifest = sources()
    f = panel()
    original06 = json.loads((INTERIM_DIR / "cobertura_proteccion_economica/resultados.json").read_text())
    exact, universes, temporal, geo = [], [], [], []
    diagnostics = {}
    for via in ["K", "A"]:
        e, diagnostics[via] = load_events(f, via)
        for (year, role, variable), p in e.groupby(["ano", "rama", "variable_monto"], observed=True):
            valid = p.monto_mensual_observado.notna()
            principal=p.universo_60.eq(True) & p.directa.eq(True)
            code = p.monto_codigo_original
            nr, ns = (888888, 999999) if year < 2012 else (8888888, 9999999)
            exact.append(dict(ronda=int(year), rama_fuente=int(role), variable=variable,
                fuente=p.fuente.iloc[0], version="Original observada", unidad="Pesos mexicanos por mes normal",
                nivel="Evento en cuestionario de hogar; beneficiario orientado, no todos los residentes",
                periodicidad="Mensual ya normalizada por el entrevistador; no dividir por2 de nuevo",
                N_eventos=len(p), N_validos=int(valid.sum()), validos_pct=pct(int(valid.sum()), len(p)),
                N_NR=int(code.eq(nr).sum()), N_NS=int(code.eq(ns).sum()), N_faltante=int(code.isna().sum()),
                N_otro_invalido=int((~valid & ~code.isin([nr, ns]) & code.notna()).sum()),
                N_cero=int(p.monto_mensual_observado.eq(0).sum()),
                N_eventos_principal=int(principal.sum()),
                N_validos_principal=int((principal & valid).sum()),
                validos_principal_pct=pct(int((principal & valid).sum()),int(principal.sum())),
                N_beneficiarios_principal=p.loc[principal,'id'].nunique(),
                N_beneficiarios_monto_principal=p.loc[principal & valid,'id'].nunique(),
                denominador='Eventos y beneficiarios del concepto captado; no todos los receptoresK/A'))
        for x in original06["montos"]:
            if x["via"] == via and x["dimension"] == "General":
                universes.append({k: x[k] for k in x if not isinstance(x[k], dict)} | {
                    "cobertura_monto_receptores_pct":pct(x["N_personas_monto"], x["N_receptores"]),
                    "alcance":"Suma parcial observada; todos eventos captados válidos no acredita totalidad real"})
    for year, p in f.loc[f.universo_60 & f.directa].groupby("ano"):
        counts = p.groupby(["a_o_ent", "mes_ent"], dropna=False).size()
        temporal.extend(dict(ronda=int(year), ano_entrevista=None if pd.isna(y) else int(y),
            mes_entrevista=None if pd.isna(m) else int(m), N=int(n)) for (y,m),n in counts.items())
        geo.append(dict(ronda=int(year), N_directas=len(p), N_urbana=int(p.localidad_lpi.eq("Urbana").sum()),
            N_rural=int(p.localidad_lpi.eq("Rural").sum()), N_indeterminado=int(p.localidad_lpi.eq("Indeterminado").sum()),
            N_discordante=int(p.geo_discordante.sum()), variable=p.geo_variable.iloc[0]))
    metadata = json.loads((PROJECT_ROOT / "diccionarios/diccionario_integrado.json").read_text())
    meta_by_name={x['columna']:x for x in metadata}
    potential=[]
    for year in YEARS:
        contract=wave_contract(year)
        for role in [1,2]:
            if year==2001:
                fields=[f"k{58 if role==1 else 64}_{t}" for t in range(1,5)]
                supports=['k77_1' if role==1 else 'k80_1']
            elif year==2003:
                fields=[('k61'+t if role==1 else 'k67'+t) for t in ('abcd' if role==1 else 'cdef')]
                supports=['k80a' if role==1 else 'k83c']
            elif year==2012:
                fields=[f"k{61 if role==1 else 67}_{t}_12" for t in range(1,5)]
                supports=[f"k{80 if role==1 else 83}_1_12"]
            else:
                suffix=f'{year%100:02}'
                fields=[f"k{61 if role==1 else 67}_{t}_{slot}_{suffix}" for t in range(1,5) for slot in range(1,contract.slots+1)]
                supports=[f"k{80 if role==1 else 83}_1_{suffix}"] if year==2015 else [f"k{80 if role==1 else 83}_1_{slot}_{suffix}" for slot in range(1,3)]
            for via,names in [('K',fields),('A',supports)]:
                for name in names:
                    key=contract.household+'__'+name
                    assert key in meta_by_name,key
                    m=meta_by_name[key]
                    events=next((z for z in exact if z['ronda']==year and z['rama_fuente']==role and z['variable']==name),None)
                    potential.append(dict(ronda=year,via=via,rama_fuente=role,columna=key,
                        variable_original=name,etiqueta=m.get('etiqueta'),campo_tag=m.get('campo_tag'),
                        formato_stata=m.get('formato_stata'),N_eventos_captados=events['N_eventos'] if events else 0,
                        periodicidad='Mes normal, pesos mexicanos; fuente hogar y rama, evento por concepto/slot',
                        alcance='Campo disponible; sin eventos es ausencia de captura afirmativa, no cero de monto ni pérdida de definición'))
    alternatives = []
    for m in metadata:
        label = m.get("etiqueta", "").lower()
        if m.get("producto") == "imputada_hogar" and any(x in label for x in ["pension", "public", "donation", "donativo"]):
            alternatives.append({k:m.get(k) for k in ["columna","variable_original","fuente_id","ano","etiqueta","formato_stata","etiquetas_valores","perfil_tags_fuente"]} | {
                "uso07":"Inventario documental; no sumar con original, ni adoptar unidad anual o imputación sin contrato validado"})
    return dict(estado="Auditada antes de comparar montos reales", variables_originales=exact,
        campos_originales_disponibles=potential,
        receptores=universes, fechas_entrevista=temporal, geografia=geo, eventos=diagnostics,
        alternativas_imputadas=alternatives, fuentes=manifest,
        periodo_principal="Promedio INPC y LPI del año calendario anterior al año real de entrevista, criterio para año pasado; no fecha de pago observada",
        sensibilidad_temporal="12meses anteriores al mes real de entrevista; año de entrevista; mínimos/máximos mensuales del año previo",
        cero_A="Instrucciones2021 permiten0 cuando no se valora especie; no garantiza transferencia efectiva cero. Sensibilidad positivos.",
        imputacion="No se reimputan datos ni se suman versiones; original vs imputado se inventaría pero análisis usa originales.",
        conyuge="2018/2021 solo contexto con pareja confirmada. El monto es de otra persona, no transferencia al focal.")


def pricing(f: pd.DataFrame, indices: pd.DataFrame, lines: pd.DataFrame) -> pd.DataFrame:
    """Precios medios como criterio temporal explícito, jamás fecha de pago inferida."""
    f = f.copy()
    rows = []
    for y, m in f[["a_o_ent", "mes_ent"]].drop_duplicates().itertuples(index=False, name=None):
        row = dict(a_o_ent=y, mes_ent=m)
        if pd.notna(y) and float(y).is_integer() and 2001 <= y <= 2022:
            y = int(y)
            periods = [f"{y-1}-{i:02}" for i in range(1,13)]
            row["inpc_original"] = float(indices.loc[periods, "inpc"].mean())
            row["factor"] = REFERENCE_INDEX / row["inpc_original"]
            row["factor_min"] = REFERENCE_INDEX / float(indices.loc[periods, "inpc"].max())
            row["factor_max"] = REFERENCE_INDEX / float(indices.loc[periods, "inpc"].min())
            row["factor_ano_entrevista"] = REFERENCE_INDEX / float(indices.loc[[f"{y}-{i:02}" for i in range(1,13)],"inpc"].mean())
            for geo in ["rural", "urbana"]:
                row[f"lpi_{geo}"] = float(lines.loc[periods, f"lpi_{geo}"].mean())
            if pd.notna(m) and float(m).is_integer() and 1 <= m <= 12:
                end = pd.Period(f"{y}-{int(m):02}", freq="M")-1
                window = pd.period_range(end=end, periods=12, freq="M").astype(str)
                row["factor_12m"] = REFERENCE_INDEX / float(indices.loc[window,"inpc"].mean())
                for geo in ["rural", "urbana"]:
                    row[f"lpi_{geo}_12m"] = float(lines.loc[window,f"lpi_{geo}"].mean())
        rows.append(row)
    prices = pd.DataFrame(rows)
    f = f.merge(prices, on=["a_o_ent", "mes_ent"], how="left", validate="many_to_one")
    f["lpi_asignada"] = np.where(f.localidad_lpi.eq("Rural"), f.lpi_rural,
                               np.where(f.localidad_lpi.eq("Urbana"), f.lpi_urbana, np.nan))
    f["lpi_asignada_12m"] = np.where(f.localidad_lpi.eq("Rural"), f.lpi_rural_12m,
                                   np.where(f.localidad_lpi.eq("Urbana"), f.lpi_urbana_12m, np.nan))
    return f


def summarize(values: pd.Series) -> dict:
    """Cuantiles empíricos no ponderados, sin IC/significancia inventados."""
    x = values.dropna().astype(float)
    return dict(N=len(x), N_cero=int(x.eq(0).sum()),
        **{key:float(x.quantile(q)) if len(x) else None for key,q in
           [("p10",.1),("q25",.25),("mediana",.5),("q75",.75),("p90",.9),("p95",.95)]},
        media=float(x.mean()) if len(x) else None, de=float(x.std()) if len(x)>1 else None,
        iqr=float(x.quantile(.75)-x.quantile(.25)) if len(x) else None)


def partitions(f: pd.DataFrame, dimensions: tuple = DIMENSIONS) -> Iterator[tuple[str, str, pd.DataFrame]]:
    """Comparaciones separadas por dimensión, no un modelo ajustado."""
    yield "General", "Todas", f
    for dim in dimensions:
        for group, p in f.groupby(dim, observed=True, dropna=False):
            yield dim, str(group), p


def benefit_summary(p: pd.DataFrame, amount: str) -> dict:
    """Un importe parcial: nominal, real, temporal y relación con dos líneas."""
    v = p[amount]
    real = v * p.factor
    eligible = v.notna() & p.lpi_asignada.notna()
    ratios = 100*v/p.lpi_asignada
    return dict(nominal=summarize(v), real=summarize(real),
        reales_positivos=summarize(real.where(v.gt(0))),
        sensibilidad_ano_entrevista=summarize(v*p.factor_ano_entrevista),
        sensibilidad_12m=summarize(v*p.factor_12m),
        real_min_fecha=summarize(v*p.factor_min), real_max_fecha=summarize(v*p.factor_max),
        lpi_pct=summarize(ratios), lpi_pct_12m=summarize(100*v/p.lpi_asignada_12m),
        diferencia_lpi_nominal=summarize((v-p.lpi_asignada).where(v.notna())),
        diferencia_lpi_real=summarize((v-p.lpi_asignada)*p.factor),
        N_geografia_ND_monto=int((v.notna() & p.localidad_lpi.eq('Indeterminado')).sum()),
        N_periodo_ND_monto=int((v.notna() & p.factor.isna()).sum()),
        N_umbral_ND_monto=int((v.notna() & p.lpi_asignada.isna()).sum()),
        N_lpi=len(p.loc[eligible]), N_prestacion_inferior_lpi=int((eligible & v.lt(p.lpi_asignada)).sum()),
        prestacion_inferior_lpi_pct=pct(int((eligible & v.lt(p.lpi_asignada)).sum()), int(eligible.sum())),
        escenario_todos_rural_pct=summarize(100*v/p.lpi_rural),
        escenario_todos_urbana_pct=summarize(100*v/p.lpi_urbana))


def gaps(rows: list[dict]) -> list[dict]:
    """Brechas de medianas en mismo soporte, unidades nominal/real y razón explícita."""
    out=[]
    df=pd.DataFrame(rows)
    for (year,via,dim),group in df.loc[df.dimension.ne("General")].groupby(["ronda","via","dimension"]):
        for a,b in combinations(group.to_dict("records"),2):
            if "Desconocido" in [a["grupo"],b["grupo"]] or dim=="grupo_tipologia":
                continue
            z=dict(ronda=int(year),via=via,dimension=dim,grupo1=a["grupo"],grupo2=b["grupo"],
                   N1=a["persona"]["nominal"]["N"],N2=b["persona"]["nominal"]["N"])
            for unit in ["nominal","real"]:
                x,y=a["persona"][unit]["mediana"],b["persona"][unit]["mediana"]
                z[f"diferencia_{unit}"]=None if x is None or y is None else x-y
                z[f"razon_{unit}"]=x/y if x is not None and y not in [None,0] else None
                z[f"relativa_{unit}_pct"]=100*(x/y-1) if x is not None and y not in [None,0] else None
            out.append(z)
    return out


def retention(f: pd.DataFrame) -> list[dict]:
    """Selección económica: basal completo frente a retenidos de cada vía comparable."""
    out=[]
    for a,b,via in [(2001,2003,"K"),(2012,2015,"K"),(2018,2021,"K"),(2003,2012,"A"),(2012,2015,"A"),(2015,2018,"A")]:
        gate="pension_propia_k" if via=="K" else "apoyo_propio"
        amount=f"monto_{via.lower()}_propio_mensual_observado_parcial"
        o=f.loc[f.ano.eq(a) & f.universo_60 & f.directa].set_index("id")
        d=f.loc[f.ano.eq(b)].set_index("id")
        p=o.join(d,how="left",lsuffix="_a",rsuffix="_b",validate="one_to_one")
        state=pd.Series("Ausente; vital desconocido",index=p.index)
        state.loc[p.tipent_b.eq(5)]="Fallecido registrado"
        state.loc[p.tipent_b.isin([3,4])]="Sustituto vivo"
        direct=p.tipent_b.isin([1,2])
        state.loc[direct]="Directa; recepción ND"
        state.loc[direct & p[gate+"_b"].notna()]="Directa; recepción conocida"
        for dim in ["General",*GROUPS]:
            for group,q in ([("Todas",p)] if dim=="General" else p.groupby(dim+"_a",observed=True)):
                known=q[gate+"_a"].notna()
                keep=known & q.tipent_b.isin([1,2]) & q[gate+"_b"].notna()
                rec=q[gate+"_a"].eq(True).fillna(False)
                observed_money=keep & rec & q[gate+"_b"].eq(True).fillna(False) & q[amount+"_a"].notna() & q[amount+"_b"].notna()
                counts=state.loc[q.index].value_counts().to_dict()
                out.append(dict(origen=a,destino=b,via=via,dimension=dim,grupo=str(group),N_basal=len(q),
                    estados={s:int(counts.get(s,0)) for s in ["Fallecido registrado","Ausente; vital desconocido","Sustituto vivo","Directa; recepción ND","Directa; recepción conocida"]},
                    N_basal_recepcion_conocida=int(known.sum()), N_pares_conocidos=int(keep.sum()),
                    cobertura_basal_pct=pct(int(q.loc[known,gate+"_a"].eq(True).sum()),int(known.sum())),
                    cobertura_basal_retenidos_pct=pct(int(q.loc[keep,gate+"_a"].eq(True).sum()),int(keep.sum())),
                    cobertura_destino_retenidos_pct=pct(int(q.loc[keep,gate+"_b"].eq(True).sum()),int(keep.sum())),
                    nominal_basal=summarize(q.loc[rec,amount+"_a"]), real_basal=summarize(q.loc[rec,amount+"_a"]*q.loc[rec,"factor_a"]),
                    nominal_basal_retenidos=summarize(q.loc[keep & rec,amount+"_a"]),
                    real_basal_retenidos=summarize(q.loc[keep & rec,amount+"_a"]*q.loc[keep & rec,"factor_a"]),
                    N_receptores_ambas_monto=int(observed_money.sum()),
                    cambio_nominal_receptores_ambas=summarize(q.loc[observed_money,amount+"_b"]-q.loc[observed_money,amount+"_a"]),
                    cambio_real_receptores_ambas=summarize(q.loc[observed_money,amount+"_b"]*q.loc[observed_money,"factor_b"]-q.loc[observed_money,amount+"_a"]*q.loc[observed_money,"factor_a"])))
    return out


def normative(indices: pd.DataFrame, lines: pd.DataFrame) -> list[dict]:
    """Prestaciones normativas reales por periodo, sin atribuirlas a toda respuestaA."""
    records=[]
    schedule=[(2007,500),(2009,500),(2012,500),(2013,525),
              (2014,580),(2015,580),(2018,580),(2019,1275),(2020,1310)]
    periods=[(str(y),[f"{y}-{m:02}" for m in range(1,13)],amount) for y,amount in schedule]
    periods += [("2021 enero–junio",[f"2021-{m:02}" for m in range(1,7)],1350),
                ("2021 julio–diciembre",[f"2021-{m:02}" for m in range(7,13)],1550)]
    for label,months,amount in periods:
        idx=float(indices.loc[months,"inpc"].mean())
        lr,lu=[float(lines.loc[months,"lpi_"+g].mean()) for g in ["rural","urbana"]]
        records.append(dict(periodo=label,N_meses=len(months),nominal_mensual=amount,
            nominal_bimestral=2*amount,inpc=idx,real_mensual=amount*REFERENCE_INDEX/idx,
            lpi_rural=lr,lpi_urbana=lu,lpi_rural_pct=100*amount/lr,lpi_urbana_pct=100*amount/lu,
            criterio="Promedio del periodo indicado; no fechas de pagos individuales.2013 cambio segundo bimestre;2021 vigencia8julio, sin prorrateo diario."))
    return records


def analyze() -> dict:
    """Ampliación07; exige auditoría concluida y concilia todos nominales con06."""
    verify_inputs()
    audit_result=json.loads((OUTPUT / "auditoria.json").read_text())
    assert audit_result["estado"]=="Auditada antes de comparar montos reales"
    indices,lines,manifest=sources()
    f=pricing(panel(),indices,lines)
    eligible=f.loc[f.universo_60 & f.directa].copy()
    assert len(eligible)==50841
    previous=json.loads((INTERIM_DIR/"cobertura_proteccion_economica/resultados.json").read_text())
    rows,proxy,spouse,programs,norm_comparison,institution_groups,comparison=[],[],[],[],[],[],[]
    for via in ["K","A"]:
        gate="pension_propia_k" if via=="K" else "apoyo_propio"
        amount=f"monto_{via.lower()}_propio_mensual_observado_parcial"
        e,_=load_events(f,via)
        for year in YEARS:
            ef=e.loc[e.ano.eq(year) & e.universo_60.eq(True) & e.directa.eq(True)]
            yp=eligible.loc[eligible.ano.eq(year)]
            if via=="K":
                ef=ef.copy()
                security=ef.seguridad_social_identificada.eq(True)
                public=ef.programa_publico_agrupado.eq(True)
                ef["institucion_grupo"]=np.select([security & public,public & ~security,security & ~public],
                    ["Evidencia seguridad social y programa agrupado","Evidencia programa público agrupado","Evidencia seguridad social"],
                    default="Sin esas evidencias institucionales")
                for label,q in ef.groupby("institucion_grupo",observed=True):
                    institution_groups.append(dict(ronda=year,grupo=str(label),N_eventos=len(q),N_personas=q.id.nunique(),
                        N_eventos_monto_separable=int(q.monto_separable_por_institucion.eq(True).sum()),
                        evento=benefit_summary(q,"monto_mensual_observado"),
                        alcance="Partición de eventos por evidencia; personas pueden aparecer en varios grupos. Multiselección no reparte monto ni identifica programa específico."))
            for dim,group,p in partitions(yp):
                recipients=p.loc[p[gate].eq(True).fillna(False)]
                events=ef.loc[ef.id.isin(p.id)]
                n_events=events.groupby("id").monto_mensual_observado.agg(N="size",valid="count")
                full_ids=n_events.index[n_events.N.eq(n_events.valid)]
                observed_sum=events.groupby("id").monto_mensual_observado.sum(min_count=1)
                raw=recipients.set_index("id")[amount]
                pd.testing.assert_series_equal(observed_sum.sort_index(),raw.reindex(observed_sum.index).sort_index(),check_names=False,check_dtype=False)
                row=dict(ronda=year,via=via,dimension=dim,grupo=group,N_elegible=len(p),
                    N_receptores=len(recipients),N_monto=int(recipients[amount].notna().sum()),
                    N_receptores_sin_monto=int(recipients[amount].isna().sum()),N_eventos=len(events),
                    N_eventos_ND=int(events.monto_mensual_observado.isna().sum()),
                    N_todos_eventos_capturados=len(full_ids),
                    N_parciales=int(recipients.loc[~recipients.id.isin(full_ids),amount].notna().sum()),
                    persona=benefit_summary(recipients,amount),evento=benefit_summary(events,"monto_mensual_observado"),
                    real_todos_eventos_capturados=summarize(recipients.loc[recipients.id.isin(full_ids),amount]*recipients.loc[recipients.id.isin(full_ids),"factor"]))
                rows.append(row)
                if dim in ["General",*GROUPS]:
                    old=next(x for x in previous["montos"] if x["ronda"]==year and x["via"]==via and x["dimension"]==dim and x["grupo"]==group)
                    assert row["N_monto"]==old["N_personas_monto"] and row["N_eventos"]==old["N_eventos"]
                    assert row["persona"]["nominal"]["mediana"]==old["suma_personal_observada_parcial"]["mediana"]
            allvalid=f.loc[f.ano.eq(year) & f.universo_60 & f[gate].eq(True).fillna(False)]
            proxy.append(dict(ronda=year,via=via,N_receptores=len(allvalid),N_sustitutos=int((~allvalid.directa).sum()),
                              persona=benefit_summary(allvalid,amount)))
            if via=="A" and year in [2018,2021]:
                for label,q in ef.groupby("programa",observed=True,dropna=False):
                    programs.append(dict(ronda=year,programa=str(label),N_eventos=len(q),
                                         N_personas=q.id.nunique(),
                                         evento=benefit_summary(q,"monto_mensual_observado")))
                if year==2021:
                    q=ef.loc[ef.programa_codigo_original.eq(5)].copy()
                    assert q.id.is_unique,'Revisar múltiples capturasA5 antes de comparar por persona'
                    for dim,label,s in partitions(q):
                        k=next((x for x in rows if x['ronda']==2021 and x['via']=='K' and x['dimension']==dim and x['grupo']==label),None)
                        if k is None:continue
                        public=benefit_summary(s,'monto_mensual_observado')
                        z=dict(ronda=2021,dimension=dim,grupo=label,K_evento=k['evento'],A5_evento=public,
                            alcance='Importe mensual por eventoK frente a A5 de vejez con norma monetaria verificada; poblaciones receptoras diferentes. No contribuciónK ni total personal.')
                        for unit in ['nominal','real']:
                            x,y=k['evento'][unit]['mediana'],public[unit]['mediana']
                            z['diferencia_'+unit]=x-y if x is not None and y is not None else None
                            z['razon_'+unit]=x/y if x is not None and y not in [None,0] else None
                        comparison.append(z)
                    # Dos referencias explícitas; ninguna demuestra pago faltante/excedente.
                    q["norma_entrevista"]=np.where(q.a_o_ent.eq(2022),1925,
                        np.where(q.a_o_ent.eq(2021) & q.mes_ent.ge(7),1550,
                        np.where(q.a_o_ent.eq(2021) & q.mes_ent.le(6),1350,np.nan)))
                    q["norma_periodo_principal"]=np.where(q.a_o_ent.eq(2021),1310,
                        np.where(q.a_o_ent.eq(2022),1450,np.nan))
                    for dimension,label,s in partitions(q,dimensions=("edad_06",)):
                        z=dict(dimension=dimension,grupo=label,N_eventos=len(s),N_personas=s.id.nunique(),
                               declarado=benefit_summary(s,"monto_mensual_observado"))
                        for benchmark in ["norma_periodo_principal","norma_entrevista"]:
                            v=s.monto_mensual_observado;n=s[benchmark]
                            z[benchmark]=dict(nominal=summarize(n.where(v.notna())),
                                real=summarize((n*s.factor).where(v.notna())),
                                diferencia_nominal=summarize(v-n),diferencia_real=summarize((v-n)*s.factor),
                                razon_pct=summarize(100*v/n),N_iguales=int((v.notna() & v.eq(n)).sum()))
                        norm_comparison.append(z)
        if via=="K":
            for year in [2018,2021]:
                p=eligible.loc[eligible.ano.eq(year) & eligible.titularidad_pareja_estado.eq(PARTNER) & eligible.pension_conyuge_k.eq(True).fillna(False)]
                for dim,group,q in partitions(p,dimensions=GROUPS):
                    spouse.append(dict(ronda=year,dimension=dim,grupo=group,N_focales=len(q),
                                       contexto="Monto del cónyuge; otra persona, no transferencia propia",
                                       persona=benefit_summary(q,"monto_k_conyuge_mensual_observado_parcial")))
    marital=[]
    for year,p in eligible.groupby("ano"):
        for label,q in p.groupby("conyugal_grupo",observed=True):
            marital.append(dict(ronda=int(year),dimension="conyugal_grupo",grupo=str(label),**coverage(receipts(q))))
    factors=[]
    for (year,y),q in eligible.groupby(["ano","a_o_ent"]):
        factors.append(dict(ronda=int(year),ano_entrevista=int(y),ano_precio_principal=int(y)-1,N=len(q),
                            inpc_original=float(q.inpc_original.iloc[0]),factor=float(q.factor.iloc[0]),
                            lpi_rural=float(q.lpi_rural.iloc[0]),lpi_urbana=float(q.lpi_urbana.iloc[0])))
    return dict(pregunta=QUESTION,metodologia=dict(poblacion="60+ por visita; directas principal; sustitutos válidos sensibilidad",
        referencia=REFERENCE,inpc_referencia=REFERENCE_INDEX,formula="nominal×INPCreferencia/INPCperiodooriginal",
        ponderacion="No ponderado; diseño y pesos sin validar",valor_presente_actuarial=False,
        monto="Original mensual por evento y suma parcial por persona; nunca ingreso total, nunca K+A",
        periodo=audit_result["periodo_principal"],sensibilidad=audit_result["sensibilidad_temporal"]),
        factores=factors,montos=rows,brechas=gaps(rows),sustitutos_sensibilidad=proxy,conyuge=spouse,programas_A=programs,
        norma_programa=normative(indices,lines),comparacion_A5=norm_comparison,
        evidencia_institucional_K=institution_groups,
        comparacion_K_A5=comparison,
        cobertura06=previous["rondas"],cobertura_conyugal=marital,comparabilidad=previous["comparabilidad"],
        seleccion=retention(f),cotas06=previous["seguimiento_principal"],fuentes=manifest)
