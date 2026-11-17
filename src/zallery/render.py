"""Render executed notebooks to Markdown + themed image folders."""

from __future__ import annotations

import base64
import json
import re
import shutil
import struct
from collections.abc import Sequence
from html import escape
from pathlib import Path
from typing import Any

import nbformat

from zallery._types import SCENE_MIME, HtmlThumbnail
from zallery.integration import Integration
from zallery.integration.plotly import MIME as _PLOTLY_MIME

BINDER_BADGE = (
    "[![Launch in Binder](https://mybinder.org/badge_logo.svg)"
    "{ .skip-lightbox .gallery-binder }]("
)
"""Start of the Binder badge of a page, up to its launch URL.

The image is the badge mybinder.org serves for READMEs. `zallery.pipeline` finds
the badge of a cached page by this text, to stamp the current git ref into it.
"""

_DOWNLOAD_BADGE = (
    "[![Download {extension}](https://img.shields.io/badge/"
    "download-{extension}-{color}?logo={logo}&logoColor=white)"
    "{{ .skip-lightbox .gallery-download }}]({name}{extension})"
)
"""Badge that downloads one form of an example, to fill in with `str.format`.

A static badge of shields.io, in the look of the Binder one: the logo and the
word "download" on the left, the file extension on the right, in the color of the
logo.
"""

_DOWNLOADS = ((".py", "python", "3776AB"), (".ipynb", "jupyter", "F37626"))
"""Extension, shields.io logo and color of each download badge, in page order."""

ERROR_MARK = "<!-- zallery: a cell of this example raised -->"
"""Comment ending the page of an example that raised.

`zallery.pipeline` reads it to give the example its error thumbnail, also when the
page comes from the cache.
"""

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
"""ANSI control sequences (colors, cursor moves) in terminal-oriented output."""

_SCENE_STYLE = (
    "<style>.gallery-scene-dark,"
    '[data-md-color-scheme="slate"] .gallery-scene-light{display:none}'
    '[data-md-color-scheme="slate"] .gallery-scene-dark{display:inline}</style>\n'
)
"""Rule showing, of the light and the dark scene of a pyvista plot, the one of the
color scheme. It comes with the page: a site needs no style of its own for it."""

_HTML_STYLE = (
    "<style>.gallery-html-dark,"
    '[data-md-color-scheme="slate"] .gallery-html-light{display:none}'
    '[data-md-color-scheme="slate"] .gallery-html-dark{display:block}</style>\n'
)
"""Rule showing, of the light and the dark variant of an HTML output, the one of
the reader's color scheme. Both are in the page: this fits static HTML. An output
whose HTML runs scripts runs them twice."""

_PLOTLY_SCRIPT = """\
(function () {
  var element = document.getElementById("%(id)s");
  var figure = JSON.parse(document.getElementById("%(id)s-figure").textContent);
  var source = "%(source)s";  // As written: the site may prefix the src with a path.
  function draw() {
    var dark = document.body.getAttribute("data-md-color-scheme") === "slate";
    var layout = figure.layouts[dark ? "slate" : "default"];
    var data = dark && figure.dark_data || figure.data;
    Plotly.react(element, data, layout, figure.config);
  }
  function start() {
    draw();
    var observer = new MutationObserver(function () {
      if (element.isConnected) { draw(); } else { observer.disconnect(); }
    });
    observer.observe(document.body, {attributeFilter: ["data-md-color-scheme"]});
  }
  if (window.Plotly) { start(); return; }
  document.querySelector('script[src$="' + source + '"]').addEventListener("load", start);
})();"""
"""Script drawing one plotly figure, and drawing it again when the scheme changes.

On a page opened directly, the `<script src>` of plotly.js before the first figure
has run already. On a page reached by instant navigation, the theme inserts that
element again, and it runs after the figure scripts: they wait for it.
"""


def _join_str_list(value: object) -> str | None:
    """Join a list of strings, returning `None` for any other input."""
    if not isinstance(value, list):
        return None
    parts: list[str] = []
    for item in value:
        if not isinstance(item, str):
            return None
        parts.append(item)
    return "".join(parts)


