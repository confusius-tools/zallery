"""The PyVista integration: gallery mode, and the dark picture of each plotter shown.

`PyVista.setup` and `PyVista.retheme` run inside the gallery's ipykernel. PyVista
runs in its gallery mode, set with environment variables before an example imports
it: `Plotter.show()` displays nothing in the notebook, takes a picture and keeps
the plotter open. After each cell, the plotters shown give their output: the
picture, and the dark one in its metadata, under `metadata["image/png"]["dark"]`.

pyvista is never imported here: it is taken from `sys.modules`, once an example
has imported it.
"""

from __future__ import annotations

import base64
import io
import os
import sys
from collections.abc import Iterator, Mapping
from contextlib import ExitStack
from typing import TYPE_CHECKING, Any

from zallery._types import SCENE_MIME
from zallery.integration import Integration, Scheme

if TYPE_CHECKING:
    from IPython.core.interactiveshell import InteractiveShell

_TEXT = (
    "GetTextProperty",
    "GetTitleTextProperty",
    "GetLabelTextProperty",
    "GetAnnotationTextProperty",
    "GetCaptionTextProperty",
)
"""Methods of VTK actors giving the property of a text: its color, among others."""

_LINES = tuple(
    f"Get{axis}Axes{kind}Property"
    for axis in "XYZ"
    for kind in ("Lines", "Gridlines", "InnerGridlines")
)
"""Methods of the axes drawn by `show_bounds` giving the property of their lines."""


def _colored(renderer: Any) -> Iterator[Any]:
    """Yield what holds a text, line or surface color in a pyvista renderer.

    Parameters
    ----------
    renderer : pyvista.Renderer
        One renderer of a plotter.

    Yields
    ------
    vtkProperty or vtkProperty2D or vtkTextProperty
        A property of an actor of the renderer, with `GetColor` and `SetColor`.
    """
    props = renderer.GetViewProps()
    for index in range(props.GetNumberOfItems()):
        actor = props.GetItemAsObject(index)
        if hasattr(actor, "GetProperty"):
            yield actor.GetProperty()
        for name in _TEXT + _LINES:
            getter = getattr(actor, name, None)
            if getter is None:
                continue
            try:
                yield getter()
            except TypeError:
                # One property for each axis, on the axes of `show_bounds`.
                yield from (getter(axis) for axis in range(3))
    # The orientation axes of `add_axes` are not among the actors.
    axes = getattr(renderer, "axes_actor", None)
    for axis in "XYZ":
        caption = getattr(axes, f"Get{axis}AxisCaptionActor2D", None)
        if caption is not None:
            yield caption().GetCaptionTextProperty()


def _png_text(image: Any) -> str:
    """Return a picture as the base64 text of a PNG file, as a notebook holds it.

    Parameters
    ----------
    image : numpy.ndarray
        The pixels, as a pyvista screenshot gives them.

    Returns
    -------
    str
        The PNG file, in base64.
    """
    # Imported here: pillow comes with pyvista, which this is for.
    from PIL import Image

    png = io.BytesIO()
    Image.fromarray(image).save(png, format="png")
    return base64.b64encode(png.getvalue()).decode()


def _take(plotter: Any, *, scene: bool) -> tuple[Any, bytes | None]:
    """Take the picture of an open plotter as it is now, and export its scene.

    Parameters
    ----------
    plotter : pyvista.Plotter
        A plotter that is still open.
    scene : bool
        Whether to export the scene for the browser too, which needs
        trame-pyvista.

    Returns
    -------
    image : numpy.ndarray
        The picture.
    exported : bytes or None
        The scene as a `.vtksz` file, or `None` if not asked for.
    """
    # After a color change, a screenshot without this is the old picture.
    plotter.render()
    image = plotter.screenshot(return_img=True)
    return image, plotter.trame.export_vtksz(filename=None) if scene else None


