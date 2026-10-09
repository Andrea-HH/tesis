import pandas as pd
from pandas.io.stata import StataMissingValue
from tesis_enasem.missing import numeric_enasem, missing_audit


def test_special_missing_code():
    val=StataMissingValue(101)
    s=pd.Series([1.0,val,None])
    result=numeric_enasem(s)
    assert result.iloc[0]==1 and result.isna().sum()==2
    assert missing_audit(pd.DataFrame({'x':s})).n.sum()==2
