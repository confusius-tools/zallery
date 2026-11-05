# %% [markdown]
# # Cells in tabs
#
# Tag consecutive code cells with `tab: <title>` to show them as tabs, each with its
# code and its output.
#
# Cells tagged one after the other share a set of tabs. An untagged cell, code or
# Markdown, ends the set. This cell is not tagged, so it renders as usual:

# %%
import matplotlib.pyplot as plt
import numpy as np

rng = np.random.default_rng(0)
samples = rng.normal(size=500)

# %% [markdown]
# These two cells draw the same samples in two ways:
#
# ```python
# # %% tags=["tab: Line", "thumbnail"]
# fig, ax = plt.subplots()
# ax.plot(samples)
# plt.show()
#
# # %% tags=["tab: Histogram"]
# fig, ax = plt.subplots()
# ax.hist(samples, bins=30)
# plt.show()
#
# print(f"mean: {samples.mean():.2f}")
# ```
#
# Tags combine: `thumbnail` puts the first figure on the index card. The cells
# render as:

# %% tags=["tab: Line", "thumbnail"]
fig, ax = plt.subplots()
ax.plot(samples)
plt.show()

# %% tags=["tab: Histogram"]
fig, ax = plt.subplots()
ax.hist(samples, bins=30)
plt.show()

print(f"mean: {samples.mean():.2f}")

# %% [markdown]
# Every tab runs, in order and in the same kernel, whichever one the reader opens.
# Use tabs for alternatives that can run one after the other, not for setups that
# conflict.
