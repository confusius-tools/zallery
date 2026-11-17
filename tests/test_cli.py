"""Tests for the `zallery` command line interface."""

from __future__ import annotations

import importlib.util
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


@pytest.mark.slow
def test_cli_runs_examples_on_encrypted_kernel_sockets(tmp_path: Path) -> None:
    """ipykernel warns on its standard error when its sockets are not encrypted."""
    project, _ = _make_project(tmp_path)

    proc = _run(project)

    assert proc.returncode == 0, f"stderr: {proc.stderr}\nstdout: {proc.stdout}"
    assert "without encryption" not in proc.stderr


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
    (project / "t8_cli.py").write_text(
        "from zallery.integration.matplotlib import Matplotlib\n"
        "class Figures(Matplotlib):\n"
        '    palette = (["#ff0000"], ["#00ff00"])\n'
    )
    (project / "pyproject.toml").write_text(
        '[tool.zallery]\nintegrations = ["t8_cli:Figures"]\n'
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
@pytest.mark.skipif(find_browser() is None, reason="needs a Chromium-family browser")
def test_cli_takes_a_plotly_figure_as_thumbnail(tmp_path: Path) -> None:
    project, examples = _make_html_project(tmp_path)
    (examples / "io" / "hello.py").write_text(
        '# %% tags=["thumbnail"]\nimport plotly.graph_objects as go\n\n'
        "go.Figure(go.Bar(y=[3, 4], marker_color='#ff0000'))\n"
    )

    proc = _run(project)

    assert proc.returncode == 0, f"stderr: {proc.stderr}\nstdout: {proc.stdout}"
    for scheme in ("light", "dark"):
        thumb = examples / "_built" / "io" / f"hello_thumb_{scheme}.png"
        assert (255, 0, 0) in _colors(thumb)


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


@pytest.mark.slow
def test_cli_abort_on_error_stops_the_build_and_prints_the_traceback(
    tmp_path: Path,
) -> None:
    project, examples = _make_project(tmp_path)
    # Before `hello.py` in its section, so that it runs first.
    (examples / "io" / "boom.py").write_text(
        "# %% [markdown]\n# # Boom\n\n# %%\nraise ValueError('boom in the example')\n"
    )

    proc = _run(project, "--abort-on-error")

    assert proc.returncode == 1, f"stderr: {proc.stderr}\nstdout: {proc.stdout}"
    assert "build aborted" in proc.stderr
    assert str(examples / "io" / "boom.py") in proc.stderr
    assert "ValueError: boom in the example" in proc.stderr
    assert "Traceback (most recent call last)" in proc.stderr
    assert not (examples / "_built" / "io" / "hello.md").exists()
    assert not (examples / "index.md").exists()


@pytest.mark.slow
def test_cli_lists_the_api_objects_an_example_uses(tmp_path: Path) -> None:
    project, examples = _make_project(tmp_path)
    (project / "pyproject.toml").write_text(
        '[project]\nname = "refs-cli-pkg"\n\n'
        '[tool.zallery]\nexamples = "docs/examples"\napi_references = true\n'
    )
    (project / "refs_cli_pkg").mkdir()
    (project / "refs_cli_pkg" / "__init__.py").write_text(
        "def add(a, b):\n    return a + b\n"
    )
    (examples / "io" / "hello.py").write_text(
        "# %% [markdown]\n# # Hello\n\n# %%\nimport refs_cli_pkg\n\n"
        "# %%\nprint(refs_cli_pkg.add(1, 2))\n"
    )

    proc = _run(project)

    assert proc.returncode == 0, f"stderr: {proc.stderr}\nstdout: {proc.stdout}"
    markdown = (examples / "_built" / "io" / "hello.md").read_text(encoding="utf-8")
    assert "## API used in this example { #gallery-api }" in markdown
    assert '<autoref identifier="refs_cli_pkg.add" optional' in markdown
    assert "<code>add</code></autoref>" in markdown


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


@pytest.mark.slow
@pytest.mark.skipif(
    importlib.util.find_spec("pyvista") is None
    or importlib.util.find_spec("imageio") is None,
    reason="needs pyvista and imageio (the docs group)",
)
def test_cli_shows_pyvista_plots_and_animations(tmp_path: Path) -> None:
    """The plain pyvista calls of a notebook give a picture, or a GIF if recorded."""
    project, examples = _make_project(tmp_path)
    (examples / "io" / "hello.py").write_text(
        "# %%\nimport pyvista as pv\n\n"
        "pl = pv.Plotter()\npl.add_mesh(pv.Sphere())\n"
        "pl.open_gif('spin.gif')\n"
        "for angle in (0, 90, 180):\n"
        "    pl.camera.azimuth = angle\n    pl.write_frame()\n"
        "pl.show()\n\n"
        "# %%\npl = pv.Plotter()\npl.add_mesh(pv.Cube())\npl.show()\n"
    )

    proc = _run(project)

    assert proc.returncode == 0, f"stderr: {proc.stderr}\nstdout: {proc.stdout}"
    built = examples / "_built" / "io"
    markdown = (built / "hello.md").read_text(encoding="utf-8")
    assert '<img src="hello_cell_01_0.gif"' in markdown
    assert (built / "hello_cell_01_0.gif").read_bytes().startswith(b"GIF8")
    # The still picture is drawn again with the colors of pyvista's dark theme.
    light = mimg.imread(built / "hello_output_light" / "cell_02_0_light.png")
    dark = mimg.imread(built / "hello_output_dark" / "cell_02_0_dark.png")
    assert tuple(light[0, 0, :3]) == (1.0, 1.0, 1.0)
    assert tuple(dark[0, 0, :3]) == (0.0, 0.0, 0.0)
    # pyvista's hint about its interactive backends is not part of the page.
    assert "trame" not in markdown


@pytest.mark.slow
@pytest.mark.skipif(
    importlib.util.find_spec("trame_pyvista") is None,
    reason="needs pyvista and trame-pyvista (the docs group)",
)
def test_cli_embeds_the_interactive_scene_of_a_pyvista_plot(tmp_path: Path) -> None:
    """With trame-pyvista installed, pyvista exports each scene shown for the browser."""
    project, examples = _make_project(tmp_path)
    (examples / "io" / "hello.py").write_text(
        "# %%\nimport pyvista as pv\n\n"
        "pl = pv.Plotter()\npl.add_mesh(pv.Cube())\npl.show()\n"
    )

    proc = _run(project)

    assert proc.returncode == 0, f"stderr: {proc.stderr}\nstdout: {proc.stdout}"
    built = examples / "_built" / "io"
    markdown = (built / "hello.md").read_text(encoding="utf-8")
    assert "?fileURL=hello_cell_01_0.vtksz" in markdown
    assert "?fileURL=hello_cell_01_0_dark.vtksz" in markdown
    # Zip archives, which the viewer reads; the dark one is another drawing.
    light = (built / "hello_cell_01_0.vtksz").read_bytes()
    dark = (built / "hello_cell_01_0_dark.vtksz").read_bytes()
    assert light.startswith(b"PK")
    assert dark.startswith(b"PK")
    assert light != dark
