# Zensical integration

Zallery writes Markdown pages; the Zensical site provides the rest, in
`zensical.toml` and a stylesheet:

- Markdown extensions `attr_list`, `md_in_html`, `admonition`, `pymdownx.details`
  and `pymdownx.superfences`.
- `nav` entries for the index page and the built pages. The
  [page of a section](writing-examples.md#section-pages) is optional there.
- Two CSS rules so each image shows in its own color scheme:

  ```css
  [data-md-color-scheme="slate"] img[src$="#only-light"] { display: none; }
  [data-md-color-scheme="default"] img[src$="#only-dark"] { display: none; }
  ```

- Fallback thumbnails for examples without a `thumbnail` cell, at
  `<gallery_root>/_assets/default_thumb.svg` and `<gallery_root>/_assets/default_thumb_dark.svg`.
- Optionally, thumbnails for examples in which a cell raised an error, at
  `<gallery_root>/_assets/error_thumb.svg` and `<gallery_root>/_assets/error_thumb_dark.svg`.
  With both files there, the card of such an example shows them in place of the
  example's own thumbnail, so that a broken example stands out on the index page.
- Optionally, styles for the classes Zallery emits: `examples-cards` and
  `examples-card-summary` on the index page, `gallery-output` and
  `gallery-rich-output` around cell outputs, with `gallery-html-light` or
  `gallery-html-dark` on an HTML output that has a variant for each scheme,
  `gallery-plotly` on plotly figures, `gallery-scene` on PyVista scenes,
  `gallery-binder` on the Binder badge, `gallery-download` on the two download
  badges, `gallery-api` on the list of [API references](api-references.md) and
  `gallery-api-cards` on the cards of the examples under an API object. This repository's
  [`zensical.toml`](https://github.com/confusius-tools/zallery/blob/main/zensical.toml)
  and
  [stylesheet](https://github.com/confusius-tools/zallery/blob/main/docs/stylesheets/extra.css)
  are a working setup, with notebook-like pandas tables; the
  [ConfUSIus stylesheet](https://github.com/confusius-tools/confusius/blob/main/docs/stylesheets/extra.css)
  also styles scikit-learn outputs. xarray views need no site styles: Zallery
  adapts them to the color scheme itself.
