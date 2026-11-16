"""Tests for zallery.render."""

from __future__ import annotations

import json
import re
from pathlib import Path

import nbformat
import plotly.graph_objects as go
import plotly.io as pio
import pytest
from plotly.offline import get_plotlyjs, get_plotlyjs_version

from zallery import Integration
from zallery._types import SCENE_MIME
from zallery.plotly import MIME, Plotly
from zallery.render import render_notebook
from zallery.xarray import Xarray

_PY_BADGE = (
    "[![Download .py](https://img.shields.io/badge/"
    "download-.py-3776AB?logo=python&logoColor=white)"
    "{ .skip-lightbox .gallery-download }](ex.py)"
)
_IPYNB_BADGE = (
    "[![Download .ipynb](https://img.shields.io/badge/"
    "download-.ipynb-F37626?logo=jupyter&logoColor=white)"
    "{ .skip-lightbox .gallery-download }](ex.ipynb)"
)


def _make_nb(*, thumbnail: bool = False) -> nbformat.NotebookNode:
    nb = nbformat.v4.new_notebook()
    nb.cells.append(nbformat.v4.new_markdown_cell("# Hello\n\nIntro text."))
    code = nbformat.v4.new_code_cell("print('hi')")
    code.outputs = [
        nbformat.v4.new_output(
            output_type="stream",
            name="stdout",
            text="hi\n",
        ),
    ]
    nb.cells.append(code)

    # 1x1 transparent PNG.
    png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YA"
        "AAAASUVORK5CYII="
    )
    plot_cell = nbformat.v4.new_code_cell("plt.plot([1, 2, 3])")
    if thumbnail:
        plot_cell.metadata["tags"] = ["thumbnail"]

    plot_cell.outputs = [
        nbformat.v4.new_output(
            output_type="display_data",
            data={"image/png": png_b64},
            metadata={"image/png": {"dark": png_b64}},
        ),
    ]
    nb.cells.append(plot_cell)
    return nb


def test_render_writes_markdown_with_code_and_output(tmp_path: Path) -> None:
    nb = _make_nb()
    md_path, _ = render_notebook(
        nb,
        nb,
        out_dir=tmp_path,
        base_name="ex",
        runtime_seconds=4.3,
    )

    md = md_path.read_text()
    assert md.startswith("# Hello")
    # Input code stays a bare highlighted block; output is wrapped so docs CSS can
    # wrap long lines instead of scrolling.
    assert "```python\nprint('hi')\n```" in md
    assert '<div class="gallery-output" markdown>\n\n```\nhi\n```\n\n</div>' in md
    assert "ex_output_light/cell_03_0_light.png#only-light" in md
    assert "ex_output_dark/cell_03_0_dark.png#only-dark" in md
    assert "**Total running time:** 4.3 s" in md
    # The downloads are badges, as the Binder one: the logo of the file type and
    # its extension, linked to the file next to the page.
    assert _PY_BADGE in md
    assert _IPYNB_BADGE in md
    assert "md-button" not in md


@pytest.mark.parametrize(
    ("text", "is_table"),
    [("┏━━┓\n┃hi┃\n┗━━┛", True), ("Please cite this dataset.", False)],
)
def test_rich_tables_are_marked_without_affecting_citations(
    tmp_path: Path, text: str, is_table: bool
) -> None:
    """Keep Rich tables unwrapped while citation banners can still wrap."""
    nb = _make_nb()
    nb.cells[1].outputs = [
        nbformat.v4.new_output(
            output_type="display_data",
            data={
                "text/html": f'<pre style="font-family:Menlo,monospace">{text}</pre>',
                "text/plain": text,
            },
            metadata={},
        )
    ]
    md_path, _ = render_notebook(
        nb, nb, out_dir=tmp_path, base_name="rich", runtime_seconds=0.0
    )
    markdown = md_path.read_text(encoding="utf-8")
    assert ('class="gallery-rich-table"' in markdown) is is_table
    assert text in markdown


def test_error_traceback_is_rendered_without_ansi_colors(tmp_path: Path) -> None:
    nb = _make_nb()
    nb.cells[1].outputs = [
        nbformat.v4.new_output(
            output_type="error",
            ename="ValueError",
            evalue="boom",
            traceback=[
                "\x1b[31mValueError\x1b[39m  Traceback (most recent call last)",
                "\x1b[32m----> \x1b[39m\x1b[32m1\x1b[39m \x1b[38;5;28;01mraise\x1b[39;00m",
                "\x1b[31mValueError\x1b[39m: boom",
            ],
        )
    ]
    md_path, _ = render_notebook(
        nb, nb, out_dir=tmp_path, base_name="err", runtime_seconds=0.0
    )

    markdown = md_path.read_text(encoding="utf-8")
    assert (
        "```\nValueError  Traceback (most recent call last)\n"
        "----> 1 raise\nValueError: boom\n```"
    ) in markdown


