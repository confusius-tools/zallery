[![PyPI version](https://img.shields.io/pypi/v/zallery?style=flat-square&color=d93a54&label=PyPI)](https://pypi.org/project/zallery/)
[![Python versions](https://img.shields.io/pypi/pyversions/zallery?style=flat-square&color=0099e5&logo=python&logoColor=white)](https://pypi.org/project/zallery/)
[![License](https://img.shields.io/github/license/confusius-tools/zallery?style=flat-square&color=3ad9a4)](https://github.com/confusius-tools/zallery/blob/main/LICENSE)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/confusius-tools/zallery/main?urlpath=lab/tree/docs/examples)

# Zallery

**Zallery** builds an example gallery for [Zensical](https://zensical.org)
documentation sites from plain Python scripts.

Each example is a [jupytext](https://jupytext.readthedocs.io) percent-format `.py`
file. Zallery runs it once in a Jupyter kernel, renders it as a notebook-style Markdown
page with code, outputs, and `.py`/`.ipynb` downloads, and writes an index page with one
card per example. Outputs have extensible built-in support for light and dark color
scheme.

## Installation

```bash
uv add --dev zallery
```

Or with pip:

```bash
pip install zallery
```

## Quick start

Add a `#!toml [tool.zallery]` section to the project's `pyproject.toml` (an empty section is
enough):

```toml
[tool.zallery]
gallery_root = "docs/examples"
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

This generates `docs/examples/index.md` (the card index),
`docs/examples/_built/my-section/hello.md` with its images and downloads, and
`docs/examples/_built/my-section/index.md` (the page of the section). Add them
to the site navigation in `zensical.toml` like any other page.

The build also writes a stylesheet, `docs/examples/_built/zallery.css`. List it in
`zensical.toml`, with its path from the docs folder:

```toml
extra_css = ["examples/_built/zallery.css"]
```

## Command line

```
zallery [--no-run] [--no-cache] [--abort-on-error] [EXAMPLE ...]
```

- With no arguments, every example is executed, or restored from cache.

```
zallery
```

- With specific paths to run only those. The whole gallery is still rendered: the
  others are restored from cache if present, or rendered without execution.

```
zallery path/to/example_1.py path/to/example_2.py
```

- `--no-run` restored from cache if present, or rendered without execution.
- `--no-cache` executes the selected examples even when a cached result exists; the
  result replaces the cache entry.
- `--abort-on-error` stops the build at the first cell that raises, prints its
  traceback and exits with status 1. Without it, the traceback is rendered on the
  page of the example and the build goes on.
    - The examples after that cell are not built and the index page is not
      written.
    - A cell tagged `raises-exception` may raise: it does not stop the build.
    - An example whose cached result shows an error is run again, so that an
      error does not pass because it is in the cache.

`python -m zallery` is equivalent.

## User guide

The user guide has one page for each topic:

- [Writing examples](https://zallery.confusius.tools/user-guide/writing-examples/):
  Syntax, tips and tricks to write and render your first example.
- [Light and dark figures](https://zallery.confusius.tools/user-guide/light-and-dark-figures/):
  how an output gets a light look and a dark look from one run.
- [Integrations](https://zallery.confusius.tools/user-guide/integrations/):
  the classes that say what changes between the two color schemes, and how to write one.
- [Matplotlib figures](https://zallery.confusius.tools/user-guide/matplotlib-figures/):
  the colors, colormaps and palettes of each color scheme, and how to change them.
- [Plotly figures](https://zallery.confusius.tools/user-guide/plotly-figures/):
  interactive figures in both color schemes.
- [PyVista plots](https://zallery.confusius.tools/user-guide/pyvista-plots/):
  pictures, GIFs and interactive scenes.
- [HTML thumbnails](https://zallery.confusius.tools/user-guide/html-thumbnails/):
  an HTML output or a plotly figure on the index card.
- [API references](https://zallery.confusius.tools/user-guide/api-references/):
  links from an example to the API documentation of what it uses, and back.
- [Configuration](https://zallery.confusius.tools/user-guide/configuration/):
  the keys of `[tool.zallery]`, the Binder badges and the cache.
- [Zensical integration](https://zallery.confusius.tools/user-guide/zensical-integration/):
  what the site has to provide.

## Development

```bash
uv sync            # install dependencies
just test          # run tests
just pre-commit    # run lint, format, type checks, docstring checks
just serve-docs    # build the example gallery in docs/examples and serve the docs
```

## License

BSD-3-Clause. See
[LICENSE](https://github.com/confusius-tools/zallery/blob/main/LICENSE).
