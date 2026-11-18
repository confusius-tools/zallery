"""Tests for zallery.index."""

from __future__ import annotations

from pathlib import Path

from zallery._types import ExampleSpec, RenderedExample
from zallery.index import build_index, build_section_pages


def _spec(source: Path, section: str) -> ExampleSpec:
    return ExampleSpec(
        source=source,
        base_name=source.stem,
        section=section,
        section_intro=f"# {section.upper()}\n\nIntro for {section}.\n",
    )


def test_build_index_groups_cards_by_section(tmp_path: Path) -> None:
    src1 = tmp_path / "io" / "load_autc.py"
    src2 = tmp_path / "io" / "load_nifti.py"
    src3 = tmp_path / "glm" / "first_level.py"
    for src in (src1, src2, src3):
        src.parent.mkdir(parents=True, exist_ok=True)
        src.touch()

    rendered = [
        RenderedExample(
            spec=_spec(src1, "io"),
            title="Load AUTC",
            summary="Quick AUTC demo.",
            md_path=src1.with_suffix(".md"),
            thumbnail_light=src1.parent / "load_autc_thumb_light.png",
            thumbnail_dark=src1.parent / "load_autc_thumb_dark.png",
        ),
        RenderedExample(
            spec=_spec(src2, "io"),
            title="Load NIfTI",
            summary="",
            md_path=src2.with_suffix(".md"),
            thumbnail_light=None,
            thumbnail_dark=None,
        ),
        RenderedExample(
            spec=_spec(src3, "glm"),
            title="First-level GLM",
            summary="Subject-level GLM.",
            md_path=src3.with_suffix(".md"),
            thumbnail_light=src3.parent / "first_level_thumb_light.png",
            thumbnail_dark=src3.parent / "first_level_thumb_dark.png",
        ),
    ]

    index_md = build_index(rendered, root=tmp_path)

    # Section headers in document order.
    assert "## GLM" in index_md
    assert "## IO" in index_md
    assert "Load AUTC" in index_md
    assert "Load NIfTI" in index_md
    assert "First-level GLM" in index_md
    # Cards include thumbnail and title links.
    assert "load_autc_thumb_light.png#only-light" in index_md
    assert "load_autc_thumb_dark.png#only-dark" in index_md
    # Falls back to default thumb for examples without one.
    assert "_assets/default_thumb.svg#only-light" in index_md
    assert "_assets/default_thumb_dark.svg#only-dark" in index_md
    # The summary rides along as a hover overlay, only where there is one.
    assert (
        '<span class="examples-card-summary" aria-hidden="true">Quick AUTC demo.</span>'
        in index_md
    )
    assert index_md.count("examples-card-summary") == 2


def test_build_index_preserves_section_order_from_input(tmp_path: Path) -> None:
    """Sections appear in the order they are first seen in the rendered list.

    Discovery sorts section folders by their prefixed name (e.g. `01_io` before
    `02_decomposition`), so the index must preserve that order rather than
    re-sorting alphabetically by the stripped section name.
    """
    src_io = tmp_path / "io" / "load.py"
    src_decomp = tmp_path / "decomposition" / "fastica.py"
    for src in (src_io, src_decomp):
        src.parent.mkdir(parents=True, exist_ok=True)
        src.touch()

    rendered = [
        RenderedExample(
            spec=_spec(src_io, "io"),
            title="Load",
            summary="",
            md_path=src_io.with_suffix(".md"),
            thumbnail_light=None,
            thumbnail_dark=None,
        ),
        RenderedExample(
            spec=_spec(src_decomp, "decomposition"),
            title="FastICA",
            summary="",
            md_path=src_decomp.with_suffix(".md"),
            thumbnail_light=None,
            thumbnail_dark=None,
        ),
    ]

    md = build_index(rendered, root=tmp_path)
    assert md.index("## IO") < md.index("## DECOMPOSITION")


