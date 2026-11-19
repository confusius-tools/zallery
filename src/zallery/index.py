"""Generate the gallery index page and the page of each section."""

from __future__ import annotations

import html as html_lib
import json
import os
import re
from collections import defaultdict
from pathlib import Path

from zallery._types import RenderedExample

_DEFAULT_THUMB_LIGHT = "_assets/default_thumb.svg"
_DEFAULT_THUMB_DARK = "_assets/default_thumb_dark.svg"

_ERROR_THUMB_LIGHT = "_assets/error_thumb.svg"
_ERROR_THUMB_DARK = "_assets/error_thumb_dark.svg"
"""Thumbnails of an example that raised, if the gallery root has both files."""

_INDEX_HEADER = "_index.md"
"""File in the gallery root whose content opens the index page, if present."""

_DEFAULT_HEADER = (
    "# Examples\n\n"
    "Each example starts from a plain Python script and is rendered as a "
    "notebook-style\n"
    "page with code, outputs, and downloadable source files.\n"
)
"""Index page header used when the gallery root has no `_index.md`."""

API_CARDS = "python/material/gallery_cards.html.jinja"
"""Path of the cards of the examples, in the folder of the mkdocstrings templates.

Next to the backlinks template Zallery ships, which imports it by its file name.
"""

SECTION_PAGE = "index.md"
"""File name of the page of a section, next to the pages of its examples."""

_FRONT_MATTER = re.compile(r"\A---\r?\n.*?\r?\n---\r?\n", re.DOTALL)
"""Front matter that opens a `_section.md`: metadata of the page of the section."""

# Markdown inline link `[text](url)`, and mkdocstrings cross-reference `[text][ident]`.
# Card overlays are copied verbatim onto the gallery index page (at the gallery root),
# where an example's relative links — written against its own built page — would not
# resolve and fail `zensical build --strict`. A cross-reference does resolve, but it
# would render as a link inside an overlay that is inert by design. The full links still
# render on the example's own page.
_INLINE_LINK = re.compile(r"\[([^\]]+)\](?:\([^)]*\)|\[[^\]]*\])")


def _flatten_links(text: str) -> str:
    """Replace Markdown inline links and cross-references with their visible text.

    Parameters
    ----------
    text : str
        Markdown text that may contain inline links or cross-references.

    Returns
    -------
    str
        The text with every `[label](target)` and `[label][identifier]` reduced to
        `label`.
    """
    return _INLINE_LINK.sub(r"\1", text)


def _demote_h1(text: str) -> str:
    """Demote a leading H1 heading to H2 so the index has a single page title."""
    lines = text.split("\n", 1)
    first = lines[0]
    # "# " matches only true H1s; "## " starts with "#" not "# ", so no extra guard needed.
    if first.startswith("# "):
        first = "#" + first
    return first + ("\n" + lines[1] if len(lines) > 1 else "")


def _split_front_matter(text: str) -> tuple[str, str]:
    """Split the content of a `_section.md` into its front matter and the rest.

    Parameters
    ----------
    text : str
        The content of the file.

    Returns
    -------
    front_matter : str
        The front matter with its two `---` lines, or an empty string if the
        file has none.
    body : str
        The rest of the file.
    """
    match = _FRONT_MATTER.match(text)
    if match is None:
        return "", text
    return match.group(), text[match.end() :]


def _link(target: Path, page_dir: Path) -> str:
    """Return the relative link to a file from a page.

    Parameters
    ----------
    target : pathlib.Path
        The file to link to.
    page_dir : pathlib.Path
        Folder of the page that holds the link.

    Returns
    -------
    str
        The path of `target` from `page_dir`, with forward slashes.
    """
    return Path(os.path.relpath(target, page_dir)).as_posix()


