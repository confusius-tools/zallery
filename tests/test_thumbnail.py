"""Tests for zallery.thumbnail."""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib.colors as mcolors
import matplotlib.image as mimg
import pytest

from zallery.theme import DARK, LIGHT
from zallery.thumbnail import find_browser, screenshot_html


def _executable(path: Path) -> Path:
    """Create an empty executable file, with the suffix Windows needs to run one."""
    path = path.with_suffix(".exe") if os.name == "nt" else path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
    path.chmod(0o755)
    return path


@pytest.fixture
def no_browser(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Hide every browser of this machine; return the empty directory on `PATH`."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    monkeypatch.delenv("ZALLERY_BROWSER", raising=False)
    monkeypatch.setenv("PATH", str(bin_dir))
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path / "playwright"))
    return bin_dir


def test_find_browser_returns_none_without_a_browser(no_browser: Path) -> None:
    assert find_browser() is None


def test_find_browser_searches_the_path(no_browser: Path) -> None:
    chromium = _executable(no_browser / "chromium")

    # As paths: Windows gives the suffix in the case of `PATHEXT`.
    assert Path(find_browser() or "") == chromium


def test_find_browser_finds_a_playwright_download(
    no_browser: Path, tmp_path: Path
) -> None:
    shell = _executable(
        tmp_path
        / "playwright"
        / "chromium_headless_shell-1228"
        / "chrome-headless-shell-linux64"
        / "chrome-headless-shell"
    )

    assert Path(find_browser() or "") == shell


def test_find_browser_uses_only_the_configured_browser(
    no_browser: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`ZALLERY_BROWSER` is the choice of the user: no other browser replaces it."""
    _executable(no_browser / "chromium")
    mine = _executable(tmp_path / "elsewhere" / "my-browser")

    monkeypatch.setenv("ZALLERY_BROWSER", str(mine))
    assert Path(find_browser() or "") == mine

    monkeypatch.setenv("ZALLERY_BROWSER", str(tmp_path / "missing"))
    assert find_browser() is None


def _corner(png: Path) -> tuple[float, ...]:
    return tuple(float(value) for value in mimg.imread(png)[2, 2, :3])


@pytest.mark.slow
@pytest.mark.skipif(find_browser() is None, reason="needs a Chromium-family browser")
def test_screenshot_html_writes_a_light_and_a_dark_picture(tmp_path: Path) -> None:
    """Each picture has its scheme's background, the given styles, and no scripts."""
    light, dark = tmp_path / "light.png", tmp_path / "dark.png"
    # The script would paint the page red; the style rule paints the block blue.
    html = (
        "<script>document.body.style.background = 'red'</script>"
        '<div class="box">Hello</div>'
    )
    css = ".gallery-rich-output .box { background: #0000ff; height: 60px; }"

    browser = find_browser()
    assert browser is not None
    assert screenshot_html(html, light, dark, browser=browser, css=css)

    assert _corner(light) == pytest.approx(mcolors.to_rgb(LIGHT.bg), abs=0.01)
    assert _corner(dark) == pytest.approx(mcolors.to_rgb(DARK.bg), abs=0.01)
    pixels = mimg.imread(light)
    height, width = pixels.shape[:2]
    assert width / height == pytest.approx(4 / 3, rel=0.05)
    blue = (pixels[..., :3] == [0.0, 0.0, 1.0]).all(axis=-1)
    assert blue.any()


def test_screenshot_html_reports_a_browser_that_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A broken browser costs the thumbnail, not the build."""
    light, dark = tmp_path / "light.png", tmp_path / "dark.png"
    browser = str(tmp_path / "missing-browser")

    done = screenshot_html("<p>Hello</p>", light, dark, browser=browser)

    assert not done
    assert not light.exists()
    # The warning names the browser itself: the system's error may not.
    assert f"{browser} failed" in capsys.readouterr().err
