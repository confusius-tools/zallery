"""The plotly integration: the template a figure is drawn with in each scheme.

`Plotly.retheme` runs inside the gallery's ipykernel. In a kernel, plotly's default
renderer sends a figure as its mime type alone, with no HTML or text: the figure
as JSON, which `render.py` draws on the page. This module gives each such output
the figure of both schemes: the light one as the payload of the mime type, the
dark one in its metadata, under `metadata[MIME]["dark"]`.

plotly is imported inside the functions only, once an example has shown a figure.
"""

from __future__ import annotations

import copy
import json
import warnings
from contextlib import ExitStack
from typing import TYPE_CHECKING, Any

from zallery.integration import Integration, Scheme

if TYPE_CHECKING:
    from IPython.core.interactiveshell import InteractiveShell

MIME = "application/vnd.plotly.v1+json"
"""Mime type of a plotly figure, which plotly's default renderer in a kernel sends."""

_CLEAR = {"layout": {"paper_bgcolor": "rgba(0,0,0,0)"}}
"""Template that drops the paper background, so that a figure sits on the page's."""


class Plotly(Integration):
    """The look of plotly figures: a template merged into the figure's own.

    Both schemes drop the paper background, so the figure sits on the page.
    Colors set on the figure itself, not by its template, are the same in both
    schemes.

    Attributes
    ----------
    type : str
        The class of plotly figures.
    template : tuple[str or None, str or None]
        Name of the plotly template merged into the figure's own for the light
        and for the dark scheme. `None` merges none.
    """

    type = "plotly.graph_objects.Figure"
    template: tuple[str | None, str | None] = (None, "plotly_dark")

    def retheme(self, fig: Any, scheme: Scheme) -> ExitStack:
        """Give a figure the template of a color scheme, in place.

        Parameters
        ----------
        fig : plotly.graph_objects.Figure
            The figure to change.
        scheme : {"light", "dark"}
            The color scheme to draw for.

        Returns
        -------
        contextlib.ExitStack
            Context manager putting the figure's own template back.

        Raises
        ------
        ValueError
            If plotly has no template of the name `template` gives. The message
            starts with the name of the class and of the attribute.
        """
        from plotly.io import templates

        own = fig.layout.template
        parts: list[Any] = [own]
        named = self.template[0 if scheme == "light" else 1]
        if named is not None:
            try:
                templates[named]
            except KeyError:
                raise ValueError(
                    f"{type(self).__name__}.template: plotly has no template "
                    f"named {named!r}."
                ) from None
            parts.append(named)
        restore = ExitStack()
        restore.callback(setattr, fig.layout, "template", own)
        fig.layout.template = templates.merge_templates(*parts, _CLEAR)
        return restore

    def _both(self, data: dict[str, Any], metadata: dict[str, Any]) -> None:
        """Give the output of a plotly figure the figure of each scheme, in place.

        Parameters
        ----------
        data : dict[str, Any]
            The mime bundle of a displayed figure. Its figure is replaced by the
            light one.
        metadata : dict[str, Any]
            The metadata of the bundle. It gets the dark figure, under
            `metadata[MIME]["dark"]`.

        Warns
        -----
        UserWarning
            If plotly rejects the figure, which can be shown with
            `validate=False`. The output is then left as sent: the figure is
            drawn as it is in both schemes.
        """
        import plotly.graph_objects as go
        import plotly.io as pio

        payload = data[MIME]
        try:
            # A copy: plotly takes the type out of each trace and does not put
            # it back when it raises.
            fig = go.Figure(copy.deepcopy(payload))
        except ValueError:
            warnings.warn(
                "Zallery: plotly rejects this figure, so it is shown as it is in"
                " both color schemes.",
                stacklevel=2,
            )
            return
        if "template" not in (payload.get("layout") or {}):
            # A figure shown without template: plotly gave this copy its default.
            fig.layout.template = None
        shown: dict[str, dict[str, Any]] = {}
        for scheme in ("light", "dark"):
            with self.retheme(fig, scheme):
                # What is not of the figure (its config) is kept as sent.
                shown[scheme] = {
                    **payload,
                    **json.loads(pio.to_json(fig, validate=False)),
                }
        data[MIME] = shown["light"]
        metadata.setdefault(MIME, {})["dark"] = shown["dark"]

    def _install(self, shell: InteractiveShell) -> None:
        """Have the kernel send every displayed figure for both schemes.

        Both ways of showing a figure, as the last expression of a cell and with
        `fig.show()`, end in `plotly.io.show`, which publishes a raw mime bundle:
        no formatter of IPython sees the figure. A hook on the display publisher
        sees every bundle. This is the capture of plotly figures, in place of the
        generic one of `Integration`.

        Parameters
        ----------
        shell : IPython.core.interactiveshell.InteractiveShell
            The shell of the kernel.
        """

        def hook(msg: dict[str, Any]) -> dict[str, Any]:
            """Add the dark figure to a message that displays a plotly figure.

            Parameters
            ----------
            msg : dict[str, Any]
                A message the kernel is about to publish.

            Returns
            -------
            dict[str, Any]
                The message, to publish.
            """
            content = msg.get("content", {})
            data = content.get("data")
            if isinstance(data, dict) and MIME in data:
                self._both(data, content.setdefault("metadata", {}))
            return msg

        # A method of ipykernel's publisher, which IPython's base class lacks.
        shell.display_pub.register_hook(hook)  # ty: ignore[unresolved-attribute]
