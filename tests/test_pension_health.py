"""Controles sustantivos de orientación, desconocidos, intervalos y composición."""
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu

from tesis_enasem.pension_health import (rank_effect,compare_groups,group_distributions,
    eligible_population,standardize)


def test_rank_effect_matches_u_with_ties_and_direction():
    a=np.array([0,1,1,3]);b=np.array([0,0,2,2,2])
    result=rank_effect(a,b,199,31)
    expected=2*mannwhitneyu(a,b).statistic/(len(a)*len(b))-1
    assert np.isclose(result['efecto'],expected)
    assert rank_effect(b,a,199,31)['efecto']==-result['efecto']
    assert result==rank_effect(a,b,199,31)
    assert -1<=result['ic95_inferior']<=result['ic95_superior']<=1


def test_constant_ranks_do_not_claim_zero_uncertainty():
    result=rank_effect(np.zeros(40),np.zeros(50),99,1)
    assert result['efecto']==0 and result['ic95_inferior'] is None


def test_unknown_receipt_not_negative_and_binary_intervals():
    frame=pd.DataFrame({'diabetes':[1]*30+[0]*30+[1]*20,
        'pension_propia_k':pd.array([True]*30+[False]*30+[None]*20,dtype='boolean')})
    result=compare_groups(frame,'diabetes','pension_propia_k')
    assert result['N_recepcion_ND']==20 and result['N_pares_validos']==60
    assert result['efecto']==100 and result['ic95_superior']<=100
    rows=group_distributions(frame,'diabetes','pension_propia_k')
    assert next(x for x in rows if x['grupo']=='Desconocido')['N_elegible_grupo']==20


def test_missing_health_does_not_become_zero():
    frame=pd.DataFrame({'n_aivd':[0]*30+[2]*30+[np.nan]*10,
        'pension_propia_k':[True]*30+[False]*40})
    r=compare_groups(frame,'n_aivd','pension_propia_k',99)
    assert r['N_salud_no_valido']==10 and r['N_no_valido']==30
    assert r['efecto']==-1


def test_absent_instrument_and_proxy_eligibility():
    frame=pd.DataFrame({'ano':[2001]*3+[2015]*3,'tipent':[1,2,3,1,2,3]})
    rules={'serial7':{'2001':{'modalidades':[]},'2015':{'modalidades':[1,2]}}}
    assert eligible_population(frame,'serial7',2001,rules).empty
    assert len(eligible_population(frame,'serial7',2015,rules))==2


def test_small_group_suppresses_effect_not_descriptives():
    frame=pd.DataFrame({'n_mov':[1]*20+[2]*40,'pension_propia_k':[True]*20+[False]*40})
    r=compare_groups(frame,'n_mov','pension_propia_k')
    assert r['efecto'] is None and r['si']['mediana']==1


def test_standardization_handles_composition_reversal_and_common_support():
    rows=[]
    for age,receipt,n,count in [('60–69',True,100,10),('60–69',False,900,180),
                                ('80+',True,900,720),('80+',False,100,90)]:
        rows.extend({'edad_salud':age,'sexo_grupo':'Mujer','educacion_ajuste':'0–5',
                     'modalidad_ajuste':'Directa','pension_propia_k':receipt,
                     'diabetes':int(i<count)} for i in range(n))
    r=standardize(pd.DataFrame(rows),'diabetes')
    assert r['N_soporte']==2000 and r['N_fuera_soporte']==0
    assert r['diferencia_cruda_mismo_soporte']>0
    assert np.isclose(r['diferencia_estandarizada'],-10)
    assert r['ic95_inferior']<r['diferencia_estandarizada']<r['ic95_superior']
