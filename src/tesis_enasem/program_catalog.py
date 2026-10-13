"""Inventario documental: una fila por intervención y ejercicio, sin beneficiarios."""
from __future__ import annotations

import re
import unicodedata
from typing import Any

import pandas as pd


STATES = ('Aguascalientes', 'Baja California', 'Baja California Sur', 'Campeche',
          'Coahuila', 'Colima', 'Chiapas', 'Chihuahua', 'Ciudad de México', 'Durango',
          'Guanajuato', 'Guerrero', 'Hidalgo', 'Jalisco', 'Estado de México', 'Michoacán',
          'Morelos', 'Nayarit', 'Nuevo León', 'Oaxaca', 'Puebla', 'Querétaro',
          'Quintana Roo', 'San Luis Potosí', 'Sinaloa', 'Sonora', 'Tabasco',
          'Tamaulipas', 'Tlaxcala', 'Veracruz', 'Yucatán', 'Zacatecas')


def normalized(value: object) -> str:
    """Normalización de búsqueda; el texto original permanece en cada registro."""
    text = unicodedata.normalize('NFKD', str(value))
    return re.sub(r'\s+', ' ', ''.join(c for c in text if not unicodedata.combining(c))).strip().lower()


def state_name(value: object) -> str | None:
    """Alias territoriales históricos explícitos, nunca inferencia de residencia."""
    key = normalized(value)
    aliases = {normalized(s): s for s in STATES}
    aliases.update({'distrito federal': 'Ciudad de México', 'mexico': 'Estado de México',
                    'michoacan de ocampo': 'Michoacán', 'coahuila de zaragoza': 'Coahuila',
                    'veracruz de ignacio de la llave': 'Veracruz',
                    'veracruz ignacio de la llave': 'Veracruz'})
    return aliases.get(key)


def documentary_value(value: Any) -> str | int | float | None:
    """ND y no aplica permanecen como texto, sin convertirlos en ceros."""
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return value
    return str(value).strip()


def inventory_header(frame: pd.DataFrame) -> int:
    """Localiza el encabezado real, excluyendo títulos y subtítulos del Excel."""
    for i in range(min(12, len(frame))):
        row = [normalized(v) for v in frame.iloc[i]]
        if ('entidad federativa' in row and any('nombre de la intervencion' in v for v in row)):
            return i
        if 'nombre del programa' in row and 'ciclo' in row:
            return i
    raise ValueError('No se encontró encabezado documental verificable.')


