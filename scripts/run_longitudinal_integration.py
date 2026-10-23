"""Construye la base provisional privada y evidencia agregada; conserva 99,676 filas."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text, read_project_bytes

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from tesis_enasem.integration import (YEARS, MISSING_CODES, encode_stata, economic_link, left_indexer,
                                     pension_2021_record, person_id, response_number, take_nullable)

ROOT = Path(__file__).resolve().parents[1]
OUT = project_path('', "data/processed/enasem_integrada_provisional.parquet")
DOCS = project_path('', "docs/integracion")
MODES = {1: "Directa seguimiento", 2: "Directa incorporación", 3: "Sustituto seguimiento",
         4: "Sustituto incorporación", 5: "Sobre fallecido"}


def write_json(path: Path, value: object) -> None:
    """Serializa agregados sin NaN ni identificadores individuales."""
    path.parent.mkdir(parents=True, exist_ok=True)
    write_project_text(path, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def read_source(source: dict) -> tuple[pd.DataFrame, dict]:
    """Verifica huella inventariada antes de leer; captura formatos Stata originales."""
    path = project_path('', "data/raw", source["archivo"])
    if sha256(read_project_bytes(path)).hexdigest() != source["sha256"]:
        raise ValueError(f"La fuente {source['fuente_id']} cambió respecto al inventario")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", pd.errors.PerformanceWarning)
        with pd.io.stata.StataReader(path, convert_missing=True, convert_categoricals=False) as reader:
            formats = dict(zip(reader.variable_labels(), reader._fmtlist))
            frame = reader.read()
    if len(frame) != source["n_registros"] or len(frame.columns) != source["n_variables"]:
        raise ValueError("Dimensiones distintas del inventario")
    return frame, formats


def source_kind(source: dict) -> str:
    """Versiones separadas por producto, sin inferir independencia de ingresos."""
    name = source["archivo"].lower()
    return "imputada_hogar" if "imput" in name or "kimp" in name else "construida_individual" if "_ind_" in name else "original_hogar"


def owner_diagnostics(individual: pd.DataFrame, household: pd.DataFrame) -> list[dict]:
    """Cotejo agregado de punteros 2021 en claves económicas, sin publicar NP."""
    ix, _, _ = left_indexer(individual, household, ["cunicah", "subhog_21"])
    checks = []
    for name in ["k45d_21", "k52a_1_21", "k52a_21"]:
        pairs = [(response_number(individual.iloc[i][name]), response_number(household.iloc[j][name]))
                 for i,j in enumerate(ix) if j >= 0]
        complete = [(a,b) for a,b in pairs if a is not None and b is not None]
        checks.append({"campo": name, "N_personas_enlazadas_ambas_fuentes": len(pairs),
                       "N_pares_valores_disponibles": len(complete), "N_discrepantes": sum(a != b for a,b in complete)})
    return checks


def append_values(arrays: list, names: list, dictionary: list, frame: pd.DataFrame,
                  source: dict, formats: dict, metadata: dict, indexer: np.ndarray | None) -> dict:
    """Añade todas las columnas; la cardinalidad se controla antes del take."""
    counts = {"columnas_originales": 0, "columnas_tags": 0, "valores_stata_faltantes_fuente": 0}
    for name in frame:
        full_name = name if source["fuente_id"] == "F20" else f"{source['fuente_id']}__{name}"
        if full_name in names:
            raise ValueError("Colisión de nombres de columnas")
        values, tags, profile = encode_stata(frame[name])
        arrays.append(values if indexer is None else take_nullable(values, indexer)); names.append(full_name)
        info = metadata[(source["archivo"], name)]
        dictionary.append({"columna": full_name, "fuente_id": source["fuente_id"], "archivo": source["archivo"],
                           "variable_original": name, "version": source["etiqueta_archivo"],
                           "producto": "maestra_ENASEMsimple" if source["fuente_id"] == "F20" else source_kind(source),
                           "unidad_fuente": source["unidad_fila"], "ano": source["anio_nominal_verificado"],
                           "formato_stata": formats[name], "dtype_original": str(frame[name].dtype),
                           "etiqueta": info["etiqueta"], "etiquetas_valores": info["etiquetas_valores"],
                           "perfil_tags_fuente": profile, "campo_tag": None,
                           "titularidad": "Preservada del proveedor; no implica ingreso propio por enlazar",
                           "homologacion": "Conservada sin recodificar; consultar contratos EDA y especificaciones de ocho conceptos"})
        counts["columnas_originales"] += 1
        missing = sum(v for k, v in profile.items() if k != MISSING_CODES[0])
        counts["valores_stata_faltantes_fuente"] += sum(v for k, v in profile.items() if k.startswith("."))
        if missing:
            tag_name = full_name + "__stata_tag"
            if tag_name in names or tag_name in frame.columns:
                raise ValueError("Colisión con columna de tag")
            dictionary[-1]["campo_tag"] = tag_name
            arrays.append(tags if indexer is None else take_nullable(tags, indexer)); names.append(tag_name)
            dictionary.append({"columna": tag_name, "fuente_id": source["fuente_id"], "variable_original": name,
                               "producto": "auxiliar_faltante", "codigos": MISSING_CODES,
                               "semantica": "Tag del archivo. Null fuera de ronda/sin enlace; consulte estado de fuente."})
            counts["columnas_tags"] += 1
    return counts


def run() -> dict:
    """Ejecuta uniones secuenciales, escribe Parquet y valida todas las columnas al releer."""
    inventory = json.loads(read_project_text(project_path('', "docs/pensiones/inventario_fuentes.json")))
    sources = {s["fuente_id"]: s for s in inventory["fuentes"]}
    for source in sources.values():
        if sha256(read_project_bytes(project_path('', "data/raw", source["archivo"]))).hexdigest() != source["sha256"]:
            raise ValueError("Una fuente cambió respecto al inventario; revisar antes de integrar")
    if sources["F04"]["sha256"] != sources["F05"]["sha256"]:
        raise ValueError("Las copias 2018 dejaron de ser idénticas: no omitir una versión distinta")
    metas = {(m["archivo"], m["variable"]): m for m in inventory["variables"]}
    master, master_formats = read_source(sources["F20"])
    ids = person_id(master)
    if len(master) != 99676 or pd.DataFrame({"id": ids, "ronda": master.ronda}).duplicated().any():
        raise ValueError("El maestro no cumple 99,676 filas / unicidad persona-ronda")
    if set(master.ronda) != set(range(1, 7)):
        raise ValueError("Rondas inesperadas")
    arrays, names, dictionary = [], [], []
    master_counts = append_values(arrays, names, dictionary, master, sources["F20"], master_formats, metas, None)
    arrays.extend([pa.array(ids), pa.array(master.ronda.map(dict(enumerate(YEARS, 1))), type=pa.int16())])
    names.extend(["id", "ano"])
    dictionary.extend([{"columna": "id", "producto": "clave_derivada", "formula": "cunicah:np",
                        "formato": "Texto preservado; números enteros sin relleno ni notación científica. Separador ':' reservado."},
                       {"columna": "ano", "producto": "calendario_nominal", "codigos": dict(enumerate(YEARS, 1)),
                        "semantica": "Año de onda, no a_o_ent"}])
    # Los puentes nunca modifican np/cunicah originales del maestro.
    bridges = {year: read_source(sources[fid])[0] for year, fid in [(2001, "F13"), (2003, "F14")]}
    cache_2021 = {}
    coverage, links, reconciliations = [], {}, []
    for fid, source in sources.items():
        if fid in ("F20", "F05", "F06"):
            continue
        year = source["anio_nominal_verificado"]
        wave = YEARS.index(year) + 1
        rows = np.flatnonzero(master.ronda.eq(wave))
        target = master.iloc[rows]
        frame, formats = read_source(source)
        keys = source["clave_preferida"]
        individual = source_kind(source) == "construida_individual"
        bridge_name = None
        if not individual and year in (2001, 2003):
            bridge_name = "F13" if year == 2001 else "F14"
        step = economic_link(master, frame, year, keys, individual, bridges.get(year))
        ix, full_ix, audit, states = step["indexer"], step["full_indexer"], step["audit"], step["states"]
        links[fid] = full_ix
        status = np.full(len(master), "fuera_ronda_fuente", dtype=object)
        status[rows] = states
        counts = append_values(arrays, names, dictionary, frame, source, formats, metas, full_ix)
        for name, values, semantic in [(f"{fid}__enlace", pa.array(status).dictionary_encode(), "Estado de LEFT JOIN por fuente"),
                                       (f"{fid}__disponible_en_ronda", pa.array(master.ronda.eq(wave)), "Fuente físicamente disponible en año nominal; no asegura enlace ni respuesta")]:
            arrays.append(values); names.append(name)
            dictionary.append({"columna": name, "fuente_id": fid, "producto": "control_enlace", "semantica": semantic})
        partitions = [("Todas", np.ones(len(target), dtype=bool)), ("Directas 1/2", target.tipent.isin([1,2]).to_numpy())]
        partitions += [(MODES[m], target.tipent.eq(m).to_numpy()) for m in MODES]
        for label, mask in partitions:
            n = int(mask.sum()); n_match = int(((ix >= 0) & mask).sum())
            item = {"fuente": fid, "archivo": source["archivo"], "ano": year, "ronda": wave,
                    "modalidad": label, "N_maestro_ronda_modalidad": n, "N_enlazadas": n_match,
                    "N_sin_enlace": n-n_match, "pct_enlace": 100*n_match/n if n else None,
                    "motivos_sin_enlace": dict(Counter(states[mask & (ix < 0)]))}
            coverage.append(item)
            if label in ("Todas", "Directas 1/2"):
                collection = inventory["puentes_historicos"] if bridge_name else inventory["correspondencias_simple"]
                old = next(a for a in collection if a["archivo"] == source["archivo"] and a.get("universo") ==
                           ("Todas las modalidades" if label == "Todas" else label))
                expected = old["n_filas_izquierda_emparejadas"]
                reconciliations.append({"fuente": fid, "universo": label, "anterior": expected,
                                        "actual": n_match, "coincide": expected == n_match})
                if expected != n_match:
                    raise ValueError(f"Cobertura distinta del inventario: {fid} / {label}")
        if fid in ("F10", "F17"):
            cache_2021[fid] = frame
        print(f"{fid} {year}: {audit['n_enlazadas']:,}/{len(target):,}; {counts['columnas_originales']} columnas; {audit['cardinalidad']}", flush=True)
        source["integracion"] = {**audit, **counts, "puente": bridge_name, "claves": keys}
        del frame
    # Derivación limitada y explícita: instrumentos 2021 ya cotejados. No 0 fuera de 2021.
    f17, f10 = cache_2021["F17"].to_dict("records"), cache_2021["F10"].to_dict("records")
    derived = []
    for row, (np_value, mode, wave) in enumerate(zip(master.np, master.tipent, master.ronda)):
        a, b = links["F17"][row], links["F10"][row]
        item = pension_2021_record(np_value, int(mode), f17[a] if a >= 0 else None, f10[b] if b >= 0 else None)
        if wave != 6:
            item["econ_titular_estado"] = "homologacion_titularidad_otra_ronda_pendiente"
        derived.append(item)
    fields = list(derived[0])
    for name in fields:
        vals = [d[name] for d in derived]
        array_type = (pa.string() if "estado" in name or "fuentes" in name else pa.float64() if "monto" in name
                      else pa.int16() if "num_" in name else pa.bool_())
        arrays.append(pa.array(vals, type=array_type)); names.append(name)
        dictionary.append({"columna": name, "producto": "derivada_provisional_2021", "fuentes": ["F10", "F17"],
                           "validacion": "Orientación key_21, NP del titular coincidente en ambas fuentes, rama de pareja, modalidad no fallecido",
                           "referencias": ["Cuestionario básico ENASEM 2021, PDF pp.63–68", "Imputación económica 2021, orientación de titular"],
                           "limites": "Solo 2021; originales, sin sumar imputados/construidos. Fuentes JSON multivaluadas. Número mínimo y monto parcial, no total. Otra ronda=NA, no cero."})
    metadata = {"version": "provisional-1", "master_sha256": sources["F20"]["sha256"],
                "missing_codes": MISSING_CODES, "primary_key": ["id", "ronda"],
                "household_columns": "Contexto económico de hogar, nunca ingreso individual por mero enlace",
                "dictionary": "docs/integracion/diccionario_columnas.json"}
    table = pa.Table.from_arrays(arrays, names=names).replace_schema_metadata({b"tesis": json.dumps(metadata).encode()})
    if table.num_rows != 99676 or len(names) != len(set(names)):
        raise ValueError("Filas o columnas inconsistentes")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    temp = OUT.with_suffix(".parquet.tmp")
    pq.write_table(table, temp, compression="zstd", row_group_size=20000)
    persisted = pq.ParquetFile(temp)
    offset = 0
    for i in range(persisted.num_row_groups):
        chunk = persisted.read_row_group(i)
        if not chunk.equals(table.slice(offset, len(chunk)), check_metadata=False):
            raise ValueError("Valores o tags cambiaron en round-trip Parquet")
        offset += len(chunk)
        del chunk
    if offset != len(master):
        raise ValueError("Round-trip incompleto")
    temp.replace(OUT)
    output_sha = sha256(read_project_bytes(OUT)).hexdigest()
    ownership = dict(Counter(d["econ_titular_estado"] for d, wave in zip(derived, master.ronda) if wave == 6))
    audit = {"fecha": "2026-10-12", "estado": "Integración provisional ejecutada; homologación parcial, sin aceptación de muestra",
             "rama": "feat/cp1-auditoria", "N_registros": len(master), "N_personas": int(ids.nunique()),
             "N_variables_maestro": len(master.columns), "N_columnas_finales": len(names),
             "N_columnas_fuente_conservadas": sum(s["n_variables"] for fid,s in sources.items() if fid not in ("F05","F06")),
             "N_fuentes_economicas_integradas": len(links), "duplicados_id_ronda": 0, "multiplicacion_registros": 0,
             "N_hashes_fuente_verificados": len(sources),
             "exclusiones_maestro": 0, "N_rondas": 6, "preservacion_maestro": master_counts,
             "roundtrip_todas_columnas": True, "hash_parquet": output_sha, "bytes_parquet": OUT.stat().st_size,
             "archivo_privado": str(OUT.relative_to(ROOT)), "fuentes": list(sources.values()),
             "excluidas": [{"fuente": "F05", "motivo": "Copia binaria idéntica F04; todas las columnas retenidas una sola vez", "equivalente_integrada": "F04"},
                            {"fuente": "F06", "motivo": "2024 inventariado separado, fuera de las seis rondas"}],
             "reconciliacion_inventario": reconciliations, "cobertura": coverage,
             "cotejo_punteros_2021": owner_diagnostics(cache_2021["F17"], cache_2021["F10"]),
             "titularidad_2021": ownership,
             "pension_2021": {name: dict(Counter(str(d[name]) for d,w in zip(derived,master.ronda) if w == 6)) for name in
                              ["pension_recibe_k_2021", "pension_contributiva_evidencia_2021", "apoyo_vejez_evidencia_2021", "apoyo_publico_recibe_2021"]},
             "registros_por_ronda": [{"ronda": w, "ano": year, "N_registros": int(master.ronda.eq(w).sum()),
                                       "N_personas": int(ids.loc[master.ronda.eq(w)].nunique())} for w, year in enumerate(YEARS, 1)]}
    write_json(project_path('docs/integracion', "validacion.json"), audit)
    write_json(project_path('docs/integracion', "diccionario_columnas.json"), dictionary)
    write_json(OUT.with_suffix(".manifest.json"), {**metadata, "N_registros": len(master), "N_columnas": len(names), "sha256": output_sha})
    export_reports(audit, dictionary)
    return audit


def md_table(rows: list[dict], columns: list[str]) -> str:
    """Tabla pública de agregados; entradas restringidas por esquema."""
    def cell(value: object, column: str) -> str:
        if value is None:
            return "ND"
        if isinstance(value, float):
            return f"{value:.3f}" if "rho" in column else f"{value:,.2f}"
        return str(value).replace("|", "/")
    return "| " + " | ".join(columns) + " |\n| " + " | ".join("---" for _ in columns) + " |\n" + "\n".join(
        "| " + " | ".join(cell(row.get(c),c) for c in columns) + " |" for row in rows) + "\n"


def export_reports(audit: dict, dictionary: list) -> None:
    """Publica únicamente evidencia agregada; diccionario sin valores de personas."""
    counts = [x for x in audit["cobertura"] if x["modalidad"] == "Todas"]
    allcols = ["fuente", "ano", "N_maestro_ronda_modalidad", "N_enlazadas", "N_sin_enlace", "pct_enlace"]
    write_project_text(DOCS.joinpath("COBERTURA.md"), "# Cobertura de integración provisional\n\nSin filtros: personas-ronda, N de ENASEMsimple por ronda y modalidad; porcentaje = enlazadas / N maestro. El enlace no valida elegibilidad ni titularidad de cada pregunta.\n\n" +
        md_table(counts, allcols) + "\n## Desglose completo por modalidad\n\n" + md_table(audit["cobertura"], ["fuente", "ano", "modalidad", *allcols[2:]]) +
        "\nLos motivos de no enlace y filas fuente no utilizadas se consultan en validacion.json. No enlazado nunca equivale a ingreso cero.\n")
    write_project_text(DOCS.joinpath("VALIDACION.md"), "# Validación de base provisional\n\n" +
        f"**{audit['N_registros']:,} registros, {audit['N_personas']:,} personas, {audit['N_columnas_finales']:,} columnas.** " +
        "Cero exclusiones, cero duplicados id+ronda y cero multiplicación de filas. Todas las 119 columnas del maestro se conservan, con tags Stata separados cuando corresponde. " +
        f"Se integraron {audit['N_fuentes_economicas_integradas']} fuentes económicas distintas y se conservaron {audit['N_columnas_fuente_conservadas']:,} columnas fuente, incluyendo la maestra.\n\n" +
        md_table(audit["registros_por_ronda"], ["ronda","ano","N_registros","N_personas"]) +
        "\n## Cardinalidad y reconciliación\n\nLas fuentes personales son one-to-one dentro de ronda; las de hogar many-to-one. Se rechazan claves derechas duplicadas; faltantes no se emparejan. " +
        "2001 usa F13→unhhid; 2003 F14→cunicah+acthog económico. No se usa acthog del maestro en 2003. " +
        "2012/2015/2018/2021 usan cunicah+subhog específico. Las 34 pruebas de cobertura coinciden exactamente con el inventario, incluyendo pérdidas documentadas.\n\n" +
        md_table(audit["reconciliacion_inventario"], ["fuente","universo","anterior","actual","coincide"]) +
        "\n## Conservación y privacidad\n\nCada archivo coincide por SHA-256, filas y columnas con el inventario. Todas las columnas, incluidas banderas y códigos numéricos desconocidos/no aplicables, se codifican sin recodificación semántica. " +
        "Se comprobó igualdad de **todas las columnas y filas**, incluidos tags, al releer los cinco grupos Parquet. Los tags originales se conservan; null por no enlace se interpreta con Fxx__enlace. " +
        "Cadenas vacías se conservan y se marcan. No se suman columnas originales/imputadas/construidas. No se deriva ingreso_total ni se corrigen anomalías CP1. " +
        "F05 equivale byte a byte a F04; su información se conserva una vez. F06/2024 permanece inventariado separado.\n\n" +
        "El Parquet y su manifiesto están ignorados en data/processed. Ningún reporte contiene identificadores individuales.\n\n" +
        "## Titularidad 2021\n\nLa derivación exige coincidencia del NP en el individual y el hogar, orientación key_21 y rama de pareja válida. La derivación de pensiones se apoya también en orientación del proveedor; el puntero K45d por sí solo no enumera el bloque K58. " +
        "Los casos discrepantes quedan desconocidos; los registros sobre fallecido se conservan pero no acreditan recepción actual. Los montos de hogar siguen siendo contexto del informante/pareja, sin dividirse ni adjudicarse por mero enlace.\n\n" +
        md_table([{"estado": k,"N_registros": v} for k,v in audit["titularidad_2021"].items()], ["estado","N_registros"]) +
        "\nCotejo adicional de las 15,716 filas individuales con hogar disponible (no 15,716 hogares independientes):\n\n" +
        md_table(audit["cotejo_punteros_2021"],["campo","N_personas_enlazadas_ambas_fuentes","N_pares_valores_disponibles","N_discrepantes"]) +
        "\nEl criterio conservador no garantiza validación sustantiva de todas las columnas: la integración estructural y la homologación tienen estados separados.\n")
    rows = [{"columna": d["columna"], "fuente": d.get("fuente_id", "derivada"), "original": d.get("variable_original", "—"),
             "producto": d["producto"], "tag": d.get("campo_tag") or "—"} for d in dictionary]
    write_project_text(DOCS.joinpath("DICCIONARIO_COLUMNAS.md"), "# Diccionario completo de columnas integradas\n\n"
        "Metadatos íntegros (etiquetas/códigos/formatos/fuente/unidad/titularidad/tags) en diccionario_columnas.json. Fxx__ identifica producto y procedencia; nombres originales de ENASEMsimple se conservan. "
        "Los valores de códigos se describen, pero no se publican claves individuales ni filas.\n\n" + md_table(rows,["columna","fuente","original","producto","tag"]))


if __name__ == "__main__":
    from tesis_enasem.release_guard import block_legacy_export
    block_legacy_export()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports-only", action="store_true", help="Reexporta desde validación calculada sin repetir uniones")
    args = parser.parse_args()
    if args.reports_only:
        export_reports(json.loads(read_project_text(project_path('docs/integracion', "validacion.json"))), json.loads(read_project_text(project_path('docs/integracion', "diccionario_columnas.json"))))
    else:
        result = run()
        print(f"Validada: {result['N_registros']:,} filas; {result['N_columnas_finales']:,} columnas; {OUT}")
