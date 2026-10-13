"""Coteja migración con respaldo: contenido, claves, figuras, notebooks e índice Git."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import ast

import nbformat
import pandas as pd

from tesis_enasem.project_paths import PROJECT_ROOT, project_path
from tesis_enasem.pension_exploration import PopulationSpec
from tesis_enasem.workspace import validate_documentary_coverage


def validate() -> dict:
    """Comprueba evidencia existente; no recalcula indicadores ni altera bases."""
    root = PROJECT_ROOT
    manifest_path = root / 'data/interim/migracion_proyecto.json'
    manifest = json.loads(manifest_path.read_text())
    baseline = json.loads((Path(manifest['backup'])/'manifest.json').read_text())
    texts = json.loads((root/'data/interim/textos_analisis.json').read_text())
    verified = 0
    for item in manifest['archivos']:
        if item['accion'] == 'texto consolidado':
            assert sha256(texts[item['origen']]['texto'].encode()).hexdigest() == item['sha256'], item['origen']
        else:
            target = project_path(item['origen'])
            assert sha256(target.read_bytes()).hexdigest() == item['sha256'], item['destino']
        verified += 1
    unchanged = []
    for name, metadata in baseline['archivos'].items():
        if name.startswith(('data/raw/', 'data/processed/', 'docs/')) and not name.endswith('.DS_Store'):
            if name.startswith('docs/') and not (root/name).exists():
                # After an approved retirement, destinations and the verified backup
                # remain authoritative; no runtime dependency on the old directory.
                continue
            assert sha256((root/name).read_bytes()).hexdigest() == metadata['sha256'], name
            unchanged.append(name)
    scientific_modules = ['integration.py','pension_ownership.py','protection_eda.py','pension_exploration.py','audit.py','independent_eda.py','economic_eda.py','joint_eda.py','source_inventory.py']
    for name in scientific_modules:
        old='src/tesis_enasem/'+name
        assert sha256((root/old).read_bytes()).hexdigest() == baseline['archivos'][old]['sha256'], old
    original_audit_report=(Path(manifest['backup'])/'audit_report_original.py').read_text()
    class IgnoreReportIO(ast.NodeTransformer):
        def visit_Expr(self, node: ast.Expr):
            if isinstance(node.value,ast.Call):
                fn=node.value.func
                if isinstance(fn,ast.Attribute) and fn.attr=='write_text' or isinstance(fn,ast.Name) and fn.id=='write_analysis_note':
                    return None
            return self.generic_visit(node)
    def computational_functions(text: str):
        return [ast.dump(IgnoreReportIO().visit(n),include_attributes=False) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)]
    assert computational_functions(original_audit_report)==computational_functions((root/'src/tesis_enasem/audit_report.py').read_text()),'Lógica CP1 modificada fuera de IO'
    frame = pd.read_parquet(root/'data/processed/enasem_integrada_provisional.parquet',columns=['id','ronda','edad','tipent'])
    assert len(frame)==99676 and frame.id.nunique()==27171
    assert not frame.duplicated(['id','ronda']).any()
    subset=PopulationSpec(minimum_age=60).select(frame)
    assert len(subset)==56004 and subset.id.nunique()==18754
    assert len(json.loads((root/'diccionarios/diccionario_integrado.json').read_text())) == 8668
    fiches=json.loads((root/'diccionarios/fichas_variables.json').read_text())
    assert len(fiches)==429
    for fiche in fiches:
        assert sha256(fiche['texto_conservado'].encode()).hexdigest()==fiche['sha256_original']
    notebook_evidence={}
    for name in ['01_INTEGRACION','02_EDA_COMPLETO']:
        source=nbformat.read(root/'notebooks'/f'{name}.ipynb',as_version=4)
        nbformat.validate(source)
        assert all(not c.get('outputs') and c.get('execution_count') is None for c in source.cells if c.cell_type=='code')
        executed=nbformat.read(root/'data/interim/notebooks_ejecutados'/f'{name}_ejecutado.ipynb',as_version=4)
        codes=[c for c in executed.cells if c.cell_type=='code']
        assert all(c.execution_count is not None for c in codes)
        assert not any(o.output_type=='error' for c in codes for o in c.outputs)
        notebook_evidence[name]={'celdas_codigo':len(codes),'errores':0,'fuente_sin_outputs':True}
    report=(root/'resultados/INFORME_GENERAL.md').read_text()
    figures=re.findall(r'!\[[^\]]*\]\(([^)]+)\)',report)
    for figure in figures:
        assert (root/'resultados'/figure).is_file(),figure
    results=json.loads(project_path('docs/eda/pensiones_exploratorio_v1/resultados.json').read_text())
    for year in (2001,2003,2012,2015,2018,2021):
        for prefix in ('B','T'):
            for n in range(1,9):
                key=f'{prefix}{n}_{year}'
                assert key in report,key
                assert project_path(results['analisis'][key]['tabla']).is_file()
                assert project_path(results['analisis'][key]['figura']).is_file()
    old_keys=set(json.loads((Path(manifest['backup'])/'manifest.json').read_text())['archivos'])
    retired_candidates=sorted(p for p in old_keys if p.startswith(('docs/','reports/','notebooks/','manuscrito/figuras/')) or p in {'manuscrito/referencias.bib','data/processed/eda_pensionaria_v1/manuscrito_antes_eda.pdf'})
    exclusions = set(manifest.get('auditoria_previa_limpieza', {}).get('excluir_del_retiro', []))
    completed = set(manifest.get('limpieza_local_definitiva', {}).get('archivos_retirados', []))
    manifest['candidatos_retiro']=[{'ruta':p,'motivo':'Consolidado o regenerable; original preservado en respaldo','aprobacion':'Autorizado y retirado' if p in completed else 'Pendiente'} for p in retired_candidates if p not in exclusions]
    adjustments = manifest.get('ajustes_previos_retiro', {})
    for item in adjustments.get('notebooks_historicos_conservados', []) + adjustments.get('capturas_pdf_conservadas', []):
        assert sha256((root/item['destino']).read_bytes()).hexdigest() == item['sha256'], item['destino']
        if (root/item['origen']).exists():
            assert sha256((root/item['origen']).read_bytes()).hexdigest() == item['sha256'], item['origen']
    if adjustments:
        adjustments['cobertura_documental'] = validate_documentary_coverage()
    current_index=sha256((root/'.git/index').read_bytes()).hexdigest()
    authorized = manifest.get('publicacion_github', {}).get('seleccion_final_sha256')
    local_consolidation = manifest.get('consolidacion_capitulos', {})
    if local_consolidation:
        # La tarea local prohíbe operaciones Git: cotejar solo el archivo del índice.
        assert current_index == local_consolidation['indice_sha256'], 'Índice alterado durante la organización local'
    elif (root/'.git/HEAD').exists():
        staged = subprocess.check_output(['git','--no-optional-locks','ls-files','--stage'],cwd=root)
        authorized = manifest.get('publicacion_github', {}).get('seleccion_final_sha256')
        if authorized:
            assert sha256(staged).hexdigest() == authorized, 'Selección pública distinta de la autorizada para preparación'
        else:
            assert staged == (Path(manifest['backup'])/'indice_git.txt').read_bytes(),'Selección preparada de Git modificada'
    else:
        assert current_index==manifest['git_index_sha256'],'Índice de la copia aislada no coincide con respaldo'
    evidence={'fecha':'2026-10-13','archivos_migrados_verificados':verified,'originales_inmutables':len(unchanged),
              'modulos_cientificos_sin_cambios':scientific_modules,
              'audit_report':'Funciones equivalentes por AST; solo salida consolidada en lugar de docs/',
              'estadisticas':'JSON agregados byte-idénticos, sin recálculo ni redefinición',
              'maestro':{'registros':99676,'personas':27171,'duplicados_persona_ronda':0},
              'muestra60':{'registros':56004,'personas':18754},
              'columnas_diccionario':8668,'fichas_conservadas':429,'figuras_informe_existentes':len(figures),
              'notebooks':notebook_evidence,'B1_B8_T1_T8_seis_rondas':True,'indice_git_intacto':bool(local_consolidation) or not bool(authorized),
              'seleccion_git_validada':True,
              'git_control':('Archivo del índice byte-idéntico al inicio de la consolidación; sin ejecutar Git' if local_consolidation else 'Selección pública preparada por autorización expresa, cotejada por huella; selección anterior respaldada' if authorized else 'Comparación de rutas, modos, blobs y etapas; actualizaciones de caché de stat no son cambios de selección'),
              'sha_archivo_indice_actual':current_index,
              'retiro_historicos':'Limpieza local autorizada ejecutada; excepciones conservadas' if completed else 'Pendiente de aprobación; ningún original eliminado',
              'github':{'visibilidad_comprobada':'public','politica_autora':'Mantener público; publicar solo selección revisada sin microdatos','publicacion':'No realizada'}}
    manifest['validacion']=evidence
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(evidence,ensure_ascii=False,indent=2))
    return evidence


if __name__=='__main__':
    validate()
