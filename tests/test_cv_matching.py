import datetime
import json

import app
from matching import lexical_fit, redact_cv, specialty_fit


def test_cv_first_rejects_unrelated_hr_director():
    cv = (
        "Internal Control Manager, Western Union\n"
        "IT Risk and Security Expert, ING Bank\n"
        "Identity and access management, audit, control, stakeholder management.\n"
        "Worked alongside HR Pay Solutions as a vendor."
    )
    hr = {"title": "HR Director", "description": "Oversee recruiting, HR policy, workforce and benefits."}
    ops = {"title": "IT Risk Manager", "description": "Risk controls, auditing, and identity security."}
    assert specialty_fit(hr["title"], cv) is False
    assert lexical_fit(hr, cv)[0] == 0
    assert lexical_fit(ops, cv)[0] >= 60


def test_relevant_operations_role_wins_over_seniority_keyword():
    cv = "Operations Manager at Example Co. Project coordination, operations, finance and risk controls."
    related = {"title": "Operations Manager", "description": "Manage daily operations and process control."}
    unrelated = {"title": "HR Director", "description": "Human resources director. Manage people and talent."}
    assert lexical_fit(related, cv)[0] >= 60
    assert lexical_fit(unrelated, cv)[0] == 0


def test_redacted_cv_sent_for_ai_match():
    excerpt = "Jordan jordan@example.com +32 470 123 456\nIT risk manager"
    redacted = redact_cv(excerpt)
    assert "jordan@example.com" not in redacted
    assert "+32 470 123 456" not in redacted
    assert "IT risk manager" in redacted


def test_reset_only_clears_own_runs_and_preserves_myjobs(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "DB", tmp_path / "matches.sqlite3")
    app.init_db()
    with app.conn() as c:
        uid = c.execute(
            "INSERT INTO users(email,password_hash,created_at) VALUES(?,?,?)",
            ("owner@example.org", "hash", app.now()),
        ).lastrowid
        other = c.execute(
            "INSERT INTO users(email,password_hash,created_at) VALUES(?,?,?)",
            ("other@example.org", "hash", app.now()),
        ).lastrowid
        for who in (uid, other):
            c.execute("INSERT INTO profiles(user_id,updated_at) VALUES(?,?)", (who, app.now()))
        saved = c.execute(
            "INSERT INTO jobs(user_id,external_id,title,company,city,country,description,url,source,published,created_at)"
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (uid, "saved", "Operations Lead", "Example", "Brussels", "Belgium", "Operations", "https://example.org/jobs/a", "Test", app.now(), app.now()),
        ).lastrowid
        unused = c.execute(
            "INSERT INTO jobs(user_id,external_id,title,company,city,country,description,url,source,published,created_at)"
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (uid, "unused", "Analyst", "Example", "Brussels", "Belgium", "Analytics", "https://example.org/jobs/b", "Test", app.now(), app.now()),
        ).lastrowid
        c.execute("INSERT INTO watchlist(user_id,job_id,added_at) VALUES(?,?,?)", (uid, saved, app.now()))
        c.execute("INSERT INTO daily_runs(user_id,local_day,run_at,state) VALUES(?,?,?,?)", (uid, app.today(), app.now(), "complete"))
        c.execute("INSERT INTO daily_runs(user_id,local_day,run_at,state) VALUES(?,?,?,?)", (other, app.today(), app.now(), "complete"))
    client = app.app.test_client()
    with client.session_transaction() as session:
        session["uid"] = uid
        session["_csrf"] = "csrf-for-test"
    response = client.post("/api/jobs/reset", headers={"X-CSRF-Token": "csrf-for-test"})
    assert response.status_code == 200
    with app.conn() as c:
        assert c.execute("SELECT count(*) FROM daily_runs WHERE user_id=?", (uid,)).fetchone()[0] == 0
        assert c.execute("SELECT count(*) FROM daily_runs WHERE user_id=?", (other,)).fetchone()[0] == 1
        assert c.execute("SELECT count(*) FROM watchlist WHERE user_id=?", (uid,)).fetchone()[0] == 1
        assert c.execute("SELECT count(*) FROM jobs WHERE user_id=?", (uid,)).fetchone()[0] == 1
        assert c.execute("SELECT id FROM jobs WHERE user_id=?", (uid,)).fetchone()[0] == saved


def test_hr_director_excluded_from_actual_run(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "DB", tmp_path / "matching.sqlite3")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app.init_db()
    with app.conn() as c:
        uid = c.execute(
            "INSERT INTO users(email,password_hash,created_at) VALUES(?,?,?)",
            ("fit@example.org", "hash", app.now()),
        ).lastrowid
        cv = "Internal Control Manager, Western Union. IT Risk Expert, ING. Audit, control, finance and risk."
        c.execute(
            "INSERT INTO profiles(user_id,city,country,cv_name,cv_text,questions,swipes,updated_at)"
            " VALUES(?,?,?,?,?,?,?,?)",
            (uid, "Brussels", "Belgium", "cv.txt", cv, json.dumps({key: 7 for key, _ in app.QUESTIONS}), '{"role_type":"People & relationships"}', app.now()),
        )
    jobs = [
        {"external_id":"hr", "title":"HR Director", "company":"Example HR", "city":"Brussels", "country":"Belgium", "description":"Run HR programs and workforce strategy", "url":"https://example.org/jobs/hr", "published":app.now(), "source":"Test"},
        {"external_id":"risk", "title":"IT Risk Manager", "company":"Example Risk", "city":"Brussels", "country":"Belgium", "description":"Own IT risk control and audit", "url":"https://example.org/jobs/risk", "published":app.now(), "source":"Test"},
    ]
    monkeypatch.setattr(app, "fetch_candidates", lambda profile: (jobs, []))
    monkeypatch.setattr(app, "_check_live", lambda job: True)
    count, error, status = app.run_search(uid)
    assert (count, error, status) == (1, None, 200)
    assert app.get_run(uid)[1][0]["title"] == "IT Risk Manager"
