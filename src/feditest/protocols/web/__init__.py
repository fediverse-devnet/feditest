"""
Types for Nodes that act as HTTP clients and servers.
"""

from feditest.nodedrivers import Node


class WebClient(Node):
    """
    Abstract class used for Nodes that speak HTTP as client.
    """
    pass


class WebServer(Node):
    """
    Abstract class used for Nodes that speak HTTP as server.
    """
    pass
