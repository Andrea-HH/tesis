"""Calidad y protección10 con datos sintéticos, sin importes o IDs originales."""
import numpy as np
import pandas as pd
import pytest
from tesis_enasem.disclosure_quality import (
    assess_n,complementary_suppression,protect_rows,redact_financial_paragraphs)
from tesis_enasem.statistical_quality import (
    numbers_in_count,select_chain,precision_state,standardization)


def test_threshold_does_not_certify_population_inference():
    assert not assess_n(9)['divulgar_monetario']
    assert not assess_n(500,ci=[1,2])['soporte_interpretativo']
    assert not assess_n(500,ci=[1,2],reviewed=True)['inferencia_nacional']
    assert assess_n(10)['revision']=='10–29'


def test_null_interval_is_not_a_rejection_rule():
    status=precision_state([25,25],[-2,2],100,0)
    assert 'No estimable' not in status
    assert 'Exploratorio' in status
    assert 'equivalencia' in precision_state([25,25],[0,0],100,0)
    assert 'No estimable' in precision_state([25,25],[-200,200],100,0)


def test_derived_values_of_a_small_branch_are_removed_together():
    rows,log=protect_rows(['Vía','N P/C','Mediana P','Mediana C','Diferencia real'],
        [['K ficticio','100/1','100','12','88']],context='Monto real')
    assert rows==[['K ficticio','Reservado','Reservado','Reservado','Reservado']]
    assert log and '12' not in str(rows) and '88' not in str(rows)


def test_missing_amount_is_not_the_sample_size():
    rows,log=protect_rows(['Grupo','N válido','N sin monto','Mediana'],
        [['Ficticio','100','1','300']],context='Monto')
    assert not log and rows[0][-1]=='300'


def test_complementary_suppression_prevents_single_unknown_per_margin():
    result=complementary_suppression(np.array([[1,100],[50,200]]))
    mask=np.array(result['suppressed'])
    assert mask.sum()>1
    assert not any(np.sum(mask,axis=0)==1) and not any(np.sum(mask,axis=1)==1)
    assert np.array(result['primary']).sum()==1


def test_no_donor_requires_retiring_a_margin():
    result=complementary_suppression(np.array([[1,0]]))
    assert result['retire_margins']


def test_flow_counts_unique_people_and_exclusion_steps():
    q=pd.DataFrame({'x':[1,1,2]},index=['a','b','c'])
    rows=select_chain(q,[('Elegible',pd.Series([True,True,False],index=q.index)),
                          ('Válido',pd.Series([True,False,True],index=q.index))])
    assert [x['N_observaciones'] for x in rows]==[2,1]
    assert [x['N_excluidas_en_paso'] for x in rows]==[1,1]
    assert rows[-1]['N_personas_unicas']==1


def test_dates_are_not_ids_but_actual_id_pattern_is_rejected():
    text,_=redact_financial_paragraphs('Regla publicada febrero2021:65 años, contexto normativo.')
    assert '2021: 65' in text
    with pytest.raises(ValueError,match='identificador'):
        redact_financial_paragraphs('Participante 123456:1')


def test_count_parser_preserves_paired_sample_sizes():
    assert numbers_in_count('1,060/373')==[1060,373]


@pytest.mark.parametrize("notation", [r"N=1\,756/1\,223", "N=1,756/1,223", "N=1756/1223", "N=1\u202f756/1\u00a0223"])
def test_large_paired_samples_not_redacted(notation):
    from tesis_enasem.disclosure_quality import paragraph_sample_numbers
    assert paragraph_sample_numbers(notation)==[1756,1223]
    text="Monto real y cuantiles; "+notation+" pares íntegros."
    assert redact_financial_paragraphs(text)==(text,0)


@pytest.mark.parametrize("notation", ["N=1", "N=3", "N=5", r"N=1\,756/5"])
def test_actual_small_monetary_samples_still_redacted(notation):
    text,count=redact_financial_paragraphs("Monto real, mediana; "+notation+" personas.")
    assert count==1 and "retirado" in text


def test_legacy_export_guard_prevents_overwrite():
    from tesis_enasem.release_guard import block_legacy_export
    with pytest.raises(SystemExit,match='bloqueado'):
        block_legacy_export()


def test_real_family_gate_checks_complementary_margins():
    from tesis_enasem.release_audit import audit_families
    rows=[dict(via='K',origen=2001,destino=2003,dimension='sexo',grupo=g,categoria=c,N_monto=n)
          for g,c,n in [('P','H',100),('P','M',110),('C','H',11),('C','M',1)]]
    result=audit_families({'embudos_contrastes':rows})
    assert len(result)==1 and result[0]['primarias']==1
    assert result[0]['complementarias']>0


def test_protected_row_is_idempotent():
    row=['Incorporación con otra vía ND','Reservado','Reservado']
    result,log=protect_rows(['Grupo','N','Mediana real'],[row],context='Monto')
    assert result==[row] and not log


def test_median_plus_difference_cannot_survive_a_protected_branch():
    from tesis_enasem.release_audit import check_related_monetary_rows
    table={'title':'Monto real por protección','headers':['Grupo','N P/C','Mediana P','Mediana C','Diferencia [IC95]'],
           'rows':[['Ejemplo','100/<10','100','Reservado','88 [80;90]']]}
    with pytest.raises(AssertionError,match='reconstructivo'):
        check_related_monetary_rows([table])
    table['rows']=[['Ejemplo','Sin soporte','Reservado','Reservado','No estimable']]
    assert check_related_monetary_rows([table])['recuperacion_por_contraste_mas_mediana'] is False