def test_consecutive_text_outputs_of_a_cell_share_one_block(tmp_path: Path) -> None:
    nb = _make_nb()
    image = nb.cells[2].outputs[0]
    nb.cells[1].outputs = [
        nbformat.v4.new_output(output_type="stream", name="stdout", text="printed\n"),
        nbformat.v4.new_output(
            output_type="execute_result",
            data={"text/plain": "42"},
            metadata={},
            execution_count=1,
        ),
        image,
        nbformat.v4.new_output(output_type="stream", name="stdout", text="after\n"),
    ]
    md_path, _ = render_notebook(
        nb, nb, out_dir=tmp_path, base_name="multi", runtime_seconds=0.0
    )

    markdown = md_path.read_text(encoding="utf-8")
    # The print and the cell's value form one block; the image splits off what
    # comes after it.
    together = markdown.index("```\nprinted\n42\n```")
    picture = markdown.index("cell_02_2_light.png#only-light")
    after = markdown.index("```\nafter\n```")
    assert together < picture < after


def test_render_writes_image_files_into_output_folder(tmp_path: Path) -> None:
    nb = _make_nb()
    render_notebook(
        nb,
        nb,
        out_dir=tmp_path,
        base_name="ex",
        runtime_seconds=1.0,
    )

    light_img = tmp_path / "ex_output_light" / "cell_03_0_light.png"
    dark_img = tmp_path / "ex_output_dark" / "cell_03_0_dark.png"
    assert light_img.is_file()
    assert light_img.stat().st_size > 0
    assert dark_img.is_file()
    assert dark_img.stat().st_size > 0


def test_render_returns_thumbnail_paths_for_tagged_output(tmp_path: Path) -> None:
    nb = _make_nb(thumbnail=True)
    _, thumbnail = render_notebook(
        nb,
        nb,
        out_dir=tmp_path,
        base_name="ex",
        runtime_seconds=1.0,
    )
    assert thumbnail == (
        tmp_path / "ex_thumb_light.png",
        tmp_path / "ex_thumb_dark.png",
    )
    assert (tmp_path / "ex_thumb_light.png").is_file()
    assert (tmp_path / "ex_thumb_dark.png").is_file()


def test_render_collapses_code_cell_with_tag(tmp_path: Path) -> None:
    """A `collapse: <title>` tag hides the code behind a titled admonition."""
    nb = nbformat.v4.new_notebook()
    nb.cells.append(nbformat.v4.new_markdown_cell("# Hello"))
    code = nbformat.v4.new_code_cell("print('hi')")
    code.metadata["tags"] = ["collapse: Setup and registration"]
    code.outputs = [
        nbformat.v4.new_output(output_type="stream", name="stdout", text="hi\n"),
    ]
    nb.cells.append(code)

    md_path, _ = render_notebook(
        nb, nb, out_dir=tmp_path, base_name="ex", runtime_seconds=1.0
    )
    md = md_path.read_text()
    # The code is wrapped in a collapsed admonition with the given title, indented as its
    # content; the output still renders (below, un-indented) so only the input is hidden.
    assert '??? example "Setup and registration"' in md
    assert "    ```python\n    print('hi')\n    ```" in md
    assert '<div class="gallery-output" markdown>\n\n```\nhi\n```' in md


def test_render_collapse_tag_without_title_uses_default(tmp_path: Path) -> None:
    nb = nbformat.v4.new_notebook()
    code = nbformat.v4.new_code_cell("x = 1")
    code.metadata["tags"] = ["collapse"]
    nb.cells.append(code)

    md_path, _ = render_notebook(
        nb, nb, out_dir=tmp_path, base_name="ex", runtime_seconds=1.0
    )
    md = md_path.read_text()
    assert '??? example "Show code"' in md
    assert "    ```python\n    x = 1\n    ```" in md


def test_render_collapse_tag_with_admonition_type(tmp_path: Path) -> None:
    """`collapse[<type>]` picks the admonition type, with or without a title."""
    nb = nbformat.v4.new_notebook()
    titled = nbformat.v4.new_code_cell("x = 1")
    titled.metadata["tags"] = ["collapse[warning]: Advanced setup"]
    nb.cells.append(titled)
    untitled = nbformat.v4.new_code_cell("y = 2")
    untitled.metadata["tags"] = ["collapse[tip]"]
    nb.cells.append(untitled)

    md_path, _ = render_notebook(
        nb, nb, out_dir=tmp_path, base_name="ex", runtime_seconds=1.0
    )
    md = md_path.read_text()
    assert '??? warning "Advanced setup"' in md
    assert '??? tip "Show code"' in md


def _print_cell(text: str, *tags: str) -> nbformat.NotebookNode:
    """Return an executed cell that printed `text`, carrying `tags`."""
    cell = nbformat.v4.new_code_cell(f"print('{text}')")
    cell.metadata["tags"] = list(tags)
    cell.outputs = [
        nbformat.v4.new_output(output_type="stream", name="stdout", text=f"{text}\n")
    ]
    return cell


