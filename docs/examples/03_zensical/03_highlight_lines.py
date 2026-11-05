# %% [markdown]
# # Highlighted lines and a title
#
# Point the reader at the lines that matter, and give the cell a title.
#
# Tag a code cell with `title: <text>` to show a title above its code, and with
# `highlight: <lines>` to highlight lines. Lines are numbers and ranges separated by
# spaces. Line 1 is the first line of code, under the `# %%` line:
#
# ```python
# # %% tags=["title: Keep the even numbers", "highlight: 2 4-5"]
# numbers = range(10)
# evens = [n for n in numbers if n % 2 == 0]
#
# print(evens)
# print(sum(evens))
# ```
#
# This renders as:

# %% tags=["title: Keep the even numbers", "highlight: 2 4-5"]
numbers = range(10)
evens = [n for n in numbers if n % 2 == 0]

print(evens)
print(sum(evens))

# %% [markdown]
# Each tag also works on its own.
