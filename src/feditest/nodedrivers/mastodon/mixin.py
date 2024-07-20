# """
# Mastodon API Node

# See MastodonNode for a description of the supported/required node parameters.
# """

# import importlib
# import sys
# import time
# from typing import Any
# from urllib.parse import urlparse

# import httpx

# from feditest import AssertionFailure, InteropLevel, SpecLevel
# from feditest.protocols import NodeDriver
# from feditest.protocols.activitypub import ActivityPubNode

# # This kludge is needed because the node driver loader
# # will always try to load the current mastodon subpackage (relative)
# # instead of absolute package
# if "mastodon" in sys.modules:
#     m = sys.modules.pop("mastodon")
#     try:
#         mastodon_api = importlib.import_module("mastodon")
#         Mastodon = mastodon_api.Mastodon # type: ignore
#     finally:
#         sys.modules["mastodon"] = m
# else:
#     from mastodon import Mastodon #


# def _dereference(uri: str) -> dict:
#     return httpx.get(
#         uri,
#         follow_redirects=True,
#         verify=False,
#         headers={"Accept": "application/activity+json"},
#     ).json()


# class Actor:
#     """Encapsulates account/actor related information. For a Mastodon "actor"
#     it contains a reference to an API wrapper and the account data. For an actor
#     without a Mastodon access_token, it has the uri and the AP actor document.
#     """

#     def __init__(self, role: str, hostname: str, params: dict[str,str]):
#         if access_token := params.get("access_token"):
#             self.api = Mastodon(
#                 api_base_url=f"https://{hostname}", access_token=access_token
#             )
#             self.data = self.api.account_verify_credentials()
#             self.uri = self.data.uri
#         else:
#             self.api = None
#             self.data = None
#             self.uri = params["uri"]
#         self.role = role
#         self.actor = _dereference(self.uri)

#     @property
#     def is_mastodon(self):
#         return self.api is not None


# class MastodonApiMixin:
#     """
#     Supported Parameters:
#         {
#             "hostame": "somehost.org",
#             "inbox_wait": {"retry_count" 5, "retry_interval": 1}, # optional
#             "follow_wait": {"retry_count" 30, "retry_interval": 1}, # optional
#             "actors": {
#                 "default_role": "primary_actor",
#                 "roles": {
#                     "primary_actor": {
#                         uri: "PRIMARY_ACTOR_URI",
#                         access_token: "ACCESS_TOKEN"
#                     },
#                     "secondary_actor": {
#                         uri: "SECONDARY_ACTOR_URI",
#                     },
#                     "external_actor": {
#                         uri: "EXTERNAL_ACTOR_URI",
#                     }
#                 }
#             },
#         }

#     Required roles depend on tests.
#     """

#     def __init__(
#         self, rolename: str, parameters: dict[str, Any], node_driver: NodeDriver
#     ):
#         super().__init__(rolename, parameters, node_driver)
#         if access_token := parameters.get("access_token"):
#             # Short config
#             self.actors = [
#                 Actor("default", self._param("hostname"), {
#                     "access_token": access_token
#                 })
#             ]
#             self.default_actor = self.actors[0]
#         else:
#             # Verbose config
#             self.actors = [
#                 Actor(role_name, self._param("hostname"), role_params)
#                 for role_name, role_params in self._param("actors", "roles").items()
#             ]
#             self.default_actor = next(
#                 a for a in self.actors
#                 if a.role == self._param("actors", "default_role")
#             )
#         self.actors_by_uri = {a.uri: a for a in self.actors}
#         self.actors_by_role = {a.role: a for a in self.actors}
#         self.uri_map: dict[str, dict] = dict()

#     def _get_actor_or_default(self, actor_uri: str | None) -> Actor:
#         return self.actors_by_uri[actor_uri] if actor_uri else self.default_actor

#     def _param(self, *keys, default: Any = None, required: bool = True):
#         value = self._parameters
#         for key in keys:
#             if key in value:
#                 value = value.get(key)
#             elif default or not required:
#                 return default
#             else:
#                 raise KeyError(f"Can't get node parameter for {keys}")
#         return value

#     # Override
#     def obtain_actor_document_uri(self, actor_rolename: str | None = None) -> str:
#         return (
#             self.actors_by_role[actor_rolename]
#             if actor_rolename
#             else self.default_actor
#         ).uri

#     # Override
#     def obtain_followers_collection_uri(self, actor_uri: str | None = None) -> str:
#         """
#         Determine the URI that points to the provided actor's followers collection.
#         """
#         return self._get_actor_or_default(actor_uri).actor["followers"]

#     # Override
#     def obtain_following_collection_uri(self, actor_uri: str | None = None) -> str:
#         """
#         Determine the URI that points to the provided actor's following collection.
#         """
#         return self._get_actor_or_default(actor_uri).actor["following"]

#     # Override
#     # FIXME: The base API doesn't have a `to` kwargs.
#     # However, delivery will not happen without recipients.
#     # We could possibly default this to the followers URI.
#     # One of the tests also uses another kwarg to specify the preferred
#     # inbox type.
#     def make_create_note(
#         self, actor_uri: str, content: str, to: str | None = None
#     ) -> str:
#         """ "
#         Perform whatever actions are necessary to the actor with actor_uri will
#         have created a Note on this Node. Determine the various Note and
#         Activity properties as per this Node's defaults.
#         """
#         sending_account = self._get_actor_or_default(actor_uri)
#         assert sending_account.is_mastodon
#         if to:
#             results = sending_account.api.search(q=to, result_type="accounts")
#             if to_account := next(
#                 (a for a in results.get("accounts", []) if a.uri == to), None
#             ):
#                 to_url = urlparse(to_account.uri)
#                 to_handle = f"@{to_account.acct}@{to_url.netloc}"
#                 content += f" {to_handle}"
#         response = sending_account.api.status_post(content)
#         self.uri_map[response.uri] = response
#         return response.uri

