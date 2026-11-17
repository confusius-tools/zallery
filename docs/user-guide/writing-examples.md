# Writing examples

Examples live under `<examples>/<section>/<name>.py`.

- The first Markdown heading of an example is its page title; the next Markdown
  paragraph is the summary shown on its index card.
- A section folder may contain a `_section.md` whose first heading becomes the section
  title on the index page.
- An `_index.md` in the examples root replaces the default header of the index page.
- A leading numeric prefix (`01_io/`, `02_first.py`) orders sections and examples and
  is stripped from the built names.
- Files and folders starting with `_` are skipped.
- Tag a cell with `thumbnail` to use its first image output on the index card. With
  [HTML thumbnails](html-thumbnails.md) switched on, a cell without an image gives its
  first HTML output.
- Tag a cell with `collapse` (or `collapse: <title>`) to hide its code behind a
  collapsed callout, handy for setup the reader can expand on demand. The cell still
  runs, and its output renders normally below the callout. The callout defaults to the
  `example` admonition; pick another type with `collapse[<type>]` or
  `collapse[<type>]: <title>`, where `<type>` is any
  [admonition](https://zensical.org/docs/authoring/admonitions/) name Zensical
  understands (`warning`, `tip`, `note`, ...).
- Tag consecutive code cells with `tab: <title>` to show them as tabs, each with its
  code and its output. An untagged cell, code or Markdown, ends the set of tabs.
  Every tab runs, in order and in the same kernel. The `collapse` and `annotate`
  tags are ignored on a tab cell.
- Tag a code cell with `title: <text>` to show a title above its code, and with
  `hl_lines: <lines>` to highlight lines: numbers and ranges separated by spaces,
  such as `hl_lines: 2 4-5`. Line 1 is the first line of the cell.
- Tag a code cell with `annotate` to attach notes to its lines. End a line with a
  comment such as `# (1)!`, and write the notes as a numbered list in the Markdown
  cell that follows. Zallery writes that cell directly under the code, above the
  output, which is where Zensical reads the notes from.
- A failing cell does not abort the build: its traceback is rendered on the page.
