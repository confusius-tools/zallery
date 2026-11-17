# PyVista plots

A PyVista plotter that a cell shows with `show()` gives its picture under the cell,
as in a notebook. The example needs no setup: Zallery runs PyVista in its gallery
mode, set with environment variables before the example imports it
(`PYVISTA_OFF_SCREEN`, `PYVISTA_BUILDING_GALLERY`, `PYVISTA_AUTO_CLOSE`, and
`PYVISTA_JUPYTER_BACKEND` set to `none`). A variable you set yourself keeps your
value. A plotter is closed after the cell that shows it.

- The picture is taken twice, like a matplotlib figure: as the example draws it,
  under PyVista's default theme, and again with the colors of PyVista's dark theme
  for the dark page. The colors that differ between the two themes are swapped: the
  background, and the black of texts, edges, outlines and axes, which becomes
  white. A color you set yourself to one of those is swapped too; other colors and
  colormaps stay. A plot you draw under another theme stays as it is.
- The two themes are the `themes` attribute of
  `zallery.integration.pyvista.PyVista`, `("DocumentTheme", "DarkTheme")`: names
  of classes of `pyvista.themes`. The environment variables are its
  `environment` attribute. Subclass it to change them
  (see [Integrations](integrations.md)).
- A plotter that records a GIF, with `open_gif` and `write_frame`, shows the
  animation instead of its last picture. Recording needs the `imageio` package. The
  animation is the same in both color schemes: its frames are recorded as the
  example runs.
- With the `trame-pyvista` package installed, the picture shares a set of tabs with
  an interactive scene, as in the PyVista documentation: "Static Scene" and
  "Interactive Scene". PyVista exports the scene and the browser draws it: the site
  needs no server. Each color scheme has its scene, which loads when the reader
  opens the tab. Zallery writes the scenes as `.vtksz` files, which hold the data
  of the plot, and copies the viewer of trame next to the page (about 1 MB, once
  per section).
- A GIF is not taken as the thumbnail: tag a cell that shows a still picture.
- On a machine without a display, VTK draws off screen through EGL or OSMesa: the
  machine needs one of them (a GPU driver or Mesa).