def test_render_puts_consecutive_tab_cells_in_one_tab_set(tmp_path: Path) -> None:
    """Cells tagged `tab: <title>` become the tabs of one set, code and output."""
    nb = nbformat.v4.new_notebook()
    nb.cells.append(nbformat.v4.new_markdown_cell("# Hello"))
    nb.cells.append(_print_cell("a", "tab: NumPy"))
    nb.cells.append(_print_cell("b", "tab: Plain Python"))
    nb.cells.append(_print_cell("c"))

    md_path, _ = render_notebook(
        nb, nb, out_dir=tmp_path, base_name="ex", runtime_seconds=1.0
    )
    md = md_path.read_text()
    head, first, rest = md.split('<div class="tabbed-block">')
    second, after = rest.split("</div>\n</div>\n</div>\n")
    # The theme shows the block at the position of the checked input: the inputs
    # come first, then one label and one block per tab, in cell order.
    (name,) = set(re.findall(r'name="(\w+)"', head))
    assert '<div class="tabbed-set tabbed-alternate" data-tabs="' in head
    assert head.endswith(
        f'<input checked="checked" id="{name}_1" name="{name}" type="radio" />'
        f'<input id="{name}_2" name="{name}" type="radio" />'
        f'<div class="tabbed-labels"><label for="{name}_1">NumPy</label>'
        f'<label for="{name}_2">Plain Python</label></div>\n'
        '<div class="tabbed-content">\n'
    )
    assert "```python\nprint('a')\n```" in first
    assert "```\na\n```" in first
    assert "print('b')" not in first
    assert "```python\nprint('b')\n```" in second
    assert "```\nb\n```" in second
    # The untagged cell is outside the set.
    assert "```python\nprint('c')\n```" in after


def test_render_starts_a_new_tab_set_after_an_untagged_cell(tmp_path: Path) -> None:
    """Each tab set has its own input name, so the sets switch independently."""
    nb = nbformat.v4.new_notebook()
    nb.cells.append(_print_cell("a", "tab: One"))
    nb.cells.append(nbformat.v4.new_markdown_cell("Some prose."))
    nb.cells.append(_print_cell("b", "tab: Two"))

    md_path, _ = render_notebook(
        nb, nb, out_dir=tmp_path, base_name="ex", runtime_seconds=1.0
    )
    md = md_path.read_text()
    names = re.findall(r'<input checked="checked" id="\w+" name="(\w+)"', md)
    assert len(names) == 2
    assert names[0] != names[1]
    assert md.index("print('a')") < md.index("Some prose.") < md.index("print('b')")


def test_render_escapes_tab_titles(tmp_path: Path) -> None:
    nb = nbformat.v4.new_notebook()
    nb.cells.append(_print_cell("a", "tab: R&D <beta>"))

    md_path, _ = render_notebook(
        nb, nb, out_dir=tmp_path, base_name="ex", runtime_seconds=1.0
    )
    assert ">R&amp;D &lt;beta&gt;</label>" in md_path.read_text()


def test_render_ignores_collapse_on_a_tab_cell(tmp_path: Path) -> None:
    """A tab is raw HTML, where the `???` syntax of `collapse` would show as text."""
    nb = nbformat.v4.new_notebook()
    nb.cells.append(_print_cell("a", "tab: One", "collapse"))

    md_path, _ = render_notebook(
        nb, nb, out_dir=tmp_path, base_name="ex", runtime_seconds=1.0
    )
    md = md_path.read_text()
    assert "???" not in md
    assert "\n```python\nprint('a')\n```\n" in md


@pytest.mark.parametrize(
    ("tags", "opening"),
    [
        (["title: Sort the values"], '``` { .python title="Sort the values" }'),
        (["hl_lines: 2 4-5"], '``` { .python hl_lines="2 4-5" }'),
        (["title: Sort", "hl_lines: 1"], '``` { .python title="Sort" hl_lines="1" }'),
        # A title cannot escape a quote: it is delimited by the kind it does not use.
        (['title: Say "hi"'], "``` { .python title='Say \"hi\"' }"),
        (['title: Say "hi", it\'s'], "``` { .python title=\"Say 'hi', it's\" }"),
        # Not line numbers: the tag is ignored instead of breaking the fence.
        (["hl_lines: first"], "```python"),
    ],
)
def test_render_writes_title_and_hl_lines_tags_as_fence_options(
    tmp_path: Path, tags: list[str], opening: str
) -> None:
    nb = nbformat.v4.new_notebook()
    nb.cells.append(_print_cell("a", *tags))

    md_path, _ = render_notebook(
        nb, nb, out_dir=tmp_path, base_name="ex", runtime_seconds=1.0
    )
    assert f"{opening}\nprint('a')\n```\n" in md_path.read_text()


