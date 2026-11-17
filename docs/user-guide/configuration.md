# Configuration

Zallery reads the `[tool.zallery]` table of the nearest `pyproject.toml` above the
working directory; relative paths resolve against that file's directory. All keys
are optional. The value of a key the project leaves out is in
[`config.toml`](https://github.com/confusius-tools/zallery/blob/main/src/zallery/config.toml),
which ships with Zallery.

| Key | Meaning |
|---|---|
| `examples` | Directory of example sections. |
| `built` | Where rendered pages and images go. If not set, the `_built` directory in `examples`. |
| `cache` | Execution/render cache. |
| `binder_repo` | `owner/repo` for the Binder launch badges. If not set, no Binder badge. |
| `integrations` | Integration classes of the project, as `"module:Class"` names: see [Integrations](integrations.md). |
| `fingerprint` | Files whose change invalidates the cache. |
| `html_thumbnails` | Whether an HTML output may be an example's thumbnail: see [HTML thumbnails](html-thumbnails.md). |
| `html_thumbnail_css` | Stylesheets of the site applied to HTML thumbnails. |

Each example page ends with two badges that download the example, as a `.py`
script and as an `.ipynb` notebook. Their images come from
[shields.io](https://shields.io), as the image of the Binder badge comes from
mybinder.org: a reader's browser fetches them from there.

With `binder_repo` set, each example page gets a Binder badge that opens its script
on [mybinder.org](https://mybinder.org) as a notebook. The git ref stamped into
Binder URLs comes from the `ZALLERY_BINDER_REF` environment variable (default
`main`). The repository has to provide the Binder environment: one that installs
the project and makes Jupyter open percent-format scripts as notebooks. This
repository's
[`binder/Dockerfile`](https://github.com/confusius-tools/zallery/blob/main/binder/Dockerfile)
is a working setup.

A cached example is reused while its source, the Python version, the configuration,
the `fingerprint` files, the modules of the integration classes of the project,
and the Zallery sources are all unchanged.
