"""Tests for zallery.config."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

import pytest

import zallery.config
from zallery.config import Config, ConfigError, deps_fingerprint, load_config


def _write_pyproject(root: Path, table: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text(f"[tool.zallery]\n{table}\n")


def _under(paths: Path | tuple[Path, ...], root: Path) -> tuple[Path, ...]:
    """Return one path or several, each relative to `root`."""
    paths = (paths,) if isinstance(paths, Path) else paths
    return tuple(path.relative_to(root) for path in paths)


def test_load_config_resolves_paths_under_the_project_root(tmp_path: Path) -> None:
    _write_pyproject(
        tmp_path,
        'examples = "site/examples"\ncache = "build/.cache"\n'
        'binder_repo = "me/repo"\nfingerprint = ["lock.txt"]\n',
    )

    config = load_config(tmp_path)

    assert config.root == tmp_path.resolve()
    assert config.examples == tmp_path.resolve() / "site" / "examples"
    assert config.built == tmp_path.resolve() / "site" / "examples" / "_built"
    assert config.cache == tmp_path.resolve() / "build" / ".cache"
    assert config.binder_repo == "me/repo"
    assert config.fingerprint_files == (tmp_path.resolve() / "lock.txt",)


def test_load_config_defaults(tmp_path: Path) -> None:
    _write_pyproject(tmp_path, "")

    config = load_config(tmp_path)

    assert config.examples == tmp_path.resolve() / "docs" / "examples"
    assert config.built == config.examples / "_built"
    assert config.cache == tmp_path.resolve() / ".gallery-cache"
    assert config.binder_repo is None
    assert config.fingerprint_files == (tmp_path.resolve() / "uv.lock",)
    assert config.html_thumbnails is False
    assert config.html_thumbnail_css == ()


def test_the_shipped_table_is_the_configuration_of_an_empty_table(
    tmp_path: Path,
) -> None:
    shipped = files("zallery").joinpath("config.toml").read_text(encoding="utf-8")
    (tmp_path / "empty").mkdir()
    (tmp_path / "empty" / "pyproject.toml").write_text("[tool.zallery]\n")
    (tmp_path / "copied").mkdir()
    (tmp_path / "copied" / "pyproject.toml").write_text(shipped, encoding="utf-8")

    empty = load_config(tmp_path / "empty")
    copied = load_config(tmp_path / "copied")

    for field in ("examples", "built", "cache", "fingerprint_files"):
        relative = getattr(empty, field)
        assert relative != empty.root
        assert _under(getattr(copied, field), copied.root) == _under(
            relative, empty.root
        )
    assert copied.binder_repo == empty.binder_repo
    assert copied.html_thumbnails == empty.html_thumbnails
    assert copied.html_thumbnail_css == empty.html_thumbnail_css
    assert [type(i) for i in copied.integrations] == [
        type(i) for i in empty.integrations
    ]


def test_a_key_the_project_leaves_out_takes_the_shipped_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(zallery.config.DEFAULTS, "cache", "elsewhere")
    monkeypatch.setitem(zallery.config.DEFAULTS, "fingerprint", ["other.lock"])
    _write_pyproject(tmp_path, 'fingerprint = ["mine.lock"]\n')

    config = load_config(tmp_path)

    assert config.cache == tmp_path.resolve() / "elsewhere"
    assert config.fingerprint_files == (tmp_path.resolve() / "mine.lock",)


def test_load_config_searches_parent_directories(tmp_path: Path) -> None:
    _write_pyproject(tmp_path, 'examples = "ex"\n')
    nested = tmp_path / "docs" / "deep"
    nested.mkdir(parents=True)
    # A pyproject without the table on the way up is skipped, not an error.
    (tmp_path / "docs" / "pyproject.toml").write_text('[project]\nname = "x"\n')

    config = load_config(nested)

    assert config.root == tmp_path.resolve()
    assert config.examples == tmp_path.resolve() / "ex"


def test_load_config_without_table_raises(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')

    with pytest.raises(ConfigError, match=r"\[tool\.zallery\]"):
        load_config(tmp_path)


def test_load_config_rejects_unknown_keys(tmp_path: Path) -> None:
    _write_pyproject(tmp_path, 'output = "docs/examples"\n')

    with pytest.raises(ConfigError, match="Unknown keys .*output"):
        load_config(tmp_path)


def test_deps_fingerprint_tracks_lockfile_and_config(tmp_path: Path) -> None:
    _write_pyproject(tmp_path, "")
    (tmp_path / "uv.lock").write_text("v1\n")
    baseline = deps_fingerprint(load_config(tmp_path))

    (tmp_path / "uv.lock").write_text("v2\n")
    after_lock = deps_fingerprint(load_config(tmp_path))
    _write_pyproject(tmp_path, 'binder_repo = "me/repo"\n')
    after_config = deps_fingerprint(load_config(tmp_path))

    assert len({baseline, after_lock, after_config}) == 3
    assert deps_fingerprint(load_config(tmp_path)) == after_config


def _classes(config: Config) -> list[str]:
    return [type(integration).__name__ for integration in config.integrations]


def test_deps_fingerprint_holds_the_sources_of_the_stock_integrations(
    tmp_path: Path,
) -> None:
    _write_pyproject(tmp_path, "")

    fingerprint = deps_fingerprint(load_config(tmp_path))

    assert "\n# zallery/config.py\n" in fingerprint
    assert "\n# zallery/integration/__init__.py\n" in fingerprint
    assert "\n# zallery/integration/matplotlib.py\n" in fingerprint
    assert "def swap_cmaps(" in fingerprint


def test_load_config_has_the_stock_integrations_by_default(tmp_path: Path) -> None:
    _write_pyproject(tmp_path, "")

    assert _classes(load_config(tmp_path)) == [
        "Matplotlib",
        "Plotly",
        "PyVista",
        "Xarray",
    ]


def test_a_listed_subclass_replaces_its_stock_class_and_others_are_added(
    tmp_path: Path,
) -> None:
    (tmp_path / "t8_conf.py").write_text(
        "from zallery import Integration\n"
        "from zallery.integration.matplotlib import Matplotlib\n"
        "class Figures(Matplotlib):\n    cmaps = {}\n"
        "class Cards(Integration):\n    type = 'cards.Card'\n"
    )
    _write_pyproject(tmp_path, 'integrations = ["t8_conf:Cards", "t8_conf:Figures"]\n')

    assert _classes(load_config(tmp_path)) == [
        "Figures",
        "Plotly",
        "PyVista",
        "Xarray",
        "Cards",
    ]


_BAD_PALETTE = (
    "from zallery.integration.matplotlib import Matplotlib\n"
    "class Bad(Matplotlib):\n    palette = ('Set2', 'coolwarm')\n"
)
_TWO_SUBCLASSES = (
    "from zallery.integration.matplotlib import Matplotlib\n"
    "class One(Matplotlib):\n    pass\n"
    "class Two(Matplotlib):\n    pass\n"
)


@pytest.mark.parametrize(
    ("body", "table", "message"),
    [
        ("", 'integrations = ["t8_absent:Mine"]\n', "t8_absent:Mine"),
        ("", 'integrations = "t8_one:Mine"\n', "list"),
        ("", "integrations = [3]\n", "list"),
        (_BAD_PALETTE, 'integrations = ["t8_palette:Bad"]\n', r"Bad\.palette"),
        (
            _TWO_SUBCLASSES,
            'integrations = ["t8_two:One", "t8_two:Two"]\n',
            "both subclass",
        ),
    ],
)
def test_load_config_rejects_bad_integrations(
    tmp_path: Path, body: str, table: str, message: str
) -> None:
    (tmp_path / "t8_palette.py").write_text(body)
    (tmp_path / "t8_two.py").write_text(body)
    _write_pyproject(tmp_path, table)

    with pytest.raises(ConfigError, match=message):
        load_config(tmp_path)


@pytest.mark.parametrize(
    "table", ['hook = "x"\n', "[tool.zallery.light]\n", "[tool.zallery.dark]\n"]
)
def test_load_config_points_removed_keys_to_integrations(
    tmp_path: Path, table: str
) -> None:
    _write_pyproject(tmp_path, table)

    with pytest.raises(ConfigError, match="integrations"):
        load_config(tmp_path)


def test_deps_fingerprint_tracks_the_integrations(tmp_path: Path) -> None:
    source = (
        "from zallery.integration.matplotlib import Matplotlib\n"
        "class Figures(Matplotlib):\n    cmaps = {}\n"
    )
    (tmp_path / "t8_print.py").write_text(source)
    _write_pyproject(tmp_path, "")
    stock = deps_fingerprint(load_config(tmp_path))
    _write_pyproject(tmp_path, 'integrations = ["t8_print:Figures"]\n')
    listed = deps_fingerprint(load_config(tmp_path))
    (tmp_path / "t8_print.py").write_text(source + "# changed\n")
    edited = deps_fingerprint(load_config(tmp_path))

    assert len({stock, listed, edited}) == 3


def test_load_config_reads_the_html_thumbnail_settings(tmp_path: Path) -> None:
    (tmp_path / "site.css").write_text("table { color: red; }\n")
    _write_pyproject(
        tmp_path, 'html_thumbnails = true\nhtml_thumbnail_css = ["site.css"]\n'
    )

    config = load_config(tmp_path)

    assert config.html_thumbnails is True
    assert config.html_thumbnail_css == (tmp_path.resolve() / "site.css",)


@pytest.mark.parametrize(
    ("table", "message"),
    [
        ('html_thumbnails = "yes"\n', "html_thumbnails"),
        ('html_thumbnail_css = "site.css"\n', "html_thumbnail_css"),
        ('html_thumbnail_css = ["missing.css"]\n', "missing.css"),
    ],
)
def test_load_config_rejects_bad_html_thumbnail_settings(
    tmp_path: Path, table: str, message: str
) -> None:
    _write_pyproject(tmp_path, table)

    with pytest.raises(ConfigError, match=message):
        load_config(tmp_path)


def test_deps_fingerprint_tracks_the_html_thumbnail_settings(tmp_path: Path) -> None:
    (tmp_path / "site.css").write_text("table { color: red; }\n")
    _write_pyproject(tmp_path, "")
    off = deps_fingerprint(load_config(tmp_path))
    _write_pyproject(
        tmp_path, 'html_thumbnails = true\nhtml_thumbnail_css = ["site.css"]\n'
    )
    on = deps_fingerprint(load_config(tmp_path))
    (tmp_path / "site.css").write_text("table { color: blue; }\n")
    restyled = deps_fingerprint(load_config(tmp_path))

    assert len({off, on, restyled}) == 3
