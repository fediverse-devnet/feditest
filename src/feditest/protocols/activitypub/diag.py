from typing import Any, cast

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
    def __init__(self, uri: str, json: Any):
        self._uri = uri
        self._json = json


    def check_is_valid_object(self) -> bool:
        """
        Interpret this instance as an ActivityStreams Object, and check whether it is valid.
        """
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
        return Actor(self)


    def as_collection(self) -> 'Collection':
        """
        Interpret this instance as a Collection, and return an instance of the Collection class.
        """
        # FIXME: check that this is indeed a valid Collection, and throw exception if it is not
        return Collection(self)


    def json_field(self, name:str):
        """
        Convenience method to access field 'name' in the JSON.
        """
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


    # Work in progress

    # def items(self) -> Iterator[AnyObject]:
    #     items = self._delegate.json_field('orderedItems' if self.is_ordered() else 'items')
    #     if items is not None:
    #         for item in items:
    #             if isinstance(item,str):
    #                 yield AnyObject(item)
    #             else:
    #                 raise Exception(f'Cannot process yet: {item}')
    #     elif first := self._delegate.json_field('first') is not None:
    #         if isinstance(first,str):
    #             first_collection = AnyObject(first).as_collection()
    #             yield from first_collection.items()
    #         else:
    #             raise Exception(f'Cannot process yet: {first}')
    #     elif next := self._delegate.json_field('next') is not None:
    #         if isinstance(next,str):
    #             next_collection = AnyObject(next).as_collection()
    #             yield from next_collection.items()
    #         else:
    #             raise Exception(f'Cannot process yet: {first}')


    # def contains(self, matcher: Callable[[AnyObject],bool]) -> bool:
    #     """
    #     Returns true if this Collection contains an item, as determined by the
    #     matcher object. This method passes the members of this collection to the
    #     matcher one at a time, and the matcher decides when there is a match.
    #     """
    #     for item in self.items():
    #         if matcher(item):
    #             return True
    #     return False


    # def contains_item_with_id(self, id: str) -> bool:
    #     """
    #     Convenience method that looks for items that are simple object identifiers.
    #     FIXME: this can be much more complicated in ActivityStreams, but this
    #     implementation is all we need right now.
    #     """
    #     return self.contains(lambda candidate: id == candidate if isinstance(candidate,str) else False)


class ActivityPubDiagNode(WebDiagClient, WebDiagServer,ActivityPubNode):
    pass

    # Work in progress

    # def fetch_remote_actor_document(remote_actor_acct_uri: str) -> Actor:
    #     pass


    # def set_inbox_uri_to(actor_acct_uri: str, inbox_uri: str | None):
    #     pass


    # def set_outbox_uri_to(actor_acct_uri: str, outbox_uri: str | None):
    #     pass


    # def add_to_followers_collection(actor_acct_uri: str, to_be_added_actor_acct_uri: str):
    #     pass


    # def add_to_following_collection(actor_acct_uri: str, to_be_added_actor_acct_uri: str):
    #     pass


    # def add_to_outbox(actor_acct_uri: str, to_be_added_activity: Activity):
    #     pass


    # def add_to_inbox(actor_acct_uri: str, to_be_added_activity: Activity):
    #     pass


    # def read_inbox_of(actor_acct_uri: str, inbox_collection: Collection):
    #     pass


    # def read_outbox_of(actor_acct_uri: str, outbox_collection: Collection):
    #     pass