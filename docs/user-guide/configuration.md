# Configuration

Zallery reads the `#!toml [tool.zallery]` table of the nearest `pyproject.toml` above
the working directory; relative paths resolve against that file's directory. All keys
are optional. See default configuration in [`config.toml`](#default-configuration).


| Key | Meaning |
|---|---|
| `examples` | Directory of example sections. |
| `built` | Where rendered pages and images go. If not set, the `_built` directory under `examples`. |
| `cache` | Execution/render cache. |
| `binder_repo` | `owner/repo` for the Binder launch badges. If not set, no Binder badge. |
| `integrations` | Integration classes of the project, as `"module:Class"` names: see [Integrations](integrations.md). |
| `fingerprint` | Files whose change invalidates the cache. |
| `html_thumbnails` | Whether an HTML output may be an example's thumbnail: see [HTML thumbnails](html-thumbnails.md). |
| `html_thumbnail_css` | Stylesheets of the site applied to HTML thumbnails. |
| `api_references` | Whether an example page lists the objects of the project's package that the example uses, as links to their API documentation: see [API references](api-references.md). |


## Default configuration

```toml
--8<-- "src/zallery/config.toml"
```

## Binder configuration

With `binder_repo` set, each example page gets a Binder badge that opens its script on
[mybinder.org](https://mybinder.org) as a notebook. The git ref stamped into Binder
URLs comes from the `ZALLERY_BINDER_REF` environment variable (default `main`). The
repository has to provide the Binder environment: one that installs the project and
makes Jupyter open percent-format scripts as notebooks. This repository's
[`binder/Dockerfile`](https://github.com/confusius-tools/zallery/blob/main/binder/Dockerfile)
is a working setup:

```dockerfile
--8<-- "binder/Dockerfile"
```

## Cache invalidation

An example cache is invalidated when any of these are changed: its source, the Python
version, the configuration, the `fingerprint` files, the modules of the integration
classes of the project, and the Zallery source code.

