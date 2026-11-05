"""Tests for zallery.theme."""

from __future__ import annotations

import base64
import io
from contextlib import ExitStack
from functools import partial

import matplotlib

matplotlib.use("Agg")

import matplotlib.colors as mcolors
import matplotlib.image as mimg
import matplotlib.pyplot as plt
import numpy as np
import pytest
from IPython.core.pylabtools import retina_figure
from matplotlib import colormaps

from zallery.theme import DARK, LIGHT, render_both, retheme, swap_cmaps, swap_colors


class _DerivedColormap(mcolors.ListedColormap):
    """A colormap built from another one, like ConfUSIus's `ThresholdedColormap`.

    It exposes the original as `source` and rebuilds itself through
    `with_source`, which is the shape `zallery.theme.swap_cmaps` relies on.
    """

    def __init__(self, source: mcolors.Colormap) -> None:
        super().__init__(
            source(np.linspace(0.0, 1.0, source.N)), name=f"{source.name}_derived"
        )
        self.source = source

    def with_source(self, name: str) -> _DerivedColormap:
        return _DerivedColormap(colormaps[name])


_SEQUENTIAL_SWAPS = {"inferno_r": "inferno"}


def _project_hook(fig, theme):
    """A hook as a project would write it: flip a sequential colormap per page."""
    mapping = (
        _SEQUENTIAL_SWAPS
        if theme == "dark"
        else {dark: light for light, dark in _SEQUENTIAL_SWAPS.items()}
    )
    return swap_cmaps(fig.findobj(), mapping)


@pytest.fixture
def figure():
    """A light-themed figure exercising every kind of artist the swap touches."""
    with matplotlib.rc_context():
        plt.style.use("default")
        plt.rcParams.update(
            {"figure.facecolor": LIGHT.bg, "axes.facecolor": LIGHT.axes_bg}
        )
        fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(6, 3), layout="constrained")
        image = ax0.imshow(
            np.linspace(-1.0, 1.0, 12).reshape(3, 4),
            cmap=_DerivedColormap(colormaps[LIGHT.diverging_cmap]),
            norm=mcolors.Normalize(-1.0, 1.0),
        )
        fig.colorbar(image, ax=ax0)
        scatter = ax1.scatter([0, 1], [0, 1], c=[0, 1], cmap=LIGHT.diverging_cmap)
        (theme_line,) = ax1.plot([0, 1], color="black")
        (red_line,) = ax1.plot([1, 0], color="tab:red")
        legend = ax1.legend([theme_line, red_line], ["theme", "kept"], framealpha=0.8)
        ax1.set_title("title")
        artists = {
            "fig": fig,
            "ax1": ax1,
            "image": image,
            "scatter": scatter,
            "theme_line": theme_line,
            "red_line": red_line,
            "legend": legend,
        }
        yield artists
        plt.close(fig)


def _corner_rgb(png_b64: str) -> tuple[float, float, float]:
    pixels = mimg.imread(io.BytesIO(base64.b64decode(png_b64)))
    r, g, b = (float(v) for v in pixels[0, 0, :3])
    return r, g, b


def test_retheme_swaps_theme_colors(figure) -> None:
    retheme(figure["fig"], LIGHT, DARK)

    assert figure["fig"].get_facecolor() == pytest.approx(mcolors.to_rgba(DARK.bg))
    assert figure["ax1"].get_facecolor() == pytest.approx(mcolors.to_rgba(DARK.axes_bg))
    assert mcolors.to_rgba(figure["ax1"].title.get_color()) == pytest.approx(
        mcolors.to_rgba(DARK.fg)
    )
    assert mcolors.to_rgba(figure["theme_line"].get_color()) == pytest.approx(
        mcolors.to_rgba(DARK.fg)
    )


def test_retheme_recolors_tick_marks(figure) -> None:
    retheme(figure["fig"], LIGHT, DARK)

    tick = figure["ax1"].xaxis.get_major_ticks()[0].tick1line
    assert mcolors.to_rgba(tick.get_markeredgecolor()) == pytest.approx(
        mcolors.to_rgba(DARK.fg)
    )


def test_retheme_keeps_intentional_colors(figure) -> None:
    figure["fig"].set_facecolor("#123456")
    (white_line,) = figure["ax1"].plot([0, 1], color="white")

    retheme(figure["fig"], LIGHT, DARK)

    assert figure["fig"].get_facecolor() == pytest.approx(mcolors.to_rgba("#123456"))
    assert figure["red_line"].get_color() == "tab:red"
    assert white_line.get_color() == "white"


def test_retheme_preserves_alpha(figure) -> None:
    retheme(figure["fig"], LIGHT, DARK)

    frame = figure["legend"].get_frame().get_facecolor()
    assert frame == pytest.approx(mcolors.to_rgba(DARK.axes_bg, alpha=0.8))


