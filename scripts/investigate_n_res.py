"""Cotejos adicionales de n_res: documentos ES/EN, modalidad y unidad de fila."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text, read_project_bytes

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

import pandas as pd
import pymupdf

from tesis_enasem.independent_eda import strict_json
from tesis_enasem.source_inventory import missing_mask
from run_independent_eda import md_table

ROOT = Path(__file__).resolve().parents[1]
URLS = {"es": "https://www.mhasweb.org/Resources/DATA/Constructed_Imputed/simpleMHAS/ENASEMsimple_Documento_Descriptivo_y_Libro_de_Codigos.pdf",
        "en": "https://mhasweb.org/Resources/DATA/Constructed_Imputed/simpleMHAS/simpleMHAS_Descriptive_Document_%26_Codebook.pdf"}


def investigate(documents: dict[str, Path]) -> dict:
    """Diagnóstico agregado focalizado; ninguna clave se exporta ni se modifica."""
    payload = json.loads(read_project_text(project_path('', "reports/eda_independiente/simple_resultados.json")))
    item = next(r for r in payload["resultados"] if r["contrato"]["variable"] == "n_res")
    printed, provenance = {}, []
    pattern = re.compile(r"^\s*(2001|2003|2012|2015|2018|2021)\s*\|\s*([\d,]+)\s+([\d.]+)\s+([\d.]+)\s+(\d+)\s+(\d+)\s*$", re.M)
    for language, path in documents.items():
        doc = pymupdf.open(path)
        matches = [(i+1,p.get_text()) for i,p in enumerate(doc) if "n_res" in p.get_text() and "3.093549" in p.get_text()]
        assert len(matches) == 1
        page, text = matches[0]
        rows = [{"anio":int(y),"N":int(n.replace(",","")),"media":float(mu),"DE":float(sd),"min":int(lo),"max":int(hi)} for y,n,mu,sd,lo,hi in pattern.findall(text)]
        assert len(rows) == 6
        printed[language] = rows
        provenance.append({"idioma":language,"url":URLS[language],"sha256":sha256(read_project_bytes(path)).hexdigest(),"pagina_n_res":page,"fecha_consulta":"2026-10-12"})
    assert printed["es"] == printed["en"]
    source = project_path('', "data/raw/simpleMHAS.dta")
    assert sha256(read_project_bytes(source)).hexdigest() == payload["sha256"]
    # Cotejo nuevo de unidad hogar frente a persona-ronda, no repetición del EDA completo.
    columns = ["cunicah","ronda","n_res", *[f"subhog_{x}" for x in ["01","03","12","15","18","21"]]]
    data = pd.read_stata(source, columns=columns, convert_missing=True, convert_categoricals=False)
    checks = []
    for s, book, suffix in zip(item["resumen"], printed["es"], ["01","03","12","15","18","21"]):
        rows = data.loc[data.ronda.eq(s["ronda"])].copy()
        rows = rows.loc[~missing_mask(rows.n_res)]
        key = ["cunicah",f"subhog_{suffix}"]
        complete = ~rows[key].apply(missing_mask).any(axis=1)
        groups = rows.loc[complete].groupby(key, sort=False).n_res
        discordant = int(groups.nunique().gt(1).sum())
        # Solo si es constante dentro del hogar se calcula una media por hogares.
        hh_mean = float(groups.first().astype(float).mean()) if not discordant else None
        modes = [r for r in item["por_modalidad"] if r["anio"] == s["anio"] and r["N_valido"]]
        checks.append({"Ronda":s["anio"], "N libro":book["N"], "N v3":s["N_valido"],
                       "Media libro":book["media"], "Media v3":s["media"], "DE libro":book["DE"], "DE v3":s["DE"],
                       "Máx. libro":book["max"], "Máx. v3":s["max"],
                       "Mín. media por modalidad":min(r["media"] for r in modes),
                       "N hogares clave completa":int(groups.ngroups), "N claves hogar faltantes":int((~complete).sum()),
                       "N hogares con n_res discordante":discordant, "Media por hogar constante":hh_mean,
                       "N valores sobre máximo libro":int(rows.n_res.astype(float).gt(book["max"]).sum())})
    result = {"fuentes":provenance,"ES_EN_coinciden":True,"cotejos":checks,"causa":"No identificada con los materiales disponibles"}
    strict_json(result, project_path('', "docs/eda/n_res_investigacion.json"))
    report = ("# Investigación de n_res: libro v2 y base v3\n\n**Resultado comprobado:** hay discrepancias en 2003, 2012, 2015 y 2018; la causa permanece sin identificar. No se modificó ningún registro.\n\n"
              "## Definición y trazabilidad\n\nEl libro define número de residentes en el hogar y atribuye la variable a ENASEM Armonizado en 2001–2018 y a ENASEMsimple en 2021 (versión española, p. 4). "
              "Los libros oficiales públicos español (p. 19) e inglés (p. 17), consultados el 12 de octubre de 2026, reproducen exactamente los mismos seis N, medias, DE y extremos. "
              "Esto descarta una discrepancia exclusiva de traducción entre estos documentos, pero no valida sus cifras contra la versión 3.\n\n"
              + md_table(provenance) + "\n## Contrastes numéricos\n\n" + md_table(checks) + "\n"
              "Los N coinciden con los valores válidos de v3 en las seis rondas. En las cuatro discrepantes cambian media y DE, y el máximo v3 supera el máximo impreso: no es un problema limitado al redondeo de la media. "
              "2001 y 2021 coinciden dentro de la precisión impresa; esto no prueba equivalencia registro por registro.\n\n"
              "## Hipótesis sometidas a comprobación\n\n"
              "| Hipótesis | Verificación | Conclusión |\n| --- | --- | --- |\n"
              "| Redondeo de medias | Diferencias exceden tolerancia; DE y máximos distintos | Insuficiente para explicar el resultado |\n"
              "| Traducción ES/EN | Seis cuadros exactamente iguales | No explica la discrepancia entre estos libros y v3 |\n"
              "| Restricción a modalidad directa/nueva/seguimiento/sustituto | En cada ronda discrepante todas las medias de modalidades con valores válidos superan la media impresa | Ninguna modalidad ni mezcla convexa de sus medias reproduce el libro |\n"
              "| Diferencia hogar/persona | Se verificó constancia intrahogar, claves faltantes y media por hogar cuando procede | Diagnóstico agregado mostrado; no se presupone la unidad usada al construir v2 |\n"
              "| Cambio de definición/construcción o corrección de versión | No hay base v2 ni programa/changelog de construcción provisto para cotejo individual | Sigue siendo hipótesis, no causa comprobada |\n"
              "| Error del cuadro documental | Las dos traducciones comparten cifras; no se dispone de cálculo original | Posible, sin prueba suficiente |\n\n"
              "El contraste de hogar es exploratorio: no se selecciona un registro arbitrario cuando n_res difiere dentro de la clave. "
              "No se reconstruye una versión anterior restando integrantes ni truncando valores. Los valores superiores al máximo impreso son diferencias entre versiones, no errores individuales demostrados.\n\n"
              "## Verificaciones pendientes e implicación metodológica\n\nSe requiere el archivo v2 o su código de creación, la variable armonizada exacta y su versión, y una nota del proveedor que detalle cambios v2→v3. "
              "La etiqueta v3 y la procedencia armonizada no bastan para afirmar la causa. No se contactó al proveedor ni se divulgaron claves. "
              "Para reproducir este contraste: `python scripts/investigate_n_res.py --es RUTA_ES --en RUTA_EN`. "
              "B01 conserva las cifras de los microdatos suministrados y queda abierto este pendiente de validación; n_res no se usará para justificar cambios causales ni corregir población. "
              "Todos los resultados son sin ponderar; no se estima tamaño medio nacional de hogares.\n")
    write_project_text(project_path('', "docs/eda/N_RES_VERSIONES.md"), report)
    print(f"n_res: {len(checks)} cotejos; ES/EN iguales; causa abierta.")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--es", required=True, type=Path)
    parser.add_argument("--en", required=True, type=Path)
    args = parser.parse_args()
    investigate({"es":args.es,"en":args.en})
