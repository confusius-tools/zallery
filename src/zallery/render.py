"""Render executed notebooks to Markdown + themed image folders."""

from __future__ import annotations

import base64
import json
import re
import shutil
from html import escape
from pathlib import Path
from typing import Any

import nbformat

from zallery._types import HtmlThumbnail

BINDER_BADGE = (
    "[![Launch in Binder](https://mybinder.org/badge_logo.svg)"
    "{ .skip-lightbox .gallery-binder }]("
)
"""Start of the Binder badge of a page, up to its launch URL.

The image is the badge mybinder.org serves for READMEs. `zallery.pipeline` finds
the badge of a cached page by this text, to stamp the current git ref into it.
"""

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
"""ANSI control sequences (colors, cursor moves) in terminal-oriented output."""

_PLOTLY_MIME = "application/vnd.plotly.v1+json"
"""Mime type of a plotly figure, which plotly's default renderer in a kernel sends."""

_PLOTLY_SCRIPT = """\
(function () {
  var element = document.getElementById("%(id)s");
  var figure = JSON.parse(document.getElementById("%(id)s-figure").textContent);
  var source = "%(source)s";  // As written: the site may prefix the src with a path.
  function draw() {
    var scheme = document.body.getAttribute("data-md-color-scheme");
    var layout = figure.layouts[scheme === "slate" ? "slate" : "default"];
    Plotly.react(element, figure.data, layout, figure.config);
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


def _flush_tabs(parts: list[str], tabs: list[tuple[str, str]]) -> None:
    """Append the pending tabs to `parts` as one set of content tabs, then clear them.

    The set is written as raw HTML, in the markup `pymdownx.tabbed` produces with
    `alternate_style` and the theme styles. The Markdown syntax (`=== "<title>"`) is
    not an option: it needs the tab content indented, where Python-Markdown reads an
    HTML output (a DataFrame, an xarray repr) as text and mangles it. In a raw HTML
    block, fenced code is still highlighted and everything else is left alone.

    Parameters
    ----------
    parts : list[str]
        Markdown fragments of the page so far; extended in place.
    tabs : list[tuple[str, str]]
        Title and Markdown content of each pending tab, in order; emptied in place.
    """
    if not tabs:
        return
    # The position of the set among the page fragments is unique on the page. The
    # prefix keeps the ids apart from those of tabs written in a Markdown cell.
    name = f"__zallery_tab_{len(parts)}"
    inputs = labels = blocks = ""
    for index, (title, content) in enumerate(tabs, start=1):
        checked = 'checked="checked" ' if index == 1 else ""
        inputs += f'<input {checked}id="{name}_{index}" name="{name}" type="radio" />'
        labels += f'<label for="{name}_{index}">{escape(title)}</label>'
        blocks += f'<div class="tabbed-block">\n\n{content}\n</div>\n'
    parts.append(
        f'<div class="tabbed-set tabbed-alternate" data-tabs="{len(parts)}:{len(tabs)}">'
        f'{inputs}<div class="tabbed-labels">{labels}</div>\n'
        f'<div class="tabbed-content">\n{blocks}</div>\n</div>\n'
    )
    tabs.clear()


def _png_data(output: dict[str, object]) -> str | None:
    """Return the base64 PNG payload from an output if present."""
    data = output.get("data")
    if not isinstance(data, dict):
        return None
    png = data.get("image/png")
    png_joined = _join_str_list(png)
    if png_joined is not None:
        return png_joined
    if isinstance(png, str):
        return png
    return None


def _dark_png_data(output: dict[str, object]) -> str | None:
    """Return the dark-theme PNG payload stored by `zallery.theme`, if any."""
    metadata = output.get("metadata")
    if not isinstance(metadata, dict):
        return None
    png_metadata = metadata.get("image/png")
    if not isinstance(png_metadata, dict):
        return None
    dark = png_metadata.get("dark")
    return dark if isinstance(dark, str) else None


def _write_png(path: Path, payload: str) -> None:
    """Decode and write one base64 PNG payload."""
    path.write_bytes(base64.b64decode(payload))


def _image_tag(*, src: str, alt: str) -> str:
    """Return a plain HTML image tag for Markdown output."""
    return f'<img src="{src}" alt="{alt}">'


def _html_block(html: str) -> str:
    """Return a raw HTML block for Markdown output."""
    return '<div class="gallery-rich-output">' + html.rstrip() + "</div>\n"


def _write_plotly_js(out_dir: Path) -> str:
    """Write the plotly.js of the installed plotly next to a page.

    plotly is installed whenever a page shows a plotly figure: the kernel runs on
    the interpreter zallery runs on. Its plotly.js is the one its figures are made
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


