"""Tests for zallery.matplotlib."""

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
from matplotlib.figure import Figure

from zallery.integration import Scheme
from zallery.matplotlib import Matplotlib, swap_colors

LIGHT_BG, DARK_BG = Matplotlib.background
LIGHT_AXES, DARK_AXES = Matplotlib.axes_background
LIGHT_FG, DARK_FG = Matplotlib.foreground


class _DerivedColormap(mcolors.ListedColormap):
    """A colormap built from another one, like ConfUSIus's `ThresholdedColormap`.

    It exposes the original as `source` and rebuilds itself through
    `with_source`, which is the shape `zallery.matplotlib.swap_cmaps` relies on.
    """

    def __init__(self, source: mcolors.Colormap) -> None:
        super().__init__(
            source(np.linspace(0.0, 1.0, source.N)), name=f"{source.name}_derived"
        )
        self.source = source

    def with_source(self, name: str) -> _DerivedColormap:
        return _DerivedColormap(colormaps[name])


class _Sequential(Matplotlib):
    """A class as a project would write it: one more colormap pair."""

    cmaps = {"coolwarm": "berlin", "inferno_r": "inferno"}


class _Paletted(Matplotlib):
    """A class with a palette for each scheme."""

    palette = (["#ff0000", "#0000ff"], ["#ffaaaa", "#aaaaff"])


@pytest.fixture
def figure():
    """A light-themed figure exercising every kind of artist the swap touches."""
    with matplotlib.rc_context():
        plt.style.use("default")
        plt.rcParams.update(
            {"figure.facecolor": LIGHT_BG, "axes.facecolor": LIGHT_AXES}
        )
        fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(6, 3), layout="constrained")
        image = ax0.imshow(
            np.linspace(-1.0, 1.0, 12).reshape(3, 4),
            cmap=_DerivedColormap(colormaps["coolwarm"]),
            norm=mcolors.Normalize(-1.0, 1.0),
        )
        fig.colorbar(image, ax=ax0)
        scatter = ax1.scatter([0, 1], [0, 1], c=[0, 1], cmap="coolwarm")
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


def _look(integration: Matplotlib, fig: Figure, scheme: Scheme) -> ExitStack:
    """Return the context manager of a retheme that has something to change."""
    look = integration.retheme(fig, scheme)
    assert look is not None
    return look


def _corner_rgb(png_b64: str) -> tuple[float, float, float]:
    pixels = mimg.imread(io.BytesIO(base64.b64decode(png_b64)))
    r, g, b = (float(v) for v in pixels[0, 0, :3])
    return r, g, b


def test_stock_colors_are_close_to_zensical_defaults() -> None:
    assert Matplotlib.background == ("#fefefe", "#0b0c0f")
    assert Matplotlib.axes_background == ("#fdfdfd", "#0b0c0f")
    assert Matplotlib.foreground == ("black", "#e2e4e9")
    assert Matplotlib.cmaps == {"coolwarm": "berlin"}


def test_retheme_swaps_theme_colors(figure) -> None:
    Matplotlib().retheme(figure["fig"], "dark")

    assert figure["fig"].get_facecolor() == pytest.approx(mcolors.to_rgba(DARK_BG))
    assert figure["ax1"].get_facecolor() == pytest.approx(mcolors.to_rgba(DARK_AXES))
    assert mcolors.to_rgba(figure["ax1"].title.get_color()) == pytest.approx(
        mcolors.to_rgba(DARK_FG)
    )
    assert mcolors.to_rgba(figure["theme_line"].get_color()) == pytest.approx(
        mcolors.to_rgba(DARK_FG)
    )


def test_retheme_to_light_leaves_a_light_figure_alone(figure) -> None:
    assert Matplotlib().retheme(figure["fig"], "light") is None


def test_retheme_recolors_tick_marks(figure) -> None:
    Matplotlib().retheme(figure["fig"], "dark")

    tick = figure["ax1"].xaxis.get_major_ticks()[0].tick1line
    assert mcolors.to_rgba(tick.get_markeredgecolor()) == pytest.approx(
        mcolors.to_rgba(DARK_FG)
    )


