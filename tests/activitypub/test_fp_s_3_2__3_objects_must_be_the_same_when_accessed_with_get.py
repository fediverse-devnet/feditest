"""
See annotated ActivityPub specification, test 3.2/3.
Objects received through the inbox and via HTTP GET must be the same.
"""

from feditest import step
from feditest.protocols.activitypub import ActivityPubNode
from feditest.protocols.web import WebServerLog

@step
def objects_must_be_the_same(
        sender: ActivityPubNode,
        receiver: ActivityPubNode
) -> None:
    sender_actor_uri : str  = sender.obtain_actor_uri();
    receiver_actor_uri : str = receiver.obtain_actor_uri();

    receiver.make_a_follow_b(receiver_actor_uri, sender_actor_uri)

# FIXME
#   log : WebServerLog = receiver.transaction( lambda:
#         sender.make_actor_create_object( 'Note', 'Test Note')
#     )
#     assert(log.inbox_delta.size() == 1, 'Expecting one difference in the inbox')
#     received_object = log.inbox_delta[0];
#
#     fetched_object = receiver.fetch_object(received_object['id'])
#     assert(compare_objects(received_object, fetched_object)==0)