"""JobFitly's established polished navy-sidebar CV template.

A source-CV identity panel + clean career narrative; no generic CONTACT heading,
no fabricated personal facts and no layout switching when content spans pages.
"""
import datetime
import html
import io
import re
from zoneinfo import ZoneInfo

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.pdfbase.pdfmetrics import stringWidth

W,H=A4
NAVY=colors.HexColor("#293D50")
INK=colors.HexColor("#151515")
MUTED=colors.HexColor("#656565")
BURGUNDY=colors.HexColor("#850D45")
WHITE=colors.white
RULE=colors.HexColor("#D8DADD")
PANEL=174
X=195
RIGHT=W-X-42
SECTIONS={
 "PROFILE":"PROFILE","SUMMARY":"PROFILE","PROFESSIONAL SUMMARY":"PROFILE",
 "EXPERIENCE":"PROFESSIONAL EXPERIENCE","WORK EXPERIENCE":"PROFESSIONAL EXPERIENCE",
 "PROFESSIONAL EXPERIENCE":"PROFESSIONAL EXPERIENCE","CAREER HISTORY":"PROFESSIONAL EXPERIENCE",
 "RELEVANT EXPERIENCE":"PROFESSIONAL EXPERIENCE",
 "PROJECTS":"PROJECTS","EDUCATION":"EDUCATION","CERTIFICATIONS":"CERTIFICATIONS",
 "CERTIFICATES":"CERTIFICATIONS","QUALIFICATIONS":"CERTIFICATIONS",
 "SKILLS":"SKILLS","KEY SKILLS":"SKILLS","CORE SKILLS":"SKILLS",
 "LANGUAGES":"LANGUAGES","ADDITIONAL INFORMATION":"ADDITIONAL INFORMATION",
 "ACHIEVEMENTS":"ACHIEVEMENTS"
}

def _plain(value):return str(value or "").strip()
def _cut(value,font,size,width):
    txt=_plain(value)
    if stringWidth(txt,font,size)<=width:return txt
    while txt and stringWidth(txt+"…",font,size)>width:txt=txt[:-1]
    return txt.rstrip()+"…"

def _para(text,fs=8.5,leading=12.2,bold=False,color=INK):
    return Paragraph(html.escape(_plain(text)).replace("\n","<br/>"),
      ParagraphStyle("jobfitlycv",fontName="Helvetica-Bold" if bold else "Helvetica",
        fontSize=fs,leading=leading,textColor=color,spaceAfter=0,allowWidows=0,allowOrphans=0))

def _sections(cv_text,name):
    out={};section="PROFILE"
    raw=_plain(cv_text).replace("\r\n","\n")
    for line in raw.splitlines():
        line=line.strip()
        if not line:continue
        if line.casefold()==name.casefold():continue
        lower=line.casefold()
        if lower.startswith(("target role:","application:","tailored cv","curriculum vitae","candidate name:")):continue
        if lower.startswith(("contact:","email:","e-mail:","phone:","mobile:","address:","linkedin:","website:")):continue
        heading=line.rstrip(":").strip().upper()
        if heading in SECTIONS:
            section=SECTIONS[heading]
            out.setdefault(section,[])
        elif heading in ("CONTACT","PERSONAL DETAILS"):
            section="IGNORED_PERSONAL_DETAILS"
        elif section!="IGNORED_PERSONAL_DETAILS":
            out.setdefault(section,[]).append(line)
    return {k:v for k,v in out.items() if v}