def test_render_places_annotations_between_code_and_output(tmp_path: Path) -> None:
    """The theme reads annotations from the list directly under the code block."""
    nb = nbformat.v4.new_notebook()
    nb.cells.append(_print_cell("a", "annotate"))
    nb.cells.append(nbformat.v4.new_markdown_cell("1.  A note."))
    nb.cells.append(nbformat.v4.new_markdown_cell("After."))

    md_path, _ = render_notebook(
        nb, nb, out_dir=tmp_path, base_name="ex", runtime_seconds=1.0
    )
    md = md_path.read_text()
    assert (
        "``` { .python .annotate }\nprint('a')\n```\n\n1.  A note.\n\n"
        '<div class="gallery-output" markdown>'
    ) in md
    # The list is moved, not copied, and later cells keep their place.
    assert md.count("1.  A note.") == 1
    assert md.index("gallery-output") < md.index("After.")


def test_render_keeps_annotations_with_the_code_of_a_collapsed_cell(
    tmp_path: Path,
) -> None:
    nb = nbformat.v4.new_notebook()
    nb.cells.append(_print_cell("a", "annotate", "collapse"))
    nb.cells.append(nbformat.v4.new_markdown_cell("1.  A note."))

    md_path, _ = render_notebook(
        nb, nb, out_dir=tmp_path, base_name="ex", runtime_seconds=1.0
    )
    assert (
        '??? example "Show code"\n\n'
        "    ``` { .python .annotate }\n    print('a')\n    ```\n\n"
        "    1.  A note.\n"
    ) in md_path.read_text()


def test_render_annotate_needs_no_following_markdown_cell(tmp_path: Path) -> None:
    nb = nbformat.v4.new_notebook()
    nb.cells.append(_print_cell("a", "annotate"))
    nb.cells.append(_print_cell("b", "annotate"))

    md_path, _ = render_notebook(
        nb, nb, out_dir=tmp_path, base_name="ex", runtime_seconds=1.0
    )
    md = md_path.read_text()
    assert "``` { .python .annotate }\nprint('a')\n```\n" in md
    assert "``` { .python .annotate }\nprint('b')\n```\n" in md


def test_render_ignores_annotate_on_a_tab_cell(tmp_path: Path) -> None:
    """A tab is raw HTML, where the list of annotations would show as text."""
    nb = nbformat.v4.new_notebook()
    nb.cells.append(_print_cell("a", "tab: One", "annotate"))
    nb.cells.append(nbformat.v4.new_markdown_cell("1.  A note."))

    md_path, _ = render_notebook(
        nb, nb, out_dir=tmp_path, base_name="ex", runtime_seconds=1.0
    )
    md = md_path.read_text()
    assert "\n```python\nprint('a')\n```\n" in md
    assert md.index("</div>\n</div>\n</div>\n") < md.index("1.  A note.")


_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YA"
    "AAAASUVORK5CYII="
)
"""A 1x1 transparent PNG."""


def _html_cell(*tags: str, image: bool = False) -> nbformat.NotebookNode:
    """Return an executed cell that displayed a table as HTML, and maybe a figure."""
    cell = nbformat.v4.new_code_cell("table")
    cell.metadata["tags"] = list(tags)
    cell.outputs = [
        nbformat.v4.new_output(
            output_type="execute_result",
            data={"text/html": "<table><tr><td>1</td></tr></table>", "text/plain": "1"},
        )
    ]
    if image:
        cell.outputs.append(
            nbformat.v4.new_output(output_type="display_data", data={"image/png": _PNG})
        )
    return cell


def _plotly_output(fig: go.Figure) -> nbformat.NotebookNode:
    """A plotly output as the kernel gives it: light figure, dark one in metadata."""
    # What plotly's default renderer in a kernel gives: its mime type alone.
    data = pio.renderers["plotly_mimetype"].to_mimebundle(fig.to_dict())
    metadata: dict = {}
    Plotly()._both(data, metadata)
    return nbformat.v4.new_output("display_data", data=data, metadata=metadata)


def _render_outputs(tmp_path: Path, outputs: list, *tags: str, **kwargs) -> str:
    """Render one code cell that has these outputs; return the page."""
    cell = nbformat.v4.new_code_cell("x", metadata={"tags": list(tags)})
    cell.outputs = list(outputs)
    nb = nbformat.v4.new_notebook()
    nb.cells.append(cell)
    md_path, _ = render_notebook(
        nb, nb, out_dir=tmp_path, base_name="ex", runtime_seconds=1.0, **kwargs
    )
    return md_path.read_text()


def _figure_json(markdown: str) -> dict:
    """Return the JSON the page holds for its first plotly figure."""
    found = re.search(r'<script type="application/json"[^>]*>(.*?)</script>', markdown)
    assert found is not None
    return json.loads(found.group(1))


def _html_output(light: str, dark: str | None = None) -> nbformat.NotebookNode:
    """An HTML output, with the dark variant an integration gave it if any."""
    metadata = {} if dark is None else {"text/html": {"dark": dark}}
    return nbformat.v4.new_output(
        "display_data",
        data={"text/html": light, "text/plain": "x"},
        metadata=metadata,
    )