def test_retheme_keeps_intentional_colors(figure) -> None:
    figure["fig"].set_facecolor("#123456")
    (white_line,) = figure["ax1"].plot([0, 1], color="white")

    Matplotlib().retheme(figure["fig"], "dark")

    assert figure["fig"].get_facecolor() == pytest.approx(mcolors.to_rgba("#123456"))
    assert figure["red_line"].get_color() == "tab:red"
    assert white_line.get_color() == "white"


def test_retheme_preserves_alpha(figure) -> None:
    Matplotlib().retheme(figure["fig"], "dark")

    frame = figure["legend"].get_frame().get_facecolor()
    assert frame == pytest.approx(mcolors.to_rgba(DARK_AXES, alpha=0.8))


def test_retheme_swaps_diverging_colormaps_including_derived(figure) -> None:
    original = figure["image"].get_cmap()

    with _look(Matplotlib(), figure["fig"], "dark"):
        derived = figure["image"].get_cmap()
        assert isinstance(derived, _DerivedColormap)
        assert derived.source.name == "berlin"
        assert figure["scatter"].get_cmap().name == "berlin"

    # Leaving the context puts the very same colormap objects back.
    assert figure["image"].get_cmap() is original
    assert figure["scatter"].get_cmap().name == "coolwarm"


def test_the_diverging_pair_is_data_of_the_class(figure) -> None:
    class NoPair(Matplotlib):
        cmaps = {}

    with _look(NoPair(), figure["fig"], "dark"):
        assert figure["scatter"].get_cmap().name == "coolwarm"


def test_retheme_swaps_palette_colors_in_artists_and_collections(figure) -> None:
    """A palette color becomes its counterpart wherever it is drawn, then comes back."""
    ax = figure["ax1"]
    (line,) = ax.plot([0, 1], color="#ff0000")
    points = ax.scatter([0, 1], [0, 1], c="#0000ff")
    band = ax.fill_between([0, 1], [0, 1], color="#ff0000", alpha=0.3)
    kept = ax.scatter([0, 1], [1, 0], color="#00ff00")

    with _look(_Paletted(), figure["fig"], "dark"):
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

    with _look(_Paletted(), figure["fig"], "dark"):
        assert np.array_equal(mapped.get_facecolor(), drawn)

    assert np.array_equal(mapped.get_facecolor(), drawn)


def test_colors_are_switched_in_artists_and_collections(figure) -> None:
    class Brand(Matplotlib):
        colors = {"tab:red": "#00ff00"}

    dots = figure["ax1"].scatter([0, 1], [1, 0], color="tab:red")
    with _look(Brand(), figure["fig"], "dark"):
        assert mcolors.to_hex(figure["red_line"].get_color()) == "#00ff00"
        assert mcolors.to_hex(dots.get_facecolor()[0]) == "#00ff00"
    assert mcolors.to_hex(figure["red_line"].get_color()) == mcolors.to_hex("tab:red")


def test_a_figure_on_black_is_rethemed_for_both_schemes() -> None:
    fig, ax = plt.subplots(facecolor="black")
    ax.set_facecolor("black")
    title = ax.set_title("t", color="white")
    image = ax.imshow([[0, 1]], cmap="berlin")
    integration = Matplotlib()
    try:
        with _look(integration, fig, "light"):
            assert mcolors.to_hex(fig.get_facecolor()) == "#fefefe"
            assert mcolors.to_hex(title.get_color()) == "#000000"
            assert image.get_cmap().name == "coolwarm"
        with _look(integration, fig, "dark"):
            assert mcolors.to_hex(fig.get_facecolor()) == "#0b0c0f"
            assert mcolors.to_hex(title.get_color()) == "#e2e4e9"
            assert image.get_cmap().name == "berlin"
        assert mcolors.to_hex(fig.get_facecolor()) == "#000000"
    finally:
        plt.close(fig)


