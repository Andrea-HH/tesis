"""Política10: calidad estadística y divulgación son evaluaciones diferentes.

Se reutilizan detectores de publication.py. El umbral10 es una decisión
conservadora del proyecto, no una regla certificada de MHAS ni de INEGI.
"""
from __future__ import annotations

import re
from typing import Any
import numpy as np

from .publication import assert_no_direct_disclosure, sanitize_local_paths
from .statistical_quality import numbers_in_count, count_column

MINIMUM_DISCLOSURE=10
MONEY=re.compile(r'monto|patrimonio|salario|ingreso|nominal|pesos|monetari|poder adquisitivo|prestación.*LPI',re.I)
CONTINUOUS=re.compile(r'mediana|\bmedia\b|cuantil|Q25|Q75|med\.|Q25/med|diferencia real|monto real|cruda \[IC',re.I)
EXCLUDED_N=re.compile(r'ND|desconocid|excluid|faltan|fuera|sin monto|conflicto',re.I)


def assess_n(n: int,*,ci: list[float]|None=None,reviewed: bool=False) -> dict[str,Any]:
    """Decisión explícita:30 no acredita validez;10–29 requiere revisión."""
    if n<0:
        raise ValueError('N negativo')
    return dict(N=n,divulgar_monetario=n>=MINIMUM_DISCLOSURE,
        revision='sin observaciones' if n==0 else 'menor de10' if n<10 else '10–29' if n<30 else '30+',
        inferencia_nacional=False,
        soporte_interpretativo=bool(n>=10 and reviewed and ci is not None),
        nota='Ni el umbral ni un IC que excluya cero certifican diseño, causalidad o equivalencia.')


def complementary_suppression(values: np.ndarray,minimum: int=MINIMUM_DISCLOSURE) -> dict:
    """Protege conteos con márgenes: impide una única incógnita por fila/columna.

    No modifica datos. Si no hay donante, debe retirarse el margen. Este control
    lineal no acredita anonimato universal frente a todas las publicaciones.
    """
    a=np.asarray(values)
    if a.ndim!=2 or not np.isfinite(a).all() or (a<0).any() or not np.equal(a,np.floor(a)).all():
        raise ValueError('Matriz de conteos enteros no negativos requerida')
    primary=(a>0)&(a<minimum);mask=primary.copy();retire=[]
    changed=True
    while changed:
        changed=False
        for axis in (0,1):
            count=a.shape[0] if axis==0 else a.shape[1]
            for index in range(count):
                line=mask[index,:] if axis==0 else mask[:,index]
                vals=a[index,:] if axis==0 else a[:,index]
                if int(line.sum())!=1:
                    continue
                candidates=np.flatnonzero((~line)&(vals>0))
                if len(candidates):
                    j=int(candidates[np.argmin(vals[candidates])])
                    if axis==0:mask[index,j]=True
                    else:mask[j,index]=True
                    changed=True
                else:
                    retire.append({'axis':axis,'index':index})
    return dict(primary=primary.tolist(),suppressed=mask.tolist(),
        complementary=(mask&~primary).tolist(),retire_margins=retire,
        nota='También se retiran porcentajes y derivados de las celdas; comprobar otras tablas y el historial.')


def sample_numbers(headers: list[str],row: list[str]) -> list[int]:
    """N de observaciones válidas/grupos, sin usar exclusiones o fechas como N."""
    pairs=[(h,row[i]) for i,h in enumerate(headers) if i<len(row) and count_column(h) and not EXCLUDED_N.search(h)]
    preferred=[(h,v) for h,v in pairs if re.search(r'válido|monto|P/C|nuevos|continuos|grupo|pares',h,re.I)]
    selected=preferred or pairs
    return [n for _,v in selected for n in numbers_in_count(v)]


def protect_rows(headers: list[str],rows: list[list[str]],*,context: str='') -> tuple[list[list[str]],list[dict]]:
    """Supresión de familias de estadísticas, nunca reemplazo con0.

    Si hay una rama pequeña se retiran su estimación, IC, diferencias y perfiles
    de la fila completa; no se deja el contraste para reconstruirla. Conteos de
    elegibilidad/ND aislados no se confunden con una estimación monetaria.
    """
    sensitive=bool(CONTINUOUS.search(' '.join(headers)) and (MONEY.search(' '.join(headers)+' '+context) or re.search(r'Edad med|Esc. med|Mujeres %|q25|q75', ' '.join(headers),re.I)))
    output=[];log=[]
    for i,row in enumerate(rows):
        if row and all(v=='Reservado' for v in row[1:]):
            output.append(row)
            continue
        ns=sample_numbers(headers,row);small=bool(ns and any(0<n<MINIMUM_DISCLOSURE for n in ns))
        nd=any(re.search(r'Desconocid|otra vía ND',c,re.I) for c in row[:2])
        if sensitive and (small or nd):
            protected=[]
            for j,value in enumerate(row):
                # Mantener etiquetas conceptuales; no cantidades o proporciones.
                if j<2 and j<len(headers) and not count_column(headers[j]) and not re.search(r'^\s*[\d.,/% −-]+\s*$',value):
                    protected.append(value)
                else:
                    protected.append('Reservado')
            output.append(protected)
            log.append(dict(fila=i+1,N=ns,motivo='N menor de10 o perfil desconocido; estimación y derivados retirados conjuntamente'))
        else:
            output.append(row)
    return output,log


def paragraph_sample_numbers(text: str) -> list[int]:
    """Lee N declarado, incluidos pares y miles LaTeX; no frecuencias de eventos.

    No convierte periodicidades, montos, exclusiones o fechas en N analítico.
    Los separadores de miles se normalizan antes de capturar el número completo.
    """
    normalized=text.replace(r"\,", "").replace(r"\thinspace", "")
    normalized=re.sub(r"(?<=\d)[\u00a0\u202f](?=\d{3}\b)", "", normalized)
    values=re.findall(r"\bN\s*=\s*(\d[\d,]*(?:\s*/\s*\d[\d,]*)*)",normalized)
    return [n for value in values for n in numbers_in_count(value)]


def redact_financial_paragraphs(text: str) -> tuple[str,int]:
    """No publica extremos seleccionados con N<10 en narrativa o notas."""
    # Fechas de reglas/actualización, revisadas en el informe: año:edad/meses no es cunicah:np.
    text=re.sub(r'((?:actualización|febrero|diciembre|julio)\s*(?:19|20)\d{2}):(?=\d)',r'\1: ',text,flags=re.I)
    pieces=re.split(r'(\n\s*\n)',text);count=0
    for i,p in enumerate(pieces):
        ns=paragraph_sample_numbers(p)
        if MONEY.search(p) and CONTINUOUS.search(p) and any(0<n<MINIMUM_DISCLOSURE for n in ns):
            pieces[i]='Detalle monetario retirado de esta edición pública por soporte menor de10; no sustenta conclusiones. Los originales y la causa del tamaño se conservan en el registro privado de auditoría10.'
            count+=1
    result=''.join(pieces)
    assert_no_direct_disclosure(result)
    return result,count
