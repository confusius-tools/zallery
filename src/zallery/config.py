"""Project configuration, read from the `[tool.zallery]` table of `pyproject.toml`.

The table is looked up from the working directory upwards, so `zallery` can run
from anywhere inside the project. Relative paths in it are resolved against the
directory holding that `pyproject.toml`, which is also the project root the kernel
and the builder get on their `sys.path` so the integration classes of the project
import.

Keys (all optional):

- `examples`: directory of example sections, default `docs/examples`.
- `built`: where rendered pages go, default `<examples>/_built`.
- `cache`: execution/render cache directory, default `.gallery-cache`.
- `binder_repo`: `owner/repo` slug for the Binder launch badges; no badges if unset.
- `integrations`: integration classes of the project, as `"module:Class"`
  names. A class that subclasses one Zallery ships takes its place; any other is
  added (see `zallery.integration`).
- `fingerprint`: files whose content invalidates the cache when it changes,
  default `["uv.lock"]`. The `zallery` sources, the modules of the integration
  classes of the project and the table itself are always part of the fingerprint.
- `html_thumbnails`: whether a cell tagged `thumbnail` may give an HTML output as
  the thumbnail, pictured by a headless browser; default `false`.
- `html_thumbnail_css`: stylesheets of the site applied to that picture.
"""

from __future__ import annotations

import inspect
import json
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

import zallery
from zallery.integration import STOCK, Integration, load, name, resolve

_TABLE = "zallery"
"""Name of the table under `[tool]`."""

_KNOWN_KEYS = frozenset(
    {"examples", "built", "cache", "binder_repo", "integrations", "fingerprint"}
    | {"html_thumbnails", "html_thumbnail_css"}
)
"""Keys the table may contain; anything else is a typo and rejected."""

_REMOVED_KEYS = frozenset({"hook", "light", "dark"})
"""Keys of earlier versions, which integration classes replace."""


class ConfigError(ValueError):
    """Raised when no usable `[tool.zallery]` table is found or it is malformed."""


@dataclass(frozen=True)
class Config:
    """Resolved project configuration.

    Attributes
    ----------
    root : pathlib.Path
        Directory holding the `pyproject.toml` the table was read from.
    examples : pathlib.Path
        Directory of example sections.
    built : pathlib.Path
        Directory rendered pages and assets are written to.
    cache : pathlib.Path
        Execution/render cache directory.
    binder_repo : str, optional
        `owner/repo` slug for Binder launch badges. If not provided, no badges.
    integrations : tuple[Integration, ...]
        The integrations in effect, in order: an instance of each class Zallery
        ships, or of the class of the project that takes its place, then of the
        other classes the project names.
    fingerprint_files : tuple[pathlib.Path, ...]
        Files whose content is part of the cache fingerprint.
    html_thumbnails : bool, default: False
        Whether an HTML output may be pictured as an example's thumbnail.
    html_thumbnail_css : tuple[pathlib.Path, ...], default: ()
        Stylesheets of the site applied to those pictures.
    """

    root: Path
    examples: Path
    built: Path
    cache: Path
    binder_repo: str | None
    integrations: tuple[Integration, ...]
    fingerprint_files: tuple[Path, ...]
    html_thumbnails: bool = False
    html_thumbnail_css: tuple[Path, ...] = ()


def find_pyproject(start: Path) -> Path | None:
    """Return the nearest `pyproject.toml` with a `[tool.zallery]` table.

    Parameters
    ----------
    start : pathlib.Path
        Directory to search from; its parents are searched in turn.

    Returns
    -------
    pathlib.Path or None
        The file, or `None` if no ancestor holds one with the table.
    """
    for directory in (start.resolve(), *start.resolve().parents):
        candidate = directory / "pyproject.toml"
        if candidate.is_file():
            with candidate.open("rb") as handle:
                data = tomllib.load(handle)
            if _TABLE in data.get("tool", {}):
                return candidate
    return None


def _integrations(listed: object, root: Path) -> tuple[Integration, ...]:
    """Return an instance of each integration class in effect.

    Parameters
    ----------
    listed : object
        The parsed TOML value of `integrations`: a list of `"module:Class"` names.
    root : pathlib.Path
        The project root, put on `sys.path` so that the classes import.

    Returns
    -------
    tuple[Integration, ...]
        The stock classes, each replaced by the listed class that subclasses it,
        then the other listed classes (see `zallery.integration.resolve`), each
        instantiated.

    Raises
    ------
    ConfigError
        If `listed` is not a list of strings, a class does not load, two listed
        classes subclass the same stock class, or a class refuses its own
        attributes when instantiated.
    """
    if not isinstance(listed, list) or not all(isinstance(e, str) for e in listed):
        raise ConfigError(
            'integrations in [tool.zallery] must be a list of "module:Class" strings.'
        )
    if listed and str(root) not in sys.path:
        sys.path.insert(0, str(root))
    try:
        classes = resolve(load(listed), load(STOCK))
        return tuple(cls() for cls in classes)
    except Exception as exc:
        # Whatever a class of the project raises is the project's to fix.
        raise ConfigError(f"integrations in [tool.zallery]: {exc}") from exc


