# Zallery Agent Guidelines

This file guides AI coding agents working in this repository.

## What is Zallery

Zallery builds an example gallery for Zensical documentation sites: it runs
jupytext percent-format `.py` examples once in a Jupyter kernel and renders each as
a Markdown page, with every figure in a light and a dark variant. It was
extracted from [ConfUSIus](https://github.com/confusius-tools/confusius), its first
user, and must not import or assume ConfUSIus.

Zallery owns the mechanism: run once, take the light rendering, apply the retheme,
take the dark rendering, restore, write both to the page. What changes between the
two schemes is the business of integration classes (`integration.py`), one for
each display library. The core holds no color, colormap, template or CSS variable
of an output's look: those are attributes of the stock classes, which a project
subclasses.

`README.md` is the user documentation: keep it in sync with behavior changes.

## Commands

Uses [uv](https://docs.astral.sh/uv/) and [just](https://github.com/casey/just).

```bash
uv sync            # install dependencies
just test          # run tests with coverage
just pre-commit    # ruff check/format, ty, codespell, numpydoc-validation
uv run ty check    # type check src and tests
uv build           # build sdist and wheel
just gallery       # build the docs example gallery with Zallery itself
just docs          # gallery, then `zensical build --strict`
just serve-docs    # gallery, then serve the docs locally
```

Run a single test: `uv run pytest tests/test_matplotlib.py::test_name`.

The docs site (`zensical.toml`, `docs/`) is small on purpose: the home page includes
`README.md`, and `docs/examples/` is a gallery built by Zallery itself. Each example
there shows one feature; a new example also needs a `nav` entry in `zensical.toml`.
`binder/Dockerfile` is the environment mybinder.org builds for the Binder badges
of the example pages; it installs the `docs` group.
Libraries only the examples import (pandas, xarray, plotly, pyvista, trame-pyvista,
imageio) are in the `docs` dependency group, which `just gallery` installs. CI
installs the default groups only, so `src` and `tests` must not import them. plotly
is also in `dev`: tests draw real plotly figures, and `plotly.py` and `render.py`
import it only for an example that has one. The pyvista tests run only where the
`docs` group is installed.
The site's own integration classes are in `tools/gallery.py`, named in
`[tool.zallery]`: outside `docs/`, which Zensical publishes whole, `__pycache__`
included.

## Code map

```
src/zallery/
├── cli.py       # `zallery` console script
├── config.py    # `[tool.zallery]` lookup, cache fingerprint
├── pipeline.py  # build_gallery: discover, cache, execute, render, index
├── discover.py  # example and section discovery
├── cache.py     # cache key and directory
├── execute.py   # kernel launch (ports below the ephemeral range), nbclient run
├── integration.py # Integration base class, loader, generic capture, kernel setup
├── matplotlib.py  # Matplotlib: light rcParams, color and colormap swap
├── plotly.py      # Plotly: template of each scheme
├── pyvista.py     # PyVista: gallery mode, theme color swap, scenes
├── xarray.py      # Xarray: CSS variables of each scheme
├── render.py    # executed notebook to Markdown page and images
├── thumbnail.py # HTML output to thumbnail PNGs, with a headless browser
└── index.py     # card index page
```

`setup`, `retheme` and the private capture methods of an integration class run in
the kernel; `html` runs in the builder, which also imports and instantiates the
classes when it loads the configuration.

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
- In prose (README, docs, docstrings, comments), the package is Zallery. Write
  `zallery` only where it is code: the command, module, PyPI name, paths and the
  `[tool.zallery]` table.

## Known gotchas

- Matplotlib layout engines (constrained, tight) re-solve on every draw and are not
  idempotent: the layout is frozen while the dark rendering is printed.
- The color swap reads every artist color before writing any, matches on RGB and
  keeps alpha. `savefig.facecolor` stays `auto`, or the swapped figure color is
  ignored.
- Kernel ports are picked below the OS ephemeral range with `cache_ports = False`;
  jupyter_client's default port selection races with outgoing connections on CI.
- ipykernel 7.3 and later warns on every start that its TCP sockets are not
  encrypted, unless its connection file holds CurveZMQ keys. Zallery sets keys on
  the kernel manager when the launched ipykernel's own spec
  (`ipykernel.kernelspec.get_kernel_dict`) says it reads them: jupyter_client's
  `transport_encryption` decides from the installed kernel spec instead, which can
  belong to another ipykernel.
- IPython swallows exceptions raised by a display formatter and drops the output
  of that formatter. An output must not be lost for its dark look, so each capture
  keeps the light one when the dark one fails:
  - matplotlib: `_print_both` catches the error, prints the traceback on stderr
    and returns the light PNG alone. Without that, the figure would show as its
    text repr only.
  - generic capture: the error leaves `_display`, IPython reports it and shows the
    object through its usual formatters.
  - PyVista: `_show_plots` displays the picture `show()` took, closes the plotter,
    and raises once every plotter of the cell is handled.
  - plotly: the error raises in the cell for `fig.show()`. For a figure shown as
    the last expression, IPython reports it and the figure shows with no dark
    figure.
- Colors and palettes of a `Matplotlib` subclass are checked in `__init__`, which
  the builder runs when it loads the configuration: a bad one is a `ConfigError`.
  Colormap names are checked when a figure uses them: an example may register its
  own.
- The stock integration modules are named after their libraries (`matplotlib.py`,
  `plotly.py`, `pyvista.py`, `xarray.py`). They reach the library by absolute
  import, and only `matplotlib.py` imports its library at module level: the others
  must stay importable without it, in the builder and on CI.
- `Integration.retheme` takes its arguments by position only, so that a subclass
  names the object as it likes (`fig`, `plotter`).
- The generic capture (`Integration._install`) wraps `lookup_by_type` of
  IPython's `ipython_display_formatter`, to register the class of `type` once an
  example has imported it. IPython's own `for_type_by_name` matches a class by
  `__module__` and `__name__` only: not by the name it is imported with
  (`pandas.DataFrame`), nor a nested class. The wrapper writes `type_printers`
  directly: `for_type` looks the class up first, which would recurse.
  `Integration._display` switches that formatter off while it formats the object,
  or `format` would come back to the handler.
- A matplotlib figure on a pure black background may still hold colors of the
  light look (axes left at their default): for the dark page both the light look
  and the black one are swapped, the black one last.
- The builder puts the project root on `sys.path` to import the classes a project
  lists, and leaves it there. A test that writes such a module uses a module name
  of its own: `sys.modules` keeps the first one.
- A collection's getters return resolved color arrays; the color as given (`"face"`,
  `None`) lives in `_original_facecolor` and `_original_edgecolor`. The palette swap
  restores from those, or an edge color stops following its face color. It skips
  colormapped collections, whose colors matplotlib recomputes on draw.
- HTML thumbnails run the browser as a command. The page's content security policy
  lets inline scripts run (a plotly thumbnail is drawn by one, with plotly.js
  written in the page) and blocks every fetch. Without its own `--user-data-dir`,
  a browser the user has open takes over the command and no picture is written.
- In a kernel, plotly's default renderer sends its mime type alone, with no HTML or
  text: Zallery draws the figure itself. Both `fig` and `fig.show()` end in
  `plotly.io.show`, which publishes a raw bundle that no formatter sees: the dark
  figure is added by a hook on the kernel's display publisher
  (`register_hook`, whose hooks are per thread), on a copy of the figure rebuilt
  from the payload. A payload without template must not get plotly's default one
  when rebuilt. With `responsive: true`, a figure is as
  high as its element, so the element gets the figure's height (525px by default,
  as plotly's notebook renderer does), or it collapses to 0 on the first redraw.
- PyVista runs in its gallery mode (environment variables set by `PyVista.setup`
  in the kernel before an example imports it): `show()` displays nothing, takes a picture
  (`last_image`) and, with `PYVISTA_AUTO_CLOSE=false`, leaves the plotter open in
  `_ALL_PLOTTERS`. A `post_execute` hook then handles each plotter shown, as
  pyvista's sphinx-gallery scraper does: it swaps in the dark theme's colors,
  takes the dark picture, and closes the plotter, which also ends a GIF recording.
  A screenshot after a color change needs `plotter.render()` first, or it is the
  old picture. With trame-pyvista installed, `show()` also keeps the scene
  exported for vtk.js (`last_vtksz`); the hook exports the dark one, and the page
  shows them in iframes of trame-vtk's standalone viewer, in a tab next to the
  picture.
- The page of an example that raised ends with the comment `render.ERROR_MARK`,
  which the pipeline reads to pick the error thumbnail. A comment, not a file: the
  state has to come back from the cache, and nothing removes a stale file from
  `_built` once the example is fixed.
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
