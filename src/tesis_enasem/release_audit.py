"""Auditoría aplicada de cierre: familias reales, canales y propuesta Git.

No promete anonimato frente a información externa arbitraria. Distingue
conteos permitidos de estadísticas monetarias protegidas y no suma medianas.
"""
from __future__ import annotations
import hashlib,json,re,subprocess
from pathlib import Path
import numpy as np
from .statistical_quality import ROOT,OUT,ORIGINAL
from .disclosure_quality import complementary_suppression,protect_rows,redact_financial_paragraphs,paragraph_sample_numbers
from .quality_outputs import markdown_blocks,clean_tex_rows
from .publication import SECRET_SIGNATURE


def audit_families(audit: dict) -> list[dict]:
    """Aplica supresión complementaria a cada partición monetaria central real.

    La propuesta no exporta estas matrices ni sus márgenes: solo decisiones.
    Se comprueba que ninguna línea publicada deje una incógnita protegida.
    """
    rows=audit['embudos_contrastes'];result=[]
    keys=sorted({(r['via'],r['origen'],r['destino'],r['dimension']) for r in rows if r['dimension']!='General'})
    for via,a,b,d in keys:
        q=[r for r in rows if (r['via'],r['origen'],r['destino'],r['dimension'])==(via,a,b,d)]
        groups=sorted({r['grupo'] for r in q});cats=sorted({r['categoria'] for r in q})
        values=np.array([[next((r['N_monto'] for r in q if r['grupo']==g and r['categoria']==c),0) for c in cats] for g in groups])
        decision=complementary_suppression(values)
        mask=np.array(decision['suppressed']);retired={(x['axis'],x['index']) for x in decision['retire_margins']}
        for axis in (0,1):
            for i in range(mask.shape[axis]):
                line=mask[i,:] if axis==0 else mask[:,i]
                assert line.sum()!=1 or (axis,i) in retired
        result.append({'via':via,'origen':a,'destino':b,'dimension':d,
            'celdas':int(values.size),'primarias':int(np.array(decision['primary']).sum()),
            'complementarias':int(np.array(decision['complementary']).sum()),
            'margenes_retirados':len(retired),
            'salida':'No exportar matriz ni márgenes; solo tablas de estadísticas con N suficiente. No se generan porcentajes de celdas monetarias protegidas.'})
    return result


def audit_parser_scope() -> dict:
    """Compara el filtro viejo/nuevo sobre todos los documentos originales."""
    fixed=[];retained=[]
    for p in (ORIGINAL/'manuscrito').rglob('*.tex'):
        if 'build' in p.relative_to(ORIGINAL).parts:continue
        for number,paragraph in enumerate(re.split(r'\n\s*\n',p.read_text()),1):
            old=[int(x.replace(',','')) for x in re.findall(r'\bN\s*=\s*([\d,]+)',paragraph)]
            from .disclosure_quality import MONEY,CONTINUOUS
            was=bool(MONEY.search(paragraph) and CONTINUOUS.search(paragraph) and any(0<n<10 for n in old))
            _,count=redact_financial_paragraphs(paragraph)
            if was and not count:fixed.append({'archivo':str(p.relative_to(ORIGINAL)),'bloque':number,'N_corregidos':paragraph_sample_numbers(paragraph)})
            if count:retained.append({'archivo':str(p.relative_to(ORIGINAL)),'bloque':number})
    assert len(fixed)==1 and fixed[0]['N_corregidos']==[1756,1223,1183,1103]
    return {'bloques_restaurados':fixed,'retiros_legitimos':retained,'estimaciones_modificadas':0}


def check_related_monetary_rows(tables: list[dict]) -> dict:
    """Comprueba dependencias estimación/contraste/IC de las filas reales.

    Una diferencia y una mediana conocida recuperan la otra mediana. Se bloquea
    toda la fila con rama <10, no solo el valor central; los IC son dependientes.
    Los valores de un cuantil no son sumandos de un total monetario.
    """
    checked=0;protected=0
    from .disclosure_quality import MONEY,CONTINUOUS,sample_numbers
    from .statistical_quality import count_column
    for table in tables:
        headers=table['headers'];context=table['title']+' '+' '.join(headers)
        if not (MONEY.search(context) or any('P-C' in h or 'P menos C' in h for h in headers)):continue
        for row in table['rows']:
            ns=sample_numbers(headers,row)
            branch=any(0<n<10 for n in ns) or any(re.search(r'<\s*10(?!\d)|Reservado|Sin soporte',v) for h,v in zip(headers,row) if count_column(h))
            if not branch:continue
            statistical=[v for h,v in zip(headers,row) if not count_column(h) and re.search(r'median|Q25|Q75|P25|P75|diferencia|\bIC|cruda|mezcla',h,re.I)]
            # A protected branch must not leave its medians, CI, ratios or contrasts.
            assert not any(re.search(r'\d',v) for v in statistical),'Derivado reconstructivo: '+table['title']
            if statistical:protected+=1
            checked+=1
    return {'filas_protegidas_y_derivados':checked,'familias_monetarias_con_derivados_revisados':protected,
        'recuperacion_por_contraste_mas_mediana':False,
        'alcance':'Filas monetarias liberadas, totales/subtotales de particiones centrales y sus derivados; sin sumar medianas. No evalúa información auxiliar externa no publicada.'}