def test_retheme_swaps_diverging_colormaps_including_derived(figure) -> None:
    original = figure["image"].get_cmap()

    with retheme(figure["fig"], LIGHT, DARK):
        derived = figure["image"].get_cmap()
        assert isinstance(derived, _DerivedColormap)
        assert derived.source.name == DARK.diverging_cmap
        assert figure["scatter"].get_cmap().name == DARK.diverging_cmap

    # Leaving the context puts the very same colormap objects back.
    assert figure["image"].get_cmap() is original
    assert figure["scatter"].get_cmap().name == LIGHT.diverging_cmap


_PALETTE = {"#ff0000": "#ffaaaa", "#0000ff": "#aaaaff"}


def test_retheme_swaps_palette_colors_in_artists_and_collections(figure) -> None:
    """A palette color becomes its counterpart wherever it is drawn, then comes back."""
    ax = figure["ax1"]
    (line,) = ax.plot([0, 1], color="#ff0000")
    points = ax.scatter([0, 1], [0, 1], c="#0000ff")
    band = ax.fill_between([0, 1], [0, 1], color="#ff0000", alpha=0.3)
    kept = ax.scatter([0, 1], [1, 0], color="#00ff00")

    with retheme(figure["fig"], LIGHT, DARK, _PALETTE):
        assert mcolors.to_hex(line.get_color()) == "#ffaaaa"
        assert mcolors.to_hex(points.get_facecolor()[0]) == "#aaaaff"
        assert band.get_facecolor()[0] == pytest.approx(mcolors.to_rgba("#ffaaaa", 0.3))
        assert mcolors.to_hex(kept.get_facecolor()[0]) == "#00ff00"

    assert line.get_color() == "#ff0000"
    assert mcolors.to_hex(points.get_facecolor()[0]) == "#0000ff"
    assert band.get_facecolor()[0] == pytest.approx(mcolors.to_rgba("#ff0000", 0.3))
    # The scatter's edge color still follows its face color.
    points.set_facecolor("#00ff00")
    assert mcolors.to_hex(points.get_edgecolor()[0]) == "#00ff00"


def test_retheme_leaves_colormapped_collections_alone(figure) -> None:
    """Colormapped data is not palette data, even where the colors coincide."""
    mapped = figure["ax1"].scatter(
        [0, 1], [0, 1], c=[0, 1], cmap=mcolors.ListedColormap(["#ff0000", "#0000ff"])
    )
    figure["fig"].canvas.draw()
    drawn = mapped.get_facecolor().copy()

    with retheme(figure["fig"], LIGHT, DARK, _PALETTE):
        assert np.array_equal(mapped.get_facecolor(), drawn)

    assert np.array_equal(mapped.get_facecolor(), drawn)


def test_render_both_draws_only_the_dark_page_with_the_dark_palette(figure) -> None:
    (line,) = figure["ax1"].plot([0, 1], color="#ff0000")
    printed: list[str] = []

    def printer(fig):
        printed.append(mcolors.to_hex(line.get_color()))
        return "png", {}

    render_both(figure["fig"], printer=printer, palette=_PALETTE)

    assert printed == ["#ff0000", "#ffaaaa"]
    assert line.get_color() == "#ff0000"


def test_swap_colors_replaces_listed_colors_and_restores_them(figure) -> None:
    artists = figure["fig"].findobj()

    with swap_colors(artists, {"tab:red": "#00ff00"}):
        assert mcolors.to_hex(figure["red_line"].get_color()) == "#00ff00"
        assert figure["theme_line"].get_color() == "black"

    assert figure["red_line"].get_color() == "tab:red"


def test_render_both_returns_light_data_and_dark_metadata(figure) -> None:
    printer = partial(retina_figure, base64=True)

    result = render_both(figure["fig"], printer=printer)

    assert result is not None
    data, metadata = result
    assert set(metadata) >= {"width", "height", "dark"}
    assert _corner_rgb(data) == pytest.approx(mcolors.to_rgb(LIGHT.bg), abs=1 / 255)
    assert _corner_rgb(metadata["dark"]) == pytest.approx(
        mcolors.to_rgb(DARK.bg), abs=1 / 255
    )
    # The figure is handed back in its light state, with identical geometry.
    again = printer(figure["fig"])
    assert again is not None
    assert _corner_rgb(again[0]) == pytest.approx(mcolors.to_rgb(LIGHT.bg), abs=1 / 255)
    assert (
        figure["fig"].get_layout_engine().__class__.__name__
        == "ConstrainedLayoutEngine"
    )


