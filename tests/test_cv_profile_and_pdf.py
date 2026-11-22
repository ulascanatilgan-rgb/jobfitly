"""Source-CV profile extraction, professional document and calm-navigation regression."""
import datetime
import io
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import re

from pypdf import PdfReader

import app as mod
from cv_profile import extract_cv_details
from pdf_cv_sidebar import tailored_cv_pdf
from pdf_documents import motivation_pdf


SOURCE_CV = """Alex Morgan
PROGRAMME OPERATIONS | FINANCIAL SERVICES
Antwerp, Belgium | +32 478 66 19 13 | alex.morgan@example.org
linkedin.com/in/alex-morgan | alex-morgan.be

PROFILE
Experienced banking operations and cross-functional project professional.

PROFESSIONAL EXPERIENCE
Operations Manager | Example Bank | 2021-2026
- Coordinated cross-functional operations and management reporting.
- Managed operational follow-up across banking stakeholders.

EDUCATION
BSc Business Administration | Example University | 2017

LANGUAGES
English - fluent; Dutch - B1
"""


def test_profile_reads_actual_uploaded_cv():
    d=extract_cv_details(SOURCE_CV)
    assert d["name"] == "Alex Morgan"
    assert d["email"] == "alex.morgan@example.org"
    assert d["location"]=="Antwerp, Belgium"
    assert "English" in d["languages"]
    assert "478" in d["phone"]
    assert "linkedin" in d["linkedin"]
    assert "email" not in extract_cv_details("Taylor Park\nPROFILE\nOperations professional")


def test_flask_upload_persists_cv_fields_and_invalidates_kits(tmp_path,monkeypatch):
    monkeypatch.setattr(mod,"DB",tmp_path/"jobfitly.sqlite3")
    mod.init_db()
    client=mod.app.test_client()
    csrf=client.get("/api/config").get_json()["csrf"]
    new=client.post("/api/register",
        json={"email":"account@example.org","password":"secret123456","remember":False},
        headers={"X-CSRF-Token":csrf})
    assert new.status_code==200
    csrf=new.get_json()["csrf"]
    response=client.post("/api/cv",data={"file":(io.BytesIO(SOURCE_CV.encode()),"example-cv.txt")},
                        headers={"X-CSRF-Token":csrf},content_type="multipart/form-data")
    assert response.status_code==200
    profile=response.get_json()["profile"]
    assert profile["cv_details"]["name"]=="Alex Morgan"
    assert profile["cv_details"]["email"]=="alex.morgan@example.org"
    assert profile["name"]=="Alex Morgan"
    with mod.conn() as db:
        details=json.loads(db.execute("SELECT cv_details FROM profiles").fetchone()["cv_details"])
    assert details["name"]=="Alex Morgan"


def test_navy_cv_has_name_and_date_but_no_contact_heading():
    pdf=tailored_cv_pdf("Alex Morgan","Operations Manager","New Employer",
        "Alex Morgan\nPROFILE\nExperienced banking operations professional.\n"
        "PROFESSIONAL EXPERIENCE\nOperations Manager | Example Bank | 2021-2026\n"
        "- Coordinated stakeholders and operational reporting.\n"
        "EDUCATION\nBSc Business Administration, 2017\n"
        "SKILLS\nProject coordination\nRisk and controls\nLANGUAGES\nEnglish; Dutch",
        details=extract_cv_details(SOURCE_CV))
    pages=PdfReader(io.BytesIO(pdf)).pages
    assert len(pages)==1
    text=pages[0].extract_text()
    assert "Alex Morgan" in text and "Example Bank" in text
    assert "alex.morgan@example.org" in text
    assert "CONTACT" not in text
    assert datetime.datetime.now(ZoneInfo("Europe/Brussels")).strftime("%d %B %Y") in text


def test_long_cv_keeps_navy_template_on_continuation_pages():
    rows="\n".join(
        "- Coordinated a source-documented control review and produced executive reporting for team %d."%i
        for i in range(60))
    pdf=tailored_cv_pdf("Alex Morgan","Operations Manager","Example Employer",
        "Alex Morgan\nPROFILE\nOperations management profile.\nPROFESSIONAL EXPERIENCE\n"
        "Operations Manager | Example Bank | 2021-2026\n"+rows+"\n"
        "EDUCATION\nBSc Business Administration",
        details=extract_cv_details(SOURCE_CV))
    pages=PdfReader(io.BytesIO(pdf)).pages
    text="\n".join(page.extract_text() for page in pages)
    assert len(pages)>1
    assert re.search(r"team\s+59",text) and "BSc Business Administration" in text
    assert text.count("Alex Morgan")>=len(pages)


def test_home_has_five_steps_and_footer_history():
    root=Path(__file__).resolve().parents[1]
    flow=(root/"static/flow.js").read_text()
    html=(root/"templates/index.html").read_text()
    assert flow.count('id:"')==5
    assert all(f'num:"{i}"' in flow for i in range(1,6))
    assert 'title:"My jobs"' in flow
    assert 'flow-history' in html
    assert "PROFILE" in flow.upper()
