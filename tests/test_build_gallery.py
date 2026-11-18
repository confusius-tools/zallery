"""End-to-end test of the gallery builder."""

from __future__ import annotations

import shutil
from functools import partial
from importlib.resources import files
from pathlib import Path

import pytest

from zallery import ExampleError
from zallery.pipeline import build_gallery

GalleryPaths = tuple[Path, Path, Path]


def _seed_example(root: Path, section: str, name: str, body: str) -> Path:
    sec = root / section
    sec.mkdir(parents=True, exist_ok=True)
    (sec / "_section.md").write_text(f"# {section.title()}\n\nIntro.\n")
    src = sec / f"{name}.py"
    src.write_text(body)
    return src


@pytest.mark.slow
def test_build_gallery_produces_expected_artifacts(gallery_paths: GalleryPaths) -> None:
    examples_root, built_dir, cache_root = gallery_paths

    _seed_example(
        examples_root,
        "io",
        "hello",
        "# %% [markdown]\n# # Hello\n#\n# Tiny example.\n\n# %%\nprint('hi')\n",
    )

    build_gallery(
        examples_root=examples_root,
        built_dir=built_dir,
        cache_root=cache_root,
        deps_fingerprint="testdeps==1.0",
    )

    first = (built_dir / "io" / "hello.md").read_text()
    assert "# Hello" in first
    assert "```python\nprint('hi')\n```" in first
    assert (built_dir / "io" / "hello.py").is_file()
    assert (built_dir / "io" / "hello.ipynb").is_file()
    assert (examples_root / "index.md").read_text().count("Hello") >= 1

    # Wipe the built dir but keep the cache. A second run must restore it
    # without re-executing.
    shutil.rmtree(built_dir)

    build_gallery(
        examples_root=examples_root,
        built_dir=built_dir,
        cache_root=cache_root,
        deps_fingerprint="testdeps==1.0",
    )
    second = (built_dir / "io" / "hello.md").read_text()

    assert first == second  # Exact same artifact, including timestamp content.
    assert (built_dir / "io" / "hello.py").is_file()
    assert (built_dir / "io" / "hello.ipynb").is_file()


@pytest.mark.slow
def test_build_gallery_prints_progress_when_non_interactive(
    gallery_paths: GalleryPaths, capsys: pytest.CaptureFixture[str]
) -> None:
    examples_root, built_dir, cache_root = gallery_paths

    _seed_example(
        examples_root,
        "io",
        "hello",
        "# %% [markdown]\n# # Hello\n\n# %%\nprint('hi')\n",
    )

    # Under pytest stdout is captured and reports `isatty() == False`, so the
    # builder takes its non-interactive path and emits plain progress lines
    # instead of the rich live bar.
    build_gallery(
        examples_root=examples_root,
        built_dir=built_dir,
        cache_root=cache_root,
        deps_fingerprint="testdeps==1.0",
    )
    fresh = capsys.readouterr().out
    assert "-> io/hello" in fresh
    assert "done in" in fresh

    # A second run hits the cache and announces it.
    shutil.rmtree(built_dir)
    build_gallery(
        examples_root=examples_root,
        built_dir=built_dir,
        cache_root=cache_root,
        deps_fingerprint="testdeps==1.0",
    )
    assert "[cached]" in capsys.readouterr().out


def test_build_gallery_no_cache_reexecutes_selected_and_restores_the_rest(
    gallery_paths: GalleryPaths, capsys: pytest.CaptureFixture[str]
) -> None:
    examples_root, built_dir, cache_root = gallery_paths
    wanted = _seed_example(
        examples_root,
        "io",
        "hello",
        "# %% [markdown]\n# # Hello\n\n# %%\nprint('hi')\n",
    )
    _seed_example(
        examples_root,
        "misc",
        "other",
        "# %% [markdown]\n# # Other\n\n# %%\nprint('bye')\n",
    )
    build_gallery(
        examples_root=examples_root,
        built_dir=built_dir,
        cache_root=cache_root,
        deps_fingerprint="testdeps==1.0",
    )
    capsys.readouterr()
    cached_md = next(cache_root.glob("**/io/hello/hello.md"))
    cached_md.write_text("stale cached page\n")

    build_gallery(
        examples_root=examples_root,
        built_dir=built_dir,
        cache_root=cache_root,
        deps_fingerprint="testdeps==1.0",
        only=[wanted],
        use_cache=False,
    )

    out = capsys.readouterr().out
    assert "-> io/hello (1 cells)" in out
    assert "-> misc/other [cached]" in out
    # The fresh run replaced the tampered cache entry and the built page.
    assert "stale cached page" not in cached_md.read_text()
    assert "print('hi')" in (built_dir / "io" / "hello.md").read_text()


