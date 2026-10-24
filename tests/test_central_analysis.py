"""Validación con casos que distinguen estimandos y dependencia."""
import numpy as np
import pandas as pd
from tesis_enasem.central_analysis import groups,FIRST,OTHER,UNKNOWN,CONT,NONE,probability,contrast

def test_other_baseline_does_not_imply_coexistence_destination():
    p=pd.DataFrame({'ano_b':[2015]*5,'tipent_b':[1]*5,
      'pension_propia_k_a':pd.Series([False]*4+[True],dtype='boolean'),
      'pension_propia_k_b':pd.Series([True]*5,dtype='boolean'),
      'apoyo_propio_a':pd.Series([False,True,pd.NA,False,False],dtype='boolean'),
      'apoyo_propio_b':pd.Series([True,False,True,False,False],dtype='boolean')})
    assert groups(p,'K').tolist()==[FIRST,OTHER,UNKNOWN,FIRST,CONT]
    # El sujeto OTHER ya no recibe A; el primero recibe ambas al destino.
    assert not p.apoyo_propio_b.iloc[1] and p.apoyo_propio_b.iloc[0]

def test_no_both_state_only_joint_admissible_window():
    p=pd.DataFrame({'ano_b':[2015,2015,np.nan],'tipent_b':[1,1,np.nan],
      'pension_propia_k_a':pd.Series([False]*3,dtype='boolean'),
      'pension_propia_k_b':pd.Series([False,False,pd.NA],dtype='boolean'),
      'apoyo_propio_a':pd.Series([False]*3,dtype='boolean'),
      'apoyo_propio_b':pd.Series([False,pd.NA,pd.NA],dtype='boolean')})
    assert NONE not in groups(p,'K').tolist()
    p.attrs['joint']=True
    assert groups(p,'K').tolist()==[NONE,'No→No','Ausente; vital desconocido']

def test_probability_keeps_denominator_and_cluster_replicates():
    q=pd.DataFrame({'cunicah_a':[1,1,2,2]});event=pd.Series([True,True,False,False])
    x=probability(q,event)
    assert x['N_denominador']==4 and x['N_incorporados']==2 and x['proporcion']==.5
    assert x['ic95_folio']==[0.,1.]

def test_constant_medians_zero_is_not_a_claim_of_equal_distributions():
    q=pd.DataFrame({'grupo':['a']*30+['b']*30,'value':[1.]*30+[1.]*30,'cunicah_a':np.arange(60)})
    x=contrast(q,('a','b'),'value',replicas=99)
    assert x['estimacion']==0 and x['ic95']==[0.,0.]
    q.loc[0:9,'value']=100
    assert contrast(q,('a','b'),'value',replicas=99)['estimacion']==0


def _common_support_frame():
    from tesis_enasem.central_analysis import FIRST,OTHER
    rows=[]
    for group in [FIRST,OTHER]:
        for sex in ['Hombre','Mujer']:
            for age in ['60–64','65–69']:
                for _ in range(20):
                    rows.append(dict(grupo=group,monto_real=100. if group==FIRST else 200.,educacion_a=3.,sexo_grupo_a=sex,edad_06_a=age,cunicah_a=len(rows)))
    return pd.DataFrame(rows)


def test_common_mixture_preserves_a_constant_median_difference():
    from tesis_enasem.central_supplement import standardize
    q=_common_support_frame();r=standardize(q,'dinero',replicas=99)
    assert r['viable'] and r['N_celdas']==4 and r['N_soporte']==[80,80]
    assert r['estimacion']==-100 and r['ic95']==[-100.,-100.]


def test_missing_covariates_count_against_support_retention():
    from tesis_enasem.central_supplement import standardize
    q=_common_support_frame();q.loc[:49,'educacion_a']=np.nan
    r=standardize(q,'dinero',replicas=99)
    assert not r['viable'] and r['N_antes']==[80,80]
    assert r['cobertura'][0]<.7 and r['estimacion'] is None


def test_export_editorial_rechaza_monto_sin_soporte():
    """Un grupo pequeño no puede producir contraste monetario exportable."""
    import runpy
    import pytest
    from pathlib import Path
    export = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/export_central_analysis.py'))
    with pytest.raises(ValueError, match='soporte'):
        export['interval']({'N': [200, 5], 'estimacion': 1, 'ic95': [0, 2]})
    assert export['interval']({'N': [200, 5], 'estimacion': None, 'ic95': None}) == 'No estimado'


def test_export_editorial_bloque_idempotente(tmp_path):
    """Reexportar una sensibilidad no duplica ni borra el contenido original."""
    import runpy
    from pathlib import Path
    export = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/export_central_analysis.py'))
    path = tmp_path / 'table.tex'
    path.write_text('Cuadro original conservado\n')
    export['block'](path, 'Primera selección')
    export['block'](path, 'Selección revisada')
    assert path.read_text().count('Cuadro original conservado') == 1
    assert 'Primera selección' not in path.read_text()
    assert path.read_text().count('Selección revisada') == 1