def _render_plotly(
    tmp_path: Path,
    title: str,
    *,
    shown: int = 1,
    layout: dict[str, object] | None = None,
) -> tuple[dict, str]:
    """Render a cell that showed a plotly bar chart; return the figure and the page."""
    figure = go.Figure(
        go.Bar(x=[1, 2], y=[3, 4]), layout={"title": {"text": title}, **(layout or {})}
    )
    output = _plotly_output(figure)
    return output.data[MIME], _render_outputs(tmp_path, [output] * shown)


def test_render_draws_a_plotly_figure_in_each_color_scheme(tmp_path: Path) -> None:
    figure, md = _render_plotly(tmp_path, "Bars")

    found = re.search(r'<script type="application/json"[^>]*>(.*?)</script>', md)
    assert found is not None
    shown = json.loads(found.group(1))
    assert shown["data"] == figure["data"]
    light, dark = shown["layouts"]["default"], shown["layouts"]["slate"]
    assert light["title"] == dark["title"] == {"text": "Bars"}
    font = figure["layout"]["template"]["layout"]["font"]["color"]
    assert light["template"]["layout"]["font"]["color"] == font
    dark_font = pio.templates["plotly_dark"].layout.font.color
    assert dark["template"]["layout"]["font"]["color"] == dark_font
    for layout in (light, dark):
        assert layout["template"]["layout"]["paper_bgcolor"] == "rgba(0,0,0,0)"


def test_render_draws_a_plotly_figure_from_the_two_figures_it_is_given(
    tmp_path: Path,
) -> None:
    """The renderer merges no template: each layout is the figure of its scheme."""
    output = _plotly_output(go.Figure(go.Bar(y=[1])))
    output.metadata[MIME]["dark"]["layout"]["title"] = {"text": "only dark"}

    page = _figure_json(_render_outputs(tmp_path, [output]))

    assert page["layouts"]["slate"]["title"] == {"text": "only dark"}
    assert "title" not in page["layouts"]["default"]
    assert "dark_data" not in page


def test_render_draws_a_plotly_figure_without_dark_figure_as_it_is(
    tmp_path: Path,
) -> None:
    figure = json.loads(pio.to_json(go.Figure(go.Bar(y=[1]))))
    output = nbformat.v4.new_output("display_data", data={MIME: figure})

    page = _figure_json(_render_outputs(tmp_path, [output]))

    assert page["layouts"]["slate"] == page["layouts"]["default"] == figure["layout"]


def test_render_keeps_dark_traces_that_differ(tmp_path: Path) -> None:
    output = _plotly_output(go.Figure(go.Bar(y=[1])))
    output.metadata[MIME]["dark"]["data"][0]["marker"] = {"color": "#ffffff"}

    markdown = _render_outputs(tmp_path, [output])

    assert _figure_json(markdown)["dark_data"][0]["marker"] == {"color": "#ffffff"}
    assert "figure.dark_data" in markdown


def test_render_loads_plotly_js_once_from_a_copy_next_to_the_page(
    tmp_path: Path,
) -> None:
    """The copy comes from the plotly that made the figures, so the versions match."""
    _, md = _render_plotly(tmp_path, "Bars", shown=2)

    name = f"plotly-{get_plotlyjs_version()}.min.js"
    assert md.count(f'<script src="{name}"></script>') == 1
    assert md.count('class="gallery-plotly"') == 2
    assert (tmp_path / name).read_text(encoding="utf-8") == get_plotlyjs()


def test_render_takes_the_thumbnail_from_a_plotly_figure(tmp_path: Path) -> None:
    """The browser gets the figure with plotly.js itself: it loads nothing."""
    cell = nbformat.v4.new_code_cell("fig")
    cell.metadata["tags"] = ["thumbnail"]
    cell.outputs = [_plotly_output(go.Figure(go.Bar(x=[1, 2], y=[3, 4])))]
    thumbnailer = _Thumbnailer()

    thumbnail = _render_thumbnail(tmp_path, cell, thumbnailer)

    assert thumbnail == (
        tmp_path / "ex_thumb_light.png",
        tmp_path / "ex_thumb_dark.png",
    )
    (html,) = thumbnailer.seen
    assert f"<script>{get_plotlyjs()}</script>" in html
    assert 'class="gallery-plotly"' in html
    assert "<script src=" not in html
    assert '"displayModeBar":false' in html


def test_render_keeps_a_plotly_title_from_closing_its_script(tmp_path: Path) -> None:
    _, md = _render_plotly(tmp_path, "a </script> b")

    assert "<script" in md
    assert md.count("</script>") == md.count("<script")


@pytest.mark.parametrize(("layout", "height"), [({}, 525), ({"height": 300}, 300)])
def test_render_gives_a_plotly_figure_the_height_plotly_draws_it_at(
    tmp_path: Path, layout: dict[str, object], height: int
) -> None:
    """A figure without a height would collapse: it is sized to its element."""
    _, md = _render_plotly(tmp_path, "Bars", layout=layout)

    assert f'class="gallery-plotly" style="height: {height}px"' in md


