# Light and dark figures

Zallery runs each example one time. From this run, an output can get two looks: one for
the light color scheme of the site and one for the dark color scheme. The page of the
example holds the two looks. The site shows the look of the color scheme that the reader
uses.

## Integrations

An *integration* is a class that gives the outputs of one display library their two
looks. Zallery ships four integrations:

| Output | Integration | Dark look |
|---|---|---|
| [Matplotlib figure](matplotlib-figures.md) | `Matplotlib` | The same figure with other colors and colormaps. |
| [Plotly figure](plotly-figures.md) | `Plotly` | The same figure with the `plotly_dark` template. |
| [PyVista plot](pyvista-plots.md) | `PyVista` | The same plot with the colors of the dark theme of PyVista. |
| [xarray object](../examples/_built/outputs/xarray.md) | `Xarray` | The same HTML view with other values for its CSS variables. |

You can change an integration, or write one for a different library: see
[Integrations](integrations.md).

## One run, two looks

An example does not run again for the dark color scheme. When a cell shows an object,
Zallery does these steps for the light color scheme, then for the dark color scheme:

1. The integration gives the object the look of the color scheme.
2. Zallery takes the rendering of the object.
3. The integration restores each change.

After these steps, the object is as the example made it. The cells that follow get the
same object.

The view of an xarray object is different. It is one HTML output, and CSS variables give
its colors. The `Xarray` integration thus changes nothing in the kernel. When Zallery
writes the page, this integration adds the values of the variables for each color
scheme.

The example
[How a figure gets its dark look](../examples/_built/matplotlib/dark_look.md) does the
steps by hand for a matplotlib figure.

## Rules for an example

When you write an example, obey these rules:

- Do not write code that depends on the color scheme. The example runs one time, with
  the light look.
- Use the default colors of the library for the parts that must change with the color
  scheme. An integration changes only the colors that it knows, such as these defaults.
- For the colors that you set, use colors that are clear on a light and on a dark
  background. An integration does not change these colors, unless one is equal to a
  color that it knows.

The page of each library gives the colors that its integration changes.

## Outputs without an integration

Zallery takes one rendering of an output that no integration knows:

- An image, such as a PIL image or a screenshot, is the same on the light page and on
  the dark page.
- An HTML output, such as a pandas table, goes on the page as it is. The stylesheet of
  the site gives the output its colors in the two color schemes.

To give such an output two looks, write an integration for its class: see
[Integrations](integrations.md).

## If the dark look fails

If an integration cannot make the dark look of an output, the output is not lost. The
page shows the light look in the two color schemes, and the error shows under the cell.

## Change a look

The colors of an integration are attributes of its class. A project changes them with a
subclass, which it names in `pyproject.toml`. The page of each library gives the
attributes. [Integrations](integrations.md) gives the procedure.
