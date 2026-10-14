"""Casos sintéticos07: periodos, geografía, faltantes y cambio de unidad."""

import numpy as np
import pandas as pd
import pytest

from tesis_enasem.monetary_policy import constant_pesos, pricing, rural_urban, summarize


def test_deflation_preserves_zero_and_missing():
    x=pd.Series([100.,0.,np.nan]); i=pd.Series([50.,100.,50.])
    y=constant_pesos(x,i,150)
    assert y.iloc[0]==300 and y.iloc[1]==0 and pd.isna(y.iloc[2])
    with pytest.raises(ValueError):constant_pesos(x,pd.Series([0.,100.,50.]),150)


def test_geography_does_not_call_all_small_localities_rural():
    codes=pd.Series([1,2,3,4,99,4])
    r=rural_urban(codes,pd.Series([True]*6),pd.Series([False]*5+[True]))
    assert r.tolist()==['Urbana','Urbana','Urbana','Rural','Indeterminado','Indeterminado']


def test_pricing_uses_actual_interview_year_and_twelve_prior_months():
    periods=pd.period_range('2000-01','2026-09',freq='M').astype(str)
    indices=pd.DataFrame({'inpc':np.arange(len(periods))+100.},index=periods)
    lines=pd.DataFrame({'lpi_rural':1000.,'lpi_urbana':2000.},index=periods)
    f=pd.DataFrame({'ano':[2012,2012],'a_o_ent':[2012,2013],'mes_ent':[12,2],
                    'localidad_lpi':['Rural','Indeterminado']})
    out=pricing(f,indices,lines)
    assert out.iloc[1].inpc_original==indices.loc['2012-01':'2012-12','inpc'].mean()
    months=pd.period_range('2012-02','2013-01',freq='M').astype(str)
    assert out.iloc[1].factor_12m==pytest.approx(146.075/indices.loc[months,'inpc'].mean())
    assert pd.isna(out.iloc[1].lpi_asignada) and out.iloc[0].lpi_asignada==1000


def test_ratio_to_line_invariant_when_both_use_same_index():
    x=pd.Series([580.,1550.]); line=pd.Series([2000.,3000.]);i=pd.Series([85.,107.])
    pd.testing.assert_series_equal(x/line,constant_pesos(x,i,146.075)/constant_pesos(line,i,146.075))


def test_nd_is_not_a_zero_in_quantiles():
    z=summarize(pd.Series([0.,100.,200.,np.nan]))
    assert z['N']==3 and z['N_cero']==1 and z['mediana']==100
    assert summarize(pd.Series([np.nan]))['mediana'] is None
