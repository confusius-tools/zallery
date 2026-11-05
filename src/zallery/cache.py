"""Cache key + cache directory helpers for the gallery builder."""

from __future__ import annotations

import hashlib
from pathlib import Path

from zallery._types import ExampleSpec


def cache_key(
    spec: ExampleSpec,
    *,
    deps_fingerprint: str,
    python_version: str,
) -> str:
    """Compute a deterministic cache key for one example.

    Parameters
    ----------
    spec : ExampleSpec
        The example; its source file content is part of the key.
    deps_fingerprint : str
        Text identifying everything else that shapes the render (lockfile,
        builder sources, configuration).
    python_version : str
        Version of the Python interpreter the example runs under.

    Returns
    -------
    str
        SHA-256 hex digest of the three inputs.
    """
    digest = hashlib.sha256()
    digest.update(spec.source.read_bytes())
    digest.update(b"\x00")
    digest.update(deps_fingerprint.encode("utf-8"))
    digest.update(b"\x00")
    digest.update(python_version.encode("utf-8"))
    return digest.hexdigest()


def cache_dir(root: Path, key: str) -> Path:
    """Return the cache directory for `key` rooted at `root`.

    Parameters
    ----------
    root : pathlib.Path
        Cache root directory.
    key : str
        Cache key of one example, see `cache_key`.

    Returns
    -------
    pathlib.Path
        Directory holding that example's cached artifacts.
    """
    return root / key