def test_build_index_flattens_links_in_card_overlays(tmp_path: Path) -> None:
    """Both link forms in a summary are flattened to their text.

    Overlays are copied verbatim onto the index page at the gallery root, where an
    example's relative cross-links (written against its own built page) would not
    resolve and would fail `zensical build --strict`. A mkdocstrings cross-reference
    resolves, but would render as a link inside an overlay that is inert by design.
    """
    src = tmp_path / "decomposition" / "nmf.py"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.touch()
    rendered = [
        RenderedExample(
            spec=_spec(src, "decomposition"),
            title="NMF",
            summary=(
                "Uses [FastICA][confusius.decomposition.FastICA]. Complements the "
                "[PCA](pca_single_recording.md) example."
            ),
            md_path=src.with_suffix(".md"),
            thumbnail_light=None,
            thumbnail_dark=None,
        ),
    ]
    md = build_index(rendered, root=tmp_path)
    assert "](pca_single_recording.md)" not in md
    assert "confusius.decomposition.FastICA" not in md
    assert "Uses FastICA. Complements the PCA example.</span>" in md


def test_build_index_escapes_html_in_card_overlays(tmp_path: Path) -> None:
    """Summary text is escaped so it cannot inject markup into the overlay span.

    Quotes are left alone: they need no escaping in text content, and an escaped one
    survives a code span, which escapes the entity's `&` in turn and shows it
    verbatim.
    """
    src = tmp_path / "io" / "ex.py"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.touch()
    rendered = [
        RenderedExample(
            spec=_spec(src, "io"),
            title="Ex",
            summary='Uses <div> & `mode="temporal"`.',
            md_path=src.with_suffix(".md"),
            thumbnail_light=None,
            thumbnail_dark=None,
        ),
    ]
    md = build_index(rendered, root=tmp_path)
    assert 'Uses &lt;div&gt; &amp; `mode="temporal"`.</span>' in md


def test_build_index_demotes_h1_section_intros(tmp_path: Path) -> None:
    """Section intros starting with H1 are demoted to H2 so there's a single page title."""
    src = tmp_path / "io" / "ex.py"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.touch()
    spec = ExampleSpec(
        source=src,
        base_name=src.stem,
        section="io",
        section_intro="# Input/Output\n\nIntro paragraph.\n",
    )
    rendered = [
        RenderedExample(
            spec=spec,
            title="Ex",
            summary="",
            md_path=src.with_suffix(".md"),
            thumbnail_light=None,
            thumbnail_dark=None,
        ),
    ]
    md = build_index(rendered, root=tmp_path)
    # Exactly one H1 (the page title); the section uses H2.
    assert md.count("\n# ") + (1 if md.startswith("# ") else 0) == 1
    assert "## Input/Output" in md


def test_build_index_header_comes_from_index_file_when_present(tmp_path: Path) -> None:
    default = build_index([], root=tmp_path)
    assert default.startswith("# Examples\n\n")

    (tmp_path / "_index.md").write_text("# Gallery\n\nProject intro.\n")
    custom = build_index([], root=tmp_path)

    assert custom == "# Gallery\n\nProject intro.\n\n"


def _failed_example(root: Path) -> RenderedExample:
    """Return an example that raised, with a figure thumbnail of its own."""
    src = root / "io" / "broken.py"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.touch()
    built = root / "_built" / "io"
    return RenderedExample(
        spec=_spec(src, "io"),
        title="Broken",
        summary="",
        md_path=built / "broken.md",
        thumbnail_light=built / "broken_thumb_light.png",
        thumbnail_dark=built / "broken_thumb_dark.png",
        failed=True,
    )


def test_build_index_marks_an_example_that_raised_with_the_error_thumbnail(
    tmp_path: Path,
) -> None:
    """The error thumbnail wins over the example's own: the card must show the fault."""
    assets = tmp_path / "_assets"
    assets.mkdir()
    (assets / "error_thumb.svg").write_text("<svg/>")
    (assets / "error_thumb_dark.svg").write_text("<svg/>")

    md = build_index([_failed_example(tmp_path)], root=tmp_path)

    assert 'src="_assets/error_thumb.svg#only-light"' in md
    assert 'src="_assets/error_thumb_dark.svg#only-dark"' in md
    assert "broken_thumb_light.png" not in md