def test_setup_writes_the_light_look_and_keeps_savefig_auto() -> None:
    class Paired(Matplotlib):
        palette = (["#ff0000", "#0000ff"], ["#00ff00", "#ffff00"])

    with matplotlib.rc_context():
        Paired().setup()
        assert plt.rcParams["figure.facecolor"] == "#fefefe"
        assert plt.rcParams["axes.facecolor"] == "#fdfdfd"
        assert plt.rcParams["axes.prop_cycle"].by_key()["color"] == [
            "#ff0000",
            "#0000ff",
        ]
        assert plt.rcParams["figure.dpi"] == 160
        assert plt.rcParams["savefig.facecolor"] == "auto"


@pytest.mark.parametrize(
    "palette", [("Set2", "coolwarm"), (["red", "blue"], ["green"]), ("Set2", ["nope"])]
)
def test_a_bad_palette_names_the_attribute(palette) -> None:
    class Bad(Matplotlib):
        pass

    Bad.palette = palette
    with pytest.raises(ValueError, match=r"^Bad\.palette"):
        Bad()


@pytest.mark.parametrize(
    ("attribute", "value"),
    [
        ("colors", {"not-a-color": "#ffffff"}),
        ("colors", {"#ffffff": "not-a-color"}),
        ("background", ("#ffffff", "not-a-color")),
        ("axes_background", ("#ffffff",)),
        ("foreground", "black"),
    ],
)
def test_a_bad_color_names_the_attribute(attribute, value) -> None:
    """A color matplotlib cannot read fails when the class is instantiated."""

    class Bad(Matplotlib):
        pass

    setattr(Bad, attribute, value)
    with pytest.raises(ValueError, match=rf"^Bad\.{attribute}"):
        Bad()


def test_an_unknown_colormap_names_the_attribute_and_leaves_the_figure(figure) -> None:
    """Colormaps may be registered by the example: they are checked when used."""

    class Bad(Matplotlib):
        cmaps = {"coolwarm": "no_such_cmap"}

    with pytest.raises(ValueError, match=r"^Bad\.cmaps"):
        Bad().retheme(figure["fig"], "dark")

    assert figure["scatter"].get_cmap().name == "coolwarm"
    assert figure["fig"].get_facecolor() == pytest.approx(mcolors.to_rgba(LIGHT_BG))


def test_a_figure_on_black_with_light_axes_gets_dark_axes() -> None:
    """Only the figure is black: its axes, drawn light, still turn dark."""
    with matplotlib.rc_context():
        Matplotlib().setup()
        fig, ax = plt.subplots(facecolor="black")
        try:
            assert mcolors.to_hex(ax.get_facecolor()) == LIGHT_AXES
            with _look(Matplotlib(), fig, "dark"):
                assert mcolors.to_hex(fig.get_facecolor()) == DARK_BG
                assert mcolors.to_hex(ax.get_facecolor()) == DARK_AXES
            with _look(Matplotlib(), fig, "light"):
                assert mcolors.to_hex(fig.get_facecolor()) == LIGHT_BG
                assert mcolors.to_hex(ax.get_facecolor()) == LIGHT_AXES
        finally:
            plt.close(fig)


def test_a_palette_is_a_colormap_name_or_a_list_and_defaults_fill_in() -> None:
    """No light palette is matplotlib's default cycle; no dark one is the light one."""

    class Named(Matplotlib):
        palette = ("Dark2", "Set2")

    class DarkOnly(Matplotlib):
        palette = (None, "tab10")

    class LightOnly(Matplotlib):
        palette = (["red", "#0000ff"], None)

    with matplotlib.rc_context():
        Named().setup()
        cycle = plt.rcParams["axes.prop_cycle"].by_key()["color"]
        assert cycle[:2] == ["#1b9e77", "#d95f02"]
        assert len(cycle) == colormaps["Dark2"].N
        DarkOnly().setup()
        default = matplotlib.rcParamsDefault["axes.prop_cycle"].by_key()["color"]
        assert plt.rcParams["axes.prop_cycle"].by_key()["color"] == [
            mcolors.to_hex(color) for color in default
        ]
        LightOnly().setup()
        assert plt.rcParams["axes.prop_cycle"].by_key()["color"] == [
            "#ff0000",
            "#0000ff",
        ]


