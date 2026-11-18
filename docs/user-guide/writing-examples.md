# Writing examples

Examples live under the [`config.toml:examples`](configuration/#default-configuration)
path as `<config:examples>/<section>/<name>.py`.

## Example title

The first Markdown heading of an example is its page title; the next Markdown paragraph
is the summary shown on its index card.


```python title="Snippet from example: <a href='../examples/_built/matplotlib/first_plot.md'>A first plot</a>" title_mode="html" linenums="1"
--8<-- "docs/examples/01_matplotlib/01_first_plot.py::4"
```

## Section content

A section folder may contain a `_section.md` whose first heading becomes the section
title on the index page.

```python title="Snippet from example: <a href='../examples/_built/matplotlib'>A first plot</a>" title_mode="html" linenums="1"
--8<-- "docs/examples/01_matplotlib/_section.md::3"


```

## Example index

The [index page](../examples/) of the gallery is generated from the examples' titles,
first paragraphs and thumbnails. A leading numeric prefix (`01_io/`, `02_first.py`)
orders sections and examples and is stripped from the built names.

- Files and folders starting with `_` are skipped.


## Cell tags

### Thumbnails

Tag a cell with `thumbnail` to use its first image output on the index card. With [HTML
thumbnails](html-thumbnails.md) switched on, a cell without an image gives its first
HTML output.

```python title="Snippet from example: <a href='../examples/_built/matplotlib/first_plot.md'>A first plot</a>" title_mode="html" linenums="9"
--8<-- "docs/examples/01_matplotlib/01_first_plot.py:9:11"
```

### Collapsed code

Tag a cell with `collapse` (or `collapse: <title>`) to hide its code behind a collapsed
callout. The cell still runs, and its output renders normally below the callout. The
callout defaults to the `example` admonition; pick another type with `collapse[<type>]`
or `collapse[<type>]: <title>`. See
[Zensical admonitions](https://zensical.org/docs/authoring/admonitions/) for further details.

```python title="Snippet from example: <a href='../examples/_built/zensical/write_admonition.md'>Write an admonition</a>" title_mode="html" linenums="61"
--8<-- "docs/examples/03_zensical/01_write_admonition.py:61:64"

```

### Tabbed code

Tag consecutive code cells with `tab: <title>` to show them as tabs, each with its code
and its output. An untagged cell, code or Markdown, ends the set of tabs. Every tab
runs, in order and in the same kernel. Tags `collapse` and `annotate` are ignored on
a tab cell.

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
`<examples>/_assets/`: see [Zensical integration](zensical-integration.md). Without them,
the example keeps its own thumbnail.

To make a broken example fail the build, run `zallery --abort-on-error`. The build then
stops at the first cell that raises, prints its traceback and exits with status 1: see
[Command line](../index.md#command-line).

A cell that raises on purpose gets the `raises-exception` tag. Such a cell does not stop
the build, also with `--abort-on-error`:

```python title="Snippet from example: <a href='../examples/_built/errors/raise_error.md'>An example that raises</a>" title_mode="html" linenums="26"
--8<-- "docs/examples/02_errors/01_raise_error.py:26:27"
```