def validate_public_content(base: Path) -> dict:
    """Revisa contenido, no solo extensión; falla ante fila pequeña aún expuesta."""
    authorized=set(json.loads((base/'diccionarios/cierre_publicacion.json').read_text())['archivos_publicar'])
    report=(base/'resultados/INFORME_GENERAL.md').read_text();tables=markdown_blocks(report)
    related=check_related_monetary_rows(tables)
    for t in tables:
        _,decisions=protect_rows(t['headers'],t['rows'],context=t['title'])
        assert not decisions, 'Fila sensible no protegida: '+t['title']
    tex=0
    for p in (base/'manuscrito').rglob('*.tex'):
        if 'build' in p.relative_to(base).parts or p.relative_to(base).as_posix() not in authorized:continue
        _,decisions=clean_tex_rows(p.read_text(),str(p));assert not decisions,p
        _,n=redact_financial_paragraphs(p.read_text());assert not n,p
        tex+=1
    for name in sorted(authorized):
        p=base/name
        assert p.is_file(),name
        assert not p.is_symlink()
        if p.suffix in {'.md','.tex','.json','.csv','.ipynb','.yml','.yaml','.toml','.bib'}:
            text=p.read_text(errors='replace');assert not SECRET_SIGNATURE.search(text),p
            assert not re.search(r'(?<![\w:])\d{6,12}:\d{1,4}(?![\w:}])',text),p
        if p.suffix=='.json':
            obj=json.loads(p.read_text())
            # Full private analytical outputs and exact money histograms are prohibited.
            assert p.name not in {'resultados.json','auditoria.json','eventos.json','precision.json'},p
        if p.suffix=='.pdf':
            import pymupdf
            doc=pymupdf.open(p)
            assert not doc.embfile_count(),p
            for page in doc:
                for link in page.get_links():
                    uri=link.get('uri','')
                    assert not uri.startswith(('file:','/Users/','/home/')),p
    return {'dependencias_monetarias':related,'cuadros_revisados':len(tables),'fuentes_tex':tex,'filas_sensibles_sin_proteger':0,
        'limite':'Se verifica el contenido liberado y los ataques algebraicos de estadísticas publicadas. Los conteos de recepción/ND permitidos no son importes individuales. Medianas y cuantiles no se tratan como sumas. No certifica ausencia de ataques con información externa arbitraria.'}


def close_audit() -> dict:
    private=json.loads((OUT/'privado/auditoria.json').read_text())
    families=audit_families(private);scope=audit_parser_scope()
    checks=validate_public_content(ROOT)
    manifest=json.loads((OUT/'propuesta_publica.json').read_text())
    tracked=set(subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0'))-{''}
    others=set(subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0'))-{''}
    entries=set(manifest['archivos'])
    result={'estado':'Controles aplicados al paquete delimitado; publicación pendiente de autorización',
        'filtro':scope,'familias_reales':families,'contenido':checks,
        'archivos_publicar':manifest['archivos'],
        'retirar_del_arbol_publico_al_publicar':sorted(tracked-entries),
        'no_incorporar':sorted(others-entries),
        'tratamiento':'Un único repositorio: las rutas fuera del manifiesto se retiran solo del índice mediante prepare_quality_release.py --stage y permanecen en disco. Se valida el árbol exacto; no se crean repositorios ni se reescribe el historial.',
        'historial':'Exposición T8 histórica identificada por separado; no se reescribió ni saneó.',
        'originales':'Snapshot privado y fuentes originales verificados por validate_statistical_quality.py'}
    (OUT/'cierre_publicacion.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('Cierre: familias reales',len(families),'cuadros',checks['cuadros_revisados'],'archivos',len(entries),'retiros propuestos',len(tracked-entries))
    return result
