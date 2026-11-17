"""The API objects an example uses, found on the live objects of its kernel.

After each cell, the names the cell reads are looked up in the namespace of the
kernel. An object of the project's package is named by the module and the class
that define it: the name its API documentation knows it by, whatever name the
example imports it under. The cell reports those objects as an output of the mime
type `MIME`, which `zallery.render` turns into cross-references at the end of the
page.
"""

from __future__ import annotations

import ast
import functools
import inspect
from collections.abc import Mapping

MIME = "application/vnd.zallery.references+json"
"""Mime type of the report of a cell: the full name of each object of the package
the cell uses, mapped to its name within its module."""


def _dotted_names(source: str) -> set[str]:
    """Return the names a cell reads, with their attributes.

    Parameters
    ----------
    source : str
        Python source of the cell.

    Returns
    -------
    set[str]
        Names such as `np`, `np.linspace` and `ax.plot`: every name, and every
        chain of attributes that starts at a name. Empty for source that does not
        parse.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    names = set()
    for node in ast.walk(tree):
        parts: list[str] = []
        base = node
        while isinstance(base, ast.Attribute):
            parts.append(base.attr)
            base = base.value
        if isinstance(base, ast.Name):
            names.add(".".join([base.id, *reversed(parts)]))
    return names


def _defined_as(obj: object) -> tuple[str, str] | None:
    """Return the module and the qualified name an object is defined under.

    Parameters
    ----------
    obj : object
        Any object.

    Returns
    -------
    tuple[str, str] or None
        Those of a function, a method or a class; those of its class for any other
        object. `None` for a module, and for what no documentation can name, such
        as a function defined in another one.
    """
    if inspect.ismodule(obj):
        return None
    if inspect.ismethod(obj):
        obj = obj.__func__
    if not (inspect.isroutine(obj) or inspect.isclass(obj)):
        obj = type(obj)
    module = getattr(obj, "__module__", None)
    qualname = getattr(obj, "__qualname__", None)
    if not isinstance(module, str) or not isinstance(qualname, str) or "<" in qualname:
        return None
    return module, qualname


def _lookup(namespace: Mapping[str, object], dotted: str) -> tuple[str, str] | None:
    """Return the module and the qualified name of the object a dotted name reads.

    Parameters
    ----------
    namespace : Mapping[str, object]
        The namespace the name is read in.
    dotted : str
        A name with its attributes, such as `ax.plot`.

    Returns
    -------
    tuple[str, str] or None
        See `_defined_as`. A property is named by the class that defines it and is
        not read: it may compute, or load data. `None` when the name is not in the
        namespace or an attribute cannot be read.
    """
    head, *attributes = dotted.split(".")
    if head not in namespace:
        return None
    obj = namespace[head]
    for attribute in attributes:
        owner = obj if inspect.isclass(obj) else type(obj)
        static = inspect.getattr_static(owner, attribute, None)
        if isinstance(static, (property, functools.cached_property)):
            for cls in owner.__mro__:
                if attribute in vars(cls):
                    defined = _defined_as(cls)
                    if defined is not None:
                        return defined[0], f"{defined[1]}.{attribute}"
            return None
        try:
            obj = getattr(obj, attribute)
        except Exception:  # noqa: BLE001
            # Whatever the object raises: an attribute that cannot be read is
            # not an object to name.
            return None
    return _defined_as(obj)


def used_objects(
    source: str, namespace: Mapping[str, object], package: str
) -> dict[str, str]:
    """Return the objects of a package that a cell uses.

    Parameters
    ----------
    source : str
        Python source of the cell.
    namespace : Mapping[str, object]
        The namespace the cell ran in, as the cell left it.
    package : str
        Import name of the package whose objects count.

    Returns
    -------
    dict[str, str]
        The full name of each object, `module.qualified_name` as defined, mapped to
        its qualified name. An instance counts as a use of its class. A method
        called on the result of a call is not found: no name holds that result.
    """
    found: dict[str, str] = {}
    for dotted in sorted(_dotted_names(source)):
        defined = _lookup(namespace, dotted)
        if defined is not None and defined[0].partition(".")[0] == package:
            found[f"{defined[0]}.{defined[1]}"] = defined[1]
    return found


def install(package: str) -> None:
    """Report, after each cell of this kernel, the objects of a package it uses.

    Parameters
    ----------
    package : str
        Import name of the package whose objects count.
    """
    from IPython import get_ipython
    from IPython.display import publish_display_data

    shell = get_ipython()

    def report(result: object) -> None:
        """Publish the objects the cell used, after its own outputs.

        Parameters
        ----------
        result : IPython.core.interactiveshell.ExecutionResult
            The result of the cell, which holds its source.
        """
        try:
            # Magics and shell escapes become Python.
            source = shell.transform_cell(result.info.raw_cell)  # ty: ignore[unresolved-attribute]
            found = used_objects(source, shell.user_ns, package)
        except Exception:  # noqa: BLE001
            # IPython prints the error of a callback under the cell: the report
            # must not put text on the page of an example.
            return
        if found:
            publish_display_data({MIME: found})

    shell.events.register("post_run_cell", report)
