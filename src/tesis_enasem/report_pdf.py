"""PDF académico generado exclusivamente desde el informe Markdown editable."""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re
from statistics import median
from tempfile import TemporaryDirectory
from urllib.parse import unquote

from markdown_it import MarkdownIt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, Image, LongTable,
    PageBreak, PageTemplate, Paragraph, Spacer, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents
import matplotlib
import pymupdf

from .project_paths import INTERIM_DIR, PROJECT_ROOT, RESULTS_DIR


def markdown_parser() -> MarkdownIt:
    """Activa tablas reales y conserva el texto HTML visible del Markdown."""
    return MarkdownIt('commonmark', {'html': True}).enable('table')


def register_fonts() -> None:
    """Usa las fuentes Unicode ya distribuidas con matplotlib."""
    directory = Path(matplotlib.get_data_path()) / 'fonts/ttf'
    for name, filename in [('Academic', 'DejaVuSans.ttf'),
                           ('AcademicBold', 'DejaVuSans-Bold.ttf'),
                           ('AcademicItalic', 'DejaVuSans-Oblique.ttf'),
                           ('AcademicMono', 'DejaVuSansMono.ttf')]:
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(directory / filename)))
    pdfmetrics.registerFontFamily('Academic', normal='Academic', bold='AcademicBold',
                                 italic='AcademicItalic', boldItalic='AcademicBold')


def inline_markup(token, source: Path) -> str:
    """Convierte texto y énfasis sin interpretar o alterar las cifras."""
    result = []
    for child in token.children or []:
        kind = child.type
        if kind == 'text': result.append(escape(child.content))
        elif kind == 'code_inline': result.append('<font name="AcademicMono">'+escape(child.content)+'</font>')
        elif kind in {'softbreak', 'hardbreak'}: result.append('<br/>')
        elif kind in {'strong_open', 'strong_close'}: result.append('<b>' if kind.endswith('open') else '</b>')
        elif kind in {'em_open', 'em_close'}: result.append('<i>' if kind.endswith('open') else '</i>')
        elif kind == 'link_open':
            target = child.attrGet('href')
            if not target.startswith(('#', 'http:', 'https:', 'mailto:')):
                target = (source.parent / unquote(target.split('#')[0])).resolve().as_uri()
            result.append(f'<link href="{escape(target, quote=True)}" color="#17635c">')
        elif kind == 'link_close': result.append('</link>')
        elif kind == 'html_inline':
            anchor = re.search(r'<a\s+id="([^"]+)"', child.content)
            if anchor: result.append(f'<a name="{escape(anchor[1])}"/>')
            elif child.content.lower().startswith('<br'): result.append('<br/>')
            else: result.append(escape(re.sub('<[^>]+>', '', child.content)))
        elif kind != 'image': result.append(escape(child.content))
    return ''.join(result)


def table_panels(rows: list[list], maximum: int = 6) -> list[list[int]]:
    """Divide columnas amplias repitiendo dos claves; ninguna celda se pierde."""
    count = len(rows[0])
    if count <= maximum: return [list(range(count))]
    return [[0, 1] + list(range(start, min(start + maximum - 2, count)))
            for start in range(2, count, maximum - 2)]


class AcademicDocument(BaseDocTemplate):
    """Encabezados, folios, destinos internos e índice con páginas verificadas."""
    def __init__(self, filename: str, **kwargs):
        super().__init__(filename, pagesize=A4, leftMargin=48, rightMargin=48,
                         topMargin=52, bottomMargin=48, **kwargs)
        self.heading_pages = []
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height,
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates(PageTemplate('academic', [frame], onPage=self.decorate))

    def decorate(self, canvas, doc):
        canvas.saveState()
        if doc.page > 1:
            canvas.setFont('Academic', 8)
            canvas.setFillColor(colors.HexColor('#45534f'))
            canvas.drawString(48, A4[1]-30, 'ENASEM · Informe general acumulativo')
            canvas.setStrokeColor(colors.HexColor('#becac5'))
            canvas.line(48, A4[1]-37, A4[0]-48, A4[1]-37)
        canvas.setFont('Academic', 8)
        canvas.drawCentredString(A4[0]/2, 25, str(doc.page))
        canvas.restoreState()

    def beforeDocument(self):
        self.heading_pages = []

    def afterFlowable(self, flowable):
        if getattr(flowable, '_academic_heading', None):
            level, title, key = flowable._academic_heading
            self.canv.bookmarkPage(key)
            self.heading_pages.append({'nivel':level, 'titulo':title, 'pagina':self.page})
            if level <= 1:
                self.notify('TOCEntry', (level, title, self.page, key))
                self.canv.addOutlineEntry(title, key, level=level, closed=True)


