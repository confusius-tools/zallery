# %% [markdown]
# # An integration of your own
#
# Zallery runs an example once and shows each output for the light and for the
# dark color scheme. What changes between the two is said by an *integration*
# class. Zallery ships one for matplotlib, plotly, PyVista and xarray. For another
# display, write your own.
#
# This cell defines a display Zallery does not know: a badge, drawn as HTML with
# its own two colors.

# %%
class Badge:
    """A label drawn as HTML."""

    def __init__(self, text, color="#7a1f2b", background="#f5c2ca"):
        self.text = text
        self.color = color
        self.background = background

    def _repr_html_(self):
        style = (
            f"color: {self.color}; background: {self.background}; "
            "padding: 0.3em 1em; border-radius: 1em; font-weight: 600"
        )
        return f'<span style="{style}">{self.text}</span>'


# %% [markdown]
# As it is, a badge has one look. This class gives it a second one:

# %%
from contextlib import ExitStack

from zallery import Integration


class Badges(Integration):
    type = "__main__.Badge"

    def retheme(self, badge, scheme):
        if scheme == "light":
            return None
        restore = ExitStack()
        restore.callback(setattr, badge, "color", badge.color)
        restore.callback(setattr, badge, "background", badge.background)
        badge.color, badge.background = badge.background, badge.color
        return restore


# %% [markdown]
# - `type` is the dotted name of the class to handle. A class that an example
#   defines is in the `__main__` module of its kernel; a class of a library has
#   the name you import it with, such as `"matplotlib.figure.Figure"`.
# - Zallery calls `retheme` before it shows the object for each scheme. The method
#   changes the object and returns a context manager that puts everything back, or
#   `None` when it has nothing to change. Here the two colors are swapped for the
#   dark scheme.
#
# Called by hand, the method shows what Zallery does around the dark rendering:

# %%
badge = Badge("stable")

with Badges().retheme(badge, "dark"):
    print("inside the block:", badge.color, "on", badge.background)
print("after the block: ", badge.color, "on", badge.background)

# %% [markdown]
# Zallery needs the class before it runs an example, so the class is in a module
# of the project, not in the example. This repository has the same class in
# `tools/gallery.py`, and its `pyproject.toml` names it:
#
# ```toml
# [tool.zallery]
# integrations = ["tools.gallery:Badges"]
# ```
#
# Zallery then shows each badge twice, and the page keeps both. Switch the color
# scheme to compare:

# %% tags=["thumbnail"]
Badge("stable")

# %% [markdown]
# A badge with other colors follows the same rule:

# %%
Badge("experimental", color="#0b4f6c", background="#bfe3f2")
