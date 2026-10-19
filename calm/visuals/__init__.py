"""Registry of graphics modules for the Visuals tab.

Add new ``BaseVisual`` subclasses to ``VISUALS``. When there is more than
one, the Visuals tab shows a picker. While it is empty the tab shows a
"Coming soon" placeholder.
"""

from calm.visuals.base import BaseVisual
from calm.visuals.bokeh_tunnel import BokehTunnel

VISUALS: list[type[BaseVisual]] = [BokehTunnel]

__all__ = ["BaseVisual", "VISUALS"]
