"""Regression tests for multi-select preferences, no repeat searches and compact home radar."""
import json
import subprocess
import shutil
from pathlib import Path

import app
from preferences import preferences_list, normalize_preferences, preference_alignment


def build_user(tmp_path,monkeypatch):
 monkeypatch.setattr(app,"DB",tmp_path/"repeat.sqlite3")
 app.init_db()
 cv=("Taylor Morgan\nEXPERIENCE\nOperations manager, banking and finance professional. "
     "Project coordination, risk controls, reporting, business management, "
     "stakeholder relationships, business operations and strategic planning. "
     "Managed operations and delivered project work across departments.")
 with app.conn() as c:
  uid=c.execute(
   "INSERT INTO users(email,password_hash,created_at) VALUES(?,?,?)",
   ("morgan@example.org","test-hash",app.now())).lastrowid
  c.execute("""INSERT INTO profiles(user_id,cv_name,cv_text,city,country,
    questions,swipes,updated_at) VALUES(?,?,?,?,?,?,?,?)""",
    (uid,"resume.txt",cv,"Brussels","Belgium",
     "{}",
     json.dumps({"role_type":"Operations & strategy","sector":"Finance"}),
     app.now()))
 return uid


def listing(i):
 return {
  "external_id":"multi-"+str(i),"title":"Operations Manager",
  "company":"Employer "+str(i),"city":"Brussels","country":"Belgium",
  "description":"Banking and financial services operations, project coordination, "
                "stakeholder management, risk controls, and reporting.",
  "url":"https://careers.example.org/jobs/multi-"+str(i),
  "published":app.now(),"source":"Greenhouse"
 }


def test_preference_lists_migrate_old_strings_and_validate():
 assert preferences_list("Finance")==["Finance"]
 assert preferences_list(["Finance","Technology","Finance"])==["Finance","Technology"]
 assert preferences_list(["No preference"])==[]
 raw={"sector":["Finance","Technology","Finance"],
      "mode":["Hybrid","Remote"],
      "priority":["No preference"],
      "invalid":["Anything"]}
 allowed={name:choices for name,_,choices in app.SWIPES}
 assert normalize_preferences(raw,allowed)=={
  "sector":["Finance","Technology"],"mode":["Hybrid","Remote"]}


def test_multiple_options_match_either_value_without_hard_exclusion():
 finance={"title":"Financial Operations Manager",
          "description":"Banking, payments, hybrid working with client teams"}
 preferences={"sector":["Finance","Technology"],"mode":["Hybrid","Remote"]}
 assert preference_alignment(finance,preferences)>6
 assert preference_alignment(finance,{"sector":["Healthcare"]})<3
 assert preference_alignment(finance,{}) is None


def test_api_saves_multiple_options_and_migrates_old_profile(tmp_path,monkeypatch):
 uid=build_user(tmp_path,monkeypatch)
 client=app.app.test_client()
 with client.session_transaction() as sess:
  sess["uid"]=uid;sess["_csrf"]="valid"
 assert app.profile_for(uid)["swipes"]=={"role_type":["Operations & strategy"],"sector":["Finance"]}
 result=client.post("/api/profile",json={"swipes":{
  "sector":["Finance","Technology"],"mode":["Hybrid","Remote"],
  "seniority":["Manager","Leadership"],"environment":["No preference"]}},
  headers={"X-CSRF-Token":"valid"})
 assert result.status_code==200
 swipes=result.json["profile"]["swipes"]
 assert swipes=={"sector":["Finance","Technology"],"mode":["Hybrid","Remote"],
                 "seniority":["Manager","Leadership"]}
 with app.conn() as c:
  assert json.loads(c.execute("SELECT swipes FROM profiles WHERE user_id=?",(uid,)).fetchone()[0])==swipes


def test_new_search_excludes_previously_displayed_jobs_even_after_reset(tmp_path,monkeypatch):
 uid=build_user(tmp_path,monkeypatch)
 monkeypatch.setattr(app,"fetch_candidates",lambda profile:([listing(i) for i in range(14)],[]))
 monkeypatch.setattr(app,"ai_cv_fit",lambda *args:{})
 monkeypatch.setattr(app,"_check_live",lambda job:True)
 count,err,status=app.run_search(uid)
 assert (count,err,status)==(5,None,200)
 _,initial=app.get_run(uid)
 assert len(initial)==5
 original={j["url"] for j in initial}
 assert len(original)==5
 with app.conn() as c:
  seen_before=c.execute("SELECT COUNT(*) FROM seen_jobs WHERE user_id=?",(uid,)).fetchone()[0]
 assert seen_before>=5
 client=app.app.test_client()
 with client.session_transaction() as sess:
  sess["uid"]=uid;sess["_csrf"]="valid"
 response=client.post("/api/jobs/reset",headers={"X-CSRF-Token":"valid"})
 assert response.status_code==200
 with app.conn() as c:
  assert c.execute("SELECT COUNT(*) FROM seen_jobs WHERE user_id=?",(uid,)).fetchone()[0]==seen_before
 count2,err2,status2=app.run_search(uid)
 assert (count2,err2,status2)==(5,None,200)
 _,subsequent=app.get_run(uid)
 assert len(subsequent)==5
 assert not (original & {j["url"] for j in subsequent})


def test_legacy_history_migration_remembers_prior_displayed_jobs(tmp_path,monkeypatch):
 uid=build_user(tmp_path,monkeypatch)
 with app.conn() as c:
  run=c.execute("INSERT INTO daily_runs(user_id,local_day,run_at,state) VALUES(?,?,?,?)",
     (uid,"2026-11-24",app.now(),"complete")).lastrowid
  for i in range(7):
   j=listing(i)
   jid=c.execute("""INSERT INTO jobs(user_id,external_id,title,company,city,country,
      description,url,source,published,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
      (uid,j["external_id"],j["title"],j["company"],j["city"],j["country"],
       j["description"],j["url"],j["source"],j["published"],app.now())).lastrowid
   c.execute("INSERT INTO run_jobs(run_id,job_id,position,fit,matched_terms) VALUES(?,?,?,?,?)",
     (run,jid,i+1,8,"[]"))
 app.init_db()
 seen=app.previously_seen(uid)
 assert all(app.is_seen(listing(i),seen) for i in range(5))
 assert all(not app.is_seen(listing(i),seen) for i in range(5,7))


def test_home_and_dropdown_ui_with_mobile_responsive_labels():
 root=Path(__file__).resolve().parents[1]
 flow=(root/"static/flow.js").read_text()
 js=(root/"static/app.js").read_text()
 css=(root/"static/style.css").read_text()
 assert "Time to boost<br>your career" in flow
 assert "compactHomeRadar" in flow and "flow-home-person" in flow
 assert "Object.keys(answers).length<20" in flow
 assert "One step at a time" not in flow
 assert "data-preference-field" in js and "type=\"checkbox\"" in js
 assert "selectedPreferenceValues" in js and "renderPreferenceMenu" in js
 assert ".flow-home-top.has-radar" in css and ".multi-pref-options" in css
 for script in ("static/app.js","static/flow.js"):
  if shutil.which("node"):
   r=subprocess.run(["node","--check",str(root/script)],capture_output=True,text=True,timeout=8)
   assert r.returncode==0,r.stderr
