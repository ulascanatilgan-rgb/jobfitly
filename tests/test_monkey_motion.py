"""Reference GIF footer regression tests."""
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]

def test_looped_monkey_gif_is_real_and_valid():
    path=ROOT/"static"/"jobfitly_monkey.gif"
    assert path.exists()
    with Image.open(path) as image:
        assert image.format=="GIF"
        assert image.n_frames>=6
        assert image.info.get("loop")==0
        assert image.size[0]>=100

def test_gif_replaces_old_svg_and_runs_across_app():
    html=(ROOT/"templates/index.html").read_text()
    css=(ROOT/"static/style.css").read_text()
    assert 'id="monkey-rope-band"' in html
    assert "/static/jobfitly_monkey.gif" in html
    assert "gibbon-art" not in html
    assert "monkey-gif-cross" in css
    assert "translate3d(calc(100vw + 170px)" in css
    assert "monkey-rope-line" in html
    assert "stroke:#850d45" in css
