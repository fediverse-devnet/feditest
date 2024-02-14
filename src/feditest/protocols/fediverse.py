"""
"""

from feditest.protocols import NodeDriver
from feditest.protocols.activitypub import ActivityPubNode
from feditest.protocols.webfinger import WebFingerServer


class FediverseNode(WebFingerServer, ActivityPubNode):
    def __init__(self, rolename: str, hostname: str, node_driver: 'NodeDriver') -> None:
        super().__init__(rolename, hostname, node_driver)