@pytest.mark.slow
def test_build_gallery_runs_only_selected_and_stubs_the_rest(
    gallery_paths: GalleryPaths,
) -> None:
    examples_root, built_dir, cache_root = gallery_paths

    wanted = _seed_example(
        examples_root,
        "io",
        "hello",
        "# %% [markdown]\n# # Hello\n\n# %%\nprint('hi')\n",
    )
    _seed_example(
        examples_root,
        "misc",
        "skipme",
        "# %% [markdown]\n# # Skip\n\n# %%\nprint('bye')\n",
    )

    build_gallery(
        examples_root=examples_root,
        built_dir=built_dir,
        cache_root=cache_root,
        deps_fingerprint="testdeps==1.0",
        only=[wanted],
    )

    # The selected example is executed: its output is rendered.
    hello = (built_dir / "io" / "hello.md").read_text()
    assert '<div class="gallery-output" markdown>' in hello
    # The rest are rendered without running: the source is there, but no outputs.
    skip = (built_dir / "misc" / "skipme.md").read_text()
    assert "print('bye')" in skip
    assert "gallery-output" not in skip
    # It is not cached, so a later run would still execute it.
    assert not list(cache_root.glob("**/misc/skipme"))
    # The index still lists the full gallery.
    index_md = (examples_root / "index.md").read_text()
    assert "Hello" in index_md
    assert "Skip" in index_md


def test_build_gallery_raises_for_unknown_only_path(
    gallery_paths: GalleryPaths,
) -> None:
    examples_root, built_dir, cache_root = gallery_paths
    _seed_example(
        examples_root, "io", "hello", "# %% [markdown]\n# # Hi\n\n# %%\nx = 1\n"
    )

    with pytest.raises(ValueError, match="Not discoverable"):
        build_gallery(
            examples_root=examples_root,
            built_dir=built_dir,
            cache_root=cache_root,
            deps_fingerprint="testdeps==1.0",
            only=[examples_root / "io" / "ghost.py"],
        )


@pytest.mark.slow
def test_build_gallery_embeds_binder_launch_url(gallery_paths: GalleryPaths) -> None:
    examples_root, built_dir, cache_root = gallery_paths
    repo_root = examples_root.parent.parent

    _seed_example(
        examples_root,
        "io",
        "hello",
        "# %% [markdown]\n# # Hello\n\n# %%\nprint('hi')\n",
    )

    build_gallery(
        examples_root=examples_root,
        built_dir=built_dir,
        cache_root=cache_root,
        deps_fingerprint="testdeps==1.0",
        repo_root=repo_root,
        binder_repo="confusius-tools/confusius",
        binder_ref="v9.9.9",
    )

    md = (built_dir / "io" / "hello.md").read_text()
    expected = (
        "https://mybinder.org/v2/gh/confusius-tools/confusius/v9.9.9"
        "?urlpath=lab/tree/docs/examples/io/hello.py"
    )
    assert f"{{ .skip-lightbox .gallery-binder }}]({expected})" in md

    # A page restored from cache is stamped with the ref of the new build.
    build_gallery(
        examples_root=examples_root,
        built_dir=built_dir,
        cache_root=cache_root,
        deps_fingerprint="testdeps==1.0",
        repo_root=repo_root,
        binder_repo="confusius-tools/confusius",
        binder_ref="main",
    )

    md = (built_dir / "io" / "hello.md").read_text()
    assert f"]({expected.replace('v9.9.9', 'main')})" in md
    assert "v9.9.9" not in md


