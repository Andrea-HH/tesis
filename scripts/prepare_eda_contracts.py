"""Construye contratos ENASEMsimple desde libro de códigos y metadatos auditados."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text, read_project_bytes

import argparse
from hashlib import sha256
from pathlib import Path
import re

import pymupdf
import json

from tesis_enasem.independent_eda import VariableSpec, simple_role, strict_json

ROOT = Path(__file__).resolve().parents[1]


def prepare(codebook: Path) -> list[dict]:
    """Extrae etiquetas/localizadores; las reglas sustantivas siguientes son explícitas."""
    doc = pymupdf.open(codebook)
    text = "\n".join(f"\nPÁGINA {i+1}\n" + page.get_text() for i, page in enumerate(doc))
    starts = list(re.finditer(r"(?m)^([a-zA-Z][a-zA-Z0-9_]*)\s+in en:", text))
    blocks = {m.group(1): text[m.start(): starts[i+1].start() if i+1 < len(starts) else len(text)]
              for i, m in enumerate(starts)}
    sorted_text = "\n".join(page.get_text(sort=True) for page in doc)
    sorted_starts = list(re.finditer(r"(?m)^([a-zA-Z][a-zA-Z0-9_]*)\s+in en:", sorted_text))
    sorted_blocks = {m.group(1): sorted_text[m.start(): sorted_starts[i+1].start() if i+1 < len(sorted_starts) else len(sorted_text)]
                     for i, m in enumerate(sorted_starts)}
    # Estadísticos impresos del proveedor para cotejo, jamás sustituyen el cálculo.
    provider_statistics = []
    for name, block in sorted_blocks.items():
        if "Obs" not in block or "Mean" not in block:
            continue
        for m in re.finditer(r"(?m)^\s*(2001|2003|2012|2015|2018|2021)\s*\|\s*([\d,]+)\s+([-\d.eE]+)\s+([-\d.eE]+)\s+([-\d.eE]+)\s+([-\d.eE]+)\s*$", block):
            year, n, mean, std, low, high = m.groups()
            provider_statistics.append({"variable": name, "anio": int(year), "N_libro": int(n.replace(",", "")),
                                        "media_libro": float(mean), "DE_libro": float(std),
                                        "min_libro": float(low), "max_libro": float(high)})
    inventory = json.loads(read_project_text(project_path('', "docs/pensiones/inventario_fuentes.json")))
    fields = [v for v in inventory["variables"] if v["archivo"] == "simpleMHAS.dta"]
    bounds = {"mes_nac": (1, 12), "n_suj_hog": (1, 2), "n_enf": (0, 7),
              "n_sint_depr": (0, 9), "n_abvd_wh": (0, 3), "n_abvd": (0, 5),
              "n_aivd": (0, 4), "n_mov": (0, 5), "n_img": (0, 4),
              "motoras_gruesas": (0, 5), "motoras_finas": (0, 3),
              "recuerdo1": (0, 8), "recuerdo2": (0, 8), "copiafiguras1": (0, 2),
              "copiafiguras2": (0, 2), "visualscan": (0, 60), "orientacion": (0, 3),
              "serial7": (0, 5)}
    # No se imponen máximos observados como límites de validez ni umbrales clínicos.
    nonnegative = {"edad", "educacion", "n_res", "hermanos_vivos", "n_hijos_vivos", "nietos"}
    score = set(bounds) - {"mes_nac", "n_suj_hog"}
    spanish_codes = {
        "sexo": {"1": "Hombre", "2": "Mujer"},
        "edad_gru": {"0": "49 o menos", "1": "50–59", "2": "60–69", "3": "70–79", "4": "80 o más"},
        "urbano": {"0": "Localidad con menos de 100 000 habitantes", "1": "Localidad con 100 000 o más habitantes"},
        "edu_gru": {"0": "Sin educación", "1": "1–5 años", "2": "6 años", "3": "7–9 años", "4": "10 o más años"},
        "est_conyugal": {"1": "Casado o unión libre", "2": "Separado o divorciado", "3": "Viudo", "4": "Nunca casado ni unido"},
        "hijos_vivos_gru": {"0": "Sin hijos", "1": "1–2", "2": "3–4", "3": "5–6", "4": "7 o más"},
        "salud_glob": {"1": "Excelente", "2": "Muy buena", "3": "Buena", "4": "Regular", "5": "Mala"},
        "memoria": {"1": "Excelente", "2": "Muy buena", "3": "Buena", "4": "Regular", "5": "Mala"},
        "enf_cat": {"0": "Ninguna", "1": "Una", "2": "Dos o más"},
        "ocupacion": {"1": "Trabaja", "2": "Busca trabajo", "3": "Labores del hogar", "4": "Retirado, incapacitado o no trabaja"},
        "autoem": {"1": "Empleado", "2": "Autoempleado"},
        "imc_imp_cat": {"1": "Bajo peso", "2": "Normal", "3": "Sobrepeso", "4": "Obesidad", "5": "Obesidad mórbida"},
    }
    contracts = []
    for v in fields:
        name = v["variable"]
        if simple_role(name).startswith("técnica"):
            continue
        if name not in blocks:
            raise ValueError(f"Sin sección individual en libro: {name}")
        block = blocks[name]
        label_match = re.search(r"in es:\s*([^\n]+)", block)
        if not label_match:
            raise ValueError(f"Sin etiqueta española: {name}")
        label = label_match.group(1).strip()
        pos = next(m.start() for m in starts if m.group(1) == name)
        page = int(re.findall(r"PÁGINA (\d+)", text[:pos])[-1])
        codes = v["etiquetas_valores"]
        if set(codes) == {"0", "1"}:
            codes = {"0": "No imputado", "1": "Imputado"} if name.endswith("_flag") or name == "bmi_flag" else {"0": "No", "1": "Sí"}
        codes = spanish_codes.get(name, codes)
        if name in {"abvd_gru", "aivd_gru"}:
            codes = {"0": "Ninguna", "1": "Una", "2": "Dos", "3": "Tres o más"}
        categorical = bool(codes)
        unit = "categoría codificada" if categorical else "conteo"
        if name in {"edad", "educacion"}:
            unit = "años cumplidos" if name == "edad" else "años de escolaridad en primera entrevista"
        if name == "mes_nac": unit = "mes calendario"
        if name == "a_o_nac": unit = "año calendario de nacimiento"
        if name in score: unit = "puntuación/conteo según escala del libro"
        if name == "horas_trabajadas": unit = "horas por semana"
        if name == "bmi_imp": unit = "kg/m², promedio de diez imputaciones"
        if name == "imp_neto": unit = "unidades monetarias almacenadas; precios y comparabilidad real pendientes"
        lower, upper = bounds.get(name, (None, None))
        if name in nonnegative: lower = 0
        note = ("Descriptivos entre valores disponibles. Los tags .s/.p/.f/.w identifican saltos, modalidad, "
                "fallecimiento y ausencia de instrumento; no permiten reconstruir por sí solos todo el universo elegible. "
                "N elegible no reconstruido; no se usa N válido como sustituto.")
        temporal = "Composición observada por ronda; no cambio individual, causal ni representativo sin pesos."
        interpretation = "La distribución caracteriza los registros con información; su cobertura y modalidad condicionan la interpretación longitudinal."
        if name in {"educacion", "edu_gru"}:
            temporal += " Escolaridad de primera entrevista: cambios de composición, no adquisición posterior de educación."
            interpretation += " La escolaridad aproxima recursos formativos; no mide ingreso ni identifica causalidad."
        if name in {"ocupacion", "autoem", "horas_trabajadas"}:
            interpretation = "Caracteriza inserción laboral observada; la categoría 4 de ocupacion reúne retiro, incapacidad y ausencia de trabajo y no identifica pensionados."
        if name in {"autoem", "horas_trabajadas"}:
            note += " Variable condicional al trabajo; rama exacta del cuestionario y diferencias de cobertura pendientes. No calcular prevalencia en toda la población."
            temporal += " Comparación condicionada a cobertura laboral y filtro todavía incompleto."
        if name == "imp_neto":
            note += " Titular: entrevistado y cónyuge si existe; no es ingreso individual. No sumar por hogar."
            interpretation = "La mediana y los cuantiles describen asimetría patrimonial. Ceros y negativos se conservan; no se atribuyen a falta de pensión."
            temporal = "Solo distribuciones dentro de ronda, sin crecimiento real ni prueba temporal de montos; validar moneda, titularidad e inflación antes de comparación económica."
        if name in {"bmi_imp", "imc_imp_cat", "bmi_flag"}:
            interpretation = "Indicador construido de estado corporal e imputación, no diagnóstico clínico; el promedio de imputaciones no preserva incertidumbre entre imputaciones."
        if name in score or name.endswith("_flag"):
            interpretation += " Las puntuaciones y banderas construidas deben distinguirse de preguntas originales y de un diagnóstico clínico."
        if name in {"feliz", "disf_vida", "energia"}:
            interpretation += " Sí es una respuesta positiva a este ítem; no equivale a un síntoma depresivo sin inversión explícita en el índice."
        imputed_scores = {"recuerdo1", "recuerdo2", "copiafiguras1", "copiafiguras2", "visualscan", "orientacion", "serial7"}
        spec = VariableSpec(name, label, "categorical" if categorical else "numeric", unit, codes, {},
                            lower, upper, not categorical and name not in {"bmi_imp", "imp_neto", *imputed_scores},
                            note, "ENASEMsimple, Documento del proyecto y libro de códigos, v2 enero 2025; datos v3 enero 2025", page,
                            temporal, interpretation)
        contracts.append(spec.__dict__)
    assert len(contracts) == 91, f"Cobertura inesperada: {len(contracts)}"
    strict_json({"fecha": "2026-10-12", "sha256_libro": sha256(read_project_bytes(codebook)).hexdigest(),
                 "archivo_libro": codebook.name, "n_paginas": len(doc),
                 "advertencia_version": "Libro v2 frente a etiqueta del archivo v3; diferencias deben verificarse, no corregirse automáticamente.",
                 "validacion": "Códigos/etiquetas, escalas, unidades y tags cotejados con secciones individuales. Universos condicionales no reconstruidos.",
                 "estadisticos_impresos_proveedor": provider_statistics,
                 "contratos": contracts}, project_path('', "docs/eda/contratos_simple.json"))
    print(f"Contratos: {len(contracts)}; claves/diseño/pesos: {len(fields)-len(contracts)}")
    return contracts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codebook", type=Path, required=True, help="PDF local del proveedor (no se copia ni publica).")
    prepare(parser.parse_args().codebook)
