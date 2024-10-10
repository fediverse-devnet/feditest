from typing import Any, Callable, Iterator, cast

import httpx

from . import ActivityPubNode
from feditest.protocols.web.diag import WebDiagClient, WebDiagServer

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


class Activity:
    """
    A facade in front of AnyObject that interprets AnyObject as an Activity.
    """
    def __init__(self, delegate: AnyObject):
        self._delegate = delegate



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




class ActivityPubDiagNode(ActivityPubNode, WebDiagClient, WebDiagServer):
    def fetch_remote_actor_document(remote_actor_uri: str) -> Actor:
        pass



