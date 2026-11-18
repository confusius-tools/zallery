# API references

An example page can end with the list of the objects of your package that the
example uses, each one a link to its API documentation. The API documentation of
an object can then list the examples that use it.

Switch the option on in `pyproject.toml`:

```toml
[project]
name = "my-package"

[tool.zallery]
api_references = true
```

The page of an example that uses `my_package` then ends with a section "API used
in this example", after the running time and the downloads. The gallery of this
site has the option on: see the end of
[How a figure gets its dark look](../examples/_built/matplotlib/dark_look.md).

- The package is the `name` of `[project]`, as it is imported: `my-package` gives
  `my_package`. Objects of other packages are not listed.
- Zallery finds the objects on the running example: after each cell, it looks at
  what the names in the cell hold. An object is listed under the module and the
  class that define it, whatever name the example gives it. With
  `import my_package as mp`, the cell `reader = mp.Reader(); reader.read()` lists
  `Reader` and `Reader.read`.
- Functions, classes, methods and properties are listed. A variable that holds an
  instance lists its class.
- A property is listed and not read, since reading one may compute or load data.
- A method called on the result of a call, as in `mp.load(path).mean()`, is not
  found: no name holds that result.
- Switching the option on or off runs the examples again.

## What the site needs

The links are cross-references that
[mkdocstrings](https://mkdocstrings.github.io/python/) resolves, so the site needs
it, with the API documentation of the package.

- An object that has API documentation becomes a link to it.
- An object that has none shows as plain text. It gives no warning, also in a
  strict build.
- With the `backlinks` option of mkdocstrings, the documentation of each object
  lists the pages that reference it, the examples among them:

    ```toml
    [project.plugins.mkdocstrings.handlers.python.options]
    backlinks = "tree"
    ```

    An object used by the example "A first plot" then shows "Referenced by:
    Examples, Matplotlib figures, A first plot, API used in this example".

The heading of the section has the id `gallery-api`, and the list has the class
`gallery-api`, for the styles of the site.

## Only the examples

mkdocstrings lists every reference to an object: those of the user guide and of
other docstrings too. To list only the examples, Zallery ships a template for the
backlinks. With `api_references` on, each build of the gallery writes it to the
`mkdocstrings` folder of the cache. Name that folder in `zensical.toml`:

```toml
[project.plugins.mkdocstrings]
custom_templates = ".zallery-cache/mkdocstrings"
```

- The template keeps the references whose anchor is `gallery-api`, the id of the
  heading that Zallery writes, and leaves out every other one.
- It shows each as the title of its example, under "Used in the examples". The
  link opens the example at its top.
- An object that no example uses shows nothing.
- Build the gallery before the site, so that the folder is there.
- With another `cache` (see [Configuration](configuration.md)), the folder is
  `<cache>/mkdocstrings`.

mkdocstrings reads one templates folder. A site that already has its own names
it to Zallery, which then writes its template there and not in the cache:

```toml
[tool.zallery]
api_references = true
api_templates = "tools/mkdocstrings"
```

- Zallery writes the file `python/material/backlinks.html.jinja` in that folder on
  every build, and leaves the other files as they are.
- The file is Zallery's: a change made to it by hand is lost at the next build.
