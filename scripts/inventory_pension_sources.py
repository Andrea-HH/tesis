from tesis_enasem.project_paths import project_path, read_project_text, write_project_text
"""Inspección local de TODOS los .dta y del inventario de referencia, sin integración."""
from pathlib import Path
import json
import re

import pandas as pd

from tesis_enasem.source_inventory import discrepancy_count, inspect_stata, inspect_workbook, match_audit, same_wave_comparisons

ROOT = Path(__file__).resolve().parents[1]


def run_inventory(raw_dir: Path = project_path('', "data/raw")) -> dict:
    """Audita fuentes separadas y correspondencias efímeras; devuelve solo agregados."""
    sources, variables, frames, years = [], [], {}, {}
    for path in sorted(raw_dir.glob("*.dta")):
        meta, fields, data = inspect_stata(path)
        # Las cuatro fuentes sin sufijo se verificaron contra los esquemas K
        # 2001/2003 y el inventario; el año no se infiere del '(1)' del nombre.
        early = {"sect_k.dta": 2001, "sect_kimp_2.dta": 2001,
                 "sect_k (1).dta": 2003, "sect_kimp.dta": 2003}
        year = early.get(path.name)
        if year is None:
            suffixes = [m.group(1) for c in data if (m := re.search(r"_(01|03|12|15|18|21|24)$", c))]
            if suffixes and path.name != "simpleMHAS.dta":
                year = 2000 + int(pd.Series(suffixes).value_counts().index[0])
        meta["anio_nominal_verificado"] = year
        meta["anio_entrevista_efectiva"] = "No inferido: requiere calendario/archivo individual de entrevistas" if year else "a_o_ent por ronda en CP1"
        meta["evidencia_anio"] = "Esquema K55/56/58 de 2001 o K58/59/61 de 2003; inventario de referencia" if path.name in early else "Sufijos modales, etiquetas del año y esquema del proveedor" if year else "ronda=1..6, a_o_ent separado"
        meta["periodo_principal"] = year != 2024
        if "cunicah" in data and any(k in data for k in ["np", "codent01", "codent03"]):
            meta["unidad_fila"] = "Persona-ronda" if year else "Persona-ronda longitudinal"
        else:
            meta["unidad_fila"] = "Entrevista económica de hogar/subhogar; contiene montos propios, de cónyuge y compartidos"
        meta["equivalencias_claves_internas"] = [
            {"columnas": [a, b], "n_evaluadas": len(data),
             "n_diferentes": discrepancy_count(data[a], data[b])}
            for a, b in [("codent01", "ps3"), ("codent03", "ent2")]
            if a in data and b in data
        ]
        sources.append(meta); variables.extend(fields); frames[path.name] = data; years[path.name] = year
        print(f"Inspeccionado {path.name}: {len(data):,} filas, {len(data.columns)} variables", flush=True)
    base = frames["simpleMHAS.dta"]
    matches = []
    bridges = []
    for name, frame in frames.items():
        year = years[name]
        if name == "simpleMHAS.dta" or year == 2024: continue
        wave = [2001, 2003, 2012, 2015, 2018, 2021].index(year)+1
        target = base.loc[base.ronda == wave]
        if "np" in frame:
            keys = ["cunicah", "np"]
        elif "codent01" in frame:
            keys = ["cunicah", "codent01"]
        elif "codent03" in frame:
            keys = ["cunicah", "codent03"]
        elif f"subhog_{str(year)[-2:]}" in frame:
            keys = ["cunicah", f"subhog_{str(year)[-2:]}"]
        elif "cunicah" in frame and "acthog" in frame:
            keys = ["cunicah", "acthog"]
        else:
            matches.append({"archivo": name, "anio": year,
                            "estado": "Requiere puente unhhid con fuente individual 2001; no unión por cunicah solamente"})
            continue
        for universe, selected in [("Todas las modalidades", target), ("Directas 1/2", target.loc[target.tipent.isin([1, 2])])]:
            info = match_audit(selected, frame, keys)
            matches.append({"archivo": name, "anio": year, "universo": universe, **info,
                            "estado": "Diagnóstico de claves; no valida atribución de montos ni universo de pregunta"})
    # Los nombres acthog no garantizan la misma codificación entre productos.
    # Construir solo puentes de claves efímeros, no una base económica integrada.
    for year, individual, origin_names, household_key in [
        (2001, "sect_k_ind_2001.dta", ["sect_k.dta", "sect_kimp_2.dta"], ["unhhid"]),
        (2003, "sect_k_ind_2003.dta", ["sect_k (1).dta", "sect_kimp.dta"], ["cunicah", "acthog"]),
    ]:
        person_key = ["cunicah", f"codent{str(year)[-2:]}"]
        bridge_columns = list(dict.fromkeys(person_key+household_key))
        bridge = frames[individual][bridge_columns]
        if bridge.duplicated(person_key).any(): raise ValueError("Puente persona no único")
        selected = base.loc[base.ronda == (1 if year == 2001 else 2)]
        target = selected[person_key+["tipent"]].merge(bridge, on=person_key, how="left", validate="one_to_one", indicator=True)
        for name in origin_names:
            for universe, part in [("Todas las modalidades", target), ("Directas 1/2", target.loc[target.tipent.isin([1, 2])])]:
                info = match_audit(part, frames[name], household_key)
                bridges.append({"archivo": name, "puente": individual, "anio": year,
                                "claves_persona_puente": person_key, "universo": universe, **info})
    groups = {}
    for s in sources: groups.setdefault(s["sha256"], []).append(s["archivo"])
    books = [inspect_workbook(p) for p in sorted(raw_dir.glob("*Inventario*ENASEM*.xlsx"))]
    return {"fuentes": sources, "variables": variables, "correspondencias_simple": matches, "puentes_historicos": bridges,
            "comparaciones_misma_ronda": same_wave_comparisons(frames, years),
            "duplicados_binarios": [g for g in groups.values() if len(g)>1], "inventarios_referencia": books,
            "alcance": "Auditoría estructural sin EDA conjunto ni base integrada; 2024 por separado"}


if __name__ == "__main__":
    result = run_inventory()
    # El manifiesto público conserva nombres/huellas y códigos Fxx, no mediciones.
    # Regenerar el inventario completo localmente y recuperar sus identificadores
    # de fuente sin cambiar las claves ni los cálculos de run_inventory.
    canonical = project_path('diccionarios/inventario_fuentes.json')
    if canonical.exists():
        previous = json.loads(canonical.read_text())
        known = {row['archivo']: row for row in previous.get('fuentes', [])}
        for source in result['fuentes']:
            old = known.get(source['archivo'])
            if old:
                if old['sha256'] != source['sha256']:
                    raise ValueError('Versión distinta: revisar y documentar antes de integrar')
                for field in ['fuente_id', 'clave_preferida', 'unidad_fila']:
                    if field in old:
                        source[field] = old[field]
    write_project_text(canonical, json.dumps(result, ensure_ascii=False, indent=2, default=str)+'\n')
    out = project_path('', "reports/tables/pensiones_inventario.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    write_project_text(out, json.dumps(result, ensure_ascii=False, indent=2, default=str)+"\n", encoding="utf-8")
    print(f"Auditoría concluida: {len(result['fuentes'])} archivos, {len(result['variables'])} columnas fuente-variable.")
