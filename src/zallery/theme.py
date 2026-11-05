"""Kernel-side theming: render each figure once for light and once for dark.

This module runs inside the gallery's ipykernel (see `execute.py`), not in the
builder process. `setup_kernel` applies the light rcParams and wraps
matplotlib_inline's PNG printer so every displayed figure also carries its dark
rendering in the output metadata, under `metadata["image/png"]["dark"]`, which
`render.py` picks up. Nothing is re-executed: the dark rendering comes from
palette-swapping the drawn artists and printing again.
"""

from __future__ import annotations

import importlib
import warnings
from collections.abc import Callable
from contextlib import ExitStack
from dataclasses import dataclass
from functools import partial
from typing import Any, Literal

import matplotlib as mpl
import matplotlib.colors as mcolors
import matplotlib.style
import numpy as np
from matplotlib.artist import Artist
from matplotlib.cm import ScalarMappable
from matplotlib.collections import Collection
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.rcsetup import cycler

from zallery._types import Palettes

Printer = Callable[[Figure], tuple[str, dict[str, Any]] | None]
"""A matplotlib_inline figure printer: base64 PNG plus metadata, or `None` if empty."""

Hook = Callable[[Figure, Literal["light", "dark"]], ExitStack]
"""Project hook returning a context manager that restores its changes."""


@dataclass(frozen=True)
class Theme:
    """Colors a rendering is built with, by role.

    Attributes
    ----------
    bg : str
        Figure background.
    axes_bg : str
        Axes background.
    fg : str
        Text, ticks, spines and default line color.
    diverging_cmap : str
        Name of the diverging colormap to use on `bg`; figures drawn with one
        theme's are switched to the other's.
    """

    bg: str
    axes_bg: str
    fg: str
    diverging_cmap: str


LIGHT = Theme(bg="#f8f9fb", axes_bg="#fefefe", fg="black", diverging_cmap="coolwarm")
"""Theme every example is executed under.

`axes_bg` is a hair off pure white so that pure white stays free for data colors
(regions, contours, text drawn over images), which the swap must keep.
"""

DARK = Theme(bg="#090c10", axes_bg="#111720", fg="#e6edf3", diverging_cmap="berlin")
"""Dark counterpart of `LIGHT`, role by role.

No value may equal a `LIGHT` value, or swapping back would be ambiguous.
"""

ON_BLACK = Theme(bg="black", axes_bg="black", fg="white", diverging_cmap="berlin")
"""Theme of figures drawn on a pure black background.

A figure whose background is pure black (a plotting function with a black default,
for one) is taken as drawn under this theme rather than `LIGHT`, so its black is
background and its white is foreground. Its pure-white data colors are swapped
like text. Being a dark theme, it is expected to use the project hook's dark-page
colors.
"""

_COLOR_SLOTS = (
    ("get_facecolor", "set_facecolor"),
    ("get_edgecolor", "set_edgecolor"),
    ("get_color", "set_color"),
    ("get_markeredgecolor", "set_markeredgecolor"),
    ("get_markerfacecolor", "set_markerfacecolor"),
)
"""Getter/setter pairs through which artists expose a single color."""


def _as_rgba(value: Any) -> tuple[float, float, float, float] | None:
    """Return `value` as an RGBA tuple, or `None` if it is not a single color.

    Parameters
    ----------
    value : Any
        Whatever an artist's color getter returned.

    Returns
    -------
    tuple[float, float, float, float] or None
        The color, or `None` for per-element color arrays (collections, images)
        and anything matplotlib cannot parse as a color.
    """
    if isinstance(value, np.ndarray) and value.ndim != 1:
        return None
    try:
        return mcolors.to_rgba(value)
    except (ValueError, TypeError):
        return None


def swap_colors(artists: list[Artist], mapping: dict[str, str]) -> ExitStack:
    """Replace every single artist color in `mapping` by its replacement.

    Colors are read for all artists before any is written: an Axes and its
    background patch expose the same facecolor, so a read-modify-write loop would
    apply the mapping twice. Matching is on RGB; the artist's alpha is kept.
    Per-element colors (collections, images) are left alone. Shared by the
    built-in theme swap and the project hook.

    Parameters
    ----------
    artists : list[matplotlib.artist.Artist]
        Artists to recolor in place.
    mapping : dict[str, str]
        Colors to replace, mapped to their replacement.

    Returns
    -------
    contextlib.ExitStack
        Context manager restoring only the changed properties to their original
        values.
    """
    restore = ExitStack()
    table = {mcolors.to_rgb(src): dst for src, dst in mapping.items()}
    writes: list[
        tuple[Callable[[Any], Any], Any, tuple[float, float, float, float]]
    ] = []
    for artist in artists:
        for getter, setter in _COLOR_SLOTS:
            if not hasattr(artist, getter):
                continue
            value = getattr(artist, getter)()
            if isinstance(artist, Line2D) and getter.startswith("get_marker"):
                # Public getters resolve "auto"; keep that link to the line color.
                value = getattr(artist, "_" + getter.removeprefix("get_"))
            rgba = _as_rgba(value)
            if rgba is not None and rgba[:3] in table:
                new = mcolors.to_rgba(table[rgba[:3]], alpha=rgba[3])
                writes.append((getattr(artist, setter), value, new))
    for setter, original, color in writes:
        restore.callback(setter, original)
        setter(color)
    return restore


