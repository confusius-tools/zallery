"""Tests for zallery.xarray."""

from __future__ import annotations

import subprocess
import sys

from zallery.xarray import Xarray

_VIEW = (
    "<pre class='xr-text-repr-fallback'>fallback</pre>"
    "<div class='xr-wrap' style='display:none'><ul class='xr-sections'></ul></div>"
)


def test_importing_the_module_does_not_import_xarray() -> None:
    code = "import sys, zallery.xarray; sys.exit('xarray' in sys.modules)"
    assert subprocess.run([sys.executable, "-c", code], check=False).returncode == 0


def test_html_leaves_other_outputs_alone() -> None:
    assert Xarray().html("<table><tr><td>1</td></tr></table>") == (
        "<table><tr><td>1</td></tr></table>"
    )


def test_html_shows_the_view_and_writes_the_variables_of_each_scheme() -> None:
    html = Xarray().html(_VIEW)

    assert "xr-text-repr-fallback" not in html
    assert "<div class='xr-wrap'><ul class='xr-sections'></ul></div>" in html
    light, dark = html.split("[data-md-color-scheme='slate'] .xr-wrap{")
    assert "[data-md-color-scheme='default'] .xr-wrap{" in light
    assert "--xr-background-color: #fff;" in light
    assert "--xr-background-color: #111720;" in dark
    # The rules that make the view fit in a Zensical page.
    assert ".gallery-rich-output .xr-sections{display:grid!important;}" in html


def test_a_subclass_sets_the_colors_of_each_scheme() -> None:
    class Mine(Xarray):
        variables = {
            **Xarray.variables,
            "--xr-background-color": ("#abcdef", "#123456"),
        }

    html = Mine().html(_VIEW)
    light, dark = html.split("[data-md-color-scheme='slate'] .xr-wrap{")
    assert "--xr-background-color: #abcdef;" in light
    assert "--xr-background-color: #123456;" in dark
