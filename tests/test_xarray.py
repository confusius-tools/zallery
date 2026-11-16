"""Tests for zallery.xarray."""

from __future__ import annotations

import subprocess
import sys

from zallery.render import _normalize_html_output
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


def test_html_writes_an_xarray_view_as_render_does_today() -> None:
    # Both exist until the render task removes its own copy.
    assert Xarray().html(_VIEW) == _normalize_html_output(_VIEW)


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
