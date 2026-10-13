"""Pruebas sintéticas: universo documental, desconocidos y años no imputados."""
import pandas as pd
import pytest

from tesis_enasem.program_catalog import parse_inventory, parse_municipal, state_name, documentary_coverage


def test_aliases_do_not_drop_veracruz_or_historical_df():
    assert state_name('Veracruz Ignacio de la Llave') == 'Veracruz'
    assert state_name('Distrito Federal') == 'Ciudad de México'
    assert state_name('desconocido') is None


def test_budget_is_not_benefit_or_eligibility_and_blank_not_zero():
    frame=pd.DataFrame([['Título',None,None,None],
        ['Entidad federativa','1. Nombre de la intervención','19. Presupuesto original','14. Etapa de vida 1'],
        ['Jalisco','Apoyo a adultos mayores',1000000,'Adultos mayores'],
        ['Jalisco','Desarrollo comunitario',0,'No Disponible']])
    rows=parse_inventory(frame,'s',2018,'nacional','https://oficial.test','estatal')
    assert len(rows)==2 and rows[0]['monto_individual_validado_mxn'] is None
    assert rows[0]['edad_elegibilidad_validada'] is None
    assert rows[0]['anios_operacion_comprobados_inventario']==[2018]
    assert rows[1]['poblacion_objetivo_categorias']==['No Disponible']
    assert not rows[0]['tipo_pension_validado']
    cov=documentary_coverage(rows)
    assert next(r for r in cov if r['entidad']=='Puebla')['estado'].startswith('sin_registros')


def test_unknown_state_aborts_instead_of_silent_omission():
    frame=pd.DataFrame([['Entidad federativa','1. Nombre de la intervención'],['Entidad inédita','Pensión']])
    with pytest.raises(ValueError,match='Entidad no reconocida'):
        parse_inventory(frame,'s',2021,'n','https://oficial.test','estatal')


def test_municipal_grouped_rows_preserve_source_period_not_operation():
    frame=pd.DataFrame([['Datos',None,None],
        ['Nombre del Municipio','Nombre del Programa, acción o intervención Municipal','Institución Responsable'],
        ['Municipio A',None,None],[None,'Apoyo alimentario','DIF'],[None,'Pensión',None],
        ['Municipio B',None,None],[None,'Actividad',None]])
    rows=parse_municipal(frame,{'periodo':'2014-2015','id':'m','url':'https://oficial.test'},'INTERVENCIONES','Jalisco')
    assert len(rows)==3 and [r['municipio'] for r in rows]==['Municipio A','Municipio A','Municipio B']
    assert all(r['anios_operacion_comprobados_inventario']==[] for r in rows)
    assert all(r['monto_individual_validado_mxn'] is None for r in rows)
    assert all(r['tipo_pension_validado'] is None for r in rows)


def test_future_federal_years_excluded_without_changing_creation():
    frame=pd.DataFrame([['Ciclo','Nombre del programa','Año de Inicio'],[2021,'P',2019],[2023,'P',2019]])
    rows=parse_inventory(frame,'f',None,'h','https://oficial.test','federal')
    assert len(rows)==1 and rows[0]['inicio_reportado_inventario']==[2019]
    assert rows[0]['anio_inicio_validado_reglas'] is None
