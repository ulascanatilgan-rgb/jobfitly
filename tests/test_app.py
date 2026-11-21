import datetime, json
import app as mod


def test_recent_rejects_old():
    old = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=90)).isoformat()
    new = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)).isoformat()
    assert not mod._recent(old)
    assert mod._recent(new)
    assert not mod._valid_public_link('http://localhost/admin')
    assert not mod._valid_public_link('https://127.0.0.1/private')
    assert mod._valid_public_link('https://www.arbeitnow.com/jobs/example')


def test_seven_motivation_points():
    p = {'name':'Alex', 'cv_text':'Alex Example\nOperations manager\nLed stakeholder workshops\nImproved onboarding experience'}
    job={'title':'Operations Manager','company':'Example','description':'Manage teams. Improve onboarding. Lead stakeholder workshops.'}
    motivation, cv = mod.build_fallback(p,job)
    assert sum(line[:2] == f'{i}.' for i in range(1,8) for line in motivation.splitlines()) == 7
    assert 'Alex Example' in cv


def test_daily_run_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, 'DB', tmp_path/'jobfitly.sqlite3')
    mod.init_db()
    with mod.conn() as c:
        uid = c.execute('INSERT INTO users(email,password_hash,created_at) VALUES(?,?,?)',('test@example.com','hash',mod.now())).lastrowid
        qs={key:7 for key,_ in mod.QUESTIONS}
        c.execute('INSERT INTO profiles(user_id,city,country,cv_name,cv_text,questions,swipes,updated_at) VALUES(?,?,?,?,?,?,?,?)',(uid,'Brussels','Belgium','resume.txt','Operations manager and project leadership experience. Published work.',json.dumps(qs),json.dumps({'role_type':'Operations & strategy'}),mod.now()))
    recent=mod.now()
    candidates=[{'external_id':str(i),'title':'Operations Manager','company':'Example '+str(i),'city':'Brussels','country':'Belgium','description':'Operations manager business stakeholder planning','url':'https://www.example.org/jobs/'+str(i),'published':recent,'source':'Test'} for i in range(6)]
    monkeypatch.setattr(mod, 'fetch_candidates', lambda p:(candidates,[]))
    monkeypatch.setattr(mod, '_check_live', lambda j:True)
    count,error,status = mod.run_search(uid)
    assert (count,error,status) == (5,None,200)
    assert len(mod.get_run(uid)[1]) == 5
    assert mod.run_search(uid)[2] == 409
    with mod.conn() as c:
        assert c.execute('SELECT count(*) n FROM daily_runs').fetchone()['n']==1