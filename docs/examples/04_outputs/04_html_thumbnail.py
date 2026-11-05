# %% [markdown]
# # An HTML output as the thumbnail
#
# An example without a figure can show one of its HTML outputs on its index card.
#
# Switch the option on in `pyproject.toml`, and list the stylesheets that give HTML
# outputs their look on your site:
#
# ```toml
# [tool.zallery]
# html_thumbnails = true
# html_thumbnail_css = ["docs/stylesheets/extra.css"]
# ```
#
# Then tag a cell with `thumbnail`, as for a figure. If the cell shows no image, its
# first HTML output becomes the thumbnail:
#
# ```python
# # %% tags=["thumbnail"]
# import pandas as pd
#
# pd.DataFrame(
#     {"planet": ["Mercury", "Venus", "Earth", "Mars"], "moons": [0, 0, 1, 2]}
# )
# ```
#
# This renders as usual on the page, and as the thumbnail of this example on the
# [gallery index](../../index.md):

# %% tags=["thumbnail"]
import pandas as pd

pd.DataFrame({"planet": ["Mercury", "Venus", "Earth", "Mars"], "moons": [0, 0, 1, 2]})

# %% [markdown]
# zallery takes the picture with a Chromium, Chrome or Edge it finds on the machine,
# once for each color scheme. Without a browser, the build prints a warning and the
# example keeps the default thumbnail.
