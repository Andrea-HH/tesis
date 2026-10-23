"""J02: armonización económica y EDA 60+ desde la base existente y auditoría v1.

No importa scripts de integración/auditoría, no abre fuentes .dta ni sobrescribe sus productos.
"""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text, read_project_bytes

import argparse
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from tesis_enasem.integration import YEARS, response_number
from tesis_enasem.pension_ownership import wave_contract
from tesis_enasem.protection_eda import (UNKNOWN, STATES, support_contract, binary_receipt,
    receipt_state, support_events, pension_institution_evidence, add_profiles, joint_category,
    protection_crosstab, reception_rates, categorical_association, numeric_association,
    support_pension_gap, longitudinal_transitions)

ROOT = Path(__file__).resolve().parents[1]
BASE = project_path('', "data/processed/enasem_integrada_provisional.parquet")
AUDIT = project_path('', "data/processed/auditoria_titularidad_v1")
PRIVATE = project_path('', "data/processed/armonizacion_economica_v1")
PUBLIC = project_path('', "docs/eda/proteccion_economica")
FIGURES = project_path('', "reports/proteccion_economica/figuras")
GROUPS = ("localidad_grupo", "sexo_grupo", "educacion_grupo", "edad_grupo")
GROUP_LABELS = {"localidad_grupo": "Localidad a 100 mil (no ruralidad estricta)", "sexo_grupo": "Sexo",
                "educacion_grupo": "Escolaridad en primera entrevista", "edad_grupo": "Edad en la visita"}
COMPARABILITY = {
    "pension_propia_k": {(2001,2003): True, (2003,2012): False, (2012,2015): True,
                         (2015,2018): False, (2018,2021): True},
    "apoyo_propio": {(2001,2003): False, (2003,2012): True, (2012,2015): True,
                     (2015,2018): True, (2018,2021): False}}
COMPARABILITY_REASONS = {
    ("pension_propia_k",2001): "Mismas cuatro contingencias; orientación 2001 solo del proveedor. Condicionada, no definitiva.",
    ("pension_propia_k",2003): "En 2012 aparece categoría federal/estatal agrupada; no transición homogénea de cobertura K.",
    ("pension_propia_k",2012): "Mismas contingencias y selección institucional múltiple; aumenta captura de slots. Recepción binaria condicionada.",
    ("pension_propia_k",2015): "Cambio de lista/estructura institucional y de donativos; no declarar pérdida homogénea de pensión.",
    ("pension_propia_k",2018): "Cuatro contingencias y slots similares; se mantiene control doble. Comparación condicionada de K, no de toda pensión.",
    ("apoyo_propio",2001): "Ejemplos y alcance incorporan Seguro Popular en 2003; negativos históricos no equivalentes sin sensibilidad.",
    ("apoyo_propio",2003): "Donativo público dinero/especie adicional en año previo; categoría amplia, programa no identificable. Condicionada.",
    ("apoyo_propio",2012): "Mismo concepto agregado; nombres de ejemplos cambian. Condicionada al agregado, no continuidad de programas.",
    ("apoyo_propio",2015): "Mismo donativo adicional, dinero/especie; 2018 desglosa hasta dos instituciones. Solo recepción agregada condicionada.",
    ("apoyo_propio",2018): "2021 incorpora explícitamente vejez en opción 5 y cambia programas; no interpretar un inicio como expansión causal."}


