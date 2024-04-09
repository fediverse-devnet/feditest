"""
Abstractions for the ActivityPub protocol
"""

import httpx
from typing import Any

from feditest.protocols.web import WebServer
from feditest.utils import http_https_uri_validate


class Actor:
    """
    A local copy of the content of an Actor at the ActivityPubNode.
    FIXME: incomplete
    """
    def __init__(self, actor_uri: str):
        self.actor_uri : str = actor_uri
        self.followers : list[str] = []
        self.following : list[str] = []


# Note:
# The data elements held by the classes here are all untyped. That's because we want to be able
# to store data we receive even if it is invalid according to the spec.
# check_integrity() helps figure out whether it is valid or not.

class AnyObject:
    """
    This container is used to hold any instance of any of the ActivityStreams types.
    We use a generic container because we also want to be able to hold objects
    that are invalid according to the spec.
    """
    def __init__(self, uri: str, json: Any):
        self.uri = uri
        self.json = json


    def check_is_valid_object(self):
        """
        Interpret this instance as an ActivityStreams Object, and check whether it is valid.
        """
        return 'type' in self.json and 'Object' == self.json['type']


    def as_actor(self):
        """
        Interpret this instance as an Actor, and return an instance of the Actor class.
        """



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
        return self.node_driver().prompt_user(
                f'On ActivityPub node {node_there.get_hostname()}, make actor {a_uri_here} follow actor {b_uri_there} and hit return once the relationship is fully established.' )


    class NotFoundError(RuntimeError):
        """
        There was a 404 or such a the supposed URI.
        """
        def __init__(self, uri: str, response: httpx.Response ):
            self.uri : str = uri
            self.http_response : httpx.Response = response


    class NotAnActorError(RuntimeError):
        """
        There was content at the supposed Actor URI but the content was invalid
        for an Actor document.
        """
        def __init__(self, uri: str):
            self.uri = uri


