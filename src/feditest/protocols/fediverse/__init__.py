"""
Abstractions for nodes that speak today's Fediverse protocol stack.
"""

import re

from feditest.nodedrivers import Account, NonExistingAccount, NotImplementedByNodeError
from feditest.protocols.activitypub import ActivityPubNode
from feditest.protocols.webfinger import WebFingerClient, WebFingerServer
from feditest.testplan import TestPlanNodeAccountField, TestPlanNodeNonExistingAccountField


def userid_validate(candidate: str) -> str | None:
    """
    Validate a local userid. Avoids user input errors.
    userpart of https://datatracker.ietf.org/doc/html/rfc7565
    """
    candidate = candidate.strip()
    return candidate if re.fullmatch(r'[-.~a-zA-Z0-9_!$&''()*+,;=]([-.~a-zA-Z0-9_!$&''()*+,;=]|%[0-9a-fA-F]{2})*', candidate) else None


ROLE_ACCOUNT_FIELD = TestPlanNodeAccountField(
        'role',
        """A symbolic name for the Account as used by tests (optional).""",
        lambda x: len(x)
)
USERID_ACCOUNT_FIELD = TestPlanNodeAccountField(
        'account_userid',
        """The user part of the acct: URI that identifies the Account (required).""",
        userid_validate
)
ROLE_NON_EXISTING_ACCOUNT_FIELD = TestPlanNodeNonExistingAccountField(
        'role',
        """A symbolic name for the non-existing Account as used by tests (optional).""",
        lambda x: len(x)
)
USERID_NON_EXISTING_ACCOUNT_FIELD = TestPlanNodeNonExistingAccountField(
        'non_existing_account_userid',
        """The user part of the acct: URI that identifies the non-existing Account (required).""",
        userid_validate
)


class FediverseAccount(Account):
    def __init__(self, role: str | None, userid: str):
        """
        actor_localid: the local id of the actor on this node, such as "joe" if the corresponding
        acct URI is acct:joe@example.com
        """
        super().__init__(role)
        self._userid = userid


    @staticmethod
    def create_from_account_info_in_testplan(account_info_in_testplan: dict[str, str | None], context_msg: str = ''):
        """
        Parses the information provided in an "account" dict of TestPlanConstellationNode
        """
        userid = USERID_ACCOUNT_FIELD.get_validate_from_or_raise(account_info_in_testplan, context_msg)
        role = ROLE_ACCOUNT_FIELD.get_validate_from(account_info_in_testplan, context_msg)
        return FediverseAccount(role, userid)


    @property
    def userid(self):
        return self._userid


    @property
    def actor_acct_uri(self):
        return f'acct:{ self._userid }@{ self.node.hostname }'


class FediverseNonExistingAccount(NonExistingAccount):
    def __init__(self, role: str | None, userid: str):
        super().__init__(role)
        self._userid = userid


    @staticmethod
    def create_from_non_existing_account_info_in_testplan(non_existing_account_info_in_testplan: dict[str, str | None], context_msg: str = ''):
        """
        Parses the information provided in an "non_existing_account" dict of TestPlanConstellationNode
        """
        userid = USERID_NON_EXISTING_ACCOUNT_FIELD.get_validate_from_or_raise(non_existing_account_info_in_testplan, context_msg)
        role = ROLE_NON_EXISTING_ACCOUNT_FIELD.get_validate_from(non_existing_account_info_in_testplan, context_msg)
        return FediverseNonExistingAccount(role, userid)


    @property
    def userid(self):
        return self._userid


    @property
    def actor_acct_uri(self):
        return f'acct:{ self._userid }@{ self.node.hostname }'


