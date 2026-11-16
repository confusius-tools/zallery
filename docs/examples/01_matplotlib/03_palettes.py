# %% [markdown]
# # A palette for each color scheme
#
# Give each color scheme its own default colors: strong ones on the light page,
# softer ones on the dark page.
#
# The look of matplotlib figures is the data of a class, `Matplotlib`. This
# gallery subclasses it in `tools/gallery.py` and sets both palettes, the light one
# first:
#
# ```python
# from zallery.matplotlib import Matplotlib
#
#
# class Figures(Matplotlib):
#     palette = ("Dark2", "Set2")
# ```
#
# Its `pyproject.toml` names the class, which takes the place of `Matplotlib`:
#
# ```toml
# [tool.zallery]
# integrations = ["tools.gallery:Figures"]
# ```
#
# A palette is the name of a listed matplotlib colormap, or a list of colors. The
# example runs once, with the light palette as matplotlib's color cycle. For the
# dark page, Zallery replaces each color with the one at the same position in the
# dark palette. Switch the site theme to compare.

# %% tags=["thumbnail"]
import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 2 * np.pi, 200)

fig, ax = plt.subplots()
for shift in range(4):
    ax.plot(x, np.sin(x + shift), label=f"shift {shift}")
ax.legend()
plt.show()

# %% [markdown]
# Scatter plots and filled areas follow too. A color that is not in the palette
# stays as it is on both pages:

# %%
rng = np.random.default_rng(0)

fig, ax = plt.subplots()
ax.fill_between(x, np.sin(x), alpha=0.3, label="filled area")
ax.scatter(x[::10], np.sin(x[::10]) + rng.normal(scale=0.2, size=20), label="scatter")
ax.plot(x, np.cos(x), color="crimson", label="crimson, kept")
ax.legend()
plt.show()
