"""
Abstractions for nodes that speak today's Fediverse protocol stack.
"""

from typing import cast

from feditest.protocols.activitypub import ActivityPubNode
from feditest.protocols.webfinger import WebFingerServer


class FediverseNode(WebFingerServer, ActivityPubNode):
    """
    A Node that can participate in today's Fediverse.
    """

    def make_create_note(self, actor_uri: str, content: str) -> str:
        """"
        Perform whatever actions are necessary to the actor with actor_uri will have created a Note
        on this Node. Determine the various Note and Activity properties as per this Node's defaults.
        """
        return cast(str, self.prompt_user(
                f'On FediverseNode "{ self.hostname }", make actor "{ actor_uri }" create a Note'
                + ' and enter its URI when created.'
                + f' Note content:"""\n{ content }\n"""' ))


    def wait_for_object_in_inbox(self, actor_uri: str, note_uri: str) -> str:
        """
        """
        return cast(str, self.prompt_user(
                f'On FediverseNode "{ self.hostname }", wait until in actor "{ actor_uri }"\'s inbox,'
                + f' Note with URI "{ note_uri }" has appeared and enter its local URI:'))


    def make_announce_object(self, actor_uri, note_uri: str) -> str:
        """
        """
        return cast(str, self.prompt_user(
                f'On FediverseNode "{ self.hostname }", make actor "{ actor_uri }" boost "{ note_uri }"'
                + ' and enter the boost activity\' local URI:'))


    def make_reply(self, actor_uri, note_uri: str, reply_content: str) -> str:
        """
        """
        return cast(str, self.prompt_user(
                f'On FediverseNode "{ self.hostname }", make actor "{ actor_uri }" reply to object with "{ note_uri }"'
                + ' and enter its URI when created.'
                + f' Reply content:"""\n{ reply_content }\n"""' ))


    def make_a_follow_b(self, a_uri_here: str, b_uri_there: str, node_there: 'ActivityPubNode') -> None:
        """
        Perform whatever actions are necessary so that actor with URI a_uri_here, which
        is hosted on this ActivityPubNode, is following actor with URI b_uri_there,
        which is hosted on ActivityPubNode node_there. Only return when the follow
        relationship is fully established.
        """
        self.prompt_user(
                f'On FediverseNode "{ self.hostname }", make actor "{ a_uri_here }" follow actor "{ b_uri_there }" and hit return once the relationship is fully established.' )
