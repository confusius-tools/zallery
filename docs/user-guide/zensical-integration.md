# Zensical integration

Zallery writes Markdown pages and a stylesheet. The Zensical site provides the rest, in
`zensical.toml`:

- Markdown extensions `attr_list`, `md_in_html`, `admonition`, `pymdownx.details`
  and `pymdownx.superfences`.
- `nav` entries for the index page and the built pages. The
  [page of a section](writing-examples.md#section-pages) is optional there.
- The stylesheet of Zallery in `extra_css`, before the stylesheet of the site if the
  site has one:

    ```toml
    extra_css = ["examples/_built/zallery.css", "stylesheets/extra.css"]
    ```

    Zallery writes `zallery.css` to the built folder on every build. The path is
    relative to the docs folder of the site.

- Fallback thumbnails for examples without a `thumbnail` cell, at
  `<gallery_root>/_assets/default_thumb.svg` and `<gallery_root>/_assets/default_thumb_dark.svg`.
- Optionally, thumbnails for examples in which a cell raised an error, at
  `<gallery_root>/_assets/error_thumb.svg` and `<gallery_root>/_assets/error_thumb_dark.svg`.
  With both files there, the card of such an example shows them in place of the
  example's own thumbnail, so that a broken example stands out on the index page.

This repository's
[`zensical.toml`](https://github.com/confusius-tools/zallery/blob/main/zensical.toml)
is a working setup.

## Styles

The stylesheet of Zallery does these things:

- It shows each image in its own color scheme.
- It lays out the cards of the examples, with the summary of an example over its
  thumbnail on hover.
- It tells the output of a cell apart from its code.
- It gives a pandas table the look of a notebook table.

To change a style, write a rule for the same class in the stylesheet of the site. The
rule of the site wins, because its stylesheet comes after the stylesheet of Zallery.
Zallery writes these classes:

| Class | Where |
|---|---|
| `examples-cards` | The cards of the examples, on the index page, a section page and under an API object. |
| `examples-card-summary` | The summary of an example, over its thumbnail. |
| `gallery-api-cards` | The cards of the examples under an API object: see [API references](api-references.md). |
| `gallery-output` | A plain-text output of a cell. |
| `gallery-rich-output` | An HTML output of a cell. |
| `gallery-html-light`, `gallery-html-dark` | An HTML output that has a variant for each color scheme. |
| `gallery-plotly` | A plotly figure. |
| `gallery-scene` | A PyVista scene. |
| `gallery-binder`, `gallery-download` | The Binder badge and the two download badges. |
| `gallery-api` | The list of [API references](api-references.md) of an example. |

The stylesheet has no rule for the outputs of scikit-learn. The
[ConfUSIus stylesheet](https://github.com/confusius-tools/confusius/blob/main/docs/stylesheets/extra.css)
styles them. xarray views need no site styles: Zallery adapts them to the color scheme
itself.
