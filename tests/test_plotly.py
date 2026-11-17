"""Tests for zallery.integration.plotly."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from contextlib import ExitStack

import plotly.graph_objects as go
import plotly.io as pio
import pytest

from zallery.integration import Scheme
from zallery.integration.plotly import MIME, Plotly

CLEAR = "rgba(0,0,0,0)"


def _payload(fig: go.Figure) -> dict:
    """Return a figure as the plotly mime type carries it, with a config."""
    return {**json.loads(pio.to_json(fig)), "config": {"scrollZoom": True}}


def _look(integration: Plotly, fig: go.Figure, scheme: Scheme) -> ExitStack:
    """Return the context manager of a retheme, which plotly always has."""
    look = integration.retheme(fig, scheme)
    assert look is not None
    return look


def test_importing_the_module_does_not_import_plotly() -> None:
    code = "import sys, zallery.integration.plotly; sys.exit('plotly' in sys.modules)"
    assert subprocess.run([sys.executable, "-c", code], check=False).returncode == 0


def test_retheme_merges_the_dark_template_and_restores_the_figure() -> None:
    fig = go.Figure(go.Bar(y=[1, 2]))
    before = fig.layout.template.to_plotly_json()
    with _look(Plotly(), fig, "dark"):
        merged = fig.layout.template.layout
        assert merged.paper_bgcolor == CLEAR
        assert merged.font.color == pio.templates["plotly_dark"].layout.font.color
    assert fig.layout.template.to_plotly_json() == before


def test_retheme_to_light_only_clears_the_paper() -> None:
    fig = go.Figure(go.Bar(y=[1, 2]))
    colorway = fig.layout.template.layout.colorway
    with _look(Plotly(), fig, "light"):
        assert fig.layout.template.layout.paper_bgcolor == CLEAR
        assert fig.layout.template.layout.colorway == colorway


def test_a_subclass_names_its_templates() -> None:
    class White(Plotly):
        template = ("plotly_white", "plotly_dark")

    fig = go.Figure(go.Bar(y=[1, 2]))
    with _look(White(), fig, "light"):
        assert (
            fig.layout.template.layout.xaxis.gridcolor
            == pio.templates["plotly_white"].layout.xaxis.gridcolor
        )


def test_an_unknown_template_names_the_attribute() -> None:
    class Wrong(Plotly):
        template = (None, "no_such_template")

    with pytest.raises(ValueError, match=r"^Wrong\.template"):
        Wrong().retheme(go.Figure(), "dark")


def test_both_puts_the_light_figure_in_the_data_and_the_dark_one_in_the_metadata() -> (
    None
):
    data = {MIME: _payload(go.Figure(go.Bar(y=[1, 2])))}
    metadata: dict = {}
    Plotly()._both(data, metadata)
    light, dark = data[MIME], metadata[MIME]["dark"]
    assert light["layout"]["template"]["layout"]["paper_bgcolor"] == CLEAR
    assert (
        dark["layout"]["template"]["layout"]["font"]["color"]
        == pio.templates["plotly_dark"].layout.font.color
    )
    assert light["data"] == dark["data"]
    assert light["config"] == dark["config"] == {"scrollZoom": True}
    json.dumps([data, metadata])


def test_both_gives_a_figure_without_template_only_what_retheme_merges() -> None:
    data: dict = {MIME: {"data": [{"type": "bar", "y": [1]}], "layout": {}}}
    Plotly()._both(data, {})
    # None of the colors, fonts and axes of plotly's default template.
    assert data[MIME]["layout"]["template"]["layout"] == {"paper_bgcolor": CLEAR}


def test_both_leaves_a_figure_plotly_rejects_as_sent() -> None:
    """A figure shown with `validate=False` is drawn as it is in both schemes."""
    payload = {"data": [{"type": "bar", "y": [1], "no_such_property": 1}], "layout": {}}
    data = {MIME: payload}
    sent = copy.deepcopy(data)
    metadata: dict = {}

    with pytest.warns(UserWarning, match="plotly"):
        Plotly()._both(data, metadata)

    assert data == sent
    assert metadata == {}
