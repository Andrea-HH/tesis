"""Casos sintéticos de selección, ND, titularidad y seguimiento pensionario."""
import numpy as np
import pandas as pd
import pytest

from tesis_enasem.pension_exploration import (PopulationSpec, ownership_category,
    age_groups, categorical_table, continuous_table, stratified_transitions, institutional_people)


def test_selection_preserves_input_and_keys():
    frame=pd.DataFrame({'id':['1:1','1:2','1:1'], 'ronda':[1,1,2],
                        'edad':[59,60,np.nan], 'sexo':[1,2,1],'tipent':[1,3,5]})
    original=frame.copy(deep=True)
    assert PopulationSpec().select(frame).id.tolist()==['1:2']
    assert len(PopulationSpec(None).select(frame))==3
    assert len(PopulationSpec(60,(1,2)).select(frame))==0
    pd.testing.assert_frame_equal(frame,original)
    with pytest.raises(ValueError):PopulationSpec().select(pd.concat([frame,frame.iloc[[1]]]))


def test_ownership_requires_two_explicit_states():
    assert ownership_category(True,False)=='Solo propia'
    assert ownership_category(False,True)=='Solo cónyuge'
    assert ownership_category(True,True)=='Ambas'
    assert ownership_category(False,False)=='Ambas negativas K'
    assert ownership_category(True,None)=='Desconocido'
    assert ownership_category(pd.NA,False)=='Desconocido'


def test_quinquennial_boundaries_and_missing():
    assert age_groups(pd.Series([59,60,64,65,69,70,74,75,79,80,np.nan])).tolist()==[
        'Desconocido','60–64','60–64','65–69','65–69','70–74','70–74','75–79','75–79','80+','Desconocido']


def test_rates_are_distinct_from_composition_and_unknown_not_zero():
    frame=pd.DataFrame({'id':['a','b','c','d'], 'tipent':[1]*4,
                        'g':['M','M','H','H'],'state':['Sí','Desconocido','Sí','No']})
    rows=categorical_table(frame,'state',['g'])
    m=next(r for r in rows if r['g']=='M' and r['categoria']=='Sí')
    assert m['pct_total']==50 and m['pct_validos']==100 and m['pct_composicion_categoria']==50
    assert m['N_desconocido']==1


def test_three_dimensional_continuous_groups_preserve_negative_wealth():
    f=pd.DataFrame({'id':['a','b','c'], 'p':['Sí','Sí','No'],'edu':['0','0','6'],'wealth':[-2,0,20]})
    rows=continuous_table(f,'wealth',['p','edu'])
    r=next(x for x in rows if x['p']=='Sí')
    assert r['mediana']==-1 and r['N_negativos']==1 and r['N_ceros']==1
    assert sum(x['N_total'] for x in rows)==3


def test_longitudinal_death_absence_reappearance_and_lower_age_not_receipt_loss():
    f=pd.DataFrame({'id':['a','b','c','a','c','b'], 'ronda':[1,1,1,2,2,3],
        'ano':[2001,2001,2001,2003,2003,2012],'edad':[65,65,65,np.nan,59,76],
        'sexo':[1]*6,'tipent':[1,1,1,5,1,1],'P':['Sí','No','No','Sí','Sí','Sí'],'g':['X']*6})
    rows=stratified_transitions(f,2001,2003,'P','g',True)
    assert sum(x['N'] for x in rows)==3
    assert next(x for x in rows if x['destino']=='Sobre fallecido')['evento']=='Estado no interpretable'
    assert next(x for x in rows if x['destino']=='Ausente con reaparición')['N']==1
    assert sum(x['N'] for x in rows if x['evento']=='Inicio observado')==1
    other=stratified_transitions(f,2001,2003,'P','g',False)
    assert all(x['evento'].startswith('Cambio de instrumento') for x in other)


def test_institution_multiple_slots_counts_people_once_not_money():
    e=pd.DataFrame({'beneficiario_id':['a','a','a','b'],'ano':[2021]*4,
                    'instituciones_codigos':[[1,2],[1,2],[1],[1]]})
    p=pd.DataFrame({'id':['a','b','c'],'ano':[2021]*3,'tipent':[1]*3,'sex':['M','M','H']})
    r=institutional_people(e,p)
    assert {x['institucion_codigo']:x['N_personas'] for x in r}=={1:2,2:1}
    assert all(x['N_receptoras_institucion_identificada']==2 for x in r)
    assert not any('monto' in k for x in r for k in x)
