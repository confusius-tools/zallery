"""Tests for zallery.config."""

from __future__ import annotations

from pathlib import Path

import pytest

from zallery.config import ConfigError, deps_fingerprint, load_config


def _write_pyproject(root: Path, table: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text(f"[tool.zallery]\n{table}\n")


def test_load_config_resolves_paths_under_the_project_root(tmp_path: Path) -> None:
    _write_pyproject(
        tmp_path,
        'examples = "site/examples"\ncache = "build/.cache"\n'
        'binder_repo = "me/repo"\nhook = "conf.hooks"\nfingerprint = ["lock.txt"]\n',
    )

    config = load_config(tmp_path)

    assert config.root == tmp_path.resolve()
    assert config.examples == tmp_path.resolve() / "site" / "examples"
    assert config.built == tmp_path.resolve() / "site" / "examples" / "_built"
    assert config.cache == tmp_path.resolve() / "build" / ".cache"
    assert config.binder_repo == "me/repo"
    assert config.hook == "conf.hooks"
    assert config.hook_file == tmp_path.resolve() / "conf" / "hooks.py"
    assert config.fingerprint_files == (tmp_path.resolve() / "lock.txt",)


def test_load_config_defaults(tmp_path: Path) -> None:
    _write_pyproject(tmp_path, "")

    config = load_config(tmp_path)

    assert config.examples == tmp_path.resolve() / "docs" / "examples"
    assert config.built == config.examples / "_built"
    assert config.cache == tmp_path.resolve() / ".gallery-cache"
    assert config.binder_repo is None
    assert config.hook is None
    assert config.hook_file is None
    assert config.fingerprint_files == (tmp_path.resolve() / "uv.lock",)
    assert config.matplotlib_palettes is None


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


def test_deps_fingerprint_tracks_lockfile_hook_and_config(tmp_path: Path) -> None:
    _write_pyproject(tmp_path, 'hook = "hooks"\n')
    (tmp_path / "uv.lock").write_text("v1\n")
    (tmp_path / "hooks.py").write_text("def gallery_retheme(fig, theme): pass\n")
    baseline = deps_fingerprint(load_config(tmp_path))

    (tmp_path / "uv.lock").write_text("v2\n")
    after_lock = deps_fingerprint(load_config(tmp_path))
    (tmp_path / "hooks.py").write_text("def gallery_retheme(fig, theme): ...\n")
    after_hook = deps_fingerprint(load_config(tmp_path))
    _write_pyproject(tmp_path, 'hook = "hooks"\nbinder_repo = "me/repo"\n')
    after_config = deps_fingerprint(load_config(tmp_path))

    assert len({baseline, after_lock, after_hook, after_config}) == 4
    assert deps_fingerprint(load_config(tmp_path)) == after_config


def test_load_config_resolves_matplotlib_palettes_to_hex_colors(tmp_path: Path) -> None:
    """A palette is a list of colors or the name of a listed matplotlib colormap."""
    _write_pyproject(
        tmp_path,
        '[tool.zallery.light]\nmatplotlib.palette = ["red", "#0000ff"]\n'
        '[tool.zallery.dark]\nmatplotlib.palette = "Set2"\n',
    )

    palettes = load_config(tmp_path).matplotlib_palettes

    assert palettes == (
        ("#ff0000", "#0000ff"),
        (
            "#66c2a5",
            "#fc8d62",
            "#8da0cb",
            "#e78ac3",
            "#a6d854",
            "#ffd92f",
            "#e5c494",
            "#b3b3b3",
        ),
    )


def test_load_config_fills_in_the_palette_not_given(tmp_path: Path) -> None:
    """Light defaults to matplotlib's own cycle, dark to the light palette."""
    _write_pyproject(tmp_path, '[tool.zallery.dark]\nmatplotlib.palette = "tab20"\n')
    light, dark = load_config(tmp_path).matplotlib_palettes or ((), ())
    assert light[:2] == ("#1f77b4", "#ff7f0e")
    assert len(light) == 10
    assert len(dark) == 20

    _write_pyproject(tmp_path, '[tool.zallery.light]\nmatplotlib.palette = "Dark2"\n')
    light, dark = load_config(tmp_path).matplotlib_palettes or ((), ())
    assert light[0] == "#1b9e77"
    assert dark == light


@pytest.mark.parametrize(
    ("tables", "message"),
    [
        ('[tool.zallery.light]\nmatplotlib.palette = "NoSuchMap"\n', "NoSuchMap"),
        # A continuous colormap has no list of colors to cycle through.
        ('[tool.zallery.light]\nmatplotlib.palette = "coolwarm"\n', "coolwarm"),
        ('[tool.zallery.light]\nmatplotlib.palette = ["red", "nocolor"]\n', "nocolor"),
        ("[tool.zallery.light]\nmatplotlib.palette = 3\n", "palette"),
        ("[tool.zallery.light]\nmatplotlib.palette = []\n", "palette"),
        ('[tool.zallery.light]\nseaborn.palette = "deep"\n', "seaborn"),
        ('[tool.zallery.dark]\nmatplotlib.cmap = "viridis"\n', "cmap"),
        # Eight colors cannot pair with the ten of matplotlib's default cycle.
        ('[tool.zallery.dark]\nmatplotlib.palette = "Set2"\n', "fewer"),
    ],
)
def test_load_config_rejects_bad_palettes(
    tmp_path: Path, tables: str, message: str
) -> None:
    _write_pyproject(tmp_path, tables)

    with pytest.raises(ConfigError, match=message):
        load_config(tmp_path)


def test_deps_fingerprint_tracks_matplotlib_palettes(tmp_path: Path) -> None:
    _write_pyproject(tmp_path, "")
    baseline = deps_fingerprint(load_config(tmp_path))

    _write_pyproject(tmp_path, '[tool.zallery.light]\nmatplotlib.palette = "Dark2"\n')

    assert deps_fingerprint(load_config(tmp_path)) != baseline
