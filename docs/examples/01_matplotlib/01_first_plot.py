# %% [markdown]
# # A first plot
#
# The smallest useful example: a title, a sentence, and one figure.
#
# zallery runs this script once and renders the figure twice, for the light and the
# dark color scheme. Switch the site theme to see the other one.

# %% tags=["thumbnail"]
import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 2 * np.pi, 200)

fig, ax = plt.subplots()
ax.plot(x, np.sin(x), label="sin(x)")
ax.plot(x, np.cos(x), label="cos(x)")
ax.set_xlabel("x")
ax.set_ylabel("y")
ax.legend()
plt.show()

# %% [markdown]
# Printed text and the value of a cell's last expression are captured too.

# %%
print(f"{x.size} samples")
np.sin(x).max()
