"""
Abstractions for the ActivityPub protocol
"""

from feditest.nodedrivers import NotImplementedByNodeError
from feditest.protocols.web import WebServer


class ActivityPubNode(WebServer):
    """
    A Node that can speak ActivityPub.
    """
    def obtain_actor_document_uri(self, rolename: str | None = None) -> str:
        """
        Smart factory method to return the URI to an Actor document on this Node that
        either exists already or is newly created. Different rolenames produce different
        results; the same rolename produces the same result.
        rolename: refer to this Actor by this rolename; used to disambiguate multiple
           Actors on the same server by how they are used in tests
        return: the URI
        """
        raise NotImplementedByNodeError(self, ActivityPubNode.obtain_actor_document_uri)