def _thumbnails(rex: RenderedExample, *, root: Path) -> tuple[Path, Path, str]:
    """Return the two pictures of the card of an example.

    An example that raised shows the error thumbnails, whatever its own: the card
    must show the fault. Without error thumbnails in the gallery root, it is
    treated as any other example.

    Parameters
    ----------
    rex : RenderedExample
        The example of the card.
    root : pathlib.Path
        Gallery root, which holds the default and the error thumbnails.

    Returns
    -------
    light : pathlib.Path
        The picture for the light color scheme.
    dark : pathlib.Path
        The picture for the dark color scheme.
    alt : str
        The text that stands for the pictures.
    """
    if (
        rex.failed
        and (root / _ERROR_THUMB_LIGHT).is_file()
        and (root / _ERROR_THUMB_DARK).is_file()
    ):
        return (
            root / _ERROR_THUMB_LIGHT,
            root / _ERROR_THUMB_DARK,
            "Example that raised an error",
        )
    if rex.thumbnail_light is None or rex.thumbnail_dark is None:
        return (
            root / _DEFAULT_THUMB_LIGHT,
            root / _DEFAULT_THUMB_DARK,
            "Example thumbnail",
        )
    return rex.thumbnail_light, rex.thumbnail_dark, rex.title


def _card_image_markdown(
    rex: RenderedExample, *, root: Path, page_dir: Path, href: str
) -> str:
    """Return theme-aware thumbnail markup for one example card.

    Parameters
    ----------
    rex : RenderedExample
        The example of the card.
    root : pathlib.Path
        Gallery root, which holds the default and the error thumbnails.
    page_dir : pathlib.Path
        Folder of the page the card is on: the pictures are linked from it.
    href : str
        Link to the page of the example.

    Returns
    -------
    str
        The two pictures, one for each color scheme, as a link to the example.
    """
    light, dark, alt = _thumbnails(rex, root=root)
    alt = html_lib.escape(alt, quote=True)
    return (
        f'[<img class="skip-lightbox" src="{_link(light, page_dir)}#only-light" '
        f'alt="{alt}"><img class="skip-lightbox" '
        f'src="{_link(dark, page_dir)}#only-dark" alt="{alt}">]({href})'
    )


def _card_overlay_markdown(rex: RenderedExample) -> str:
    """Return the hover-overlay markup carrying an example's summary.

    The span is centred over the card's thumbnail by `extra.css` and revealed on hover,
    mirroring sphinx-gallery's thumbnail tooltip. It stays in the thumbnail's paragraph
    so it adds no vertical space to the card.

    The summary keeps whatever inline markup Markdown gives it (`abbr` for the glossary
    terms in `docs/includes/abbreviations.md`, `code` for backticks), so `extra.css` has
    to lay the overlay out as flowing text. Do not wrap the text in an inner element:
    the pipeline drops a nested bare span, and the CSS is written not to need one.

    Parameters
    ----------
    rex : RenderedExample
        The example whose summary is shown on hover.

    Returns
    -------
    str
        The overlay markup, or an empty string for an example without a summary.
    """
    if not rex.summary:
        return ""
    # Text content, so quotes are left alone: escaping them here would survive a code
    # span, which escapes the `&` of the entity in turn and shows it verbatim.
    summary = html_lib.escape(_flatten_links(rex.summary), quote=False)
    return f'<span class="examples-card-summary" aria-hidden="true">{summary}</span>'


def _by_section(rendered: list[RenderedExample]) -> dict[str, list[RenderedExample]]:
    """Group the rendered examples by section.

    Parameters
    ----------
    rendered : list[RenderedExample]
        The rendered examples, in the order their sections should appear.

    Returns
    -------
    dict[str, list[RenderedExample]]
        The examples of each section. Sections are in the order they are first
        seen: `discover()` yields specs sorted by the section folder name (`01_io`
        before `02_registration`), not by the name without its prefix.
    """
    by_section: dict[str, list[RenderedExample]] = defaultdict(list)
    for rendered_example in rendered:
        by_section[rendered_example.spec.section].append(rendered_example)
    return by_section


def _cards(items: list[RenderedExample], *, root: Path, page_dir: Path) -> str:
    """Return the card grid of the examples of one section.

    Parameters
    ----------
    items : list[RenderedExample]
        The examples of the section.
    root : pathlib.Path
        Gallery root, which holds the default and the error thumbnails.
    page_dir : pathlib.Path
        Folder of the page the grid is on: links are relative to it.

    Returns
    -------
    str
        One card for each example, sorted by source file name.
    """
    parts = ['<div class="grid cards examples-cards" markdown>\n\n']
    for rendered_example in sorted(items, key=lambda item: item.spec.source.name):
        href = _link(rendered_example.md_path, page_dir)
        image = _card_image_markdown(
            rendered_example, root=root, page_dir=page_dir, href=href
        )
        overlay = _card_overlay_markdown(rendered_example)
        parts.append(
            f"-   {image}{overlay}\n\n    ---\n\n"
            f"    **[{rendered_example.title}]({href})**\n\n"
        )
    parts.append("</div>\n\n")
    return "".join(parts)


