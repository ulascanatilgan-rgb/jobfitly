"""Alternative Next Move: CV evidence, user choice, and nonrestrictive search."""
import json
import shutil
import subprocess
from pathlib import Path

import app
from next_moves import alternative_next_moves, path_title_match, valid_path_titles

CV = (
 "Taylor Morgan\n"
 "Operations Manager at a financial services group, 2019-2025.\n"
 "Led banking operations, coordinated project work and improved business processes.\n"
 "Performed audit and risk controls, managed stakeholder engagement, delivered "
 "cross-functional project coordination, financial analysis and reporting. "
 "Delivered process improvement for payments operations and information security. "
 "Supported customers, client relations and management reporting."
)

def setup_profile(tmp_path,monkeypatch):
 monkeypatch.setattr(app,"DB",tmp_path/"alternate.sqlite3")
 app.init_db()
 with app.conn() as c:
  uid=c.execute("INSERT INTO users(email,password_hash,created_at) VALUES(?,?,?)",
                ("morgan@example.org","hash",app.now())).lastrowid
  c.execute("""INSERT INTO profiles(user_id,cv_name,cv_text,questions,swipes,
    keywords,updated_at) VALUES(?,?,?,?,?,?,?)""",
    (uid,"cv.txt",CV,json.dumps({"analytical":8,"strategy":9,"people":7,
                               "coordination":8,"operations":8}),
     json.dumps({"role_type":["Operations & strategy"],"sector":["Finance"]}),
     "Operations, compliance",app.now()))
 return uid

def job(index,title,description=None):
 return {
  "external_id":f"next-{index}","title":title,"company":f"Employer {index}",
  "city":"Brussels","country":"Belgium","source":"Greenhouse",
  "description":description or (
    "Lead banking operations, project coordination and financial reporting "
    "with stakeholder engagement and process improvement."),
  "url":f"https://careers.example.org/jobs/next-{index}",
  "published":app.now()
 }

def test_three_distinct_exploratory_paths_are_grounded_in_cv():
 from career_dna import career_dna
 dna=career_dna(CV)
 suggestions=alternative_next_moves(CV,dna,{
  "analytical":8,"strategy":9,"people":7,"coordination":8}, {})
 assert len(suggestions)==3
 titles=[entry["title"] for entry in suggestions]
 assert len(set(titles))==3
 assert all(title.lower() not in CV.lower() for title in titles)
 assert all(len(entry["description"].split(". "))>=4 for entry in suggestions)
 assert all(entry["cv_evidence"] for entry in suggestions)
 assert all(0<=entry["evidence_score"]<=100 for entry in suggestions)
 assert all(entry["style_score"] is not None for entry in suggestions)

def test_no_cv_means_no_invented_opportunities():
 assert alternative_next_moves("")==[]
 assert alternative_next_moves("Hello World") == []

def test_invalid_role_titles_cannot_be_injected():
 assert valid_path_titles(["Chief of Staff","Chief of Staff","Fake Surgeon"])==["Chief of Staff"]
 assert valid_path_titles("Chief of Staff")==[]
 assert path_title_match(job(1,"Chief of Staff"),["Chief of Staff"])==1
 assert path_title_match(job(2,"Operations Manager"),["Chief of Staff"])==0

def test_profile_api_persists_recommended_paths_and_removal(tmp_path,monkeypatch):
 uid=setup_profile(tmp_path,monkeypatch)
 suggestions=app.profile_for(uid)["next_moves"]
 assert len(suggestions)==3
 chosen=suggestions[0]["title"]
 client=app.app.test_client()
 with client.session_transaction() as sess:
  sess["uid"]=uid;sess["_csrf"]="token"
 response=client.post("/api/profile",json={"path_keywords":[chosen]},
                      headers={"X-CSRF-Token":"token"})
 assert response.status_code==200,response.json
 p=response.json["profile"]
 assert p["path_keywords"]==[chosen]
 assert p["keywords"]=="Operations, compliance"
 with app.conn() as c:
  assert json.loads(c.execute("SELECT path_keywords FROM profiles WHERE user_id=?",
                              (uid,)).fetchone()[0])==[chosen]
 response=client.post("/api/profile",json={"path_keywords":[]},
                      headers={"X-CSRF-Token":"token"})
 assert response.status_code==200
 assert response.json["profile"]["path_keywords"]==[]
 rejected=client.post("/api/profile",json={"path_keywords":["Unlicensed Doctor"]},
                      headers={"X-CSRF-Token":"token"})
 assert rejected.status_code==400

def test_selected_path_makes_adjacent_title_findable_without_blocking_cv_roles(tmp_path,monkeypatch):
 uid=setup_profile(tmp_path,monkeypatch)
 title=app.profile_for(uid)["next_moves"][0]["title"]
 with app.conn() as c:
  c.execute("UPDATE profiles SET path_keywords=? WHERE user_id=?",(json.dumps([title]),uid))
 jobs=[job(0,title)]+[job(i,"Operations Manager") for i in range(1,9)]
 monkeypatch.setattr(app,"fetch_candidates",lambda p:(jobs,[]))
 monkeypatch.setattr(app,"ai_cv_fit",lambda *args,**kwargs:{})
 monkeypatch.setattr(app,"_check_live",lambda _:True)
 count,error,status=app.run_search(uid)
 assert status==200,(count,error,status)
 assert count==5
 _,found=app.get_run(uid)
 assert any(entry["title"]==title for entry in found)
 assert any(entry["title"]=="Operations Manager" for entry in found)

def test_selected_paths_do_not_act_as_hard_filter(tmp_path,monkeypatch):
 uid=setup_profile(tmp_path,monkeypatch)
 title=app.profile_for(uid)["next_moves"][0]["title"]
 with app.conn() as c:
  c.execute("UPDATE profiles SET path_keywords=? WHERE user_id=?",(json.dumps([title]),uid))
 jobs=[job(i,"Operations Manager") for i in range(8)]
 monkeypatch.setattr(app,"fetch_candidates",lambda p:(jobs,[]))
 monkeypatch.setattr(app,"ai_cv_fit",lambda *args,**kwargs:{})
 monkeypatch.setattr(app,"_check_live",lambda _:True)
 count,error,status=app.run_search(uid)
 assert (count,error,status)==(5,None,200)
 _,found=app.get_run(uid)
 assert len(found)==5
 assert all(entry["title"]=="Operations Manager" for entry in found)

def test_profile_and_keywords_ui_and_syntax():
 root=Path(__file__).resolve().parents[1]
 js=(root/"static/app.js").read_text()
 css=(root/"static/style.css").read_text()
 assert "Alternative Next Move" in js
 assert "renderAlternativeNextMoves" in js
 assert "Add to search" in js
 assert "renderSelectedPathKeywords" in js
 assert "removeAlternativePath" in js
 assert "selected-path-list" in js
 assert "CV strength overlap" in js and "Work-style alignment" in js
 assert ".next-moves-cards" in css and ".selected-path-chip" in css
 if shutil.which("node"):
  done=subprocess.run(["node","--check",str(root/"static/app.js")],
                      capture_output=True,text=True,timeout=8)
  assert done.returncode==0,done.stderr
