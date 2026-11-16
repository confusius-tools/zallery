"""The xarray integration: the colors of an xarray view in each scheme.

`Xarray.html` runs in the builder. The HTML view of an xarray object is one HTML
for both schemes, whose colors come from CSS variables: nothing is rethemed in the
kernel. xarray picks the values of those variables with selectors that do not
match Zensical's `data-md-color-scheme` attribute, so this module writes them for
each scheme, with the rules that make the view fit in a Zensical page.

xarray is not imported: the view is recognized in the HTML.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

from zallery.integration import Integration

_RULES = (
    ".xr-array-preview,.xr-array-preview span,.xr-preview,.xr-var-preview,.xr-var-dtype,.xr-var-dims,.xr-var-name,.xr-obj-type,.xr-obj-name{color:var(--xr-font-color0)!important;}"
    ".gallery-rich-output{overflow-x:auto;}"
    ".gallery-rich-output .xr-var-list,.gallery-rich-output .xr-dim-list,.gallery-rich-output .xr-attrs{padding-left:0!important;margin:0!important;list-style:none!important;}"
    # Zensical's `.md-typeset ul li` rule adds margin-left:1.25em to <li>
    # elements, including those inside .xr-dim-list.
    ".gallery-rich-output .xr-dim-list li{margin-left:0!important;}"
    # MkDocs Material's `.md-typeset ul:not([hidden])` has higher specificity
    # than xarray's `.xr-sections` and forces `display:flow-root`, collapsing
    # the grid. Force it back so each coordinate row stays on one line.
    ".gallery-rich-output .xr-sections{display:grid!important;}"
    # Same Material rule also clobbers `.xr-var-list` (another <ul>).
    ".gallery-rich-output .xr-var-list,.gallery-rich-output .xr-var-item{display:contents!important;}"
    ".gallery-rich-output .xr-var-name,.gallery-rich-output .xr-var-dims,.gallery-rich-output .xr-var-dtype,.gallery-rich-output .xr-var-preview{margin:0!important;}"
    # Dask's chunk SVG labels can sit near element boundaries; forcing
    # overflow visible prevents edge labels (e.g., diagonal chunk labels)
    # from being clipped in docs layout containers.
    ".gallery-rich-output .xr-array-data table,.gallery-rich-output .xr-array-data td,.gallery-rich-output .xr-array-data svg{overflow:visible!important;}"
    ".gallery-rich-output .xr-array-data svg text,.gallery-rich-output .xr-array-data svg tspan,.gallery-rich-output .xr-array-preview svg text,.gallery-rich-output .xr-array-preview svg tspan,.gallery-rich-output .xr-preview svg text,.gallery-rich-output .xr-preview svg tspan{fill:var(--xr-font-color0)!important;}"
    ".gallery-rich-output .xr-array-data svg{color:var(--xr-font-color0)!important;}"
    # Dask injects inline `stroke: rgb(0,0,0)` on the root SVG; in dark
    # mode we override stroke/text color explicitly to keep labels legible.
    "[data-md-color-scheme='slate'] .gallery-rich-output .xr-array-data svg{stroke:rgba(255,255,255,0.5)!important;}"
    "[data-md-color-scheme='slate'] .gallery-rich-output .xr-array-data svg text,[data-md-color-scheme='slate'] .gallery-rich-output .xr-array-data svg tspan{fill:rgba(255,255,255,0.92)!important;stroke:none!important;}"
)
"""Style rules that make an xarray view fit in a Zensical page, whatever the scheme."""


class Xarray(Integration):
    """The look of xarray views: the values of xarray's CSS variables per scheme.

    Attributes
    ----------
    type : None
        Nothing is rethemed in the kernel.
    variables : Mapping[str, tuple[str, str]]
        CSS variables of xarray's view, each with its light and its dark value.
    """

    variables: Mapping[str, tuple[str, str]] = {
        "--xr-font-color0": ("rgba(0,0,0,1)", "rgba(255,255,255,0.95)"),
        "--xr-font-color2": ("rgba(0,0,0,0.62)", "rgba(255,255,255,0.68)"),
        "--xr-font-color3": ("rgba(0,0,0,0.42)", "rgba(255,255,255,0.45)"),
        "--xr-border-color": ("var(--md-default-bg-color--lightest)", "#2a3347"),
        "--xr-disabled-color": ("rgba(0,0,0,0.35)", "rgba(255,255,255,0.28)"),
        "--xr-background-color": ("#fff", "#111720"),
        "--xr-background-color-row-even": ("#f8f9fb", "#161d29"),
        "--xr-background-color-row-odd": ("#edf0f5", "#1d2533"),
    }

    def html(self, html: str) -> str:
        """Return an xarray view as a Zensical page should hold it.

        The plain-text fallback is dropped, the view is shown (xarray hides it
        until its own style sheet loads), and the style rules and the variables
        of each scheme are added.

        Parameters
        ----------
        html : str
            An HTML output of an example.

        Returns
        -------
        str
            The view to write on the page; any other HTML as it is.
        """
        if "xr-wrap" not in html:
            return html
        html = re.sub(
            r"<pre class=['\"]xr-text-repr-fallback['\"]>.*?</pre>",
            "",
            html,
            flags=re.DOTALL,
        )
        html = html.replace(
            "<div class='xr-wrap' style='display:none'>", "<div class='xr-wrap'>"
        )
        html = html.replace(
            '<div class="xr-wrap" style="display:none">', '<div class="xr-wrap">'
        )
        schemes = "".join(
            f"[data-md-color-scheme='{scheme}'] .xr-wrap{{"
            + "".join(
                f"{name}: {values[index]};" for name, values in self.variables.items()
            )
            + "}"
            for index, scheme in enumerate(("default", "slate"))
        )
        return f"{html}\n<style>{_RULES}{schemes}</style>\n"
