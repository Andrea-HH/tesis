"""Beneficiarios sintéticos: ninguna prueba requiere microdatos ENASEM."""
import pytest

from tesis_enasem.pension_ownership import (wave_contract, orient_person, receipt,
                                          pension_events, unique_events, tri_or, partner_pointer_confirmed)


def modern_pair(year=2021):
    suffix = f"_{year%100}"
    row = {"np": 20, "tipent": 1}
    ind = {"key_21": 2, "k45d"+suffix: 10, "k52a_1"+suffix: 20, "k52a"+suffix: 2}
    hh = dict(ind)
    return row, ind, hh


def test_spouse_section_is_person_when_partner_is_financial_respondent():
    p,i,h = modern_pair()
    c = wave_contract(2021)
    h.update({g:2 for g in c.own_gates})
    h.update({g:2 for g in c.spouse_gates})
    h['k64d_21'] = 1
    role,_ = orient_person(p,i,h,c)
    assert role == 2
    assert receipt(h,c.spouse_gates) is True
    assert receipt(h,c.own_gates) is False
    e = pension_events(h,c,role)
    assert len(e) == 1 and e[0]['beneficiario_viudez']
    # La pensión no se atribuye a NP10 ni al asegurado fallecido.
    assert e[0]['rama'] == 2 and e[0]['tipo'] == 2


@pytest.mark.parametrize('year',[2018,2021])
def test_discordant_or_double_pointers_keep_unknown(year):
    p,i,h = modern_pair(year)
    c = wave_contract(year)
    h[f'k52a_1_{year%100}'] = 11
    assert orient_person(p,i,h,c)[0] is None
    h[f'k52a_1_{year%100}'] = h[f'k45d_{year%100}'] = 20
    assert orient_person(p,i,h,c)[0] is None


def test_dead_person_does_not_acquire_partners_pension():
    p,i,h = modern_pair()
    p['tipent'] = 5
    assert orient_person(p,i,h,wave_contract(2021))[0] is None


def test_negative_dk_and_missing_do_not_become_negative_receipt():
    c = wave_contract(2012)
    h = dict.fromkeys(c.own_gates,2)
    assert receipt(h,c.own_gates) is False
    h[c.own_gates[-1]] = 9
    assert receipt(h,c.own_gates) is None
    h[c.own_gates[0]] = 1
    assert receipt(h,c.own_gates) is True
    assert tri_or(False,None) is None


def test_amount_response_codes_are_specific_not_global_eight_nine():
    c = wave_contract(2021)
    h = {'k58a_21':1,'k61_1_1_21':9,'k59_1_1_21':1,'k61_1_2_21':9999999}
    events = pension_events(h,c,1)
    assert events[0]['monto_mensual_observado'] == 9
    assert events[1]['monto_mensual_observado'] is None
    assert events[1]['monto_codigo_original'] == 9999999


@pytest.mark.parametrize('year,gate,amount',[(2001,'k55a','k58_1'),(2003,'k58a','k61a')])
def test_early_amounts_use_six_digit_missing_codes(year,gate,amount):
    e = pension_events({gate:1,amount:999999},wave_contract(year),1)
    assert e[0]['monto_mensual_observado'] is None
    assert e[0]['monto_codigo_original'] == 999999


def test_multiple_institutions_do_not_multiply_a_single_amount():
    c = wave_contract(2012)
    e = pension_events({'k58a_12':1,'k59_1_01_12':1,'k59_1_02_12':1,'k61_1_12':2000},c,1)
    assert len(e) == 1 and e[0]['monto_mensual_observado'] == 2000
    assert 'sin_correspondencia_univoca' in e[0]['alcance_institucion']


def test_same_payment_replicated_in_person_rows_counts_once_only():
    e = {'ano':2021,'hogar_fuente':'HH','fuente':'F10','version':'original','rama':1,
         'tipo':1,'slot':1,'monto':2000}
    assert len(unique_events([e,e])) == 1
    spouse = dict(e,rama=2)
    assert len(unique_events([e,spouse])) == 2  # iguales pero dos beneficiarios
    second = dict(e,slot=2)
    assert len(unique_events([e,second])) == 2  # dos pensiones del mismo beneficiario
    with pytest.raises(ValueError):
        unique_events([e,dict(e,monto=3000)])


def test_original_and_imputed_versions_never_collapse_into_one_payment():
    e = {'ano':2021,'hogar_fuente':'HH','fuente':'F10','version':'original','rama':1,
         'tipo':1,'slot':1,'monto':2000}
    assert len(unique_events([e,dict(e,version='imputada')])) == 2
    # La agregación debe seleccionar una versión explícita, no sumar ambas.


def test_early_external_informant_does_not_trigger_invented_interview_order():
    p={'np':20,'tipent':3}
    i={'key12':2}
    h={'k96a_12':103}
    assert orient_person(p,i,h,wave_contract(2012))[0] is None
    h['k96a_12']=10
    assert orient_person(p,i,h,wave_contract(2012))[0] == 2
    i['key12']=1
    assert orient_person(p,i,h,wave_contract(2012))[0] is None


def test_future_survivor_expectation_is_not_current_receipt():
    c=wave_contract(2021)
    assert pension_events({'k69_1_1_21':1,'k70_21':1,'k77_21':1},c,2) == []


def test_own_receipt_does_not_validate_other_discordant_partner_pointer():
    p,i,h=modern_pair()
    h['k45d_21']=11
    assert orient_person(p,i,h,wave_contract(2021))[0] == 2
    assert partner_pointer_confirmed(i,h,wave_contract(2021),2)[0] is False
    h['k45d_21']=10
    assert partner_pointer_confirmed(i,h,wave_contract(2021),2)[0] is True