def load_config(start: Path) -> Config:
    """Load the configuration that applies to `start`.

    Parameters
    ----------
    start : pathlib.Path
        Directory to search from, typically the working directory.

    Returns
    -------
    Config
        The resolved configuration, with relative paths made absolute under the
        project root.

    Raises
    ------
    ConfigError
        If no `pyproject.toml` with a `[tool.zallery]` table is found, or the table
        has unknown keys, keys of an earlier version, or a malformed value.
    """
    pyproject = find_pyproject(start)
    if pyproject is None:
        raise ConfigError(
            f"No pyproject.toml with a [tool.zallery] table found in {start} or its "
            "parents."
        )
    with pyproject.open("rb") as handle:
        table = tomllib.load(handle)["tool"][_TABLE]
    if _REMOVED_KEYS & set(table):
        raise ConfigError(
            "hook, light and dark are no longer keys of [tool.zallery]: subclass an "
            "integration class and name it in integrations (see Integrations in "
            "the README)."
        )
    unknown = sorted(set(table) - _KNOWN_KEYS)
    if unknown:
        raise ConfigError(
            f"Unknown keys in [tool.zallery] of {pyproject}: {', '.join(unknown)}. "
            f"Known keys: {', '.join(sorted(_KNOWN_KEYS))}."
        )

    root = pyproject.parent
    examples = root / table.get("examples", "docs/examples")
    html_thumbnails = table.get("html_thumbnails", False)
    if not isinstance(html_thumbnails, bool):
        raise ConfigError("html_thumbnails in [tool.zallery] must be true or false.")
    stylesheets = table.get("html_thumbnail_css", [])
    if not isinstance(stylesheets, list):
        raise ConfigError("html_thumbnail_css in [tool.zallery] must be a list.")
    html_thumbnail_css = tuple(root / str(path) for path in stylesheets)
    missing = [str(path) for path in html_thumbnail_css if not path.is_file()]
    if missing:
        raise ConfigError(
            f"No such html_thumbnail_css file in [tool.zallery]: {', '.join(missing)}."
        )
    return Config(
        root=root,
        examples=examples,
        built=root / table["built"] if "built" in table else examples / "_built",
        cache=root / table.get("cache", ".gallery-cache"),
        binder_repo=table.get("binder_repo"),
        integrations=_integrations(table.get("integrations", []), root),
        fingerprint_files=tuple(
            root / p for p in table.get("fingerprint", ["uv.lock"])
        ),
        html_thumbnails=html_thumbnails,
        html_thumbnail_css=html_thumbnail_css,
    )


def deps_fingerprint(config: Config) -> str:
    """Return a string identifying everything that shapes an example's render.

    Any change to it makes every cached example miss: the configured fingerprint
    files (the lockfile by default), the `zallery` sources, the modules of the
    integration classes of the project, and the configuration values themselves. The Binder ref is deliberately not part of
    it, so renders are reused across branches.

    Parameters
    ----------
    config : Config
        The project configuration.

    Returns
    -------
    str
        Concatenated, locale-independent text of all the inputs.
    """
    parts: list[str] = [
        json.dumps(
            {
                "examples": str(config.examples.relative_to(config.root)),
                "built": str(config.built.relative_to(config.root)),
                "binder_repo": config.binder_repo,
                "integrations": [name(type(i)) for i in config.integrations],
                "html_thumbnails": config.html_thumbnails,
            },
            sort_keys=True,
        )
    ]
    # Read everything as UTF-8 so the text does not depend on the platform's locale.
    for path in (*config.fingerprint_files, *config.html_thumbnail_css):
        if path.is_file():
            parts.append(f"\n# {path.relative_to(config.root)}\n")
            parts.append(path.read_text(encoding="utf-8"))
    for path in sorted(Path(zallery.__file__).resolve().parent.glob("*.py")):
        parts.append(f"\n# zallery/{path.name}\n")
        parts.append(path.read_text(encoding="utf-8"))
    for integration in config.integrations:
        cls = type(integration)
        if cls.__module__.partition(".")[0] == "zallery":
            # Among the sources above.
            continue
        source = inspect.getsourcefile(cls)
        if source is not None and Path(source).is_file():
            parts.append(f"\n# {name(cls)}\n")
            parts.append(Path(source).read_text(encoding="utf-8"))
    return "".join(parts)
