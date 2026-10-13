"""Inventario exhaustivo de fuentes locales; exporta metadatos y conteos, nunca filas."""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
from itertools import combinations
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import pandas as pd
from pandas.io.stata import StataMissingValue


def missing_mask(series: pd.Series) -> pd.Series:
    """Reconoce perdidos Stata y cadenas vacías sin convertir desconocidos a cero."""
    return series.map(lambda x: isinstance(x, StataMissingValue) or pd.isna(x)
                      or (isinstance(x, str) and not x.strip()))


def key_audit(data: pd.DataFrame, keys: list[str]) -> dict:
    """Conteos de claves completas y duplicadas; no devuelve identificadores."""
    complete = ~pd.concat([missing_mask(data[k]) for k in keys], axis=1).any(axis=1)
    valid = data.loc[complete, keys]
    return {"claves": keys, "n_completas": int(complete.sum()),
            "n_incompletas": int((~complete).sum()), "n_unicas": len(valid.drop_duplicates()),
            "filas_duplicadas": int(valid.duplicated(keep=False).sum()),
            "exceso_duplicados": int(valid.duplicated().sum())}


def match_audit(left: pd.DataFrame, right: pd.DataFrame, keys: list[str]) -> dict:
    """Prueba de correspondencia por conjuntos y cardinalidad, sin base fusionada."""
    def valid(frame: pd.DataFrame) -> pd.DataFrame:
        good = ~pd.concat([missing_mask(frame[k]) for k in keys], axis=1).any(axis=1)
        return frame.loc[good, keys]
    l, r = valid(left), valid(right)
    lk, rk = set(map(tuple, l.to_numpy())), set(map(tuple, r.to_numpy()))
    matched = l.apply(lambda row: tuple(row) in rk, axis=1)
    return {"claves": keys, "n_izquierda": len(left), "n_derecha": len(right),
            "n_claves_comunes": len(lk & rk), "n_filas_izquierda_emparejadas": int(matched.sum()),
            "n_claves_solo_izquierda": len(lk-rk), "n_claves_solo_derecha": len(rk-lk),
            "n_claves_izquierda_incompletas": len(left)-len(l),
            "n_claves_derecha_incompletas": len(right)-len(r),
            "izquierda_unica": bool(not l.duplicated().any()), "derecha_unica": bool(not r.duplicated().any())}


def normalized_name(name: str) -> str:
    """Retira solo sufijo de ola: candidato léxico, jamás equivalencia semántica."""
    return re.sub(r"_(01|03|12|15|18|21|24)$", "", name.lower())


def discrepancy_count(left: pd.Series, right: pd.Series) -> int:
    """Compara valores alineados: 1 y 1.0 coinciden; los tags Stata se conservan."""
    if len(left) != len(right) or not left.index.equals(right.index):
        raise ValueError("Comparación requiere índices alineados")
    def token(value: object) -> tuple:
        if isinstance(value, StataMissingValue):
            return ("stata_missing", value.string)
        if pd.isna(value):
            return ("pandas_missing",)
        return ("string", value) if isinstance(value, str) else ("value", value)
    return sum(token(a) != token(b) for a, b in zip(left, right))


def inspect_stata(path: Path) -> tuple[dict, list[dict], pd.DataFrame]:
    """Lee cada archivo completo preservando códigos y etiquetas originales."""
    with pd.io.stata.StataReader(path, convert_categoricals=False, convert_missing=True) as reader:
        labels = reader.variable_labels()
        value_labels = reader.value_labels()
        # pandas no ofrece accessor público para la asociación variable-etiqueta.
        label_names = dict(zip(labels, reader._lbllist))
        data_label = reader.data_label
        data = reader.read()
    variables = []
    for name in data:
        s = data[name]
        miss = missing_mask(s)
        special = Counter(x.string for x in s[miss] if isinstance(x, StataMissingValue))
        variables.append({"archivo": path.name, "variable": name, "etiqueta": labels.get(name, ""),
                          "nombre_sin_sufijo": normalized_name(name), "dtype": str(s.dtype),
                          "n": len(s), "n_no_perdidos_stata": int((~miss).sum()),
                          "n_perdidos": int(miss.sum()), "pct_perdidos": round(100*miss.mean(), 3),
                          "perdidos_especiales": dict(special),
                          "etiquetas_valores": {str(k): v for k, v in value_labels.get(label_names[name], {}).items()},
                          "revision_semantica": "Pendiente: filtros, códigos numéricos NR/NS, unidad y periodo"})
    candidate_keys = [["cunicah", "np", "ronda"], ["cunicah", "np"], ["unhhid"],
                      ["cunicah", "acthog"], ["cunicah", "codent01"], ["cunicah", "codent03"],
                      ["cunicah", "ps3"], ["cunicah", "ent2"], ["cunicah"]]
    candidate_keys += [["cunicah", c] for c in data if re.fullmatch(r"subhog_\d{2}", c)]
    checks = [key_audit(data, keys) for keys in candidate_keys if all(k in data for k in keys)]
    content_hash = sha256(pd.util.hash_pandas_object(data.astype(str), index=False).values.tobytes()).hexdigest()
    meta = {"archivo": path.name, "sha256": sha256(path.read_bytes()).hexdigest(),
            "sha256_contenido_ordenado": content_hash, "n_registros": len(data),
            "n_variables": len(data.columns), "etiqueta_archivo": data_label,
            "claves_candidatas": checks, "columnas": list(data.columns)}
    return meta, variables, data


