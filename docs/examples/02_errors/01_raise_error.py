# %% [markdown]
# # An example that raises
#
# A failing cell does not abort the gallery build: its traceback is rendered on the
# page, as a notebook would show it.
#
# The cells before the failure render normally.

# %%
values = [1, 2, 3]
print(sum(values))

# %% [markdown]
# This cell fails on purpose:

# %%
raise ValueError("This example fails on purpose.")

# %% [markdown]
# The kernel is still alive, so the cells after it run with the state left by the
# cells before.

# %%
print(len(values))
