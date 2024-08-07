"""
Abstractions for nodes that speak today's Fediverse protocol stack.
"""

from typing import cast

from feditest.protocols.activitypub import ActivityPubNode
from feditest.protocols.webfinger import WebFingerServer


class FediverseNode(WebFingerServer, ActivityPubNode):
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
        if deliver_to :
            return cast(str, self.prompt_user(
                    f'On FediverseNode "{ self.hostname }", make actor "{ actor_uri }" create a Note'
                    + ' to be delivered to ' + ", ".join(deliver_to)
                    + ' and enter its URI when created.'
                    + f' Note content:"""\n{ content }\n"""' ))
        return cast(str, self.prompt_user(
                f'On FediverseNode "{ self.hostname }", make actor "{ actor_uri }" create a Note'
                + ' and enter its URI when created.'
                + f' Note content:"""\n{ content }\n"""' ))


    def wait_for_object_in_inbox(self, actor_uri: str, object_uri: str) -> str:
        """
        """
        return cast(str, self.prompt_user(
                f'On FediverseNode "{ self.hostname }", wait until in actor "{ actor_uri }"\'s inbox,'
                + f' the object with URI "{ object_uri }" has appeared and enter its local URI:'))


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