def inspect_workbook(path: Path) -> dict:
    """Extrae todas las hojas, valores y fórmulas del inventario sin modificarlo."""
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    relns = "{http://schemas.openxmlformats.org/package/2006/relationships}"
    with ZipFile(path) as z:
        strings = []
        if "xl/sharedStrings.xml" in z.namelist():
            strings = ["".join(t.itertext()) for t in ET.fromstring(z.read("xl/sharedStrings.xml"))]
        targets = {r.attrib["Id"]: r.attrib["Target"] for r in
                   ET.fromstring(z.read("xl/_rels/workbook.xml.rels")).findall(relns+"Relationship")}
        sheets = []
        for sheet in ET.fromstring(z.read("xl/workbook.xml")).find("s:sheets", ns):
            rid = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            target = targets[rid].lstrip("/")
            name = target if target.startswith("xl/") else "xl/"+target
            root = ET.fromstring(z.read(name))
            rows, formulas = [], []
            for row in root.findall(".//s:sheetData/s:row", ns):
                values = []
                for c in row.findall("s:c", ns):
                    v, f = c.find("s:v", ns), c.find("s:f", ns)
                    value = v.text if v is not None else "".join(c.find("s:is", ns).itertext()) if c.find("s:is", ns) is not None else ""
                    if c.get("t") == "s": value = strings[int(value)]
                    values.append({"celda": c.get("r"), "valor": value})
                    if f is not None: formulas.append({"celda": c.get("r"), "formula": f.text})
                rows.append(values)
            sheets.append({"hoja": sheet.get("name"), "filas": rows, "formulas": formulas})
    return {"archivo": path.name, "sha256": sha256(path.read_bytes()).hexdigest(), "hojas": sheets}


def same_wave_comparisons(frames: dict[str, pd.DataFrame], years: dict[str, int | None]) -> list[dict]:
    """Compara todas las parejas de fuente de la misma ola; no omite duplicados."""
    result = []
    for a, b in combinations(frames, 2):
        if years.get(a) is None or years.get(a) != years.get(b): continue
        left, right = frames[a], frames[b]
        common = sorted(set(left) & set(right))
        candidates = [["cunicah", "np"], ["unhhid"], ["cunicah", "acthog"],
                      ["cunicah", f"subhog_{str(years[a])[-2:]}"]]
        keys = next((k for k in candidates if all(c in common for c in k)), None)
        item = {"fuente_a": a, "fuente_b": b, "anio": years[a],
                "n_variables_mismo_nombre": len(common), "variables_mismo_nombre": common,
                "variables_equivalentes": "No inferidas por nombre"}
        if keys:
            item["correspondencia"] = match_audit(left, right, keys)
            if item["correspondencia"]["izquierda_unica"] and item["correspondencia"]["derecha_unica"]:
                # Solo comparación efímera validada; ningún contenido individual se devuelve.
                l = left.set_index(keys); r = right.set_index(keys)
                ix = l.index.intersection(r.index)
                unequal = {}
                for c in set(common)-set(keys):
                    unequal[c] = discrepancy_count(l.loc[ix, c], r.loc[ix, c])
                item["n_comparadas"] = len(ix)
                item["discrepancias_por_variable"] = unequal
        else: item["correspondencia"] = "Sin clave común validable sin puente"
        result.append(item)
    return result
