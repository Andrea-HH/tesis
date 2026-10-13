"""Notebook de auditoría por ronda; ejecución visible exclusivamente agregada."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text
import argparse
import json
from pathlib import Path
import nbformat
from nbclient import NotebookClient

ROOT=Path(__file__).resolve().parents[1]


def build() -> nbformat.NotebookNode:
    """Reutiliza el módulo; verifica sidecars sin mostrar identificadores."""
    md,code=nbformat.v4.new_markdown_cell,nbformat.v4.new_code_cell
    n=nbformat.v4.new_notebook()
    n.cells=[md('# 05c · Titularidad de pensiones: auditoría provisional\n\n'
        'Objetivo: separar beneficiario personal, pensión de pareja y presencia en hogar. '
        'Maestro completo: todas las edades/modalidades, clave id+ronda. Base anterior intacta; '
        'sidecar privado versionado, fuentes originales y CP1 conservados. Clasificación pendiente de validación definitiva.'),
        md('## Reproducción y denominadores\n\n'
           'RECALCULAR=True ejecuta solo esta auditoría, no la integración ni los EDA anteriores. '
           'Por defecto se verifican las tablas ya calculadas contra el sidecar. No mostrar filas, IDs o NP. '
           'Sí K requiere afirmativa; no K exige cuatro negativas. Desconocidos visibles. '
           'Hogar económico no equivale a todas las personas de la vivienda.'),
        code("from pathlib import Path\nfrom hashlib import sha256\nimport json,sys\nimport pandas as pd\nfrom IPython.display import display,Markdown,Image\n"
             "ROOT=next(p for p in [Path.cwd(),*Path.cwd().parents] if (p/'pyproject.toml').exists())\n"
             "sys.path.insert(0,str(ROOT/'scripts'))\nfrom run_pension_ownership_audit import run\nfrom export_ownership_manuscript import export\n"
             "RECALCULAR=False\nif RECALCULAR:\n    run()\n"
             "r=json.loads((ROOT/'docs/integracion/titularidad/resultados.json').read_text())\n"
             "assert sha256((ROOT/'data/processed/enasem_integrada_provisional.parquet').read_bytes()).hexdigest()==r['base_sha256_preservada']\n"
             "private=ROOT/'data/processed/auditoria_titularidad_v1'\n"
             "p=pd.read_parquet(private/'personas_ronda.parquet')\nassert len(p)==99676 and p.id.nunique()==27171\nassert not p[['id','ronda']].duplicated().any()\n"
             "display(pd.DataFrame(r['resumen_rondas']))\nprint('Base anterior preservada; sidecar 99,676 personas-ronda, clave única. Ningún ID se muestra.')"),
        md('## Contratos documentales\n\n'
           '2001: key01 publicado, J1/controles ausentes (validación independiente pendiente). '
           '2003: codent03, K96a y key03. 2012/2015: NP, K96a y key12/key15; informante externo desconocido. '
           '2018/2021: punteros propios/pareja concordantes en individual y hogar; 2021 también key_21. '
           'La recepción de la pareja exige cotejar el otro puntero por separado. '
           'Una sola persona por rama. Sección del cónyuge puede ser propia para la persona de la fila.'),
        code("display(pd.DataFrame(r['contratos_rondas']))\ndisplay(pd.DataFrame(r['cotejos_orientacion_construida']))\n"
             "display(pd.DataFrame(json.loads((ROOT/'docs/integracion/titularidad/fuentes_documentales.json').read_text())))")]
    report=read_project_text(project_path('', 'docs/integracion/titularidad/AUDITORIA_TITULARIDAD.md'))
    for year in [2001,2003,2012,2015,2018,2021]:
        section=report.split(f'### {year}\n',1)[1].split('\n### ',1)[0].split('\n## ',1)[0]
        n.cells += [md(f'## Ronda {year}\n\n'+section),code(
            f"a=next(a for a in r['resumen_rondas'] if a['ano']=={year})\ns=p.loc[p.ano.eq({year})]\n"
            "assert len(s)==a['N_personas']\nassert s.titularidad_rama.isna().sum()==a['N_titular_indeterminado']\n"
            "assert s.pension_propia_k.eq(True).sum()==a['N_pension_propia_si']\n"
            "assert s.pension_propia_k.eq(False).sum()+s.pension_propia_k.eq(True).sum()+s.pension_propia_k.isna().sum()==len(s)\n"
            "assert s.pension_conyuge_k.eq(True).sum()==a['N_pension_conyuge_si']\n"
            "assert s.pension_conyuge_k.eq(False).sum()+s.pension_conyuge_k.eq(True).sum()+s.pension_conyuge_k.isna().sum()==len(s)\n"
            f"display(pd.DataFrame([x for x in r['modalidades'] if x['ano']=={year}]))\n"
            f"display(pd.DataFrame([x for x in r['duplicacion_montos'] if x['ano']=={year}]))")]
    n.cells += [md('## Transiciones 2021 y doble conteo\n\n'
        'Se separan tres matrices: indicador propio almacenado frente a auditoría; indicador de pareja '
        'antes/después del cotejo del otro puntero dentro de esta auditoría; y escenario ingenuo '
        'contrafactual de atribuir cualquier pensión del hogar a cada persona. Firmas iguales entre beneficios no justifican borrarlos. '
        'Hogar se suma por evento original único; persona se restringe a su beneficiario. '
        'Los montos antes/después de viudez y las versiones imputadas no se suman como componentes adicionales.'),
        code("display(pd.DataFrame(r['transiciones_2021']))\n"
             "e=pd.read_parquet(private/'eventos_originales.parquet')\n"
             "assert not e[['ano','hogar_fuente','fuente','version','rama','tipo','slot']].duplicated().any()\n"
             "assert set(e.version)=={'original'}\n"
             "for a in r['duplicacion_montos']:\n    v=e.loc[e.ano.eq(a['ano']) & e.enlazado_maestro]\n"
             "    assert len(v)==a['N_slots_declarados_enlazados']\n"
             "    assert abs(v.monto_mensual_observado.sum()-a['suma_mensual_parcial_hogares'])<0.01\n"
             "display(pd.DataFrame(r['duplicacion_montos']))"),
        md('## Comparación visual y manuscrito\n\n'
           'La figura usa BrBG y conteos absolutos. Los instrumentos y los niveles de verificación difieren; '
           'no se interpreta una reducción entre rondas como pérdida individual de cobertura. '
           'Los programas públicos, viudez y transferencias mixtas mantienen procedencia y límites propios.'),
        code("export()\ndisplay(Image(filename=str(ROOT/'manuscrito/figuras/borradores/titularidad_rondas.png')))"),
        md('## Interpretación y pendientes\n\n'+report.split('## Modalidades y limitaciones',1)[1].split('## Documentos primarios',1)[0]),
        md('## Próximo paso de validación\n\n'
           'Recuperar control J1/orden de entrevistas y esclarecer punteros discordantes con el proveedor. '
           'Validar prestaciones de supervivencia/divorcio y apoyos públicos sin duplicarlos con K. '
           'La auditoría no aprueba clasificación final, muestra, pesos o deflactor; no hay modelos ni publicación.')]
    n.metadata.kernelspec={'display_name':'Python 3','language':'python','name':'python3'}
    n.metadata.language_info={'name':'python','version':'3.11'}
    nbformat.write(n,project_path('', 'notebooks/05c_titularidad_pensiones.ipynb'))
    return n


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    n=build()
    if args.execute:
        NotebookClient(n,timeout=1200,kernel_name='myenv',resources={'metadata':{'path':str(ROOT)}}).execute()
        nbformat.write(n,project_path('', 'reports/notebooks/05c_titularidad_pensiones_ejecutado.ipynb'))
        print('Notebook titularidad ejecutado; salidas exclusivamente agregadas.')
