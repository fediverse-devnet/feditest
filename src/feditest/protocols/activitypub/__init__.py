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
        Smart factory method to return the https URI to an Actor document on this Node that
        either exists already or is newly created. Different rolenames produce different
        results; the same rolename produces the same result.
        rolename: refer to this Actor by this rolename; used to disambiguate multiple
           Actors on the same server by how they are used in tests
        return: the URI
        """
        raise NotImplementedByNodeError(self, ActivityPubNode.obtain_actor_document_uri)

    # You might expect lots of more methods here. Sorry to disappoint. But there's a reason:
    #
    # Example: you might expect a method that checks that some actor A is following actor B
    # (which is hosted on this ActivityPubNode). You might think that could be implemented
    # in one of the following ways:
    #
    #  * an API call to the ActivityPubNode or a database query. Yep, it could, but that's
    #    a lot of work to implement, and many applications don't have such an API.
    #
    #  * find the following collection of actor B, and look into that collection. That would
    #    require "something" to perform HTTP GET requests oforn B's actor document, and the
    #    collection URIs. That works, but who is that "something"? It cannot be FediTest,
    #    otherwise FediTest would become its own Node in the current Constellation, thereby
    #    changing it quite a bit. This is particularly important when applications require
    #    authorized fetch to fetch follower collections, and suddenly FediTest needs to
    #    first exchange public keys etc. and for that it would have to be an HTTP server,
    #    with DNS and TLS certs and nope, we are not going there.
    #
    # Instead, we ask an ActivityPubDiagNode in the Constellation to perform the fetch
    # of the followers collection on our behalf. It is already part of the Constellation
    # and likely has already exchanged keys.
    #
    # So: you find what you want on the "other" Node which is likeley an ActivityPubDiagNode
    # anyway.
