"""
Abstractions for nodes that speak today's Fediverse protocol stack.
"""

from feditest.protocols import NodeDriver
from feditest.protocols.activitypub import ActivityPubNode
from feditest.protocols.webfinger import WebFingerServer


class FediverseNode(WebFingerServer, ActivityPubNode):
    """
    A Node that can participate in today's Fediverse.
    """
    pass # pylint: disable=unnecessary-pass