def build_story(text: str, source: Path):
    """Respeta el orden editorial; sitúa figuras, notas e interpretación juntas."""
    register_fonts()
    body = ParagraphStyle('body', fontName='Academic', fontSize=10, leading=14,
                          spaceAfter=8, splitLongWords=True)
    cell = ParagraphStyle('cell', parent=body, fontSize=8.5, leading=11, spaceAfter=0)
    heading_styles = {level: ParagraphStyle(f'h{level}', parent=body,
                      fontName='AcademicBold', fontSize={1:20,2:15,3:12}.get(level,11),
                      leading={1:25,2:20,3:16}.get(level,15),
                      spaceBefore=12, spaceAfter=8, keepWithNext=True)
                      for level in range(1,7)}
    tokens = markdown_parser().parse(text)
    title = next(tokens[k+1].content for k,t in enumerate(tokens) if t.type=='heading_open')
    date = re.search(r'\*\*Actualización:\*\* ([^\n]+)', text)
    story = [Spacer(1,120), Paragraph(escape(title), ParagraphStyle('cover', parent=heading_styles[1],alignment=TA_CENTER)),
             Spacer(1,25), Paragraph('Pensiones, titularidad, apoyos y trayectorias longitudinales',
             ParagraphStyle('subtitle',parent=body,alignment=TA_CENTER,fontSize=13,leading=19)),
             Spacer(1,40), Paragraph(escape(date[1] if date else datetime.now().strftime('%d/%m/%Y')),
             ParagraphStyle('date',parent=body,alignment=TA_CENTER)),
             Spacer(1,55), Paragraph('Síntesis académica de evidencia previamente calculada.<br/>Documento de trabajo; resultados provisionales y limitaciones explícitas.',
             ParagraphStyle('status',parent=body,alignment=TA_CENTER)),PageBreak(),
             Paragraph('Índice de contenido',heading_styles[2])]
    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle('toc1',parent=body,fontName='AcademicBold',fontSize=10,leading=14,spaceBefore=5),
                       ParagraphStyle('toc2',parent=body,fontSize=9,leading=12,leftIndent=15)]
    story += [toc, PageBreak()]
    audit={'tablas':0,'filas_datos':0,'celdas':0,'figuras':[], 'encabezados':[], 'texto_inline':[], 'paneles':0}
    index=0;skip_index=False;heading_number=0;table_number=0
    while index<len(tokens):
        token=tokens[index]
        if token.type=='heading_open':
            inline=tokens[index+1];level=int(token.tag[1]);title=inline.content
            if level==1: index+=3;continue
            if level==2 and title in ['Índice','Índice navegable']:
                skip_index=True;index+=3;continue
            if level==2:skip_index=False
            if skip_index:index+=3;continue
            heading_number+=1;p=Paragraph(inline_markup(inline,source),heading_styles[level])
            p._academic_heading=(max(0,level-2),title,f'heading-{heading_number}')
            story.append(p);audit['encabezados'].append(title);index+=3;continue
        if skip_index:index+=1;continue
        if token.type=='html_block':
            for anchor in re.findall(r'<a\s+id="([^"]+)"',token.content):
                story.append(Paragraph(f'<a name="{escape(anchor)}"/>',body))
            summary=re.search(r'<summary>(.*?)</summary>',token.content,re.S)
            if summary:story.append(Paragraph(escape(summary[1]),body))
        elif token.type=='table_open':
            rows=[];index+=1
            while tokens[index].type!='table_close':
                if tokens[index].type=='tr_open':rows.append([])
                elif tokens[index].type=='inline':rows[-1].append(tokens[index])
                index+=1
            table_number+=1;audit['tablas']+=1;audit['filas_datos']+=len(rows)-1
            audit['celdas']+=sum(len(row) for row in rows)
            panels=table_panels(rows)
            for panel_number, columns in enumerate(panels,1):
                if len(panels)>1:
                    story.append(Paragraph(f'Cuadro {table_number}, bloque de columnas {panel_number}/{len(panels)}. Las primeras dos columnas conservan las claves comunes; las filas mantienen su orden.',body))
                data=[[Paragraph(('<b>'+inline_markup(row[c],source)+'</b>') if n==0 else inline_markup(row[c],source),cell) for c in columns] for n,row in enumerate(rows)]
                weights=[max(10,min(55,max(len(rows[0][c].content),
                         median(len(row[c].content) for row in rows[1:] or rows)))) for c in columns]
                available=A4[0]-96
                widths=[42+(available-42*len(columns))*weight/sum(weights) for weight in weights]
                table=LongTable(data,colWidths=widths,repeatRows=1,splitByRow=1,splitInRow=0,hAlign='LEFT',spaceAfter=10)
                table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e5efeb')),
                    ('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#4b7065')),
                    ('LINEBELOW',(0,-1),(-1,-1),.5,colors.HexColor('#81978f')),
                    ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),4),
                    ('RIGHTPADDING',(0,0),(-1,-1),4),('TOPPADDING',(0,0),(-1,-1),4),
                    ('BOTTOMPADDING',(0,0),(-1,-1),4)]))
                story.append(table);audit['paneles']+=1
        elif token.type=='inline':
            images=[c for c in token.children or [] if c.type=='image']
            if images:
                for img in images:
                    target=(source.parent / unquote(img.attrGet('src'))).resolve()
                    if not target.is_file():raise FileNotFoundError(target)
                    image=Image(str(target),lazy=2)
                    scale=min((A4[0]-96)/image.imageWidth,440/image.imageHeight)
                    image.drawWidth=image.imageWidth*scale;image.drawHeight=image.imageHeight*scale
                    story += [image,Spacer(1,8)]
                    audit['figuras'].append(str(target.relative_to(PROJECT_ROOT)))
            else:
                markup=inline_markup(token,source)
                if markup:
                    paragraph=Paragraph(markup,body)
                    if re.match(r'^(?:\*\*)?(?:Cuadro |Figura |Pregunta y aporte:|Objetivo y aporte:)', token.content):
                        paragraph.keepWithNext=True
                    story.append(paragraph);audit['texto_inline'].append(token.content)
        elif token.type=='fence':
            for line in token.content.splitlines():story.append(Paragraph(escape(line) or ' ',cell))
        index+=1
    return story,audit