def test_print_both_draws_only_the_dark_page_with_the_dark_palette(figure) -> None:
    (line,) = figure["ax1"].plot([0, 1], color="#ff0000")
    printed: list[str] = []

    def printer(fig):
        printed.append(mcolors.to_hex(line.get_color()))
        return "png", {}

    _Paletted()._print_both(figure["fig"], printer=printer)

    assert printed == ["#ff0000", "#ffaaaa"]
    assert line.get_color() == "#ff0000"


def test_swap_colors_replaces_listed_colors_and_restores_them(figure) -> None:
    artists = figure["fig"].findobj()

    with swap_colors(artists, {"tab:red": "#00ff00"}):
        assert mcolors.to_hex(figure["red_line"].get_color()) == "#00ff00"
        assert figure["theme_line"].get_color() == "black"

    assert figure["red_line"].get_color() == "tab:red"


def test_print_both_returns_light_data_and_dark_metadata(figure) -> None:
    printer = partial(retina_figure, base64=True)

    result = Matplotlib()._print_both(figure["fig"], printer=printer)

    assert result is not None
    data, metadata = result
    assert set(metadata) >= {"width", "height", "dark"}
    assert _corner_rgb(data) == pytest.approx(mcolors.to_rgb(LIGHT_BG), abs=1 / 255)
    assert _corner_rgb(metadata["dark"]) == pytest.approx(
        mcolors.to_rgb(DARK_BG), abs=1 / 255
    )
    # The figure is handed back in its light state, with identical geometry.
    again = printer(figure["fig"])
    assert again is not None
    assert _corner_rgb(again[0]) == pytest.approx(mcolors.to_rgb(LIGHT_BG), abs=1 / 255)
    assert (
        figure["fig"].get_layout_engine().__class__.__name__
        == "ConstrainedLayoutEngine"
    )


@pytest.mark.parametrize("cmap", ["inferno", "berlin"])
def test_print_both_preserves_existing_destination_colormap(cmap) -> None:
    """Displaying twice must not change an explicitly chosen destination palette."""
    fig, ax = plt.subplots(facecolor=LIGHT_BG)
    image = ax.imshow([[0, 1]], cmap=cmap)
    original = image.get_cmap()
    printed = []

    def printer(fig):
        printed.append(image.get_cmap().name)
        return "png", {}

    try:
        for _ in range(2):
            _Sequential()._print_both(fig, printer=printer)
            assert image.get_cmap() is original
        assert printed == [cmap] * 4
    finally:
        plt.close(fig)


def test_print_both_preserves_automatic_marker_colors() -> None:
    """Automatic marker colors must still follow later line-color changes."""
    fig, ax = plt.subplots(facecolor=LIGHT_BG)
    (line,) = ax.plot([0, 1], color="black", marker="o")
    try:
        Matplotlib()._print_both(fig, printer=lambda fig: ("png", {}))
        line.set_color("red")
        assert line.get_markerfacecolor() == "red"
        assert line.get_markeredgecolor() == "red"
    finally:
        plt.close(fig)