def _plotly_block(
    figure: dict[str, Any], element_id: str, source: str, *, load: bool
) -> str:
    """Return HTML drawing a plotly figure in the color scheme of the page.

    The light drawing is the figure as made. The dark one merges plotly's dark
    template into the figure's own. Both drop the paper background, so the figure
    sits on the page's.

    Parameters
    ----------
    figure : dict
        The figure, as the plotly mime type carries it.
    element_id : str
        Id of the element the figure is drawn in, unique in the page.
    source : str
        URL of plotly.js, relative to the page (see `_write_plotly_js`).
    load : bool
        Whether to load plotly.js before the figure: true for the first figure of
        the page only.

    Returns
    -------
    str
        The HTML: the element, the figure as JSON, and the script drawing it.
    """
    # Imported here, for galleries with no plotly figure.
    from plotly.io import templates

    layout = figure.get("layout") or {}
    own = layout.get("template") or {}
    clear = {"layout": {"paper_bgcolor": "rgba(0,0,0,0)"}}
    page = {
        "data": figure.get("data") or [],
        "layouts": {
            scheme: {
                **layout,
                "template": templates.merge_templates(*parts).to_plotly_json(),
            }
            for scheme, parts in (
                ("default", (own, clear)),
                ("slate", (own, "plotly_dark", clear)),
            )
        },
        "config": {"responsive": True, **(figure.get("config") or {})},
    }
    # `<` escaped, so that no string of the figure can close the script element.
    data = json.dumps(page, separators=(",", ":")).replace("<", "\\u003c")
    script = _PLOTLY_SCRIPT % {"id": element_id, "source": source}
    # A responsive figure is as high as its element: without a height, the element
    # collapses on the first redraw. Same height as plotly's notebook renderer.
    height = layout.get("height") or (own.get("layout") or {}).get("height") or 525
    return (
        (f'<script src="{source}"></script>\n' if load else "")
        + f'<div id="{element_id}" class="gallery-plotly" '
        f'style="height: {height}px"></div>\n'
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

    In particular, xarray's notebook HTML repr includes a plain-text fallback and uses
    theme selectors that do not match Zensical's `data-md-color-scheme` attribute.
    """
    if "font-family:Menlo" in html and any(corner in html for corner in "┏┌╔╭"):
        html = html.replace("<pre ", '<pre class="gallery-rich-table" ', 1)
    if "xr-wrap" in html:
        html = re.sub(
            r"<pre class=['\"]xr-text-repr-fallback['\"]>.*?</pre>",
            "",
            html,
            flags=re.DOTALL,
        )
        html = html.replace(
            "<div class='xr-wrap' style='display:none'>", "<div class='xr-wrap'>"
        )
        html = html.replace(
            '<div class="xr-wrap" style="display:none">', '<div class="xr-wrap">'
        )
        html += (
            "\n<style>"
            ".xr-array-preview,.xr-array-preview span,.xr-preview,.xr-var-preview,.xr-var-dtype,.xr-var-dims,.xr-var-name,.xr-obj-type,.xr-obj-name{color:var(--xr-font-color0)!important;}"
            ".gallery-rich-output{overflow-x:auto;}"
            ".gallery-rich-output .xr-var-list,.gallery-rich-output .xr-dim-list,.gallery-rich-output .xr-attrs{padding-left:0!important;margin:0!important;list-style:none!important;}"
            # Zensical's `.md-typeset ul li` rule adds margin-left:1.25em to <li>
            # elements, including those inside .xr-dim-list.
            ".gallery-rich-output .xr-dim-list li{margin-left:0!important;}"
            # MkDocs Material's `.md-typeset ul:not([hidden])` has higher specificity
            # than xarray's `.xr-sections` and forces `display:flow-root`, collapsing
            # the grid. Force it back so each coordinate row stays on one line.
            ".gallery-rich-output .xr-sections{display:grid!important;}"
            # Same Material rule also clobbers `.xr-var-list` (another <ul>).
            ".gallery-rich-output .xr-var-list,.gallery-rich-output .xr-var-item{display:contents!important;}"
            ".gallery-rich-output .xr-var-name,.gallery-rich-output .xr-var-dims,.gallery-rich-output .xr-var-dtype,.gallery-rich-output .xr-var-preview{margin:0!important;}"
            # Dask's chunk SVG labels can sit near element boundaries; forcing
            # overflow visible prevents edge labels (e.g., diagonal chunk labels)
            # from being clipped in docs layout containers.
            ".gallery-rich-output .xr-array-data table,.gallery-rich-output .xr-array-data td,.gallery-rich-output .xr-array-data svg{overflow:visible!important;}"
            ".gallery-rich-output .xr-array-data svg text,.gallery-rich-output .xr-array-data svg tspan,.gallery-rich-output .xr-array-preview svg text,.gallery-rich-output .xr-array-preview svg tspan,.gallery-rich-output .xr-preview svg text,.gallery-rich-output .xr-preview svg tspan{fill:var(--xr-font-color0)!important;}"
            ".gallery-rich-output .xr-array-data svg{color:var(--xr-font-color0)!important;}"
            # Dask injects inline `stroke: rgb(0,0,0)` on the root SVG; in dark
            # mode we override stroke/text color explicitly to keep labels legible.
            "[data-md-color-scheme='slate'] .gallery-rich-output .xr-array-data svg{stroke:rgba(255,255,255,0.5)!important;}"
            "[data-md-color-scheme='slate'] .gallery-rich-output .xr-array-data svg text,[data-md-color-scheme='slate'] .gallery-rich-output .xr-array-data svg tspan{fill:rgba(255,255,255,0.92)!important;stroke:none!important;}"
            "[data-md-color-scheme='default'] .xr-wrap{"
            "--xr-font-color0: rgba(0,0,0,1);"
            "--xr-font-color2: rgba(0,0,0,0.62);"
            "--xr-font-color3: rgba(0,0,0,0.42);"
            "--xr-border-color: var(--md-default-bg-color--lightest);"
            "--xr-disabled-color: rgba(0,0,0,0.35);"
            "--xr-background-color: #fff;"
            "--xr-background-color-row-even: #f8f9fb;"
            "--xr-background-color-row-odd: #edf0f5;"
            "}"
            "[data-md-color-scheme='slate'] .xr-wrap{"
            "--xr-font-color0: rgba(255,255,255,0.95);"
            "--xr-font-color2: rgba(255,255,255,0.68);"
            "--xr-font-color3: rgba(255,255,255,0.45);"
            "--xr-border-color: #2a3347;"
            "--xr-disabled-color: rgba(255,255,255,0.28);"
            "--xr-background-color: #111720;"
            "--xr-background-color-row-even: #161d29;"
            "--xr-background-color-row-odd: #1d2533;"
            "}"
            "</style>\n"
        )
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
) -> tuple[Path, tuple[Path, Path] | None]:
    """Render an executed notebook to Markdown plus light and dark image folders.

    Parameters
    ----------
    source_notebook : nbformat.NotebookNode
        The example as read from disk; provides code, Markdown and cell tags.
    executed_notebook : nbformat.NotebookNode
        The same cells after execution. Figure outputs carry their dark rendering
        under `metadata["image/png"]["dark"]` (see `zallery.theme`); other
        PNGs are shown unchanged in both themes.
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
        first_html: str | None = None
        for output_index, output in enumerate(outputs):
            output_type = output.get("output_type")
            if output_type == "stream":
                stream_text = _clean_stream_text(str(output.get("text", "")))
                if stream_text:
                    pending_text.append(stream_text)
                continue

            if output_type in {"execute_result", "display_data"}:
                light_png = _png_data(output)
                if light_png is not None:
                    _flush_text_outputs(cell_parts, pending_text)
                    # Images that did not come through the matplotlib hook have no
                    # dark rendering: show the same picture in both themes.
                    dark_png = _dark_png_data(output) or light_png
                    light_name = f"cell_{cell_index:02d}_{output_index}_light.png"
                    dark_name = f"cell_{cell_index:02d}_{output_index}_dark.png"
                    light_path = light_image_dir / light_name
                    dark_path = dark_image_dir / dark_name
                    _write_png(light_path, light_png)
                    _write_png(dark_path, dark_png)

                    alt = f"Example output from cell {cell_index}, image {output_index}"
                    cell_parts.append(
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
                    block = _plotly_block(
                        data[_PLOTLY_MIME], element_id, plotly_js, load=load
                    )
                    cell_parts.append(_html_block(block))
                    continue
                if isinstance(data, dict) and "text/html" in data:
                    html = data["text/html"]
                    if isinstance(html, list):
                        html = "".join(html)
                    _flush_text_outputs(cell_parts, pending_text)
                    html = _normalize_html_output(str(html))
                    first_html = first_html or html
                    cell_parts.append(_html_block(html))
                    continue
                if isinstance(data, dict) and "text/plain" in data:
                    pending_text.append(str(data["text/plain"]))
                continue

            if output_type == "error":
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
            if html_thumbnail(first_html, thumb_light, thumb_dark):
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
    buttons.append(f"[Download .py]({base_name}.py){{ .md-button }}")
    buttons.append(f"[Download .ipynb]({base_name}.ipynb){{ .md-button }}")
    parts.append(" ".join(buttons) + "\n")

    markdown_path = out_dir / f"{base_name}.md"
    markdown_path.write_text("\n".join(parts), encoding="utf-8")
    return markdown_path, thumbnail