def parse_inventory(frame: pd.DataFrame, source_id: str, year: int | None,
                    sheet: str, url: str, level: str) -> list[dict]:
    """Extrae todos los programas: no suma hojas nacional y estatales duplicadas.

    Elegibilidad, montos y continuidad no se infieren de nombre, población ni
    presupuesto. La referencia a la celda permite revisar el dato original.
    """
    h = inventory_header(frame)
    names = [str(v).strip() for v in frame.iloc[h]]
    keys = [normalized(v) for v in names]
    name_col = next(i for i, k in enumerate(keys) if 'nombre de la intervencion' in k or k == 'nombre del programa')
    state_col = next((i for i, k in enumerate(keys) if k == 'entidad federativa'), None)
    cycle_col = next((i for i, k in enumerate(keys) if k == 'ciclo'), None)
    result = []
    for position in range(h + 1, len(frame)):
        values = frame.iloc[position].tolist()
        name = documentary_value(values[name_col])
        if not isinstance(name, str) or not name or normalized(name) in {'nan', 'no aplica'}:
            continue
        territory = state_name(values[state_col]) if state_col is not None else None
        if level == 'estatal' and territory is None:
            raise ValueError(f'Entidad no reconocida en fila {position+1}; revisar antes de excluir.')
        cycle = int(values[cycle_col]) if cycle_col is not None else year
        if cycle is None or not 2001 <= cycle <= 2021:
            continue
        fields = {f'{i}:{names[i]}': documentary_value(v) for i, v in enumerate(values)
                  if not pd.isna(v) and not names[i].startswith('nan')}

        def select(pattern: str) -> list[object]:
            return [documentary_value(values[i]) for i, k in enumerate(keys)
                    if re.search(pattern, k) and not pd.isna(values[i])]

        stages = select(r'etapa de vida|grupos de atencion')
        target = ' '.join(str(v) for v in stages)
        markers = []
        # Marcadores de revisión: NO clasifican prestaciones ni elegibilidad.
        for tag, pattern in [('vejez', r'adult[oa]s? mayor(?:es)?|vejez|ancian|tercera edad'),
                             ('discapacidad', r'discapaci'), ('alimentacion', r'aliment|despensa|leche'),
                             ('transferencia_asistencia', r'pension|apoyo economico|monetari|asistenci|vulnerab')]:
            if re.search(pattern, normalized(name + ' ' + target + ' ' + ' '.join(map(str, select(r'tipo de apoyo'))))):
                markers.append(tag)
        result.append({
            'registro_documental': f'{source_id}:{position+1}', 'nombre_oficial': name,
            'nivel_gobierno': level, 'territorio': territory if territory else 'Ámbito federal; alcance efectivo según reglas',
            'territorio_original': documentary_value(values[state_col]) if state_col is not None else None,
            'institucion_responsable': select(r'^2\. dependencia|^3\. entidad|^entidad$|^unidad responsable$'),
            'nombres_historicos_reportados': select(r'nombre anterior'),
            'inicio_reportado_inventario': select(r'^ano de inicio$'),
            'anio_inicio_validado_reglas': None, 'anio_terminacion_validado': None,
            'anios_operacion_comprobados_inventario': [cycle],
            'poblacion_objetivo_categorias': stages,
            'edad_elegibilidad_validada': None,
            'requisitos_reportados': select(r'requisitos que deben'),
            'beneficio_reportado': select(r'tipo de apoyo|apoyos que reciben|como se entreg'),
            'tipo_pension_validado': None, 'monto_individual_validado_mxn': None,
            'periodicidad_validada': None,
            'documento_normativo_reportado': select(r'tipo de documento|principal normatividad'),
            'fecha_documento_reportada': select(r'ano de (vigencia|publicacion)'),
            'enlaces_reportados_por_coneval': select(r'hipervinculo|vinculo a la normatividad'),
            'fuente_id': source_id, 'fuente_oficial': url, 'hoja': sheet, 'fila_excel': position+1,
            'estado_verificacion': 'inventario_oficial_revisado; reglas_individuales_pendientes',
            'marcadores_revision': markers,
            'identificacion_enasem': 'no_asignada; requiere pregunta, codigo y titular',
            'campos_originales': fields,
        })
    return result


def documentary_coverage(records: list[dict]) -> list[dict]:
    """Cobertura estatal por año; ausencia de registro no demuestra inexistencia."""
    years = sorted({r['anios_operacion_comprobados_inventario'][0] for r in records if r['nivel_gobierno'] == 'estatal'})
    out = []
    for state in STATES:
        for year in years:
            rows = [r for r in records if r['nivel_gobierno'] == 'estatal' and r['territorio'] == state and r['anios_operacion_comprobados_inventario'] == [year]]
            out.append({'entidad': state, 'anio': year, 'intervenciones_inventariadas': len(rows),
                        'marcadas_vejez': sum('vejez' in r['marcadores_revision'] for r in rows),
                        'marcadas_discapacidad': sum('discapacidad' in r['marcadores_revision'] for r in rows),
                        'estado': 'registros_documentados' if rows else 'sin_registros_en_fuente; no_demuestra_ausencia'})
    return out


