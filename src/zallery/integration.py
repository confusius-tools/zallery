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
import sys
import warnings
from collections.abc import Sequence
from contextlib import AbstractContextManager, ExitStack
from functools import partial
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from IPython.core.interactiveshell import InteractiveShell

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
        included, such as `"matplotlib.figure.Figure"`: the name an example
        imports the class with, or the one of the module that defines it. `None`
        for an integration with nothing to retheme in the kernel.
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

    def _install(self, shell: InteractiveShell) -> None:
        """Have the kernel show the objects of `type` once for each scheme.

        The generic capture: it serves any object IPython's formatters can show.
        The library of the class is not imported: the class is looked up by name
        each time IPython shows an object, and registered once an example has
        imported it. IPython's own registration by name would match only the
        module that defines a class, not the name it is imported with
        (`pandas.DataFrame`), nor a class nested in another. A stock class whose
        library does not display through the formatters replaces this method.

        Parameters
        ----------
        shell : IPython.core.interactiveshell.InteractiveShell
            The shell of the kernel.
        """
        dotted = self.type
        if dotted is None:
            return
        # IPython annotates the formatter as optional; a running shell has one.
        handler = shell.display_formatter.ipython_display_formatter  # ty: ignore[unresolved-attribute]
        show = partial(self._display, shell=shell)
        lookup = handler.lookup_by_type

        def lookup_by_type(typ: Any) -> Any:
            """Register the class if it is imported by now, then look up as usual.

            Parameters
            ----------
            typ : type
                The class of the object IPython is about to show.

            Returns
            -------
            Callable
                The handler IPython has for that class.
            """
            cls = _resolve(dotted)
            if cls is not None and cls not in handler.type_printers:
                # Not `for_type`: it looks the class up first, which is this.
                handler.type_printers[cls] = show
            return lookup(typ)

        # The one place IPython passes through for every object it shows.
        handler.lookup_by_type = lookup_by_type

    def _display(self, obj: Any, *, shell: InteractiveShell) -> None:
        """Publish one output for an object: its light look, the dark one beside it.

        The object goes through IPython's formatters under `retheme` for each
        scheme. The dark payload of each mime type that differs from the light
        one goes in the metadata of that type, under `"dark"`.

        Parameters
        ----------
        obj : Any
            An object of the class named by `type`, being displayed.
        shell : IPython.core.interactiveshell.InteractiveShell
            The shell of the kernel.
        """
        from IPython.display import publish_display_data

        formatter: Any = shell.display_formatter
        handler = formatter.ipython_display_formatter
        bundles: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
        for scheme in ("light", "dark"):
            with ExitStack() as stack:
                look = self.retheme(obj, scheme)
                if look is None and scheme == "dark":
                    # The dark look is the light one.
                    break
                if look is not None:
                    stack.enter_context(look)
                # Off, or `format` would come back here.
                stack.callback(setattr, handler, "enabled", handler.enabled)
                handler.enabled = False
                bundles[scheme] = formatter.format(obj)
        data, metadata = bundles["light"]
        dark, _ = bundles.get("dark", ({}, {}))
        for mime, payload in dark.items():
            # The text of an object is not a look.
            if mime != "text/plain" and payload != data.get(mime):
                metadata.setdefault(mime, {})["dark"] = payload
        publish_display_data(data, metadata)


def _resolve(dotted: str) -> type | None:
    """Return the class a dotted name designates, if its module is imported.

    Parameters
    ----------
    dotted : str
        A class as `"module.Class"`; the class may be nested in another.

    Returns
    -------
    type or None
        The class. `None` while no module of that name is imported, or if the
        rest of the name is not a class of it.
    """
    parts = dotted.split(".")
    for count in range(len(parts) - 1, 0, -1):
        obj: Any = sys.modules.get(".".join(parts[:count]))
        if obj is None:
            continue
        for part in parts[count:]:
            obj = getattr(obj, part, None)
        return obj if isinstance(obj, type) else None
    return None


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


def setup_kernel(names: Sequence[str]) -> None:
    """Configure the running kernel for the integration classes in effect.

    Runs in the kernel, in a cell of its own before the first cell of the example.
    Each class is instantiated and set up, in order; then each one arranges the
    capture of its objects.

    Parameters
    ----------
    names : Sequence[str]
        The classes in effect, as `"module:Class"`, importable from the kernel.
        The builder resolves them (see `resolve`): the kernel uses them as given.
    """
    from IPython import get_ipython

    warnings.filterwarnings("ignore", message="IProgress not found.*")
    # rich.live.Live.refresh() warns once per process the first time it detects a
    # Jupyter kernel without ipywidgets installed; it would land in the rendered
    # output of whichever cell happens to trigger it.
    warnings.filterwarnings(
        "ignore", message='install "ipywidgets" for Jupyter support'
    )
    integrations = [cls() for cls in load(names)]
    for integration in integrations:
        integration.setup()
    shell = get_ipython()
    for integration in integrations:
        integration._install(shell)
