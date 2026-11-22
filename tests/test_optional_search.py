"""Optional search preferences and progressive source-backed CV matching."""
import json
from pathlib import Path

import app as mod


def make_user(tmp_path, monkeypatch, cv=None):
    monkeypatch.setattr(mod, "DB", tmp_path / "optional.sqlite3")
    mod.init_db()
    cv = cv or ("Taylor Morgan\nPROFILE\nOperations management professional. "
                "Operations reporting, process control, project coordination, "
                "stakeholder engagement, banking, business operations, audit and risk. "
                "Managed project coordination and business operations across teams.")
    with mod.conn() as c:
        uid = c.execute(
            "INSERT INTO users(email,password_hash,created_at) VALUES(?,?,?)",
            ("taylor@example.org", "fake-hash", mod.now())
        ).lastrowid
        c.execute(
            "INSERT INTO profiles(user_id,name,city,country,cv_name,cv_text,questions,swipes,updated_at) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (uid, "Taylor Morgan", "", "", "resume.txt", cv, "{}", "{}", mod.now())
        )
    return uid


def job(i, title="Operations Coordinator", company="Employer", country="Belgium"):
    return {
        "external_id": "listing-" + str(i), "title": title,
        "company": company + str(i), "city": "Antwerp", "country": country,
        "description": "Coordinate operations reporting and project processes, "
                       "business operations stakeholder engagement and management.",
        "url": "https://careers.example.org/openings/" + str(i),
        "published": mod.now(), "source": "Employer careers"
    }


def test_cv_only_search_returns_five_without_any_preferences(tmp_path, monkeypatch):
    uid=make_user(tmp_path,monkeypatch)
    monkeypatch.setattr(mod,"fetch_candidates",lambda profile:([job(i) for i in range(9)],[]))
    monkeypatch.setattr(mod,"_check_live",lambda item:True)
    monkeypatch.setattr(mod,"ai_cv_fit",lambda *args:{})
    result=mod.run_search(uid)
    assert result==(5,None,200)
    run,items=mod.get_run(uid)
    assert len(items)==5
    assert items==sorted(items,key=lambda x:x["score"],reverse=True)
    with mod.conn() as c:
        assert json.loads(c.execute("SELECT swipes FROM profiles WHERE user_id=?",(uid,)).fetchone()[0])=={}


def test_ranking_nearest_source_backed_roles_without_inventing_five(tmp_path,monkeypatch):
    uid=make_user(tmp_path,monkeypatch)
    monkeypatch.setattr(mod,"fetch_candidates",lambda profile:([job(1)],[]))
    monkeypatch.setattr(mod,"_check_live",lambda item:True)
    monkeypatch.setattr(mod,"ai_cv_fit",lambda *args:{})
    count,error,status=mod.run_search(uid)
    assert (count,error,status)==(1,None,200)
    assert len(mod.get_run(uid)[1])==1


def test_zero_source_results_do_not_claim_any_real_listing(tmp_path,monkeypatch):
    uid=make_user(tmp_path,monkeypatch)
    monkeypatch.setattr(mod,"fetch_candidates",lambda profile:([],[]))
    monkeypatch.setattr(mod,"ai_cv_fit",lambda *args:{})
    count,error,status=mod.run_search(uid)
    assert count is None and status==422 and "source-backed" in error
    with mod.conn() as c:
        assert c.execute("SELECT count(*) FROM daily_runs").fetchone()[0]==0


def test_fallback_search_reaches_remote_and_related_roles(monkeypatch):
    calls=[]
    def fake_search(profile,days):
        calls.append((profile.get("search_scope"),profile.get("search_focus"),days))
        if "remote" in str(profile.get("search_scope")):
            return [job(i) for i in range(5)]
        return []
    monkeypatch.setattr(mod,"search_jobs",fake_search)
    results,errors=mod.fetch_candidates({
        "cv_for_matching":"Operations coordination and project management in banking with risk controls.",
        "country":"Belgium","city":"","keywords":"","swipes":{},"questions":{}
    })
    assert not errors
    assert len(results)==5
    assert len(calls)>=4
    assert len(set(result["url"] for result in results))==5


def test_optional_search_ready_is_not_tied_to_dropdown_choices():
    root=Path(__file__).resolve().parents[1]
    flow=(root/"static/flow.js").read_text()
    main=(root/"static/app.js").read_text()
    assert 'if(id==="search")return "Ready";' in flow
    assert "var ready=!!p.has_cv;" in flow
    assert "const ready=!!p.has_cv;" in main
    assert "if(!data.city||!data.country)" not in main
    assert "if(!state.swipes[s.id])" not in main
