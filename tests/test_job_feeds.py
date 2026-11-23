"""Contract tests for independent public job feeds (no network or API keys)."""
import datetime
import job_feeds

def test_normalize_himalayas_application_link_and_respect_country(monkeypatch):
    moment=datetime.datetime.now(datetime.timezone.utc)
    timestamp=int(moment.timestamp())
    def fake(url,params):
        assert url=="https://himalayas.app/jobs/api/search"
        assert params["country"]=="BE"
        return {"jobs":[
            {"title":"Risk Manager","companyName":"Valid Employer","description":"<p>Technology risk and audit oversight</p>",
             "applicationLink":"https://himalayas.app/companies/valid/jobs/risk-manager?ref=jobfitly",
             "pubDate":timestamp,"expiryDate":timestamp+86400,"locationRestrictions":["Belgium"]},
            {"title":"Risk Manager","companyName":"Expired Employer","description":"IT risk and audit",
             "applicationLink":"https://himalayas.app/companies/expired/jobs/risk-manager",
             "pubDate":timestamp,"expiryDate":timestamp-86400,"locationRestrictions":[]},
            {"title":"Risk Manager","companyName":"US Only","description":"IT risk and audit",
             "applicationLink":"https://himalayas.app/companies/usa/jobs/risk-manager",
             "pubDate":timestamp,"expiryDate":timestamp+86400,"locationRestrictions":["United States"]}
        ]}
    monkeypatch.setattr(job_feeds,"_fetch_json",fake)
    result=job_feeds._himalayas({"country":"Belgium"},"BE","risk")
    assert len(result)==1
    assert result[0]["title"]=="Risk Manager"
    assert result[0]["source"]=="Himalayas"
    assert "himalayas.app" in result[0]["url"]
    assert result[0]["description"]=="Technology risk and audit oversight"
    assert result[0]["published"]==moment.date().isoformat()

def test_jobicy_europe_jobs_and_block_usa_only(monkeypatch):
    today=datetime.datetime.now(datetime.timezone.utc).isoformat()
    def fake(url,params):
        assert url=="https://jobicy.com/api/jobs"
        assert params["geo"]=="europe" and params["count"]==200
        return {"jobs":[
          {"jobTitle":"Project Manager","companyName":"EU Company","jobGeo":"EMEA",
           "jobDescription":"<p>Coordinate cross-functional project delivery.</p>",
           "pubDate":today,"url":"https://jobicy.com/jobs/project-manager"},
          {"jobTitle":"Project Manager","companyName":"American Company","jobGeo":"USA only",
           "jobDescription":"Coordinate project delivery.",
           "pubDate":today,"url":"https://jobicy.com/jobs/us-only"}
        ]}
    monkeypatch.setattr(job_feeds,"_fetch_json",fake)
    results=job_feeds._jobicy({"country":"Belgium"},"BE")
    assert len(results)==1
    assert results[0]["company"]=="EU Company"
    assert results[0]["source"]=="Jobicy"

def test_arbeitnow_physical_location_stays_in_country(monkeypatch):
    date=int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    monkeypatch.setattr(job_feeds,"_fetch_json",lambda *args,**kwargs:{"data":[
      {"title":"Financial Analyst","company_name":"BE Company",
       "location":"Brussels, Belgium","description":"<p>Prepare financial reporting</p>",
       "url":"https://www.arbeitnow.com/jobs/companies/be/analyst","created_at":date},
      {"title":"Financial Analyst","company_name":"DE Company",
       "location":"Berlin, Germany","description":"<p>Prepare financial reporting</p>",
       "url":"https://www.arbeitnow.com/jobs/companies/de/analyst","created_at":date}
    ]})
    found=job_feeds._arbeitnow({"country":"Belgium"},"BE",1)
    assert len(found)==1 and found[0]["company"]=="BE Company"
    assert found[0]["source"]=="Arbeitnow"

