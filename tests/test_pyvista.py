"""Tests for zallery.integration.pyvista."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from zallery.integration.pyvista import PyVista


def test_importing_the_module_does_not_import_pyvista() -> None:
    code = "import sys, zallery.integration.pyvista; sys.exit('pyvista' in sys.modules)"
    assert subprocess.run([sys.executable, "-c", code], check=False).returncode == 0


def test_setup_keeps_a_variable_the_project_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYVISTA_OFF_SCREEN", "mine")
    monkeypatch.delenv("PYVISTA_BUILDING_GALLERY", raising=False)
    PyVista().setup()
    assert os.environ["PYVISTA_OFF_SCREEN"] == "mine"
    assert os.environ["PYVISTA_BUILDING_GALLERY"] == "true"


def test_retheme_swaps_the_theme_colors_and_restores_them() -> None:
    pyvista = pytest.importorskip("pyvista", reason="needs the docs group")

    plotter = pyvista.Plotter(off_screen=True)
    plotter.add_mesh(pyvista.Sphere(), show_edges=True)
    light = pyvista.themes.DocumentTheme().background.float_rgb
    dark = pyvista.themes.DarkTheme().background.float_rgb
    integration = PyVista()
    try:
        assert integration.retheme(plotter, "light") is None
        look = integration.retheme(plotter, "dark")
        assert look is not None
        with look:
            assert plotter.renderers[0].background_color.float_rgb == dark
        assert plotter.renderers[0].background_color.float_rgb == light
    finally:
        plotter.close()


def test_an_unknown_theme_names_the_attribute() -> None:
    pyvista = pytest.importorskip("pyvista", reason="needs the docs group")

    class Bad(PyVista):
        themes = ("DocumentTheme", "NoSuchTheme")

    plotter = pyvista.Plotter(off_screen=True)
    try:
        with pytest.raises(ValueError, match=r"^Bad\.themes"):
            Bad().retheme(plotter, "dark")
    finally:
        plotter.close()


def test_a_subclass_may_name_another_dark_theme() -> None:
    pyvista = pytest.importorskip("pyvista", reason="needs the docs group")

    class ParaView(PyVista):
        themes = ("DocumentTheme", "ParaViewTheme")

    plotter = pyvista.Plotter(off_screen=True)
    light = plotter.renderers[0].background_color.float_rgb
    try:
        look = ParaView().retheme(plotter, "dark")
        assert look is not None
        with look:
            assert (
                plotter.renderers[0].background_color.float_rgb
                == pyvista.themes.ParaViewTheme().background.float_rgb
                != light
            )
        assert plotter.renderers[0].background_color.float_rgb == light
    finally:
        plotter.close()