def test_print_both_restores_original_state_when_printing_fails(
    figure, capsys: pytest.CaptureFixture[str]
) -> None:
    """A failed dark print must restore colormap objects, colors and layout.

    The light rendering is kept, and the error is reported: a figure is not lost
    for its dark look.
    """
    fig = figure["fig"]
    image = figure["image"]
    cmap = image.get_cmap()
    engine = fig.get_layout_engine()
    sequential = figure["ax1"].scatter([0, 1], [1, 0], c=[0, 1], cmap="inferno_r")
    (line,) = figure["ax1"].plot([0, 1], color="black", marker="o")

    def printer(fig):
        if mcolors.to_hex(fig.get_facecolor()) == DARK_BG:
            assert sequential.get_cmap().name == "inferno"
            raise RuntimeError("dark print failed")
        return "png", {}

    assert _Sequential()._print_both(fig, printer=printer) == ("png", {})
    assert "dark print failed" in capsys.readouterr().err

    assert image.get_cmap() is cmap
    assert sequential.get_cmap().name == "inferno_r"
    assert fig.get_layout_engine() is engine
    assert mcolors.to_hex(fig.get_facecolor()) == LIGHT_BG
    assert line.get_color() == "black"
    line.set_color("red")
    assert line.get_markerfacecolor() == "red"


def test_print_both_passes_through_empty_figure() -> None:
    fig = plt.figure()
    try:
        printer = partial(retina_figure, base64=True)
        assert Matplotlib()._print_both(fig, printer=printer) is None
    finally:
        plt.close(fig)


def test_print_both_themes_figures_drawn_on_black() -> None:
    """A figure on a pure black background renders for both pages and is restored."""
    fig, ax = plt.subplots(facecolor="black")
    ax.set_facecolor("black")
    title = ax.set_title("title", color="white")
    schemes: list[str] = []

    class Recording(Matplotlib):
        def retheme(self, fig, scheme):
            schemes.append(scheme)
            return super().retheme(fig, scheme)

    try:
        result = Recording()._print_both(
            fig, printer=partial(retina_figure, base64=True)
        )

        assert result is not None
        data, metadata = result
        assert _corner_rgb(data) == pytest.approx(mcolors.to_rgb(LIGHT_BG), abs=1 / 255)
        assert _corner_rgb(metadata["dark"]) == pytest.approx(
            mcolors.to_rgb(DARK_BG), abs=1 / 255
        )
        assert schemes == ["light", "dark"]
        assert mcolors.to_hex(fig.get_facecolor()) == "#000000"
        assert mcolors.to_hex(ax.get_facecolor()) == "#000000"
        assert mcolors.to_hex(title.get_color()) == "#ffffff"
    finally:
        plt.close(fig)


def test_print_both_restores_what_a_subclass_changes(figure) -> None:
    """A subclass adds its changes to the stack of the stock class."""
    seen: list[tuple[float, ...]] = []

    class Titled(Matplotlib):
        def retheme(self, fig, scheme):
            restore = super().retheme(fig, scheme)
            if restore is not None:
                seen.append(tuple(fig.get_facecolor()))
                restore.callback(fig.axes[1].set_title, fig.axes[1].get_title())
                fig.axes[1].set_title("dark title")
            return restore

    Titled()._print_both(figure["fig"], printer=partial(retina_figure, base64=True))

    assert len(seen) == 1
    assert seen[0] == pytest.approx(mcolors.to_rgba(DARK_BG))
    assert figure["ax1"].get_title() == "title"


def test_print_both_keeps_the_light_rendering_when_retheme_raises(
    figure, capsys: pytest.CaptureFixture[str]
) -> None:
    class Broken(Matplotlib):
        def retheme(self, fig, scheme):
            if scheme == "dark":
                raise RuntimeError("retheme broke")
            return super().retheme(fig, scheme)

    result = Broken()._print_both(
        figure["fig"], printer=partial(retina_figure, base64=True)
    )

    assert result is not None
    data, metadata = result
    assert "dark" not in metadata
    assert _corner_rgb(data) == pytest.approx(mcolors.to_rgb(LIGHT_BG), abs=1 / 255)
    assert "retheme broke" in capsys.readouterr().err
    assert figure["fig"].get_facecolor() == pytest.approx(mcolors.to_rgba(LIGHT_BG))
    assert (
        figure["fig"].get_layout_engine().__class__.__name__
        == "ConstrainedLayoutEngine"
    )
