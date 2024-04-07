"""
Abstractions for nodes that speak today's Fediverse protocol stack.
"""

from feditest.protocols.activitypub import ActivityPubNode
from feditest.protocols.webfinger import WebFingerServer


class FediverseNode(WebFingerServer, ActivityPubNode):
    pass
