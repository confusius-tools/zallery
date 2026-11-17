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

- [Writing examples](https://confusius-tools.github.io/zallery/user-guide/writing-examples/):
  where examples live, their titles and order, and the cell tags.
- [Light and dark figures](https://confusius-tools.github.io/zallery/user-guide/light-and-dark-figures/):
  how a matplotlib figure gets its two looks, and how to change the colors.
- [Integrations](https://confusius-tools.github.io/zallery/user-guide/integrations/):
  the classes that say what changes between the two color schemes, and how to write one.
- [Plotly figures](https://confusius-tools.github.io/zallery/user-guide/plotly-figures/):
  interactive figures in both color schemes.
- [PyVista plots](https://confusius-tools.github.io/zallery/user-guide/pyvista-plots/):
  pictures, GIFs and interactive scenes.
- [HTML thumbnails](https://confusius-tools.github.io/zallery/user-guide/html-thumbnails/):
  an HTML output or a plotly figure on the index card.
- [Configuration](https://confusius-tools.github.io/zallery/user-guide/configuration/):
  the keys of `[tool.zallery]`, the Binder badges and the cache.
- [Zensical integration](https://confusius-tools.github.io/zallery/user-guide/zensical-integration/):
  what the site has to provide.

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
