"""Mobile UI and secure persistent-session regression checks."""
from pathlib import Path
import app as mod

def test_login_remember_cookie(tmp_path,monkeypatch):
    monkeypatch.setattr(mod,'DB',tmp_path/'jobfitly.sqlite3')
    mod.init_db()
    client=mod.app.test_client()
    csrf=client.get('/api/config').get_json()['csrf']
    created=client.post('/api/register',json={'email':'remember@example.org','password':'secure-password-123','remember':True},headers={'X-CSRF-Token':csrf})
    assert created.status_code==200
    assert 'expires=' in created.headers.get('Set-Cookie','').lower()
    csrf=created.get_json()['csrf']
    assert client.get('/api/me').status_code==200
    assert client.post('/api/logout',headers={'X-CSRF-Token':csrf}).status_code==200
    csrf=client.get('/api/config').get_json()['csrf']
    logged=client.post('/api/login',json={'email':'remember@example.org','password':'secure-password-123','remember':False},headers={'X-CSRF-Token':csrf})
    assert logged.status_code==200
    assert 'expires=' not in logged.headers.get('Set-Cookie','').lower()

def test_mobile_photo_and_pwa():
    base=Path(__file__).resolve().parents[1]
    html=(base/'templates/index.html').read_text()
    css=(base/'static/style.css').read_text()
    js=(base/'static/app.js').read_text()
    assert 'hero-mobile-portrait' in html and 'jobfitly-executive-20261123.avif' in css
    assert 'manifest.webmanifest' in html and 'apple-touch-icon' in html
    assert 'auth-remember' in html and 'remember:' in js
    assert 'hero-word' in css and 'buildHeroWordReveal' in js
    assert 'data-preference' in js and 'search-preferences-grid' in css
