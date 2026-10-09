import pandas as pd
import pytest
from tesis_enasem.panel import make_person_id, followup_pairs, balanced_panel_ids


def test_make_id_and_balanced():
    data=pd.DataFrame({'cunicah':[1.0,1.0,2.0,2.0], 'np':[10,10,1,1], 'ronda':[1,2,1,2]})
    data['id']=make_person_id(data)
    assert data['id'].tolist()==['1_10','1_10','2_1','2_1']
    assert len(balanced_panel_ids(data,n_rounds=2))==2


def test_temporal_pairs_refuse_gaps_and_duplicate():
    data=pd.DataFrame({'id':['a','a','a','b'],'ronda':[1,2,4,1],'vulnerable_q1':[0,1,0,1]})
    paired=followup_pairs(data,'vulnerable_q1')
    assert paired.loc[paired.ronda.eq(1)&paired.id.eq('a'),'outcome_futuro'].iloc[0]==1
    assert pd.isna(paired.loc[paired.ronda.eq(2),'outcome_futuro'].iloc[0])
    with pytest.raises(ValueError):
        followup_pairs(pd.concat([data,data.iloc[[0]]]),'vulnerable_q1')
