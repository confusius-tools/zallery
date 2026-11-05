# %% [markdown]
# # A pandas DataFrame
#
# A DataFrame shows as the table a notebook displays, in both color schemes.
#
# pandas gives the table as HTML. zallery copies it to the page, and the site's
# stylesheet gives it the look of a notebook table.

# %% tags=["thumbnail"]
import numpy as np
import pandas as pd

rng = np.random.default_rng(0)
frame = pd.DataFrame(
    {
        "subject": [f"sub-{number:02d}" for number in range(1, 7)],
        "group": ["control", "treated"] * 3,
        "age": rng.integers(20, 40, size=6),
        "score": rng.normal(100, 15, size=6).round(1),
    }
)
frame

# %% [markdown]
# The result of an operation is a table too, here with a named index:

# %%
frame.groupby("group")[["age", "score"]].mean()

# %% [markdown]
# A Series has no HTML form, so it shows as text:

# %%
frame["score"]
