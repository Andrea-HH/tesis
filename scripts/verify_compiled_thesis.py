"""Verifica el PDF compilado y genera imágenes de revisión en GitHub Actions.

No lee microdatos ni recalcula estimaciones. El control textual y geométrico
no sustituye la revisión visual de las imágenes producidas.
"""
from __future__ import annotations
import hashlib
import json
import re
import subprocess
from pathlib import Path
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "manuscrito/build"
pdf = BUILD / "main.pdf"
doc = pymupdf.open(pdf)
texts = [p.get_text() for p in doc]
all_text = "\n".join(texts)
normalized = re.sub(r"\s+", " ", all_text).casefold()
required = [
    "Selección documentada de ventanas longitudinales",
    "Comparabilidad longitudinal de K y A en las cinco ventanas",
    "Por qué K utiliza ventanas distintas de A",
    "homologación pendiente",
    "Seguro Popular",
    "primera vía",
    "complementariedad",
    "2018",
    "2021",
    "Composición de las incorporaciones observadas",
    "Probabilidad observada de incorporación",
    "Monto posterior por mitad patrimonial",
    "Respuesta a la pregunta central",
    "Correspondencia entre objetivos",
    "Sensibilidad de la medición y alcance de primera vía",
    "Unión K/A",
    "Diferencia de contrastes",
    "42,72",
    "49,77",
]
for phrase in required:
    if phrase.casefold() not in normalized:
        raise ValueError("Texto ausente del PDF: " + phrase)
if "\ufffd" in all_text or "??" in all_text:
    raise ValueError("Carácter de reemplazo o referencia sin resolver")
log = (BUILD / "main.log").read_text(errors="replace")
bad = [line for line in log.splitlines()
       if "undefined" in line.lower() or "Missing character:" in line]
if bad:
    raise ValueError("Diagnóstico TeX pendiente: " + repr(bad))
outside = []
for number, page in enumerate(doc, 1):
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                x0, y0, x1, y1 = (pymupdf.Rect(span["bbox"]) * page.rotation_matrix)
                if span["text"].strip() and (x0 < -1 or y0 < -1 or x1 > page.rect.width + 1 or y1 > page.rect.height + 1):
                    outside.append({"page": number, "text": span["text"], "bbox": span["bbox"]})
if outside:
    raise ValueError("Texto fuera de página: " + repr(outside[:10]))
# Se incluyen portada, resumen y páginas con la matriz y su explicación.
focus = {0, 1}
tokens = ["Selección documentada", "Decisión y diferencias", "Cuadro 3.",
          "Por qué K utiliza", "La selección de ventanas del cuadro",
          "homologación pendiente", "Estimandos del contraste", "Contraste central:",
          "Cuadro 4.", "Respuesta estadística", "Correspondencia entre objetivos",
    "Sensibilidad de la medición y alcance de primera vía",
    "Unión K/A",
    "Diferencia de contrastes",
    "42,72",
    "49,77",
          "Patrimonio neto basal", "Límites que permanecen"]
for i, text in enumerate(texts):
    if any(token in text for token in tokens):
        focus.add(i)
preview = ROOT / "data/interim/validacion_final_faseC_20261023/revision_pdf"
preview.mkdir(parents=True, exist_ok=True)
images = []
# Dos páginas grandes por lámina; lectura visual de cuadro y notas.
for group in range(0, len(sorted(focus)), 2):
    selected = sorted(focus)[group:group+2]
    sheet = pymupdf.open()
    width, height = 612, 792
    canvas = sheet.new_page(width=width*2, height=height)
    for column, pno in enumerate(selected):
        rect = pymupdf.Rect(column*width, 0, (column+1)*width, height)
        canvas.show_pdf_page(rect, doc, pno)
    path = preview / f"comparabilidad_{group//2+1:02d}.png"
    canvas.get_pixmap(matrix=pymupdf.Matrix(1, 1), alpha=False).save(path)
    images.append(str(path.relative_to(ROOT)))
# Contactos de todo el documento para detectar páginas vacías o desbordes.
for offset in range(0, len(doc), 12):
    sheet = pymupdf.open()
    canvas = sheet.new_page(width=612, height=792)
    for k, pno in enumerate(range(offset, min(offset+12, len(doc)))):
        col, row = k % 4, k // 4
        canvas.show_pdf_page(pymupdf.Rect(col*153, row*264, (col+1)*153, (row+1)*264), doc, pno)
    path = preview / f"contacto_{offset//12+1:02d}.png"
    canvas.get_pixmap(alpha=False).save(path)
    images.append(str(path.relative_to(ROOT)))
public_paths = set(json.loads((ROOT/'diccionarios/cierre_publicacion.json').read_text())['archivos_publicar'])
source_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
checks = {
    "source_commit": source_sha,
    "source_status": "working tree" if subprocess.check_output(["git","status","--porcelain"],cwd=ROOT,text=True).strip() else "committed",
    "source_files_sha256": {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/"manuscrito").rglob("*.tex")) if "build" not in p.relative_to(ROOT).parts and p.relative_to(ROOT).as_posix() in public_paths},
    "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
    "pages": len(doc),
    "required_text": required,
    "required_text_present": True,
    "undefined_references": bad,
    "outside_page_spans": outside,
    "overfull_hboxes": [line for line in log.splitlines() if "Overfull" in line],
    "focus_pages": [i+1 for i in sorted(focus)],
    "preview_images": images,
    "visual_review": "Pendiente de inspección humana o del asistente; no certificada por este script",
    "statistical_recalculation": False,
    "stored_estimates_revalidated": (ROOT/"data/interim/validacion_final_faseC_20261023/comprobaciones_numericas.json").exists(),
}
# Bibliography and embedded figures also belong to the compiled provenance.
checks['source_files_sha256']['investigacion/referencias.bib'] = hashlib.sha256((ROOT/'investigacion/referencias.bib').read_bytes()).hexdigest()
tex = '\n'.join(p.read_text() for p in (ROOT/'manuscrito').rglob('*.tex') if p.relative_to(ROOT).as_posix() in public_paths)
for rel in re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}', tex):
    figure=(ROOT/'manuscrito'/rel).resolve()
    name=figure.relative_to(ROOT).as_posix()
    assert name in public_paths, name
    checks['source_files_sha256'][name] = hashlib.sha256(figure.read_bytes()).hexdigest()
(BUILD / "validacion_pdf.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2)+"\n")
print(json.dumps(checks, ensure_ascii=False, indent=2))
