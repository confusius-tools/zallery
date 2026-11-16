# %% [markdown]
# # PyVista plots
#
# A [PyVista](https://docs.pyvista.org) plot shows on the page with the code a
# notebook runs: build a `Plotter` and call `show()`. The example needs no setup:
# Zallery runs PyVista in its gallery mode, off screen, and puts the picture of
# each plotter shown by a cell under that cell.
#
# A plotter that records a GIF shows the animation instead. Recording needs the
# `imageio` package.

# %%
import pyvista as pv

sphere = pv.Sphere()
pl = pv.Plotter()
pl.enable_hidden_line_removal()
pl.add_mesh(sphere, show_edges=True, color="tan")
pl.open_gif("animation.gif", fps=10)
for angle in range(0, 360, 10):
    rotated = sphere.rotate_x(angle, point=(0, 0, 0), inplace=False)
    pl.clear_actors()
    pl.add_mesh(rotated, show_edges=True, color="tan")
    pl.write_frame()
pl.show()

# %% [markdown]
# The animation is the same in both color schemes: its frames are recorded as the
# example runs.
#
# A plotter without a recording shows its picture, and Zallery takes that picture
# twice: as the example draws it, under PyVista's default theme, and again with
# the colors of PyVista's dark theme, for the dark color scheme. Switch the scheme
# to see it.
#
# With the `trame-pyvista` package installed, the picture shares a set of tabs
# with an interactive scene, as in the PyVista documentation. PyVista exports the
# scene and your browser draws it, with no server.

# %% tags=["thumbnail"]
hills = pv.examples.load_random_hills()
pl = pv.Plotter()
pl.add_mesh(hills, scalars="Elevation", scalar_bar_args={"title": "Elevation"})
pl.show_bounds()
pl.show()
