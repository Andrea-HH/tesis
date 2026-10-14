"""Casos críticos08: ND, sums incompletas, concepto y puente de medianas."""

import numpy as np
import pandas as pd
import pytest

from tesis_enasem.benefit_transitions import (
    classify, event_measures, pair_frame, paired_summary, standardize, weighted_quantiles,
    frequency_quantiles, median_order_interval, precision_bootstrap, _precision_pool,
    missing_median_bounds,
)


def test_states_preserve_death_absence_proxy_and_unknown():
    p=pd.DataFrame({'ano_b':[2015,2015,2015,2015,np.nan,2015,2015,2015],
        'tipent_b':[1,1,1,1,np.nan,5,3,1],
        'pension_propia_k_a':pd.Series([False,False,True,True,True,True,False,pd.NA],dtype='boolean'),
        'pension_propia_k_b':pd.Series([False,True,True,False,pd.NA,pd.NA,True,True],dtype='boolean')})
    s=classify(p,'K')
    assert s.tolist()==['No→No','No→Sí','Sí→Sí','Sí→No','Ausente; vital desconocido',
                        'Fallecido registrado','Sustituto vivo; fuera del principal','Recepción ND en alguna visita']
    assert classify(p,'K',True).iloc[6]=='No→Sí'
    assert classify(p,'K',True).iloc[5]=='Fallecido registrado'


def test_incomplete_captured_events_do_not_become_a_personal_sum():
    e=pd.DataFrame({'id':['a','a','b','b','c'],'ano':[2012]*5,
        'monto_mensual_observado':[100,np.nan,100,50,0],
        'tipo':[1]*5,'instituciones_codigos':[[1],[1],[1],[1],[2]],
        'programa_publico_agrupado':[False]*5,'seguridad_social_identificada':[True]*5})
    r=event_measures(e,'K').set_index('id')
    assert pd.isna(r.loc['a','monto_completo_K'])
    assert not r.loc['a','todos_capturados_K']
    assert r.loc['b','monto_completo_K']==150
    assert r.loc['c','monto_completo_K']==0
    assert pd.isna(r.loc['b','firma_seguridad_K'])
    assert r.loc['c','firma_seguridad_K']=='1:2'


def test_prior_death_conflict_is_separate_and_does_not_invent_a_death():
    p=pd.DataFrame({'ano_b':[2018,2018],'tipent_b':[1,5],
        'apoyo_propio_a':pd.Series([True,True],dtype='boolean'),
        'apoyo_propio_b':pd.Series([True,pd.NA],dtype='boolean'),
        'vital_discordante_a':[True,False],'vital_discordante_b':[True,False]})
    assert classify(p,'A').tolist()==['Conflicto de estado vital registrado','Fallecido registrado']
    assert classify(p,'A',honor_conflicts=False).iloc[0]=='Sí→Sí'


def test_individual_changes_and_difference_of_medians_are_not_equivalent():
    q=pd.DataFrame({'monto_completo_K_a':[10.,20.,100.],
        'monto_completo_K_b':[100.,15.,20.],
        'factor_a':[2.]*3,'factor_b':[1.]*3,
        'inpc_original_a':[50.]*3,'inpc_original_b':[100.]*3,
        'a_o_ent_a':[2012]*3,'a_o_ent_b':[2015]*3,'mes_ent_a':[6]*3,'mes_ent_b':[6]*3,
        'factor_12m_a':[2.]*3,'factor_12m_b':[1.]*3,
        'factor_ano_entrevista_a':[2.]*3,'factor_ano_entrevista_b':[1.]*3})
    r=paired_summary(q,'K')
    assert r['diferencia_medianas_real']==-20
    assert r['cambio_individual_real']['mediana']==-25
    assert r['puente_medianas']['termino_precio']==-20
    assert r['puente_medianas']['termino_nominal']==0
    assert r['identidad_contable']['suma_medias']==pytest.approx(r['identidad_contable']['media_cambio'])
    assert r['N_real_baja']==2 and r['N_real_sube']==1


def test_weighted_median_uses_distribution_not_average_of_group_medians():
    values=pd.Series([10.,100.,np.nan]);weights=pd.Series([.7,.3,1.])
    r=weighted_quantiles(values,weights)
    assert r['mediana']==10 and r['q75']==100
    assert weighted_quantiles(values,pd.Series([0.,0.,0.]))['mediana'] is None


def test_sparse_adjustment_is_blocked_and_unknown_schooling_is_not_filled():
    q=pd.DataFrame({'patron':['No→Sí','Sí→Sí','No→Sí'],
        'monto_completo_K_b':[100.,200.,150.],'factor_b':[1.]*3,
        'educacion_a':[0.,6.,np.nan],'sexo_grupo_a':['Hombre']*3,
        'edad_06_a':['60–64']*3})
    r=standardize(q,'K')
    assert not r['viable'] and r['N_en_soporte']=={'No→Sí':0,'Sí→Sí':0}
    assert r['N_covariables_ND']['No→Sí']==1


def test_duplicate_person_in_destination_cannot_multiply_a_cohort():
    f=pd.DataFrame({'id':['a','a','a'],'ano':[2012,2015,2015],
        'universo_60':[True]*3,'directa':[True]*3})
    with pytest.raises(AssertionError):pair_frame(f,2012,2015)


