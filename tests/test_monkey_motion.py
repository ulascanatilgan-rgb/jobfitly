"""Gibbon animation regression: fidelity, continuous rope sag, mobile and accessibility."""
from pathlib import Path
import shutil
import subprocess

BASE=Path(__file__).resolve().parents[1]


def test_reference_style_gibbon_is_embedded_in_authenticated_app():
    html=(BASE/"templates/index.html").read_text()
    assert 'id="monkey-rope-band"' in html
    assert 'id="gibbon-rope-path"' in html
    assert 'id="gibbon-traveler"' in html
    assert 'id="gibbon-left-arm"' in html
    assert 'id="gibbon-right-arm"' in html
    assert 'id="gibbon-left-hand"' in html
    assert 'id="gibbon-right-hand"' in html
    assert 'id="gibbon-head"' in html
    assert '/static/monkey_motion.js?v=' in html
    assert "monkey-tail" not in html
    assert html.index('id="monkey-rope-band"') > html.index('class="flow-app-footer"')
    assert html.index('id="monkey-rope-band"') < html.index('id="watch-counter"')


def test_hands_reach_and_grip_alternately_and_rope_bends_under_load():
    js=(BASE/"static/monkey_motion.js").read_text()
    assert "cycleSeconds = 3.55" in js
    assert "handPose(phase, shift" in js
    assert "handPose((phase + 0.5) % 1" in js
    assert "leftHand.weight * leftHand.x" not in js  # weight calculation is explicit
    assert "leftHand.x * leftHand.weight + rightHand.x * rightHand.weight" in js
    assert "Math.exp(-distance * distance" in js
    assert "ropePath.setAttribute('d', path)" in js
    assert "hand.y += ropeHeight" in js
    assert "requestAnimationFrame(render)" in js
    assert "prefers-reduced-motion: reduce" in js


def test_burgundy_linework_black_rope_and_higher_footer():
    css=(BASE/"static/style.css").read_text()
    assert ".monkey-rope-band{height:120px}" in css
    assert ".gibbon-traveler{width:164px;height:119px}" in css
    assert "height:144px" in css and "padding-bottom:156px" in css
    assert ".gibbon-outline path" in css
    assert "stroke:#850d45" in css
    assert "#gibbon-rope-path{stroke:#171619" in css


def test_gibbon_animation_javascript_is_valid():
    if not shutil.which("node"): return
    result=subprocess.run(
      ["node","--check",str(BASE/"static/monkey_motion.js")],
      capture_output=True,text=True,timeout=8
    )
    assert result.returncode == 0, result.stderr
