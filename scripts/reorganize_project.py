"""Migra ubicaciones con respaldo externo; nunca retira históricos ni prepara Git."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def prepare(backup: Path) -> None:
    """Conserva todos los documentos y clasifica sus ubicaciones sin borrar originales."""
    baseline = json.loads((backup / "manifest.json").read_text())
    routes = {"archivos": {}, "directorios": {
        "docs/eda/pensiones_exploratorio_v1": "data/interim/eda_pensionaria",
        "docs/eda/proteccion_economica": "data/interim/proteccion_economica",
        "docs/integracion/titularidad": "data/interim/titularidad",
        "docs/integracion": "data/interim/integracion",
        "docs/pensiones/nacional": "data/interim/catalogo_nacional",
        "docs/pensiones": "data/interim/inventario",
        "docs/eda": "data/interim/eda_independiente",
        "docs/recuperacion": "investigacion/notas/recuperacion",
        "docs": "data/interim/historico",
        "reports/tables": "data/interim/cp1",
        "reports/eda_independiente": "data/interim/eda_independiente",
        "reports/notebooks": "data/interim/notebooks_ejecutados",
        "reports": "data/interim/ejecucion",
    }, "estado": "Históricos conservados hasta aprobación final; no usarlos como destinos nuevos"}
    special = {
        "docs/integracion/diccionario_columnas.json": "diccionarios/diccionario_integrado.json",
        "docs/pensiones/inventario_fuentes.json": "diccionarios/inventario_fuentes.json",
        "docs/eda/cobertura_variables.json": "diccionarios/cobertura_variables.json",
        "docs/eda/contratos_simple.json": "diccionarios/contratos_enasemsimple.json",
        "docs/eda/contratos_k2021.json": "diccionarios/contratos_k2021.json",
        "docs/eda/universos_simple.json": "diccionarios/universos_enasemsimple.json",
        "docs/eda/pensiones_exploratorio_v1/mapa_columnas.json": "diccionarios/mapa_conceptual.json",
        "docs/eda/proteccion_economica/contratos_armonizacion.json": "diccionarios/armonizacion_pensiones.json",
        "docs/eda/pensiones_exploratorio_v1/mapa_armonizadas.json": "diccionarios/armonizacion_pensiones.json",
        "docs/pensiones/nacional/matriz_variables_rondas.json": "diccionarios/programas_variables_rondas.json",
        "docs/pensiones/nacional/fuentes_descargadas.json": "investigacion/fuentes_oficiales/fuentes_descargadas.json",
        "manuscrito/referencias.bib": "investigacion/referencias.bib",
    }
    texts, fiches, records = {}, [], []
    for folder in ("diccionarios", "investigacion/articulos", "investigacion/fuentes_oficiales", "investigacion/notas", "resultados/figuras"):
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
    files = [p for p in (ROOT / "docs").rglob("*") if p.is_file() and p.name != ".DS_Store"]
    files += [p for p in (ROOT / "reports").rglob("*") if p.is_file() and p.suffix != ".png" and p.name not in {".DS_Store", ".gitkeep"} and "pdf_qa" not in p.parts]
    files += [ROOT / "manuscrito/referencias.bib"]
    for p in files:
        old = p.relative_to(ROOT).as_posix()
        if p.suffix == ".md":
            destination = "data/interim/textos_virtuales/" + old
            text = p.read_text()
            texts[old] = {"texto": text, "sha256_original": sha(p)}
            if old.startswith(("docs/eda/variables/", "docs/eda/k2021/")):
                fiche = {"variable": p.stem, "origen": old, "sha256_original": sha(p),
                         "secciones": [{"titulo": m.group(1), "contenido": m.group(2)} for m in re.finditer(r"(?ms)^## ([^\n]+)\n(.*?)(?=^## |\Z)", text)],
                         "texto_conservado": text}
                fiches.append(fiche)
        elif old in special:
            destination = special[old]
        elif p.suffix == ".json" and any(w in p.stem for w in ("contrato", "diccionario", "mapa", "inventario", "disponibilidad", "versiones_fuente", "universo", "fuentes_documentales")):
            destination = "diccionarios/" + old.removeprefix("docs/").replace("/", "__")
        else:
            prefix = next((k for k in sorted(routes["directorios"], key=len, reverse=True) if old.startswith(k + "/")), None)
            destination = routes["directorios"][prefix] + old[len(prefix):] if prefix else old
        routes["archivos"][old] = destination
        if p.suffix != ".md":
            target = ROOT / destination
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and sha(target) != sha(p):
                raise ValueError(f"Destino conflictivo: {destination}")
            if p != target:
                shutil.copy2(p, target)
            assert sha(p) == sha(target)
        records.append({"origen": old, "destino": destination, "sha256": sha(p), "accion": "texto consolidado" if p.suffix == ".md" else "copia verificada"})
    canonical = {}
    for base in (ROOT / "reports", ROOT / "manuscrito/figuras"):
        for p in sorted(base.rglob("*.png")):
            if any(w in p.parts for w in ("pdf_qa", "qa")):
                continue
            old = p.relative_to(ROOT).as_posix()
            digest = sha(p)
            if digest in canonical:
                destination = canonical[digest]
            else:
                name = old.removeprefix("reports/").removeprefix("manuscrito/").replace("/", "__")
                destination = "resultados/figuras/" + name
                shutil.copy2(p, ROOT / destination)
                canonical[digest] = destination
            routes["archivos"][old] = destination
            records.append({"origen": old, "destino": destination, "sha256": digest, "accion": "figura única"})
    save(ROOT / "diccionarios/rutas_migracion.json", routes)
    save(ROOT / "diccionarios/fichas_variables.json", fiches)
    save(ROOT / "data/interim/textos_analisis.json", texts)
    history = {n: value for n, value in texts.items() if n in {"docs/DECISIONES.md", "docs/EXPERIMENTOS.md", "docs/HANDOFF.md", "docs/ROADMAP.md", "docs/PLAN_EDA_RONDAS_Y_PENSIONES.md", "docs/PREGUNTA_Y_ALCANCE.md", "docs/CP0_VERIFICACION.md"} or n.startswith("docs/recuperacion/")}
    save(ROOT / "investigacion/notas/historial_metodologico.json", history)
    save(ROOT / "investigacion/fuentes_oficiales/catalogo_local.json", {"fuentes": "data/raw/documentacion_catalogo", "nota": "Documentos conservados en origen, no duplicados aquí; autorización de redistribución pendiente", "inventarios": "data/interim/catalogo_nacional/indice_catalogo.json"})
    save(ROOT / "data/interim/migracion_proyecto.json", {"backup": str(backup), "git_index_sha256": baseline["git_index_sha256"], "archivos": records, "base_original": baseline["archivos"]["data/processed/enasem_integrada_provisional.parquet"], "estado": "Retiro histórico y publicación pendientes de aprobación"})
    print(f"Clasificados {len(records)} archivos; {len(fiches)} fichas consolidadas, {len(canonical)} figuras únicas.")


def rewrite_scripts() -> None:
    """Actualiza construcción y lectura de rutas; mantiene cálculos y lógica científica."""
    from tesis_enasem.project_paths import project_path
    for p in (ROOT / "scripts").glob("*.py"):
        if p.name in {"reorganize_project.py", "build_main_notebooks.py", "validate_migration.py"}:
            continue
        text = p.read_text()
        tree = ast.parse(text)
        prefixes = {"ROOT": ""}
        for node in tree.body:
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.BinOp):
                def parts(value: ast.AST) -> list | None:
                    if isinstance(value, ast.Name) and value.id in prefixes:
                        return [prefixes[value.id]]
                    if isinstance(value, ast.Constant) and isinstance(value.value, str):
                        return [value.value]
                    if isinstance(value, ast.BinOp) and isinstance(value.op, ast.Div):
                        a, b = parts(value.left), parts(value.right)
                        return a + b if a is not None and b is not None else None
                    return None
                pieces = parts(node.value)
                if pieces is not None:
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            prefixes[target.id] = str(Path(*pieces))
        encoded = text.encode()
        lines = encoded.splitlines(keepends=True)
        offsets = [0]
        for line in lines:
            offsets.append(offsets[-1] + len(line))
        def span(node: ast.AST) -> tuple[int, int]:
            return offsets[node.lineno - 1] + node.col_offset, offsets[node.end_lineno - 1] + node.end_col_offset
        replacements = []
        class Transform(ast.NodeVisitor):
            def visit_BinOp(self, node: ast.BinOp) -> None:
                pieces = []
                item = node
                while isinstance(item, ast.BinOp) and isinstance(item.op, ast.Div):
                    pieces.insert(0, item.right)
                    item = item.left
                if isinstance(item, ast.Name) and item.id in prefixes:
                    args = [repr(prefixes[item.id])] + [ast.get_source_segment(text, x) for x in pieces]
                    replacements.append((*span(node), "project_path(" + ", ".join(args) + ")"))
                else:
                    self.generic_visit(node)
        Transform().visit(tree)
        for start, end, value in sorted(replacements, reverse=True):
            encoded = encoded[:start] + value.encode() + encoded[end:]
        text = encoded.decode()
        # Separate pass preserves nested route changes without AST reformatting prose.
        tree = ast.parse(text); encoded = text.encode(); lines = encoded.splitlines(keepends=True); offsets = [0]
        for line in lines:
            offsets.append(offsets[-1] + len(line))
        replacements = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"read_text", "write_text"}:
                a, b = span(node.func)
                replacements.append((a, b, ("read_project_text" if node.func.attr == "read_text" else "write_project_text") + "(" + ast.get_source_segment(text, node.func.value) + ", "))
                # Replace function prefix plus original opening parenthesis once.
        for a, b, value in sorted(replacements, reverse=True):
            encoded = encoded[:a] + value.encode() + encoded[b + 1:]
        text = encoded.decode().replace(", )", ")")
        ast.parse(text)
        if replacements or "project_path(" in text:
            import_line = "from tesis_enasem.project_paths import project_path, read_project_text, write_project_text\n"
            location = text.find("\n", text.find("from __future__ import annotations")) + 1 if "from __future__ import annotations" in text else 0
            text = text[:location] + import_line + text[location:]
            p.write_text(text)
    print("Rutas de scripts centralizadas; funciones analíticas preservadas.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--rewrite-scripts", action="store_true")
    args = parser.parse_args()
    if args.rewrite_scripts:
        rewrite_scripts()
    else:
        prepare(args.backup)
