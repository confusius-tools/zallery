# HTML thumbnails

An example without a figure can show an HTML output, such as a DataFrame or an
xarray view, on its index card. Switch the option on in `pyproject.toml`:

```toml
[tool.zallery]
html_thumbnails = true
html_thumbnail_css = ["docs/stylesheets/extra.css"]
```

A `thumbnail` cell that shows no image then gives its first HTML output, or plotly
figure, as the thumbnail. Zallery pictures the top-left corner of the output
with a headless browser, once for each color scheme.

- The machine that builds the gallery needs a Chromium-family browser. Zallery
  uses the one named by the `ZALLERY_BROWSER` environment variable (a command or
  a path). Without that variable, it takes the first of `chromium`,
  `chromium-browser`, `google-chrome`, `google-chrome-stable`, `chrome`,
  `microsoft-edge` and `msedge` on the `PATH`, then the headless shell that
  `uvx playwright install chromium-headless-shell` downloads.
- Without a browser, the build prints a warning and goes on: the examples keep the
  default thumbnail.
- `html_thumbnail_css` lists stylesheets of your site, so that the output looks as
  it does on its page. The stylesheet of Zallery is always part of the picture, before
  those of your site. The theme's own stylesheet is not part of the picture;
  Zallery sets the `data-md-color-scheme` attribute and the
  `--md-default-bg-color` and `--md-default-fg-color` variables that site styles
  usually build on.
- The page of the picture has the colors of a default Zensical page. A site with
  its own page colors sets `--md-default-bg-color` and `--md-default-fg-color` for
  each scheme in one of those stylesheets, as it does for its pages.
- An output with a dark variant (see [Integrations](integrations.md)) gives each
  picture its own HTML.
- The picture runs the output's own scripts but loads nothing from the network: an
  output whose scripts need a file from the network comes out empty.
