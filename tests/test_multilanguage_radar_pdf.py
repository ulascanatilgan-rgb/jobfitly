"""Regression coverage for multi-language choices, returning from PDFs, and animated profile."""
import io
import shutil
import subprocess
from pathlib import Path

import app
import job_search


def test_multiple_languages_include_both_english_and_french():
    assert job_search.selected_languages("English, French") == {"english","french"}
    assert job_search.selected_languages("English") == {"english"}
    assert job_search.selected_languages("") == set()
    assert job_search.selected_languages(["English","German","English"]) == {"english","german"}


def test_language_requirements_detect_only_explicit_mandates():
    assert job_search.required_languages("Fluent French required.")=={"french"}
    assert job_search.required_languages("Dutch is mandatory for this position.")=={"dutch"}
    assert job_search.required_languages("You will collaborate with our French-speaking team.")==set()


def test_cv_search_applies_selected_languages_to_feed_jobs(tmp_path,monkeypatch):
    monkeypatch.setattr(app,"DB",tmp_path/"languages.sqlite3")
    app.init_db()
    with app.conn() as db:
        uid=db.execute("INSERT INTO users(email,password_hash,created_at) VALUES(?,?,?)",
            ("candidate@example.org","test-hash",app.now())).lastrowid
        db.execute("INSERT INTO profiles(user_id,cv_text,cv_name,language,updated_at) VALUES(?,?,?,?,?)",
            (uid,"Taylor Morgan\nOperations manager. Managed operations processes, "
             "project reporting, coordination and stakeholder communications.",
             "resume.txt","English, French",app.now()))
    jobs=[]
    for i in range(7):
        jobs.append({
            "title":"Operations Manager","company":f"Company {i}","external_id":f"job-{i}",
            "description":("Management of operations and project reporting; "
                           +("Fluent Dutch required." if i==0 else "Fluent French required.")),
            "url":f"https://jobicy.com/jobs/operations-{i}",
            "city":"Brussels","country":"Belgium","source":"Jobicy","published":app.now()
        })
    monkeypatch.setattr(app,"fetch_candidates",lambda p:(jobs,[]))
    monkeypatch.setattr(app,"_check_live",lambda j:True)
    monkeypatch.setattr(app,"ai_cv_fit",lambda *args:{})
    assert app.run_search(uid)==(5,None,200)
    _,results=app.get_run(uid)
    assert len(results)==5
    assert all(j["external_id"]!="job-0" for j in results)


def test_pdf_inline_preview_and_original_download_are_same_pdf(tmp_path,monkeypatch):
    monkeypatch.setattr(app,"DB",tmp_path/"preview.sqlite3")
    app.init_db()
    cv=("Taylor Morgan\nOperations Manager | Finance\nPROFILE\nOperations manager "
        "with extensive reporting and project coordination experience.\n"
        "PROFESSIONAL EXPERIENCE\nOperations Manager | Example Company | 2021-2026\n"
        "Managed financial operations and reporting.")
    with app.conn() as db:
        uid=db.execute("INSERT INTO users(email,password_hash,created_at) VALUES(?,?,?)",
            ("pdf-user@example.org","test-hash",app.now())).lastrowid
        db.execute("INSERT INTO profiles(user_id,name,cv_text,cv_name,updated_at) VALUES(?,?,?,?,?)",
                   (uid,"Taylor Morgan",cv,"resume.txt",app.now()))
        jid=db.execute("INSERT INTO jobs(user_id,external_id,title,company,city,country,description,url,source,published,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (uid,"job-001","Operations Manager","Example Employer","Brussels","Belgium",
             "Operations management and stakeholder reporting.",
             "https://jobs.example.org/openings/001","Test",app.now(),app.now())).lastrowid
        db.execute("INSERT INTO kits(user_id,job_id,motivation,cv,updated_at) VALUES(?,?,?,?,?)",
            (uid,jid,"A concise motivation draft for this role.",
             "Taylor Morgan\nPROFILE\nOperations management and reporting.\n"
             "PROFESSIONAL EXPERIENCE\nOperations Manager | Example Company | 2021-2026\n"
             "- Coordinated stakeholder reporting.\nEDUCATION\nBusiness Administration",
             app.now()))
    client=app.app.test_client()
    with client.session_transaction() as sess:
        sess["uid"]=uid
    inline=client.get(f"/api/kit/{jid}/download/cv?view=1")
    original=client.get(f"/api/kit/{jid}/download/cv")
    assert inline.status_code==200 and original.status_code==200
    assert inline.data.startswith(b"%PDF") and original.data.startswith(b"%PDF")
    assert "inline" in inline.headers["Content-Disposition"]
    assert "attachment" in original.headers["Content-Disposition"]
    assert inline.headers["Cache-Control"]=="private, no-store"


def test_monkey_and_radar_and_pdf_back_controls_present():
    root=Path(__file__).resolve().parents[1]
    html=(root/"templates/index.html").read_text()
    js=(root/"static/app.js").read_text()
    css=(root/"static/style.css").read_text()
    assert "monkey-rope-band" in html and "monkey-rope-line" in html
    assert "monkey-traverse" in css and "monkey-swinging" in html
    assert "renderWorkStyleRadar" in js and "radar-surface" in js
    assert "job matching" in js and "20 responses" in js
    assert "pdf-preview-screen" in js
    assert "Back to JobFitly" in js and "closePdfPreview()" in js
    assert "languagePicker('search-languages',p.language)" in js
    assert "languagePicker('onboard-languages',p.language)" in js
    assert "chosenLanguages('search-languages')" in js
    assert "chosenLanguages('onboard-languages')" in js


def test_frontend_javascript_is_syntactically_valid():
    if shutil.which("node") is None:
        return
    root=Path(__file__).resolve().parents[1]
    for filename in ("static/app.js","static/flow.js"):
        completed=subprocess.run(["node","--check",str(root/filename)],
                                 stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=8)
        assert completed.returncode==0,completed.stderr
