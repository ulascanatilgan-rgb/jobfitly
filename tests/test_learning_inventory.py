"""End-to-end zero-extra-service inventory, Career DNA and JobFitly Learns tests."""
import datetime
import json
import os
import subprocess
from pathlib import Path

import app
import career_dna
import shared_inventory


def profile_user(tmp_path,monkeypatch):
 monkeypatch.setattr(app,"DB",tmp_path/"learning.sqlite3")
 app.init_db()
 cv=("Taylor Morgan\nOPERATIONS MANAGER\nManaged banking operations, audit processes, "
     "financial reporting, project coordination and stakeholder relationships across "
     "business teams. Led process improvement projects and risk controls.")
 with app.conn() as c:
  uid=c.execute("INSERT INTO users(email,password_hash,created_at) VALUES(?,?,?)",
                ("test@example.org","hash",app.now())).lastrowid
  c.execute("INSERT INTO profiles(user_id,cv_text,cv_name,city,country,updated_at) VALUES(?,?,?,?,?,?)",
            (uid,cv,"cv.txt","Brussels","Belgium",app.now()))
 return uid,cv


def vacancy(i,source="Greenhouse"):
 return {"external_id":f"{source}-{i}","title":"Operations Manager",
   "company":f"Employer {i}","city":"Brussels","country":"Belgium",
   "description":"Banking operations, project coordination, reporting, "
                 "stakeholder relations and business process controls.",
   "url":f"https://careers.example.org/jobs/{source}/{i}",
   "source":source,"published":"","location_label":"Brussels, Belgium"}


def test_career_dna_uses_only_cv_evidence():
 cv=("A person coordinated financial reporting, risk controls and stakeholder "
     "management within banking operations. Led project management delivery.")
 dna=career_dna.career_dna(cv)
 names=[r["name"] for r in dna["role_families"]]
 assert "Finance & banking" in names
 assert "Risk & compliance" in names
 assert "Project & programme" in names
 assert "Stakeholder management" in dna["transferable_skills"]
 assert "Healthcare" not in names
 assert career_dna.role_similarity(vacancy(1),dna)>0


def test_shared_ats_caches_once_for_all_users(tmp_path,monkeypatch):
 db=tmp_path/"inventory.sqlite3"
 count=[]
 monkeypatch.setattr(shared_inventory,"_boards",lambda:[("greenhouse","a","Company A"),
                                                       ("lever","b","Company B"),
                                                       ("ashby","c","Company C")])
 def fake(board):
  count.append(board[0])
  return [vacancy(len(count),board[0].title())]
 monkeypatch.setattr(shared_inventory,"_fetch_board",fake)
 monkeypatch.setattr(shared_inventory,"_licensed_adzuna",lambda:False)
 first=shared_inventory.refresh_shared(db,{"country":"Belgium"})
 second=shared_inventory.refresh_shared(db,{"country":"Belgium"})
 assert len(count)==3
 assert len(first)==3 and len(second)==3
 assert {item["url"] for item in first}=={item["url"] for item in second}
 assert not shared_inventory.shared_jobs(db,"Germany")
 assert not any("Taylor" in str(x) for x in second)


def test_api_not_for_me_removes_rejected_job_and_refills_from_reserves(tmp_path,monkeypatch):
 uid,cv=profile_user(tmp_path,monkeypatch)
 monkeypatch.setattr(app,"fetch_candidates",lambda p:([vacancy(i) for i in range(9)],[]))
 monkeypatch.setattr(app,"ai_cv_fit",lambda *args:{})
 monkeypatch.setattr(app,"_check_live",lambda job:True)
 assert app.run_search(uid)==(5,None,200)
 _,start=app.get_run(uid)
 assert len(start)==5
 with app.conn() as c:
  assert c.execute("SELECT COUNT(*) FROM run_jobs").fetchone()[0]>=6
 client=app.app.test_client()
 with client.session_transaction() as sess:
  sess["uid"]=uid;sess["_csrf"]="test-csrf"
 rejected=start[0]
 response=client.post(f"/api/jobs/{rejected['id']}/not-for-me",
       headers={"X-CSRF-Token":"test-csrf"})
 assert response.status_code==200
 assert response.json["learned"] is True
 after=response.json["jobs"]
 assert len(after)==5
 assert rejected["id"] not in [job["id"] for job in after]
 assert app.feedback_penalty(rejected,app.feedback_for(uid))==100
 undone=client.delete(f"/api/jobs/{rejected['id']}/not-for-me",
       headers={"X-CSRF-Token":"test-csrf"})
 assert undone.status_code==200
 assert rejected["id"] in [job["id"] for job in undone.json["jobs"]]


def test_cached_preview_never_shares_cv_or_disliked_jobs(tmp_path,monkeypatch):
 uid,_=profile_user(tmp_path,monkeypatch)
 with app.conn() as c:
  for i in range(7):
   v=vacancy(i)
   c.execute("""INSERT INTO shared_jobs(
    url,source,title,company,city,country,description,published,
    location_label,external_id,fetched_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
    (v["url"],v["source"],v["title"],v["company"],v["city"],v["country"],
     v["description"],v["published"],v["location_label"],v["external_id"],
     int(datetime.datetime.now(datetime.timezone.utc).timestamp())))
  c.execute("INSERT INTO job_feedback(user_id,url,title,company,created_at) VALUES(?,?,?,?,?)",
            (uid,vacancy(0)["url"],"Operations Manager","Employer 0",app.now()))
 preview=app.preview_candidates(uid)
 assert len(preview)==5
 assert vacancy(0)["url"] not in [j["url"] for j in preview]
 assert all("cv_text" not in j for j in preview)


def test_adzuna_never_calls_api_without_commercial_permission(monkeypatch):
 monkeypatch.setenv("ADZUNA_APP_ID","fake")
 monkeypatch.setenv("ADZUNA_APP_KEY","fake")
 monkeypatch.delenv("ADZUNA_COMMERCIAL_LICENSE_CONFIRMED",raising=False)
 assert not shared_inventory._licensed_adzuna()


def test_new_frontend_controls_are_present_and_valid():
 root=Path(__file__).resolve().parents[1]
 js=(root/"static/app.js").read_text()
 flow=(root/"static/flow.js").read_text()
 css=(root/"static/style.css").read_text()
 assert "Not for me" in js and "rejectJob(id)" in js
 assert "Career DNA" in js and "renderCareerDNA" in js
 assert "/api/jobs/preview" in flow and "Early matches" in flow
 assert ".not-for-me" in css and ".find-preview" in css
 for name in ("static/app.js","static/flow.js"):
  import shutil
  if shutil.which("node"):
   result=subprocess.run(["node","--check",str(root/name)],
     capture_output=True,text=True,timeout=8)
   assert result.returncode==0,result.stderr
