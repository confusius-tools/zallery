"""The matplotlib integration: the light look, and the dark one of a drawn figure.

`Matplotlib.setup` and `Matplotlib.retheme` run inside the gallery's ipykernel
(see `zallery.integration.setup_kernel`), not in the builder process. Examples run
under the light look. Each displayed figure is printed again with the dark look
and carries that rendering in its output metadata, under
`metadata["image/png"]["dark"]`, which `render.py` picks up. Nothing is
re-executed: the dark rendering comes from swapping colors and colormaps on the
drawn artists and printing again.
"""

from __future__ import annotations

import traceback
from collections.abc import Callable, Iterable, Mapping, Sequence
from contextlib import ExitStack
from functools import partial
from typing import TYPE_CHECKING, Any

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

from zallery.integration import Integration, Scheme

if TYPE_CHECKING:
    from IPython.core.interactiveshell import InteractiveShell

Printer = Callable[[Figure], tuple[str, dict[str, Any]] | None]
"""A matplotlib_inline figure printer: base64 PNG plus metadata, or `None` if empty."""

Palette = str | Sequence[str]
"""A color cycle: the name of a listed matplotlib colormap, or a list of colors."""

_ON_BLACK = ("black", "black", "white")
"""Background, axes background and foreground of a figure drawn on pure black.

A figure whose background is pure black (a plotting function with a black default,
for one) is taken as drawn with these rather than with the light look, so its
black is background and its white is foreground. Its pure-white data colors are
swapped like text.
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
    Per-element colors (collections, images) are left alone. Public, for a
    subclass of `Matplotlib` that overrides `retheme`.

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
    automatically. Public, for a subclass of `Matplotlib` that overrides
    `retheme`.

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
    # A name matplotlib does not know raises: what is switched by then is put back.
    with ExitStack() as restore:
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
                mappable.set_cmap(
                    with_source(mapping[name]) if derived else mapping[name]
                )
        return restore.pop_all()


class Matplotlib(Integration):
    """The look of matplotlib figures: examples run light, each figure is drawn dark.

    A pair is `(light, dark)`; a mapping is `{light: dark}`. Subclass and set the
    attributes to change the look. Only colors and colormaps that exactly match a
    light value are changed on a figure; anything else the author chose on purpose
    is kept.

    Attributes
    ----------
    type : str
        The class of matplotlib figures.
    background : tuple[str, str]
        Figure background. The stock values are close to the page colors of a
        default Zensical site. The light one is a hair off pure white, so that
        pure white stays free for data colors (regions, contours, text drawn over
        images), which the swap must keep.
    axes_background : tuple[str, str]
        Axes background. Its light value differs from the figure's, so that a
        subclass can give the axes their own dark color.
    foreground : tuple[str, str]
        Text, ticks, spines and default lines. The light value must be the color
        matplotlib draws them with: it is matched, not written to `rcParams`.
    palette : tuple[Palette or None, Palette or None] or None
        The default color cycle of each scheme. Examples run with the light one;
        the dark rendering shows each of its colors as the dark color at the same
        position. A missing light palette is matplotlib's default cycle, a missing
        dark one is the light one. `None` leaves the cycle alone.
    cmaps : Mapping[str, str]
        Colormap names to switch for the dark rendering.
    colors : Mapping[str, str]
        Other exact colors to switch, in single artists and in collections.
    rcparams : Mapping[str, Any]
        Other `rcParams` the examples run under.
    """

    type = "matplotlib.figure.Figure"
    background: tuple[str, str] = ("#fefefe", "#0b0c0f")
    axes_background: tuple[str, str] = ("#fdfdfd", "#0b0c0f")
    foreground: tuple[str, str] = ("black", "#e2e4e9")
    palette: tuple[Palette | None, Palette | None] | None = None
    cmaps: Mapping[str, str] = {"coolwarm": "berlin"}
    colors: Mapping[str, str] = {}
    rcparams: Mapping[str, Any] = {
        "figure.dpi": 160,
        "savefig.dpi": 200,
        "figure.figsize": (7, 4),
    }

    def __init__(self) -> None:
        """Check the colors and resolve the palettes.

        Colormap names are not checked here: an example may register its own.

        Raises
        ------
        ValueError
            If a color attribute or `palette` is malformed. The message starts
            with the name of the class and of the attribute.
        """
        for attribute in ("background", "axes_background", "foreground"):
            pair = getattr(self, attribute)
            if not isinstance(pair, tuple) or len(pair) != 2:
                raise ValueError(
                    f"{type(self).__name__}.{attribute}: give a pair of colors, "
                    f"(light, dark), not {pair!r}."
                )
            self._check_colors(attribute, pair)
        if not isinstance(self.colors, Mapping):
            # A bad value of a class attribute, as the other cases are: one kind
            # of error for the configuration to catch.
            raise ValueError(  # noqa: TRY004
                f"{type(self).__name__}.colors: give a mapping of colors, "
                f"{{light: dark}}, not {self.colors!r}."
            )
        self._check_colors("colors", [*self.colors, *self.colors.values()])
        self._cycles = self._resolve_palette()

    def _check_colors(self, attribute: str, colors: Iterable[Any]) -> None:
        """Raise if matplotlib cannot read one of the colors of an attribute.

        Parameters
        ----------
        attribute : str
            Name of the attribute, for the error message.
        colors : Iterable[Any]
            The colors it holds.

        Raises
        ------
        ValueError
            If one is not a color. The message starts with the name of the class
            and of the attribute.
        """
        for color in colors:
            try:
                mcolors.to_rgb(color)
            except (ValueError, TypeError) as exc:
                raise ValueError(f"{type(self).__name__}.{attribute}: {exc}") from None

    def _palette_colors(self, value: Palette) -> tuple[str, ...]:
        """Return one palette, given by name or as a list of colors, as hex colors.

        Parameters
        ----------
        value : Palette
            The name of a listed matplotlib colormap, or a non-empty list of
            matplotlib colors.

        Returns
        -------
        tuple[str, ...]
            The colors as `#rrggbb` strings.

        Raises
        ------
        ValueError
            If `value` is neither, or holds something matplotlib cannot read as a
            color.
        """
        where = f"{type(self).__name__}.palette"
        if isinstance(value, str):
            colors = getattr(mpl.colormaps.get(value), "colors", None)
            if colors is None:
                raise ValueError(
                    f"{where}: {value!r} is not a listed matplotlib colormap such "
                    'as "Set2". Give such a name or a list of colors.'
                )
        elif isinstance(value, Sequence) and len(value) > 0:
            colors = value
        else:
            raise ValueError(
                f"{where}: a palette is the name of a listed matplotlib colormap or "
                f"a non-empty list of colors, not {value!r}."
            )
        try:
            return tuple(mcolors.to_hex(color) for color in colors)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"{where}: {exc}") from None

    def _resolve_palette(self) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
        """Return the light and the dark color cycle `palette` asks for.

        Returns
        -------
        tuple[tuple[str, ...], tuple[str, ...]] or None
            The light and the dark cycle, as hex colors. `None` if no palette is
            set.

        Raises
        ------
        ValueError
            If `palette` is not a pair, a palette is malformed, or the dark one is
            shorter than the light one.
        """
        where = f"{type(self).__name__}.palette"
        if self.palette is None:
            return None
        if not isinstance(self.palette, tuple) or len(self.palette) != 2:
            raise ValueError(f"{where}: give a pair, (light, dark).")
        light, dark = self.palette
        if light is None and dark is None:
            return None
        if light is None:
            default = mpl.rcParamsDefault["axes.prop_cycle"].by_key()["color"]
            light_colors = tuple(mcolors.to_hex(color) for color in default)
        else:
            light_colors = self._palette_colors(light)
        dark_colors = light_colors if dark is None else self._palette_colors(dark)
        if len(dark_colors) < len(light_colors):
            raise ValueError(
                f"{where}: the dark palette has {len(dark_colors)} colors, fewer "
                f"than the light one ({len(light_colors)}): every light color needs "
                "a dark counterpart. Without a light palette, the light one is "
                "matplotlib's default cycle."
            )
        return light_colors, dark_colors

    def setup(self) -> None:
        """Apply the light look to `rcParams`.

        `savefig.facecolor` is deliberately left at `"auto"`, so that the swapped
        figure color is what gets printed. The foreground is not written: it is
        matplotlib's own.
        """
        mpl.style.use("default")
        if self._cycles is not None:
            mpl.rcParams["axes.prop_cycle"] = cycler(color=list(self._cycles[0]))
        for key, value in self.rcparams.items():
            # matplotlib types the keys as literals; these are a subclass's.
            mpl.rcParams[key] = value  # ty: ignore[invalid-assignment]
        mpl.rcParams["figure.facecolor"] = self.background[0]
        mpl.rcParams["axes.facecolor"] = self.axes_background[0]

    def retheme(self, fig: Figure, scheme: Scheme) -> ExitStack | None:
        """Recolor a drawn figure for a color scheme, in place.

        Parameters
        ----------
        fig : matplotlib.figure.Figure
            A figure drawn under the light look, or on a pure black background.
        scheme : {"light", "dark"}
            The color scheme to recolor for.

        Returns
        -------
        contextlib.ExitStack or None
            Context manager restoring the original colors and colormaps. `None`
            for the light scheme and a figure drawn light: nothing to change. A
            figure on black is recolored for both schemes; for the light one,
            `cmaps` and `colors` apply in reverse.

        Raises
        ------
        ValueError
            If `cmaps` names a colormap matplotlib does not know. The message
            starts with the name of the class and of the attribute; the figure is
            left as it came.
        """
        on_black = mcolors.to_rgb(fig.get_facecolor()) == mcolors.to_rgb(_ON_BLACK[0])
        if scheme == "light" and not on_black:
            return None
        index = 0 if scheme == "light" else 1
        target = (
            self.background[index],
            self.axes_background[index],
            self.foreground[index],
        )
        light = (self.background[0], self.axes_background[0], self.foreground[0])
        # The figure background last: it wins where figure and axes share a color
        # (a figure on black).
        roles: dict[str, str] = {}
        for drawn in (light,) * (scheme == "dark") + (_ON_BLACK,) * on_black:
            # What a figure on black holds of the light look (axes left at their
            # default, for one) turns dark too; its black is background, not text.
            roles |= {drawn[1]: target[1], drawn[0]: target[0], drawn[2]: target[2]}
        if scheme == "light":
            colors = {dark: light for light, dark in self.colors.items()}
            cmaps = {dark: light for light, dark in self.cmaps.items()}
        else:
            palette = dict(zip(*self._cycles)) if self._cycles is not None else {}
            colors = {**palette, **self.colors}
            cmaps = dict(self.cmaps)
        artists = fig.findobj()
        with ExitStack() as restore:
            # A theme color wins over a palette color.
            restore.enter_context(swap_colors(artists, {**colors, **roles}))
            restore.enter_context(_swap_collection_colors(artists, colors))
            try:
                restore.enter_context(swap_cmaps(artists, cmaps))
            except (ValueError, KeyError) as exc:
                raise ValueError(f"{type(self).__name__}.cmaps: {exc}") from None
            return restore.pop_all()

    def _print_both(
        self, fig: Figure, *, printer: Printer
    ) -> tuple[str, dict[str, Any]] | None:
        """Print `fig` for the light scheme, then for the dark one.

        Parameters
        ----------
        fig : matplotlib.figure.Figure
            The figure to print. It is handed back as it came.
        printer : Callable[[matplotlib.figure.Figure], tuple[str, dict] or None]
            The figure printer matplotlib_inline registered for `Figure`.

        Returns
        -------
        tuple[str, dict[str, Any]] or None
            The light rendering and its metadata, with the dark rendering added
            under `"dark"`. `None` when `printer` returns `None` (an empty figure).
            The light rendering alone when the dark one fails: the error is
            reported on the standard error, and the figure is not lost for it.

        Notes
        -----
        Layout engines (constrained, tight) re-solve on every draw and are not
        idempotent, so the dark rendering would come out shifted by a few pixels.
        The layout is frozen while the dark rendering is printed, which keeps the
        geometry identical; the engine is restored afterwards, so later cells
        still re-solve the layout.
        """
        with ExitStack() as restore:
            look = self.retheme(fig, "light")
            if look is not None:
                restore.enter_context(look)
            light = printer(fig)
        if light is None:
            return None
        data, metadata = light
        try:
            with ExitStack() as restore:
                restore.callback(fig.set_layout_engine, fig.get_layout_engine())
                fig.set_layout_engine("none")
                look = self.retheme(fig, "dark")
                if look is not None:
                    restore.enter_context(look)
                dark = printer(fig)
        except Exception:  # noqa: BLE001
            # Whatever the `retheme` of a subclass raises: IPython would swallow
            # the error and drop the whole output.
            traceback.print_exc()
            return light
        if dark is None:
            return light
        return data, {**metadata, "dark": dark[0]}

    def _install(self, shell: InteractiveShell) -> None:
        """Have the kernel print every displayed figure for both schemes.

        Retina PNGs, and the PNG printer of figures wrapped by `_print_both`. This
        is the capture of matplotlib figures, in place of the generic one of
        `Integration`.

        Parameters
        ----------
        shell : IPython.core.interactiveshell.InteractiveShell
            The shell of the kernel.
        """
        from matplotlib_inline.backend_inline import set_matplotlib_formats

        set_matplotlib_formats("retina")
        # IPython annotates the formatter as optional; a running shell has one.
        display_formatter = shell.display_formatter
        formatter = display_formatter.formatters["image/png"]  # ty: ignore[unresolved-attribute]
        printer = formatter.lookup_by_type(Figure)
        formatter.for_type(Figure, partial(self._print_both, printer=printer))
