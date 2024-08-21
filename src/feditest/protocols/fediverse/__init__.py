"""
Abstractions for nodes that speak today's Fediverse protocol stack.
"""

from typing import cast

from feditest.protocols import NotImplementedByNodeError
from feditest.protocols.activitypub import ActivityPubNode
from feditest.protocols.webfinger import FallbackWebFingerServer, WebFingerClient, WebFingerQueryResponse, WebFingerServer
from feditest.testplan import TestPlanConstellationNode, TestPlanError
from feditest.utils import http_https_acct_uri_parse_validate

class FediverseNode(WebFingerClient, WebFingerServer, ActivityPubNode):
    """
    A Node that can participate in today's Fediverse.
    The methods defined on FediverseNode reflect -- well, try to start reflecting, we are only
    learning what those are -- what users expect of the Fediverse.
    """

    def make_create_note(self, actor_uri: str, content: str, deliver_to: list[str] | None = None) -> str:
        """"
        Perform whatever actions are necessary to the actor with actor_uri will have created a Note
        on this Node. The optional arguments allow the creation of variations.
        deliver_to: make sure the Node is delivered to these Actors (i.e. in arrives in their inbox)
        """
        raise NotImplementedByNodeError(self, FediverseNode.make_create_note)


    def wait_for_object_in_inbox(self, actor_uri: str, object_uri: str) -> str:
        """
        """
        raise NotImplementedByNodeError(self, FediverseNode.wait_for_object_in_inbox)


    def make_announce_object(self, actor_uri, note_uri: str) -> str:
        """
        """
        raise NotImplementedByNodeError(self, FediverseNode.make_announce_object)


    def make_reply(self, actor_uri, note_uri: str, reply_content: str) -> str:
        """
        """
        raise NotImplementedByNodeError(self, FediverseNode.make_reply)


    def make_a_follow_b(self, a_uri_here: str, b_uri_there: str, node_there: 'ActivityPubNode') -> None:
        """
        Perform whatever actions are necessary so that actor with URI a_uri_here, which
        is hosted on this ActivityPubNode, is following actor with URI b_uri_there,
        which is hosted on ActivityPubNode node_there. Only return when the follow
        relationship is fully established.
        """
        raise NotImplementedByNodeError(self, FediverseNode.make_a_follow_b)
