import pandas as pd
import numpy as np
from tesis_enasem.transforms import asinh_transform


def test_asinh_preserves_sign_and_zero():
    result=asinh_transform(pd.Series([-3,0,3,None]))
    assert result.iloc[0]<0 and result.iloc[1]==0 and result.iloc[2]>0
    assert np.isnan(result.iloc[3])
