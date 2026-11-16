"""Tests for zallery.integration."""

from __future__ import annotations

import importlib
import re
import sys
from collections.abc import Iterator
from contextlib import ExitStack
from pathlib import Path

import pytest
from IPython.core.interactiveshell import InteractiveShell
from IPython.display import display
from IPython.utils.capture import capture_output

from zallery import Integration
from zallery.integration import load, name, resolve, setup_kernel

_MODULE = (
    "from zallery import Integration\n"
    "class Mine(Integration):\n    type = 'a.B'\n"
    "class NotOne:\n    pass\n"
    "class Colon(Integration):\n    type = 'a:B'\n"
    "class Bare(Integration):\n    type = 'B'\n"
)


def test_integration_defaults_change_nothing() -> None:
    integration = Integration()
    assert integration.type is None
    assert integration.setup() is None
    assert integration.retheme(object(), "dark") is None
    assert integration.html("<b>x</b>") == "<b>x</b>"


def test_load_imports_classes_by_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "t1_mine.py").write_text(_MODULE)
    monkeypatch.syspath_prepend(tmp_path)
    (cls,) = load(["t1_mine:Mine"])
    assert name(cls) == "t1_mine:Mine"


@pytest.mark.parametrize(
    "entry",
    [
        "t1_bad.Mine",
        "t1_absent:Mine",
        "t1_bad:Absent",
        "t1_bad:NotOne",
        "t1_bad:Colon",
        "t1_bad:Bare",
    ],
)
def test_load_names_the_entry_it_rejects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, entry: str
) -> None:
    (tmp_path / "t1_bad.py").write_text(_MODULE)
    monkeypatch.syspath_prepend(tmp_path)
    with pytest.raises(ValueError, match=re.escape(entry)):
        load([entry])


def test_resolve_replaces_a_stock_class_by_its_subclass_and_adds_the_rest() -> None:
    class A(Integration): ...

    class B(Integration): ...

    class SubB(B): ...

    class New(Integration): ...

    assert resolve([], [A, B]) == [A, B]
    assert resolve([New, SubB], [A, B]) == [A, SubB, New]
    assert resolve([B], [A, B]) == [A, B]


def test_resolve_rejects_two_subclasses_of_one_stock_class() -> None:
    class A(Integration): ...

    class One(A): ...

    class Two(A): ...

    with pytest.raises(ValueError, match="One.*Two|Two.*One"):
        resolve([One, Two], [A])


@pytest.fixture
def shell() -> Iterator[InteractiveShell]:
    """An IPython shell in this process, as the kernel of an example has one."""
    instance = InteractiveShell.instance()
    yield instance
    InteractiveShell.clear_instance()


class Card:
    """A display Zallery does not know: an HTML repr that depends on a color."""

    def __init__(self) -> None:
        self.color = "black"

    def _repr_html_(self) -> str:
        return f'<p style="color:{self.color}">card</p>'


class Gold(Card):
    """A subclass of the type an integration names."""


class Cards(Integration):
    """An integration as a project would write it for `Card`."""

    type = f"{Card.__module__}.{Card.__qualname__}"

    def retheme(self, obj, scheme):
        if scheme == "light":
            return None
        stack = ExitStack()
        stack.callback(setattr, obj, "color", obj.color)
        obj.color = "white"
        return stack


def _shown(obj: object) -> list:
    """Display an object; return the outputs the shell published."""
    with capture_output() as captured:
        display(obj)
    return captured.outputs


def test_an_object_of_the_type_is_shown_with_its_dark_look(
    shell: InteractiveShell,
) -> None:
    Cards()._install(shell)
    card = Card()
    (output,) = _shown(card)
    assert "color:black" in output.data["text/html"]
    assert "color:white" in output.metadata["text/html"]["dark"]
    assert "text/plain" not in output.metadata
    assert card.color == "black"


