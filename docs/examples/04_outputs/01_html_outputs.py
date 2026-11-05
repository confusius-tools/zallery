# %% [markdown]
# # HTML outputs
#
# An object that displays itself as HTML in a notebook keeps that rendering on the
# page.
#
# zallery copies the HTML of an output to the page as it is, and the site's theme
# styles it in both color schemes.
#
# ## An object with an HTML representation
#
# Libraries such as pandas and xarray give their objects a `_repr_html_` method, which
# a notebook calls to display them. Any object can have one:


# %%
class Inventory:
    """Items and their count, displayed as an HTML table."""

    def __init__(self, items):
        self.items = items

    def _repr_html_(self):
        rows = "".join(
            f"<tr><td>{name}</td><td>{count}</td></tr>"
            for name, count in self.items.items()
        )
        head = "<thead><tr><th>Item</th><th>Count</th></tr></thead>"
        return f"<table>{head}<tbody>{rows}</tbody></table>"


Inventory({"apples": 3, "pears": 5, "plums": 8})

# %% [markdown]
# ## HTML written by hand
#
# `IPython.display.HTML` displays a string of HTML:

# %%
from IPython.display import HTML

HTML("<p>Text with <strong>emphasis</strong> and <code>code</code>.</p>")

# %% [markdown]
# ## A Rich table
#
# [Rich](https://rich.readthedocs.io) prints as HTML in a notebook, so its tables keep
# their borders and alignment:

# %% tags=["thumbnail"]
from rich.console import Console
from rich.table import Table

table = Table("Item", "Count", title="Inventory")
table.add_row("apples", "3")
table.add_row("pears", "5")
table.add_row("plums", "8")
Console().print(table)