class _Thumbnailer:
    """Stand-in for the browser: records the HTML it is given and writes two files."""

    def __init__(self, *, works: bool = True) -> None:
        self.works = works
        self.seen: list[str] = []
        self.seen_dark: list[str] = []

    def __call__(
        self, html: str, dark_html: str, light_path: Path, dark_path: Path
    ) -> bool:
        self.seen.append(html)
        self.seen_dark.append(dark_html)
        if self.works:
            light_path.write_bytes(b"light")
            dark_path.write_bytes(b"dark")
        return self.works


def _render_thumbnail(
    tmp_path: Path, cell: nbformat.NotebookNode, thumbnailer: _Thumbnailer | None
) -> tuple[Path, Path] | None:
    nb = nbformat.v4.new_notebook()
    nb.cells.append(cell)
    _, thumbnail = render_notebook(
        nb,
        nb,
        out_dir=tmp_path,
        base_name="ex",
        runtime_seconds=1.0,
        html_thumbnail=thumbnailer,
    )
    return thumbnail


def test_render_takes_the_thumbnail_from_an_html_output(tmp_path: Path) -> None:
    thumbnailer = _Thumbnailer()

    thumbnail = _render_thumbnail(tmp_path, _html_cell("thumbnail"), thumbnailer)

    assert thumbnailer.seen == ["<table><tr><td>1</td></tr></table>"]
    assert thumbnail == (
        tmp_path / "ex_thumb_light.png",
        tmp_path / "ex_thumb_dark.png",
    )
    assert thumbnail[0].read_bytes() == b"light"
    assert thumbnail[1].read_bytes() == b"dark"


def test_render_takes_html_thumbnails_only_from_tagged_cells(tmp_path: Path) -> None:
    thumbnailer = _Thumbnailer()

    assert _render_thumbnail(tmp_path, _html_cell(), thumbnailer) is None
    assert thumbnailer.seen == []


def test_render_takes_no_html_thumbnail_unless_given_the_means(tmp_path: Path) -> None:
    assert _render_thumbnail(tmp_path, _html_cell("thumbnail"), None) is None


def test_render_prefers_an_image_to_an_html_output_as_thumbnail(tmp_path: Path) -> None:
    """The HTML comes first in the cell, and the figure still wins."""
    thumbnailer = _Thumbnailer()

    thumbnail = _render_thumbnail(
        tmp_path, _html_cell("thumbnail", image=True), thumbnailer
    )

    assert thumbnailer.seen == []
    assert thumbnail is not None
    assert (
        thumbnail[0].read_bytes()
        == (tmp_path / "ex_output_light" / "cell_01_1_light.png").read_bytes()
    )


def test_render_has_no_thumbnail_when_the_html_one_fails(tmp_path: Path) -> None:
    thumbnailer = _Thumbnailer(works=False)

    assert _render_thumbnail(tmp_path, _html_cell("thumbnail"), thumbnailer) is None
    assert len(thumbnailer.seen) == 1


def test_render_handles_notebook_without_images(tmp_path: Path) -> None:
    nb = nbformat.v4.new_notebook()
    nb.cells.append(nbformat.v4.new_code_cell("x = 1"))

    _, thumbnail = render_notebook(
        nb,
        nb,
        out_dir=tmp_path,
        base_name="ex",
        runtime_seconds=0.1,
    )
    assert thumbnail is None


def test_render_adds_binder_badge_when_url_given(tmp_path: Path) -> None:
    nb = _make_nb()
    url = "https://mybinder.org/v2/gh/owner/repo/main?urlpath=lab/tree/foo/ex.py"
    md_path, _ = render_notebook(
        nb,
        nb,
        out_dir=tmp_path,
        base_name="ex",
        runtime_seconds=1.0,
        binder_url=url,
    )

    md = md_path.read_text()
    # The badge mybinder.org serves for READMEs, linked to the launch URL.
    binder = (
        "[![Launch in Binder](https://mybinder.org/badge_logo.svg)"
        f"{{ .skip-lightbox .gallery-binder }}]({url})"
    )
    assert binder in md
    # The three badges share the last line of the page, Binder first.
    assert md.rstrip().splitlines()[-1] == f"{binder} {_PY_BADGE} {_IPYNB_BADGE}"


def test_render_omits_binder_badge_when_url_missing(tmp_path: Path) -> None:
    nb = _make_nb()
    md_path, _ = render_notebook(
        nb,
        nb,
        out_dir=tmp_path,
        base_name="ex",
        runtime_seconds=1.0,
    )

    md = md_path.read_text()
    assert "Binder" not in md


