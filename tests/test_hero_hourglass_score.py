"""Test JobFitly hero, search hourglass, and motivational profile score."""
from pathlib import Path
import shutil
import subprocess

BASE=Path(__file__).resolve().parents[1]

def test_landing_photo_and_preserved_white_fade():
    html=(BASE/"templates/index.html").read_text()
    css=(BASE/"static/style.css").read_text()
    image=BASE/"static/jobfitly-executive-20261123.avif"
    assert image.is_file() and image.read_bytes()[4:12]==b"ftypavif"
    assert 'src="/static/jobfitly-executive-20261123.avif"' in html
    assert "hero-mobile-portrait" in html and "hero-full-image" in html
    assert "url('/static/jobfitly-executive-20261123.avif')" in css
    assert "linear-gradient(to right,#fff" in css
    assert "linear-gradient(to bottom,#fff" in css

def test_hourglass_is_visible_while_searching():
    flow=(BASE/"static/flow.js").read_text()
    css=(BASE/"static/style.css").read_text()
    assert 'setAttribute("role","status")' in flow
    assert "find-hourglass-svg" in flow
    assert "Finding the right opportunities" in flow
    assert "find-hg-sand-top" in css
    assert "find-hourglass-rotate" in css

def test_faster_intro_and_score_widget():
    js=(BASE/"static/app.js").read_text()
    css=(BASE/"static/style.css").read_text()
    assert "var(--word-index)*.035s" in css
    assert "jobfitly-word-enter .21s" in css
    assert 'viewBox="0 0 400 338"' in js
    assert 'i===6?Math.max(90,px)' in js
    assert "renderPossibilityScore(p)" in js
    assert "Math.max(80,Math.min(100" in js
    assert "Not a hiring probability." in js
    assert ".possibility-pills" in css

def test_javascript_parses():
    if not shutil.which("node"):return
    for filename in ("static/app.js","static/flow.js"):
        p=subprocess.run(["node","--check",str(BASE/filename)],capture_output=True,text=True,timeout=8)
        assert p.returncode==0,p.stderr