def test_aggregator_isolates_provider_failure(monkeypatch):
    monkeypatch.setattr(job_feeds,"_jobicy",lambda *args,**kwargs:[
       {"url":"https://jobicy.com/jobs/a","title":"Operations Lead","source":"Jobicy"}])
    def outage(*args,**kwargs):
        raise ValueError("unavailable")
    monkeypatch.setattr(job_feeds,"_himalayas",outage)
    monkeypatch.setattr(job_feeds,"_arbeitnow",lambda *args,**kwargs:[])
    result,errors=job_feeds.discover_feed_jobs({"country":"Belgium","cv_for_matching":"Operations team leadership"})
    assert len(result)==1
    assert result[0]["source"]=="Jobicy"
    assert errors and all("himalayas" in err for err in errors)

def test_cv_queries_do_not_include_identity():
    cv="Alex Morgan\n+32 470 000 000\nalex@example.com\nIT Risk Manager, compliance and audit projects."
    queries=job_feeds._role_queries(cv)
    assert "risk" in queries
    assert all("alex" not in q.lower() and "@" not in q and "+32" not in q for q in queries)


def test_full_search_survives_openai_outage_with_five_real_feed_jobs(monkeypatch,tmp_path):
    import app
    import requests
    monkeypatch.setattr(app,"DB",tmp_path/"resilient.sqlite3")
    app.init_db()
    with app.conn() as c:
        uid=c.execute("INSERT INTO users(email,password_hash,created_at) VALUES(?,?,?)",
                      ("demo@example.org","hash",app.now())).lastrowid
        c.execute("INSERT INTO profiles(user_id,cv_name,cv_text,questions,swipes,updated_at) VALUES(?,?,?,?,?,?)",
                  (uid,"sample.txt",
                   "Taylor Morgan\nOperations Manager\nOperations process controls, cross-functional "
                   "stakeholder planning, management reporting, audit, project coordination, "
                   "risk processes and business operations.", "{}", "{}", app.now()))
    fake=[]
    for index in range(8):
        fake.append({"external_id":f"jobicy:{index}","title":"Operations Manager",
                     "company":f"Employer {index}","city":"Remote","country":"Europe",
                     "description":"Operations management, risk process controls, "
                                   "project coordination and reporting.",
                     "url":f"https://jobicy.com/jobs/operations-manager-{index}",
                     "published":app.now(),"source":"Jobicy"})
    monkeypatch.setattr(app,"discover_feed_jobs",lambda profile:(fake,[]))
    def no_web(*args,**kwargs):
        raise requests.Timeout("Simulated failure")
    monkeypatch.setattr(app,"search_jobs",no_web)
    monkeypatch.setenv("OPENAI_API_KEY","synthetic-fixture-only")
    monkeypatch.setattr(app,"ai_cv_fit",lambda *args,**kwargs:{})
    assert app.run_search(uid)==(5,None,200)
    _,jobs=app.get_run(uid)
    assert len(jobs)==5 and all("jobicy.com" in j["url"] for j in jobs)


def test_abandoned_search_is_recoverable(monkeypatch,tmp_path):
    import app
    monkeypatch.setattr(app,"DB",tmp_path/"interrupted.sqlite3")
    app.init_db()
    earlier=(datetime.datetime.now(datetime.timezone.utc)-
             datetime.timedelta(minutes=9)).isoformat()
    with app.conn() as c:
        uid=c.execute("INSERT INTO users(email,password_hash,created_at) VALUES(?,?,?)",
                      ("again@example.org","hash",app.now())).lastrowid
        c.execute("INSERT INTO profiles(user_id,cv_name,cv_text,updated_at) VALUES(?,?,?,?)",
                  (uid,"sample.txt",
                   "Operations Manager. Cross-functional business operations and risk, "
                   "program coordination with stakeholder engagement, financial reporting.",app.now()))
        c.execute("INSERT INTO daily_runs(user_id,local_day,run_at,state) VALUES(?,?,?,?)",
                  (uid,app.today(),earlier,"working"))
    monkeypatch.setattr(app,"fetch_candidates",lambda profile:([],[]))
    result=app.run_search(uid)
    assert result[2]==422
    assert "source-backed" in result[1]
    with app.conn() as c:
        assert c.execute("SELECT COUNT(*) FROM daily_runs").fetchone()[0]==0
