"""Tests for zallery.execute."""

from __future__ import annotations

import base64
import importlib.util
import io
import socket
import sys
from pathlib import Path

import pytest
from matplotlib.image import imread

from zallery import execute
from zallery.execute import ExampleError, execute_example, find_kernel_ports


def test_execute_runs_jupytext_py_and_returns_executed_nb(tmp_path: Path) -> None:
    src = tmp_path / "ex.py"
    src.write_text("# %% [markdown]\n# # Hello\n\n# %%\nx = 6 * 7\nprint(x)\n")

    nb, seconds = execute_example(src, timeout=60)

    assert seconds > 0
    code_cells = [c for c in nb.cells if c.cell_type == "code"]
    assert len(code_cells) == 1
    streams = [
        out
        for out in code_cells[0].outputs
        if out.get("output_type") == "stream" and out.get("name") == "stdout"
    ]
    assert any("42" in out.get("text", "") for out in streams)


def test_execute_uses_current_python_interpreter(tmp_path: Path) -> None:
    """The kernel must be the same Python that runs the script."""
    src = tmp_path / "ex.py"
    src.write_text(f"# %%\nimport sys\nassert sys.executable == {sys.executable!r}\n")
    # Will raise if the kernel is some other interpreter.
    execute_example(src, timeout=60)


def test_execute_captures_cell_error_as_output_and_continues(tmp_path: Path) -> None:
    """A failing cell records its traceback and execution continues to the next cell.

    The renderer (`zallery.render`) already inlines `error` outputs into
    the rendered Markdown the same way a normal Jupyter notebook would, so the
    executor must not abort on the first failing cell.
    """
    src = tmp_path / "broken.py"
    src.write_text("# %%\nraise RuntimeError('boom')\n\n# %%\nprint('after')\n")

    nb, _ = execute_example(src, timeout=60)

    code_cells = [c for c in nb.cells if c.cell_type == "code"]
    assert len(code_cells) == 2

    error_outputs = [
        out for out in code_cells[0].outputs if out.get("output_type") == "error"
    ]
    assert error_outputs, "the failing cell did not produce an error output"
    assert error_outputs[0].get("ename") == "RuntimeError"
    assert "boom" in error_outputs[0].get("evalue", "")

    after_streams = [
        out
        for out in code_cells[1].outputs
        if out.get("output_type") == "stream" and out.get("name") == "stdout"
    ]
    assert any("after" in out.get("text", "") for out in after_streams)


def test_execute_attaches_dark_rendering_to_figure_outputs(tmp_path: Path) -> None:
    """One run yields both themes: the dark PNG rides along in the output metadata."""
    src = tmp_path / "ex.py"
    src.write_text("# %%\nimport matplotlib.pyplot as plt\n_ = plt.plot([1, 2, 3])\n")

    nb, _ = execute_example(src, timeout=120)

    code_cells = [c for c in nb.cells if c.cell_type == "code"]
    assert len(code_cells) == 1, "the injected setup cell must not leak out"
    images = [
        out
        for out in code_cells[0].outputs
        if out.get("output_type") == "display_data" and "image/png" in out["data"]
    ]
    assert len(images) == 1
    dark = images[0]["metadata"]["image/png"]["dark"]
    assert isinstance(dark, str)
    assert dark != images[0]["data"]["image/png"]