def _cell_tags(cell: nbformat.NotebookNode) -> set[str]:
    """Return the tags attached to one notebook cell."""
    return set(cell.metadata.get("tags", []))


_COLLAPSE_TAG = re.compile(r"collapse(?:\[(?P<kind>[^\]]+)\])?(?::(?P<title>.*))?\Z")


def _collapse_spec(tags: set[str]) -> tuple[str, str] | None:
    """Return the (admonition type, title) for a collapsed code cell, or `None`.

    A cell tagged `collapse` has its code hidden behind a collapsed admonition —
    useful for tucking away setup/boilerplate. The tag accepts an optional admonition
    type in brackets and an optional title after a colon: `collapse`,
    `collapse: <title>`, `collapse[<type>]`, or `collapse[<type>]: <title>`. The type
    is any admonition name Zensical understands (`example`, `warning`, `tip`, ...).

    Parameters
    ----------
    tags : set[str]
        The cell's tags.

    Returns
    -------
    kind : str
        The admonition type, defaulting to `example`.
    title : str
        The callout title, defaulting to `Show code`.
    """
    # Sorted so that a cell mistakenly carrying several collapse tags picks the same
    # one on every build instead of following set iteration order.
    for tag in sorted(tags):
        match = _COLLAPSE_TAG.match(tag)
        if match:
            kind = (match["kind"] or "").strip() or "example"
            title = (match["title"] or "").strip() or "Show code"
            return kind, title
    return None


def _collapsible_code(kind: str, title: str, code_block: str) -> str:
    """Wrap a fenced code block in a collapsed `??? <kind>` admonition.

    Parameters
    ----------
    kind : str
        The admonition type (e.g. `example`, `warning`).
    title : str
        The admonition title shown on the collapsed callout.
    code_block : str
        The fenced code block Markdown to hide.

    Returns
    -------
    str
        The Markdown for the collapsed callout, with `code_block` indented as its content.
    """
    indented = "\n".join(
        ("    " + line) if line.strip() else "" for line in code_block.splitlines()
    )
    return f'??? {kind} "{title}"\n\n{indented}\n'


def _tag_value(tags: set[str], key: str) -> str | None:
    """Return the value of a cell's `<key>: <value>` tag, or `None`.

    Parameters
    ----------
    tags : set[str]
        The cell's tags.
    key : str
        The name before the colon, such as `tab` or `title`.

    Returns
    -------
    str or None
        The value, or `None` if no tag gives a non-empty one.
    """
    prefix = f"{key}:"
    # Sorted for the same reason as in `_collapse_spec`.
    for tag in sorted(tags):
        value = tag.removeprefix(prefix).strip()
        if tag.startswith(prefix) and value:
            return value
    return None


_HIGHLIGHT_LINES = re.compile(r"\d+(-\d+)?(\s+\d+(-\d+)?)*")
"""Line numbers and ranges separated by spaces, such as `2 4-5`."""


def _code_fence(source: str, tags: set[str], *, annotate: bool) -> str:
    """Return the fenced code block of a code cell.

    The tags `title: <text>` and `hl_lines: <lines>` become the options of the same
    name on the fence. An `hl_lines` value that is not a list of line numbers and
    ranges is ignored.

    Parameters
    ----------
    source : str
        The cell's code.
    tags : set[str]
        The cell's tags.
    annotate : bool
        Whether to mark the block as annotated, so that the theme reads the numbered
        list that follows it as the notes of its `# (1)!` comments.

    Returns
    -------
    str
        The Markdown for the fenced block.
    """
    options = [".annotate"] if annotate else []
    title = _tag_value(tags, "title")
    if title is not None:
        # The option has no escape for a quote: delimit the title with the kind it
        # does not use, and give up its double quotes if it uses both.
        if '"' in title and "'" in title:
            title = title.replace('"', "'")
        quote = "'" if '"' in title else '"'
        options.append(f"title={quote}{title}{quote}")
    lines = _tag_value(tags, "hl_lines")
    if lines is not None and _HIGHLIGHT_LINES.fullmatch(lines):
        options.append(f'hl_lines="{lines}"')
    opening = "``` { .python " + " ".join(options) + " }" if options else "```python"
    return f"{opening}\n{source.rstrip()}\n```\n"


