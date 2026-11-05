"""Tests for the `zallery` command line interface."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import matplotlib.image as mimg
import pytest

from zallery.thumbnail import find_browser


def _make_project(tmp_path: Path) -> tuple[Path, Path]:
    """Return a mini-project with a `[tool.zallery]` table and one example."""
    project = tmp_path / "project"
    examples = project / "docs" / "examples"
    (examples / "_assets").mkdir(parents=True)
    (examples / "_assets" / "default_thumb.png").write_bytes(b"\x89PNG\r\n")
    (examples / "io").mkdir()
    (examples / "io" / "_section.md").write_text("## Input/Output\n\nIO.\n")
    (examples / "io" / "hello.py").write_text(
        "# %% [markdown]\n# # Hello ┏\n\n# %%\nprint('hi')\n", encoding="utf-8"
    )
    (project / "pyproject.toml").write_text(
        '[tool.zallery]\nexamples = "docs/examples"\n'
    )
    (project / "uv.lock").write_text("# placeholder\n")
    return project, examples


def _run(
    cwd: Path, *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "zallery", *args],
        cwd=cwd,
        env={**os.environ, **(env or {})},
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.slow
def test_cli_builds_the_gallery_of_the_enclosing_project(tmp_path: Path) -> None:
    """Run from a subdirectory, the CLI finds the table upwards and builds."""
    project, examples = _make_project(tmp_path)

    proc = _run(examples / "io")

    assert proc.returncode == 0, f"stderr: {proc.stderr}\nstdout: {proc.stdout}"
    markdown = (examples / "_built" / "io" / "hello.md").read_text(encoding="utf-8")
    assert "# Hello ┏" in markdown
    assert '<div class="gallery-output" markdown>' in markdown
    assert (examples / "index.md").is_file()
    assert (project / ".gallery-cache").is_dir()


def _colors(png: Path) -> set[tuple[int, ...]]:
    """Return the RGB colors present in an image, as 0-255 integers."""
    pixels = (mimg.imread(png)[..., :3] * 255).round().astype(int)
    return {tuple(int(v) for v in pixel) for pixel in pixels.reshape(-1, 3)}


@pytest.mark.slow
def test_cli_draws_each_page_with_its_matplotlib_palette(tmp_path: Path) -> None:
    """The light palette is the color cycle; the dark page shows its counterpart."""
    project, examples = _make_project(tmp_path)
    (examples / "io" / "hello.py").write_text(
        "# %%\nimport matplotlib.pyplot as plt\n_ = plt.plot([1, 2, 3], linewidth=20)\n"
    )
    (project / "pyproject.toml").write_text(
        "[tool.zallery]\n"
        '[tool.zallery.light]\nmatplotlib.palette = ["#ff0000"]\n'
        '[tool.zallery.dark]\nmatplotlib.palette = ["#00ff00"]\n'
    )

    proc = _run(project)

    assert proc.returncode == 0, f"stderr: {proc.stderr}\nstdout: {proc.stdout}"
    built = examples / "_built" / "io"
    light = _colors(built / "hello_output_light" / "cell_01_0_light.png")
    dark = _colors(built / "hello_output_dark" / "cell_01_0_dark.png")
    assert (255, 0, 0) in light
    assert (0, 255, 0) not in light
    assert (0, 255, 0) in dark
    assert (255, 0, 0) not in dark


@pytest.mark.slow
def test_cli_draws_a_plotly_figure_on_its_page(tmp_path: Path) -> None:
    project, examples = _make_project(tmp_path)
    (examples / "io" / "hello.py").write_text(
        "# %%\nimport plotly.graph_objects as go\n\ngo.Figure(go.Bar(y=[3, 4]))\n"
    )

    proc = _run(project)

    assert proc.returncode == 0, f"stderr: {proc.stderr}\nstdout: {proc.stdout}"
    markdown = (examples / "_built" / "io" / "hello.md").read_text(encoding="utf-8")
    assert '<div id="zallery-plotly-1-0" class="gallery-plotly"' in markdown


def _make_html_project(tmp_path: Path) -> tuple[Path, Path]:
    """Return a project asking for HTML thumbnails, with one HTML-only example."""
    project, examples = _make_project(tmp_path)
    (examples / "io" / "hello.py").write_text(
        '# %% [markdown]\n# # Hello\n\n# %% tags=["thumbnail"]\n'
        "from IPython.display import HTML\n\nHTML('<b>hi</b>')\n"
    )
    (project / "pyproject.toml").write_text("[tool.zallery]\nhtml_thumbnails = true\n")
    return project, examples


@pytest.mark.slow
@pytest.mark.skipif(find_browser() is None, reason="needs a Chromium-family browser")
def test_cli_takes_html_thumbnails_when_switched_on(tmp_path: Path) -> None:
    project, examples = _make_html_project(tmp_path)

    proc = _run(project)

    assert proc.returncode == 0, f"stderr: {proc.stderr}\nstdout: {proc.stdout}"
    light = examples / "_built" / "io" / "hello_thumb_light.png"
    dark = examples / "_built" / "io" / "hello_thumb_dark.png"
    assert _colors(light) != _colors(dark)
    index = (examples / "index.md").read_text(encoding="utf-8")
    assert "_built/io/hello_thumb_light.png#only-light" in index


@pytest.mark.slow
def test_cli_builds_without_a_browser_for_html_thumbnails(tmp_path: Path) -> None:
    """No browser costs the thumbnails and a warning, not the build."""
    project, examples = _make_html_project(tmp_path)

    proc = _run(project, env={"ZALLERY_BROWSER": str(tmp_path / "missing-browser")})

    assert proc.returncode == 0, f"stderr: {proc.stderr}\nstdout: {proc.stdout}"
    assert "ZALLERY_BROWSER" in proc.stderr
    assert not (examples / "_built" / "io" / "hello_thumb_light.png").exists()
    index = (examples / "index.md").read_text(encoding="utf-8")
    assert "_assets/default_thumb.svg#only-light" in index


def test_cli_no_run_renders_every_example_without_executing(tmp_path: Path) -> None:
    """`--no-run` renders code and prose only, and caches nothing."""
    project, examples = _make_project(tmp_path)

    proc = _run(project, "--no-run")

    assert proc.returncode == 0, f"stderr: {proc.stderr}\nstdout: {proc.stdout}"
    markdown = (examples / "_built" / "io" / "hello.md").read_text(encoding="utf-8")
    assert "print('hi')" in markdown
    assert "gallery-output" not in markdown
    assert "[not run]" in proc.stdout
    assert not list((project / ".gallery-cache").glob("**/hello"))


def test_cli_no_run_rejects_example_paths(tmp_path: Path) -> None:
    project, examples = _make_project(tmp_path)

    proc = _run(project, "--no-run", str(examples / "io" / "hello.py"))

    assert proc.returncode == 2
    assert "--no-run cannot be combined" in proc.stderr


def test_cli_returns_1_when_examples_dir_missing(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text("[tool.zallery]\n")

    proc = _run(project)

    assert proc.returncode == 1
    assert "No examples directory" in proc.stderr


def test_cli_returns_2_without_configuration(tmp_path: Path) -> None:
    proc = _run(tmp_path)

    assert proc.returncode == 2
    assert "[tool.zallery]" in proc.stderr