def _swap_collection_colors(
    artists: list[Artist], mapping: dict[str, str]
) -> ExitStack:
    """Replace the colors in `mapping` inside the color arrays of collections.

    `swap_colors` leaves collections alone: a scatter plot, a filled area or the bars
    of an error bar keep their colors as an array, one row per element. Here each row
    matching a color in `mapping` is replaced; the row's alpha is kept. Colormapped
    collections are skipped: their colors come from the data, and matplotlib computes
    them again on every draw.

    Parameters
    ----------
    artists : list[matplotlib.artist.Artist]
        Artists to recolor in place; anything but a collection is ignored.
    mapping : dict[str, str]
        Colors to replace, mapped to their replacement.

    Returns
    -------
    contextlib.ExitStack
        Context manager restoring the colors the collections were given, so that a
        link such as an edge color following the face color survives.
    """
    restore = ExitStack()
    table = {mcolors.to_rgb(src): mcolors.to_rgb(dst) for src, dst in mapping.items()}
    writes: list[tuple[Callable[[Any], Any], Any, np.ndarray]] = []
    for artist in artists:
        if not isinstance(artist, Collection) or artist.get_array() is not None:
            continue
        for slot in ("facecolor", "edgecolor"):
            colors = np.array(getattr(artist, f"get_{slot}")(), dtype=float)
            changed = False
            for row in colors.reshape(-1, 4):
                replacement = table.get(tuple(row[:3]))
                if replacement is not None:
                    row[:3] = replacement
                    changed = True
            if changed:
                # The getter returns the resolved array; the color as it was given
                # ("face", `None` for the default) is only kept privately.
                original = getattr(artist, f"_original_{slot}")
                writes.append((getattr(artist, f"set_{slot}"), original, colors))
    for setter, original, colors in writes:
        restore.callback(setter, original)
        setter(colors)
    return restore


def swap_cmaps(artists: list[Artist], mapping: dict[str, str]) -> ExitStack:
    """Switch every mappable drawn with a colormap in `mapping` to its replacement.

    Colormaps are matched by name. A colormap derived from another one, exposing
    the original as `source` and a `with_source(name)` rebuild (as ConfUSIus's
    `ThresholdedColormap` does), is matched on its source and rebuilt, so derived
    colormaps keep their shape in both themes. Colorbars follow their mappable
    automatically. Shared by the built-in theme swap and the project hook.

    Parameters
    ----------
    artists : list[matplotlib.artist.Artist]
        Artists to update in place.
    mapping : dict[str, str]
        Colormap names to replace, mapped to the replacement's name.

    Returns
    -------
    contextlib.ExitStack
        Context manager restoring the original colormaps.
    """
    restore = ExitStack()
    for mappable in artists:
        if not isinstance(mappable, ScalarMappable):
            continue
        cmap = mappable.get_cmap()
        source = getattr(cmap, "source", None)
        with_source = getattr(cmap, "with_source", None)
        derived = source is not None and with_source is not None
        name = source.name if derived else cmap.name
        if name in mapping:
            restore.callback(mappable.set_cmap, cmap)
            mappable.set_cmap(with_source(mapping[name]) if derived else mapping[name])
    return restore


def retheme(
    fig: Figure, src: Theme, dst: Theme, palette: dict[str, str] | None = None
) -> ExitStack:
    """Recolor a drawn figure from `src` to `dst` in place.

    Only colors and colormaps that exactly match a `src` role or a `palette`
    color are touched; anything else the author chose on purpose is kept.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        Figure to recolor.
    src : Theme
        Theme the figure is currently drawn with.
    dst : Theme
        Theme to recolor to.
    palette : dict[str, str], optional
        Colors of the default cycle to replace, mapped to their replacement.
        Unlike the theme roles, they are also replaced inside collections. A
        theme role wins over a palette entry for the same color. If not
        provided, only the theme roles are swapped.

    Returns
    -------
    contextlib.ExitStack
        Context manager restoring the original colors and colormaps.
    """
    artists = fig.findobj()
    # `bg` wins when `src` uses the same color for both backgrounds (`ON_BLACK`).
    palette = palette or {}
    roles = {getattr(src, role): getattr(dst, role) for role in ("axes_bg", "bg", "fg")}
    with ExitStack() as restore:
        restore.enter_context(swap_colors(artists, {**palette, **roles}))
        restore.enter_context(_swap_collection_colors(artists, palette))
        restore.enter_context(
            swap_cmaps(artists, {src.diverging_cmap: dst.diverging_cmap})
        )
        return restore.pop_all()


