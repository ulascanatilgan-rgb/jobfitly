"""Prevent locations from becoming candidate names, and keep PDF UX reliable."""
import io
import json
import datetime
from pathlib import Path
import pytest
from cv_profile import extract_cv_details, is_plausible_person_name
import app as mod
from pdf_cv_sidebar import tailored_cv_pdf
from pypdf import PdfReader

CV_WITH_LOCATION_FIRST = """Kapellen Belgium
Ulas Atılgan
IAM Expert | Financial Services
ulas.atilgan@example.com
Phone: +32 499 22 33 44
PROFILE
Security governance and financial operations professional.
PROFESSIONAL EXPERIENCE
IAM Expert | Example Bank | 2019–present
Led access governance reporting and collaborated across international teams.
EDUCATION
MSc Information Technologies
"""

def test_extractor_prefers_person_to_location():
    details=extract_cv_details(CV_WITH_LOCATION_FIRST)
    assert details["name"]=="Ulas Atılgan"
    assert details["email"]=="ulas.atilgan@example.com"
    assert not is_plausible_person_name("Kapellen Belgium")
    assert not is_plausible_person_name("Operations Manager")
    assert not is_plausible_person_name("Belgium Antwerp")
    assert is_plausible_person_name("Ulas Atılgan")

def test_only_place_and_job_title_are_not_names():
    details=extract_cv_details("Kapellen Belgium\nOperations Manager\nPROFILE\nBusiness professional.")
    assert "name" not in details

def test_legacy_wrong_profile_is_healed_and_old_kits_are_invalidated(tmp_path,monkeypatch):
    monkeypatch.setattr(mod,"DB",tmp_path/"new.sqlite3")
    mod.init_db()
    with mod.conn() as c:
        uid=c.execute("INSERT INTO users(email,password_hash,created_at) VALUES(?,?,?)",
            ("candidate@example.org","hash",mod.now())).lastrowid
        c.execute("INSERT INTO profiles(user_id,name,cv_name,cv_text,cv_details,updated_at) VALUES(?,?,?,?,?,?)",
            (uid,"Kapellen Belgium","cv.txt",CV_WITH_LOCATION_FIRST,
             json.dumps({"name":"Kapellen Belgium","location":"Kapellen Belgium"}),mod.now()))
    p=mod.profile_for(uid)
    assert p["name"]=="Ulas Atılgan"
    assert p["cv_details"]["name"]=="Ulas Atılgan"
    with mod.conn() as c:
        assert c.execute("SELECT name FROM profiles WHERE user_id=?",(uid,)).fetchone()["name"]=="Ulas Atılgan"

def test_ambiguous_source_requires_manual_confirmation(tmp_path,monkeypatch):
    monkeypatch.setattr(mod,"DB",tmp_path/"new.sqlite3")
    mod.init_db()
    with mod.conn() as c:
        uid=c.execute("INSERT INTO users(email,password_hash,created_at) VALUES(?,?,?)",
            ("candidate@example.org","hash",mod.now())).lastrowid
        c.execute("INSERT INTO profiles(user_id,name,cv_text,cv_details,updated_at) VALUES(?,?,?,?,?)",
            (uid,"Kapellen Belgium","Kapellen Belgium\nPROFILE\nAudit and compliance work.",
             '{"name":"Kapellen Belgium"}',mod.now()))
    profile=mod.profile_for(uid)
    assert profile["name"]=="" and profile["name_needs_confirmation"]
    with pytest.raises(ValueError,match="confirm"):mod.verified_cv_details(uid,require_name=True)
    client=mod.app.test_client()
    with client.session_transaction() as session:
        session["uid"]=uid
        session["_csrf"]="testing-token"
    bad=client.post("/api/profile/name",json={"name":"Kapellen Belgium"},headers={"X-CSRF-Token":"testing-token"})
    assert bad.status_code==400
    good=client.post("/api/profile/name",json={"name":"Ulas Atılgan"},headers={"X-CSRF-Token":"testing-token"})
    assert good.status_code==200
    assert good.get_json()["profile"]["name"]=="Ulas Atılgan"

def test_compact_cv_keeps_prominent_name_on_one_page():
    sections=("Ulas Atılgan\nPROFILE\nFinancial services and operations specialist.\n"
       "PROFESSIONAL EXPERIENCE\nIAM Expert | Example Bank | 2019–present\n"
       "- Managed access governance processes and cross-functional reporting.\n"
       "- Coordinated control improvements and stakeholder communication.\n"
       "Internal Auditor | Other Bank | 2015–2019\n"
       "- Reviewed governance risks and presented findings to leadership.\n"
       "EDUCATION\nMSc Information Technologies\nBA Business Administration\n"
       "CERTIFICATIONS\nCISA; CIA\nSKILLS\nGovernance and risk reporting\nLANGUAGES\nEnglish, Dutch")
    result=tailored_cv_pdf("Ulas Atılgan","Operations Manager","Example Employer",sections,
                           details=extract_cv_details(CV_WITH_LOCATION_FIRST))
    pdf=PdfReader(io.BytesIO(result))
    assert len(pdf.pages)==1
    text=pdf.pages[0].extract_text()
    assert "Ulas Atılgan" in text and "Example Employer" in text
    assert "Kapellen Belgium" not in text.split("Ulas Atılgan")[1].split("PROFESSIONAL EXPERIENCE")[0].split("PROFILE")[0]

def test_animated_hourglass_and_stacked_price():
    root=Path(__file__).resolve().parents[1]
    js=(root/"static"/"app.js").read_text()
    css=(root/"static"/"style.css").read_text()
    assert "kit-hourglass" in js and "kit-preparing" in js
    assert "kit-sand-stream" in css and "kit-hourglass-flip" in css
    assert ".hero-clean-inner .hero-pricing{flex-direction:column" in css
    assert "jobfitly-hero-impact" in css