def _tab_set(key: str, tabs: list[tuple[str, str]]) -> str:
    """Return one set of content tabs.

    The set is written as raw HTML, in the markup `pymdownx.tabbed` produces with
    `alternate_style` and the theme styles. The Markdown syntax (`=== "<title>"`) is
    not an option: it needs the tab content indented, where Python-Markdown reads an
    HTML output (a DataFrame, an xarray repr) as text and mangles it. In a raw HTML
    block, fenced code is still highlighted and everything else is left alone.

    Parameters
    ----------
    key : str
        What tells the set from the others of the page; it goes in the ids.
    tabs : list[tuple[str, str]]
        Title and Markdown content of each tab, in order.

    Returns
    -------
    str
        The HTML of the set, with its first tab selected.
    """
    # The prefix keeps the ids apart from those of tabs written in a Markdown cell.
    name = f"__zallery_tab_{key}"
    inputs = labels = blocks = ""
    for index, (title, content) in enumerate(tabs, start=1):
        checked = 'checked="checked" ' if index == 1 else ""
        inputs += f'<input {checked}id="{name}_{index}" name="{name}" type="radio" />'
        labels += f'<label for="{name}_{index}">{escape(title)}</label>'
        blocks += f'<div class="tabbed-block">\n\n{content}\n</div>\n'
    return (
        f'<div class="tabbed-set tabbed-alternate" data-tabs="{key}:{len(tabs)}">'
        f'{inputs}<div class="tabbed-labels">{labels}</div>\n'
        f'<div class="tabbed-content">\n{blocks}</div>\n</div>\n'
    )


def _flush_tabs(parts: list[str], tabs: list[tuple[str, str]]) -> None:
    """Append the pending tab cells to `parts` as one set of tabs, then clear them.

    Parameters
    ----------
    parts : list[str]
        Markdown fragments of the page so far; extended in place.
    tabs : list[tuple[str, str]]
        Title and Markdown content of each pending tab, in order; emptied in place.
    """
    if not tabs:
        return
    # The position of the set among the page fragments is unique on the page.
    parts.append(_tab_set(str(len(parts)), tabs))
    tabs.clear()


def _image_data(output: dict[str, object], mime: str = "image/png") -> str | None:
    """Return the base64 payload of one image type from an output, if present."""
    data = output.get("data")
    if not isinstance(data, dict):
        return None
    image = data.get(mime)
    image_joined = _join_str_list(image)
    if image_joined is not None:
        return image_joined
    if isinstance(image, str):
        return image
    return None


def _dark(output: dict[str, object], mime: str) -> object:
    """Return the dark payload an integration stored for one mime type, if any."""
    metadata = output.get("metadata")
    if not isinstance(metadata, dict):
        return None
    mime_metadata = metadata.get(mime)
    if not isinstance(mime_metadata, dict):
        return None
    return mime_metadata.get("dark")


def _dark_data(output: dict[str, object], mime: str = "image/png") -> str | None:
    """Return the dark payload of a mime type whose payload is text, if any."""
    dark = _dark(output, mime)
    return dark if isinstance(dark, str) else None


def _write_image(path: Path, payload: str) -> None:
    """Decode and write one base64 image payload."""
    path.write_bytes(base64.b64decode(payload))


def _image_tag(*, src: str, alt: str) -> str:
    """Return a plain HTML image tag for Markdown output."""
    return f'<img src="{src}" alt="{alt}">'


