"""The integration classes of this site's example gallery.

`[tool.zallery]` in `pyproject.toml` names them under `integrations`. Zallery
imports them from the root of the repository, in the builder and in the kernel of
each example.
"""

from __future__ import annotations

from contextlib import ExitStack
from typing import Any

from zallery import Integration
from zallery.integration import Scheme
from zallery.matplotlib import Matplotlib


class Figures(Matplotlib):
    """The matplotlib look of this site.

    Its page colors, which `docs/stylesheets/extra.css` sets too, so that figures
    blend into the page. The same hues on both pages: strong on light, softer on
    dark.
    """

    background = ("#f8f9fb", "#090c10")
    axes_background = ("#fefefe", "#111720")
    foreground = ("black", "#e6edf3")
    palette = ("Dark2", "Set2")


class Badges(Integration):
    """The dark look of the badges of the "integration of your own" example."""

    # A class an example defines is in the `__main__` module of its kernel.
    type = "__main__.Badge"

    def retheme(self, badge: Any, scheme: Scheme) -> ExitStack | None:
        """Swap the two colors of a badge for the dark scheme.

        Parameters
        ----------
        badge : Badge
            The badge about to be shown.
        scheme : {"light", "dark"}
            The color scheme the next rendering is for.

        Returns
        -------
        contextlib.ExitStack or None
            Context manager putting the colors back. `None` for the light scheme:
            a badge is drawn light.
        """
        if scheme == "light":
            return None
        restore = ExitStack()
        restore.callback(setattr, badge, "color", badge.color)
        restore.callback(setattr, badge, "background", badge.background)
        badge.color, badge.background = badge.background, badge.color
        return restore
