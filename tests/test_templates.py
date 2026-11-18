"""Tests for the mkdocstrings templates Zallery ships."""

from __future__ import annotations

from importlib.resources import files
from typing import NamedTuple

import jinja2
import pytest


class Crumb(NamedTuple):
    """A step of the trail of a backlink, as mkdocs-autorefs gives it."""

    title: str
    url: str


class Backlink(NamedTuple):
    """A backlink: the trail to the reference, the page title before the heading."""

    crumbs: tuple[Crumb, ...]


def _example(title: str, page: str) -> Backlink:
    """Return the backlink of a reference Zallery wrote at the end of an example."""
    return Backlink(
        (
            Crumb("Examples", ""),
            Crumb(title, f"{page}#{title.lower().replace(' ', '-')}"),
            Crumb("API used in this example", f"{page}#gallery-api"),
        )
    )


def _render(backlinks: dict[str, list[Backlink]], option: str | bool = "tree") -> str:
    text = (
        files("zallery")
        .joinpath("templates", "python", "material", "backlinks.html.jinja")
        .read_text(encoding="utf-8")
    )
    template = jinja2.Environment(autoescape=True).from_string(text)
    return template.render(config={"backlinks": option}, backlinks=backlinks)


def test_backlinks_template_keeps_only_the_examples() -> None:
    html = _render(
        {
            "referenced-by": [
                _example("A first plot", "../../examples/first/"),
                Backlink(
                    (Crumb("User guide", ""), Crumb("Colors", "../guide/#colors"))
                ),
            ],
            "used-by": [Backlink((Crumb("other.function", "../api/#other.function"),))],
        }
    )

    assert "Used in the examples" in html
    assert '<a href="../../examples/first/#a-first-plot">A first plot</a>' in html
    # Not the heading of the list, and no other page.
    assert "gallery-api" not in html
    assert "Colors" not in html
    assert "other.function" not in html


def test_backlinks_template_lists_the_examples_by_title() -> None:
    html = _render(
        {
            "referenced-by": [
                _example("Second example", "../b/"),
                _example("A first example", "../a/"),
            ]
        }
    )

    assert html.index("A first example") < html.index("Second example")
    assert html.count("<li") == 2


@pytest.mark.parametrize(
    ("backlinks", "option"),
    [
        ({"referenced-by": [Backlink((Crumb("Colors", "../guide/#colors"),))]}, "tree"),
        ({}, "flat"),
        ({"referenced-by": [_example("A first plot", "../a/")]}, False),
    ],
    ids=["no example", "no backlink", "backlinks off"],
)
def test_backlinks_template_shows_nothing(
    backlinks: dict[str, list[Backlink]], option: str | bool
) -> None:
    assert _render(backlinks, option).strip() == ""