def _html_block(html: str, scheme: str | None = None) -> str:
    """Return a raw HTML block for Markdown output.

    Parameters
    ----------
    html : str
        The HTML of an output.
    scheme : str, optional
        `"light"` or `"dark"`, for the variant of an output that has both: the
        block shows under that color scheme only (see `_HTML_STYLE`). If not
        provided, the block shows under both.

    Returns
    -------
    str
        The block.
    """
    only = f" gallery-html-{scheme}" if scheme is not None else ""
    return f'<div class="gallery-rich-output{only}">' + html.rstrip() + "</div>\n"


def _write_plotly_js(out_dir: Path) -> str:
    """Write the plotly.js of the installed plotly next to a page.

    plotly is installed whenever a page shows a plotly figure: the kernel runs on
    the interpreter Zallery runs on. Its plotly.js is the one its figures are made
    for.

    Parameters
    ----------
    out_dir : pathlib.Path
        Folder of the page.

    Returns
    -------
    str
        The file name, which holds the plotly.js version.
    """
    # Imported here, for galleries with no plotly figure.
    from plotly.offline import get_plotlyjs, get_plotlyjs_version

    name = f"plotly-{get_plotlyjs_version()}.min.js"
    (out_dir / name).write_text(get_plotlyjs(), encoding="utf-8")
    return name


def _write_scene_viewer(out_dir: Path) -> str:
    """Copy the page that draws an exported pyvista scene next to a page.

    It is the standalone viewer of trame-vtk, which is installed whenever pyvista
    exports a scene: it loads the scene named in its `fileURL` query and draws it
    with vtk.js, in the browser alone.

    Parameters
    ----------
    out_dir : pathlib.Path
        Folder of the page.

    Returns
    -------
    str
        The file name, which holds the trame-vtk version.
    """
    # Imported here, for galleries with no pyvista scene.
    from importlib.metadata import version

    from trame_vtk.tools.vtksz2html import HTML_VIEWER_PATH

    name = f"vtk-viewer-{version('trame-vtk')}.html"
    shutil.copyfile(HTML_VIEWER_PATH, out_dir / name)
    return name


def _plotly_block(
    figure: dict[str, Any],
    element_id: str,
    source: str,
    *,
    load: bool,
    thumbnail: bool = False,
    dark: dict[str, Any] | None = None,
) -> str:
    """Return HTML drawing a plotly figure in the color scheme of the page.

    The renderer changes nothing in the figures: the look of each scheme is what
    the kernel gave them (see `zallery.integration.plotly`).

    Parameters
    ----------
    figure : dict
        The figure of the light scheme, as the plotly mime type carries it.
    element_id : str
        Id of the element the figure is drawn in, unique in the page.
    source : str
        URL of plotly.js, relative to the page (see `_write_plotly_js`).
    load : bool
        Whether to load plotly.js before the figure: true for the first figure of
        the page only.
    thumbnail : bool, default: False
        Whether to draw the figure for a thumbnail picture instead: at the size of
        the browser window, which it fills, with plotly.js written in the page,
        since the browser loads nothing.
    dark : dict, optional
        The figure of the dark scheme. If not provided, the figure is drawn as it
        is under both schemes.

    Returns
    -------
    str
        The HTML: the element, the figure as JSON, and the script drawing it.
    """
    layout = figure.get("layout") or {}
    dark_layout = layout if dark is None else dark.get("layout") or {}
    own = layout.get("template") or {}
    if thumbnail:
        # Imported here, for galleries with no plotly figure.
        from plotly.offline import get_plotlyjs

        loader = f"<script>{get_plotlyjs()}</script>\n"
        layout, dark_layout = (
            {k: v for k, v in each.items() if k not in ("width", "height")}
            for each in (layout, dark_layout)
        )
        style = "position: fixed; inset: 0"
    else:
        loader = f'<script src="{source}"></script>\n' if load else ""
        # A responsive figure is as high as its element: without a height, the
        # element collapses on the first redraw. Same height as plotly's notebook
        # renderer.
        height = layout.get("height") or (own.get("layout") or {}).get("height") or 525
        style = f"height: {height}px"
    page = {
        "data": figure.get("data") or [],
        "layouts": {"default": layout, "slate": dark_layout},
        "config": {
            "responsive": True,
            **(figure.get("config") or {}),
            # The toolbar is of no use on a picture.
            **({"displayModeBar": False} if thumbnail else {}),
        },
    }
    dark_data = [] if dark is None else dark.get("data") or []
    if dark is not None and dark_data != page["data"]:
        # Traces that differ between the schemes; equal ones are held once.
        page["dark_data"] = dark_data
    # `<` escaped, so that no string of the figure can close the script element.
    data = json.dumps(page, separators=(",", ":")).replace("<", "\\u003c")
    script = _PLOTLY_SCRIPT % {"id": element_id, "source": source}
    return (
        f'{loader}<div id="{element_id}" class="gallery-plotly" style="{style}"></div>\n'
        f'<script type="application/json" id="{element_id}-figure">{data}</script>\n'
        f"<script>\n{script}\n</script>"
    )


