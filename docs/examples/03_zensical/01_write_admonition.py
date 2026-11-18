# %% [markdown]
# # Writing an admonition
#
# An admonition is a callout box: write one in a Markdown cell, or put a code cell
# in one with the `admonition` or the `collapse` tag.
#
# ## In a Markdown cell
#
# Markdown cells are copied to the page as they are, so the
# [Zensical syntax](https://zensical.org/docs/authoring/admonitions/) applies: `!!!`,
# a type, an optional title in quotes, then the body indented by four spaces. Every
# line keeps the `# ` prefix of a Markdown cell:
#
# ```python
# # %% [markdown]
# # !!! tip "Pick a type"
# #     `note`, `tip`, `warning`, `example`, or any other type Zensical knows.
# ```
#
# This renders as:
#
# !!! tip "Pick a type"
#     `note`, `tip`, `warning`, `example`, or any other type Zensical knows.
#
# ## Around a code cell
#
# Tag a code cell with `admonition` to show its code in an admonition. The cell
# still runs, and its output shows under the admonition:
#
# ```python
# # %% tags=["admonition"]
# values = [3, 1, 2]
# print(sorted(values))
# ```
#
# This renders as:

# %% tags=["admonition"]
values = [3, 1, 2]
print(sorted(values))

# %% [markdown]
# ## Collapsed
#
# With the `collapse` tag, the admonition is collapsed. It hides the code until the
# reader opens it:
#
# ```python
# # %% tags=["collapse"]
# squares = [value**2 for value in values]
# print(squares)
# ```
#
# This renders as:

# %% tags=["collapse"]
squares = [value**2 for value in values]
print(squares)

# %% [markdown]
# ## Type and title
#
# The two tags take an admonition type in brackets and a title after a colon, both
# optional:
#
# - `admonition`: an `example` admonition titled "Example".
# - `collapse`: an `example` admonition titled "Show code".
# - `admonition: <title>` or `collapse: <title>`: your own title.
# - `admonition[<type>]` or `collapse[<type>]`: another admonition type.
# - `admonition[<type>]: <title>` or `collapse[<type>]: <title>`: both.
#
# For example:
#
# ```python
# # %% tags=["collapse[warning]: Slow setup"]
# total = sum(range(1_000_000))
# print(total)
# ```
#
# This renders as:

# %% tags=["collapse[warning]: Slow setup"]
total = sum(range(1_000_000))
print(total)

# %% [markdown]
# ## With the output inside
#
# Add the `include-output` tag to put the output of the cell in the admonition too,
# under the code. The tag has an effect only together with `admonition` or
# `collapse`:
#
# ```python
# # %% tags=["admonition[tip]: Largest first", "include-output"]
# print(sorted(values, reverse=True))
# ```
#
# This renders as:

# %% tags=["admonition[tip]: Largest first", "include-output"]
print(sorted(values, reverse=True))

# %% [markdown]
# With `collapse`, the reader opens the admonition to see the code and its output,
# here a figure:
#
# ```python
# # %% tags=["collapse: Code and figure", "include-output"]
# import matplotlib.pyplot as plt
#
# fig, ax = plt.subplots(figsize=(5, 2.5))
# ax.plot(values, marker="o")
# plt.show()
# ```
#
# This renders as:

# %% tags=["collapse: Code and figure", "include-output"]
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(5, 2.5))
ax.plot(values, marker="o")
plt.show()
