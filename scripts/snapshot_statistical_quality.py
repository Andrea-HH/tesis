"""Congela originales ANTES de editar; conserva una instantánea existente.

No se debe borrar el manifiesto para recrearlo después de corregir documentos.
"""
from pathlib import Path
import subprocess,json,hashlib,shutil,datetime
from tesis_enasem.project_paths import PROJECT_ROOT
root=PROJECT_ROOT;base=root/'data/interim/auditoria_calidad_divulgacion';snap=base/'privado/originales'
if (base/'instantanea.json').exists():
 print('Instantánea previa conservada');raise SystemExit
paths=set(subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0'))
paths.update(subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=root).decode().split('\0'))
paths.update(['notebooks/09_INCORPORACION_PROTECCION_PROPIA.ipynb'])
for folder in ['incorporacion_proteccion_propia','transiciones_montos_pensionarios','politicas_montos_suficiencia','cobertura_proteccion_economica','pensiones_salud','trayectorias_pensiones_salud','pensiones_mortalidad_seleccion','eda_pensionaria']:
 paths.update(str(p.relative_to(root)) for p in (root/'data/interim'/folder).glob('*.json'))
entries={}
for name in sorted(paths):
 p=root/name
 if not name or not p.is_file() or name.startswith(('data/raw/','data/processed/','.git/')):continue
 dest=snap/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
 entries[name]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
base.mkdir(parents=True,exist_ok=True)
manifest={'fecha':'2026-10-23','git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'stash0':subprocess.check_output(['git','rev-parse','stash@{0}'],cwd=root,text=True).strip(),'archivos':entries,'nota':'Instantánea privada inmutable de originales; data/raw y processed no se copian ni modifican; permanecen excluidos de Git.'}
(base/'instantanea.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('Preservados',len(entries),'archivos privados originales;',round(sum(v['bytes'] for v in entries.values())/1e6,1),'MB; stash intacto.')
# Agregados externos referenciados por el índice EDA; conservar también sus huellas.
external={}
for p in sorted((root/'data/interim/eda_pensionaria/tablas').glob('*.json')):
 name=str(p.relative_to(root));dest=snap/name;dest.parent.mkdir(parents=True,exist_ok=True)
 shutil.copy2(p,dest);external[name]=hashlib.sha256(p.read_bytes()).hexdigest()
(base/'privado/fuentes_eda_adicionales.json').write_text(json.dumps(external,ensure_ascii=False,indent=2)+'\n')
