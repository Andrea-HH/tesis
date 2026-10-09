import pandas as pd
from tesis_enasem.outcomes import classify_relative_vulnerability, label_by_wave
from tesis_enasem.weights import weighted_quantile


def test_missing_wealth_stays_missing():
    data=pd.DataFrame({'imp_neto':[-1,0,10,100,None]})
    result=classify_relative_vulnerability(data)
    assert pd.isna(result.iloc[-1])
    assert result.iloc[0]==1 and result.iloc[-2]==0


def test_wave_specific_cutoffs():
    data=pd.DataFrame({'ano':[2001]*4+[2003]*4,'imp_neto':[1,2,3,4,100,200,300,400]})
    res=label_by_wave(data)
    assert res['vulnerable_q1'].tolist()==[1,0,0,0,1,0,0,0]


def test_weighted_quantiles():
    assert weighted_quantile([1,2,3],[.5],sample_weight=[1,1,1])[0]==2
