"""
"""

from feditest.protocols import NodeDriver
from feditest.protocols.web import WebServer
from feditest.utils import http_https_uri_validate


class ActivityPubNode(WebServer):
    def __init__(self, rolename: str, hostname: str, node_driver: 'NodeDriver') -> None:
        super().__init__(rolename, hostname, node_driver)

    def obtain_actor_document_uri(self, rolename: str = None) -> str:
        """
        Return the URI that leads to an Actor document that either exists already or is
        newly created.
        rolename: refer to this actor by this rolename; used to disambiguate multiple actors on the same server
        return: the URI
        """
        if rolename:
            return self.node_driver.prompt_user(
                    f'Please enter an URI at this ActivityPubNode that serves an ActivityPub Actor document for actor {rolename}:',
                    http_https_uri_validate )
        else:
            return self.node_driver.prompt_user(
                    'Please enter an URI at this ActivityPubNode that serves an ActivityPub Actor document:',
                    http_https_uri_validate )

    def make_a_follow_b(self, a: str, b: str) -> None:
        ...
