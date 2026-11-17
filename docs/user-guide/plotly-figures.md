# Plotly figures

A plotly figure that a cell shows, as its last expression or with `fig.show()`, is
drawn on the page as in a notebook: zoom, pan and hover work. The example needs no
renderer setup.

- The light page shows the figure as made. The dark page draws it again with
  plotly's `plotly_dark` template merged into the figure's own. Both drop the
  paper background, so the figure sits on the page. Colors set on the figure
  itself, not by its template, are the same in both schemes.
- The templates are the `template` attribute of
  `zallery.integration.plotly.Plotly`, `(None, "plotly_dark")`: the name of a
  plotly template for each scheme, or `None` to merge none. Subclass it to change
  them (see [Integrations](integrations.md)).
- Zallery copies plotly.js from the plotly package that made the figure next to
  the page, so the site loads nothing from plotly's servers. The file weighs about
  5 MB; there is one per section that has plotly figures.
- With [HTML thumbnails](html-thumbnails.md) switched on, the plotly figure of a
  `thumbnail` cell is its example's thumbnail, drawn to fill the card in each color
  scheme.
