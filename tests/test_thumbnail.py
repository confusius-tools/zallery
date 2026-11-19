"""Tests for zallery.thumbnail."""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib.colors as mcolors
import matplotlib.image as mimg
import numpy as np
import pytest

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
    """Each picture has its scheme's background, the given styles, and the output's
    own drawing, script included."""
    light, dark = tmp_path / "light.png", tmp_path / "dark.png"
    # The style rule paints the first block blue; the script, the second one green.
    html = (
        '<div class="box">Hello</div><div id="drawn"></div>'
        "<script>document.getElementById('drawn').style.cssText ="
        " 'background: #00ff00; height: 60px'</script>"
    )
    css = ".gallery-rich-output .box { background: #0000ff; height: 60px; }"

    browser = find_browser()
    assert browser is not None
    assert screenshot_html(html, html, light, dark, browser=browser, css=css)

    # Zensical's default page colors: white, and `hsla(225, 15%, 5%, 1)`.
    assert _corner(light) == pytest.approx((1.0, 1.0, 1.0), abs=0.01)
    assert _corner(dark) == pytest.approx(mcolors.to_rgb("#0b0c0f"), abs=0.01)
    pixels = mimg.imread(light)
    height, width = pixels.shape[:2]
    assert width / height == pytest.approx(4 / 3, rel=0.05)
    blue = (pixels[..., :3] == [0.0, 0.0, 1.0]).all(axis=-1)
    assert blue.any()
    green = (pixels[..., :3] == [0.0, 1.0, 0.0]).all(axis=-1)
    assert green.any()


@pytest.mark.slow
@pytest.mark.skipif(find_browser() is None, reason="needs a Chromium-family browser")
def test_screenshot_html_applies_the_stylesheet_of_zallery(tmp_path: Path) -> None:
    """A pandas table is pictured as on its page, with no style of the site."""
    light, dark = tmp_path / "light.png", tmp_path / "dark.png"
    html = (
        '<table border="1" class="dataframe"><tbody>'
        '<tr><td style="width: 300px; height: 150px"></td></tr></tbody></table>'
    )

    browser = find_browser()
    assert browser is not None
    assert screenshot_html(html, html, light, dark, browser=browser)

    # The colors the stylesheet gives the first row of a table, in each scheme.
    for picture, stripe in ((light, "#edf0f5"), (dark, "#1d2533")):
        pixels = mimg.imread(picture)[..., :3]
        striped = np.isclose(pixels, mcolors.to_rgb(stripe), atol=0.01).all(axis=-1)
        assert striped.mean() > 0.2


@pytest.mark.slow
@pytest.mark.skipif(find_browser() is None, reason="needs a Chromium-family browser")
def test_screenshot_html_takes_the_page_color_of_the_site_styles(
    tmp_path: Path,
) -> None:
    """A site with its own page colors sets Zensical's variables, as on the site."""
    light, dark = tmp_path / "light.png", tmp_path / "dark.png"
    css = (
        '[data-md-color-scheme="default"] { --md-default-bg-color: #ff0000; }'
        '[data-md-color-scheme="slate"] { --md-default-bg-color: #0000ff; }'
    )

    browser = find_browser()
    assert browser is not None
    assert screenshot_html(
        "<p>x</p>", "<p>x</p>", light, dark, browser=browser, css=css
    )

    assert _corner(light) == pytest.approx((1.0, 0.0, 0.0), abs=0.01)
    assert _corner(dark) == pytest.approx((0.0, 0.0, 1.0), abs=0.01)


@pytest.mark.slow
@pytest.mark.skipif(find_browser() is None, reason="needs a Chromium-family browser")
def test_screenshot_html_derives_the_light_text_colors_from_the_site_text_color(
    tmp_path: Path,
) -> None:
    """A site text color set on the scheme attribute reaches Zensical's lighter
    text colors, unless the site sets those too."""
    light, dark = tmp_path / "light.png", tmp_path / "dark.png"
    html = '<div class="light"></div><div class="lighter"></div>'
    css = (
        '[data-md-color-scheme="default"] { --md-default-fg-color: #ff0000; }'
        '[data-md-color-scheme="slate"] { --md-default-fg-color: #0000ff; }'
        "[data-md-color-scheme] { --md-default-fg-color--lighter: #00ff00; }"
        ".light { background: var(--md-default-fg-color--light); height: 60px; }"
        ".lighter { background: var(--md-default-fg-color--lighter); height: 60px; }"
    )

    browser = find_browser()
    assert browser is not None
    assert screenshot_html(html, html, light, dark, browser=browser, css=css)

    # The site text color at 54 %, over the page background.
    for png, color in ((light, (1.0, 0.0, 0.0)), (dark, (0.0, 0.0, 1.0))):
        pixels = mimg.imread(png)[..., :3]
        expected = 0.54 * np.array(color) + 0.46 * np.array(_corner(png))
        assert (np.abs(pixels - expected) < 0.02).all(axis=-1).any()
        assert (pixels == [0.0, 1.0, 0.0]).all(axis=-1).any()


@pytest.mark.slow
@pytest.mark.skipif(find_browser() is None, reason="needs a Chromium-family browser")
def test_screenshot_html_pictures_each_scheme_from_its_own_html(tmp_path: Path) -> None:
    """An output with a dark variant gives each picture the HTML of its scheme."""
    light, dark = tmp_path / "light.png", tmp_path / "dark.png"
    box = '<div style="background: {}; height: 60px"></div>'

    browser = find_browser()
    assert browser is not None
    assert screenshot_html(
        box.format("#ff0000"), box.format("#0000ff"), light, dark, browser=browser
    )

    red = (mimg.imread(light)[..., :3] == [1.0, 0.0, 0.0]).all(axis=-1)
    blue = (mimg.imread(dark)[..., :3] == [0.0, 0.0, 1.0]).all(axis=-1)
    assert red.any()
    assert blue.any()
    assert not (mimg.imread(light)[..., :3] == [0.0, 0.0, 1.0]).all(axis=-1).any()


def test_screenshot_html_reports_a_browser_that_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A broken browser costs the thumbnail, not the build."""
    light, dark = tmp_path / "light.png", tmp_path / "dark.png"
    browser = str(tmp_path / "missing-browser")

    done = screenshot_html("<p>Hello</p>", "<p>Hello</p>", light, dark, browser=browser)

    assert not done
    assert not light.exists()
    # The warning names the browser itself: the system's error may not.
    assert f"{browser} failed" in capsys.readouterr().err
