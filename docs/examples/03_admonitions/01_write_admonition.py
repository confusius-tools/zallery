# %% [markdown]
# # Writing an admonition
#
# An admonition is a callout box: write one in a Markdown cell, or fold a code cell
# into one with the `collapse` tag.
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
# Tag a code cell with `collapse` to hide its code in a collapsed admonition. The
# cell still runs, and its output stays visible below. The next cell starts with
# `# %% tags=["collapse"]`:

# %% tags=["collapse"]
values = [3, 1, 2]
print(sorted(values))

# %% [markdown]
# The tag takes an admonition type in brackets and a title after a colon, both
# optional:
#
# - `collapse`: an `example` admonition titled "Show code".
# - `collapse: <title>`: your own title.
# - `collapse[<type>]`: another admonition type.
# - `collapse[<type>]: <title>`: both.
#
# The next cell starts with `# %% tags=["collapse[warning]: Slow setup"]`:

# %% tags=["collapse[warning]: Slow setup"]
total = sum(range(1_000_000))
print(total)