class FediverseNode(WebFingerClient, WebFingerServer, ActivityPubNode):
    """
    A Node that can participate in today's Fediverse.
    The methods defined on FediverseNode reflect -- well, try to start reflecting, we are only
    learning what those are -- what users expect of the Fediverse.
    The methods here do not reflect the entire expressiveness of ActivityPub and ActivityStreams,
    only the subset relevant for interop in today's Fediverse. (As we broaden support for
    more applications, that list and the exposed variations may grow.)

    While on this level, it's not strictly defined, the actor_acct_uri parameters are expected
    to be acct: URIs.
    """
    def obtain_actor_acct_uri(self, rolename: str | None = None) -> str:
        """
        Smart factory method to return the acct: URI of an Actor on this Node that
        either exists already or is newly created. Different rolenames produce different
        results; the same rolename produces the same result.
        rolename: refer to this Actor by this rolename; used to disambiguate multiple
           Actors on the same server by how they are used in tests
        return: the handle
        """
        raise NotImplementedByNodeError(self, FediverseNode.obtain_actor_acct_uri)

# Operations related to relations between actors

    def make_follow(self, actor_acct_uri: str, to_follow_actor_acct_uri: str) -> None:
        """
        Perform whatever actions are necessary so the actor with actor_acct_uri will have initiated
        a Follow request for the Actor with to_follow_actor_acct_uri.
        The actor with actor_acct_uri must be on this Node.
        No return value: we already have the to_follow_actor_acct_uri
        """
        raise NotImplementedByNodeError(self, FediverseNode.make_follow)


    def set_auto_accept_follow(self, actor_acct_uri: str, auto_accept_follow: bool = True) -> None:
        """
        Configure the behavior of this Node for the Actor with actor_acct_uri so that when
        Follow requests come in, they are automatically accepted.
        The actor with actor_acct_uri must be on this Node.
        This method exists so that implementations can throw a NotImplementedByNodeError
        if they do not have the requested behavior (or it cannot be scripted) and
        the corresponding tests does not run.
        """
        if auto_accept_follow:
            return # Assumed default

        raise NotImplementedByNodeError(self, FediverseNode.set_auto_accept_follow)


    def make_follow_accept(self, actor_acct_uri: str, would_be_follower_actor_acct_uri: str) -> None:
        """
        Perform whatever actions are necessary so the actor with actor_acct_uri will have accepted
        a Follow request previously made by the Actor with would_be_follower_actor_acct_uri.
        Calling this makes no sense if `auto_accept_follow` is true for the actor with actor_acct_uri,
        as it only applies to a pending Follow request.
        The actor with actor_acct_uri must be on this Node.
        """
        raise NotImplementedByNodeError(self, FediverseNode.make_follow_accept)


    def make_follow_reject(self, actor_acct_uri: str, would_be_follower_actor_acct_uri: str) -> None:
        """
        Perform whatever actions are necessary so the actor with actor_acct_uri will have rejected
        a Follow request previously made by the Actor with would_be_follower_actor_acct_uri.
        Calling this makes no sense if `auto_accept_follow` is true for the actor with actor_acct_uri,
        as it only applies to a pending Follow request.
        The actor with actor_acct_uri must be on this Node.
        """
        raise NotImplementedByNodeError(self, FediverseNode.make_follow_reject)


    def make_unfollow(self, actor_acct_uri: str, following_actor_acct_uri: str) -> None:
        """
        Perform whatever actions are necessary so the actor with actor_acct_uri will have
        unfollowed the Actor with following_actor_acct_uri.
        The actor with actor_acct_uri must be on this Node.
        """
        raise NotImplementedByNodeError(self, FediverseNode.make_unfollow)


    def actor_is_following_actor(self, actor_acct_uri: str, leader_actor_acct_uri: str) -> bool:
        """
        Return True if the Actor at actor_acct_uri is following the Actor at leader_actor_acct_uri,
        in the opinion of this Node.
        """
        raise NotImplementedByNodeError(self, FediverseNode.actor_is_following_actor)


    def actor_is_followed_by_actor(self, actor_acct_uri: str, follower_actor_acct_uri: str) -> bool:
        """
        Return True if the Actor at actor_acct_uri is followed by Actor at follower_actor_acct_uri,
        in the opinion of this Node.
        """
        raise NotImplementedByNodeError(self, FediverseNode.actor_is_followed_by_actor)

