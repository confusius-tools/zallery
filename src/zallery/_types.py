"""Shared dataclasses for the gallery builder."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

Palettes = tuple[tuple[str, ...], tuple[str, ...]]
"""The light and the dark matplotlib color cycle, in this order, as hex colors.

The dark color at a position replaces the light color at the same position.
"""


HtmlThumbnail = Callable[[str, Path, Path], bool]
"""Writes the thumbnails of an HTML output.

Called with the HTML and the paths of the light and the dark PNG; returns
whether it wrote them (see `zallery.thumbnail.screenshot_html`).
"""


@dataclass(frozen=True)
class ExampleSpec:
    """A single discovered example file.

    Attributes
    ----------
    source : pathlib.Path
        Absolute path to the percent-format `.py` file.
    base_name : str
        Output stem used for the rendered Markdown, downloads, and cache entry.
        Derived from `source.stem` with any leading numeric ordering prefix
        (e.g. `01_`) stripped, so the source filename can control card order
        without leaking the prefix into URLs.
    section : str
        Section folder name (e.g. `"io"`).
    section_intro : str
        Contents of the sibling `_section.md` file, or empty string if none.
    """

    source: Path
    base_name: str
    section: str
    section_intro: str


@dataclass(frozen=True)
class RenderedExample:
    """An example after the renderer has produced its artifacts."""

    spec: ExampleSpec
    title: str
    summary: str
    md_path: Path
    thumbnail_light: Path | None
    thumbnail_dark: Path | None
