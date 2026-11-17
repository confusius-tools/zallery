# Integrations

What a display library needs, and what changes on its outputs between the two
color schemes, is said by an *integration* class. Zallery ships four:

| Class | For |
|---|---|
| `zallery.integration.matplotlib:Matplotlib` | [matplotlib figures](light-and-dark-figures.md) |
| `zallery.integration.plotly:Plotly` | [plotly figures](plotly-figures.md) |
| `zallery.integration.pyvista:PyVista` | [PyVista plots](pyvista-plots.md) |
| `zallery.integration.xarray:Xarray` | HTML views of xarray objects |

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
from zallery.integration.matplotlib import Matplotlib


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

`swap_colors` and `swap_cmaps` of `zallery.integration.matplotlib` take the
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