def parse_municipal(frame: pd.DataFrame, source: dict, sheet: str,
                    territory: str) -> list[dict]:
    """Lee la hoja principal; las hojas COVID son subconjuntos, no otra oferta.

    Los cortes 2012-2013 y 2014-2015 son periodos documentales, no dos años
    automáticamente comprobados de operación. Solo se rellenan encabezados de
    municipio agrupados; no se rellenan nombres, cantidades ni elegibilidad.
    """
    period = source['periodo']
    h = next((i for i in range(min(12, len(frame))) if any(
        'municipal' in normalized(v) and ('programa' in normalized(v) or 'intervencion' in normalized(v))
        for v in frame.iloc[i]) and any(normalized(v) in {'municipio','nombre del municipio'}
        for v in list(frame.iloc[i])+list(frame.iloc[max(0,i-1)]))), None)
    if h is None:
        raise ValueError('No hay encabezado municipal reconocible.')
    headers = [normalized(v) for v in frame.iloc[h]]
    name_col = next(i for i, k in enumerate(headers) if 'municipal' in k and ('programa' in k or 'intervencion' in k))
    # En 2012-2013, el nombre de municipio está en la fila superior.
    upper = [normalized(v) for v in frame.iloc[max(0, h-1)]]
    combined = [a if a != 'nan' else b for a, b in zip(headers, upper)]
    municipal_col = next((i for i,k in enumerate(combined) if k in {'municipio','nombre del municipio'}), None)
    if municipal_col is None:
        raise ValueError('No se encontró el municipio: no asignar por posición.')
    data = frame.iloc[h+1:].copy()
    data.iloc[:, municipal_col] = data.iloc[:, municipal_col].ffill()
    out = []
    for position, row in data.iterrows():
        name = documentary_value(row.iloc[name_col])
        municipality = documentary_value(row.iloc[municipal_col])
        if not isinstance(name,str) or not name or not isinstance(municipality,str):
            continue
        fields = {f'{i}:{combined[i]}': documentary_value(v) for i,v in enumerate(row)
                  if not pd.isna(v)}
        def values(pattern: str) -> list[object]:
            return [documentary_value(row.iloc[i]) for i,k in enumerate(combined)
                    if re.search(pattern,k) and not pd.isna(row.iloc[i])]
        target = values(r'^definicion|poblacion objetivo')
        markers = []
        for tag,pattern in [('vejez',r'adult[oa]s? mayor(?:es)?|vejez|ancian|tercera edad'),
                            ('discapacidad',r'discapaci'), ('alimentacion',r'aliment|despensa|leche'),
                            ('transferencia_asistencia',r'pension|apoyo economico|asistenci|vulnerab')]:
            if re.search(pattern, normalized(name+' '+' '.join(map(str,target)))):
                markers.append(tag)
        out.append({'registro_documental':f"{source['id']}:{position+1}",
                    'nombre_oficial':name, 'nivel_gobierno':'municipal',
                    'territorio':territory,'municipio':municipality,
                    'periodo_documental':period,
                    'anios_operacion_comprobados_inventario':[],
                    'operacion_anual_validada':False,
                    'institucion_responsable':values(r'institucion responsable'),
                    'poblacion_objetivo_categorias':target,
                    'edad_elegibilidad_validada':None,
                    'anio_inicio_validado_reglas':None,'anio_terminacion_validado':None,
                    'monto_individual_validado_mxn':None,'periodicidad_validada':None,
                    'tipo_pension_validado':None,'beneficio_reportado':None,
                    'fuente_id':source['id'],'fuente_oficial':source['url'],
                    'hoja':sheet,'fila_excel':int(position)+1,
                    'enlaces_reportados_por_coneval':values(r'hipervinculo'),
                    'estado_verificacion':'inventario_oficial_revisado; operacion_y_reglas_pendientes',
                    'marcadores_revision':markers,
                    'identificacion_enasem':'no_asignada; categoria_agregada_no_identifica_programa',
                    'campos_originales':fields})
    return out


def academic_spacing(text: str) -> str:
    """Separa palabras/cifras en prosa; conserva URLs, código y nombres de archivo."""
    chunks = re.split(r'(`[^`]*`|https?://[^\s)]+|\[[^\]]*\]\([^)]*\))', text)
    for i in range(0, len(chunks), 2):
        chunks[i] = re.sub(r'([A-Za-zÁÉÍÓÚÑáéíóúñ]{2,})(\d)', r'\1 \2', chunks[i])
        chunks[i] = re.sub(r'(\d)([A-Za-zÁÉÍÓÚÑáéíóúñ]{2,})', r'\1 \2', chunks[i])
        chunks[i] = re.sub(r'\b([ay])(?=\d)', r'\1 ', chunks[i])
        chunks[i] = re.sub(r'(?<=\d)y(?=\d)', ' y ', chunks[i])
        for original, spaced in {
            'SHA 256': 'SHA256', 'CP 1': 'CP1', 'CP 2': 'CP2',
            '05 ey': '05e y', '05eejecutado': '05e ejecutado',
            'Kagrupa': 'K agrupa', 'Aes ': 'A es ', 'Nde ': 'N de ',
            'COVIDno': 'COVID no', 'conSHA256y': 'con SHA256 y',
            'normasUDLAPy': 'normas UDLAP y', 'estructuraUDLAPy': 'estructura UDLAP y',
            'B01y': 'B01 y', '5,583A': '5,583 A', 'ApéndiceA': 'Apéndice A',
            'VSCode': 'VS Code', 'gráficaBrBG': 'gráfica BrBG',
        }.items():
            chunks[i] = chunks[i].replace(original, spaced)
    return ''.join(chunks)