def _executed_nb_with_png(
    light_b64: str, dark_b64: str | None
) -> nbformat.NotebookNode:
    nb = nbformat.v4.new_notebook()
    cell = nbformat.v4.new_code_cell("plt.plot([1])")
    metadata = {"image/png": {"dark": dark_b64}} if dark_b64 is not None else {}
    cell.outputs = [
        nbformat.v4.new_output(
            output_type="display_data",
            data={"image/png": light_b64},
            metadata=metadata,
        )
    ]
    nb.cells.append(cell)
    return nb


def test_render_writes_light_png_from_data_and_dark_png_from_metadata(
    tmp_path: Path,
) -> None:
    import base64

    light_b64 = base64.b64encode(b"light_pixel").decode()
    dark_b64 = base64.b64encode(b"dark_pixel").decode()
    source_nb = nbformat.v4.new_notebook()
    source_nb.cells.append(nbformat.v4.new_code_cell("plt.plot([1])"))

    render_notebook(
        source_nb,
        _executed_nb_with_png(light_b64, dark_b64),
        out_dir=tmp_path,
        base_name="ex",
        runtime_seconds=1.0,
    )

    assert (
        tmp_path / "ex_output_light" / "cell_01_0_light.png"
    ).read_bytes() == b"light_pixel"
    assert (
        tmp_path / "ex_output_dark" / "cell_01_0_dark.png"
    ).read_bytes() == b"dark_pixel"


def test_render_falls_back_to_light_png_when_no_dark_rendering(tmp_path: Path) -> None:
    """Images not produced by matplotlib (PIL, screenshots) show as-is in both themes."""
    import base64

    light_b64 = base64.b64encode(b"only_pixel").decode()
    source_nb = nbformat.v4.new_notebook()
    source_nb.cells.append(nbformat.v4.new_code_cell("img"))

    render_notebook(
        source_nb,
        _executed_nb_with_png(light_b64, None),
        out_dir=tmp_path,
        base_name="ex",
        runtime_seconds=1.0,
    )

    assert (
        tmp_path / "ex_output_light" / "cell_01_0_light.png"
    ).read_bytes() == b"only_pixel"
    assert (
        tmp_path / "ex_output_dark" / "cell_01_0_dark.png"
    ).read_bytes() == b"only_pixel"


def test_render_shows_a_gif_output_in_both_color_schemes(tmp_path: Path) -> None:
    """An animation has no dark rendering: one file, shown whatever the scheme."""
    import base64

    gif = b"GIF89a-frames"
    cell = nbformat.v4.new_code_cell("animation")
    cell.outputs = [
        nbformat.v4.new_output(
            output_type="display_data",
            data={"image/gif": base64.b64encode(gif).decode(), "text/plain": "<Image>"},
        )
    ]
    nb = nbformat.v4.new_notebook()
    nb.cells.append(cell)

    md_path, _ = render_notebook(
        nb, nb, out_dir=tmp_path, base_name="ex", runtime_seconds=1.0
    )

    md = md_path.read_text()
    assert '<img src="ex_cell_01_0.gif" alt=' in md
    assert "<Image>" not in md
    assert (tmp_path / "ex_cell_01_0.gif").read_bytes() == gif


def test_render_drops_vtk_falling_back_to_off_screen_rendering(tmp_path: Path) -> None:
    """Without a display, VTK warns before rendering off screen: noise, not output."""
    warning = (
        "\x1b[0m\x1b[33m2026-11-16 12:50:07.222 (   0.361s) [    74E4BF167740]"
        "vtkXOpenGLRenderWindow.:1452  WARN| bad X server connection. DISPLAY=\x1b[0m\n"
    )
    cell = nbformat.v4.new_code_cell("pl.show()")
    cell.outputs = [
        nbformat.v4.new_output(output_type="stream", name="stderr", text=warning),
        nbformat.v4.new_output(output_type="stream", name="stdout", text="kept\n"),
    ]
    nb = nbformat.v4.new_notebook()
    nb.cells.append(cell)

    md_path, _ = render_notebook(
        nb, nb, out_dir=tmp_path, base_name="ex", runtime_seconds=1.0
    )

    md = md_path.read_text()
    assert "X server" not in md
    assert "kept" in md


def test_render_embeds_an_exported_scene_in_the_viewer_of_trame(tmp_path: Path) -> None:
    """The still picture and the scene share a tab set; the picture is the thumbnail."""
    viewer = pytest.importorskip("trame_vtk.tools.vtksz2html").HTML_VIEWER_PATH
    import base64

    cell = nbformat.v4.new_code_cell("pl.show()")
    cell.metadata["tags"] = ["thumbnail"]
    cell.outputs = [
        nbformat.v4.new_output(
            output_type="display_data",
            data={
                "image/png": _PNG,
                SCENE_MIME: base64.b64encode(b"PK-scene").decode(),
            },
        )
    ]
    nb = nbformat.v4.new_notebook()
    nb.cells.append(cell)

    md_path, thumbnail = render_notebook(
        nb, nb, out_dir=tmp_path, base_name="ex", runtime_seconds=1.0
    )

    md = md_path.read_text()
    found = re.search(r'<iframe [^>]*src="([^"?]+)\?fileURL=ex_cell_01_0\.vtksz"', md)
    assert found is not None
    assert (tmp_path / found.group(1)).read_bytes() == viewer.read_bytes()
    assert (tmp_path / "ex_cell_01_0.vtksz").read_bytes() == b"PK-scene"
    # The 1x1 picture gives the frame its shape.
    assert "aspect-ratio: 1 / 1" in md
    static, interactive = md.index(">Static Scene<"), md.index(">Interactive Scene<")
    picture = md.index("ex_output_light/cell_01_0_light.png#only-light")
    assert static < interactive < picture < found.start()
    assert thumbnail == (
        tmp_path / "ex_thumb_light.png",
        tmp_path / "ex_thumb_dark.png",
    )