@pytest.mark.slow
def test_build_gallery_shows_the_error_thumbnail_of_an_example_that_raises(
    gallery_paths: GalleryPaths,
) -> None:
    """Also from the cache: the second build does not run the example again."""
    examples_root, built_dir, cache_root = gallery_paths
    for name in ("error_thumb.svg", "error_thumb_dark.svg"):
        (examples_root / "_assets" / name).write_text("<svg/>")
    _seed_example(examples_root, "io", "fine", "# %%\nprint('hi')\n")
    _seed_example(examples_root, "io", "broken", "# %%\nraise ValueError('no')\n")

    for _ in range(2):
        build_gallery(
            examples_root=examples_root,
            built_dir=built_dir,
            cache_root=cache_root,
            deps_fingerprint="testdeps==1.0",
        )

        index = (examples_root / "index.md").read_text()
        cards = {
            card.split("](")[1].split(")")[0]: card for card in index.split("-   ")[1:]
        }
        assert "error_thumb.svg#only-light" in cards["_built/io/broken.md"]
        assert "default_thumb.svg#only-light" in cards["_built/io/fine.md"]


_BOOM = "# %% [markdown]\n# # Boom\n\n# %%\nraise ValueError('boom in the example')\n"
_FINE = "# %% [markdown]\n# # Fine\n\n# %%\nprint('hi')\n"


@pytest.mark.slow
def test_build_gallery_aborts_at_the_first_example_that_raises_when_asked(
    gallery_paths: GalleryPaths,
) -> None:
    examples_root, built_dir, cache_root = gallery_paths
    failing = _seed_example(examples_root, "a_first", "boom", _BOOM)
    _seed_example(examples_root, "b_second", "fine", _FINE)

    with pytest.raises(ExampleError, match="ValueError: boom in the example") as raised:
        build_gallery(
            examples_root=examples_root,
            built_dir=built_dir,
            cache_root=cache_root,
            deps_fingerprint="testdeps==1.0",
            abort_on_error=True,
        )

    assert raised.value.source == failing
    assert not (built_dir / "b_second" / "fine.md").exists()
    assert not (examples_root / "index.md").exists()


@pytest.mark.slow
def test_build_gallery_runs_a_cached_example_that_raised_again_to_abort(
    gallery_paths: GalleryPaths,
) -> None:
    examples_root, built_dir, cache_root = gallery_paths
    _seed_example(examples_root, "io", "boom", _BOOM)
    build = partial(
        build_gallery,
        examples_root=examples_root,
        built_dir=built_dir,
        cache_root=cache_root,
        deps_fingerprint="testdeps==1.0",
    )

    # Without the option the error is content: on the page, and in the cache.
    build()
    assert "ValueError" in (built_dir / "io" / "boom.md").read_text()

    # An example that is not run is restored as it is.
    build(only=[], abort_on_error=True)

    with pytest.raises(ExampleError, match="ValueError: boom in the example"):
        build(abort_on_error=True)


def test_build_gallery_writes_the_backlinks_template_with_an_api_package(
    gallery_paths: GalleryPaths,
) -> None:
    examples_root, built_dir, cache_root = gallery_paths
    _seed_example(examples_root, "io", "hello", _FINE)
    build = partial(
        build_gallery,
        examples_root=examples_root,
        built_dir=built_dir,
        cache_root=cache_root,
        deps_fingerprint="testdeps==1.0",
        only=[],
    )
    written = (
        cache_root / "mkdocstrings" / "python" / "material" / "backlinks.html.jinja"
    )

    build()
    assert not written.exists()

    build(api_package="pkg")
    shipped = files("zallery").joinpath(
        "templates", "python", "material", "backlinks.html.jinja"
    )
    assert written.read_text(encoding="utf-8") == shipped.read_text(encoding="utf-8")

    # A project may name the folder, which keeps what it holds.
    own = cache_root.parent / "templates"
    (own / "python" / "material").mkdir(parents=True)
    (own / "python" / "material" / "class.html.jinja").write_text("the project's")
    shutil.rmtree(cache_root / "mkdocstrings")

    build(api_package="pkg", api_templates=own)
    moved = own / "python" / "material" / "backlinks.html.jinja"
    assert moved.read_text(encoding="utf-8") == shipped.read_text(encoding="utf-8")
    assert (own / "python" / "material" / "class.html.jinja").read_text() == (
        "the project's"
    )
    assert not (cache_root / "mkdocstrings").exists()
