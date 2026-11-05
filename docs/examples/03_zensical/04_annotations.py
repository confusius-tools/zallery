# %% [markdown]
# # Code annotations
#
# Attach a note to a line of code. The reader opens it from a marker at the end of
# the line.
#
# Tag the cell with `annotate` and end a line with a comment such as `# (1)!`. Write
# the notes as a numbered list in the Markdown cell that follows:
#
# ```python
# # %% tags=["annotate"]
# values = [3, 1, 2]
# ordered = sorted(values)  # (1)!
# print(ordered[-1])  # (2)!
#
# # %% [markdown]
# # 1.  `sorted` returns a new list and leaves `values` as it is.
# # 2.  The last item of a sorted list is the largest one.
# ```
#
# This renders as:

# %% tags=["annotate"]
values = [3, 1, 2]
ordered = sorted(values)  # (1)!
print(ordered[-1])  # (2)!

# %% [markdown]
# 1.  `sorted` returns a new list and leaves `values` as it is.
# 2.  The last item of a sorted list is the largest one.

# %% [markdown]
# zallery writes the list directly under the code, above the output: that is where
# Zensical reads the notes from. In the downloaded script, the markers are plain
# comments.
