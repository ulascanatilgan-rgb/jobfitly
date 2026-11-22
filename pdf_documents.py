"""Premium JobFitly A4 application PDFs. Template: user's uploaded motivation sample.

Generated text must be reviewed by the applicant; visual formatting is deterministic.
"""
import datetime
import html
import io
import re
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pathlib import Path as FontPath
import reportlab
_FONTDIR=FontPath(reportlab.__file__).resolve().parent / "fonts"
for _font, _file in (("CVUnicode", "Vera.ttf"), ("CVUnicodeBold", "VeraBd.ttf")):
    if _font not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(_font,str(_FONTDIR / _file)))
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, HRFlowable

INK = colors.HexColor("#181818")
MUTED = colors.HexColor("#565656")
BURGUNDY = colors.HexColor("#850D45")
RULE = colors.HexColor("#DDDDDD")
LEFT = 54
RIGHT = 54
W, H = A4


def _clean(value):
    return str(value or "").strip()


def _fit_text(value,font,size,width):
    value=_clean(value)
    if stringWidth(value,font,size)<=width:return value
    while value and stringWidth(value+'...',font,size)>width:value=value[:-1]
    return value.rstrip()+'...'


def _xml(value):
    return html.escape(_clean(value)).replace("\n", "<br/>")


def _date():
    return datetime.datetime.now(ZoneInfo("Europe/Brussels")).strftime("%d %B %Y")


def _paragraph(text, font_size, leading, bold=False, color=INK):
    return Paragraph(_xml(text), ParagraphStyle(
        "fitly", fontName="CVUnicodeBold" if bold else "CVUnicode",
        fontSize=font_size, leading=leading, textColor=color,
        allowWidows=0, allowOrphans=0
    ))


def _extract_motivation_sections(content):
    """Understand numbered heading lines followed by prose, like the user's PDF."""
    raw=_clean(content)
    lines=raw.replace("\r\n","\n").replace("\r","\n").split("\n")
    intro=[]; sections=[]; current=None
    for line in lines:
        line=line.strip()
        if not line:
            continue
        match=re.match(r"^([1-7])[.)]\s+(.+)",line)
        if match:
            if current: sections.append(current)
            current={"num":int(match.group(1)),"heading":match.group(2).strip(),"body":[]}
        elif current is None:
            if line.upper().startswith(("MOTIVATION","TARGET ROLE:")):continue
            intro.append(line)
        else:
            current["body"].append(line)
    if current:sections.append(current)
    # A one-line point may contain the heading and full body. Keep all words.
    for item in sections:
        if not item["body"]:
            split=re.split(r"\s+[-–—:]\s+",item["heading"],maxsplit=1)
            if len(split)==2:
                item["heading"],body=split
                item["body"].append(body)
        item["body"]=" ".join(item["body"])
    if len(sections)!=7 or [s["num"] for s in sections]!=list(range(1,8)):
        raise ValueError("Motivation must contain precisely seven numbered points, 1 through 7.")
    text=" ".join(intro).strip()
    return text, sections


def motivation_pdf(name, role, company, text, city="", email=""):
    """Render an Egmont-style one-page A4 PDF with auto-fit and honest content."""
    name=_clean(name) or "Applicant"
    role=_clean(role)
    company=_clean(company)
    intro,sections=_extract_motivation_sections(text)
    if not intro:
        intro="I am interested in this opportunity and would welcome the chance to discuss how my experience matches the requirements of the role."
    content_width=W-LEFT-RIGHT
    date=_date()
    selections=((9.3,14.2,14.5),(8.9,13.6,11),(8.5,13.0,9),(8.1,12.1,7))
    chosen=None
    for fs,leading,gap in selections:
        parts=[]
        ip=_paragraph(intro,fs,leading)
        _,ih=ip.wrap(content_width,700)
        used=ih+22
        for item in sections:
            number=_paragraph(item["heading"],fs+0.25,leading,True)
            _,hh=number.wrap(content_width-38,500)
            body=_paragraph(item["body"],fs,leading)
            _,bh=body.wrap(content_width-38,600)
            row_h=max(18,hh)+bh+(5 if item["body"] else 0)
            used+=row_h+gap
            parts.append((number,hh,body,bh,row_h))
        # Available below the document heading and above fixed footer.
        if used<=H-238-92:
            chosen=(fs,leading,gap,parts,ip,ih)
            break
    if not chosen:
        raise ValueError("Motivation text is too long for the one-page professional template.")
    fs,leading,gap,parts,ip,ih=chosen
    stream=io.BytesIO()
    c=canvas.Canvas(stream,pagesize=A4,pageCompression=1)
    c.setTitle(f"Motivation | {role} | {company}")
    c.setAuthor(name)
    # Top band: personal identity and today's date.
    c.setFillColor(INK);c.setFont("CVUnicodeBold",10.8)
    c.drawString(LEFT,H-53,name[:76])
    c.setFillColor(MUTED);c.setFont("CVUnicode",9.2)
    c.drawRightString(W-RIGHT,H-53,date)
    c.setStrokeColor(RULE);c.setLineWidth(0.75)
    c.line(LEFT,H-69,W-RIGHT,H-69)
    c.setFillColor(INK);c.setFont("CVUnicodeBold",22)
    c.drawString(LEFT,H-106,"MOTIVATION")
    c.setFillColor(INK);c.setFont("CVUnicodeBold",11.4)
    # Long role/company text wraps without overflowing.
    rolep=_paragraph(role,11.2,14.7,True)
    _,roleh=rolep.wrap(content_width,80)
    rolep.drawOn(c,LEFT,H-125-roleh)
    cop=_paragraph(company,10.2,14,color=MUTED)
    _,coh=cop.wrap(content_width,80)
    cop.drawOn(c,LEFT,H-130-roleh-coh)
    y=H-152-roleh-coh
    ip.drawOn(c,LEFT,y-ih)
    y-=ih+22
    for item,(number,hh,body,bh,rowh) in zip(sections,parts):
        c.setFillColor(BURGUNDY);c.setFont("CVUnicodeBold",10)
        c.drawString(LEFT,y-11,f'{item["num"]}.')
        number.drawOn(c,LEFT+30,y-hh)
        y-=max(18,hh)
        if item["body"]:
            y-=3
            body.drawOn(c,LEFT+30,y-bh)
            y-=bh+gap
        else:y-=gap
    c.setStrokeColor(RULE);c.setLineWidth(0.75)
    c.line(LEFT,75,W-RIGHT,75)
    c.setFillColor(INK);c.setFont("CVUnicodeBold",9.5)
    c.drawString(LEFT,58,name[:92])
    detail=" · ".join(v for v in (_clean(city),_clean(email)) if v)
    if detail:
        c.setFillColor(MUTED);c.setFont("CVUnicode",8.2)
        if stringWidth(detail,"CVUnicode",8.2)>content_width:
            detail=detail[:100]
        c.drawString(LEFT,45,detail)
    c.showPage();c.save()
    return stream.getvalue()


