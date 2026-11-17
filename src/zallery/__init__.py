"""Build a light-and-dark example gallery for Zensical docs from jupytext scripts.

Examples are percent-format `.py` files executed once in an ipykernel; each
output is rendered for both color schemes from that single run. What changes
between the two is said by integration classes, one for each display library
(see [`Integration`][zallery.Integration]). [`build_gallery`][zallery.build_gallery]
runs the whole pipeline: discover, cache, execute, render, index.
"""

from zallery.execute import ExampleError
from zallery.integration import Integration
from zallery.pipeline import build_gallery

__all__ = ["ExampleError", "Integration", "build_gallery"]