def test_an_object_shown_twice_gives_the_same_output_twice(
    shell: InteractiveShell,
) -> None:
    Cards()._install(shell)
    card = Card()
    (first,), (second,) = _shown(card), _shown(card)
    assert first.data == second.data
    assert first.metadata == second.metadata


def test_an_object_of_a_subclass_is_rethemed_too(shell: InteractiveShell) -> None:
    Cards()._install(shell)
    (output,) = _shown(Gold())
    assert "color:white" in output.metadata["text/html"]["dark"]


def test_an_object_with_one_look_has_no_dark_variant(shell: InteractiveShell) -> None:
    class Plain(Cards):
        def retheme(self, obj, scheme):
            return None

    Plain()._install(shell)
    (output,) = _shown(Card())
    assert "color:black" in output.data["text/html"]
    assert "dark" not in output.metadata.get("text/html", {})


def test_a_retheme_that_raises_leaves_the_light_output_and_the_object(
    shell: InteractiveShell,
) -> None:
    class Broken(Cards):
        def retheme(self, obj, scheme):
            if scheme == "dark":
                raise RuntimeError("no dark look")

    Broken()._install(shell)
    card = Card()
    outputs = _shown(card)
    assert any("color:black" in o.data.get("text/html", "") for o in outputs)
    assert card.color == "black"


def test_an_integration_without_type_installs_nothing(shell: InteractiveShell) -> None:
    Integration()._install(shell)
    (output,) = _shown(Card())
    assert "dark" not in output.metadata.get("text/html", {})


def test_setup_kernel_sets_up_then_installs_each_class(
    shell: InteractiveShell, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "t7_order.py").write_text(
        "from zallery import Integration\n"
        "calls = []\n"
        "class One(Integration):\n"
        "    def setup(self): calls.append('setup one')\n"
        "    def _install(self, shell): calls.append('install one')\n"
        "class Two(One):\n"
        "    def setup(self): calls.append('setup two')\n"
        "    def _install(self, shell): calls.append('install two')\n"
    )
    monkeypatch.syspath_prepend(tmp_path)
    setup_kernel(["t7_order:One", "t7_order:Two"])
    assert sys.modules["t7_order"].calls == [
        "setup one",
        "setup two",
        "install one",
        "install two",
    ]


_BADGES = (
    "class Badge:\n"
    "    color = 'black'\n"
    "    def _repr_html_(self):\n"
    "        return f'<p style=\"color:{self.color}\">badge</p>'\n"
    "class Outer:\n"
    "    class Inner(Badge):\n"
    "        pass\n"
)


def _package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, package: str) -> None:
    """Write a package that defines `Badge` in a submodule and re-exports it."""
    (tmp_path / package).mkdir()
    (tmp_path / package / "__init__.py").write_text(
        f"from {package}.badge import Badge, Outer\n"
    )
    (tmp_path / package / "badge.py").write_text(_BADGES)
    monkeypatch.syspath_prepend(tmp_path)


def test_a_type_is_the_name_a_class_is_imported_with(
    shell: InteractiveShell, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`mylib.Badge` names a class that `mylib/badge.py` defines."""
    _package(tmp_path, monkeypatch, "t11_alias")

    class Badges(Cards):
        type = "t11_alias.Badge"

    Badges()._install(shell)
    # The library is imported after the kernel is set up, by the example.
    library = importlib.import_module("t11_alias")
    (output,) = _shown(library.Badge())
    assert "color:white" in output.metadata["text/html"]["dark"]


def test_a_type_may_name_a_class_nested_in_another(
    shell: InteractiveShell, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _package(tmp_path, monkeypatch, "t11_nested")

    class Inners(Cards):
        type = "t11_nested.badge.Outer.Inner"

    Inners()._install(shell)
    library = importlib.import_module("t11_nested")
    (output,) = _shown(library.Outer.Inner())
    assert "color:white" in output.metadata["text/html"]["dark"]
    # The class it derives from is not of that type.
    (plain,) = _shown(library.Badge())
    assert "dark" not in plain.metadata.get("text/html", {})
