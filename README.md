[![PyPI version](https://img.shields.io/pypi/v/zallery?style=flat-square&color=d93a54&label=PyPI)](https://pypi.org/project/zallery/)
[![Python versions](https://img.shields.io/pypi/pyversions/zallery?style=flat-square&color=0099e5&logo=python&logoColor=white)](https://pypi.org/project/zallery/)
[![License](https://img.shields.io/github/license/confusius-tools/zallery?style=flat-square&color=3ad9a4)](https://github.com/confusius-tools/zallery/blob/main/LICENSE)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/confusius-tools/zallery/main?urlpath=lab/tree/docs/examples)

# zallery

**zallery** builds an example gallery for [Zensical](https://zensical.org)
documentation sites from plain Python scripts.

Each example is a [jupytext](https://jupytext.readthedocs.io) percent-format `.py`
file. zallery runs it once in a Jupyter kernel, renders it as a notebook-style
Markdown page with code, outputs, and `.py`/`.ipynb` downloads, and writes an index
page with one card per example. Every matplotlib figure comes out twice, for the
light and the dark color scheme, from that single run.

## Installation

```bash
uv add --dev zallery
```

Or with pip:

```bash
pip install zallery
```

## Quick start

Add a `[tool.zallery]` table to the project's `pyproject.toml` (an empty table is
enough, every key has a default):

```toml
[tool.zallery]
examples = "docs/examples"
```

Create a section with one example:

```bash
mkdir -p docs/examples/my-section
printf '# My section\n\nIntro.\n' > docs/examples/my-section/_section.md
cat > docs/examples/my-section/hello.py <<'EOF'
# %% [markdown]
# # My example
#
# Short description.

# %%
print("hi")
EOF
```

Build the gallery from anywhere inside the project:

```bash
uv run zallery
```

This writes `docs/examples/index.md` (the card index) and
`docs/examples/_built/my-section/hello.md` with its images and downloads. Add them
to the site navigation like any other page; both are generated, so keep them and
the cache directory out of version control.

## Command line

```
zallery [--no-run] [--no-cache] [EXAMPLE ...]
```

- With no arguments, every example is executed, or restored from cache when its
  source and the cache fingerprint are unchanged.
- Name example scripts to run only those. The whole gallery is still rendered: the
  others are restored from cache if present, or rendered with code and Markdown only.
- `--no-run` executes nothing, to iterate on prose or layout.
- `--no-cache` executes the selected examples even when a cached result exists; the
  result replaces the cache entry.

`python -m zallery` is equivalent.

## Writing examples

Examples live under `<examples>/<section>/<name>.py`.

- The first Markdown heading of an example is its page title; the next Markdown
  paragraph is the summary shown on its index card.
- A section folder may contain a `_section.md` whose first heading becomes the section
  title on the index page.
- An `_index.md` in the examples root replaces the default header of the index page.
- A leading numeric prefix (`01_io/`, `02_first.py`) orders sections and examples and
  is stripped from the built names.
- Files and folders starting with `_` are skipped.
- Tag a cell with `thumbnail` to use its first image output on the index card. With
  [HTML thumbnails](#html-thumbnails) switched on, a cell without an image gives its
  first HTML output.
- Tag a cell with `collapse` (or `collapse: <title>`) to hide its code behind a
  collapsed callout, handy for setup the reader can expand on demand. The cell still
  runs, and its output renders normally below the callout. The callout defaults to the
  `example` admonition; pick another type with `collapse[<type>]` or
  `collapse[<type>]: <title>`, where `<type>` is any
  [admonition](https://zensical.org/docs/authoring/admonitions/) name Zensical
  understands (`warning`, `tip`, `note`, ...).
- Tag consecutive code cells with `tab: <title>` to show them as tabs, each with its
  code and its output. An untagged cell, code or Markdown, ends the set of tabs.
  Every tab runs, in order and in the same kernel. The `collapse` and `annotate`
  tags are ignored on a tab cell.
- Tag a code cell with `title: <text>` to show a title above its code, and with
  `hl_lines: <lines>` to highlight lines: numbers and ranges separated by spaces,
  such as `hl_lines: 2 4-5`. Line 1 is the first line of the cell.
- Tag a code cell with `annotate` to attach notes to its lines. End a line with a
  comment such as `# (1)!`, and write the notes as a numbered list in the Markdown
  cell that follows. zallery writes that cell directly under the code, above the
  output, which is where Zensical reads the notes from.
- A failing cell does not abort the build: its traceback is rendered on the page.

## Light and dark figures

Every example runs once, under a light matplotlib style. Each figure is then
re-rendered for dark mode without re-executing anything: zallery swaps the theme
colors (figure background, axes background, black foreground) and the default
diverging colormap (`coolwarm` to `berlin`) on the drawn artists, prints a second
PNG, and restores the exact properties it changed. Both PNGs land on the page, and
the site shows the one matching the reader's color scheme.

What this means when writing an example:

- Read backgrounds from matplotlib rather than hardcoding them, for example
  `mpl.rcParams["figure.facecolor"]`. Figures created with `plt.subplots` or
  `plt.figure` already get this background. Pure black is a theme color wherever
  it appears (text, lines, line markers, and backgrounds). Per-element colors
  (`scatter(c="black")`, collections) are left alone. Pure white and any other
  explicit color are kept as is.
- A figure whose background is pure black is taken as drawn for a dark page: its
  black is swapped as background and its white as text for both pages, pure-white
  data colors included. This cannot work at a finer grain, since one figure can
  hold both a plot on black with white text and a regular plot.
- Do not branch on the theme in the example: there is only one run. Pick colormaps
  that read well on both backgrounds, or swap them with a hook (below).
- Images not drawn by matplotlib (PIL images, screenshots) are shown unchanged in
  both themes.

To give each color scheme its own default colors, set a palette for each one in
`pyproject.toml`:

```toml
[tool.zallery.light]
matplotlib.palette = "Dark2"

[tool.zallery.dark]
matplotlib.palette = "Set2"
```

A palette is the name of a listed matplotlib colormap (`"Set2"`, `"tab10"`) or a
list of colors. Examples run with the light palette as matplotlib's color cycle. On
the dark page, each color of the light palette is replaced by the color at the same
position of the dark palette, so the dark palette needs at least as many colors.

- Without a light palette, the light page uses matplotlib's default cycle. Without
  a dark palette, both pages show the light one.
- Palette colors are also replaced in scatter plots, filled areas and other
  collections, unlike the theme colors above. Colormapped data keeps its colormap.
- Only exact palette colors are replaced. A color derived from one (lightened, or
  desaturated as seaborn does for bars) stays as drawn. A color you set yourself
  that equals a palette color is replaced too.

When the built-in swap is not enough, point the `hook` key at a module of the
project that defines `gallery_retheme(fig, theme)`. It runs in the kernel after a
theme swap and returns a context manager that restores what it changed, also when
printing fails. It is called with `"dark"` before the dark rendering, and with
`"light"` when a figure drawn on black is first converted to light. There is no
call to undo: the returned context manager does that.

```python
from zallery.theme import swap_cmaps

SWAPS = {"inferno_r": "inferno"}


def gallery_retheme(fig, theme):
    """Draw with `inferno_r` on the light page, `inferno` on the dark page."""
    mapping = SWAPS if theme == "dark" else {dark: light for light, dark in SWAPS.items()}
    return swap_cmaps(fig.findobj(), mapping)
```

`zallery.theme.swap_cmaps` and `zallery.theme.swap_colors` take the figure's
artists and a mapping, and each returns such a context manager; combine several
with `contextlib.ExitStack`.

## Plotly figures

A plotly figure that a cell shows, as its last expression or with `fig.show()`, is
drawn on the page as in a notebook: zoom, pan and hover work. The example needs no
renderer setup.

- The light page shows the figure as made. The dark page draws it again with
  plotly's `plotly_dark` template merged into the figure's own. Both drop the
  paper background, so the figure sits on the page. Colors set on the figure
  itself, not by its template, are the same in both schemes.
- zallery copies plotly.js from the plotly package that made the figure next to
  the page, so the site loads nothing from plotly's servers. The file weighs about
  5 MB; there is one per section that has plotly figures.
- With [HTML thumbnails](#html-thumbnails) switched on, the plotly figure of a
  `thumbnail` cell is its example's thumbnail, drawn to fill the card in each color
  scheme.

## HTML thumbnails

An example without a figure can show an HTML output, such as a DataFrame or an
xarray view, on its index card. Switch the option on in `pyproject.toml`:

```toml
[tool.zallery]
html_thumbnails = true
html_thumbnail_css = ["docs/stylesheets/extra.css"]
```

A `thumbnail` cell that shows no image then gives its first HTML output, or plotly
figure, as the thumbnail. zallery pictures the top-left corner of the output with a headless
browser, once for each color scheme.

- The machine that builds the gallery needs a Chromium-family browser. zallery
  uses the one named by the `ZALLERY_BROWSER` environment variable (a command or
  a path). Without that variable, it takes the first of `chromium`,
  `chromium-browser`, `google-chrome`, `google-chrome-stable`, `chrome`,
  `microsoft-edge` and `msedge` on the `PATH`, then the headless shell that
  `uvx playwright install chromium-headless-shell` downloads.
- Without a browser, the build prints a warning and goes on: the examples keep the
  default thumbnail.
- `html_thumbnail_css` lists stylesheets of your site, so that the output looks as
  it does on its page. The theme's own stylesheet is not part of the picture;
  zallery sets the `data-md-color-scheme` attribute and the
  `--md-default-fg-color` variables that site styles usually build on.
- The picture runs the output's own scripts but loads nothing from the network: an
  output whose scripts need a file from the network comes out empty.

## Configuration

zallery reads the `[tool.zallery]` table of the nearest `pyproject.toml` above the
working directory; relative paths resolve against that file's directory. All keys
are optional:

| Key | Default | Meaning |
|---|---|---|
| `examples` | `docs/examples` | Directory of example sections. |
| `built` | `<examples>/_built` | Where rendered pages and images go. |
| `cache` | `.gallery-cache` | Execution/render cache. |
| `binder_repo` | unset | `owner/repo` for the Binder launch badges. |
| `hook` | unset | Dotted name of a module, importable from the project root, defining `gallery_retheme(fig, theme)`. |
| `fingerprint` | `["uv.lock"]` | Files whose change invalidates the cache. |
| `html_thumbnails` | `false` | Whether an HTML output may be an example's thumbnail: see [HTML thumbnails](#html-thumbnails). |
| `html_thumbnail_css` | `[]` | Stylesheets of the site applied to HTML thumbnails. |
| `light`, `dark` | none | Tables of presets for each color scheme. Their key so far is `matplotlib.palette`: see [Light and dark figures](#light-and-dark-figures). |

With `binder_repo` set, each example page gets a Binder badge that opens its script
on [mybinder.org](https://mybinder.org) as a notebook. The git ref stamped into
Binder URLs comes from the `ZALLERY_BINDER_REF` environment variable (default
`main`). The repository has to provide the Binder environment: one that installs
the project and makes Jupyter open percent-format scripts as notebooks. This
repository's
[`binder/Dockerfile`](https://github.com/confusius-tools/zallery/blob/main/binder/Dockerfile)
is a working setup.

A cached example is reused while its source, the Python version, the configuration,
the `fingerprint` files, the hook module, and the zallery sources are all unchanged.

## Zensical integration

zallery writes Markdown pages; the Zensical site provides the rest, in
`zensical.toml` and a stylesheet:

- Markdown extensions `attr_list`, `md_in_html`, `admonition`, `pymdownx.details`
  and `pymdownx.superfences`.
- `nav` entries for the index page and the built pages.
- Two CSS rules so each image shows in its own color scheme:

  ```css
  [data-md-color-scheme="slate"] img[src$="#only-light"] { display: none; }
  [data-md-color-scheme="default"] img[src$="#only-dark"] { display: none; }
  ```

- Fallback thumbnails for examples without a `thumbnail` cell, at
  `<examples>/_assets/default_thumb.svg` and `<examples>/_assets/default_thumb_dark.svg`.
- Optionally, styles for the classes zallery emits: `examples-cards` and
  `examples-card-summary` on the index page, `gallery-output` and
  `gallery-rich-output` around cell outputs, `gallery-plotly` on plotly figures,
  `gallery-binder` on the Binder
  badge. This repository's
  [`zensical.toml`](https://github.com/confusius-tools/zallery/blob/main/zensical.toml)
  and
  [stylesheet](https://github.com/confusius-tools/zallery/blob/main/docs/stylesheets/extra.css)
  are a working setup, with notebook-like pandas tables; the
  [ConfUSIus stylesheet](https://github.com/confusius-tools/confusius/blob/main/docs/stylesheets/extra.css)
  also styles scikit-learn outputs. xarray views need no site styles: zallery
  adapts them to the color scheme itself.

## Relationship to ConfUSIus

zallery is extracted from [ConfUSIus](https://github.com/confusius-tools/confusius),
where it builds the documentation's example gallery. It does not depend on
ConfUSIus and makes no assumption about what the examples compute.

## Development

```bash
uv sync            # install dependencies
just test          # run tests
just pre-commit    # run lint, format, type checks, docstring checks
just serve-docs    # build the example gallery in docs/examples and serve the docs
```

## License

BSD-3-Clause. See `LICENSE`.
