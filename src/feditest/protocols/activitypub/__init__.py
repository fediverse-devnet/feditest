"""
Abstractions for the ActivityPub protocol
"""

from typing import Any, Callable, Iterator, cast

import httpx
from hamcrest import is_not
from feditest.protocols.activitypub.utils import is_member_of_collection_at

from feditest import InteropLevel, SpecLevel, assert_that
from feditest.protocols import NotImplementedByNodeError
from feditest.protocols.web import WebServer

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
    def __init__(self, uri: str):
        self._uri = uri
        self._json : Any | None = None


    def _ensure_fetched(self) -> None:
        """
        Make sure the uri has been dereferenced.

        Note: this could potentially be a smart factory, but currently it is not because
        we'd have to figure out when to expire the cache and that has some time.
        """
        if not self._json:
             # FIXME: this needs better error handling
            r : httpx.Response = httpx.get(
                self._uri,
                follow_redirects=True,
                verify=False,
                headers={"Accept": "application/activity+json"})
            r.raise_for_status() # May throw. No need for our own exceptions
            self._json = r.json()


    def check_is_valid_object(self) -> bool:
        """
        Interpret this instance as an ActivityStreams Object, and check whether it is valid.
        """
        self._ensure_fetched()
        json = cast(dict, self._json)
        if 'type' not in json:
            return False
        type = json['type']
        if not isinstance(type,str):
            return False
        return 'Object' == type


    def as_actor(self) -> 'Actor':
        """
        Interpret this instance as an Actor, and return an instance of the Actor class.
        """
        # FIXME: check that this is indeed a valid Actor, and throw exception if it is not
        self._ensure_fetched()
        return Actor(self)


    def as_collection(self) -> 'Collection':
        """
        Interpret this instance as a Collection, and return an instance of the Collection class.
        """
        # FIXME: check that this is indeed a valid Collection, and throw exception if it is not
        self._ensure_fetched()
        return Collection(self)


    def json_field(self, name:str):
        """
        Convenience method to access field 'name' in the JSON.
        """
        self._ensure_fetched()
        json = cast(dict, self._json)
        return json.get(name)


class Actor:
    """
    A facade in front of AnyObject that interprets AnyObject as an Actor.
    """
    def __init__(self, delegate: AnyObject):
        self._delegate = delegate


    def followers_uri(self):
        # FIXME can this be in different format, like a list?
        return self._delegate.json_field('followers')


    def following_uri(self):
        # FIXME can this be in different format, like a list?
        return self._delegate.json_field('following')


class Collection:
    """
    A facade in front of AnyObject that interprets AnyObject as a Collection.
    """
    def __init__(self, delegate: AnyObject):
        self._delegate = delegate


    def is_ordered(self):
        return 'OrderedCollection' == self._delegate.json_field('type')


    def items(self) -> Iterator[AnyObject]:
        items = self._delegate.json_field('orderedItems' if self.is_ordered() else 'items')
        if items is not None:
            for item in items:
                if isinstance(item,str):
                    yield AnyObject(item)
                else:
                    raise Exception(f'Cannot process yet: {item}')
        elif first := self._delegate.json_field('first') is not None:
            if isinstance(first,str):
                first_collection = AnyObject(first).as_collection()
                yield from first_collection.items()
            else:
                raise Exception(f'Cannot process yet: {first}')
        elif next := self._delegate.json_field('next') is not None:
            if isinstance(next,str):
                next_collection = AnyObject(next).as_collection()
                yield from next_collection.items()
            else:
                raise Exception(f'Cannot process yet: {first}')


    def contains(self, matcher: Callable[[AnyObject],bool]) -> bool:
        """
        Returns true if this Collection contains an item, as determined by the
        matcher object. This method passes the members of this collection to the
        matcher one at a time, and the matcher decides when there is a match.
        """
        for item in self.items():
            if matcher(item):
                return True
        return False


    def contains_item_with_id(self, id: str) -> bool:
        """
        Convenience method that looks for items that are simple object identifiers.
        FIXME: this can be much more complicated in ActivityStreams, but this
        implementation is all we need right now.
        """
        return self.contains(lambda candidate: id == candidate if isinstance(candidate,str) else False)


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


    def obtain_followers_collection_uri(self, actor_uri: str) -> str:
        """
        Determine the URI that points to the provided Actor's followers collection.
        This is a separate API call because there is no guarantee that FediTest tests is permitted
        to access the Actor JSON file and may not be able to get it from there.
        The default implementation determines this from the Actor file. Subclasses may override.
        """
        actor = AnyObject(actor_uri).as_actor()
        return actor.followers_uri()


    def obtain_following_collection_uri(self, actor_uri: str) -> str:
        """
        Determine the URI that points to the provided Actor's following collection.
        This is a separate API call because there is no guarantee that FediTest tests is permitted
        to access the Actor JSON file and may not be able to get it from there.
        The default implementation determines this from the Actor file. Subclasses may override.
        """
        actor = AnyObject(actor_uri).as_actor()
        return actor.following_uri()


    def assert_member_of_collection_at(
        self,
        candidate_member_uri: str,
        collection_uri: str,
        spec_level: SpecLevel | None = None,
        interop_level: InteropLevel | None= None
    ):
        """
        Raise an AssertionError if candidate_member_uri is not a member of the collection at collection_uri
        """
        assert_that(candidate_member_uri, is_member_of_collection_at(collection_uri, self), spec_level=spec_level, interop_level=interop_level)


    def assert_not_member_of_collection_at(
        self,
        candidate_member_uri: str,
        collection_uri: str,
        spec_level: SpecLevel | None = None,
        interop_level: InteropLevel | None= None
    ):
        """
        Raise an AssertionError if candidate_member_uri is a member of the collection at collection_uri
        """
        assert_that(candidate_member_uri, is_not(is_member_of_collection_at(collection_uri, self)), spec_level=spec_level, interop_level=interop_level)