def normalized(text: str) -> str:
    """Normaliza solo espaciado y marcas Markdown para cotejar texto del PDF."""
    text=re.sub(r'[`*_]', '',text)
    return re.sub(r'\s+','',text)


def generate_report_pdf(source: Path | None = None, destination: Path | None = None) -> dict:
    """Genera, verifica y sustituye atómicamente el único PDF; limpia temporales."""
    source=source or RESULTS_DIR/'INFORME_GENERAL.md'
    destination=destination or RESULTS_DIR/'INFORME_GENERAL.pdf'
    raw=source.read_bytes();text=raw.decode('utf-8')
    story,audit=build_story(text,source)
    destination.parent.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix='.informe_pdf_',dir=destination.parent) as temporary:
        output=Path(temporary)/'informe.pdf'
        doc=AcademicDocument(str(output),title='Informe general acumulativo — tesis ENASEM',author='Proyecto de tesis ENASEM')
        doc.multiBuild(story)
        pdf=pymupdf.open(output)
        # Excluir encabezados y folios del cotejo evita interrumpir párrafos
        # que continúan en la siguiente página.
        extracted='\n'.join(p.get_text(clip=pymupdf.Rect(47,45,p.rect.width-47,p.rect.height-43)) for p in pdf)
        readable=normalized(extracted)
        missing_headings=[t for t in audit['encabezados'] if normalized(t) not in readable]
        if missing_headings:raise ValueError(f'Encabezados ausentes: {missing_headings}')
        # Cada celda y cada párrafo deben aparecer; se comprueba el contenido visible,
        # incluyendo el texto de enlaces, sin exigir marcas de presentación Markdown.
        expected=[]
        split_cells=[]
        parsed = markdown_parser().parse(text)
        for number,t in enumerate(parsed):
            if t.type=='inline' and not any(c.type=='image' for c in t.children or []):
                plain=''.join(c.content if c.type in ['text','code_inline'] else '\n' if c.type in ['softbreak','hardbreak'] else '' for c in t.children or [])
                if plain.strip():
                    expected.append(plain)
                    if number and parsed[number-1].type in ['td_open','th_open']:
                        split_cells.append(plain)
        missing=[t for t in expected if normalized(t) not in readable]
        # Una celda que continúa en otra página puede quedar intercalada con
        # el encabezado repetido: exigir todos sus términos, en orden y próximos.
        fragmented=[]
        for cell_text in list(missing):
            if cell_text not in split_cells: continue
            words = [normalized(w) for w in cell_text.split() if normalized(w)]
            pattern = '.{0,160}?'.join(re.escape(w) for w in words)
            if re.search(pattern, readable):
                fragmented.append(cell_text)
                missing.remove(cell_text)
        if missing:raise ValueError(f'Textos/celdas ausentes ({len(missing)}): {missing[:5]}')
        image_count=sum(len(p.get_image_info()) for p in pdf)
        if image_count!=len(audit['figuras']):raise ValueError('Cantidad de figuras PDF distinta del Markdown')
        if len(set(audit['figuras']))!=len(audit['figuras']):raise ValueError('Figura repetida en la síntesis')
        out_of_bounds=[]
        for number,page in enumerate(pdf,1):
            for block in page.get_text('dict')['blocks']:
                rect=pymupdf.Rect(block['bbox'])
                if rect.x0<-1 or rect.y0<-1 or rect.x1>page.rect.width+1 or rect.y1>page.rect.height+1:
                    out_of_bounds.append(number)
        if out_of_bounds:raise ValueError(f'Contenido fuera de página: {sorted(set(out_of_bounds))}')
        evidence={'fuente':str(source.relative_to(PROJECT_ROOT)), 'markdown_sha256':sha256(raw).hexdigest(),
            'pdf_sha256':sha256(output.read_bytes()).hexdigest(),'paginas':len(pdf),'tablas':audit['tablas'],
            'filas_datos':audit['filas_datos'],'celdas':audit['celdas'],'paneles_tabla':audit['paneles'],
            'figuras':audit['figuras'],'encabezados_cotejados':len(audit['encabezados']),
            'textos_y_celdas_cotejados':len(expected),'textos_ausentes':0,'figuras_pdf':image_count,
            'celdas_continuadas_cotejadas_por_terminos':len(fragmented),
            'contenido_fuera_pagina':0,'enlaces_pdf':sum(len(p.get_links()) for p in pdf),
            'indice_con_paginas':True,'paginas_encabezados':doc.heading_pages}
        evidence['imagenes_sha256'] = {name:sha256((PROJECT_ROOT/name).read_bytes()).hexdigest()
                                      for name in audit['figuras']}
        pdf.close()
        if source.read_bytes()!=raw:raise ValueError('Markdown cambió durante la conversión; regenerar.')
        output.replace(destination)
    (INTERIM_DIR/'informe_general_pdf_validacion.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    return evidence


def validate_report_sync() -> dict:
    """Rechaza un PDF obsoleto si cambia Markdown, imagen o archivo generado."""
    evidence=json.loads((INTERIM_DIR/'informe_general_pdf_validacion.json').read_text())
    assert sha256((RESULTS_DIR/'INFORME_GENERAL.md').read_bytes()).hexdigest()==evidence['markdown_sha256'], 'PDF pendiente de regenerar: Markdown actualizado'
    assert sha256((RESULTS_DIR/'INFORME_GENERAL.pdf').read_bytes()).hexdigest()==evidence['pdf_sha256'], 'PDF distinto del generado'
    for name,digest in evidence['imagenes_sha256'].items():
        assert sha256((PROJECT_ROOT/name).read_bytes()).hexdigest()==digest, f'Figura actualizada: regenerar PDF ({name})'
    return evidence
