"""
A NodeDriver that supports all protocols but doesn't automate anything.
"""

from feditest import nodedriver
from feditest.nodedrivers import AbstractManualWebServerNodeDriver


@nodedriver
class ManualFediverseNodeDriver(AbstractManualWebServerNodeDriver):
    """
    A NodeDriver that supports all web server-side protocols but doesn't automate anything.
    """
    pass
