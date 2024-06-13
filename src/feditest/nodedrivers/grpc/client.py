import importlib
import logging
import sys
from typing import Any

# Avoid local package import
grpc_lib = importlib.import_module("grpc")

import feditest
from feditest import nodedriver
from feditest.nodedrivers import grpc
from feditest.nodedrivers.grpc.node_pb2 import (
    ActorFollowersUriReply,
    ActorFollowersUriRequest,
    ActorFollowingUriReply,
    ActorFollowingUriRequest,
    ActorUriReply,
    ActorUriRequest,
    AnnounceObjectReply,
    AnnounceObjectRequest,
    CollectionContainsReply,
    CollectionContainsRequest,
    CreateObjectReply,
    CreateObjectRequest,
    FollowActorRequest,
    ReplyToObjectReply,
    ReplyToObjectRequest,
    WaitForInboxObjectReply,
    WaitForInboxObjectRequest,
)
from feditest.nodedrivers.grpc.node_pb2_grpc import FeditestNodeStub
from feditest.protocols import Node, NodeDriver
from feditest.protocols.activitypub import ActivityPubNode
from feditest.protocols.fediverse import FediverseNode


class GrpcNodeClient(FediverseNode):
    def __init__(
        self,
        rolename: str,
        parameters: dict[str, Any],
        node_driver: NodeDriver,
    ):
        super().__init__(rolename, parameters, node_driver)
        self.channel = grpc_lib.insecure_channel(parameters["server_endpoint"])
        self.service = FeditestNodeStub(self.channel)

    def close(self):
        self.channel.close()

    def obtain_actor_document_uri(self, actor_rolename: str | None = None) -> str:
        reply: ActorUriReply = self.service.GetActorUri(
            ActorUriRequest(role_name=actor_rolename)
        )
        return reply.actor_uri

    def obtain_followers_collection_uri(self, actor_uri: str | None = None) -> str:
        reply: ActorFollowersUriReply = self.service.GetActorFollowersUri(
            ActorFollowersUriRequest(actor_uri=actor_uri)
        )
        return reply.uri

    def obtain_following_collection_uri(self, actor_uri: str | None = None) -> str:
        reply: ActorFollowingUriReply = self.service.GetActorFollowingUri(
            ActorFollowingUriRequest(actor_uri=actor_uri)
        )
        return reply.uri

    # TODO Not completely consistent with current FediverseNode API
    def make_create_note(
        self,
        actor_uri: str,
        content: str,
        /,
        to: str | None = None,
    ) -> str:
        reply: CreateObjectReply = self.service.CreateObject(
            CreateObjectRequest(
                type="Note",
                actor_uri=actor_uri,
                content=content,
                inbox_kind="Actor",
                to_uri=to,
            )
        )
        return reply.object_uri  # TODO Not clear what this should return

    def wait_for_object_in_inbox(self, actor_uri: str, note_uri: str) -> str:
        reply: WaitForInboxObjectReply = self.service.WaitForInboxObject(
            WaitForInboxObjectRequest(actor_uri=actor_uri, object_uri=note_uri)
        )
        if not reply.succeeded:
            raise AssertionError(
                f"{note_uri} not found in inbox for actor: {actor_uri}"
            )
        return note_uri  # TODO Not clear what this should return

    def make_announce_object(self, actor_uri, note_uri: str) -> str:
        reply: AnnounceObjectReply = self.service.AnnounceObject(
            AnnounceObjectRequest(actor_uri=actor_uri, object_uri=note_uri)
        )
        if not reply.succeeded:
            raise AssertionError(f"Announce of {note_uri} failed")
        return reply.activity_uri  # TODO Not clear what this should return

    def make_reply(self, actor_uri, note_uri: str, reply_content: str) -> str:
        reply: ReplyToObjectReply = self.service.ReplyToObject(
            ReplyToObjectRequest(
                actor_uri=actor_uri,
                object_uri=note_uri,
                content=reply_content,
            )
        )
        return reply.activity_uri  # TODO Not clear what this should return

    def make_a_follow_b(
        self,
        a_uri_here: str,
        b_uri_there: str,
        node_there: "ActivityPubNode",
    ) -> None:
        reply = self.service.FollowActor(
            FollowActorRequest(
                following_actor_uri=a_uri_here,
                followed_actor_uri=b_uri_there,
            )
        )
        return reply.accepted  # TODO method declared return type is None

    def _collection_contains(
        self,
        candidate_member_uri: str,
        collection_uri: str,
    ) -> bool:
        reply: CollectionContainsReply = self.service.CollectionContains(
            CollectionContainsRequest(
                object_uri=candidate_member_uri,
                collection_uri=collection_uri,
            )
        )
        return reply.result

    def assert_member_of_collection_at(
        self, candidate_member_uri: str, collection_uri: str
    ) -> None: # TODO ActivityPubNode doesn't declare return type
        if not self._collection_contains(candidate_member_uri, collection_uri):
            raise AssertionError(f"{candidate_member_uri} not in {collection_uri}")

    def assert_not_member_of_collection_at(
        self, candidate_member_uri: str, collection_uri: str
    ) -> None: # TODO ActivityPubNode doesn't declare return type:
        if self._collection_contains(candidate_member_uri, collection_uri):
            raise AssertionError(f"{candidate_member_uri} in {collection_uri}")


@nodedriver
class GrpcNodeClientDriver(NodeDriver):
    """
    Knows how to instantiate Mastodon via UBOS.
    """

    def _provision_node(self, rolename: str, parameters: dict[str, Any]) -> Node:
        return GrpcNodeClient(rolename, parameters, self)

    def _unprovision_node(self, node: Node) -> None:
        node.close()


def _run_example():
    # NOTE(gRPC Python Team): .close() is possible on a channel and should be
    # used in circumstances in which the with statement does not fit the needs
    # of the code.
    with grpc_lib.insecure_channel("localhost:50051") as channel:
        stub = FeditestNodeStub(channel)
        response = stub.GetActorUri(ActorUriRequest())
    print("client received: " + response.actor_uri)


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout)
    _run_example()
