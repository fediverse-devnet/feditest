"""
Abstractions for the ActivityPub protocol
"""

from feditest.protocols import NodeDriver
from feditest.protocols.web import WebServer
from feditest.utils import http_https_uri_validate


class ActivityPubNode(WebServer):
    # Use superclass constructor

    def obtain_actor_document_uri(self, actor_rolename: str = None) -> str:
        """
        Return the URI that leads to an Actor document that either exists already or is
        newly created.
        rolename: refer to this actor by this rolename; used to disambiguate multiple actors on the same server
        return: the URI
        """
        if actor_rolename:
            return self.node_driver.prompt_user(
                    f'Please enter an URI at node {self._rolename} that serves an ActivityPub Actor document for actor in role {actor_rolename}:',
                    http_https_uri_validate )
        else:
            return self.node_driver.prompt_user(
                    f'Please enter an URI at node {self._rolename} that serves an ActivityPub Actor document:',
                    http_https_uri_validate )

    def make_a_follow_b(self, a_uri_here: str, b_uri_there: str, node_there: 'ActivityPubNode') -> None:
        """
        Perform whatever actions are necessary so that actor with URI a_uri_here, which
        is hosted on this ActivityPubNode, is following actor with URI b_uri_there,
        which is hosted on ActivityPubNode node_there. Only return when the follow
        relationship is fully established.
        """
        return self.node_driver.prompt_user(
                f'On ActivityPub node {node_there._hostname}, make actor {a_uri_here} follow actor {b_uri_there} and hit return when established.' )
