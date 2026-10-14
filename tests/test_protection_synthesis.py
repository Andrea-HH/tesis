"""Errores interpretativos que debe prevenir la síntesis06/07, con datos sintéticos."""

from tesis_enasem.protection_synthesis import gap_change, ratio


def test_signed_gap_reversal_is_not_necessarily_convergence():
    change=gap_change(5.92,-9.13)
    assert change['cambio_firmado']<0
    assert change['cambio_magnitud']>0
    assert change['cambia_signo'] and change['lectura']=='Se amplía'
    assert gap_change(12.43,9.24)['lectura']=='Se estrecha'


def test_relative_inequality_is_unidentified_when_reference_is_zero_or_missing():
    assert ratio(1000,0) is None
    assert ratio(None,1000) is None
    assert ratio(0,1000)==0
