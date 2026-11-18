# Writing examples

The gallery root lives in the
[`tool.zallery:gallery_root`](configuration/#default-configuration) path specified in the
`pyproject.toml`. Examples as `<gallery_root>/<section>/<name>.py`.


```toml title="pyproject.toml"
...
--8<-- "src/zallery/config.toml:5:8"
...
```

## Gallery index page

The [index page](../examples/) of the gallery is generated from the examples' titles,
first paragraphs and thumbnails. A leading numeric prefix (`01_io/`, `02_first.py`)
orders sections and examples and is stripped from the built names.

!!! warning "Files and folders starting with `_` are skipped"

## Section content

A section folder may contain a `_section.md`. Its first heading is the title of the
section, and the text after the heading is the introduction of the section.

```markdown title="Snippet from section: <a href='../examples/_built/matplotlib/index.md'>Matplotlib figures</a>" title_mode="html" linenums="1"
--8<-- "docs/examples/01_matplotlib/_section.md"
```

The title and the introduction show on the [gallery index page](#gallery-index-page) of
the gallery and on the [page of the section](#section-pages). Front matter is optional
and goes to the page of the section only.

## Section pages

Zallery also writes one page for each section, `_built/<section>/index.md`, next to the
pages of its examples. The page holds the content of `_section.md`, then the cards of
the examples of the section.

To use the page in the navigation of the site, list it first in its section:

```toml title="zensical.toml"
nav = [
    { "Matplotlib figures" = [
        "examples/_built/matplotlib/index.md",
        { "A first plot" = "examples/_built/matplotlib/first_plot.md" },
    ]},
]
```

With the `navigation.indexes` feature of the theme, these rules apply:

- The name of the section in the navigation opens the page of the section.
- If the front matter of `_section.md` has an `icon`, such as `icon: lucide/chart-spline`,
  the section shows this icon in the navigation.

An example cannot have the name `index.py`, because its page would be the page of the
section.

## Example title

The first Markdown heading of an example is its page title; the next Markdown paragraph
is the summary shown on its index card.


```python title="Snippet from example: <a href='../examples/_built/matplotlib/first_plot.md'>A first plot</a>" title_mode="html" linenums="1"
--8<-- "docs/examples/01_matplotlib/01_first_plot.py::4"
```

## Cell tags

### Thumbnails

Tag a cell with `thumbnail` to use its first image output on the index card. With [HTML
thumbnails](html-thumbnails.md) switched on, a cell without an image gives its first
HTML output.

```python title="Snippet from example: <a href='../examples/_built/matplotlib/first_plot.md'>A first plot</a>" title_mode="html" linenums="9"
--8<-- "docs/examples/01_matplotlib/01_first_plot.py:9:11"
```

### Code in an admonition

Tag a cell with `admonition` to show its code in an
[admonition](https://zensical.org/docs/authoring/admonitions/). The cell still runs, and
its output shows under the admonition.

```python title="Snippet from example: <a href='../examples/_built/zensical/write_admonition.md'>Writing an admonition</a>" title_mode="html" linenums="38"
--8<-- "docs/examples/03_zensical/01_write_admonition.py:38:40"
```

Tag a cell with `collapse` to get a collapsed admonition. It hides the code until the
reader opens it.

The two tags take an admonition type in brackets and a title after a colon. The type and
the title are optional:

| Tag | Admonition |
|---|---|
| `admonition` | Type `example`, with the title "Example". |
| `collapse` | Type `example`, collapsed, with the title "Show code". |
| `admonition: <title>`, `collapse: <title>` | Your title. |
| `admonition[<type>]`, `collapse[<type>]` | A different type, such as `warning` or `tip`. |
| `admonition[<type>]: <title>`, `collapse[<type>]: <title>` | A different type and your title. |

```python title="Snippet from example: <a href='../examples/_built/zensical/write_admonition.md'>Writing an admonition</a>" title_mode="html" linenums="82"
--8<-- "docs/examples/03_zensical/01_write_admonition.py:82:84"
```

### Output in the admonition

Add the `include-output` tag to put the output of the cell in the admonition too, under
the code. The tag has an effect only together with `admonition` or `collapse`.

```python title="Snippet from example: <a href='../examples/_built/zensical/write_admonition.md'>Writing an admonition</a>" title_mode="html" linenums="118"
--8<-- "docs/examples/03_zensical/01_write_admonition.py:118:123"
```

The tag `annotate` is ignored on a cell that has `include-output`.

### Tabbed code

Tag consecutive code cells with `tab: <title>` to show them as tabs, each with its code
and its output. An untagged cell, code or Markdown, ends the set of tabs. Every tab
runs, in order and in the same kernel. The tags `admonition`, `collapse` and `annotate`
are ignored on a tab cell.

```python title="Snippet from example: <a href='../examples/_built/zensical/tab_cells/#__zallery_tab_3_1'>Cells in tabs</a>" title_mode="html" linenums="37"
--8<-- "docs/examples/03_zensical/02_tab_cells.py:37:45"
```

### Title, highlighted lines and annotated code

Adding title, line highlighting and annotation is also possible using notation similar
to Zensical. [`"title: <text>"`](https://zensical.org/docs/authoring/code-blocks/#add-a-title) " instead of `title="<text>"`, and [`"hl_lines: <lines>"`](https://zensical.org/docs/authoring/code-blocks/#highlight-specific-lines) instead of `hl_lines="<lines>"`.

```python title="Snippet from example: <a href='../examples/_built/zensical/highlight_lines.md'>Highlighted lines and a title</a>" title_mode="html" linenums="21"
--8<-- "docs/examples/03_zensical/03_highlight_lines.py:21:24"
```

For code annotations, tag a code cell with `annotate`. Adding the annotation to the code
block follows the same pattern [as in Zensical](https://zensical.org/docs/authoring/code-blocks/#add-annotations):


```python title="Snippet from example: <a href='../examples/_built/zensical/annotations.md'>Code annotations</a>" title_mode="html" linenums="23"
--8<-- "docs/examples/03_zensical/04_annotations.py:23:30"
```

## Error handling

A cell that raises does not stop the build. Its traceback is rendered on the page, as a
notebook shows it, and the cells after it still run.

On the [index page](../examples/), the card of such an example shows the error thumbnail
of the site in place of its own, so that a broken example stands out:

<div class="grid cards examples-cards" markdown>

-   [<img src="../examples/_assets/error_thumb.svg#only-light" alt="Example that raised an error"><img src="../examples/_assets/error_thumb_dark.svg#only-dark" alt="Example that raised an error">](../examples/_built/errors/raise_error.md)

    ---

    **[An example that raises](../examples/_built/errors/raise_error.md)**

</div>

The two pictures are files of the site, `error_thumb.svg` and `error_thumb_dark.svg` in
`<gallery_root>/_assets/`: see [Zensical integration](zensical-integration.md). Without them,
the example keeps its own thumbnail.

To make a broken example fail the build, run `zallery --abort-on-error`. The build then
stops at the first cell that raises, prints its traceback and exits with status 1: see
[Command line](../index.md#command-line).

A cell that raises on purpose gets the `raises-exception` tag. Such a cell does not stop
the build, also with `--abort-on-error`:

```python title="Snippet from example: <a href='../examples/_built/errors/raise_error.md'>An example that raises</a>" title_mode="html" linenums="26"
--8<-- "docs/examples/02_errors/01_raise_error.py:26:27"
```
