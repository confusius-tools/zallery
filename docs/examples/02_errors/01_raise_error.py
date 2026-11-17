# %% [markdown]
# # An example that raises
#
# A failing cell does not abort the gallery build: its traceback is rendered on the
# page, as a notebook would show it. On the index page, the card of the example
# shows the error thumbnail of the site, if the site has one.
#
# The cells before the failure render normally.

# %%
values = [1, 2, 3]
print(sum(values))

# %% [markdown]
# This cell fails on purpose. Its `raises-exception` tag says that the error is
# expected: a build run with `--abort-on-error` stops at the first cell that
# raises, but not at this one.
#
# ```python
# # %% tags=["raises-exception"]
# raise ValueError("This example fails on purpose.")
# ```
#
# This renders as:

# %% tags=["raises-exception"]
raise ValueError("This example fails on purpose.")

# %% [markdown]
# The kernel is still alive, so the cells after it run with the state left by the
# cells before.

# %%
print(len(values))
