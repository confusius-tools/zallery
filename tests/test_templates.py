"""Tests for the mkdocstrings templates Zallery ships."""

from __future__ import annotations

import re
from importlib.resources import files
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urljoin

import jinja2
import pytest

from zallery._types import ExampleSpec, RenderedExample
from zallery.index import build_api_cards, build_index


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


_TEMPLATES = files("zallery").joinpath("templates", "python", "material")


def _render(
    backlinks: dict[str, list[Backlink]],
    option: str | bool = "tree",
    cards: str | None = None,
) -> str:
    """Render the backlinks template as mkdocstrings does, from its folder.

    `cards` is the file Zallery writes next to it on a build; the one it ships
    holds no card.
    """
    names = ("backlinks.html.jinja", "gallery_cards.html.jinja")
    sources = {
        name: _TEMPLATES.joinpath(name).read_text(encoding="utf-8") for name in names
    }
    if cards is not None:
        sources["gallery_cards.html.jinja"] = cards
    environment = jinja2.Environment(autoescape=True, loader=jinja2.DictLoader(sources))
    return environment.get_template("backlinks.html.jinja").render(
        config={"backlinks": option}, backlinks=backlinks
    )


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

    assert "Examples using:" in html
    assert '<a href="../../examples/first/#a-first-plot">A first plot</a>' in html
    # Not the heading of the list, and no other page.
    assert "#gallery-api" not in html
    assert "API used in this example" not in html
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


def _rendered(
    root: Path, name: str, title: str, *, thumbnail: bool, failed: bool = False
) -> RenderedExample:
    """Return a rendered example of the section `io`, built under `root/_built`."""
    folder = root / "_built" / "io"
    return RenderedExample(
        spec=ExampleSpec(root / "io" / f"{name}.py", name, "io", "# IO\n"),
        title=title,
        summary="",
        md_path=folder / f"{name}.md",
        thumbnail_light=folder / f"{name}_thumb_light.png" if thumbnail else None,
        thumbnail_dark=folder / f"{name}_thumb_dark.png" if thumbnail else None,
        failed=failed,
    )


def _pictures(markup: str, page: str) -> dict[str, list[str]]:
    """Return the pictures of each card, by the page its link opens.

    The markup is the HTML of the template or the Markdown of the gallery index.
    Addresses are resolved from `page`, the address of the page the markup is on.
    """
    links = re.findall(r'<a href="([^"#]*)[^"]*">((?:<img[^>]*>)+)</a>', markup)
    links += [
        (href, images)
        for images, href in re.findall(r"\[((?:<img[^>]*>)+)\]\(([^)]*)\)", markup)
    ]
    return {
        urljoin(page, href).removesuffix(".md").rstrip("/"): [
            urljoin(page, src) for src in re.findall(r'src="([^"]*)"', images)
        ]
        for href, images in links
    }


def test_backlinks_template_shows_the_cards_of_the_gallery_index(
    tmp_path: Path,
) -> None:
    root = tmp_path / "examples"
    (root / "_assets").mkdir(parents=True)
    for name in ("error_thumb.svg", "error_thumb_dark.svg"):
        (root / "_assets" / name).write_text("<svg/>")
    rendered = [
        _rendered(root, "load", "Load a file", thumbnail=True),
        _rendered(root, "save", "Save a file", thumbnail=False),
        _rendered(root, "boom", "A failing example", thumbnail=True, failed=True),
    ]
    site = "https://site.test/"
    backlinks = {
        "referenced-by": [
            _example(
                example.title, f"../../examples/_built/io/{example.spec.base_name}/"
            )
            for example in rendered
        ]
    }

    html = _render(backlinks, cards=build_api_cards(rendered, root=root))

    # The same grid, and for each example the pictures the gallery index shows:
    # its own, the default ones, or the error ones.
    # A class of its own next to those of the index: a site makes these smaller.
    assert '<div class="grid cards examples-cards gallery-api-cards">' in html
    on_api_page = _pictures(html, site + "api/pkg/")
    on_index = _pictures(build_index(rendered, root=root), site + "examples/")
    assert len(on_api_page) == 3
    assert on_api_page == on_index
    assert on_api_page[site + "examples/_built/io/save"] == [
        site + "examples/_assets/default_thumb.svg#only-light",
        site + "examples/_assets/default_thumb_dark.svg#only-dark",
    ]
    assert 'alt="Load a file"' in html
    assert "<strong><a" in html


def test_backlinks_template_reads_a_page_address_that_ends_in_html(
    tmp_path: Path,
) -> None:
    root = tmp_path / "examples"
    rendered = [_rendered(root, "load", "Load a file", thumbnail=True)]

    html = _render(
        {"referenced-by": [_example("Load a file", "../examples/_built/io/load.html")]},
        cards=build_api_cards(rendered, root=root),
    )

    assert 'src="../examples/_built/io/load_thumb_light.png#only-light"' in html


def test_backlinks_template_keeps_an_example_without_card_as_its_title() -> None:
    html = _render({"referenced-by": [_example("A first plot", "../examples/first/")]})

    assert '<a href="../examples/first/#a-first-plot">A first plot</a>' in html
    assert "<img" not in html