def render_both(
    fig: Figure,
    *,
    printer: Printer,
    hook: Hook | None = None,
    palette: dict[str, str] | None = None,
) -> tuple[str, dict[str, Any]] | None:
    """Print `fig` under `LIGHT`, then under `DARK`, without re-executing anything.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        A figure drawn under the `LIGHT` theme, or under `ON_BLACK` if its
        background is pure black. An `ON_BLACK` figure is swapped to `LIGHT`
        first and handed back in `ON_BLACK`.
    printer : Callable[[matplotlib.figure.Figure], tuple[str, dict] or None]
        The figure printer matplotlib_inline registered for `Figure`.
    hook : Callable[[matplotlib.figure.Figure, str], contextlib.ExitStack], optional
        Project hook called after each theme swap. Returns a context manager that
        restores its changes, including when rendering fails. If not provided,
        nothing else is adjusted.
    palette : dict[str, str], optional
        Colors of the light color cycle, mapped to the color the dark rendering
        shows instead (see `retheme`). If not provided, cycle colors are the
        same in both renderings.

    Returns
    -------
    tuple[str, dict[str, Any]] or None
        The light rendering and its metadata, with the dark rendering added under
        `"dark"`. `None` when `printer` returns `None` (an empty figure).

    Notes
    -----
    The layout is frozen only while the dark rendering is printed; the figure's
    layout engine is restored before returning.
    """
    if mcolors.to_rgb(fig.get_facecolor()) == mcolors.to_rgb(ON_BLACK.bg):
        with retheme(fig, ON_BLACK, LIGHT) as restore:
            if hook is not None:
                restore.enter_context(hook(fig, "light"))
            return render_both(fig, printer=printer, hook=hook, palette=palette)
    light = printer(fig)
    if light is None:
        return None
    data, metadata = light
    # Layout engines (constrained, tight) re-solve on every draw and are not
    # idempotent, so the dark render would come out shifted by a few pixels.
    # Freezing the layout during the dark render keeps the geometry identical; the
    # engine is restored afterwards so later cells still re-solve the layout.
    with ExitStack() as restore:
        restore.callback(fig.set_layout_engine, fig.get_layout_engine())
        fig.set_layout_engine("none")
        restore.enter_context(retheme(fig, LIGHT, DARK, palette))
        if hook is not None:
            restore.enter_context(hook(fig, "dark"))
        dark = printer(fig)
    if dark is None:
        return light
    return data, {**metadata, "dark": dark[0]}


def setup_kernel(
    hook_module: str | None = None, palettes: Palettes | None = None
) -> None:
    """Configure the running kernel: light rcParams, retina PNGs, dark hook.

    Must run before any example cell. `savefig.facecolor` is deliberately left at
    `"auto"` so the swapped figure facecolor is what gets printed.

    Parameters
    ----------
    hook_module : str, optional
        Dotted name of a module defining `gallery_retheme(fig, theme)`, the
        project hook called after each built-in swap (see `render_both`). It must
        be importable from the kernel. If not provided, only the built-in swap
        runs.
    palettes : Palettes, optional
        The light and the dark color cycle. Examples run with the light one;
        the dark rendering shows each of its colors as the dark color at the
        same position. If not provided, matplotlib's default cycle is used
        for both.
    """
    from IPython import get_ipython
    from matplotlib_inline.backend_inline import set_matplotlib_formats

    hook: Hook | None = None
    if hook_module is not None:
        hook = importlib.import_module(hook_module).gallery_retheme

    warnings.filterwarnings("ignore", message="IProgress not found.*")
    # rich.live.Live.refresh() warns once per process the first time it detects a
    # Jupyter kernel without ipywidgets installed; it would land in the rendered
    # output of whichever cell happens to trigger it.
    warnings.filterwarnings(
        "ignore", message='install "ipywidgets" for Jupyter support'
    )
    light, dark = palettes or ((), ())
    mpl.style.use("default")
    if light:
        mpl.rcParams["axes.prop_cycle"] = cycler(color=list(light))
    mpl.rcParams.update(
        {
            "figure.dpi": 160,
            "savefig.dpi": 200,
            "figure.figsize": (7, 4),
            "figure.facecolor": LIGHT.bg,
            "axes.facecolor": LIGHT.axes_bg,
        }
    )
    set_matplotlib_formats("retina")
    shell = get_ipython()
    png_formatter = shell.display_formatter.formatters["image/png"]
    printer = png_formatter.lookup_by_type(Figure)
    png_formatter.for_type(
        Figure,
        partial(
            render_both, printer=printer, hook=hook, palette=dict(zip(light, dark))
        ),
    )
