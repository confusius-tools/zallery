"""Tests for zallery.references."""

from __future__ import annotations

import importlib
import sys
from collections.abc import Iterator

import pytest

from zallery.references import used_objects

_PACKAGE = "refs_pkg"
"""A package name of its own: `sys.modules` keeps the first module of a name."""


@pytest.fixture(scope="module")
def package(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    """Write and import a small package; return its name."""
    root = tmp_path_factory.mktemp("refs")
    source = root / _PACKAGE
    source.mkdir()
    # `load` and `Reader` are public under the package, defined in its modules.
    (source / "__init__.py").write_text(
        f"from {_PACKAGE}._impl import load\nfrom {_PACKAGE}.io import Reader\n"
    )
    (source / "_impl.py").write_text(
        "def load():\n    return 1\n\n\n"
        "def factory():\n    def inner():\n        return 1\n    return inner\n"
    )
    (source / "io.py").write_text(
        "class Base:\n"
        "    def close(self):\n        return None\n\n\n"
        "class Reader(Base):\n"
        "    evaluated = False\n\n"
        "    def read(self):\n        return 1\n\n"
        "    @property\n"
        "    def costly(self):\n"
        "        type(self).evaluated = True\n"
        "        return 1\n\n"
        "    def __getattr__(self, name):\n"
        "        raise RuntimeError('no attribute, and not an AttributeError')\n"
    )
    sys.path.insert(0, str(root))
    importlib.import_module(_PACKAGE)
    yield _PACKAGE
    sys.path.remove(str(root))
    for name in [m for m in sys.modules if m.partition(".")[0] == _PACKAGE]:
        del sys.modules[name]


def _run(source: str) -> dict[str, object]:
    """Run a cell and return the namespace it leaves, as a kernel has it."""
    namespace: dict[str, object] = {}
    exec(compile(source, "<cell>", "exec"), namespace)  # noqa: S102
    return namespace


def test_a_function_is_named_by_the_module_that_defines_it(package: str) -> None:
    source = f"import {package} as rp\nvalue = rp.load()\n"

    found = used_objects(source, _run(source), package)

    assert found == {f"{package}._impl.load": "load"}


def test_a_method_is_named_by_the_class_that_defines_it(package: str) -> None:
    source = (
        f"from {package} import Reader\n"
        "reader = Reader()\nreader.read()\nreader.close()\n"
    )

    found = used_objects(source, _run(source), package)

    assert found == {
        f"{package}.io.Reader": "Reader",
        f"{package}.io.Reader.read": "Reader.read",
        f"{package}.io.Base.close": "Base.close",
    }


def test_a_property_is_named_and_not_evaluated(package: str) -> None:
    source = f"from {package} import Reader\nreader = Reader()\n"
    namespace = _run(source)
    reader_class = namespace["Reader"]

    found = used_objects("reader.costly", namespace, package)

    assert found == {
        f"{package}.io.Reader": "Reader",
        f"{package}.io.Reader.costly": "Reader.costly",
    }
    assert reader_class.evaluated is False  # ty: ignore[unresolved-attribute]


def test_objects_of_other_packages_are_left_out(package: str) -> None:
    source = "import json\ntext = json.dumps([1])\nitems = [1, 2]\nitems.append(3)\n"

    assert used_objects(source, _run(source), package) == {}


def test_the_method_of_a_call_result_is_left_out(package: str) -> None:
    source = f"import {package} as rp\nvalue = rp.Reader().read()\n"

    found = used_objects(source, _run(source), package)

    # `read` is called on a value no name holds: only the class is known.
    assert found == {f"{package}.io.Reader": "Reader"}


@pytest.mark.parametrize(
    "cell",
    [
        "this is not python",
        "gone.attribute",
        "reader.no_such_attribute",
        "inner",
    ],
    ids=["syntax error", "unknown name", "getattr raises", "nested function"],
)
def test_what_cannot_be_named_is_left_out(package: str, cell: str) -> None:
    source = (
        f"import {package}._impl as impl\nfrom {package} import Reader\n"
        "reader = Reader()\ninner = impl.factory()\n"
    )
    namespace = _run(source)
    del namespace["Reader"]

    found = used_objects(cell, namespace, package)

    # The instance still names its class; nothing else is added.
    assert set(found) <= {f"{package}.io.Reader"}