# Operations related to content creation, modification, deletion

    def make_create_note(self, actor_acct_uri: str, content: str, deliver_to: list[str] | None = None) -> str:
        """"
        Perform whatever actions are necessary so the actor with actor_acct_uri will have created
        a Note object on this Node with the specified content.
        deliver_to: make sure the Node is delivered to these Actors (i.e. in arrives in their inbox)
        return: URI to the Note object
        """
        raise NotImplementedByNodeError(self, FediverseNode.make_create_note)


    def update_note(self, actor_acct_uri: str, note_uri: str, new_content: str) -> None:
        """
        Return the reply's content if the Actor at actor_acct_uri can see that the Note at note_uri has a reply
        note with reply_uri on this Node.
        """
        raise NotImplementedByNodeError(self, FediverseNode.update_note)


    def delete_object(self, actor_acct_uri: str, object_uri: str) -> None:
        """
        Delete a note (boost, announce).
        """
        raise NotImplementedByNodeError(self, FediverseNode.delete_object)

# Operations related to engaging with existing content

    def make_reply_note(self, actor_acct_uri: str, to_be_replied_to_object_uri: str, reply_content: str) -> str:
        """
        Perform whatever actions are necessary so the actor with actor_acct_uri will have created
        a Note object that replies to the object at to_be_replied_to_object_uri with the specified content.
        return: URI to the Reply object
        """
        raise NotImplementedByNodeError(self, FediverseNode.make_reply_note)


    def like_object(self, actor_acct_uri: str, object_uri: str) -> None:
        """
        Like an object (like a note).
        """
        raise NotImplementedByNodeError(self, FediverseNode.like_object)


    def unlike_object(self, actor_acct_uri: str, object_uri: str) -> None:
        """
        Unlike an object (like a note) that was previously liked
        """
        raise NotImplementedByNodeError(self, FediverseNode.unlike_object)


    def announce_object(self, actor_acct_uri: str, object_uri: str) -> None:
        """
        Announce an object (boost, reblog).
        """
        raise NotImplementedByNodeError(self, FediverseNode.announce_object)


    def unannounce_object(self, actor_acct_uri: str, object_uri: str) -> None:
        """
        Undo a previous announce of an object (boost, reblog).
        """
        raise NotImplementedByNodeError(self, FediverseNode.unannounce_object)


    def actor_has_received_object(self, actor_acct_uri: str, object_uri: str) -> str | None:
        """
        If the object at object_uri has arrived with the Actor at actor_acct_uri, return the content
        of the object.
        """
        raise NotImplementedByNodeError(self, FediverseNode.actor_has_received_object)

# Operations related to examining existing objects

    def note_content(self, actor_acct_uri: str, note_uri: str) -> str | None:
        """
        Return the content of the Note at not_uri if the Actor at actor_acct_uri can access it.
        """
        raise NotImplementedByNodeError(self, FediverseNode.note_content)


    def object_author(self, actor_acct_uri: str, object_uri: str) -> str | None:
        """
        Return the actor acct URI of actor that is the author of the object at object_uri.
        """
        raise NotImplementedByNodeError(self, FediverseNode.object_author)


    def direct_replies_to_object(self, actor_acct_uri: str, object_uri: str) -> list[str]:
        """
        Return the URIs of the objects that directly reply to the object at object_uri.
        """
        raise NotImplementedByNodeError(self, FediverseNode.direct_replies_to_object)


    def object_likers(self, actor_acct_uri: str, object_uri: str) -> list[str]:
        """
        Return the set of actor acct URI of the actors that liked this object.
        """
        raise NotImplementedByNodeError(self, FediverseNode.object_likers)


    def object_announcers(self, actor_acct_uri: str, object_uri: str) -> list[str]:
        """
        Return the set of actor acct URI of the actors that announced/boosted/reblogged this object.
        """
        raise NotImplementedByNodeError(self, FediverseNode.object_announcers)

