"""Tests for search presentation and professional CV PDF fallback."""
import io
from pathlib import Path
from pypdf import PdfReader
import app as mod

def test_results_highest_fit_first(tmp_path,monkeypatch):
    monkeypatch.setattr(mod,'DB',tmp_path/'jobfitly.sqlite3')
    mod.init_db()
    with mod.conn() as c:
        uid=c.execute('INSERT INTO users(email,password_hash,created_at) VALUES(?,?,?)',
                      ('rank@example.org','hash',mod.now())).lastrowid
        rid=c.execute('INSERT INTO daily_runs(user_id,local_day,run_at,state) VALUES(?,?,?,?)',
                      (uid,mod.today(),mod.now(),'complete')).lastrowid
        for position,fit in enumerate((6.2,9.3,7.7),1):
            jid=c.execute('INSERT INTO jobs(user_id,external_id,title,company,city,country,description,url,source,published,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
              (uid,str(position),'Operations Manager','Employer','Brussels','Belgium','Operations role',
               'https://example.org/'+str(position),'OpenAI web search',mod.now(),mod.now())).lastrowid
            c.execute('INSERT INTO run_jobs(run_id,job_id,position,fit,matched_terms) VALUES(?,?,?,?,?)',
                      (rid,jid,position,fit,'[]'))
    _,jobs=mod.get_run(uid)
    assert [j['score'] for j in jobs]==[9.3,7.7,6.2]

def test_search_cards_do_not_show_search_provider():
    root=Path(__file__).resolve().parents[1]
    js=(root/'static/app.js').read_text()
    flow=(root/'static/flow.js').read_text()
    card=js.split('function jobCard(',1)[1].split('function reloadJobs(',1)[0]
    assert 'esc(j.source)' not in card and 'OpenAI web search' not in card
    assert 'b.score' in flow and '.sort(' in flow
    assert 'Update CV · PDF' in js

def test_cv_export_keeps_long_history_without_error():
    body=('Alex Morgan\nPROFILE\nSenior operations professional.\nPROFESSIONAL EXPERIENCE\n'+
          '\n'.join(f'- Verified responsibility for reporting task number {i} across multiple stakeholder teams.'
                    for i in range(1,52))+
          '\n- Final verified project with employer.\nEDUCATION\nBachelor of Business Administration')
    result=mod.render_tailored_cv_pdf('Alex Morgan','Operations Manager','Example Employer',
                                     body,city='Antwerp, Belgium',email='alex@example.org')
    pages=PdfReader(io.BytesIO(result)).pages
    extracted='\n'.join(page.extract_text() for page in pages)
    assert pages and 'Final verified project' in extracted
    assert 'Example Employer' in extracted and 'Alex Morgan' in extracted
