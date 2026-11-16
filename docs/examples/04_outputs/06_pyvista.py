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
# A plotter without a recording shows its last picture:

# %% tags=["thumbnail"]
pl = pv.Plotter()
pl.add_mesh(pv.Sphere(), show_edges=True, color="tan")
pl.show()

# %% [markdown]
# The pictures are the same in both color schemes, on PyVista's own background.
