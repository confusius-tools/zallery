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
# The next two cells draw the same samples in two ways. The first one starts with
# `# %% tags=["tab: Line", "thumbnail"]`, the second one with
# `# %% tags=["tab: Histogram"]`:

# %% tags=["tab: Line", "thumbnail"]
fig, ax = plt.subplots()
ax.plot(samples)
ax.set_xlabel("sample")
ax.set_ylabel("value")
plt.show()

# %% tags=["tab: Histogram"]
fig, ax = plt.subplots()
ax.hist(samples, bins=30)
ax.set_xlabel("value")
ax.set_ylabel("count")
plt.show()

print(f"mean: {samples.mean():.2f}")

# %% [markdown]
# Every tab runs, in order and in the same kernel, whichever one the reader opens.
# Use tabs for alternatives that can run one after the other, not for setups that
# conflict.