def tailored_cv_pdf(name,role,company,cv_text,city="",email="",details=None):
    """Generate the original navy/white one-page layout; continue the SAME design if needed."""
    details=dict(details or {})
    name=_plain(details.get("name") or name) or "Applicant"
    role=_plain(role)
    company=_plain(company)
    date=datetime.datetime.now(ZoneInfo("Europe/Brussels")).strftime("%d %B %Y")
    sections=_sections(cv_text,name)
    skills=sections.pop("SKILLS",[])
    languages=sections.pop("LANGUAGES",[])
    if not sections:sections={"PROFILE":[_plain(cv_text)]}
    section_items=list(sections.items())
    info=[
      details.get("location") or city,
      details.get("email") or email,
      details.get("phone"),
      details.get("linkedin"),
      details.get("website"),
      details.get("nationality")
    ]
    info=[_plain(x) for x in info if _plain(x)]
    def side_groups():
        groups=[]
        if info:groups.append(("",info))
        if skills:groups.append(("SKILLS",skills))
        if languages or details.get("languages"):
            groups.append(("LANGUAGES",languages or [details["languages"]]))
        return groups
    buf=io.BytesIO()
    c=canvas.Canvas(buf,pagesize=A4,pageCompression=1)
    c.setTitle(f"CV | {name} | {role}")
    c.setAuthor(name)
    page=0
    def paint_page():
        nonlocal page
        page+=1
        c.setFillColor(NAVY);c.rect(0,0,PANEL,H,stroke=0,fill=1)
        c.setStrokeColor(colors.HexColor("#718595"));c.setLineWidth(.65)
        c.line(24,H-56,PANEL-24,H-56)
        side_y=H-80
        for title,values in side_groups():
            if title:
                side_y-=7
                if side_y<75:break
                c.setFillColor(colors.HexColor("#E5EDF2"));c.setFont("Helvetica-Bold",8)
                c.drawString(24,side_y,_cut(title,"Helvetica-Bold",8,PANEL-47))
                side_y-=17
            for line in values:
                p=_para(line,7.7,10.4,color=WHITE)
                _,height=p.wrap(PANEL-48,500)
                if side_y-height<65:
                    break
                p.drawOn(c,24,side_y-height)
                side_y-=height+7
            side_y-=15
        c.setFillColor(MUTED);c.setFont("Helvetica",8)
        c.drawRightString(W-42,H-30,date)
        c.setFillColor(INK);c.setFont("Helvetica-Bold",17)
        c.drawString(X,H-49,_cut(name,"Helvetica-Bold",17,RIGHT))
        c.setFillColor(MUTED);c.setFont("Helvetica",9)
        c.drawString(X,H-66,_cut(role,"Helvetica",9,RIGHT))
        c.setFillColor(BURGUNDY);c.setFont("Helvetica",8)
        c.drawString(X,H-81,_cut(company,"Helvetica",8,RIGHT))
        c.setStrokeColor(RULE);c.setLineWidth(.75)
        c.line(X,H-91,W-42,H-91)
        c.line(X,47,W-42,47)
        c.setFillColor(MUTED);c.setFont("Helvetica",7)
        c.drawRightString(W-42,33,str(page))
        return H-113

    y=paint_page()
    for section,rows in section_items:
        first=True
        for row in rows:
            is_bullet=bool(re.match(r"^[•*\-]\s+",row))
            cleaned=re.sub(r"^[•*\-]\s+","",row).strip()
            if is_bullet:cleaned="•  "+cleaned
            job_line=(not is_bullet and ((" | " in cleaned or " — " in cleaned or " – " in cleaned)
                and len(cleaned)<120))
            fs=8.5;leading=12.1
            para=_para(cleaned,fs,leading,bold=job_line)
            _,ph=para.wrap(RIGHT,750)
            if first:
                if y-(18+ph+5)<62:
                    c.showPage();y=paint_page()
                c.setFillColor(BURGUNDY);c.setFont("Helvetica-Bold",9.2)
                c.drawString(X,y,_cut(section,"Helvetica-Bold",9.2,RIGHT))
                y-=18;first=False
            if y-ph-5<62:
                c.showPage();y=paint_page()
                c.setFillColor(BURGUNDY);c.setFont("Helvetica-Bold",9.2)
                c.drawString(X,y,_cut(section+" (continued)","Helvetica-Bold",9.2,RIGHT))
                y-=19
            if ph>y-61:
                # Split unusual large paragraphs into smaller source-preserving blocks.
                words=cleaned.split()
                lines=[];part=""
                for word in words:
                    candidate=(part+" "+word).strip()
                    q=_para(candidate,fs,leading,bold=job_line);_,qh=q.wrap(RIGHT,750)
                    if qh>180 and part:
                        lines.append(part);part=word
                    else:part=candidate
                if part:lines.append(part)
                for segment in lines:
                    q=_para(segment,fs,leading,bold=job_line);_,qh=q.wrap(RIGHT,750)
                    if y-qh-6<62:
                        c.showPage();y=paint_page()
                    q.drawOn(c,X,y-qh);y-=qh+5
            else:
                para.drawOn(c,X,y-ph)
                y-=ph+5
        y-=10
    c.showPage();c.save()
    return buf.getvalue()