def test_execute_raises_when_kernel_setup_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A broken setup cell must not silently produce light-only pages."""
    monkeypatch.setattr(
        execute, "_setup_source", lambda *_: "raise RuntimeError('no theme')"
    )
    src = tmp_path / "ex.py"
    src.write_text("# %%\nprint('hi')\n")

    with pytest.raises(RuntimeError, match="no theme"):
        execute_example(src, timeout=60)


def test_execute_binds_kernel_ports_below_the_ephemeral_range(tmp_path: Path) -> None:
    """Kernel ports stay out of the range the OS hands to outgoing connections.

    Ports drawn from that range can be taken by a client connection between
    jupyter_client choosing them and the kernel binding them, which surfaced in CI
    as a heartbeat socket failing with "Address already in use".
    """
    src = tmp_path / "ex.py"
    src.write_text(
        "# %%\n"
        "from ipykernel.kernelapp import IPKernelApp\n"
        "app = IPKernelApp.instance()\n"
        "print(app.shell_port, app.iopub_port, app.stdin_port, "
        "app.control_port, app.hb_port)\n"
    )

    nb, _ = execute_example(src, timeout=60)

    stdout = "".join(
        out.get("text", "")
        for out in nb.cells[0].outputs
        if out.get("output_type") == "stream" and out.get("name") == "stdout"
    )
    ports = [int(token) for token in stdout.split()]
    assert len(ports) == 5
    assert len(set(ports)) == 5
    assert all(10000 <= port < 32768 for port in ports)


def test_find_kernel_ports_skips_ports_in_use(monkeypatch: pytest.MonkeyPatch) -> None:
    taken = find_kernel_ports(1)[0]
    held = socket.socket()
    held.bind(("127.0.0.1", taken))
    # Start the scan on the held port so the skip is exercised deterministically.
    monkeypatch.setattr(execute.random, "randrange", lambda *_: taken)
    try:
        ports = find_kernel_ports()
    finally:
        held.close()

    assert taken not in ports
    assert len(set(ports)) == 5
    assert all(taken < port < 32768 for port in ports)


@pytest.mark.slow
def test_execute_runs_the_project_integration_in_the_kernel(tmp_path: Path) -> None:
    """A class named in `integrations` is imported from `root` in the kernel."""
    marker = tmp_path / "calls.txt"
    (tmp_path / "t8_kernel.py").write_text(
        "from pathlib import Path\n"
        "from zallery.integration.matplotlib import Matplotlib\n"
        "class Recording(Matplotlib):\n"
        "    def retheme(self, fig, scheme):\n"
        f"        with Path({str(marker)!r}).open('a') as f:\n"
        "            f.write(scheme + '\\n')\n"
        "        return super().retheme(fig, scheme)\n"
    )
    src = tmp_path / "ex.py"
    src.write_text("# %%\nimport matplotlib.pyplot as plt\n_ = plt.plot([1, 2, 3])\n")

    execute_example(
        src, timeout=120, integrations=["t8_kernel:Recording"], root=tmp_path
    )

    assert marker.read_text() == "light\ndark\n"


@pytest.mark.slow
def test_execute_gives_a_new_display_its_dark_variant(tmp_path: Path) -> None:
    """A class with `type` and `retheme` is all a display Zallery does not know needs."""
    (tmp_path / "t8_cards.py").write_text(
        "from contextlib import ExitStack\n"
        "from zallery import Integration\n"
        "class Cards(Integration):\n"
        "    type = '__main__.Card'\n"
        "    def retheme(self, card, scheme):\n"
        "        if scheme == 'light':\n            return None\n"
        "        stack = ExitStack()\n"
        "        stack.callback(setattr, card, 'color', card.color)\n"
        "        card.color = 'white'\n"
        "        return stack\n"
    )
    src = tmp_path / "ex.py"
    src.write_text(
        "# %%\nclass Card:\n    color = 'black'\n"
        "    def _repr_html_(self):\n"
        "        return f'<p style=\"color:{self.color}\">card</p>'\n\nCard()\n"
    )

    notebook, _ = execute_example(
        src, timeout=120, integrations=["t8_cards:Cards"], root=tmp_path
    )

    (output,) = notebook.cells[0].outputs
    assert "color:black" in output.data["text/html"]
    assert "color:white" in output.metadata["text/html"]["dark"]


@pytest.mark.slow
def test_execute_gives_a_plotly_figure_its_dark_figure_however_it_is_shown(
    tmp_path: Path,
) -> None:
    src = tmp_path / "ex.py"
    src.write_text(
        "# %%\nimport plotly.graph_objects as go\n\n"
        "fig = go.Figure(go.Bar(y=[3, 4]))\nfig.show()\nfig\n"
    )

    notebook, _ = execute_example(src, timeout=120)

    mime = "application/vnd.plotly.v1+json"
    outputs = [o for o in notebook.cells[0].outputs if mime in o.get("data", {})]
    assert len(outputs) == 2
    for output in outputs:
        light = output.data[mime]["layout"]["template"]["layout"]
        dark = output.metadata[mime]["dark"]["layout"]["template"]["layout"]
        assert light["paper_bgcolor"] == dark["paper_bgcolor"] == "rgba(0,0,0,0)"
        assert dark["font"]["color"] != light["font"]["color"]


@pytest.mark.slow
@pytest.mark.skipif(
    importlib.util.find_spec("pyvista") is None, reason="needs pyvista (the docs group)"
)
def test_execute_keeps_a_pyvista_picture_whose_dark_look_fails(tmp_path: Path) -> None:
    """A plot is not lost for its dark look: the light picture shows, with the error."""
    (tmp_path / "t11_pyvista.py").write_text(
        "from zallery.integration.pyvista import PyVista\n"
        "class Bad(PyVista):\n"
        "    themes = ('DocumentTheme', 'NoSuchTheme')\n"
    )
    src = tmp_path / "ex.py"
    src.write_text(
        "# %%\nimport pyvista as pv\n\n"
        "plotter = pv.Plotter()\n_ = plotter.add_mesh(pv.Sphere())\nplotter.show()\n"
    )

    notebook, _ = execute_example(
        src, timeout=120, integrations=["t11_pyvista:Bad"], root=tmp_path
    )

    outputs = notebook.cells[0].outputs
    pictures = [o for o in outputs if "image/png" in o.get("data", {})]
    assert len(pictures) == 1
    assert "dark" not in pictures[0].metadata.get("image/png", {})
    # IPython reports what a callback raises: the cell shows the traceback.
    reported = "".join("".join(o.get("traceback", [])) for o in outputs)
    assert "Bad.themes" in reported


@pytest.mark.slow
@pytest.mark.skipif(
    importlib.util.find_spec("pyvista") is None, reason="needs pyvista (the docs group)"
)
def test_execute_takes_a_pyvista_picture_again_for_a_light_look(tmp_path: Path) -> None:
    """A light look that changes a plotter replaces the picture `show()` took."""
    (tmp_path / "t12_pyvista.py").write_text(
        "from contextlib import ExitStack\n"
        "from zallery.integration.pyvista import PyVista\n"
        "class Pure(PyVista):\n"
        "    def retheme(self, plotter, scheme):\n"
        "        renderer, restore = plotter.renderer, ExitStack()\n"
        "        color = renderer.background_color\n"
        "        restore.callback(setattr, renderer, 'background_color', color)\n"
        "        renderer.background_color = 'red' if scheme == 'light' else 'blue'\n"
        "        return restore\n"
    )
    src = tmp_path / "ex.py"
    src.write_text(
        "# %%\nimport pyvista as pv\n\n"
        "plotter = pv.Plotter()\n_ = plotter.add_mesh(pv.Sphere())\nplotter.show()\n"
    )

    notebook, _ = execute_example(
        src, timeout=120, integrations=["t12_pyvista:Pure"], root=tmp_path
    )

    (picture,) = [
        o for o in notebook.cells[0].outputs if "image/png" in o.get("data", {})
    ]
    for png, color in [
        (picture.data["image/png"], (1, 0, 0)),
        (picture.metadata["image/png"]["dark"], (0, 0, 1)),
    ]:
        corner = imread(io.BytesIO(base64.b64decode(png)))[0, 0, :3]
        assert tuple(corner) == pytest.approx(color, abs=0.01)


@pytest.mark.slow
def test_execute_stops_at_the_first_cell_that_raises_when_asked(tmp_path: Path) -> None:
    marker = tmp_path / "a-later-cell-ran"
    src = tmp_path / "boom.py"
    src.write_text(
        "# %%\nprint('before')\n\n"
        "# %%\nraise ValueError('boom in the example')\n\n"
        f"# %%\nopen({str(marker)!r}, 'w').close()\n"
    )

    with pytest.raises(ExampleError) as raised:
        execute_example(src, timeout=60, abort_on_error=True)

    assert raised.value.source == src
    assert "ValueError: boom in the example" in raised.value.traceback
    assert "----> 1 raise ValueError" in raised.value.traceback
    # The colors of the kernel's traceback are for a terminal that reads them.
    assert "\x1b" not in raised.value.traceback
    assert str(src) in str(raised.value)
    assert raised.value.traceback in str(raised.value)
    assert not marker.exists()


@pytest.mark.slow
def test_execute_lets_a_cell_tagged_raises_exception_raise(tmp_path: Path) -> None:
    src = tmp_path / "expected.py"
    src.write_text(
        '# %% tags=["raises-exception"]\nraise ValueError("expected")\n\n'
        "# %%\nprint('after')\n"
    )

    notebook, _ = execute_example(src, timeout=60, abort_on_error=True)

    assert notebook.cells[0].outputs[0]["output_type"] == "error"
    assert notebook.cells[1].outputs[0]["text"] == "after\n"


@pytest.mark.slow
def test_execute_reports_a_failed_kernel_setup_as_such_when_aborting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        execute, "_setup_source", lambda *_: "raise RuntimeError('no theme')"
    )
    src = tmp_path / "ex.py"
    src.write_text("# %%\nprint('hi')\n")

    with pytest.raises(RuntimeError, match="(?s)Gallery kernel setup failed.*no theme"):
        execute_example(src, timeout=60, abort_on_error=True)


_REFERENCES_MIME = "application/vnd.zallery.references+json"


def _write_package(root: Path, name: str) -> None:
    (root / name).mkdir()
    (root / name / "__init__.py").write_text(f"from {name}._impl import add\n")
    (root / name / "_impl.py").write_text("def add(a, b):\n    return a + b\n")


@pytest.mark.slow
def test_execute_reports_the_objects_of_the_package_each_cell_uses(
    tmp_path: Path,
) -> None:
    _write_package(tmp_path, "refs_kernel_pkg")
    src = tmp_path / "ex.py"
    src.write_text(
        "# %%\nimport json\nimport refs_kernel_pkg as rk\n\n"
        "# %%\nprint(rk.add(1, 2))\n\n"
        "# %%\nprint(json.dumps([1]))\n"
    )

    notebook, _ = execute_example(
        src, timeout=60, root=tmp_path, api_package="refs_kernel_pkg"
    )

    reported = [
        [out["data"][_REFERENCES_MIME] for out in cell.outputs if "data" in out]
        for cell in notebook.cells
    ]
    assert reported == [[], [{"refs_kernel_pkg._impl.add": "add"}], []]
    # The report comes after the outputs of the cell itself.
    assert notebook.cells[1].outputs[0]["text"] == "3\n"


@pytest.mark.slow
def test_execute_reports_no_object_without_a_package(tmp_path: Path) -> None:
    _write_package(tmp_path, "refs_kernel_off_pkg")
    src = tmp_path / "ex.py"
    src.write_text("# %%\nimport refs_kernel_off_pkg as rk\nprint(rk.add(1, 2))\n")

    notebook, _ = execute_example(src, timeout=60, root=tmp_path)

    assert [out["output_type"] for out in notebook.cells[0].outputs] == ["stream"]
