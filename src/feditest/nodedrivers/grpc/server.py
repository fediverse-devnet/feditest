import logging
import os
import sys
from concurrent import futures

import grpc

from feditest.nodedrivers.grpc.node_pb2 import (
    ActorFollowersUriReply,
    ActorFollowingUriReply,
    ActorUriReply,
    AnnounceObjectReply,
    CollectionContainsReply,
    CreateObjectReply,
    FollowActorReply,
    ReplyToObjectReply,
    WaitForInboxObjectReply,
)
from feditest.nodedrivers.grpc.node_pb2_grpc import (
    FeditestNodeServicer,
    add_FeditestNodeServicer_to_server,
)


class ExampleNodeServer(FeditestNodeServicer):
    def GetActorUri(self, request, context):
        return ActorUriReply(actor_uri="https://server.test/actor/carol")

    def GetActorFollowersUri(self, request, context):
        return ActorFollowersUriReply(uri="https://server.test/actor/carol/followers")

    def GetActorFollowingUri(self, request, context):
        return ActorFollowingUriReply(uri="https://server.test/actor/carol/following")

    def CreateObject(self, request, context):
        # TODO maybe activity_uri ... don't know yet
        return CreateObjectReply(object_uri="https://server.test/activities/Create/1")

    def WaitForInboxObject(self, request, context):
        return WaitForInboxObjectReply(
            succeeded=request.object_uri == "https://server.test/note/1"
        )

    def AnnounceObject(self, request, context):
        return AnnounceObjectReply(
            succeeded=True, activity_uri="https://server.test/announce"
        )

    def ReplyToObject(self, request, context):
        return ReplyToObjectReply(
            succeeded=True, activity_uri="https://server.test/reply"
        )

    def FollowActor(self, request, context):
        return FollowActorReply(accepted=True)

    def CollectionContains(self, request, context):
        return CollectionContainsReply(
            result=(request.object_uri == "https://server.test/carol")
        )

    @staticmethod
    def serve():
        port = "50051"
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        add_FeditestNodeServicer_to_server(ExampleNodeServer(), server)
        server.add_insecure_port("[::]:" + port)
        server.start()
        print("Server started, listening on " + port)
        server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout)
    ExampleNodeServer.serve()
