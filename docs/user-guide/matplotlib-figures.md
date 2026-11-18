# Matplotlib figures

A matplotlib figure that a cell shows goes on the page as two PNG images, one for each
color scheme. The example needs no setup.

```python title="Snippet from example: <a href='../examples/_built/matplotlib/first_plot.md'>A first plot</a>" title_mode="html" linenums="9"
--8<-- "docs/examples/01_matplotlib/01_first_plot.py:9:21"
```

## How a figure gets its dark look

Examples run with the light look. For the dark page, Zallery does these steps on the
drawn figure:

1. Zallery replaces the colors and the colormaps of the light look with those of the
   dark look.
2. Zallery prints the figure again, as a second PNG image.
3. Zallery restores each property that it changed.

The example
[How a figure gets its dark look](../examples/_built/matplotlib/dark_look.md) does these
steps by hand.

## The two looks

The two looks are the attributes of a class,
[`Matplotlib`][zallery.integration.matplotlib.Matplotlib]. A pair is `(light, dark)`. A
mapping is `{light: dark}`.

| Attribute | Default | Meaning |
|---|---|---|
| `background` | `("#fefefe", "#0b0c0f")` | Figure background. |
| `axes_background` | `("#fdfdfd", "#0b0c0f")` | Axes background. |
| `foreground` | `("black", "#e2e4e9")` | Text, ticks, spines and default lines. |
| `palette` | `None` | The default color cycle of each color scheme. |
| `cmaps` | `{"coolwarm": "berlin"}` | Colormaps to replace. |
| `colors` | `{}` | Other exact colors to replace. |
| `rcparams` | dpi 160, savefig dpi 200, figsize `(7, 4)` | Other `rcParams` that the examples run with. |

The default colors are near the page colors of a default Zensical site. As a result, a
figure looks like a part of the page. The light backgrounds are almost white, but not
pure white. Thus pure white stays free for your data, and Zallery does not replace it.

## Colors that change

Zallery replaces only a color or a colormap that is exactly equal to a light value.
Other colors and colormaps stay as you set them. These rules apply:

- Pure black is the light value of `foreground`. Zallery replaces pure black in texts,
  lines, line markers and backgrounds.
- Zallery does not replace the colors of `background`, `axes_background` and
  `foreground` in a collection, such as the points of `scatter(c="black")`.
- Zallery replaces the colors of `palette` and of `colors` in collections too: scatter
  plots, filled areas and more.
- Zallery does not replace single colors in data drawn with a colormap. Only `cmaps`
  changes such data.
- Pure white stays the same.
- A color made from a replaced color stays as drawn. Examples are a lighter color and
  the less saturated bars of seaborn.
- A color that you set and that is equal to a palette color changes too.

### Figures on a black background

Some plot functions draw on a pure black background. Zallery takes such a figure as
drawn for a dark page. For each color scheme, Zallery replaces its black with the
background color and its white with the foreground color. This replacement includes data
colors that are pure white.

Zallery decides this for the full figure, from the figure background. A finer rule is
not possible, because one figure can hold a plot on black and a usual plot.

## Rules for an example

When you write an example with matplotlib figures, obey these rules:

- Get the background color from matplotlib, for example
  `mpl.rcParams["figure.facecolor"]`. Do not write the color in the example. Figures
  from `plt.subplots` or `plt.figure` have this background already.
- Do not write code that depends on the color scheme. The example runs one time.
- Use colormaps that are clear on a light and on a dark background, or pair them in
  `cmaps`.

## Change the look

To change the look, subclass `Matplotlib` in a module of your project:

```python title="tools/gallery.py"
from zallery.integration.matplotlib import Matplotlib


class Figures(Matplotlib):
    background = ("#f8f9fb", "#090c10")
    palette = ("Dark2", "Set2")
    cmaps = {"coolwarm": "berlin", "inferno_r": "inferno"}
    colors = {"#a8323e": "#ff6b6b"}
```

Then name the class in `pyproject.toml`. The class takes the place of `Matplotlib`:

```toml title="pyproject.toml"
[tool.zallery]
integrations = ["tools.gallery:Figures"]
```

### Palettes

`palette` gives each color scheme its default colors. A palette is the name of a listed
matplotlib colormap, such as `"Set2"` or `"tab10"`, or a list of colors. These rules
apply:

- Examples run with the light palette as the color cycle of matplotlib.
- On the dark page, each color of the light palette becomes the color at the same
  position of the dark palette. Thus the dark palette must have at least as many colors
  as the light palette.
- If the light palette is `None`, the light page uses the default cycle of matplotlib.
- If the dark palette is `None`, the two pages show the light palette.

The example
[A palette for each color scheme](../examples/_built/matplotlib/palettes.md) shows a
palette for each page.

### Colormaps and other colors

`cmaps` and `colors` are mappings from a light value to a dark value:

- `cmaps` pairs colormaps by name. For example, a figure drawn with `inferno_r` shows
  `inferno` on the dark page.
- `colors` pairs other colors, such as the colors of a brand.

### Foreground color and `rcParams`

`foreground` and `rcparams` have limits:

- Zallery matches `foreground` on the figure and does not set it. The light value must
  be the color that matplotlib draws text and axes with. To change this color, also set
  the related keys in `rcparams`.
- `rcparams` in a subclass replaces the default value. As a result, the dpi and the
  figure size of the table are lost. To keep them, write
  `rcparams = {**Matplotlib.rcparams, "font.size": 9}`.

### Ruff rule RUF012

If a project selects rule RUF012 of ruff, ruff reports `cmaps = {...}` and
`colors = {...}` as mutable class attributes. Annotate them as `Mapping[str, str]`, as
`Matplotlib` does, or ignore the rule for that file.
