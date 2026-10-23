"""Audita titularidad desde las uniones existentes; base anterior de solo lectura."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text, read_project_bytes

import argparse
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from run_longitudinal_integration import ROOT, read_source, write_json, md_table as integration_md_table
from tesis_enasem.integration import YEARS, economic_link, response_number, person_id
from tesis_enasem.pension_ownership import (wave_contract, orient_person, receipt, tri_or,
                                          pension_events, unique_events, partner_pointer_confirmed)

BASE = project_path('', "data/processed/enasem_integrada_provisional.parquet")
PRIVATE = project_path('', "data/processed/auditoria_titularidad_v1")
PUBLIC = project_path('', "docs/integracion/titularidad")


def md_table(rows: list[dict]) -> str:
    """Muestra todas las columnas del agregado, incluyendo denominadores variables."""
    columns = list(dict.fromkeys(c for row in rows for c in row))
    return integration_md_table(rows, columns)


def state(value: object) -> str:
    """Codificación legible de booleanos anulables para transiciones agregadas."""
    return "desconocido" if value is None or pd.isna(value) else "si" if bool(value) else "no"


def run() -> dict:
    """Reproduce las seis rondas, guarda sidecars privados y solo publica agregados."""
    before = sha256(read_project_bytes(BASE)).hexdigest()
    validation = json.loads(read_project_text(project_path('', 'docs/integracion/validacion.json')))
    if before != validation['hash_parquet']:
        raise ValueError('La base cambió respecto a la integración anterior: no sustituir su referencia silenciosamente')
    inventory = json.loads(read_project_text(project_path('', "docs/pensiones/inventario_fuentes.json")))
    sources = {s["fuente_id"]: s for s in inventory["fuentes"]}
    for s in sources.values():
        if sha256(read_project_bytes(project_path('', "data/raw", s["archivo"]))).hexdigest() != s["sha256"]:
            raise ValueError("Fuente modificada respecto al inventario")
    master, _ = read_source(sources["F20"])
    master = master.copy()
    master["id"] = person_id(master)
    stored = pq.read_table(BASE, columns=["id", "ronda", "pension_recibe_k_2021", "econ_titular_estado",
                                        "pension_monto_mensual_observado_parcial_2021"]).to_pandas()
    if len(stored) != 99676 or stored[["id", "ronda"]].duplicated().any():
        raise ValueError("Base anterior sin unicidad o tamaño esperado")
    if not stored[["id", "ronda"]].equals(master[["id", "ronda"]].astype(stored[["id", "ronda"]].dtypes)):
        raise ValueError("Orden/identificadores distintos entre base y maestro")
    output = master[["id", "cunicah", "np", "ronda", "tipent"]].copy()
    output["ano"] = output.ronda.map(dict(enumerate(YEARS, 1)))
    for c in ["pension_propia_k", "pension_conyuge_k", "pension_hogar_k", "apoyo_vejez_propio_2021", "apoyo_vejez_conyuge_2021"]:
        output[c] = pd.Series(pd.NA, index=output.index, dtype="boolean")
    output["titularidad_estado"] = "sin_fuentes"
    output["titularidad_pareja_estado"] = "titular_propio_no_validado"
    output["titularidad_rama"] = pd.Series(pd.NA, index=output.index, dtype="Int8")
    output["hogar_fuente"] = None
    summaries, diagnostics, duplicates, events, households, transitions, modes = [], [], [], [], [], [], []
    checks, contracts = [], []
    for wave, year in enumerate(YEARS, 1):
        con = wave_contract(year)
        contracts.append(asdict(con))
        individual, _ = read_source(sources[con.individual])
        hh, _ = read_source(sources[con.household])
        bridge = individual if year in (2001, 2003) else None
        si = economic_link(master, individual, year, sources[con.individual]["clave_preferida"], True)
        sh = economic_link(master, hh, year, sources[con.household]["clave_preferida"], False, bridge)
        rows, ii, hi = si["rows"], si["indexer"], sh["indexer"]
        ind_records, hh_records = individual.to_dict("records"), hh.to_dict("records")
        if con.couple:
            single_records = [record for record in hh_records if response_number(record.get(con.couple)) == 1]
            contradictory = sum(receipt(record,con.spouse_gates) is True for record in single_records)
            checks.append({'ano':year,'fuente':con.household,'tipo':'filtro_pareja','N_pares_validos':len(single_records),
                           'N_discordantes':contradictory,'verificacion':'afirmativa_conyuge_en_rama_sin_pareja'})
            if contradictory:
                raise ValueError('Recepción en rama de pareja excluida: resolver universo antes de clasificar')
        if year in (2001,2003,2012):
            # Comprueba key como orientación relativa, no como NP/CLAVE absoluta.
            for typ in range(1,5):
                suff = f"_{year%100:02}"
                own_col = (f"imam55{'abcd'[typ-1]}_01" if year==2001 else
                           f"imam58{'abcd'[typ-1]}_03" if year==2003 else f"imamk61_{typ}_12")
                spouse_col = (f"imam61{'abcd'[typ-1]}_01" if year==2001 else
                              f"imam64{'cdef'[typ-1]}_03" if year==2003 else f"imamk67_{typ}_12")
                target_col = f"pens_{typ}{suff}"
                valid, different = 0,0
                for record in ind_records:
                    key = response_number(record.get(con.key))
                    if key not in (1,2):
                        continue
                    target = response_number(record.get(target_col))
                    selected = response_number(record.get(own_col if key==1 else spouse_col))
                    if target is not None and selected is not None:
                        valid += 1
                        different += abs(target-selected)>0.01+1e-7*abs(target)
                checks.append({"ano":year,"fuente":con.individual,"tipo":typ,"N_pares_validos":valid,
                               "N_discordantes":different,"verificacion":"pens_tipo_vs_imam_rama_key"})
        raw_roles = []
        partner_unchecked=pd.Series(pd.NA,index=rows,dtype='boolean')
        for n, idx in enumerate(rows):
            role, status = orient_person(master.iloc[idx], ind_records[ii[n]] if ii[n] >= 0 else None,
                                         hh_records[hi[n]] if hi[n] >= 0 else None, con)
            raw_roles.append((int(idx), int(hi[n]), role, status))
        # Una rama económica no puede identificar simultáneamente dos personas.
        counts = Counter((h, r) for _, h, r, _ in raw_roles if h >= 0 and r)
        role_ids = {(h, r): master.iloc[idx].id for idx, h, r, _ in raw_roles
                    if h >= 0 and r and counts[h, r] == 1}
        mappings = Counter(int(h) for h in hi if h >= 0)
        linked_hh = set(mappings)
        both_valid_hh = {h for h in linked_hh if (h, 1) in role_ids and (h, 2) in role_ids}
        for idx, h, role, status in raw_roles:
            if h >= 0:
                output.at[idx, "hogar_fuente"] = f"{con.household}:{h}"
                raw_household = hh_records[h]
                hg_a, hg_b = receipt(raw_household,con.own_gates), receipt(raw_household,con.spouse_gates)
                if con.couple and response_number(raw_household.get(con.couple)) == 1:
                    hg_b = False
                context = tri_or(hg_a,hg_b)
                output.at[idx,'pension_hogar_k'] = pd.NA if context is None else context
            if role and counts[h, role] > 1:
                role, status = None, "mas_de_una_persona_en_misma_rama"
            output.at[idx, "titularidad_estado"] = status
            if role is None:
                continue
            output.at[idx, "titularidad_rama"] = role
            record = hh_records[h]
            a, b = receipt(record, con.own_gates), receipt(record, con.spouse_gates)
            single = bool(con.couple and response_number(record.get(con.couple)) == 1)
            if single:
                b = False  # Ausencia de pareja residente explícita, no faltante convertido.
            own, spouse = (a, b) if role == 1 else (b, a)
            partner_unchecked.at[idx]=pd.NA if spouse is None else spouse
            pos = int(np.searchsorted(rows,idx))
            partner_ok,partner_status = partner_pointer_confirmed(ind_records[ii[pos]],record,con,role)
            output.at[idx,'titularidad_pareja_estado'] = partner_status
            if not partner_ok:
                spouse = None
            for c, value in [("pension_propia_k", own), ("pension_conyuge_k", spouse), ("pension_hogar_k", tri_or(a, b))]:
                output.at[idx, c] = pd.NA if value is None else value
            if year == 2021:
                for c, rama in [("apoyo_vejez_propio_2021", role), ("apoyo_vejez_conyuge_2021", 3-role)]:
                    if c == 'apoyo_vejez_conyuge_2021' and not partner_ok:
                        continue
                    g = "k79a_21" if rama == 1 else "k82c_21"
                    stem = "k79a_1" if rama == 1 else "k82c_1"
                    gate = response_number(record.get(g), (8, 9))
                    programs = [response_number(record.get(f"{stem}_{s}_21"), (8, 9)) for s in (1,2)]
                    value = True if gate == 1 and 5 in programs else False if gate == 2 else None
                    output.at[idx, c] = pd.NA if value is None else value
        # Hogares y eventos únicos: jamás sumar de nuevo las filas persona-ronda.
        wave_events = []
        for h, record in enumerate(hh_records):
            a, b = receipt(record, con.own_gates), receipt(record, con.spouse_gates)
            single = bool(con.couple and response_number(record.get(con.couple)) == 1)
            if single:
                b = False
            households.append({"ano": year, "hogar_fuente": f"{con.household}:{h}", "fuente": con.household,
                               "enlazado_maestro": h in linked_hh, "pension_hogar_k": tri_or(a,b),
                               "rama_informante_recibe": a, "rama_pareja_recibe": b})
            for role in (1, 2):
                for e in pension_events(record, con, role):
                    e.update(ano=year, fuente=con.household, hogar_fuente=f"{con.household}:{h}",
                             beneficiario_id=role_ids.get((h, role)), enlazado_maestro=h in linked_hh,
                             replicaciones_persona_maestro=mappings[h])
                    wave_events.append(e)
        wave_events = unique_events(wave_events)
        events.extend(wave_events)
        linked_events = [e for e in wave_events if e["enlazado_maestro"]]
        valid_amounts = [e for e in linked_events if e["monto_mensual_observado"] is not None]
        safe = sum(e["monto_mensual_observado"] for e in valid_amounts)
        naive = sum(e["monto_mensual_observado"]*e["replicaciones_persona_maestro"] for e in valid_amounts)
        # Firmas iguales son candidatos a revisión, NO una instrucción de deduplicar.
        signatures = Counter((e["hogar_fuente"], e["tipo"], e["instituciones_originales"], e["monto_mensual_observado"], e["anio_inicio_original"])
                             for e in valid_amounts if e["monto_mensual_observado"] > 0)
        repeated = {k for k,v in signatures.items() if v > 1}
        repeated_across = 0
        for signature in repeated:
            roles = {e['rama'] for e in valid_amounts if (e['hogar_fuente'],e['tipo'],e['instituciones_originales'],e['monto_mensual_observado'],e['anio_inicio_original']) == signature}
            repeated_across += len(roles)>1
        duplicates.append({"ano": year, "N_hogares_enlazados": len(linked_hh),
                           "N_hogares_ambas_personas_orientadas": len(both_valid_hh),
                           "N_slots_declarados_enlazados": len(linked_events), "N_slots_monto_observado": len(valid_amounts),
                           "N_slots_sin_monto_observado": len(linked_events)-len(valid_amounts),
                           "N_replicas_evitable_persona": sum(e["replicaciones_persona_maestro"]-1 for e in linked_events),
                           "suma_mensual_parcial_hogares": float(safe), "suma_ingenua_filas_persona": float(naive),
                           "exceso_por_replicacion": float(naive-safe),
                           "N_firmas_coincidentes_a_revisar": len(repeated),
                           "N_firmas_coincidentes_entre_beneficiarios": repeated_across,
                           "N_hogares_ambas_ramas_reciben": sum(receipt(hh_records[h], con.own_gates) is True and receipt(hh_records[h], con.spouse_gates) is True for h in linked_hh),
                           "N_slots_viudez": sum(e["tipo"] == 2 for e in linked_events),
                           "N_slots_viudez_beneficiario_identificado": sum(e["tipo"] == 2 and e["beneficiario_id"] is not None for e in linked_events)})
        part = output.iloc[rows]
        hpart = [h for h in households if h["ano"] == year and h["enlazado_maestro"]]
        summary = {"ano": year, "ronda": wave, "N_personas": len(part),
                   "N_titular_orientado": int(part.titularidad_rama.notna().sum()),
                   "N_titular_cotejo_independiente": 0 if year==2001 else int(part.titularidad_rama.notna().sum()),
                   "N_titular_indeterminado": int(part.titularidad_rama.isna().sum()),
                   "N_pension_propia_si": int(part.pension_propia_k.eq(True).sum()),
                   "N_pension_propia_no": int(part.pension_propia_k.eq(False).sum()),
                   "N_pension_propia_desconocida": int(part.pension_propia_k.isna().sum()),
                   "N_pension_conyuge_si": int(part.pension_conyuge_k.eq(True).sum()),
                   "N_pension_conyuge_no": int(part.pension_conyuge_k.eq(False).sum()),
                   "N_pension_conyuge_desconocida": int(part.pension_conyuge_k.isna().sum()),
                   "N_ambas_reciben": int((part.pension_propia_k.eq(True) & part.pension_conyuge_k.eq(True)).sum()),
                   "N_hogares_fuente": len(hh), "N_hogares_enlazados": len(hpart),
                   "N_hogares_pension_si": sum(h["pension_hogar_k"] is True for h in hpart),
                   "N_hogares_pension_no": sum(h["pension_hogar_k"] is False for h in hpart),
                   "N_hogares_pension_desconocida": sum(h["pension_hogar_k"] is None for h in hpart)}
        for kind in ("propia", "conyuge"):
            summary[f"pct_pension_{kind}_sobre_N_personas"] = 100*summary[f"N_pension_{kind}_si"]/len(part)
        if year == 2021:
            sums = {}
            for event in wave_events:
                beneficiary, amount = event['beneficiario_id'],event['monto_mensual_observado']
                if beneficiary is not None and amount is not None:
                    sums[beneficiary] = sums.get(beneficiary,0)+amount
            before_amount = stored.iloc[rows].pension_monto_mensual_observado_parcial_2021
            after_amount = part.id.map(sums)
            valid = before_amount.notna() & after_amount.notna()
            checks.append({'ano':year,'fuente':'F17/F10','tipo':'todas','N_pares_validos':int(valid.sum()),
                           'N_discordantes':int((before_amount[valid]-after_amount[valid]).abs().gt(.01).sum()),
                           'N_discordantes_disponibilidad':int((before_amount.notna()!=after_amount.notna()).sum()),
                           'verificacion':'monto_personal_almacenado_vs_eventos_originales_unicos'})
            for c in ("apoyo_vejez_propio_2021", "apoyo_vejez_conyuge_2021"):
                summary["N_"+c+"_si"] = int(part[c].eq(True).sum())
        summaries.append(summary)
        for status, n in part.titularidad_estado.value_counts().items():
            diagnostics.append({"ano": year, "estado": status, "N": int(n), "pct_N_ronda": 100*int(n)/len(part)})
        for status,n in part.titularidad_pareja_estado.value_counts().items():
            diagnostics.append({'ano':year,'estado':'pareja_'+status,'N':int(n),'pct_N_ronda':100*int(n)/len(part)})
        for mode, subgroup in part.groupby("tipent"):
            modes.append({"ano": year, "tipent": int(mode), "N": len(subgroup),
                          "N_titular_orientado": int(subgroup.titularidad_rama.notna().sum()),
                          "N_propia_si": int(subgroup.pension_propia_k.eq(True).sum()),
                          "N_propia_desconocida": int(subgroup.pension_propia_k.isna().sum())})
        if year >= 2018:
            pointer_a, pointer_b = f'k45d_{year%100}',f'k52a_1_{year%100}'
            pairs_hh = [(response_number(record.get(pointer_a)),response_number(record.get(pointer_b))) for record in hh_records]
            checks.append({'ano':year,'fuente':con.household,'tipo':'punteros_hogar',
                           'N_pares_validos':sum(a is not None and b is not None for a,b in pairs_hh),
                           'N_discordantes':sum(a is not None and b is not None and a==b for a,b in pairs_hh),
                           'verificacion':'ambas_ramas_apuntan_a_misma_persona'})
            for field in (f"k45d_{year%100}", f"k52a_1_{year%100}", f"k52a_{year%100}"):
                vals = [(response_number(ind_records[i].get(field)), response_number(hh_records[h].get(field))) for i,h in zip(ii,hi) if i>=0 and h>=0]
                complete = [(a,b) for a,b in vals if a is not None and b is not None]
                diagnostics.append({"ano": year, "estado": "cotejo_"+field, "N": sum(a!=b for a,b in complete), "N_pares_disponibles": len(complete)})
        if year == 2021:
            old = stored.iloc[rows].pension_recibe_k_2021.map(state)
            new = part.pension_propia_k.map(state)
            ct = pd.crosstab(old, new)
            for a in ct.index:
                for b in ct.columns:
                    transitions.append({"comparacion": "clasificacion_almacenada_vs_auditada", "antes": a, "despues": b, "N": int(ct.loc[a,b])})
            ct=pd.crosstab(partner_unchecked.map(state),part.pension_conyuge_k.map(state))
            for a in ct.index:
                for b in ct.columns:
                    transitions.append({'comparacion':'pareja_sin_cotejo_del_otro_puntero_vs_cotejada','antes':a,'despues':b,'N':int(ct.loc[a,b])})
            naive_states = [state(tri_or(receipt(hh_records[h], con.own_gates), receipt(hh_records[h], con.spouse_gates))) if h>=0 else "desconocido" for h in hi]
            ct = pd.crosstab(pd.Series(naive_states, index=rows), new)
            for a in ct.index:
                for b in ct.columns:
                    transitions.append({"comparacion": "contrafactual_cualquier_pension_hogar_atribuida_a_persona", "antes": a, "despues": b, "N": int(ct.loc[a,b])})
    if len(output) != 99676 or output[["id", "ronda"]].duplicated().any():
        raise ValueError("La auditoría alteró unidad persona-ronda")
    if sha256(read_project_bytes(BASE)).hexdigest() != before:
        raise ValueError("La base anterior fue modificada")
    report = {"version": "titularidad_v1", "base_sha256_preservada": before, "N_registros": len(output),
              "N_personas": output.id.nunique(), "fuentes_hash_verificadas": len(sources),
              "resumen_rondas": summaries, "estados_titularidad": diagnostics, "modalidades": modes,
              "cotejos_orientacion_construida": checks, "contratos_rondas": contracts,
              "duplicacion_montos": duplicates, "transiciones_2021": transitions,
              "definicion": "Recepción K de jubilación, viudez, invalidez/accidente y otras pensiones; apoyo vejez 2021 separado; provisional sin pesos"}
    PRIVATE.mkdir(parents=True, exist_ok=True)
    # Artefactos independientes: jamás se escribe BASE ni se eliminan sus columnas.
    output.to_parquet(project_path('data/processed/auditoria_titularidad_v1', "personas_ronda.parquet"), index=False)
    pd.DataFrame(events).to_parquet(project_path('data/processed/auditoria_titularidad_v1', "eventos_originales.parquet"), index=False)
    pd.DataFrame(households).to_parquet(project_path('data/processed/auditoria_titularidad_v1', "hogares.parquet"), index=False)
    write_json(project_path('data/processed/auditoria_titularidad_v1', "manifest.json"), {"base_sha256": before, "archivos": {p.name: sha256(read_project_bytes(p)).hexdigest() for p in PRIVATE.glob("*.parquet")}})
    write_json(project_path('docs/integracion/titularidad', "resultados.json"), report)
    write_json(project_path('docs/integracion/titularidad', 'diccionario_auxiliares.json'), {
        'version':'titularidad_v1','unidad':'persona-ronda','id':'cunicah:np original del maestro',
        'ronda':'nominal 1..6','ano':'año nominal, distinto de a_o_ent','tipent':'modalidad individual CP1',
        'pension_propia_k':'Booleano anulable, recepción K atribuida a beneficiario. 2001 orientación del proveedor candidata sin J1 independiente.',
        'pension_conyuge_k':'Booleano anulable, contexto de pareja residente; nunca ingreso del sujeto por esta variable.',
        'pension_hogar_k':'Contexto económico enlazado independiente de la orientación individual; no cuenta todos los habitantes de la vivienda.',
        'titularidad_rama':'1 rama informante, 2 rama pareja; ninguna implica recepción sin respuesta válida.',
        'titularidad_estado':'Motivo de orientación/indeterminación, conservando informante externo y discrepancias.',
        'titularidad_pareja_estado':'Cotejo separado del otro puntero moderno; su discrepancia no invalida la recepción propia concordante.',
        'hogar_fuente':'Localizador privado de fila fuente única. No es un identificador público ni clave longitudinal de hogar.',
        'apoyo_vejez_propio_2021':'Programa5 en K79/K82 según beneficiario; dinero o especie sin desglose.',
        'apoyo_vejez_conyuge_2021':'Programa5 de la pareja, nunca monto adjudicado al sujeto.',
        'eventos_originales':'Clave año+hogar_fuente+fuente+version+rama+tipo+slot única. Monto/inst/código de origen conservados; ningún imputado sumado.',
        'hogares':'Una fila económica fuente por año; recepción, enlace y ramas separadas. Parquet privado.',
        'faltantes':'NA no es cero ni ausencia de programa. Los códigos originales y tags completos permanecen en la base anterior.'})
    # Referencias/documentación, nunca copias de cuestionarios ni microdatos.
    document_folder = Path('/tmp/tesis-titularidad-docs')
    documents = []
    for file in ('fuentes.json','fuentes_adicionales.json','fuentes_cuestionarios.json','fuentes_codebooks.json'):
        if (document_folder/file).exists():
            documents.extend(json.loads(read_project_text(document_folder/file)))
    cached=Path('/tmp/tesis-pensiones-docs')
    for name,url in [('q2018','https://www.inegi.org.mx/contenidos/programas/enasem/2018/doc/enasem_2018_cuestionario_basico.pdf'),
                     ('q2021','https://www.inegi.org.mx/contenidos/programas/enasem/2021/doc/enasem_2021_cuestionario_basico.pdf'),
                     ('im2021','https://www.mhasweb.org/Resources/DOCUMENTS/2021/Imputation_of_Non_Reponse_on_Economic_Variables_in_the_MHAS_ENASEM_2021.pdf')]:
        path=cached/(name+'.pdf')
        if path.exists():
            import pymupdf
            with pymupdf.open(path) as document:
                pages=len(document)
            documents.append({'nombre':name,'url':url,'valido':True,'paginas':pages,'sha256':sha256(read_project_bytes(path)).hexdigest()})
    if documents:
        write_json(project_path('docs/integracion/titularidad', 'fuentes_documentales.json'),documents)
    render_report(report)
    return report


def render_report(report: dict) -> None:
    """Narrativa/tablas exclusivamente agregadas y con denominadores explícitos."""
    text = ["# Auditoría de titularidad pensionaria · versión 1", "",
            "## Objetivo, alcance y preservación", "",
            "Se evalúa a quién corresponde la recepción del bloque K, conservando todas las 99,676 personas-ronda de ENASEMsimple (27,171 personas del periodo). La base integrada anterior permanece intacta, con SHA-256 `"+report["base_sha256_preservada"]+"`. Los auxiliares se guardan por separado en data/processed/auditoria_titularidad_v1. Ningún identificador se publica. CP1 y los datos fuente no se modificaron.", "",
            "La pensión propia corresponde al beneficiario, aunque su pareja haya respondido la sección económica. Pensión del cónyuge significa contexto de la pareja residente, no ingreso adjudicado al sujeto. Ambas categorías pueden coexistir. Hogar significa entrevista económica de persona/pareja y subhogar específico: no constituye un censo de prestaciones de todos los miembros de la vivienda.", "",
            "## Método y límites documentales", "",
            "Se reutilizan las uniones auditadas: puentes F13/F14 en 2001/2003 y subhogares por año en 2012–2021. La clave personal sigue siendo cunicah:np, y cada observación id+ronda es única. La respuesta 1 confirma recepción; cuatro negativas 2 confirman ausencia en este bloque. NR=8, NS=9 y especiales Stata mantienen desconocidos. Una cantidad positiva, imputada o construida, no reemplaza la respuesta de recepción.", "",
            "2001 utiliza key01 del producto individual: orientación del proveedor, con validación independiente limitada porque J1/controles de entrevista no están suministrados. 2003 coteja key03 con K96a y codent03 (3 puede referirse a códigos 3/4, condicionado a unicidad). 2012/2015 cotejan key12/key15 con K96a y NP. Los informantes externos, ausentes o discordantes permanecen indeterminados; no se reconstruye el orden de entrevistas. 2018/2021 requieren concordancia del NP seleccionado en los punteros del individual y hogar; 2021 exige además key_21. Una misma rama no puede identificar dos personas. Todos estos son auxiliares provisionales, no una homologación final de ocho conceptos.", "",
            "La ausencia explícita de pareja residente permite cerrar su rama como no aplicable a pareja residente; no se deriva de columnas faltantes. En los hogares con rama de pareja desconocida se mantiene desconocida la ausencia total de pensiones. En las personas sobre fallecidos no se acredita recepción actual.", "",
            "## Resultados por ronda", ""]
    for row in report["resumen_rondas"]:
        y, n = row["ano"], row["N_personas"]
        person_rows = [{"Resultado": label, "N": row[key], "% de N ronda": round(100*row[key]/n,2)} for label,key in [
            ("Personas totales", "N_personas"), ("Titular orientado provisionalmente", "N_titular_orientado"),
            ("Titularidad indeterminada", "N_titular_indeterminado"), ("Pensión propia K: sí", "N_pension_propia_si"),
            ("Pensión propia K: no explícito", "N_pension_propia_no"), ("Pensión propia K: desconocida", "N_pension_propia_desconocida"),
            ("Personas con pensión del cónyuge K", "N_pension_conyuge_si"), ("Ambas personas reciben K", "N_ambas_reciben")]]
        person_rows += [{'Resultado':'Recepción de pareja K desconocida','N':row['N_pension_conyuge_desconocida'],'% de N ronda':round(100*row['N_pension_conyuge_desconocida']/n,2)}]
        hn = row["N_hogares_enlazados"]
        household_rows = [{"Resultado": label, "N": row[key], "% hogares enlazados": round(100*row[key]/hn,2)} for label,key in [
            ("Hogares enlazados únicos", "N_hogares_enlazados"), ("Hogares con pensión K", "N_hogares_pension_si"),
            ("Hogares sin pensión K explícita", "N_hogares_pension_no"), ("Hogares de recepción K desconocida", "N_hogares_pension_desconocida")]]
        text += [f"### {y}", "", md_table(person_rows), "", md_table(household_rows), "",
                 f"En {y}, {row['N_pension_propia_si']:,} de {n:,} personas de la ronda tienen evidencia de recepción propia K bajo estas reglas ({row['pct_pension_propia_sobre_N_personas']:.2f}%). La orientación se confirma o conserva documentalmente para {row['N_titular_orientado']:,}, mientras {row['N_titular_indeterminado']:,} requieren verificación. Hay {row['N_pension_conyuge_si']:,} personas cuya pareja recibe, incluidas {row['N_ambas_reciben']:,} que también reciben personalmente: estos conteos se solapan y no se suman como personas diferentes. {row['N_hogares_pension_si']:,} de {hn:,} entrevistas económicas enlazadas contienen recepción K; el denominador de hogar difiere del individual. No es una estimación nacional ponderada.", "",
                 md_table([r for r in report["estados_titularidad"] if r["ano"] == y]), ""]
        if y == 2001:
            text += ["Los titulares orientados se basan en key01 publicado; no se declara comprobación independiente del control J1. Su clasificación permanece candidata hasta recuperar ese control. No se confunde codent01 con NP moderno.", ""]
        if y in (2003,2012,2015):
            text += ["Los casos de informante externo o control discordante quedan desconocidos incluso si el proveedor publicó montos. El salto documental basado en orden de entrevista no se reproduce sin sus controles. Las diferencias entre rondas pueden reflejar disponibilidad de ese control y composición, además de cambios en recepción.", ""]
        if y == 2021:
            text += [f"El programa de vejez explícito se identifica adicionalmente para {row['N_apoyo_vejez_propio_2021_si']:,} personas y para {row['N_apoyo_vejez_conyuge_2021_si']:,} parejas. K79/K82 permite dinero o especie; esta evidencia se mantiene separada de recepción K y no acredita por sí sola un monto monetario. Una negativa en K58/K64 no significa ausencia de todo apoyo pensionario.", ""]
    changes = sum(r["N"] for r in report["transiciones_2021"] if r["comparacion"] == "clasificacion_almacenada_vs_auditada" and r["antes"] != r["despues"])
    partner_changes=sum(r['N'] for r in report['transiciones_2021'] if r['comparacion'].startswith('pareja_sin') and r['antes']!=r['despues'])
    partner_positive_changes=sum(r['N'] for r in report['transiciones_2021'] if r['comparacion'].startswith('pareja_sin') and r['antes']=='si' and r['despues']=='desconocido')
    text += ["## Cotejos de la orientación construida histórica", "", md_table(report['cotejos_orientacion_construida']), "",
             "Se coteja cada pens_tipo publicado contra el componente imam de la rama seleccionada por key (1 propia del informante económico, 2 pareja del informante). La concordancia valida el significado operativo del key en estos archivos; no reemplaza el control original de titularidad ni convierte el monto imputado en evidencia de recepción. CLAVE3 histórico identifica a una persona absoluta; key es una orientación relativa de la fila. No se intercambian.", ""]
    text += ["## Discrepancias y cambios de clasificación en 2021", "",
             f"La comparación con la clasificación efectivamente almacenada en la base anterior arroja **{changes:,} cambios de estado de recepción propia K**. Se presenta la matriz completa, incluidos desconocidos. La comparación de pareja es interna a la auditoría: rama orientada antes/después de cotejar el OTRO puntero, no un indicador guardado anteriormente. El escenario de cualquier pensión del hogar atribuida al sujeto es contrafactual y no fue la regla aplicada en la base anterior.", "",
             f"El cotejo adicional de pareja cambia **{partner_changes:,} estados a desconocidos**, incluidos **{partner_positive_changes:,} inicialmente afirmativos**. La recepción comprobable de pareja queda en {report['resumen_rondas'][-1]['N_pension_conyuge_si']:,}, y ambos reciben en {report['resumen_rondas'][-1]['N_ambas_reciben']:,}. No se alteran los punteros ni se adjudica al sujeto un pago de titularidad dudosa.", "",
             md_table(report["transiciones_2021"]), "",
             "Las diferencias de punteros se cuentan entre pares disponibles por campo; los 32 casos de puntero propio y 97 del cónyuge documentados previamente no se suman como errores independientes. La concordancia del puntero seleccionado puede confirmar un titular mientras el otro campo queda pendiente. No se corrigen NP ni se impone automáticamente una fuente sobre otra.", "",
             "## Auditoría de duplicación de montos", "", md_table(report["duplicacion_montos"]), "",
             "Cada evento original se identifica por año, hogar económico, fuente, versión, rama beneficiaria, contingencia y slot. Se agrega una sola vez en hogares, aunque el LEFT JOIN lo replique en dos filas individuales. La suma ingenua sirve exclusivamente para cuantificar esa replicación; no es una estimación de ingresos. Las sumas son montos mensuales observados parciales en pesos nominales de cada ronda: incluyen ceros válidos, excluyen NR/NS y cantidades faltantes, y no se comparan como poder adquisitivo real.", "",
             "Dos beneficios con monto e institución iguales, pertenecientes a beneficiarios o slots distintos, no se eliminan automáticamente. Las firmas coincidentes son candidatos a revisión de origen, no duplicados comprobados. Si ambos cónyuges reciben, se conservan ambas ramas y sus instituciones/montos. En 2012/2015 las instituciones son una selección múltiple por contingencia: no se multiplica el monto por institución ni se inventa una correspondencia institución-slot.", "",
             "Los montos originales, derivados, imputados y construidos ya están conservados en la base anterior. El registro de eventos usa solo originales: ningún valor imam/am, bandera ni pens_t/inc_pension se suma como ingreso adicional. Elegir una versión imputada para análisis futuros requerirá un registro separado con la misma clave lógica y su bandera. No se duplica la copia individual 2018 ni se incorpora 2024.", "",
             "Los libros K2001 PDF p.38 y K2003 p.43 documentan RF=888888 y NS=999999 para los montos pensionarios originales; en 2012–2021 son 8888888/9999999. Estos códigos se excluyen únicamente en las preguntas correspondientes y se conservan en monto_codigo_original. La revisión del primer cálculo de montos detectó que la regla de siete dígitos no era válida en las dos rondas tempranas; se corrigió el contrato y se recalculó únicamente esta auditoría, sin modificar la base ni el EDA anterior.", "",
             "## Viudez y supervivencia", "",
             "La contingencia de viudez (tipo 2) se atribuye a la persona que cobra según la orientación económica validada; quien generó originalmente el derecho no se transforma en receptor actual. Las expectativas de heredar una pensión K60/K63/K66/K69 o K70–77 no son pagos recibidos. Los montos antes/después de la muerte K101/K103 pueden referirse a prestaciones ya registradas en K58/K64 y no se añaden a sus slots. Los bloques de divorcio/separación/supervivencia K79b/K82d permanecen como fuentes separadas de composición ambigua; no se tipifican automáticamente como pensión previsional ni se suman sin reconciliar.", "",
             "## Modalidades y limitaciones", "", md_table(report["modalidades"]), "",
             "Los conteos conservan directas, sustitutos y sobre fallecidos con sus códigos individuales de CP1. El informante económico no es necesariamente el beneficiario ni el entrevistado directo. No hay pesos longitudinales aprobados, deflactor, clasificación definitiva contributiva/no contributiva ni corrección automática de punteros. También sigue pendiente recuperar J1/control 2001, validar órdenes históricos, resolver discrepancias 2021 y cotejar la titularidad contra fuentes adicionales. La recepción declarada se refiere al periodo retrospectivo de cada cuestionario, no acredita cobro al día de entrevista.", "",
             "El descenso del conteo K entre 2015 y 2018 no demuestra pérdida de cobertura pensionaria: las categorías institucionales cambian. K59/K65 en 2012/2015 permite programas federales/estatales, mientras 2018/2021 pregunta los apoyos públicos en otro bloque. En 2012, 3,279 hogares mantienen desconocida la ausencia total por falta de un filtro de pareja utilizable en el archivo suministrado; la falta de afirmativas no se transformó en ausencia. Completar este denominador exige controles originales adicionales. La comparación temporal es de composición y cobertura documental, no de efectos causales ni trayectoria individual de cobro.", "",
             "## Documentos primarios cotejados", "",
             "Cuestionarios básicos y libros K de cada ronda, concordancia de preguntas y documentos de imputación del proveedor. Los localizadores/huellas están en fuentes_documentales.json; el documento de variables creadas v4/mayo 2026 no describe por sí solo las reglas económicas y no se utiliza para fijar titularidad.", ""]
    for document in json.loads(read_project_text(project_path('docs/integracion/titularidad', 'fuentes_documentales.json'))) if (project_path('docs/integracion/titularidad', 'fuentes_documentales.json')).exists() else []:
        if document.get('valido'):
            text.append(f"- [{document['nombre']}]({document['url']}), {document['paginas']} páginas; SHA-256 registrado.")
    text += ["", "## Reproducción y consulta en VS Code", "",
             "Ejecutar `python scripts/run_pension_ownership_audit.py` y `python scripts/build_ownership_notebook.py --execute`. Abrir el informe, `resultados.json` y `reports/notebooks/05c_titularidad_pensiones_ejecutado.ipynb`. Los Parquet del sidecar contienen microdatos privados: no deben publicarse. El notebook fuente no contiene outputs y la copia ejecutada muestra exclusivamente agregados. La redacción y tabla de síntesis se incluyen en capítulos 3–4 del manuscrito.", ""]
    PUBLIC.mkdir(parents=True, exist_ok=True)
    write_project_text(project_path('docs/integracion/titularidad', "AUDITORIA_TITULARIDAD.md"), "\n".join(text))


if __name__ == "__main__":
    from tesis_enasem.release_guard import block_legacy_export
    block_legacy_export()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reports-only',action='store_true',help='Regenera narrativa desde agregados sin repetir la auditoría')
    args=parser.parse_args()
    if args.reports_only:
        r=json.loads(read_project_text(project_path('docs/integracion/titularidad', 'resultados.json')))
        render_report(r)
    else:
        r = run()
    print(json.dumps({k:r[k] for k in ["version","N_registros","N_personas","resumen_rondas"]}, ensure_ascii=False, indent=2))
