"""
Abstractions for the ActivityPub protocol
"""

from typing import Any, cast

from hamcrest import is_not
from feditest.protocols.activitypub.utils import is_member_of_collection_at

from feditest import InteropLevel, SpecLevel, assert_that
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
    def __init__(self, uri: str, json_data: Any):
        self.uri = uri
        self.json = json_data


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
    """
    A Node that can speak ActivityPub.
    """
    # Use superclass constructor

    def obtain_actor_document_uri(self, actor_rolename: str | None = None) -> str:
        """
        Return the URI that leads to an Actor document that either exists already or is
        newly created.
        rolename: refer to this actor by this rolename; used to disambiguate multiple actors on the same server
        return: the URI
        """
        if actor_rolename:
            return cast(str, self.prompt_user(
                    f'Please enter an URI at Node "{self._rolename}" that serves an ActivityPub Actor document for the actor in role "{actor_rolename}": ',
                    self.parameter('node-uri'),
                    http_https_uri_validate))

        return cast(str, self.prompt_user(
                f'Please enter an URI at Node "{self._rolename}" that serves an ActivityPub Actor document: ',
                self.parameter('node-uri'),
                http_https_uri_validate))


    def obtain_followers_collection_uri(self, actor_uri: str) -> str:
        """
        Determine the URI that points to the provided actor's followers collection.
        """
        return cast(str, self.prompt_user(
                f'Enter the URI of the followers collection of actor "{actor_uri}": ',
                http_https_uri_validate))


    def obtain_following_collection_uri(self, actor_uri: str) -> str:
        """
        Determine the URI that points to the provided actor's following collection.
        """
        return cast(str, self.prompt_user(
                f'Enter the URI of the following collection of actor "{actor_uri}": ',
                http_https_uri_validate))


    def assert_member_of_collection_at(self,
        candidate_member_uri: str,
        collection_uri: str,
        spec_level: SpecLevel | None = None,
        interop_level: InteropLevel | None= None):
        """
        Raise an AssertionError if candidate_member_uri is a member of the collection at collection_uri
        """
        assert_that(candidate_member_uri, is_member_of_collection_at(collection_uri, self), spec_level=spec_level, interop_level=interop_level)


    def assert_not_member_of_collection_at(self,
        candidate_member_uri: str,
        collection_uri: str,
        spec_level: SpecLevel | None = None,
        interop_level: InteropLevel | None= None):
        """
        Raise an AssertionError if candidate_member_uri is not a member of the collection at collection_uri
        """
        assert_that(candidate_member_uri, is_not(is_member_of_collection_at(collection_uri, self)), spec_level=spec_level, interop_level=interop_level)