#     # Override
#     def wait_for_object_in_inbox(self, actor_uri: str, note_uri: str) -> str:
#         for _ in range(
#             self._param("inbox_wait", "retry_count", default=5)
#         ):  # TODO Try for 5 seconds. Make configurable?
#             response = next(
#                 (
#                     s
#                     for s in self._get_actor_or_default(actor_uri).api.timeline("local")
#                     if s.uri == note_uri
#                 ),
#                 None,
#             )
#             if response:
#                 return response
#             time.sleep(self._param("inbox_wait", "retry_interval", default=1))
#         raise Exception(f"Can't map {note_uri} to Mastodon Status identifier")

#     # Override
#     def make_announce_object(self, actor_uri, note_uri: str) -> str:
#         if note := self.uri_map.get(note_uri):
#             reblog = self._get_actor_or_default(actor_uri).api.status_reblog(note.id)
#             self.uri_map[reblog.uri] = reblog
#             return reblog.uri

#     # Override
#     def make_reply(self, actor_uri, note_uri: str, reply_content: str) -> str:
#         if note := self.uri_map.get(note_uri):
#             reply = self._get_actor_or_default(actor_uri).api.status_reply(
#                 to_status=note, status=reply_content
#             )
#             self.uri_map[reply.uri] = reply
#             return reply.uri
#         return None

#     # Override
#     # The purpose of node_there isn't clear.
#     def make_a_follow_b(
#         self,
#         a_uri_here: str,
#         b_uri_there: str,
#         node_there: ActivityPubNode | None = None,
#     ) -> None:
#         """
#         Perform whatever actions are necessary so that actor with URI a_uri_here, which
#         is hosted on this ActivityPubNode, is following actor with URI b_uri_there,
#         which is hosted on ActivityPubNode node_there. Only return when the follow
#         relationship is fully established.
#         """
#         a_account = self._get_actor_or_default(a_uri_here)
#         assert a_account.is_mastodon
#         results = a_account.api.search(q=b_uri_there, result_type="accounts")
#         if b_account := next(
#             (b for b in results.get("accounts", []) if b.uri == b_uri_there), None
#         ):
#             relationship = a_account.api.account_follow(b_account)
#             if not relationship["following"]:
#                 for _ in range(self._param("follow_wait", "retry_count", default=30)):
#                     time.sleep(self._param("follow_wait", "retry_interval", default=30))
#                     relationship = a_account.api.account_relationships(b_account)
#                     if relationship["following"]:
#                         break
#         else:
#             raise Exception(f"Can't find account for {b_uri_there}")

#     @staticmethod
#     def _collection_items(collection_uri: str) -> list:
#         collection = _dereference(collection_uri)
#         collection_page = _dereference(collection["first"])
#         item_key = (
#             "orderedItems" if collection.get("type") == "OrderedCollection" else "items"
#         )
#         return collection_page[item_key]

#     @staticmethod
#     def _assert(condition: bool, message: str|None = None) -> None:
#         if not condition:
#             raise AssertionFailure(SpecLevel.UNSPECIFIED, InteropLevel.UNKNOWN, message)

#     # Override
#     def assert_member_of_collection_at(
#         self,
#         candidate_member_uri: str,
#         collection_uri: str,
#         spec_level: SpecLevel | None = None,
#         interop_level: InteropLevel | None= None
#     ):
#         """
#         Raise an AssertionError if candidate_member_uri is a member of the
#         collection at collection_uri
#         """
#         self._assert(candidate_member_uri in self._collection_items(
#             collection_uri
#         ), f"{candidate_member_uri} not in {collection_uri}")

#     # Override
#     def assert_not_member_of_collection_at(
#         self,
#         candidate_member_uri: str,
#         collection_uri: str,
#         spec_level: SpecLevel | None = None,
#         interop_level: InteropLevel | None= None
#     ):
#         """
#         Raise an AssertionError if candidate_member_uri is not a member of
#         the collection at collection_uri
#         """
#         self._assert(candidate_member_uri not in self._collection_items(
#             collection_uri
#         ), f"{candidate_member_uri} should not be in {collection_uri}")

#     # Test setup support

#     def delete_follows(self, actor_uri: str | None = None):
#         account = self._get_actor_or_default(actor_uri)
#         if account.is_mastodon:
#             for followed in account.api.account_following(account.data.id):
#                 account.api.account_unfollow(followed)

#     def delete_statuses(self, actor_uri: str | None = None):
#         account = self._get_actor_or_default(actor_uri)
#         if account.is_mastodon:
#             for status in account.api.account_statuses(account.data.id):
#                 account.api.status_delete(status)

#     # Other convenience methods

#     def _ensure_actor(self, actor: Actor | str):
#         if isinstance(actor, Actor):
#             return actor
#         elif isinstance(actor, str):
#             return self.actors_by_role.get(actor)
#         else:
#             raise Exception(f"Can't resolve actor: {actor}")

#     def follow(self, actor1: Actor | str, actor2: Actor | str):
#         self.make_a_follow_b(
#             self._ensure_actor(actor1).uri,
#             self._ensure_actor(actor2).uri,
#         )

#     @property
#     def server_version(self):
#         return self.default_actor.api.instance()["version"]