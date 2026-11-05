"""Thumbnails of HTML outputs, taken by a headless Chromium-family browser.

An HTML output (a DataFrame, an xarray view) has no picture to put on its index
card. The browser is run as a command on a small page holding the output, once for
each color scheme, and prints the top-left corner of that page to a PNG.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BROWSER_ENV = "ZALLERY_BROWSER"
"""Environment variable naming the browser to use: a command or a path."""

_COMMANDS = (
    "chromium",
    "chromium-browser",
    "google-chrome",
    "google-chrome-stable",
    "chrome",
    "microsoft-edge",
    "msedge",
)
"""Commands a Chromium-family browser is installed under, in order of preference."""

_WINDOW = (440, 330)
"""Width and height of the page in CSS pixels: the 4:3 shape of an index card."""

_SCALE = 2
"""Device pixels per CSS pixel, so the picture stays sharp on dense screens."""

_POLICY = "default-src 'none'; style-src 'unsafe-inline'; img-src data:; font-src data:"
"""Content security policy of the page: no script runs, nothing is fetched."""


def _playwright_browser() -> str | None:
    """Return the headless shell Playwright downloaded, if any.

    `playwright install chromium-headless-shell` puts the browser in a cache folder,
    not on the `PATH`. It is the simplest way to get a browser on a build machine.

    Returns
    -------
    str or None
        Path of the program, or `None` if Playwright downloaded none.
    """
    root = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if root is None:
        if sys.platform == "darwin":
            root = Path.home() / "Library" / "Caches" / "ms-playwright"
        elif sys.platform == "win32":
            local = os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
            root = Path(local) / "ms-playwright"
        else:
            cache = os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")
            root = Path(cache) / "ms-playwright"
    # ponytail: text order, not version order, picks among several downloads; any of
    # them works.
    shells = sorted(
        Path(root).glob("chromium_headless_shell-*/*/chrome-headless-shell*")
    )
    return str(shells[-1]) if shells else None


def find_browser() -> str | None:
    """Return the browser to take thumbnails with, or `None` if there is none.

    Returns
    -------
    str or None
        The program named by the `ZALLERY_BROWSER` environment variable when it is
        set, and nothing else: a wrong value is not replaced by another browser.
        Otherwise the first Chromium-family browser on the `PATH`, then the
        headless shell Playwright downloaded.
    """
    configured = os.environ.get(BROWSER_ENV)
    if configured:
        return shutil.which(configured)
    for command in _COMMANDS:
        found = shutil.which(command)
        if found is not None:
            return found
    return _playwright_browser()


def _page(html: str, css: str, *, scheme: str, background: str, color: str) -> str:
    """Return a page showing one HTML output as it shows on the site.

    The output sits in the same wrappers and under the same color scheme attribute
    as on an example page, so the styles of the output and of the site apply. The
    theme variables and font sizes that site styles usually build on are defined
    here, since the theme's own stylesheet is not available.

    Parameters
    ----------
    html : str
        The HTML output.
    css : str
        Styles of the site to apply.
    scheme : str
        Value of the `data-md-color-scheme` attribute: `default` or `slate`.
    background : str
        Page background color.
    color : str
        Text color.

    Returns
    -------
    str
        The HTML document.
    """
    return f"""<!doctype html>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="{_POLICY}">
<style>
:root {{
  --md-default-bg-color: {background};
  --md-default-fg-color: {color};
  --md-default-fg-color--light: color-mix(in srgb, {color} 54%, transparent);
  --md-default-fg-color--lighter: color-mix(in srgb, {color} 32%, transparent);
  --md-default-fg-color--lightest: color-mix(in srgb, {color} 7%, transparent);
  --md-code-font-family: ui-monospace, monospace;
}}
html {{ font-size: 125%; }}
body {{
  margin: 0;
  padding: 0.7rem;
  background: {background};
  color: {color};
  font: 0.8rem/1.6 system-ui, sans-serif;
}}
{css}
</style>
<body data-md-color-scheme="{scheme}">
<div class="md-typeset"><div class="gallery-rich-output">{html}</div></div>
"""


def screenshot_html(
    html: str, light_path: Path, dark_path: Path, *, browser: str, css: str = ""
) -> bool:
    """Write a light and a dark PNG thumbnail of an HTML output.

    Parameters
    ----------
    html : str
        The HTML output.
    light_path : pathlib.Path
        Where to write the thumbnail for the light color scheme.
    dark_path : pathlib.Path
        Where to write the thumbnail for the dark color scheme.
    browser : str
        The Chromium-family browser to run (see `find_browser`).
    css : str, default: ""
        Styles of the site to apply, so the output looks as it does on its page.

    Returns
    -------
    bool
        Whether both thumbnails were written. A browser that fails is reported on
        the standard error and leaves no thumbnail: the build goes on without one.
    """
    # Imported here so that a build without HTML thumbnails does not pay for
    # matplotlib, which the theme module imports.
    from zallery.theme import DARK, LIGHT

    width, height = _WINDOW
    with tempfile.TemporaryDirectory(prefix="zallery-thumbnail-") as scratch:
        for scheme, theme, path in (
            ("default", LIGHT, light_path),
            ("slate", DARK, dark_path),
        ):
            page = Path(scratch) / f"{scheme}.html"
            page.write_text(
                _page(html, css, scheme=scheme, background=theme.bg, color=theme.fg),
                encoding="utf-8",
            )
            command = [
                browser,
                "--headless",
                # The sandbox is not available on many build machines (containers,
                # recent Ubuntu). What it guards against is ruled out instead: the
                # page's policy runs no script and fetches nothing, no host resolves,
                # and the content comes from example code that already ran on this
                # machine.
                "--no-sandbox",
                "--host-resolver-rules=MAP * ~NOTFOUND",
                # A profile of its own, or a browser the user has open takes over
                # the command and no picture is written.
                f"--user-data-dir={Path(scratch) / 'profile'}",
                "--hide-scrollbars",
                f"--window-size={width},{height}",
                f"--force-device-scale-factor={_SCALE}",
                f"--screenshot={path}",
                page.as_uri(),
            ]
            try:
                subprocess.run(command, check=True, capture_output=True, timeout=120)
            except (OSError, subprocess.SubprocessError) as error:
                print(f"zallery: no HTML thumbnail, {error}", file=sys.stderr)
                light_path.unlink(missing_ok=True)
                return False
    return light_path.is_file() and dark_path.is_file()
