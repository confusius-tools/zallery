# %% [markdown]
# # Choosing the thumbnail
#
# Tag the cell whose figure should represent the example on the gallery index.
#
# This example draws two figures. The second cell starts with
# `# %% tags=["thumbnail"]`, so its figure is the one on the card. An example
# without a tagged cell gets a placeholder thumbnail.

# %%
import matplotlib.pyplot as plt
import numpy as np

rng = np.random.default_rng(0)

fig, ax = plt.subplots()
ax.hist(rng.normal(size=1000), bins=30)
ax.set_title("Not the thumbnail")
plt.show()

# %% [markdown]
# The tagged cell. Its image uses the `coolwarm` colormap, which zallery replaces
# with `berlin` on the dark page.

# %% tags=["thumbnail"]
x, y = np.meshgrid(np.linspace(-3, 3, 200), np.linspace(-3, 3, 200))

fig, ax = plt.subplots()
image = ax.imshow(
    np.sin(x) * np.cos(y), cmap="coolwarm", extent=(-3, 3, -3, 3), origin="lower"
)
fig.colorbar(image, ax=ax)
ax.set_title("The thumbnail")
plt.show()