def test_build_index_keeps_the_thumbnail_of_a_failed_example_without_error_assets(
    tmp_path: Path,
) -> None:
    md = build_index([_failed_example(tmp_path)], root=tmp_path)

    assert "_built/io/broken_thumb_light.png#only-light" in md
    assert "error_thumb" not in md


def _example(
    root: Path, section: str, name: str, title: str, *, intro: str | None = None
) -> RenderedExample:
    """Return a rendered example of a section, built under `root/_built`."""
    source = root / section / f"{name}.py"
    spec = _spec(source, section)
    if intro is not None:
        spec = ExampleSpec(source, name, section, intro)
    return RenderedExample(
        spec=spec,
        title=title,
        summary="",
        md_path=root / "_built" / section / f"{name}.md",
        thumbnail_light=None,
        thumbnail_dark=None,
    )


def test_build_section_pages_gives_each_section_its_page(tmp_path: Path) -> None:
    rendered = [
        _example(tmp_path, "io", "load", "Load a file"),
        _example(tmp_path, "io", "save", "Save a file"),
        _example(tmp_path, "glm", "fit", "Fit a model"),
    ]

    pages = build_section_pages(rendered, root=tmp_path)

    assert set(pages) == {
        tmp_path / "_built" / "io" / "index.md",
        tmp_path / "_built" / "glm" / "index.md",
    }
    io_page = pages[tmp_path / "_built" / "io" / "index.md"]
    # The title of the section is the title of the page.
    assert io_page.startswith("# IO\n\nIntro for io.\n")
    # Its own examples only, with links from the folder of the page.
    assert "**[Load a file](load.md)**" in io_page
    assert "**[Save a file](save.md)**" in io_page
    assert "Fit a model" not in io_page
    assert 'src="../../_assets/default_thumb.svg#only-light"' in io_page


def test_build_section_pages_links_the_thumbnail_from_the_page(tmp_path: Path) -> None:
    folder = tmp_path / "_built" / "io"
    example = RenderedExample(
        spec=_spec(tmp_path / "io" / "load.py", "io"),
        title="Load a file",
        summary="",
        md_path=folder / "load.md",
        thumbnail_light=folder / "images" / "load_thumb_light.png",
        thumbnail_dark=folder / "images" / "load_thumb_dark.png",
    )

    page = build_section_pages([example], root=tmp_path)[folder / "index.md"]

    assert 'src="images/load_thumb_light.png#only-light"' in page
    assert 'src="images/load_thumb_dark.png#only-dark"' in page


def test_build_section_pages_names_a_section_without_intro_by_its_folder(
    tmp_path: Path,
) -> None:
    rendered = [_example(tmp_path, "glm", "fit", "Fit a model", intro="")]

    page = build_section_pages(rendered, root=tmp_path)[
        tmp_path / "_built" / "glm" / "index.md"
    ]

    assert page.startswith("# glm\n")


_FRONT_MATTER_INTRO = "---\nicon: lucide/bug\n---\n\n# Input\n\nReading files.\n"


def test_build_section_pages_keeps_the_front_matter_of_the_section(
    tmp_path: Path,
) -> None:
    rendered = [
        _example(tmp_path, "io", "load", "Load a file", intro=_FRONT_MATTER_INTRO)
    ]

    page = build_section_pages(rendered, root=tmp_path)[
        tmp_path / "_built" / "io" / "index.md"
    ]

    assert page.startswith("---\nicon: lucide/bug\n---\n\n# Input\n\nReading files.\n")


def test_build_index_leaves_out_the_front_matter_of_a_section(tmp_path: Path) -> None:
    rendered = [
        _example(tmp_path, "io", "load", "Load a file", intro=_FRONT_MATTER_INTRO)
    ]

    index_md = build_index(rendered, root=tmp_path)

    assert "## Input\n\nReading files." in index_md
    assert "icon" not in index_md
    assert "---\n\n##" not in index_md
