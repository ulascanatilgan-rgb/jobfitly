"""JobFitly's established one-page CV aesthetic: navy information panel, white career column.

This template works from text-only uploads. It cannot reproduce a photograph
embedded in a discarded source PDF; the original uploaded CV is not retained.
"""
import html
import io
import re

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.pdfbase.pdfmetrics import stringWidth

W,H=A4
NAVY=colors.HexColor("#293D50")
INK=colors.HexColor("#151515")
MUTED=colors.HexColor("#626262")
BURGUNDY=colors.HexColor("#850D45")
WHITE=colors.white
LINE=colors.HexColor("#D8DADD")
PANEL=174
RIGHT_X=195
RIGHT_W=W-RIGHT_X-42

SECTIONS={
    "PROFILE":"PROFILE",
    "PROFESSIONAL SUMMARY":"PROFILE",
    "SUMMARY":"PROFILE",
    "EXPERIENCE":"PROFESSIONAL EXPERIENCE",
    "WORK EXPERIENCE":"PROFESSIONAL EXPERIENCE",
    "PROFESSIONAL EXPERIENCE":"PROFESSIONAL EXPERIENCE",
    "CAREER HISTORY":"PROFESSIONAL EXPERIENCE",
    "PROJECTS":"PROJECTS",
    "FINANCIAL MARKETS & PERSONAL PROJECTS":"PROJECTS",
    "FINANCIAL MARKETS AND PERSONAL PROJECTS":"PROJECTS",
    "EDUCATION":"EDUCATION",
    "CERTIFICATIONS":"CERTIFICATIONS",
    "CERTIFICATES":"CERTIFICATIONS",
    "SKILLS":"SKILLS",
    "KEY SKILLS":"SKILLS",
    "CORE SKILLS":"SKILLS",
    "LANGUAGES":"LANGUAGES",
}

def _plain(value):
    return str(value or "").strip()

def _fit_text(value,font,size,width):
    value=_plain(value)
    if stringWidth(value,font,size)<=width:return value
    while value and stringWidth(value+'...',font,size)>width:value=value[:-1]
    return value.rstrip()+'...'

def _p(value,size,leading,bold=False,color=INK):
    return Paragraph(html.escape(_plain(value)),ParagraphStyle(
        "cv-panel",fontName="Helvetica-Bold" if bold else "Helvetica",
        fontSize=size,leading=leading,textColor=color
    ))

def _sections(text,name):
    result={"PROFILE":[]};current="PROFILE"
    lines=_plain(text).replace("\r\n","\n").split("\n")
    for index,line in enumerate(lines):
        line=line.strip()
        if not line:continue
        if index<=2 and line.casefold()==_plain(name).casefold():continue
        if line.casefold().startswith(("target role:","application:","tailored cv","curriculum vitae")):continue
        head=line.rstrip(":").strip().upper()
        if head in SECTIONS:
            current=SECTIONS[head]
            result.setdefault(current,[])
        else:
            result.setdefault(current,[]).append(line)
    # A section header must not be rendered without content.
    return {key:value for key,value in result.items() if value}


def _line_style(line,body_size,leading):
    trimmed=line.strip()
    bullet=bool(re.match(r"^[•*\-]\s*",trimmed))
    text=re.sub(r"^[•*\-]\s*","",trimmed) if bullet else trimmed
    if bullet:text="•  "+text
    # Recognize concise employer/role lines without claiming unverifiable new facts.
    job_line=not bullet and ((" | " in text or " — " in text or " – " in text) and len(text)<125)
    return _p(text,body_size,leading,bold=job_line)


def tailored_cv_pdf(name,role,company,cv_text,city="",email=""):
    """Render user's known navy-sidebar style as a single, clean A4 PDF."""
    name=_plain(name) or "Applicant"
    data=_sections(cv_text,name)
    def group(key):
        return data.pop(key,[])
    profile=group("PROFILE")
    skills=group("SKILLS")
    languages=group("LANGUAGES")
    # Professional experience, education, etc. retain the order written by AI.
    if profile:data={"PROFILE":profile,**data}
    elif not data:data={"PROFILE":[cv_text]}
    right_sections=list(data.items())
    fontsize_choices=[(8.6,12.3,10),(8.2,11.7,8),(7.8,11.1,7),(7.5,10.5,6)]
    fit=None
    for fs,leading,gap in fontsize_choices:
        prepared=[];total=0
        for section,lines in right_sections:
            rows=[]
            for line in lines:
                p=_line_style(line,fs,leading)
                _,height=p.wrap(RIGHT_W,600)
                rows.append((p,height))
            h=16+sum(height+3 for _,height in rows)+gap
            total+=h
            prepared.append((section,rows,h))
        if total<=H-161:
            fit=(fs,leading,gap,prepared)
            break
    if fit is None:
        raise ValueError("CV text is too long for an accessible one-page layout.")
    fs,leading,gap,prepared=fit
    buf=io.BytesIO()
    c=canvas.Canvas(buf,pagesize=A4,pageCompression=1)
    c.setTitle(f"CV | {name} | {role}")
    c.setAuthor(name)
    # Fixed left information panel.
    c.setFillColor(NAVY);c.rect(0,0,PANEL,H,stroke=0,fill=1)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold",9.5)
    c.drawString(24,H-48,"PROFILE")
    c.setStrokeColor(colors.HexColor("#748594"));c.setLineWidth(.7)
    c.line(24,H-61,PANEL-24,H-61)
    side_y=H-81
    def sidebar(title,lines):
        nonlocal side_y
        if not lines:return
        side_y-=12
        c.setFillColor(colors.HexColor("#DDE7EE"))
        c.setFont("Helvetica-Bold",8.1)
        c.drawString(24,side_y,title)
        side_y-=12
        for line in lines:
            p=_p(line,8,11,color=WHITE)
            _,h=p.wrap(PANEL-47,350)
            p.drawOn(c,24,side_y-h)
            side_y-=h+7
        side_y-=14
    sidebar("CONTACT",[x for x in (_plain(email),_plain(city)) if x])
    sidebar("SKILLS",skills)
    sidebar("LANGUAGES",languages)
    if side_y<38:
        raise ValueError("CV sidebar is too long for the one-page layout.")
    # Right career column.
    c.setFillColor(INK);c.setFont("Helvetica-Bold",18)
    c.drawString(RIGHT_X,H-45,_fit_text(name,"Helvetica-Bold",18,RIGHT_W))
    c.setFillColor(MUTED);c.setFont("Helvetica",9)
    c.drawString(RIGHT_X,H-61,_fit_text(role,"Helvetica",9,RIGHT_W))
    c.setFillColor(BURGUNDY);c.setFont("Helvetica",8)
    c.drawString(RIGHT_X,H-76,_fit_text("Application to "+_plain(company),"Helvetica",8,RIGHT_W))
    c.setStrokeColor(LINE);c.setLineWidth(.8)
    c.line(RIGHT_X,H-90,W-42,H-90)
    y=H-110
    for section,rows,_ in prepared:
        c.setFillColor(BURGUNDY);c.setFont("Helvetica-Bold",9.1)
        c.drawString(RIGHT_X,y,section[:55])
        y-=16
        for p,h in rows:
            p.drawOn(c,RIGHT_X,y-h)
            y-=h+3
        y-=gap
    c.setStrokeColor(LINE)
    c.line(RIGHT_X,45,W-42,45)
    c.setFillColor(MUTED);c.setFont("Helvetica",7.7)
    c.drawString(RIGHT_X,32,"Application CV  |  Generated from the candidate's CV")
    c.showPage();c.save()
    return buf.getvalue()
