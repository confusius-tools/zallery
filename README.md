[![PyPI version](https://img.shields.io/pypi/v/zallery?style=flat-square&color=d93a54&label=PyPI)](https://pypi.org/project/zallery/)
[![Python versions](https://img.shields.io/pypi/pyversions/zallery?style=flat-square&color=0099e5&logo=python&logoColor=white)](https://pypi.org/project/zallery/)
[![License](https://img.shields.io/github/license/confusius-tools/zallery?style=flat-square&color=3ad9a4)](https://github.com/confusius-tools/zallery/blob/main/LICENSE)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/confusius-tools/zallery/main?urlpath=lab/tree/docs/examples)

# Zallery

**Zallery** builds an example gallery for [Zensical](https://zensical.org)
documentation sites from plain Python scripts.

Each example is a [jupytext](https://jupytext.readthedocs.io) percent-format `.py`
file. Zallery runs it once in a Jupyter kernel, renders it as a notebook-style
Markdown page with code, outputs, and `.py`/`.ipynb` downloads, and writes an index
page with one card per example. Every figure comes out twice, for the light and
the dark color scheme, from that single run.

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
  cell that follows. Zallery writes that cell directly under the code, above the
  output, which is where Zensical reads the notes from.
- A failing cell does not abort the build: its traceback is rendered on the page.

## Light and dark figures

Every example runs once, under a light matplotlib style. Each figure is then
re-rendered for dark mode without re-executing anything: Zallery swaps the theme
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
  that read well on both backgrounds, or pair them in `cmaps` (below).
- Images not drawn by matplotlib (PIL images, screenshots) are shown unchanged in
  both themes.

These colors and colormaps are the data of a class,
`zallery.matplotlib.Matplotlib`. A pair is `(light, dark)`; a mapping is
`{light: dark}`:

| Attribute | Default | Meaning |
|---|---|---|
| `background` | `("#fefefe", "#0b0c0f")` | Figure background. |
| `axes_background` | `("#fdfdfd", "#0b0c0f")` | Axes background. |
| `foreground` | `("black", "#e2e4e9")` | Text, ticks, spines and default lines. |
| `palette` | `None` | The default color cycle of each scheme. |
| `cmaps` | `{"coolwarm": "berlin"}` | Colormaps to switch. |
| `colors` | `{}` | Other exact colors to switch. |
| `rcparams` | dpi 160, savefig dpi 200, figsize `(7, 4)` | Other `rcParams` the examples run under. |

The default colors are close to the page colors of a default Zensical site, so
that a figure sits on the page. The light backgrounds are a hair off white: pure
white stays a color of yours, which the swap keeps.

To change the look, subclass `Matplotlib` in a module of your project:

```python
# tools/gallery.py
from zallery.matplotlib import Matplotlib


class Figures(Matplotlib):
    background = ("#f8f9fb", "#090c10")
    palette = ("Dark2", "Set2")
    cmaps = {"coolwarm": "berlin", "inferno_r": "inferno"}
    colors = {"#a8323e": "#ff6b6b"}
```

and name the class in `pyproject.toml`. It takes the place of `Matplotlib`:

```toml
[tool.zallery]
integrations = ["tools.gallery:Figures"]
```

- `palette` gives each color scheme its own default colors. A palette is the name
  of a listed matplotlib colormap (`"Set2"`, `"tab10"`) or a list of colors.
  Examples run with the light palette as matplotlib's color cycle. On the dark
  page, each color of the light palette is replaced by the color at the same
  position of the dark palette, so the dark palette needs at least as many colors.
  With `None` for the light palette, the light page uses matplotlib's default
  cycle; with `None` for the dark one, both pages show the light one.
- `cmaps` pairs colormaps by name: a figure drawn with `inferno_r` shows `inferno`
  on the dark page.
- `colors` pairs other colors, such as those of a brand.
- Palette colors and `colors` are also replaced in scatter plots, filled areas and
  other collections, unlike the theme colors above. Colormapped data keeps its
  colormap.
- Only exact colors are replaced. A color derived from one (lightened, or
  desaturated as seaborn does for bars) stays as drawn. A color you set yourself
  that equals a palette color is replaced too.
- `foreground` is matched, not set: its light value must be the color matplotlib
  draws text and axes with. To change it, set the matching keys in `rcparams` too.

## Integrations

What a display library needs, and what changes on its outputs between the two
color schemes, is said by an *integration* class. Zallery ships four:

| Class | For |
|---|---|
| `zallery.matplotlib:Matplotlib` | [matplotlib figures](#light-and-dark-figures) |
| `zallery.plotly:Plotly` | [plotly figures](#plotly-figures) |
| `zallery.pyvista:PyVista` | [PyVista plots](#pyvista-plots) |
| `zallery.xarray:Xarray` | HTML views of xarray objects |

Subclass one to change it, or subclass `zallery.Integration` for a display Zallery
does not know. A class has one attribute and three methods, all optional:

- `type` is the dotted name of the class whose objects it handles, subclasses
  included, such as `"matplotlib.figure.Figure"`: the name you import the class
  with.
- `setup()` runs in the kernel, once, before the first cell of the example. It
  prepares the library for the light scheme.
- `retheme(obj, scheme)` runs in the kernel. Zallery calls it for `"light"`, then
  for `"dark"`, each time just before it takes the rendering for that scheme. The
  object arrives both times as the example left it. The method changes the object
  in place and returns a context manager that restores every change, also when the
  rendering fails. It returns `None` when it changed nothing.
- `html(html)` runs when the page is written, on each HTML output, and returns the
  HTML to write. It is for a display whose two looks are one HTML driven by CSS:
  `Xarray` writes the values of xarray's CSS variables for each scheme there (its
  `variables` attribute).

List your classes in `pyproject.toml`, as `"module:Class"` names importable from
the directory of that file. Keep the module out of the directory Zensical
publishes (`docs/`), or the site gets a copy of it:

```toml
[tool.zallery]
integrations = ["tools.gallery:Figures", "tools.gallery:Badges"]
```

- A class that subclasses one of Zallery's takes its place.
- Any other class is added.
- A color or a palette that matplotlib cannot read stops the build before it runs
  an example, with a message naming the attribute. A colormap name is checked when
  a figure uses it.
- An output is not lost for its dark look: if `retheme` fails for the dark scheme,
  the output shows with its light look in both schemes, and the error shows under
  the cell.

When data is not enough, override `retheme`. `super().retheme(...)` gives the
context manager of the stock class, or `None`:

```python
from matplotlib.lines import Line2D
from zallery.matplotlib import Matplotlib


class Figures(Matplotlib):
    def retheme(self, fig, scheme):
        """Draw lines thicker on the dark page."""
        restore = super().retheme(fig, scheme)
        if scheme == "dark" and restore is not None:
            for line in fig.findobj(Line2D):
                restore.callback(line.set_linewidth, line.get_linewidth())
                line.set_linewidth(1.5 * line.get_linewidth())
        return restore
```

`zallery.matplotlib.swap_colors` and `zallery.matplotlib.swap_cmaps` take the
figure's artists and a mapping, and each returns such a context manager; combine
several with `contextlib.ExitStack`.

For a display Zallery does not know, a class with `type` and `retheme` is enough:

```python
from contextlib import ExitStack

from zallery import Integration


class Badges(Integration):
    type = "mylib.Badge"

    def retheme(self, badge, scheme):
        if scheme == "light":
            return None
        restore = ExitStack()
        restore.callback(setattr, badge, "color", badge.color)
        badge.color = "white"
        return restore
```

- Zallery shows each object of that class as a notebook does (its `_repr_html_`,
  `_repr_png_` and so on), once for each scheme. The page keeps both and shows the
  one of the reader's color scheme.
- A dark variant is kept for PNG and HTML outputs.
- An HTML output with a dark variant is on the page twice, one of them hidden by a
  style rule. This fits static HTML. An output whose HTML runs scripts runs them
  twice.
- The gallery of this repository has
  [such a class](https://github.com/confusius-tools/zallery/blob/main/tools/gallery.py).

## Plotly figures

A plotly figure that a cell shows, as its last expression or with `fig.show()`, is
drawn on the page as in a notebook: zoom, pan and hover work. The example needs no
renderer setup.

- The light page shows the figure as made. The dark page draws it again with
  plotly's `plotly_dark` template merged into the figure's own. Both drop the
  paper background, so the figure sits on the page. Colors set on the figure
  itself, not by its template, are the same in both schemes.
- The templates are the `template` attribute of `zallery.plotly.Plotly`,
  `(None, "plotly_dark")`: the name of a plotly template for each scheme, or `None`
  to merge none. Subclass it to change them (see [Integrations](#integrations)).
- Zallery copies plotly.js from the plotly package that made the figure next to
  the page, so the site loads nothing from plotly's servers. The file weighs about
  5 MB; there is one per section that has plotly figures.
- With [HTML thumbnails](#html-thumbnails) switched on, the plotly figure of a
  `thumbnail` cell is its example's thumbnail, drawn to fill the card in each color
  scheme.

## PyVista plots

A PyVista plotter that a cell shows with `show()` gives its picture under the cell,
as in a notebook. The example needs no setup: Zallery runs PyVista in its gallery
mode, set with environment variables before the example imports it
(`PYVISTA_OFF_SCREEN`, `PYVISTA_BUILDING_GALLERY`, `PYVISTA_AUTO_CLOSE`, and
`PYVISTA_JUPYTER_BACKEND` set to `none`). A variable you set yourself keeps your
value. A plotter is closed after the cell that shows it.

- The picture is taken twice, like a matplotlib figure: as the example draws it,
  under PyVista's default theme, and again with the colors of PyVista's dark theme
  for the dark page. The colors that differ between the two themes are swapped: the
  background, and the black of texts, edges, outlines and axes, which becomes
  white. A color you set yourself to one of those is swapped too; other colors and
  colormaps stay. A plot you draw under another theme stays as it is.
- The two themes are the `themes` attribute of `zallery.pyvista.PyVista`,
  `("DocumentTheme", "DarkTheme")`: names of classes of `pyvista.themes`. The
  environment variables are its `environment` attribute. Subclass it to change them
  (see [Integrations](#integrations)).
- A plotter that records a GIF, with `open_gif` and `write_frame`, shows the
  animation instead of its last picture. Recording needs the `imageio` package. The
  animation is the same in both color schemes: its frames are recorded as the
  example runs.
- With the `trame-pyvista` package installed, the picture shares a set of tabs with
  an interactive scene, as in the PyVista documentation: "Static Scene" and
  "Interactive Scene". PyVista exports the scene and the browser draws it: the site
  needs no server. Each color scheme has its scene, which loads when the reader
  opens the tab. Zallery writes the scenes as `.vtksz` files, which hold the data
  of the plot, and copies the viewer of trame next to the page (about 1 MB, once
  per section).
- A GIF is not taken as the thumbnail: tag a cell that shows a still picture.
- On a machine without a display, VTK draws off screen through EGL or OSMesa: the
  machine needs one of them (a GPU driver or Mesa).

## HTML thumbnails

An example without a figure can show an HTML output, such as a DataFrame or an
xarray view, on its index card. Switch the option on in `pyproject.toml`:

```toml
[tool.zallery]
html_thumbnails = true
html_thumbnail_css = ["docs/stylesheets/extra.css"]
```

A `thumbnail` cell that shows no image then gives its first HTML output, or plotly
figure, as the thumbnail. Zallery pictures the top-left corner of the output
with a headless browser, once for each color scheme.

- The machine that builds the gallery needs a Chromium-family browser. Zallery
  uses the one named by the `ZALLERY_BROWSER` environment variable (a command or
  a path). Without that variable, it takes the first of `chromium`,
  `chromium-browser`, `google-chrome`, `google-chrome-stable`, `chrome`,
  `microsoft-edge` and `msedge` on the `PATH`, then the headless shell that
  `uvx playwright install chromium-headless-shell` downloads.
- Without a browser, the build prints a warning and goes on: the examples keep the
  default thumbnail.
- `html_thumbnail_css` lists stylesheets of your site, so that the output looks as
  it does on its page. The theme's own stylesheet is not part of the picture;
  Zallery sets the `data-md-color-scheme` attribute and the
  `--md-default-bg-color` and `--md-default-fg-color` variables that site styles
  usually build on.
- The page of the picture has the colors of a default Zensical page. A site with
  its own page colors sets `--md-default-bg-color` and `--md-default-fg-color` for
  each scheme in one of those stylesheets, as it does for its pages.
- An output with a dark variant (see [Integrations](#integrations)) gives each
  picture its own HTML.
- The picture runs the output's own scripts but loads nothing from the network: an
  output whose scripts need a file from the network comes out empty.

## Configuration

Zallery reads the `[tool.zallery]` table of the nearest `pyproject.toml` above the
working directory; relative paths resolve against that file's directory. All keys
are optional:

| Key | Default | Meaning |
|---|---|---|
| `examples` | `docs/examples` | Directory of example sections. |
| `built` | `<examples>/_built` | Where rendered pages and images go. |
| `cache` | `.gallery-cache` | Execution/render cache. |
| `binder_repo` | unset | `owner/repo` for the Binder launch badges. |
| `integrations` | `[]` | Integration classes of the project, as `"module:Class"` names: see [Integrations](#integrations). |
| `fingerprint` | `["uv.lock"]` | Files whose change invalidates the cache. |
| `html_thumbnails` | `false` | Whether an HTML output may be an example's thumbnail: see [HTML thumbnails](#html-thumbnails). |
| `html_thumbnail_css` | `[]` | Stylesheets of the site applied to HTML thumbnails. |

With `binder_repo` set, each example page gets a Binder badge that opens its script
on [mybinder.org](https://mybinder.org) as a notebook. The git ref stamped into
Binder URLs comes from the `ZALLERY_BINDER_REF` environment variable (default
`main`). The repository has to provide the Binder environment: one that installs
the project and makes Jupyter open percent-format scripts as notebooks. This
repository's
[`binder/Dockerfile`](https://github.com/confusius-tools/zallery/blob/main/binder/Dockerfile)
is a working setup.

A cached example is reused while its source, the Python version, the configuration,
the `fingerprint` files, the modules of the integration classes of the project,
and the Zallery sources are all unchanged.

## Zensical integration

Zallery writes Markdown pages; the Zensical site provides the rest, in
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
- Optionally, thumbnails for examples in which a cell raised an error, at
  `<examples>/_assets/error_thumb.svg` and `<examples>/_assets/error_thumb_dark.svg`.
  With both files there, the card of such an example shows them in place of the
  example's own thumbnail, so that a broken example stands out on the index page.
- Optionally, styles for the classes Zallery emits: `examples-cards` and
  `examples-card-summary` on the index page, `gallery-output` and
  `gallery-rich-output` around cell outputs, with `gallery-html-light` or
  `gallery-html-dark` on an HTML output that has a variant for each scheme,
  `gallery-plotly` on plotly figures, `gallery-scene` on PyVista scenes,
  `gallery-binder` on the Binder
  badge. This repository's
  [`zensical.toml`](https://github.com/confusius-tools/zallery/blob/main/zensical.toml)
  and
  [stylesheet](https://github.com/confusius-tools/zallery/blob/main/docs/stylesheets/extra.css)
  are a working setup, with notebook-like pandas tables; the
  [ConfUSIus stylesheet](https://github.com/confusius-tools/confusius/blob/main/docs/stylesheets/extra.css)
  also styles scikit-learn outputs. xarray views need no site styles: Zallery
  adapts them to the color scheme itself.

## Relationship to ConfUSIus

Zallery is extracted from [ConfUSIus](https://github.com/confusius-tools/confusius),
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
