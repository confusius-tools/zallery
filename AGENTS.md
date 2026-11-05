# zallery Agent Guidelines

This file guides AI coding agents working in this repository.

## What is zallery

zallery builds an example gallery for Zensical documentation sites: it runs
jupytext percent-format `.py` examples once in a Jupyter kernel and renders each as
a Markdown page, with every matplotlib figure in a light and a dark variant. It was
extracted from [ConfUSIus](https://github.com/confusius-tools/confusius), its first
user, and must not import or assume ConfUSIus.

`README.md` is the user documentation: keep it in sync with behavior changes.

## Commands

Uses [uv](https://docs.astral.sh/uv/) and [just](https://github.com/casey/just).

```bash
uv sync            # install dependencies
just test          # run tests with coverage
just pre-commit    # ruff check/format, ty, codespell, numpydoc-validation
uv run ty check    # type check src and tests
uv build           # build sdist and wheel
just gallery       # build the docs example gallery with zallery itself
just docs          # gallery, then `zensical build --strict`
just serve-docs    # gallery, then serve the docs locally
```

Run a single test: `uv run pytest tests/test_theme.py::test_name`.

The docs site (`zensical.toml`, `docs/`) is small on purpose: the home page includes
`README.md`, and `docs/examples/` is a gallery built by zallery itself. Each example
there shows one feature; a new example also needs a `nav` entry in `zensical.toml`.
`binder/Dockerfile` is the environment mybinder.org builds for the Binder badges
of the example pages; it installs the `docs` group.
Libraries only the examples import (pandas, xarray) are in the `docs` dependency
group, which `just gallery` installs. CI installs the default groups only, so `src`
and `tests` must not import them.

## Code map

```
src/zallery/
├── cli.py       # `zallery` console script
├── config.py    # `[tool.zallery]` lookup, cache fingerprint
├── pipeline.py  # build_gallery: discover, cache, execute, render, index
├── discover.py  # example and section discovery
├── cache.py     # cache key and directory
├── execute.py   # kernel launch (ports below the ephemeral range), nbclient run
├── theme.py     # runs in the kernel: light/dark re-render of matplotlib figures
├── render.py    # executed notebook to Markdown page and images
├── thumbnail.py # HTML output to thumbnail PNGs, with a headless browser
└── index.py     # card index page
```

## Conventions

- Absolute imports only; comprehensive type hints.
- NumPy docstrings on every function and method, private ones included.
  - Optional params: `arg : type, optional` or `arg : type, default: value`.
  - Fallback behavior: "If not provided, ...".
  - Booleans start with "Whether to ...".
  - One `name : type` block per returned value.
  - Dataclass fields go under `Attributes`.
  - Module-level constants get a docstring right after them.
- Comments end with a period and do not duplicate code.
- Tests exercise the public API, with assertions that fail if the function returns
  garbage. Tests that start a kernel are marked `slow`.
- Commit messages follow Commitizen: `<type>(<scope>): <summary>`.

## Known gotchas

- Matplotlib layout engines (constrained, tight) re-solve on every draw and are not
  idempotent: the layout is frozen while the dark rendering is printed.
- The color swap reads every artist color before writing any, matches on RGB and
  keeps alpha. `savefig.facecolor` stays `auto`, or the swapped figure color is
  ignored.
- Kernel ports are picked below the OS ephemeral range with `cache_ports = False`;
  jupyter_client's default port selection races with outgoing connections on CI.
- IPython swallows exceptions raised by a display formatter, so a failing hook
  shows up on the kernel's stderr, not as a cell error.
- A collection's getters return resolved color arrays; the color as given (`"face"`,
  `None`) lives in `_original_facecolor` and `_original_edgecolor`. The palette swap
  restores from those, or an edge color stops following its face color. It skips
  colormapped collections, whose colors matplotlib recomputes on draw.
- HTML thumbnails run the browser as a command. `--blink-settings=scriptEnabled=false`
  makes it write no picture, so scripts are blocked by the page's content security
  policy instead. Without its own `--user-data-dir`, a browser the user has open
  takes over the command and no picture is written either.
- Tab cells are written as raw HTML in the markup of `pymdownx.tabbed`, not with the
  `===` syntax: indented under `===`, an HTML output is parsed as Markdown text and
  mangled (styles, scripts, table cells). `md_in_html` is no help: it wraps the tab
  inputs in a paragraph, which breaks the theme's CSS.

## Publishing setup

- The GitHub environment `pypi` restricts deployments to `v*` tags.
- PyPI Trusted Publisher (a pending publisher for the first release): project
  `zallery`, owner `confusius-tools`, repository `zallery`, workflow `publish.yml`,
  environment `pypi`. No API token is needed.
- To release: set `project.version`, run `uv lock`, commit and push, then push a
  matching `vVERSION` tag. `publish.yml` runs lint and tests, checks that the tag
  matches the version, builds, and publishes.
- Publishing is permanent. Use a new version for every release.
- Keep publishing instructions out of the README.