def tailored_cv_pdf(name,role,company,cv_text,city="",email=""):
    """Multi-page, legible professional CV. Never inserts experience not in generated text."""
    name=_clean(name) or "Applicant"
    stream=io.BytesIO()
    width=W-LEFT-RIGHT
    doc=SimpleDocTemplate(stream,pagesize=A4,leftMargin=LEFT,rightMargin=RIGHT,
        topMargin=104,bottomMargin=67,title=f"CV | {name} | {role}")
    body=ParagraphStyle("cv-body",fontName="CVUnicode",fontSize=9.2,leading=14.4,
        textColor=INK,spaceAfter=5)
    heading=ParagraphStyle("cv-head",fontName="CVUnicodeBold",fontSize=10.2,leading=15,
        textColor=BURGUNDY,spaceBefore=13,spaceAfter=6,keepWithNext=True)
    bullet=ParagraphStyle("cv-bullet",parent=body,leftIndent=11,firstLineIndent=-7)
    detail=ParagraphStyle("cv-detail",parent=body,textColor=MUTED,fontSize=8.5)
    story=[]
    for index,line in enumerate(_clean(cv_text).splitlines()):
        line=line.strip()
        if not line:continue
        if index==0 and line.casefold()==name.casefold():continue
        if line.casefold().startswith(("target role:","tailored cv","curriculum vitae")):continue
        if re.match(r"^[•*\-]\s+",line):
            story.append(Paragraph("&#8226; "+_xml(re.sub(r"^[•*\-]\s+","",line)),bullet))
        elif (len(line)<=85 and (
                line.isupper() and len(line)>3 or
                line.strip().rstrip(":").casefold() in
                {"professional summary","summary","experience","professional experience",
                 "work experience","education","certifications","skills","key skills",
                 "languages","career history","qualifications","projects","achievements"})):
            story.append(Paragraph(_xml(line.rstrip(":")),heading))
        else:story.append(Paragraph(_xml(line),body))
    if not story:story.append(Paragraph("CV content was not provided.",body))
    def header(c,document):
        c.saveState()
        c.setFillColor(INK);c.setFont("CVUnicodeBold",18)
        c.drawString(LEFT,H-46,_fit_text(name,"CVUnicodeBold",18,width))
        c.setFillColor(INK);c.setFont("CVUnicode",9)
        c.drawString(LEFT,H-63,_fit_text(role,"CVUnicode",9,width))
        c.setFillColor(MUTED);c.setFont("CVUnicode",8.5)
        c.drawString(LEFT,H-78,_fit_text("Application to "+_clean(company),"CVUnicode",8.5,width))
        c.setStrokeColor(RULE);c.setLineWidth(.8)
        c.line(LEFT,H-91,W-RIGHT,H-91)
        c.setStrokeColor(RULE);c.line(LEFT,53,W-RIGHT,53)
        c.setFillColor(MUTED);c.setFont("CVUnicode",8)
        contact=" · ".join(v for v in (_clean(city),_clean(email)) if v)
        c.drawString(LEFT,40,contact[:96])
        c.drawRightString(W-RIGHT,40,str(document.page))
        c.restoreState()
    doc.build(story,onFirstPage=header,onLaterPages=header)
    return stream.getvalue()
