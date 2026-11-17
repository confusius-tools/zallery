# Light and dark figures

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
`zallery.integration.matplotlib.Matplotlib`. A pair is `(light, dark)`; a mapping
is `{light: dark}`:

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
from zallery.integration.matplotlib import Matplotlib


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
- `rcparams` in a subclass replaces the default one: the dpi and figure size above
  are lost. To keep them, write `rcparams = {**Matplotlib.rcparams, "font.size": 9}`.
- In a project that selects ruff's rule RUF012, ruff flags `cmaps = {...}` and
  `colors = {...}` as mutable class attributes. Annotate them as
  `Mapping[str, str]`, as `Matplotlib` does, or ignore the rule for that file.
