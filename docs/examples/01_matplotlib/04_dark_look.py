# %% [markdown]
# # How a figure gets its dark look
#
# Zallery draws a figure once and prints it twice. For the dark page it changes
# the figure, prints it, and puts every change back. This example does those
# steps by hand, with the functions and the class that Zallery uses.
#
# The figure has a line with a title, and an image drawn with the `coolwarm`
# colormap:

# %% tags=["thumbnail"]
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_hex

from zallery.integration.matplotlib import Matplotlib, swap_cmaps, swap_colors

x = np.linspace(-3, 3, 200)

fig, (left, right) = plt.subplots(ncols=2, figsize=(8, 3.5))
left.plot(x, np.tanh(x))
left.set_title("A line")
image = right.imshow(np.outer(np.tanh(x), np.tanh(x)), cmap="coolwarm")
right.set_title("An image")
fig.colorbar(image)
plt.show()

# %% [markdown]
# ## Colormaps
#
# `swap_cmaps` switches the colormaps of the artists it gets, and returns a
# context manager that switches them back:

# %%
print("as drawn:        ", image.get_cmap().name)
with swap_cmaps(fig.findobj(), {"coolwarm": "berlin"}):
    print("inside the block:", image.get_cmap().name)
print("after the block: ", image.get_cmap().name)

# %% [markdown]
# ## Colors
#
# `swap_colors` does the same for single colors, such as the black of a title:

# %%
title = left.title

print("as drawn:        ", to_hex(title.get_color()))
with swap_colors(fig.findobj(), {"black": "#e2e4e9"}):
    print("inside the block:", to_hex(title.get_color()))
print("after the block: ", to_hex(title.get_color()))

# %% [markdown]
# ## The class
#
# Which colors and colormaps to switch is the data of the `Matplotlib` class:

# %%
print("colormaps: ", Matplotlib.cmaps)
print("foreground:", Matplotlib.foreground)

# %% [markdown]
# Its `retheme` method puts the two functions together. Zallery calls it for each
# color scheme, just before it prints the figure:

# %%
look = Matplotlib()

with look.retheme(fig, "dark"):
    print("inside the block:", image.get_cmap().name, to_hex(title.get_color()))
print("after the block: ", image.get_cmap().name, to_hex(title.get_color()))

# %% [markdown]
# To change the look, subclass `Matplotlib` and set its data. This gallery does:
# see [A palette for each color scheme](palettes.md).