@pytest.mark.parametrize("cmap", ["inferno", "berlin"])
def test_render_both_preserves_existing_destination_colormap(cmap) -> None:
    """Displaying twice must not change an explicitly chosen destination palette."""
    fig, ax = plt.subplots(facecolor=LIGHT.bg)
    image = ax.imshow([[0, 1]], cmap=cmap)
    original = image.get_cmap()
    printed = []

    def printer(fig):
        printed.append(image.get_cmap().name)
        return "png", {}

    try:
        for _ in range(2):
            render_both(fig, printer=printer, hook=_project_hook)
            assert image.get_cmap() is original
        assert printed == [cmap] * 4
    finally:
        plt.close(fig)


def test_render_both_preserves_automatic_marker_colors() -> None:
    """Automatic marker colors must still follow later line-color changes."""
    fig, ax = plt.subplots(facecolor=LIGHT.bg)
    (line,) = ax.plot([0, 1], color="black", marker="o")
    try:
        render_both(fig, printer=lambda fig: ("png", {}))
        line.set_color("red")
        assert line.get_markerfacecolor() == "red"
        assert line.get_markeredgecolor() == "red"
    finally:
        plt.close(fig)


def test_render_both_restores_original_state_when_printing_fails(figure) -> None:
    """A failed dark print must restore colormap objects, colors and layout."""
    fig = figure["fig"]
    image = figure["image"]
    cmap = image.get_cmap()
    engine = fig.get_layout_engine()
    sequential = figure["ax1"].scatter([0, 1], [1, 0], c=[0, 1], cmap="inferno_r")
    (line,) = figure["ax1"].plot([0, 1], color="black", marker="o")

    def printer(fig):
        if mcolors.to_hex(fig.get_facecolor()) == DARK.bg:
            assert sequential.get_cmap().name == "inferno"
            raise RuntimeError("dark print failed")
        return "png", {}

    with pytest.raises(RuntimeError, match="dark print failed"):
        render_both(fig, printer=printer, hook=_project_hook)

    assert image.get_cmap() is cmap
    assert sequential.get_cmap().name == "inferno_r"
    assert fig.get_layout_engine() is engine
    assert mcolors.to_hex(fig.get_facecolor()) == LIGHT.bg
    assert line.get_color() == "black"
    line.set_color("red")
    assert line.get_markerfacecolor() == "red"


def test_render_both_passes_through_empty_figure() -> None:
    fig = plt.figure()
    try:
        assert render_both(fig, printer=partial(retina_figure, base64=True)) is None
    finally:
        plt.close(fig)


def test_render_both_themes_figures_drawn_on_black() -> None:
    """A figure on a pure black background renders for both pages and is restored."""
    fig, ax = plt.subplots(facecolor="black")
    ax.set_facecolor("black")
    title = ax.set_title("title", color="white")
    themes: list[str] = []

    def hook(fig, theme):
        themes.append(theme)
        return ExitStack()

    try:
        result = render_both(
            fig, printer=partial(retina_figure, base64=True), hook=hook
        )

        assert result is not None
        data, metadata = result
        assert _corner_rgb(data) == pytest.approx(mcolors.to_rgb(LIGHT.bg), abs=1 / 255)
        assert _corner_rgb(metadata["dark"]) == pytest.approx(
            mcolors.to_rgb(DARK.bg), abs=1 / 255
        )
        # The hook first sees the figure converted to light, then to dark.
        assert themes == ["light", "dark"]
        assert mcolors.to_hex(fig.get_facecolor()) == "#000000"
        assert mcolors.to_hex(ax.get_facecolor()) == "#000000"
        assert mcolors.to_hex(title.get_color()) == "#ffffff"
    finally:
        plt.close(fig)


def test_render_both_restores_hook_changes(figure) -> None:
    """The hook sees the dark figure and registers its exact restoration."""
    seen: list[tuple[str, tuple[float, ...]]] = []

    def hook(fig, theme):
        seen.append((theme, tuple(fig.get_facecolor())))
        restore = ExitStack()
        restore.callback(fig.axes[1].set_title, fig.axes[1].get_title())
        fig.axes[1].set_title("dark title")
        return restore

    render_both(figure["fig"], printer=partial(retina_figure, base64=True), hook=hook)

    assert [theme for theme, _ in seen] == ["dark"]
    assert seen[0][1] == pytest.approx(mcolors.to_rgba(DARK.bg))
    assert figure["ax1"].get_title() == "title"


def test_render_both_restores_light_when_hook_raises(figure) -> None:
    def hook(fig, theme):
        raise RuntimeError("hook broke")

    with pytest.raises(RuntimeError, match="hook broke"):
        render_both(
            figure["fig"], printer=partial(retina_figure, base64=True), hook=hook
        )

    assert figure["fig"].get_facecolor() == pytest.approx(mcolors.to_rgba(LIGHT.bg))