def build_section_pages(
    rendered: list[RenderedExample], *, root: Path
) -> dict[Path, str]:
    """Return the Markdown text of the page of each section.

    The page of a section is next to the pages of its examples. It holds the
    content of the `_section.md` of the section, front matter included, then one
    card for each example. A site lists it first under the section in its
    navigation: the front matter then gives the section its icon there.

    Parameters
    ----------
    rendered : list[RenderedExample]
        The rendered examples.
    root : pathlib.Path
        Gallery root, which holds the default and the error thumbnails.

    Returns
    -------
    dict[pathlib.Path, str]
        The text of each page, by the path to write it to.
    """
    pages: dict[Path, str] = {}
    for section, items in _by_section(rendered).items():
        page_dir = items[0].md_path.parent
        front_matter, intro = _split_front_matter(items[0].spec.section_intro)
        if front_matter:
            front_matter = front_matter.rstrip() + "\n\n"
        pages[page_dir / SECTION_PAGE] = (
            front_matter
            + (intro.strip() or f"# {section}")
            + "\n\n"
            + _cards(items, root=root, page_dir=page_dir)
        )
    return pages


def _jinja_string(text: str) -> str:
    """Return a text as a string literal of a Jinja template.

    Parameters
    ----------
    text : str
        Any text, such as the title of an example.

    Returns
    -------
    str
        The literal, in double quotes. It holds none of the characters that open
        or close a Jinja tag: they are written as escapes, which Jinja reads.
    """
    # A JSON string is a Jinja string: both read the same escapes.
    literal = json.dumps(text, ensure_ascii=False)
    for character in "{}%#":
        literal = literal.replace(character, f"\\u{ord(character):04x}")
    return literal


def build_api_cards(rendered: list[RenderedExample], *, root: Path) -> str:
    """Return the cards of the examples, as a template the backlinks one imports.

    The backlinks template Zallery ships shows, under an API object, a card for
    each example that uses it. mkdocstrings gives that template the title and the
    address of an example, not its pictures: they come from this text, which
    Zallery writes next to the template on every build (see `API_CARDS`).

    Parameters
    ----------
    rendered : list[RenderedExample]
        The rendered examples.
    root : pathlib.Path
        Gallery root, which holds the default and the error thumbnails.

    Returns
    -------
    str
        A Jinja template that sets `cards`: for each example, by the name of its
        built folder and of its page (`io/load`), the pictures the gallery index
        shows for it, as links from that folder, and the text that stands for
        them.
    """
    entries = []
    for rex in rendered:
        folder = rex.md_path.parent
        light, dark, alt = _thumbnails(rex, root=root)
        fields = {
            "light": _link(light, folder),
            "dark": _link(dark, folder),
            "alt": alt,
        }
        card = ", ".join(
            f"{_jinja_string(key)}: {_jinja_string(value)}"
            for key, value in fields.items()
        )
        key = _jinja_string(f"{folder.name}/{rex.md_path.stem}")
        entries.append(f"  {key}: {{{card}}},\n")
    return (
        "{#- The card of each example. Zallery writes this file on every build. -#}\n"
        "{% set cards = {\n" + "".join(entries) + "} %}\n"
    )


def build_index(rendered: list[RenderedExample], *, root: Path) -> str:
    """Return the Markdown text of the gallery index page.

    Parameters
    ----------
    rendered : list[RenderedExample]
        The rendered examples, in the order their sections should appear.
    root : pathlib.Path
        Examples root the index page is written to; links are relative to it. An
        `_index.md` there replaces the default page header.

    Returns
    -------
    str
        The index page: the header, then one card grid per section.
    """
    header_path = root / _INDEX_HEADER
    header = (
        header_path.read_text(encoding="utf-8")
        if header_path.is_file()
        else _DEFAULT_HEADER
    )
    parts: list[str] = [header.rstrip() + "\n\n"]

    for section, items in _by_section(rendered).items():
        # The front matter of a section is for its own page.
        intro = _demote_h1(_split_front_matter(items[0].spec.section_intro)[1].strip())
        parts.append((intro if intro else f"## {section}") + "\n\n")
        parts.append(_cards(items, root=root, page_dir=root))

    return "".join(parts)