def test_render_shows_the_scene_of_each_color_scheme(tmp_path: Path) -> None:
    """A scene redrawn for the dark scheme comes in the metadata, as a dark PNG does."""
    pytest.importorskip("trame_vtk")
    import base64

    cell = nbformat.v4.new_code_cell("pl.show()")
    cell.outputs = [
        nbformat.v4.new_output(
            output_type="display_data",
            data={
                "image/png": _PNG,
                SCENE_MIME: base64.b64encode(b"PK-light").decode(),
            },
            metadata={SCENE_MIME: {"dark": base64.b64encode(b"PK-dark").decode()}},
        )
    ]
    nb = nbformat.v4.new_notebook()
    nb.cells.append(cell)

    md_path, _ = render_notebook(
        nb, nb, out_dir=tmp_path, base_name="ex", runtime_seconds=1.0
    )

    md = md_path.read_text()
    assert (tmp_path / "ex_cell_01_0.vtksz").read_bytes() == b"PK-light"
    assert (tmp_path / "ex_cell_01_0_dark.vtksz").read_bytes() == b"PK-dark"
    light = re.search(r'<iframe class="gallery-scene gallery-scene-light"[^>]*>', md)
    dark = re.search(r'<iframe class="gallery-scene gallery-scene-dark"[^>]*>', md)
    assert light is not None and "fileURL=ex_cell_01_0.vtksz" in light.group()
    assert dark is not None and "fileURL=ex_cell_01_0_dark.vtksz" in dark.group()
    # The rule that shows one of the two comes with the page.
    assert md.count('[data-md-color-scheme="slate"] .gallery-scene-light') == 1


def test_render_shows_an_html_output_with_a_dark_variant_in_each_scheme(
    tmp_path: Path,
) -> None:
    output = _html_output("<p>light</p>", "<p>dark</p>")

    markdown = _render_outputs(tmp_path, [output, output])

    light = '<div class="gallery-rich-output gallery-html-light"><p>light</p></div>'
    dark = '<div class="gallery-rich-output gallery-html-dark"><p>dark</p></div>'
    assert markdown.count(light) == markdown.count(dark) == 2
    # Two outputs, one style rule.
    assert markdown.count("<style>") == 1


def test_render_shows_an_html_output_with_one_look_once(tmp_path: Path) -> None:
    markdown = _render_outputs(tmp_path, [_html_output("<p>one</p>")])

    assert '<div class="gallery-rich-output"><p>one</p></div>' in markdown
    assert "gallery-html-" not in markdown


def test_render_passes_html_outputs_through_the_integrations(tmp_path: Path) -> None:
    class Shout(Integration):
        def html(self, html: str) -> str:
            return html.upper()

    output = _html_output("<p>light</p>", "<p>dark</p>")

    markdown = _render_outputs(tmp_path, [output], integrations=[Shout()])

    assert "<P>LIGHT</P>" in markdown
    assert "<P>DARK</P>" in markdown


def test_render_leaves_an_xarray_view_to_its_integration(tmp_path: Path) -> None:
    output = _html_output("<div class='xr-wrap' style='display:none'></div>")

    assert "--xr-font-color0" not in _render_outputs(tmp_path, [output])
    assert "--xr-font-color0" in _render_outputs(
        tmp_path, [output], integrations=[Xarray()]
    )


def test_render_hands_each_scheme_its_html_for_the_thumbnail(tmp_path: Path) -> None:
    thumbnailer = _Thumbnailer(works=False)
    output = _html_output("<p>light</p>", "<p>dark</p>")

    _render_outputs(tmp_path, [output], "thumbnail", html_thumbnail=thumbnailer)

    assert thumbnailer.seen == ["<p>light</p>"]
    assert thumbnailer.seen_dark == ["<p>dark</p>"]


def test_render_hands_an_html_with_one_look_twice_for_the_thumbnail(
    tmp_path: Path,
) -> None:
    thumbnailer = _Thumbnailer(works=False)

    _render_outputs(
        tmp_path, [_html_output("<p>one</p>")], "thumbnail", html_thumbnail=thumbnailer
    )

    assert thumbnailer.seen == thumbnailer.seen_dark == ["<p>one</p>"]
