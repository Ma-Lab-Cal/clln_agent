"""Render the checked-in Markdown case studies as portable PDF documents."""
import argparse
from html import escape
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle


def render(root):
    root=Path(root)
    fonts=Path('/usr/share/fonts/truetype/dejavu')
    regular,bold='Helvetica','Helvetica-Bold'
    if (fonts/'DejaVuSans.ttf').exists():
        pdfmetrics.registerFont(TTFont('ReleaseRegular',str(fonts/'DejaVuSans.ttf')))
        pdfmetrics.registerFont(TTFont('ReleaseBold',str(fonts/'DejaVuSans-Bold.ttf')))
        regular,bold='ReleaseRegular','ReleaseBold'
    body=ParagraphStyle('body',fontName=regular,fontSize=9.2,leading=14.2,spaceAfter=8,textColor=colors.HexColor('#253b35'))
    title=ParagraphStyle('title',fontName=bold,fontSize=22,leading=27,spaceAfter=18,textColor=colors.HexColor('#233a37'))
    project_style=ParagraphStyle('project',fontName=bold,fontSize=8.5,leading=12,spaceAfter=10,textColor=colors.HexColor('#99732f'))
    heading=ParagraphStyle('heading',fontName=bold,fontSize=12,leading=16,spaceBefore=12,spaceAfter=7,textColor=colors.HexColor('#176b62'))
    small=ParagraphStyle('small',parent=body,fontSize=8,leading=11)
    def inline(text):
        text=escape(text)
        text=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'<link href="\2" color="#176b62">\1</link>',text)
        text=re.sub(r'`([^`]+)`',r'<font name="Courier">\1</font>',text)
        return text
    for source in sorted((root/'docs/case-studies').glob('*.md')):
        story=[Paragraph('Contrastive Local Learning Networks',project_style)];paragraph=[];table_rows=[]
        def flush_paragraph():
            if paragraph:story.append(Paragraph(inline(' '.join(paragraph)),body));paragraph.clear()
        def flush_table():
            if not table_rows:return
            data=[[Paragraph(inline(cell),small) for cell in row] for row in table_rows]
            table=Table(data,colWidths=[506/len(data[0])]*len(data[0]),repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eee9dc')),('VALIGN',(0,0),(-1,-1),'TOP'),
                                      ('BOTTOMPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),
                                      ('LINEBELOW',(0,0),(-1,-1),.4,colors.HexColor('#d8ded8'))]))
            story.extend([table,Spacer(1,9)]);table_rows.clear()
        for line in source.read_text().splitlines()+['']:
            if line.startswith('|'):
                flush_paragraph()
                cells=[x.strip() for x in line.strip('|').split('|')]
                if not all(re.fullmatch(r'[- :]+',cell) for cell in cells):table_rows.append(cells)
                continue
            flush_table()
            image=re.fullmatch(r'!\[([^]]*)\]\(([^)]+)\)',line)
            if image:
                flush_paragraph();path=(source.parent/image.group(2)).resolve()
                graphic=Image(str(path));graphic.drawHeight*=506/graphic.drawWidth;graphic.drawWidth=506
                story.extend([graphic,Paragraph(inline(image.group(1)),small),Spacer(1,6)])
            elif line.startswith('# '):
                flush_paragraph();story.append(Paragraph(inline(line[2:]),title))
            elif line.startswith('## '):
                flush_paragraph();story.append(Paragraph(inline(line[3:]),heading))
            elif line.startswith('- '):
                flush_paragraph();story.append(Paragraph('• '+inline(line[2:]),body))
            elif not line.strip():flush_paragraph()
            else:paragraph.append(line)
        def footer(canvas,doc):
            canvas.saveState();canvas.setFont(regular,7);canvas.setFillColor(colors.HexColor('#53625c'))
            canvas.drawString(43,26,'CLLN project | Simulation and verification study | 2 November 2026')
            canvas.drawRightString(568,26,str(doc.page));canvas.restoreState()
        document=SimpleDocTemplate(str(source.with_suffix('.pdf')),pagesize=(612,792),leftMargin=43,rightMargin=43,
                                   topMargin=38,bottomMargin=43,title='Contrastive Local Learning Networks: '+source.read_text().splitlines()[0][2:],author='')
        document.build(story,onFirstPage=footer,onLaterPages=footer)
        print(source.with_suffix('.pdf').name)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    render(parser.parse_args().root)
