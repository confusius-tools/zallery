"""Integration classes: what a display library needs, and its look in each scheme.

Zallery runs an example once and shows each output for the light and for the dark
color scheme. An integration class says what changes between the two for the
objects of one library: [`Integration`][zallery.integration.Integration] is the
base class, and Zallery ships one subclass for each library it supports (`STOCK`).
A project subclasses one to change its look, or writes its own for another
library, and names the class in the `integrations` key of `[tool.zallery]`.

A class is used in two processes. `setup` and `retheme` run in the kernel of each
example; `html` runs in the builder.
"""

from __future__ import annotations

import importlib
from collections.abc import Sequence
from contextlib import AbstractContextManager
from typing import Any, Literal

Scheme = Literal["light", "dark"]
"""A color scheme of the site."""

STOCK: tuple[str, ...] = (
    "zallery.matplotlib:Matplotlib",
    "zallery.plotly:Plotly",
    "zallery.pyvista:PyVista",
    "zallery.xarray:Xarray",
)
"""Names of the integration classes Zallery ships, in the order they are used."""


class Integration:
    """What one display library needs, and how its outputs change with the scheme.

    Subclass it, set `type`, and override the methods the library needs. A
    subclass is instantiated with no argument, once in each kernel and once in the
    builder.

    Attributes
    ----------
    type : str or None
        Dotted name of the class whose objects `retheme` handles, subclasses
        included, such as `"matplotlib.figure.Figure"`. `None` for an integration
        with nothing to retheme in the kernel.
    """

    type: str | None = None

    def setup(self) -> None:
        """Prepare the library for the light scheme, before the example runs.

        Runs in the kernel, once, before the first cell. It must not import a
        library the example may not use. The default does nothing.
        """

    def retheme(
        self, obj: Any, scheme: Scheme, /
    ) -> AbstractContextManager[Any] | None:
        """Give an object the look of a color scheme, until the rendering is taken.

        Runs in the kernel. Zallery calls it for `"light"`, then for `"dark"`, each
        time just before it takes the rendering for that scheme. The object arrives
        both times as the example left it. The default changes nothing. Both
        arguments are passed by position: a subclass names them as it likes.

        Parameters
        ----------
        obj : Any
            An object of the class named by `type`, to change in place.
        scheme : {"light", "dark"}
            The color scheme the next rendering is for.

        Returns
        -------
        contextlib.AbstractContextManager or None
            A context manager whose exit restores every change, also when the
            rendering fails. `None` when nothing was changed: Zallery may then
            reuse a rendering it already has.
        """
        return None

    def html(self, html: str) -> str:
        """Return an HTML output as the page should hold it.

        Runs in the builder, on each HTML output of a page. It is for a display
        whose two looks are one HTML driven by CSS. The default returns the
        output as it is.

        Parameters
        ----------
        html : str
            An HTML output of an example.

        Returns
        -------
        str
            The HTML to write on the page.
        """
        return html


def name(cls: type[Integration]) -> str:
    """Return the name that designates an integration class in the configuration.

    Parameters
    ----------
    cls : type[Integration]
        An integration class.

    Returns
    -------
    str
        The class as `"module:Class"`, which `load` reads back.
    """
    return f"{cls.__module__}:{cls.__qualname__}"


def load(names: Sequence[str]) -> list[type[Integration]]:
    """Import integration classes from their names.

    Parameters
    ----------
    names : Sequence[str]
        Classes as `"module:Class"`, each importable from `sys.path`.

    Returns
    -------
    list[type[Integration]]
        The classes, in the order given.

    Raises
    ------
    ValueError
        If a name has no colon, does not import, is not a subclass of
        `Integration`, or has a `type` that is not a dotted class name. The
        message holds the name.
    """
    classes: list[type[Integration]] = []
    for entry in names:
        module_name, _, attribute = entry.partition(":")
        if not module_name or not attribute:
            raise ValueError(f'{entry!r} is not a "module:Class" name.')
        try:
            cls: Any = importlib.import_module(module_name)
            for part in attribute.split("."):
                cls = getattr(cls, part)
        except Exception as exc:
            # Whatever the module raises when imported is the project's to fix.
            raise ValueError(f"{entry!r} does not import: {exc}") from exc
        if not (isinstance(cls, type) and issubclass(cls, Integration)):
            # A wrong name in a list of the configuration: a bad value, as the
            # other cases are, for one kind of error to catch.
            raise ValueError(  # noqa: TRY004
                f"{entry!r} is not a subclass of zallery.Integration."
            )
        target = cls.type
        if target is not None and not (
            isinstance(target, str) and "." in target and ":" not in target
        ):
            raise ValueError(
                f"{entry!r}: type must be the dotted name of a class, such as "
                f'"matplotlib.figure.Figure", not {target!r}.'
            )
        classes.append(cls)
    return classes


def resolve(
    listed: Sequence[type[Integration]], stock: Sequence[type[Integration]]
) -> list[type[Integration]]:
    """Return the classes in effect: the stock ones, changed by those a project lists.

    Parameters
    ----------
    listed : Sequence[type[Integration]]
        Classes the project names.
    stock : Sequence[type[Integration]]
        Classes Zallery ships.

    Returns
    -------
    list[type[Integration]]
        The stock classes in their order, each replaced by the listed class that
        subclasses it, then the other listed classes in the order given.

    Raises
    ------
    ValueError
        If two listed classes subclass the same stock class.
    """
    effective = list(stock)
    added: list[type[Integration]] = []
    replaced: dict[int, type[Integration]] = {}
    for cls in listed:
        index = next((i for i, base in enumerate(stock) if issubclass(cls, base)), None)
        if index is None:
            added.append(cls)
            continue
        other = replaced.setdefault(index, cls)
        if other is not cls:
            raise ValueError(
                f"{name(other)} and {name(cls)} both subclass {name(stock[index])}: "
                "list one of them."
            )
        effective[index] = cls
    return effective + added
