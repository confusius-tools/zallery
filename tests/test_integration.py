"""Tests for zallery.integration."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from zallery import Integration
from zallery.integration import load, name, resolve

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
