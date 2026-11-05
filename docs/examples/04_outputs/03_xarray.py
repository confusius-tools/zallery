# %% [markdown]
# # xarray objects
#
# A DataArray or a Dataset keeps its interactive view: the sections fold and unfold
# on the page, in both color schemes.
#
# The view is HTML and CSS only, so it works on a static page. Click the icons at
# the end of a row to see the attributes and the values of a variable.

# %%
import numpy as np
import xarray as xr

rng = np.random.default_rng(0)
time = np.arange(0, 2.5, 0.5)
signal = xr.DataArray(
    rng.normal(size=(time.size, 2, 3)),
    dims=("time", "y", "x"),
    coords={
        "time": ("time", time, {"units": "s"}),
        "y": ("y", np.arange(2) * 0.1, {"units": "mm"}),
        "x": ("x", np.arange(3) * 0.1, {"units": "mm"}),
    },
    name="signal",
    attrs={"units": "a.u.", "description": "Random values"},
)
signal

# %% [markdown]
# A Dataset groups several variables that share coordinates:

# %% tags=["thumbnail"]
dataset = xr.Dataset(
    {"signal": signal, "mean": signal.mean("time"), "peak": signal.max("time")},
    attrs={"title": "A small dataset"},
)
dataset