def test_frequency_quantiles_match_expanded_sample_and_even_medians():
    values=np.array([30.,10.,10.,100.])
    counts=np.array([[1,2,0,1],[0,1,2,2],[0,0,0,0]])
    got=frequency_quantiles(values,counts)
    for i,row in enumerate(counts[:2]):
        expected=np.quantile(np.repeat(values,row),[.25,.5,.75])
        np.testing.assert_allclose(got[i],expected)
    assert np.isnan(got[2]).all()
    with pytest.raises(ValueError):frequency_quantiles(values,np.array([[1.,1.,-1.,1.]]))
    with pytest.raises(ValueError):frequency_quantiles(values,np.array([[.2,.8,0.,0.]]))


def test_inverse_cdf_quantile_does_not_average_even_middle_values():
    values=np.array([10.,100.])
    assert frequency_quantiles(values,np.array([[1,1]]))[0,1]==55
    assert frequency_quantiles(values,np.array([[.5,.5]]),inverse_cdf=True)[0,1]==10


def test_order_interval_has_binomial_coverage_and_keeps_open_small_sample():
    result=median_order_interval(np.arange(1.,21.))
    assert result['inferior']==6 and result['superior']==15
    assert result['cobertura_minima_binomial']>=.95
    assert median_order_interval(np.array([1.]))['inferior'] is None
    tied=median_order_interval(np.full(101,580.))
    assert tied['inferior']==tied['superior']==580
    with pytest.raises(ValueError):median_order_interval(np.array([np.nan]))


def test_missing_median_bounds_are_external_and_do_not_fill_person_records():
    values=np.array([10.,20.,30.,40.,50.]);before=values.copy()
    bounded=missing_median_bounds(values,2,nonnegative=True)
    assert bounded['inferior']==20 and bounded['superior']==40
    unrestricted=missing_median_bounds(values,7)
    assert unrestricted['inferior'] is None and unrestricted['superior'] is None
    assert missing_median_bounds(values,0)['inferior']==30
    np.testing.assert_array_equal(values,before)


def test_bootstrap_preserves_same_person_and_overlap_across_visits():
    # Dos visitas idénticas: cualquier réplica por ID debe tener diferencia cero.
    frame=pd.DataFrame({'folio_precision':[10,20,30,40]*2},index=['a','b','c','d']*2)
    values=np.array([0.,1.,1.,0.]*2)
    first=np.arange(8)<4
    pools={'a':_precision_pool(values,first),'b':_precision_pool(values,~first)}
    recipes=[{'id':'change','op':'mean_diff','left':'b','right':'a'}]
    r=precision_bootstrap(frame,pools,recipes,replicas=199,seed=4)
    assert r['N_personas']==r['N_clusters']==4 and r['max_filas_cluster']==2
    assert r['estimaciones'][0]['ic95']==[0.,0.]
    assert r==precision_bootstrap(frame,pools,recipes,replicas=199,seed=4)


def test_folio_sensitivity_keeps_both_people_and_repeated_visits_together():
    frame=pd.DataFrame({'folio_precision':[10,10,20,20,30,30]*2},index=list('abcdef')*2)
    values=np.array([0.,1.,0.,1.,0.,1.]*2)
    pool=_precision_pool(values,np.ones(12,dtype=bool))
    r=precision_bootstrap(frame,{'v':pool},[{'id':'mean','op':'mean','left':'v'}],cluster='folio',replicas=199)
    assert r['N_clusters']==3 and r['max_filas_cluster']==4
    assert r['estimaciones'][0]['ic95']==[.5,.5]
    # Missing values are omitted, never a zero receipt/amount.
    assert _precision_pool(np.array([10.,np.nan,30.]),np.ones(3,dtype=bool))['diagnostics']['N']==2


def test_bootstrap_fixed_support_reestimates_composition_with_overlap():
    frame=pd.DataFrame({'folio_precision':np.arange(8)},index=list('abcdefgh'))
    adjustment={'N_strata':2,'parts':{
        'new':{'positions':np.array([0,1,2,3]),'strata':np.array([0,0,1,1]),'nominal':np.array([10.,10.,100.,100.]),'real':np.array([20.,20.,200.,200.])},
        'cont':{'positions':np.array([4,5,6,7]),'strata':np.array([0,0,1,1]),'nominal':np.array([10.,10.,100.,100.]),'real':np.array([20.,20.,200.,200.])}}}
    # Idéntica distribución en cada estrato: reponderar a la misma mezcla debe
    # conservar contraste0 en réplicas con presencia en ambos grupos/celdas.
    # Aumentar multiplicidades originales evita celdas vacías en este test sintético.
    parts=adjustment['parts']
    frame=pd.concat([frame]*20,ignore_index=True)
    frame.index=[str(x) for x in range(len(frame))]
    for group,part in parts.items():
        base=part['positions'].copy()
        part['positions']=np.concatenate([base+8*j for j in range(20)])
        for key in ['strata','nominal','real']:part[key]=np.tile(part[key],20)
    recipes=[{'id':'adjusted','op':'quantile_diff','left':'std_new_real','right':'std_cont_real'}]
    r=precision_bootstrap(frame,{},recipes,adjustment=adjustment,replicas=199,seed=3)
    assert r['estimaciones'][0]['ic95']==[0.,0.]
    assert r['ajuste_diagnostico']['N_replicas_celda_vacia']==0

