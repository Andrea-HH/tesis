"""Congela fuentes públicas oficiales07; no descarga ni modifica microdatos."""

from __future__ import annotations

import csv
import io
import json
from hashlib import sha256
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

from tesis_enasem.economic_protection import save_json
from tesis_enasem.project_paths import INTERIM_DIR

ROOT = INTERIM_DIR / "politicas_montos_suficiencia"
F = ROOT / "fuentes"
URL = "https://www.inegi.org.mx/app/indicesdeprecios/"


def prepare() -> None:
    """Descarga serie865541 observada en el árbol oficial y valida cobertura mensual."""
    F.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.get(URL + "Estructura.aspx?idEstructura=112001700010", timeout=40).raise_for_status()
    request = dict(idEstructura="112001700010", _formato="CSV", _anioI="2000",
                   _anioF="2026", _meta="1", _tipo="BIE", _info="Niveles",
                   _orient="vertical", esquema="", cvEstructura="112001700010",
                   pf="inp", cuadro="112001700010", _series="e|865541", st="")
    path = F / "inpc_inegi_exportacion.csv"
    if not path.exists():
        response = session.post(URL + "Exportacion.aspx?INPtipoExporta=CSV", data=request, timeout=40)
        response.raise_for_status()
        path.write_bytes(response.content)
    months = {n: i + 1 for i, n in enumerate("Ene Feb Mar Abr May Jun Jul Ago Sep Oct Nov Dic".split())}
    rows = []
    for row in csv.reader(io.StringIO(path.read_bytes().decode("cp1252"))):
        if len(row) == 2 and row[0][:3] in months and len(row[0]) == 8:
            rows.append(dict(periodo=f"{row[0][4:]}-{months[row[0][:3]]:02}", inpc=float(row[1])))
    inpc = pd.DataFrame(rows)
    expected = pd.period_range("2000-01", "2026-09", freq="M").astype(str).tolist()
    assert inpc.periodo.tolist() == expected and inpc.inpc.gt(0).all()
    assert inpc.iloc[-1].inpc == 146.075
    save_json(ROOT / "inpc_mensual.json", rows)
    raw = pd.read_excel(F / "Líneas_de_Pobreza_por_Ingresos_mar2025.xlsx", sheet_name=0, header=None)
    lpi = raw.loc[pd.to_datetime(raw[5], errors="coerce").notna(), [5, 6, 7, 9, 10]].copy()
    lpi.columns = ["periodo", "lpei_rural", "lpei_urbana", "lpi_rural", "lpi_urbana"]
    lpi.periodo = pd.to_datetime(lpi.periodo).dt.strftime("%Y-%m")
    assert lpi.periodo.tolist() == pd.period_range("1992-01", "2025-03", freq="M").astype(str).tolist()
    assert lpi.iloc[:, 1:].astype(float).gt(0).all().all()
    save_json(ROOT / "lineas_mensuales.json", lpi.to_dict("records"))
    urls = {
        "inpc_referencia": "https://sidof.segob.gob.mx/notas/docFuente/5800864",
        "lpi_metodo": "https://www.coneval.org.mx/Medicion/MP/Paginas/Lineas-de-Pobreza-por-Ingresos.aspx",
        "lpi_inegi": "https://www.inegi.org.mx/desarrollosocial/lp/",
        "geo_2021": "https://www.inegi.org.mx/rnm/index.php/catalog/861/variable/F40/V14465?name=TAM_LOC_21",
        "geo_2018": "https://www.inegi.org.mx/rnm/index.php/catalog/861/variable/F46/V16487?name=TAM_LOC_18",
        "k2021": "https://www.inegi.org.mx/rnm/index.php/catalog/861/variable/F40/V14717?name=K61_1_1_21",
        "a2021": "https://www.inegi.org.mx/rnm/index.php/catalog/861/variable/F40/V14790?name=K80_1_1_21",
        "krec2021": "https://www.inegi.org.mx/rnm/index.php/catalog/861/variable/F40/V14714?name=K58A_21",
        "arec2021": "https://www.inegi.org.mx/rnm/index.php/catalog/861/variable/F40/V14788?name=K79A_21",
    }
    for name, code in {"rop2007":4964186,"rop2009":5076295,"rop2012":5228700,
                       "rop2013":5309974,"rop2018":5509626,"rop2019":5551445,
                       "rop2020":5583304,"rop2021_inicio":5608440,
                       "rop2021_julio":5623150,"rop2022_fechas_tardias":5639752,
                       "antecedentes_rop2023":5676228}.items():
        urls[name] = f"https://sidof.segob.gob.mx/notas/docFuente/{code}"
    manifest = []
    for name, url in urls.items():
        target = F / (name + ".txt")
        if not target.exists():
            try:
                response = session.get(url, timeout=10)
            except requests.exceptions.Timeout:
                if "/docFuente/" not in url:
                    raise
                url = "https://dof.gob.mx/nota_detalle_popup.php?codigo=" + url.rsplit("/", 1)[-1]
                response = session.get(url, timeout=15)
            response.raise_for_status()
            text = BeautifulSoup(response.content, "html.parser").get_text(" ", strip=True)
            target.write_text(text)
        content = target.read_text()
        assert len(content) > (10 if name == "lpi_inegi" else 200), (name, content)
        manifest.append(dict(clave=name, url=url, archivo=str(target.relative_to(ROOT)),
                             sha256=sha256(target.read_bytes()).hexdigest()))
    save_json(ROOT / "fuentes.json", dict(consulta="2026-10-14", referencia="2026-09",
        inpc_referencia=146.075, base="Segunda quincena julio2018=100; serie enlazada actualización2024",
        serie=865541, inpc_url=URL+"Estructura.aspx?idEstructura=112001700010",
        solicitud_exportacion=request, inpc_sha256=sha256(path.read_bytes()).hexdigest(),
        inpc_N=len(rows), lpi_N=len(lpi), lpi_version="CONEVAL marzo2025; reestimada con actualización2024",
        lpi_url="https://www.coneval.org.mx/Medicion/Documents/Lineas_de_Pobreza_por_Ingresos/Lineas_de_Pobreza_por_Ingresos.zip",
        lpi_sha256=sha256((F / "Líneas_de_Pobreza_por_Ingresos_mar2025.xlsx").read_bytes()).hexdigest(),
        documentos=manifest))
    print(f"Fuentes: INPC{len(rows)} meses; líneas{len(lpi)} meses; documentos{len(manifest)}")


if __name__ == "__main__":
    prepare()