def write_json(path: Path, value: object) -> None:
    """Serializa agregados; nunca publica filas individuales ni IDs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    write_project_text(path, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False))


def table(rows: list[dict], columns: list[str] | None = None) -> str:
    """Markdown sin ocultar filas ni denominadores."""
    if not rows:
        return "Sin observaciones para esta tabla."
    cols = columns or list(dict.fromkeys(k for r in rows for k in r))
    def value(v: object) -> str:
        if v is None or pd.isna(v):
            return "ND"
        if isinstance(v, (float, np.floating)):
            return f"{v:,.2f}"
        if isinstance(v, (int, np.integer)) and not isinstance(v, bool):
            return f"{v:,}"
        return str(v).replace("|", "/").replace("\n", " ")
    return "\n".join(["| "+" | ".join(cols)+" |", "| "+" | ".join("---" for _ in cols)+" |"]+
                     ["| "+" | ".join(value(r.get(c)) for c in cols)+" |" for r in rows])


def checked_inputs() -> dict[str, str]:
    """Congela las huellas de los productos anteriores; no reconstruye uniones."""
    paths = [BASE, *[project_path('data/processed/auditoria_titularidad_v1', f) for f in ("personas_ronda.parquet", "eventos_originales.parquet", "hogares.parquet", "manifest.json")],
             project_path('', "docs/integracion/titularidad/resultados.json"), project_path('', "reports/eda_independiente/simple_resultados.json")]
    hashes = {str(p.relative_to(ROOT)): sha256(read_project_bytes(p)).hexdigest() for p in paths}
    expected = json.loads(read_project_text(project_path('', "docs/integracion/validacion.json")))["hash_parquet"]
    if hashes[str(BASE.relative_to(ROOT))] != expected:
        raise ValueError("La base anterior cambió: no sustituir su referencia")
    return hashes


def metadata_columns() -> list[dict]:
    """Selección trazable de preguntas y versiones económicas ya integradas."""
    dictionary = json.loads(read_project_text(project_path('', "docs/integracion/diccionario_columnas.json")))
    selected = []
    for r in dictionary:
        v, source = r.get("variable_original", ""), r.get("fuente_id", "")
        if source in ("", "F20") or r["columna"].endswith("__stata_tag"):
            continue
        label = r.get("etiqueta", "").lower()
        relevant = (any(x in label for x in ("pension", "pensión", "retirement", "government gift", "public instit", "transfer income from institut"))
                    or re.search(r"^(imam|am|dum)?k?(76a|79a|82c|80_1|83_1)", v))
        if relevant:
            selected.append(r)
    return selected


def prepare() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[dict], list[dict], list[dict]]:
    """Auxiliares nuevos, alineados uno-a-uno con roles ya auditados."""
    schema = set(pq.read_schema(BASE).names)
    metadata = metadata_columns()
    required = {"id", "cunicah", "np", "ronda", "tipent", "edad", "sexo", "educacion", "urbano", "a_o_ent"}
    for c in ("edad", "educacion", "urbano"):
        if c+"__stata_tag" in schema:
            required.add(c+"__stata_tag")
    required.update(r["columna"] for r in metadata)
    required.update(r.get("campo_tag") for r in metadata if r.get("campo_tag"))
    for year in YEARS:
        w, a = wave_contract(year), support_contract(year)
        for v in (a.own_gate, a.spouse_gate, *a.own_amounts, *a.spouse_amounts, *a.own_programs, *a.spouse_programs):
            required.add(w.household+"__"+v)
        if w.couple:
            required.add(w.household+"__"+w.couple)
        for s in (w.household, w.individual, w.imputed):
            if s:
                required.add(s+"__enlace")
        weight = f"factori_{year%100:02}"
        if weight in schema:
            required.add(weight)
    missing = required-schema
    if missing:
        raise ValueError(f"Campos necesarios ausentes: {sorted(missing)}")
    source = pd.read_parquet(BASE, columns=sorted(required))
    ownership = pd.read_parquet(project_path('data/processed/auditoria_titularidad_v1', "personas_ronda.parquet"))
    if len(source) != len(ownership) or not (source.id.eq(ownership.id) & source.ronda.eq(ownership.ronda)).all():
        raise ValueError("Orden distinto: no alinear roles por posición")
    if len(source) != 99676 or source[["id", "ronda"]].duplicated().any():
        raise ValueError("Tamaño o clave maestra inesperados")
    frame = ownership.copy()
    for c in ("edad", "sexo", "educacion", "urbano", "a_o_ent"):
        frame[c] = source[c]
    for c in ("apoyo_propio", "apoyo_conyuge"):
        frame[c] = pd.Series(pd.NA, dtype="boolean", index=frame.index)
    contracts, support_rows, versions = [], [], []
    for year in YEARS:
        w, a = wave_contract(year), support_contract(year)
        mask = frame.ano.eq(year)
        prefix = w.household+"__"
        variables = (a.own_gate, a.spouse_gate, *a.own_amounts, *a.spouse_amounts, *a.own_programs, *a.spouse_programs)
        roles = {}
        for idx, row in frame.loc[mask & frame.titularidad_rama.notna()].iterrows():
            role = int(row.titularidad_rama)
            key = (row.hogar_fuente, role)
            if key in roles and roles[key] != row.id:
                raise ValueError("Rama pensionaria con más de un beneficiario")
            roles[key] = row.id
            own = a.own_gate if role == 1 else a.spouse_gate
            other = a.spouse_gate if role == 1 else a.own_gate
            frame.at[idx, "apoyo_propio"] = binary_receipt(source.at[idx, prefix+own])
            partner_state = row.titularidad_pareja_estado
            single = role == 1 and w.couple and response_number(source.at[idx,prefix+w.couple]) == 1
            if partner_state == "sin_pareja_residente_explicita" or single:
                frame.at[idx, "apoyo_conyuge"] = False
            elif partner_state in ("puntero_pareja_concordante", "contexto_pareja_pregunta_historica"):
                # Rama sin pareja histórica: el no de K no se extrapola a A si falta el control.
                val = binary_receipt(source.at[idx, prefix+other])
                frame.at[idx, "apoyo_conyuge"] = val
        # Cada entrevista económica/rol una vez; no sumar réplicas en las filas personales.
        hhs = frame.loc[mask & frame.hogar_fuente.notna()].drop_duplicates("hogar_fuente")
        for idx, row in hhs.iterrows():
            record = {v: source.at[idx, prefix+v] for v in variables}
            for role in (1, 2):
                for event in support_events(record, a, role):
                    event.update(ano=year, fuente=w.household, hogar_fuente=row.hogar_fuente,
                                 beneficiario_id=roles.get((row.hogar_fuente, role)))
                    support_rows.append(event)
        c = asdict(a)
        c.update(fuente_original=w.household, fuente_individual=w.individual, fuente_imputada_hogar=w.imputed,
                 universo="Recepción del periodo previo, personas vivas; propio exige rama orientada. Pareja exige otro puntero/filtro.",
                 unidad="Donativo público adicional dinero/especie; no equivale a pensión no contributiva",
                 periodo="Año previo a entrevista efectiva, distinto de ronda nominal",
                 monto="Mes normal nominal; frecuencia legal no observada. No sumar con K ni otras versiones.",
                 limite_2001="J1 independiente pendiente" if year==2001 else None,
                 discrepancia_2015="Cuestionario K80/K83 imprime seis dígitos; libro/etiquetas originales siete. Retener alerta." if year==2015 else None)
        contracts.append(c)
        for r in metadata:
            if not r["columna"].startswith(tuple(s+"__" for s in (w.household, w.individual, w.imputed) if s)):
                continue
            values = source.loc[mask & frame.edad.ge(60), r["columna"]]
            nums = pd.to_numeric(values, errors="coerce")
            tags = source.loc[values.index, r["campo_tag"]] if r.get("campo_tag") else None
            versions.append({"ano":year, "fuente":r["fuente_id"], "variable":r["variable_original"],
                "columna":r["columna"], "producto":r.get("producto"), "etiqueta":r.get("etiqueta"),
                "N_60":len(values), "N_almacenado_no_faltante":int(values.notna().sum()),
                "N_tags":int(tags.gt(0).sum()) if tags is not None else 0,
                "N_codigo_monto_NRNS_candidato":int(nums.isin((888888,999999,8888888,9999999)).sum()),
                "uso":"Fuente/versión conservada, no sumada y no usada para inferir recepción",
                "unidad_aprobada_comparacion_versiones":False})
    frame = add_profiles(frame)
    frame["categoria_conjunta"] = [joint_category(p,a) for p,a in zip(frame.pension_propia_k,frame.apoyo_propio)]
    frame["P"] = frame.pension_propia_k.map(receipt_state)
    frame["A"] = frame.apoyo_propio.map(receipt_state)
    frame["PA"] = [f"K:{p} A:{a}" if UNKNOWN not in (p,a) else UNKNOWN for p,a in zip(frame.P,frame.A)]
    e = pd.read_parquet(project_path('data/processed/auditoria_titularidad_v1', "eventos_originales.parquet"))
    enriched = pd.DataFrame([pension_institution_evidence(r) for r in e.to_dict("records")])
    pensions = pd.concat([e, enriched], axis=1)
    supports = pd.DataFrame(support_rows)
    frame["seguridad_social_evidencia"] = pd.Series(pd.NA,index=frame.index,dtype="boolean")
    frame.loc[frame.pension_propia_k.eq(False).fillna(False),"seguridad_social_evidencia"] = False
    frame["vejez_identificada_2021"] = pd.Series(pd.NA,index=frame.index,dtype="boolean")
    frame.loc[frame.ano.eq(2021)&frame.apoyo_propio.eq(False).fillna(False),"vejez_identificada_2021"] = False
    ss_keys = set(zip(pensions.loc[pensions.seguridad_social_identificada,"beneficiario_id"],
                      pensions.loc[pensions.seguridad_social_identificada,"ano"]))
    old_keys = set(zip(supports.loc[supports.ano.eq(2021)&supports.programa_codigo_original.eq(5),"beneficiario_id"],
                       supports.loc[supports.ano.eq(2021)&supports.programa_codigo_original.eq(5),"ano"]))
    for idx,r in frame.iterrows():
        if (r.id,r.ano) in ss_keys:
            frame.at[idx,"seguridad_social_evidencia"] = True
        if (r.id,r.ano) in old_keys:
            frame.at[idx,"vejez_identificada_2021"] = True
    # Montos separados por beneficiario/versión/bloque, nunca K+A ni persona+pareja.
    for block,data in (("k",pensions),("a",supports)):
        amount=data.groupby(["ano","hogar_fuente","rama"]).monto_mensual_observado.sum(min_count=1).to_dict()
        for label in ("propio","conyuge"):
            field=f"monto_{block}_{label}_mensual_observado_parcial"
            frame[field]=np.nan
            for idx,r in frame.loc[frame.titularidad_rama.notna()].iterrows():
                role=int(r.titularidad_rama)
                if label=="conyuge":
                    if r.titularidad_pareja_estado not in ("puntero_pareja_concordante","contexto_pareja_pregunta_historica"):
                        continue
                    role=3-role
                frame.at[idx,field]=amount.get((r.ano,r.hogar_fuente,role),np.nan)
    return frame, source, pensions, contracts, support_rows, versions


def summarize(frame: pd.DataFrame, source: pd.DataFrame, pensions: pd.DataFrame,
              supports: pd.DataFrame) -> dict:
    """Nuevos agregados descriptivos 60+ y transiciones; ninguna estimación nacional."""
    rates, categories, coverage, associations, numeric, gaps, cross = [], [], [], [], [], [], {}
    flows, money, institutions, programs, candidates, modes, weights = [], [], [], [], [], [], []
    institution_coverage, old_program_cross = [], []
    age60 = frame.loc[frame.edad.ge(60)]
    for year in YEARS:
        part = age60.loc[age60.ano.eq(year)]
        w = wave_contract(year)
        row = {"ano":year, "N_ronda_completa":int(frame.ano.eq(year).sum()), "N_60":len(part),
            "N_elegible_vivo_60":int(part.tipent.ne(5).sum()), "N_sobre_fallecido_60":int(part.tipent.eq(5).sum()),
            "N_edad_desconocida_ronda":int((frame.ano.eq(year)&frame.edad.isna()).sum()),
            "N_fuente_original_enlazada_60":int(part.hogar_fuente.notna().sum()),
            "N_titular_orientado_60":int(part.titularidad_rama.notna().sum()),
            "N_titular_indeterminado_60":int(part.titularidad_rama.isna().sum()),
            "ponderado":False}
        coverage.append(row)
        rates += [{"ano":year, **r} for r in reception_rates(part, [])]
        for mode, g in part.groupby("tipent"):
            modes += [{"ano":year,"tipent":int(mode), **r} for r in reception_rates(g, [])]
        for cat,g in part.groupby("categoria_conjunta",observed=True):
            categories.append({"ano":year,"categoria":cat,"N":len(g),"N_60":len(part),
                               "pct_60":100*len(g)/len(part)})
        gap = support_pension_gap(part)
        gaps.append({"ano":year, **gap})
        cross[f"{year}_pension_apoyo"] = protection_crosstab(part, [])
        associations.append({"ano":year,"cruce":"Pensión K × Apoyo", "estrato":"Toda submuestra 60+",
                              **categorical_association(part,"P","A")})
        for group in GROUPS:
            cross[f"{year}_recepcion_{group}"] = [{"ano":year, **r} for r in reception_rates(part,[group])]
            for outcome in ("P","A"):
                associations.append({"ano":year,"cruce":f"{outcome} × {GROUP_LABELS[group]}",
                    "estrato":"Toda submuestra 60+", **categorical_association(part,outcome,group)})
        for group in ("localidad_grupo","sexo_grupo"):
            cross[f"{year}_pension_apoyo_{group}"] = protection_crosstab(part,[group])
            for level, g in part.groupby(group,observed=True):
                if level == UNKNOWN:
                    continue
                associations.append({"ano":year,"cruce":f"Pensión K × Apoyo / {GROUP_LABELS[group]}",
                    "estrato":str(level), **categorical_association(g,"P","A")})
                gaps.append({"ano":year, "estratificador":group, "estrato":str(level), **support_pension_gap(g)})
        for group,condition in (("educacion_grupo","sexo_grupo"),("edad_grupo","localidad_grupo")):
            key=f"{year}_pension_{group}_{condition}"
            cross[key] = [{"ano":year, **r} for r in reception_rates(part,[condition,group]) if r["variable"]=="pension_propia_k"]
            for level,g in part.groupby(condition,observed=True):
                if level != UNKNOWN:
                    associations.append({"ano":year,"cruce":f"Pensión K × {GROUP_LABELS[group]} / {GROUP_LABELS[condition]}",
                        "estrato":str(level), **categorical_association(g,"P",group)})
        for control in ("edad","educacion"):
            for outcome in ("pension_propia_k","apoyo_propio"):
                numeric.append({"ano":year, "control":control,"recepcion":outcome, **numeric_association(part,control,outcome)})
        weight=f"factori_{year%100:02}"
        values=source.loc[part.index,weight] if weight in source else pd.Series(dtype=float)
        weights.append({"ano":year, "variable":weight,"N_60":len(part),"N_ponderador_positivo":int(values.gt(0).sum()),
                        "aplicado":False,"razon":"Factor transversal disponible; diseño, dominio 60+, calibración y atrición no validados"})
        selected_ids=set(part.id)
        for kind, data in (("K",pensions),("A",supports)):
            own=data.loc[data.ano.eq(year)&data.beneficiario_id.isin(selected_ids)]
            known=own.monto_mensual_observado.dropna()
            money.append({"ano":year,"bloque":kind,"unidad":"Evento de beneficiario 60+ identificado",
                "N_eventos":len(own),"N_beneficiarios":int(own.beneficiario_id.nunique()),"N_monto_observado":len(known),
                "N_monto_desconocido":len(own)-len(known), "mediana_nominal_mensual":float(known.median()) if len(known) else None,
                "p25":float(known.quantile(.25)) if len(known) else None,"p75":float(known.quantile(.75)) if len(known) else None,
                "suma_parcial_por_bloque":float(known.sum()),"sumable_entre_bloques":False})
        pe=pensions.loc[pensions.ano.eq(year)&pensions.beneficiario_id.isin(selected_ids)]
        ss_people=set(pe.loc[pe.seguridad_social_identificada,"beneficiario_id"])
        public_people=set(pe.loc[pe.programa_publico_agrupado,"beneficiario_id"])
        institution_coverage.append({"ano":year,"N_60":len(part),"N_IMSS_ISSSTE_identificado":len(ss_people),
            "N_programa_publico_agrupado_K":len(public_people),
            "N_K_afirmativa_sin_IMSS_ISSSTE_comprobado":int(part.pension_propia_k.eq(True).sum())-len(ss_people),
            "nota":"No IMSS/ISSSTE comprobado no significa ausencia de toda pensión contributiva; grupos pueden solaparse"})
        if year==2021:
            for ss in STATES:
                for old in STATES:
                    n=int((part.seguridad_social_evidencia.map(receipt_state).eq(ss)&
                           part.vejez_identificada_2021.map(receipt_state).eq(old)).sum())
                    old_program_cross.append({"ano":year,"seguridad_social_evidencia":ss,"vejez_identificada":old,
                        "N":n,"N_60":len(part),"pct_60":100*n/len(part),
                        "nota":"No seguridad social = negativa K; ND incluye otras instituciones sin clasificación exhaustiva. No vejez = negativa A."})
        for typ,g in pe.groupby("tipo"):
            institutions.append({"ano":year,"tipo_contingencia":int(typ),"N_eventos":len(g),
                "N_beneficiarios":int(g.beneficiario_id.nunique()),"N_slots_en_tipo_con_IMSS_ISSSTE":int(g.seguridad_social_identificada.sum()),
                "N_slots_en_tipo_con_programa_publico_agrupado":int(g.programa_publico_agrupado.sum()),
                "N_slots_en_tipo_con_institucion_sin_tipo_comprobado":int(g.institucion_sin_tipo_comprobado.sum()),
                "alcance":"En 2012/2015 institución identifica contingencia, no cada slot ni reparto del monto"})
        ae=supports.loc[supports.ano.eq(year)&supports.beneficiario_id.isin(selected_ids)]
        for (program,typ),g in ae.groupby(["programa","tipo_documental"],observed=True):
            programs.append({"ano":year,"programa":program,"tipo_documental":typ,"N_eventos":len(g),
                "N_beneficiarios":int(g.beneficiario_id.nunique()),"N_monto_observado":int(g.monto_mensual_observado.notna().sum())})
        # Revisión de pendientes existente, sin nueva adjudicación ni deduplicación.
        if year==2015:
            valid=pensions.loc[pensions.ano.eq(year)&pensions.enlazado_maestro&pensions.monto_mensual_observado.gt(0)]
            sig=[(r.hogar_fuente,r.tipo,r.instituciones_originales,r.monto_mensual_observado,r.anio_inicio_original)
                 for r in valid.itertuples()]
            counts=Counter(sig)
            repeated={s for s,n in counts.items() if n>1}
            candidates.append({"ano":year,"pendiente":"Firmas de pensión K 2015", "N_firmas":len(repeated),
                "N_eventos_en_firmas":sum(counts[s] for s in repeated),
                "accion":"Conservadas todas. Igual monto/institución/año no acredita prestación duplicada."})
            if len(repeated)!=33:
                raise ValueError("Firmas 2015 no reconciliadas con auditoría anterior")
        # Coincidencias K/A son señales de posible solapamiento, nunca descuentos automáticos.
        candidate_pairs=0
        for hh, g in pe.loc[pe.monto_mensual_observado.gt(0)].groupby("hogar_fuente"):
            other=ae.loc[ae.hogar_fuente.eq(hh)&ae.monto_mensual_observado.gt(0)]
            for p in g.itertuples():
                candidate_pairs += int((other.beneficiario_id.eq(p.beneficiario_id)&
                                        other.monto_mensual_observado.eq(p.monto_mensual_observado)).sum())
        candidates.append({"ano":year,"pendiente":"Coincidencia nominal K/A de mismo beneficiario 60+",
            "N_pares":candidate_pairs,"accion":"Señal, no prueba de doble prestación; no sumar K+A ni descontar."})
    for a,b in zip(YEARS[:-1],YEARS[1:]):
        for var in COMPARABILITY:
            flows += longitudinal_transitions(frame,a,b,var,COMPARABILITY[var][a,b])
    return {"bloque":"J02 armonización y EDA de protección económica", "fecha":"2026-10-12",
        "N_base_preservada":len(frame),"N_personas_periodo_base":int(frame.id.nunique()),
        "N_personas_ronda_60":len(age60),"N_personas_60_alguna_visita":int(age60.id.nunique()),
        "poblacion":"Edad >=60 en cada visita; todas las modalidades conservadas. Fallecidos desconocidos para recepción actual.",
        "ponderado":False,"cobertura":coverage,"recepcion":rates,"categorias":categories,"modalidades":modes,
        "cruces":cross,"asociaciones":associations,"asociaciones_ordinales":numeric,"brechas_apoyo":gaps,
        "transiciones":flows,"montos":money,"instituciones":institutions,"programas":programs,
        "pendientes_revisados":candidates,"ponderadores":weights,"cobertura_institucional":institution_coverage,
        "seguridad_social_vejez_2021":old_program_cross,
        "comparabilidad":[{"variable":v,"ano_origen":a,"ano_destino":b,"comparable_condicionada":c,
             "motivo":COMPARABILITY_REASONS[v,a]} for v,pairs in COMPARABILITY.items() for (a,b),c in pairs.items()]}


def draw_matrix(rows: list[dict], path: Path, title: str, groups: list[str]) -> None:
    """BrBG: N y porcentaje de fila K, incluidos desconocidos, por perfil."""
    data=pd.DataFrame(rows)
    blocks=[("Toda submuestra",data)] if not groups else list(data.groupby(groups,observed=True,dropna=False))
    cols=min(3,len(blocks)); nrows=int(np.ceil(len(blocks)/cols))
    fig,axes=plt.subplots(nrows,cols,figsize=(4.3*cols,3.4*nrows+1.2),squeeze=False)
    for ax,(level,block) in zip(axes.flat,blocks):
        numbers=block.pivot(index="pension",columns="apoyo",values="N").reindex(index=STATES,columns=STATES,fill_value=0)
        rates=numbers.div(numbers.sum(axis=1).replace(0,np.nan),axis=0)*100
        ax.imshow(rates.fillna(0),cmap="BrBG",vmin=0,vmax=100,aspect="auto")
        for i,j in np.ndindex(3,3):
            rate=rates.iloc[i,j]
            ax.text(j,i,f"{int(numbers.iloc[i,j]):,}\n{rate:.1f}%" if pd.notna(rate) else "0\nND",ha="center",va="center",fontsize=10,
                    color="white" if pd.notna(rate) and (rate<15 or rate>85) else "black")
        level=" / ".join(map(str,level)) if isinstance(level,tuple) else str(level)
        ax.set_title(level+f" · N={int(numbers.values.sum()):,}",fontsize=11)
        specialized = "Seguridad social" in title
        ax.set_xticks(range(3),["Vejez sí","Negativa A","Vejez ND"] if specialized else ["Apoyo sí","Apoyo no","Apoyo ND"],fontsize=9)
        ax.set_yticks(range(3),["IMSS/ISSSTE sí","Negativa K","SS sin resolver"] if specialized else ["Pensión sí","Pensión no","Pensión ND"],fontsize=9)
    for ax in list(axes.flat)[len(blocks):]:
        ax.set_visible(False)
    fig.suptitle(title+"\n60+ por visita · muestra sin ponderar",fontsize=13)
    fig.text(.02,.015,"Celda: N y % dentro de la fila pensionaria de cada estrato. ND se conserva; no equivale a negativa.\nK y A son bloques documentales; no todas las pensiones son contributivas. Denominadores y pares conocidos en tabla numérica.",fontsize=9)
    fig.tight_layout(rect=(0,.09,1,.9)); fig.savefig(path,dpi=140);plt.close(fig)


def draw_rates(rows: list[dict], path: Path, title: str, group: str, condition: str | None = None) -> None:
    """Tasas dentro de perfiles; denominador conocido explícito y desconocidos en tabla."""
    data=pd.DataFrame(rows)
    blocks=[("Toda submuestra",data)] if condition is None else list(data.groupby(condition,observed=True))
    fig,axes=plt.subplots(1,len(blocks),figsize=(max(8,5*len(blocks)),5.3),squeeze=False)
    colors=plt.get_cmap("BrBG")
    labels={"pension_propia_k":"Propia K","pension_conyuge_k":"Pareja K","apoyo_propio":"Apoyo propio A","apoyo_conyuge":"Apoyo pareja A"}
    variables=[v for v in labels if v in set(data.variable)]
    for ax,(level,block) in zip(axes.flat,blocks):
        levels=list(block[group].unique()); x=np.arange(len(levels)); width=.8/len(variables)
        for j,v in enumerate(variables):
            b=block.loc[block.variable.eq(v)].set_index(group).reindex(levels)
            values=b.pct_si_conocido.to_numpy(dtype=float)
            color=colors(.12 if len(variables)==1 else (j+.5)/len(variables))
            bars=ax.bar(x-.4+width*(j+.5),np.nan_to_num(values,nan=0),width=width,label=labels[v],color=color)
            for bar, val, n in zip(bars,values,b.N_si):
                label=f"{val:.1f}% (n={int(n)})" if np.isfinite(val) else "ND"
                ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+1,label,ha="center",fontsize=8,rotation=90)
        ax.set_xticks(x,levels,rotation=25,ha="right",fontsize=9);ax.set_ylim(0,135)
        ax.set_yticks(range(0,101,20))
        ax.set_ylabel("% recepción entre respuestas conocidas");ax.set_title(str(level),fontsize=11)
        ax.legend(fontsize=8);ax.grid(axis="y",alpha=.12)
    fig.suptitle(title+"\n60+ por visita · muestra sin ponderar",fontsize=13)
    fig.text(.02,.015,"Tasas dentro del grupo, no composición de receptores. N total/elegible/conocido/desconocido y porcentaje sobre N total en tabla.\nPareja sin pareja residente explícita se distingue documentalmente; falta de respuesta no se convierte en cero.",fontsize=9)
    fig.tight_layout(rect=(0,.1,1,.9));fig.savefig(path,dpi=140);plt.close(fig)


def figures(report: dict) -> list[dict]:
    """Una figura y tabla por cruce/onda; figuras de transición adicionales."""
    FIGURES.mkdir(parents=True,exist_ok=True)
    index=[]
    for key,rows in report["cruces"].items():
        year=int(key.split("_")[0]); path=project_path('reports/proteccion_economica/figuras', key+".png")
        if "pension_apoyo" in key:
            groups=[g for g in GROUPS if g in rows[0]]
            title=f"{year} · Seguridad social identificada × vejez explícita" if "seguridad_social" in key else f"{year} · Pensión K × donativo público A"
            draw_matrix(rows,path,title,groups)
        else:
            groups=[g for g in GROUPS if g in rows[0]]
            group=groups[-1]
            condition=groups[0] if len(groups)>1 else None
            # El orden semántico para educación×sexo/edad×localidad se fija explícitamente.
            if "educacion_grupo_sexo_grupo" in key:
                group,condition="educacion_grupo","sexo_grupo"
            if "edad_grupo_localidad_grupo" in key:
                group,condition="edad_grupo","localidad_grupo"
            draw_rates(rows,path,f"{year} · Recepción × {GROUP_LABELS[group]}",group,condition)
        table_path=project_path('docs/eda/proteccion_economica', "tablas", key+".json")
        write_json(table_path,rows)
        index.append({"cruce":key,"N_filas_tabla":len(rows),"tabla":str(table_path.relative_to(ROOT)),
                      "figura":str(path.relative_to(ROOT))})
    for var in COMPARABILITY:
        for a,b in zip(YEARS[:-1],YEARS[1:]):
            rows=[r for r in report["transiciones"] if r["variable"]==var and r["ano_origen"]==a]
            data=pd.DataFrame(rows)
            pivot=data.pivot_table(index="origen",columns="destino",values="N",aggfunc="sum",fill_value=0).reindex(index=STATES,fill_value=0)
            fig,ax=plt.subplots(figsize=(11,4.8))
            ax.imshow(pivot,cmap="BrBG",aspect="auto")
            for i,j in np.ndindex(pivot.shape):
                value=float(pivot.iloc[i,j]); maximum=float(pivot.values.max())
                color="white" if value<.15*maximum or value>.85*maximum else "black"
                ax.text(j,i,str(int(value)),ha="center",va="center",fontsize=10,color=color)
            ax.set_xticks(range(len(pivot.columns)),pivot.columns,rotation=24,ha="right",fontsize=9)
            ax.set_yticks(range(3),STATES);ax.set_title(f"{a} → {b} · {var}\nCohorte 60+ viva en origen, sin ponderar; conteos")
            fig.text(.02,.015,"Matriz de observación. Inicio/pérdida solo interpretables si el contrato admite comparación condicionada. Ausencia no prueba fallecimiento.",fontsize=9)
            fig.tight_layout(rect=(0,.09,1,1));key=f"transicion_{var}_{a}_{b}"
            path=project_path('reports/proteccion_economica/figuras', key+".png");fig.savefig(path,dpi=140);plt.close(fig)
            table_path=project_path('docs/eda/proteccion_economica', "tablas", key+".json");write_json(table_path,rows)
            index.append({"cruce":key,"N_filas_tabla":len(rows),"tabla":str(table_path.relative_to(ROOT)),"figura":str(path.relative_to(ROOT))})
    return index


def supplement(report: dict, frame: pd.DataFrame) -> None:
    """Contraste institucional 2021 desde auxiliares existentes, con desconocidos conservados."""
    part=frame.loc[frame.ano.eq(2021)&frame.edad.ge(60)].copy()
    part['pension_propia_k']=part.seguridad_social_evidencia
    part['apoyo_propio']=part.vejez_identificada_2021
    report['cruces']['2021_pension_apoyo_seguridad_social_vejez']=protection_crosstab(part,[])
    part['SS']=part.seguridad_social_evidencia.map(receipt_state)
    part['V']=part.vejez_identificada_2021.map(receipt_state)
    report['asociaciones']=[a for a in report['asociaciones'] if a['cruce']!='Seguridad social identificada × vejez explícita']
    report['asociaciones'].append({'ano':2021,'cruce':'Seguridad social identificada × vejez explícita',
        'estrato':'SS sí versus negativa K; vejez sí versus negativa A; excluye otros no tipificados',
        **categorical_association(part,'SS','V')})
    for row in report['cobertura']:
        year=row['ano']; mask=frame.ano.eq(year)&frame.edad.isna()
        row['N_edad_desconocida_vivos']=int((mask&frame.tipent.ne(5)).sum())
        row['N_edad_desconocida_sobre_fallecido']=int((mask&frame.tipent.eq(5)).sum())


def narrative(report: dict) -> None:
    """Interpretaciones específicas desde resultados, con delimitación del alcance económico."""
    intro=["# J02 · Pensiones y apoyos públicos: armonización y EDA conjunto", "",
        "## Objetivo, población y método", "",
        "Se estudia la recepción observada y su distribución entre perfiles de personas de 60 años o más en cada visita, sin filtrar permanentemente la base. Se reutilizan los roles y claves de la auditoría v1; no se repiten las 17 uniones ni se reclasifican sus titulares. La base anterior conserva 99,676 filas y 27,171 personas. K agrupa jubilación, viudez, incapacidad y otra pensión; A pregunta donativos públicos adicionales en dinero o especie durante el año previo. K no significa exclusivamente contributiva y A no significa exclusivamente pensión no contributiva.", "",
        "N total es la submuestra 60+ de la ronda. N elegible vivo excluye únicamente los registros sobre fallecidos para recepción contemporánea; estos se conservan y muestran desconocidos en N total. N orientado es cobertura de titularidad, no elegibilidad. N conocido exige respuesta sí/no admisible, nunca un monto positivo. La pareja requiere validación separada del puntero; ausencia de pareja residente se documenta aparte. Educación mide años en la primera entrevista; urbano es localidad <100 mil frente a ≥100 mil, no ruralidad estricta. Edad es la reportada en esa visita: no se corrigen las anomalías de CP1.", "",
        "Los factores transversales están disponibles, pero su calibración, dominio analítico y el diseño conjunto no están validados para esta selección y seguimiento. Todas las tablas describen la muestra, no estiman cobertura nacional. Se reportan V de Cramér y Spearman como tamaños de asociación contemporánea, sin pruebas de significación poblacional; los estratos desconocidos se muestran en tablas y se excluyen de esas medidas. Las celdas pequeñas se señalan. No hay modelos, causalidad, suficiencia de ingreso ni cambios de política identificados.", "",
        "## Armonización documental y contable", "",
        "2001: K76a/K79a; 2003: K79a/K82c; desde 2012: K79a/K82c con sufijo. Hasta 2015 el donativo es agregado sin nombre observado; los ejemplos del cuestionario no prueban el programa individual. En 2018 se permiten hasta dos instituciones (PROAGRO, PROSPERA, INAPAM, otra); en 2021 se modifican nombres y se añade explícitamente opción 5 de vejez. Las listas de instituciones K incluyen categorías públicas agrupadas en rondas posteriores. Solo IMSS/ISSSTE acreditan aquí seguridad social identificada; otros organismos/regímenes quedan sin tipificación automática. La categoría pública agrupada no identifica ámbito ni programa exacto. Los derechos de viudez corresponden a quien recibe, no a quien originó el derecho.", "",
        "El texto de K79/K82 excluye ingreso ya mencionado. Esta instrucción reduce solapamiento esperado, pero no demuestra que cada respuesta la respetó. Se conservan todas las mediciones y no se suman K+A ni las versiones original/imputada/construida. Los eventos propios se seleccionan por beneficiario auditado; montos del cónyuge quedan en sus eventos. Un mismo evento de hogar se cuenta una vez aunque aparezca en dos personas. Una segunda institución no multiplica un monto por contingencia. INAPAM no prueba una pensión monetaria y dinero/especie no puede separarse. El monto de mes normal no informa la periodicidad normativa de pago. La comparación entre años es nominal; no mide poder adquisitivo.", "",
        "La matriz contractual completa está en contratos_armonizacion.json, las versiones en versiones_fuente.json y las [fuentes primarias/hashes](../../integracion/titularidad/fuentes_documentales.json) en el dossier de titularidad. K2001 p.51 y p.52 documenta K76/K79; K2003 p.82 del cuestionario; K2012 p.101; K2015 p.102; K2018 pp.79/83; K2021 pp.66/70 (páginas PDF, cotejar foliación impresa). K80/K83 2015 tiene discrepancia documental de seis dígitos en cuestionario frente a siete en libro/etiquetas; los originales suministrados tienen 0 valores de los códigos de seis dígitos en ambos campos, por lo que la alerta no cambió montos ni recepción. Se conserva la discrepancia. Las etiquetas heredadas de programas en el libro 2021 no sustituyen la lista vigente del cuestionario.", "",
        "## Flujo y cobertura de fuentes", "",table(report["cobertura"]),"",table(report["ponderadores"]),"",
        "## Resultados independientes por ronda",""]
    text=intro
    for year in YEARS:
        cov=next(r for r in report["cobertura"] if r["ano"]==year)
        rates=[r for r in report["recepcion"] if r["ano"]==year]
        p=next(r for r in rates if r["variable"]=="pension_propia_k")
        a=next(r for r in rates if r["variable"]=="apoyo_propio")
        gap=next(r for r in report["brechas_apoyo"] if r["ano"]==year and "estrato" not in r)
        text += [f"### {year}","",table(rates),"",table([r for r in report["categorias"] if r["ano"]==year]),"",
                 f"De {cov['N_60']:,} registros de 60+, {cov['N_elegible_vivo_60']:,} corresponden a personas vivas y {cov['N_titular_orientado_60']:,} tienen orientación propia utilizable. Se identifica pensión propia K en {p['N_si']:,} y apoyo propio A en {a['N_si']:,}; quedan respectivamente {p['N_desconocido']:,} y {a['N_desconocido']:,} estados desconocidos. Entre respuestas conocidas, las proporciones son {p['pct_si_conocido']:.2f}% y {a['pct_si_conocido']:.2f}%. Estos porcentajes no deben confundirse con tasas sobre todos los elegibles ni con cobertura nacional.","",
                 table(gap["grupos"]),"",
                 f"El apoyo entre quienes tienen negativa propia K supera al apoyo entre receptoras K en {gap['diferencia_pp_no_menos_si']:.2f} puntos porcentuales (diferencia con signo). Se observan tanto cobertura adicional respecto de una negativa K como coexistencia. No se conoce el contrafactual sin programa, ni una negativa K descarta todas las pensiones no contributivas; por tanto, no se afirma una ampliación causal ni cobertura de personas sin ninguna pensión.","",
                 table([r for r in report["asociaciones"] if r["ano"]==year]),"",
                 table([r for r in report["asociaciones_ordinales"] if r["ano"]==year]),""]
        for group in GROUPS:
            key=f"{year}_recepcion_{group}"; rows=report["cruces"][key]
            text += [f"#### Recepción por {GROUP_LABELS[group]}","",table(rows),"",
                     f"![{key}](../../../reports/proteccion_economica/figuras/{key}.png)",""]
            for v in ("pension_propia_k","apoyo_propio"):
                known=[r for r in rows if r["variable"]==v and r[group]!=UNKNOWN and r["N_conocido"]]
                if known:
                    lo,hi=min(known,key=lambda r:r['pct_si_conocido']),max(known,key=lambda r:r['pct_si_conocido'])
                    text += [f"Para {v}, la tasa entre respuestas conocidas va de {lo['pct_si_conocido']:.2f}% en «{lo[group]}» ({lo['N_si']:,}/{lo['N_conocido']:,}) a {hi['pct_si_conocido']:.2f}% en «{hi[group]}» ({hi['N_si']:,}/{hi['N_conocido']:,}). Es una diferencia dentro de grupos, no la composición del conjunto receptor. Los desconocidos y tamaños de grupo se muestran arriba; la comparación puede reflejar selección documental y composición socioeconómica.",""]
        for suffix in ("pension_apoyo","pension_apoyo_localidad_grupo","pension_apoyo_sexo_grupo",
                       "pension_educacion_grupo_sexo_grupo","pension_edad_grupo_localidad_grupo"):
            key=f"{year}_{suffix}"; rows=report["cruces"][key]
            text += [f"#### Cruce {suffix}","",table(rows),"",
                f"![{key}](../../../reports/proteccion_economica/figuras/{key}.png)","",
                "Las celdas muestran N y su denominador propio. Las medidas estratificadas arriba permiten evaluar la heterogeneidad contemporánea; no se apilan rondas como observaciones independientes. Una celda ND permanece distinta de las negativas y los porcentajes entre pares conocidos no describen a quienes faltan.",""]
            if "pension_apoyo" in suffix:
                stratifiers=[g for g in GROUPS if g in rows[0]]
                blocks=[("Toda submuestra",rows)] if not stratifiers else [(level,[r for r in rows if r[stratifiers[0]]==level])
                    for level in dict.fromkeys(r[stratifiers[0]] for r in rows)]
                for level,block in blocks:
                    p_no=[r for r in block if r['pension']=='No' and r['apoyo']!=UNKNOWN]
                    p_yes=[r for r in block if r['pension']=='Sí' and r['apoyo']!=UNKNOWN]
                    na=sum(r['N'] for r in p_no);nb=sum(r['N'] for r in p_yes)
                    a_yes=sum(r['N'] for r in p_no if r['apoyo']=='Sí');b_yes=sum(r['N'] for r in p_yes if r['apoyo']=='Sí')
                    if na and nb:
                        text += [f"En «{level}», recibe apoyo {a_yes:,}/{na:,} ({100*a_yes/na:.2f}%) entre negativas K y {b_yes:,}/{nb:,} ({100*b_yes/nb:.2f}%) entre receptoras K. La diferencia es {100*a_yes/na-100*b_yes/nb:.2f} puntos porcentuales. Esta comparación distingue cobertura adicional observada y coexistencia dentro del mismo perfil; no prueba un cambio de elegibilidad ni impacto redistributivo.",""]
            else:
                condition="sexo_grupo" if "educacion" in suffix else "localidad_grupo"
                control="educacion_grupo" if "educacion" in suffix else "edad_grupo"
                for level in dict.fromkeys(r[condition] for r in rows):
                    block=[r for r in rows if r[condition]==level and r[control]!=UNKNOWN and r['N_conocido']]
                    if not block:
                        continue
                    lo,hi=min(block,key=lambda r:r['pct_si_conocido']),max(block,key=lambda r:r['pct_si_conocido'])
                    text += [f"Dentro de «{level}», la recepción K entre respuestas conocidas es menor en «{lo[control]}»: {lo['N_si']:,}/{lo['N_conocido']:,} ({lo['pct_si_conocido']:.2f}%), y mayor en «{hi[control]}»: {hi['N_si']:,}/{hi['N_conocido']:,} ({hi['pct_si_conocido']:.2f}%). Las diferencias no separan mecanismos de trayectoria laboral, cohortes o selección por supervivencia; las celdas pequeñas y faltantes limitan la precisión.",""]
        text += ["#### Instituciones, programas y montos", "",table([r for r in report["instituciones"] if r["ano"]==year]),"",
                 table([r for r in report["programas"] if r["ano"]==year]),"",table([r for r in report["montos"] if r["ano"]==year]),"",
                 "Los eventos y beneficiarios tienen denominadores distintos. Tipos 1/2/3/4 son jubilación/viudez/incapacidad/otra. Una persona puede recibir varios beneficios, por lo que los conteos institucionales no se suman como personas diferentes. Las medianas describen montos originales observados de eventos, con faltantes; no son ingreso total ni valor real comparable entre rondas.",""]
    text += ["## Seguridad social identificada y vejez explícita", "",table(report['cobertura_institucional']),"",
             table(report['seguridad_social_vejez_2021']),"",
             "IMSS/ISSSTE es evidencia positiva de familia contributiva, incluidas prestaciones derivadas; no determina régimen ni acredita cotización personal. No se recodifican las demás instituciones como no contributivas. La opción 5 de vejez 2021 acredita programa en el bloque de donativos; las negativas de vejez se limitan a negativas A, y los otros apoyos no se vuelven ausencia de vejez sin cobertura exhaustiva. Estos auxiliares no reemplazan las ocho especificaciones ni aprueban una clasificación final.","",
             "## Transiciones entre rondas consecutivas", "",table(report["comparabilidad"]),"",
             "La cohorte de cada par contiene personas de 60+ vivas en origen. Se conserva todo el seguimiento del maestro para distinguir muerte registrada, ausencia con posterior reaparición, ausencia sin retorno observado, edad final no elegible y recepción desconocida. Los intervalos son nominales, no duraciones exactas hasta iniciar una prestación. Solo pares señalados como comparables condicionados admiten inicio, continuidad y pérdida de recepción observada. En los demás pares se presenta la matriz de observación sin atribuir una trayectoria homogénea de recepción. No se identifica pérdida definitiva ni fecha de alta/baja.","",table(report["transiciones"]),"",
             "## Pendientes revisados y límites", "",table(report["pendientes_revisados"]),"",
             "J1/orden 2001, informantes externos y punteros discordantes no se resuelven por edad, sexo, monto ni por el cónyuge. Las 33 firmas 2015 se reconcilian desde eventos ya auditados y permanecen intactas. Los nuevos pares de igualdad nominal K/A son candidatos, no beneficios duplicados demostrados. Los bloques mixtos de divorcio/separación/supervivencia permanecen fuera de la suma; ‘negativas K y A’ no significa ausencia de toda prestación, de ingreso o de ayuda familiar. No se aprueban las ocho homologaciones definitivas ni decisiones predictivas.","",
             "La asociación puede estar afectada por dependencia entre cónyuges, no respuesta, attrición, supervivencia y composición de incorporaciones. No hay intervalos nacionales ni pruebas ajustadas por diseño; no se cuantifica impacto de políticas. Los cambios de instituciones, opciones, ejemplos y entrevistado económico limitan la historia 2001–2021. Ruralidad estricta, equivalencia monetaria, programas agrupados, periodicidad legal individual e imputación temporal siguen pendientes.","",
             "## Consulta y reproducción", "",
             "Abrir este informe en vista previa Markdown de VS Code y reports/notebooks/05d_pensiones_apoyos_ejecutado.ipynb. Las 54 tablas de cruces principales, el cruce institucional suplementario 2021 y 10 matrices de transición tienen figura BrBG y JSON numérico en indice_artefactos.json. Los microdatos nuevos quedan en data/processed/armonizacion_economica_v1, ignorados. El notebook fuente permite recalcular únicamente J02; por defecto carga agregados y verifica huellas. Ejecutar run_protection_eda.py → export_protection_manuscript.py → build_protection_notebook.py --execute. CP1, auditoría v1, B01 y base integrada previa se comprueban por huella y permanecen preservados.",""]
    write_project_text(project_path('docs/eda/proteccion_economica', "INFORME_PROTECCION_ECONOMICA.md"), "\n".join(text))
    lines=[]
    for a,b in zip(YEARS[:-1],YEARS[1:]):
        for v in COMPARABILITY:
            rows=[x for x in report['transiciones'] if x['ano_origen']==a and x['variable']==v]
            eligible=sum(x['N'] for x in rows if x['destino'] in STATES[:2] and x['origen'] in STATES[:2])
            counts={state:sum(x['N'] for x in rows if x['interpretacion']==state) for state in
                    ('Inicio observado','Continuidad observada','Pérdida de recepción observada','Negativas continuas')}
            deaths=sum(x['N'] for x in rows if x['destino']=='Sobre fallecido')
            absent=sum(x['N'] for x in rows if x['destino'].startswith('Ausente'))
            label='pensión K' if v.startswith('pension') else 'apoyo A'
            if COMPARABILITY[v][a,b]:
                n_yes=counts['Continuidad observada']+counts['Pérdida de recepción observada']
                n_no=counts['Inicio observado']+counts['Negativas continuas']
                lines.append(f"{a}–{b}, {label}: {eligible:,} pares de recepción conocidos; {counts['Inicio observado']:,}/{n_no:,} cambian de no a sí, {counts['Continuidad observada']:,}/{n_yes:,} mantienen sí y {counts['Pérdida de recepción observada']:,}/{n_yes:,} pasan de sí a no. Además, la cohorte registra {deaths:,} entrevistas sobre fallecidos y {absent:,} ausencias. Estos denominadores condicionan a seguimiento y respuesta; no son tasas administrativas ni efectos de política.")
            else:
                lines.append(f"{a}–{b}, {label}: existen {eligible:,} pares con respuestas conocidas, {deaths:,} entrevistas sobre fallecidos y {absent:,} ausencias de la cohorte. El contrato no permite interpretar estos pares como inicio o pérdida homogénea debido al cambio del instrumento.")
    report_path=project_path('docs/eda/proteccion_economica', 'INFORME_PROTECCION_ECONOMICA.md')
    body=read_project_text(report_path).replace('## Pendientes revisados y límites','### Interpretación del seguimiento\n\n'+'\n\n'.join(lines)+'\n\n## Pendientes revisados y límites')
    write_project_text(report_path, body)


def run() -> dict:
    """Ejecuta solo J02; verifica preservación y exporta evidencia agregada."""
    before=checked_inputs()
    frame,source,pensions,contracts,support_rows,versions=prepare()
    supports=pd.DataFrame(support_rows)
    report=summarize(frame,source,pensions,supports)
    supplement(report,frame)
    PRIVATE.mkdir(parents=True,exist_ok=True);PUBLIC.mkdir(parents=True,exist_ok=True)
    frame.to_parquet(project_path('data/processed/armonizacion_economica_v1', "personas_ronda.parquet"),index=False)
    pensions.to_parquet(project_path('data/processed/armonizacion_economica_v1', "eventos_pensionarios.parquet"),index=False)
    supports.to_parquet(project_path('data/processed/armonizacion_economica_v1', "eventos_apoyos.parquet"),index=False)
    report["huellas_preservadas"]=before
    if checked_inputs()!=before:
        raise ValueError("Un producto anterior cambió durante el análisis")
    write_json(project_path('docs/eda/proteccion_economica', "resultados.json"),report)
    write_json(project_path('docs/eda/proteccion_economica', "contratos_armonizacion.json"),contracts)
    write_json(project_path('docs/eda/proteccion_economica', "versiones_fuente.json"),versions)
    index=figures(report);write_json(project_path('docs/eda/proteccion_economica', "indice_artefactos.json"),index)
    write_json(project_path('data/processed/armonizacion_economica_v1', "manifest.json"),{"version":"v1","entradas_preservadas":before,
        "salidas":{p.name:sha256(read_project_bytes(p)).hexdigest() for p in PRIVATE.glob("*.parquet")},
        "N_registros":len(frame),"N_cruces":len(report["cruces"]),"N_figuras":len(index)})
    narrative(report)
    return report


if __name__=="__main__":
    from tesis_enasem.release_guard import block_legacy_export
    block_legacy_export()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports-only",action="store_true",help="Actualiza narrativa desde agregados sin recalcular")
    parser.add_argument("--figures-only",action="store_true",help="Actualiza figuras/agregados suplementarios desde sidecar sin repetir análisis")
    args=parser.parse_args()
    if args.figures_only:
        before=checked_inputs()
        r=json.loads(read_project_text(project_path('docs/eda/proteccion_economica', 'resultados.json')))
        p=pd.read_parquet(project_path('data/processed/armonizacion_economica_v1', 'personas_ronda.parquet'))
        # Precisa metadatos de ámbito institucional sin repetir distribución ni alterar montos.
        pensions=pd.read_parquet(project_path('data/processed/armonizacion_economica_v1', 'eventos_pensionarios.parquet'))
        pensions['alcance_evidencia_institucion']=['Contingencia completa; no asignable a slot' if
            'seleccion_multiple' in v else 'Institución del slot' for v in pensions.alcance_institucion]
        pensions.to_parquet(project_path('data/processed/armonizacion_economica_v1', 'eventos_pensionarios.parquet'),index=False)
        for row in r['instituciones']:
            for old,new in [('N_eventos_IMSS_ISSSTE','N_slots_en_tipo_con_IMSS_ISSSTE'),
                ('N_eventos_programa_publico_agrupado','N_slots_en_tipo_con_programa_publico_agrupado'),
                ('N_eventos_institucion_sin_tipo_comprobado','N_slots_en_tipo_con_institucion_sin_tipo_comprobado')]:
                if old in row:
                    row[new]=row.pop(old)
            row['alcance']='En 2012/2015 institución identifica contingencia, no cada slot ni reparto del monto'
        supplement(r,p);write_json(project_path('docs/eda/proteccion_economica', 'resultados.json'),r)
        index=figures(r);write_json(project_path('docs/eda/proteccion_economica', 'indice_artefactos.json'),index)
        m=json.loads(read_project_text(project_path('data/processed/armonizacion_economica_v1', 'manifest.json')));m['N_cruces']=len(r['cruces']);m['N_figuras']=len(index)
        m['salidas']['eventos_pensionarios.parquet']=sha256(read_project_bytes(project_path('data/processed/armonizacion_economica_v1', 'eventos_pensionarios.parquet'))).hexdigest()
        write_json(project_path('data/processed/armonizacion_economica_v1', 'manifest.json'),m);narrative(r)
        assert checked_inputs()==before
    elif args.reports_only:
        r=json.loads(read_project_text(project_path('docs/eda/proteccion_economica', "resultados.json")));narrative(r)
    else:
        r=run()
    print(json.dumps({k:r[k] for k in ("bloque","N_base_preservada","N_personas_ronda_60","N_personas_60_alguna_visita","cobertura")},ensure_ascii=False,indent=2))