def _output_code_block(text: str) -> str:
    """Return a fenced code block for plain-text cell output.

    The block is wrapped in a `gallery-output` container so docs CSS can wrap long
    output lines (warnings, reprs, tracebacks) instead of showing a horizontal
    scrollbar, without affecting the syntax-highlighted input code cells. The
    `markdown` attribute lets Zensical still render the fence as a highlighted block.

    ANSI escape sequences, such as the colors of an IPython traceback, are dropped:
    a fenced block would show them verbatim.

    Parameters
    ----------
    text : str
        The plain-text output to display.

    Returns
    -------
    str
        The Markdown for the wrapped, fenced output block.
    """
    return (
        '<div class="gallery-output" markdown>\n\n```\n'
        + _ANSI_ESCAPE.sub("", text).rstrip("\n")
        + "\n```\n\n</div>\n"
    )


def _flush_text_outputs(parts: list[str], pending: list[str]) -> None:
    """Append the pending plain-text outputs to `parts` as one block, then clear them.

    Consecutive plain-text outputs of a cell (printed text, the value of its last
    expression, a traceback) read as one output, as in a notebook, so they share a
    block. An image or HTML output in between starts a new one.

    Parameters
    ----------
    parts : list[str]
        Markdown fragments of the page so far; extended in place.
    pending : list[str]
        Plain-text outputs not written yet, in order; emptied in place.
    """
    if pending:
        parts.append(
            _output_code_block("\n".join(text.rstrip("\n") for text in pending))
        )
        pending.clear()


def _normalize_html_output(html: str) -> str:
    """Normalize rich HTML reprs for static docs rendering.

    A table that `rich` drew with box characters gets a class, for the site styles
    to keep its lines joined.
    """
    if "font-family:Menlo" in html and any(corner in html for corner in "┏┌╔╭"):
        html = html.replace("<pre ", '<pre class="gallery-rich-table" ', 1)
    return html


def _page_html(html: str, integrations: Sequence[Integration]) -> str:
    """Return an HTML output as the page holds it.

    Parameters
    ----------
    html : str
        The HTML of an output, or its dark variant.
    integrations : Sequence[Integration]
        The integrations in effect: the output passes through the `html` method
        of each, in order.

    Returns
    -------
    str
        The HTML to write on the page.
    """
    html = _normalize_html_output(html)
    for integration in integrations:
        html = integration.html(html)
    return html


def _clean_stream_text(text: str) -> str:
    """Remove known noisy notebook warnings from stream output."""
    cleaned_lines: list[str] = []
    skip_next = False
    for line in text.splitlines():
        if "TqdmWarning: IProgress not found" in line:
            skip_next = True
            continue
        if skip_next and "from .autonotebook import tqdm as notebook_tqdm" in line:
            skip_next = False
            continue
        # VTK, on a machine without display, before it renders off screen instead.
        if "vtkXOpenGLRenderWindow" in line and "bad X server connection" in line:
            continue
        skip_next = False
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip("\n")