class PyVista(Integration):
    """The look of PyVista plots: the colors of one theme swapped for another's.

    Like the swap of matplotlib figures, it changes the colors that equal those of
    the theme examples run under: the background, and the color of texts, edges,
    outlines and axes. A color an example sets itself to one of those is changed
    too; all others, and colormaps, stay.

    Attributes
    ----------
    type : str
        The class of PyVista plotters.
    themes : tuple[str, str]
        Names of the light and the dark theme, classes of `pyvista.themes`. The
        light one must be the theme examples run under: PyVista's default one.
    environment : Mapping[str, str]
        Environment PyVista reads when imported: its gallery mode, in which
        `Plotter.show()` displays nothing, takes a picture and keeps the plotter
        open. A variable the project sets itself keeps its value.
    """

    type = "pyvista.Plotter"
    themes: tuple[str, str] = ("DocumentTheme", "DarkTheme")
    environment: Mapping[str, str] = {
        "PYVISTA_OFF_SCREEN": "true",
        "PYVISTA_BUILDING_GALLERY": "true",
        "PYVISTA_JUPYTER_BACKEND": "none",
        "PYVISTA_AUTO_CLOSE": "false",
    }

    def setup(self) -> None:
        """Set `environment`, for the examples that import PyVista."""
        for name, value in self.environment.items():
            os.environ.setdefault(name, value)

    def retheme(self, plotter: Any, scheme: Scheme) -> ExitStack | None:
        """Give a plotter the colors of the dark theme, in place.

        Parameters
        ----------
        plotter : pyvista.Plotter
            A plotter that is still open.
        scheme : {"light", "dark"}
            The color scheme the next picture is for.

        Returns
        -------
        contextlib.ExitStack or None
            Context manager restoring the colors. `None` for the light scheme:
            the plotter is drawn light already.

        Raises
        ------
        ValueError
            If `themes` names no theme of PyVista. The message starts with the
            name of the class and of the attribute.
        """
        if scheme == "light":
            return None
        themes = sys.modules["pyvista"].themes
        try:
            light, dark = (getattr(themes, name)() for name in self.themes)
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError(f"{type(self).__name__}.themes: {exc}") from None
        ink = {
            light.font.color.float_rgb: dark.font.color.float_rgb,
            light.edge_color.float_rgb: dark.edge_color.float_rgb,
            light.outline_color.float_rgb: dark.outline_color.float_rgb,
        }
        restore = ExitStack()
        for renderer in plotter.renderers:
            background = renderer.background_color
            if background.float_rgb == light.background.float_rgb:
                restore.callback(setattr, renderer, "background_color", background)
                renderer.background_color = dark.background
            for colored in _colored(renderer):
                for name in ("Color", "EdgeColor"):
                    get = getattr(colored, f"Get{name}", None)
                    if get is None:
                        continue
                    color = tuple(get())
                    if color in ink:
                        setter = getattr(colored, f"Set{name}")
                        restore.callback(setter, *color)
                        setter(*ink[color])
        return restore

    def _show_plots(self) -> None:
        """Display the picture of each plotter shown by the cell that just ran.

        A plotter that records a GIF shows the GIF, others their last picture, as
        pyvista's own sphinx-gallery scraper does. Plotters not shown yet are left
        for a later cell; those shown are closed, which also ends a recording.

        The light picture is the one `show()` took, unless `retheme` has something
        to change for the light scheme. The picture is taken again under the dark
        look, and goes in the metadata of the output. A GIF has one rendering: its
        frames are recorded already.

        With trame-pyvista installed, pyvista also exports the scene of each
        plotter it shows, for a browser to draw. The light and the dark scene go
        in the output of the picture and in its metadata, under `SCENE_MIME`.

        A plot is not lost for a look that fails: its picture as `show()` took it
        is displayed, the plotter is closed, and the error is raised once every
        plotter is handled, for IPython to report.
        """
        pyvista = sys.modules.get("pyvista")
        if pyvista is None:
            return
        from IPython.display import Image, display

        plotters = pyvista.plotting.plotter._ALL_PLOTTERS
        failures: list[Exception] = []
        for key, plotter in list(plotters.items()):
            # `show()` takes the picture; a project may have it close the plotter too.
            if plotter.last_image is None and not plotter._closed:
                continue
            del plotters[key]
            if plotter._gif_filename is not None:
                # Closing ends the recording.
                plotter.close()
                display(Image(filename=plotter._gif_filename))
            elif plotter.last_image is not None:
                image = plotter.last_image
                scene = getattr(plotter, "last_vtksz", None)
                export = scene is not None
                metadata: dict[str, dict[str, str]] = {}
                if not plotter._closed:
                    try:
                        look = self.retheme(plotter, "light")
                        if look is not None:
                            with look:
                                image, scene = _take(plotter, scene=export)
                        look = self.retheme(plotter, "dark")
                        if look is not None:
                            with look:
                                dark, dark_scene = _take(plotter, scene=export)
                            metadata["image/png"] = {"dark": _png_text(dark)}
                            if dark_scene is not None:
                                metadata[SCENE_MIME] = {
                                    "dark": base64.b64encode(dark_scene).decode()
                                }
                    except Exception as failure:  # noqa: BLE001
                        # Whatever the `retheme` of a subclass raises: raised
                        # below, once the picture is shown and the plotter closed.
                        failures.append(failure)
                    plotter.close()
                data = {"image/png": _png_text(image)}
                if scene is not None:
                    data[SCENE_MIME] = base64.b64encode(scene).decode()
                display(data, metadata=metadata, raw=True)
        if failures:
            raise failures[0]

    def _install(self, shell: InteractiveShell) -> None:
        """Have the kernel show, after each cell, the plotters the cell showed.

        `show()` displays nothing in gallery mode, so no formatter of IPython
        sees a plotter. This is the capture of PyVista plots, in place of the
        generic one of `Integration`.

        Parameters
        ----------
        shell : IPython.core.interactiveshell.InteractiveShell
            The shell of the kernel.
        """
        shell.events.register("post_execute", self._show_plots)
