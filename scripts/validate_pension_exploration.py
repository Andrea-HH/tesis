"""Verifica reconciliación sustantiva y correspondencia de entregables EDA v1."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text, read_project_bytes
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import nbformat

from run_pension_exploration import ROOT,PUBLIC,YEARS,checked_hashes,write_json,inputs
from tesis_enasem.pension_exploration import PopulationSpec


def validate() -> None:
    r=json.loads(read_project_text(PUBLIC/'resultados.json'));p,k,a=inputs();s=PopulationSpec().select(p)
    n_wave={y:int(s.ano.eq(y).sum()) for y in YEARS}
    for year in YEARS:
        univ=r['univariados'][str(year)];assert sum(x['N'] for x in univ['titularidad'])==n_wave[year]
        for z in univ['recibos_reutilizados']:assert z['N_si']+z['N_no']+z['N_desconocido']==n_wave[year]
        for var,rows in univ['controles'].items():
            if 'categoria' in rows[0]:assert sum(z['N'] for z in rows)==n_wave[year]
            else:
                assert rows[0]['N_valido']+rows[0]['N_desconocido']==n_wave[year]
                assert sum(x['N'] for x in univ['histograma_'+var])==rows[0]['N_valido']
        for prefix in ['B','T']:
            for j in range(1,9):
                key=f'{prefix}{j}_{year}';x=r['analisis'][key];bundle=json.loads(read_project_text(project_path('', x['tabla'])))
                assert (project_path('', x['figura'])).exists() and bundle['interpretacion']==x['interpretacion']
                if 'tasas' in bundle:
                    for z in bundle['tasas']:assert z['N_si']+z['N_no']+z['N_desconocido']==z['N_total']
                    assert sum(z['N_total'] for z in bundle['tasas'] if z['variable']=='pension_propia_k')==n_wave[year]
                if 'conjunta' in bundle:assert sum(z['N'] for z in bundle['conjunta'])==n_wave[year]
                if 'patrimonio' in bundle:assert sum(z['N_total'] for z in bundle['patrimonio'])==n_wave[year]
                if prefix=='T':
                    assert len(bundle['grupos'])==2 or (j in (4,5) and 'conjunta' in bundle) or (j==8 and 'patrimonio' in bundle)
        events=k.loc[k.ano.eq(year)&k.beneficiario_id.isin(s.loc[s.ano.eq(year),'id'])]
        inst=r['univariados'][str(year)]['instituciones']
        for z in inst:
            ids=set(events.loc[events.instituciones_codigos.map(lambda codes:z['institucion_codigo'] in list(codes)),'beneficiario_id'])
            assert len(ids)==z['N_personas']
    for key,x in r['seguimiento'].items():
        rows=json.loads(read_project_text(project_path('', x['tabla'])));assert rows and (project_path('', x['figura'])).exists()
        assert all(z['N']>=0 and z['N']<=z['N_origen_estado'] for z in rows)
        if not rows[0]['comparabilidad_condicionada']:
            assert all(z['evento'].startswith('Cambio de instrumento') for z in rows)
            assert x['estado']=='No viable con los datos actuales'
    statuses={'Completo y validado','Completo provisional','Parcial','Pendiente','No viable con los datos actuales'}
    matrix=json.loads(read_project_text(PUBLIC/'matriz_cumplimiento.json'))
    assert all(z['Estado'] in statuses for z in matrix)
    for z in matrix:
        if z['Estado'].startswith('Completo'):
            for field in ['Tabla generada','Gráfica generada']:
                value=z[field]
                if value.startswith(('docs/','reports/')):assert (project_path('', value)).is_file(),value
            assert z['Interpretación'] and z['Archivo y ubicación']
    for path in (project_path('', 'notebooks')).glob('06[a-d]_*.ipynb'):
        nb=nbformat.read(path,as_version=4);nbformat.validate(nb)
        assert not any(cell.get('outputs') for cell in nb.cells)
        executed=project_path('', 'reports/notebooks', f'{path.stem}_ejecutado.ipynb')
        n=nbformat.read(executed,as_version=4)
        assert not any(o.get('output_type')=='error' for cell in n.cells for o in cell.get('outputs',[]))
        assert all(cell.get('execution_count') is not None for cell in n.cells if cell.cell_type=='code')
    # Metadatos pueden nombrar id; agregados sustantivos no deben publicar una clave personal.
    forbidden={'id','cunicah','np','beneficiario_id','hogar_fuente'}
    def check_schema(obj):
        if isinstance(obj,dict):
            assert not forbidden.intersection(obj)
            for value in obj.values():check_schema(value)
        elif isinstance(obj,list):
            for value in obj:check_schema(value)
    for path in (PUBLIC/'tablas').glob('*.json'):check_schema(json.loads(read_project_text(path)))
    hashes=checked_hashes()
    record={'maestro_N':len(p),'maestro_personas':p.id.nunique(),'muestra60_N':len(s),'muestra60_personas':s.id.nunique(),
      'clave_persona_ronda_unica':not p[['id','ronda']].duplicated().any(),'N_por_onda':n_wave,
      'B1_B8_y_T1_T8_en_seis_rondas':True,'trivariados_simultaneos_comprobados':True,
      'particiones_y_porcentajes_reconciliados':True,'instituciones_personas_no_slots':True,
      'rupturas_no_interpretadas_como_inicio_perdida':True,'agregados_sin_claves_personales':True,
      'notebooks_ejecutados_sin_errores':True,'N_entradas_anteriores_preservadas':len(hashes),
      'clasificacion_definitiva':False,'ponderacion_validada':False,'aceptacion_metodologica':'Pendiente',
      'estados_matriz':dict(Counter(x['Estado'] for x in matrix)),
      'sha_resultados':sha256(read_project_bytes(PUBLIC/'resultados.json')).hexdigest()}
    write_json(PUBLIC/'validacion_tecnica.json',record);print(json.dumps(record,ensure_ascii=False,indent=2))


if __name__=='__main__':validate()