def _is_blank_widget_output(output: dict[str, object]) -> bool:
    """Return whether `output` is a content-free rich/Jupyter display artifact.

    Some dependency prints via `rich`'s Jupyter console protocol, which renders a
    `display_data` output carrying both `text/html` and `text/plain` even when
    there is nothing to show (confirmed in CI: an empty `<pre style="...">` tag
    with a blank `text/plain`). `text/plain` is the one part of Jupyter's
    mimetype-bundle convention every real result populates (matplotlib figures
    carry `image/png` instead), so a blank one reliably means "nothing a reader
    would want to see". Real cell output (a figure, a DataArray repr, printed
    text) never has a blank `text/plain`.
    """
    if output.get("output_type") != "display_data":
        return False
    data = output.get("data")
    if not isinstance(data, dict) or not data:
        return False
    if any(isinstance(key, str) and key.startswith("image/") for key in data):
        return False
    if not set(data).issubset({"text/html", "text/plain"}):
        return False

    plain = data.get("text/plain", "")
    text = _join_str_list(plain)
    if text is None:
        text = str(plain)
    return not text.strip()


def render_notebook(
    source_notebook: nbformat.NotebookNode,
    executed_notebook: nbformat.NotebookNode,
    *,
    out_dir: Path,
    base_name: str,
    runtime_seconds: float,
    binder_url: str | None = None,
    html_thumbnail: HtmlThumbnail | None = None,
    integrations: Sequence[Integration] = (),
) -> tuple[Path, tuple[Path, Path] | None]:
    """Render an executed notebook to Markdown plus light and dark image folders.

    Parameters
    ----------
    source_notebook : nbformat.NotebookNode
        The example as read from disk; provides code, Markdown and cell tags.
    executed_notebook : nbformat.NotebookNode
        The same cells after execution. An output an integration rethemed
        carries its dark variant under `metadata[<mime type>]["dark"]` (see
        `zallery.integration`); other outputs are shown unchanged in both schemes.
    out_dir : pathlib.Path
        Directory to write the page and image folders into.
    base_name : str
        Output stem for the page and its asset folders.
    runtime_seconds : float
        Execution time printed at the bottom of the page.
    binder_url : str, optional
        Binder launch URL for the page's badge. If not provided, no badge.
    html_thumbnail : HtmlThumbnail, optional
        Writes the thumbnails of an HTML output. If not provided, only an image
        output can be a thumbnail.
    integrations : Sequence[Integration], default: ()
        The integrations in effect: each HTML output passes through their `html`
        method, in order.

    Returns
    -------
    markdown_path : pathlib.Path
        The rendered page.
    thumbnail : tuple[pathlib.Path, pathlib.Path] or None
        Light and dark thumbnail paths, if a `thumbnail`-tagged cell produced an
        image, or an HTML output that `html_thumbnail` could picture.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    light_image_dir = out_dir / f"{base_name}_output_light"
    dark_image_dir = out_dir / f"{base_name}_output_dark"
    light_image_dir.mkdir(exist_ok=True)
    dark_image_dir.mkdir(exist_ok=True)

    parts: list[str] = []
    tabs: list[tuple[str, str]] = []
    thumbnail: tuple[Path, Path] | None = None
    plotly_js: str | None = None
    scene_viewer: str | None = None
    html_schemes = False
    failed = False
    cells = source_notebook.cells
    # Index of a Markdown cell already written under the code cell it annotates.
    moved = 0

    for cell_index, (cell, executed_cell) in enumerate(
        zip(cells, executed_notebook.cells, strict=True), start=1
    ):
        if cell_index == moved:
            continue
        if cell.cell_type == "markdown":
            _flush_tabs(parts, tabs)
            parts.append(cell.source.rstrip() + "\n")
            continue
        if cell.cell_type != "code":
            continue

        tags = _cell_tags(cell)
        tab_title = _tag_value(tags, "tab")
        cell_parts: list[str] = []
        # A tab is a raw HTML block, where Markdown syntax (the `???` of `collapse`,
        # the list of annotations) would show as text: both tags are ignored there.
        annotate = "annotate" in tags and tab_title is None
        code_block = _code_fence(cell.source, tags, annotate=annotate)
        # `cell_index` counts from 1, so it is the position of the next cell.
        following = cells[cell_index] if cell_index < len(cells) else None
        if annotate and following is not None and following.cell_type == "markdown":
            # The theme takes the notes from the list directly under the code block.
            code_block += "\n" + following.source.rstrip() + "\n"
            moved = cell_index + 1
        collapse = _collapse_spec(tags)
        if collapse is not None and tab_title is None:
            cell_parts.append(_collapsible_code(*collapse, code_block))
        else:
            cell_parts.append(code_block)

        outputs = [
            o
            for o in executed_cell.get("outputs", [])
            if not _is_blank_widget_output(o)
        ]
        pending_text: list[str] = []
        first_html: tuple[str, str] | None = None
        for output_index, output in enumerate(outputs):
            output_type = output.get("output_type")
            if output_type == "stream":
                stream_text = _clean_stream_text(str(output.get("text", "")))
                if stream_text:
                    pending_text.append(stream_text)
                continue

            if output_type in {"execute_result", "display_data"}:
                gif = _image_data(output, "image/gif")
                if gif is not None:
                    _flush_text_outputs(cell_parts, pending_text)
                    # An animation has no dark rendering: one file, in both schemes.
                    name = f"{base_name}_cell_{cell_index:02d}_{output_index}.gif"
                    _write_image(out_dir / name, gif)
                    alt = f"Example output from cell {cell_index}, image {output_index}"
                    cell_parts.append(_image_tag(src=name, alt=alt) + "\n")
                    continue
                light_png = _image_data(output)
                if light_png is not None:
                    _flush_text_outputs(cell_parts, pending_text)
                    # Images that did not come through the matplotlib hook have no
                    # dark rendering: show the same picture in both themes.
                    dark_png = _dark_data(output) or light_png
                    light_name = f"cell_{cell_index:02d}_{output_index}_light.png"
                    dark_name = f"cell_{cell_index:02d}_{output_index}_dark.png"
                    light_path = light_image_dir / light_name
                    dark_path = dark_image_dir / dark_name
                    _write_image(light_path, light_png)
                    _write_image(dark_path, dark_png)

                    alt = f"Example output from cell {cell_index}, image {output_index}"
                    pictures = (
                        _image_tag(
                            src=f"{base_name}_output_light/{light_name}#only-light",
                            alt=alt,
                        )
                        + _image_tag(
                            src=f"{base_name}_output_dark/{dark_name}#only-dark",
                            alt=alt,
                        )
                        + "\n"
                    )
                    scene = _image_data(output, SCENE_MIME)
                    if scene is None:
                        cell_parts.append(pictures)
                    else:
                        if scene_viewer is None:
                            scene_viewer = _write_scene_viewer(out_dir)
                            cell_parts.append(_SCENE_STYLE)
                        # The frame has the shape of the picture: a PNG starts with
                        # its size.
                        width, height = struct.unpack(
                            ">II", base64.b64decode(light_png)[16:24]
                        )
                        dark_scene = _dark_data(output, SCENE_MIME)
                        stem = f"{base_name}_cell_{cell_index:02d}_{output_index}"
                        frames = ""
                        for scheme, payload in (("light", scene), ("dark", dark_scene)):
                            if payload is None:
                                continue
                            name = f"{stem}{'_dark' * (scheme == 'dark')}.vtksz"
                            _write_image(out_dir / name, payload)
                            # Without a dark scene, the only frame is for both schemes.
                            one = f" gallery-scene-{scheme}" * (dark_scene is not None)
                            frames += (
                                f'<iframe class="gallery-scene{one}" title="{alt}" '
                                f'src="{scene_viewer}?fileURL={name}" loading="lazy" '
                                f'style="width: 100%; aspect-ratio: {width} / {height};'
                                ' border: 0"></iframe>\n'
                            )
                        # The picture first, as in the pyvista documentation: a scene
                        # loads when its tab is opened.
                        cell_parts.append(
                            _tab_set(
                                f"scene_{cell_index}_{output_index}",
                                [
                                    ("Static Scene", pictures),
                                    ("Interactive Scene", frames),
                                ],
                            )
                        )

                    if "thumbnail" in tags and thumbnail is None:
                        thumb_light = out_dir / f"{base_name}_thumb_light.png"
                        thumb_dark = out_dir / f"{base_name}_thumb_dark.png"
                        shutil.copyfile(light_path, thumb_light)
                        shutil.copyfile(dark_path, thumb_dark)
                        thumbnail = (thumb_light, thumb_dark)
                    continue

                data = output.get("data", {})
                if isinstance(data, dict) and _PLOTLY_MIME in data:
                    _flush_text_outputs(cell_parts, pending_text)
                    load = plotly_js is None
                    if plotly_js is None:
                        plotly_js = _write_plotly_js(out_dir)
                    element_id = f"zallery-plotly-{cell_index}-{output_index}"
                    figure = data[_PLOTLY_MIME]
                    dark_figure = _dark(output, _PLOTLY_MIME)
                    if not isinstance(dark_figure, dict):
                        dark_figure = None
                    block = _plotly_block(
                        figure, element_id, plotly_js, load=load, dark=dark_figure
                    )
                    cell_parts.append(_html_block(block))
                    if (
                        html_thumbnail is not None
                        and "thumbnail" in tags
                        and first_html is None
                    ):
                        # One HTML for both pictures: its script draws the figure
                        # of the scheme the page is pictured under.
                        picture = _plotly_block(
                            figure,
                            element_id,
                            plotly_js,
                            load=True,
                            thumbnail=True,
                            dark=dark_figure,
                        )
                        first_html = (picture, picture)
                    continue
                if isinstance(data, dict) and "text/html" in data:
                    html = data["text/html"]
                    if isinstance(html, list):
                        html = "".join(html)
                    _flush_text_outputs(cell_parts, pending_text)
                    html = _page_html(str(html), integrations)
                    dark_html = _dark_data(output, "text/html")
                    if dark_html is None:
                        cell_parts.append(_html_block(html))
                    else:
                        dark_html = _page_html(dark_html, integrations)
                        if not html_schemes:
                            cell_parts.append(_HTML_STYLE)
                            html_schemes = True
                        cell_parts.append(
                            _html_block(html, "light") + _html_block(dark_html, "dark")
                        )
                    first_html = first_html or (html, dark_html or html)
                    continue
                if isinstance(data, dict) and "text/plain" in data:
                    pending_text.append(str(data["text/plain"]))
                continue

            if output_type == "error":
                failed = True
                pending_text.append("\n".join(output.get("traceback", [])))
        _flush_text_outputs(cell_parts, pending_text)

        # After the outputs, so that an image anywhere in the cell comes first.
        if (
            html_thumbnail is not None
            and first_html is not None
            and thumbnail is None
            and "thumbnail" in tags
        ):
            thumb_light = out_dir / f"{base_name}_thumb_light.png"
            thumb_dark = out_dir / f"{base_name}_thumb_dark.png"
            if html_thumbnail(*first_html, thumb_light, thumb_dark):
                thumbnail = (thumb_light, thumb_dark)

        if tab_title is None:
            _flush_tabs(parts, tabs)
            parts.extend(cell_parts)
        else:
            tabs.append((tab_title, "\n".join(cell_parts)))
    _flush_tabs(parts, tabs)

    parts.append("\n---\n")
    parts.append(f"**Total running time:** {runtime_seconds:.1f} s\n\n")
    buttons: list[str] = []
    if binder_url is not None:
        buttons.append(f"{BINDER_BADGE}{binder_url})")
    buttons.extend(
        _DOWNLOAD_BADGE.format(
            extension=extension, logo=logo, color=color, name=base_name
        )
        for extension, logo, color in _DOWNLOADS
    )
    parts.append(" ".join(buttons) + "\n")
    if failed:
        parts.append(ERROR_MARK + "\n")

    markdown_path = out_dir / f"{base_name}.md"
    markdown_path.write_text("\n".join(parts), encoding="utf-8")
    return markdown_path, thumbnail
