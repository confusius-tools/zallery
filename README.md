[![PyPI version](https://img.shields.io/pypi/v/zallery?style=flat-square&color=d93a54&label=PyPI)](https://pypi.org/project/zallery/)
[![Python versions](https://img.shields.io/pypi/pyversions/zallery?style=flat-square&color=0099e5&logo=python&logoColor=white)](https://pypi.org/project/zallery/)
[![License](https://img.shields.io/github/license/confusius-tools/zallery?style=flat-square&color=3ad9a4)](https://github.com/confusius-tools/zallery/blob/main/LICENSE)

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
- Tag a cell with `thumbnail` to use its first image output on the index card.
- Tag a cell with `collapse` (or `collapse: <title>`) to hide its code behind a
  collapsed callout, handy for setup the reader can expand on demand. The cell still
  runs, and its output renders normally below the callout. The callout defaults to the
  `example` admonition; pick another type with `collapse[<type>]` or
  `collapse[<type>]: <title>`, where `<type>` is any
  [admonition](https://zensical.org/docs/authoring/admonitions/) name Zensical
  understands (`warning`, `tip`, `note`, ...).
- A failing cell does not abort the build: its traceback is rendered on the page.

## Light and dark figures

Every example runs once, under a light matplotlib style. Each figure is then
re-rendered for dark mode without re-executing anything: zallery swaps the theme
colors (figure background, axes background, black foreground) and the default
diverging colormap (`coolwarm` to `berlin`) on the drawn artists, prints a second
PNG, and swaps everything back. Both PNGs land on the page, and the site shows the
one matching the reader's color scheme.

What this means when writing an example:

- Read backgrounds from matplotlib rather than hardcoding them, for example
  `mpl.rcParams["figure.facecolor"]`. Pure black and pure white are theme colors
  wherever they appear (text, lines, line markers, and backgrounds). Per-element
  colors (`scatter(c="black")`, collections) are left alone, and any other explicit
  color is kept as is.
- Do not branch on the theme in the example: there is only one run. Pick colormaps
  that read well on both backgrounds, or swap them with a hook (below).
- Images not drawn by matplotlib (PIL images, screenshots) are shown unchanged in
  both themes.

When the built-in swap is not enough, point the `hook` key at a module of the
project that defines `gallery_retheme(fig, theme)`. It runs in the kernel after the
swap, with `"dark"` before the dark rendering and `"light"` after the figure is
swapped back, and must undo for `"light"` what it did for `"dark"`:

```python
from zallery.theme import swap_cmaps

SWAPS = {"inferno_r": "inferno"}


def gallery_retheme(fig, theme):
    """Draw with `inferno_r` on the light page, `inferno` on the dark page."""
    mapping = SWAPS if theme == "dark" else {dark: light for light, dark in SWAPS.items()}
    swap_cmaps(fig, mapping)
```

## Configuration

zallery reads the `[tool.zallery]` table of the nearest `pyproject.toml` above the
working directory; relative paths resolve against that file's directory. All keys
are optional:

| Key | Default | Meaning |
|---|---|---|
| `examples` | `docs/examples` | Directory of example sections. |
| `built` | `<examples>/_built` | Where rendered pages and images go. |
| `cache` | `.gallery-cache` | Execution/render cache. |
| `binder_repo` | unset | `owner/repo` for the Binder launch buttons. |
| `hook` | unset | Dotted name of a module, importable from the project root, defining `gallery_retheme(fig, theme)`. |
| `fingerprint` | `["uv.lock"]` | Files whose change invalidates the cache. |

The git ref stamped into Binder URLs comes from the `ZALLERY_BINDER_REF`
environment variable (default `main`).

A cached example is reused while its source, the Python version, the configuration,
the `fingerprint` files, the hook module, and the zallery sources are all unchanged.

## Site integration

zallery writes Markdown; the site provides the rest:

- Markdown extensions `attr_list`, `md_in_html`, `admonition`, `pymdownx.details`
  and `pymdownx.superfences`.
- Two CSS rules so each image shows in its own color scheme:

  ```css
  [data-md-color-scheme="slate"] img[src$="#only-light"] { display: none; }
  [data-md-color-scheme="default"] img[src$="#only-dark"] { display: none; }
  ```

- Fallback thumbnails for examples without a `thumbnail` cell, at
  `<examples>/_assets/default_thumb.svg` and `<examples>/_assets/default_thumb_dark.svg`.
- Optionally, styles for the classes zallery emits: `examples-cards` and
  `examples-card-summary` on the index page, `gallery-output` and
  `gallery-rich-output` around cell outputs. The
  [ConfUSIus stylesheet](https://github.com/confusius-tools/confusius/blob/main/docs/stylesheets/extra.css)
  is a complete example.

## Relationship to ConfUSIus

zallery is extracted from [ConfUSIus](https://github.com/confusius-tools/confusius),
where it builds the documentation's example gallery. It does not depend on
ConfUSIus and makes no assumption about what the examples compute.

## Development

```bash
uv sync            # install dependencies
just test          # run tests
just pre-commit    # run lint, format, type checks, docstring checks
```

## License

BSD-3-Clause. Portions derived from ConfUSIus; see `NOTICE`.
