"""
"""

from feditest import register_test
from feditest.protocols.activitypub import ActivityPubNode, compare_objects
from feditest.protocols.web import WebServerLog

@register_test
def objects_must_be_the_same(
        iut:    ActivityPubNode,
        driver: ActivityPubNode
) -> None:
    sender_actor_uri : str  = iut.obtain_actor_uri();
    receiver_actor_uri : str = driver.obtain_actor_uri();

    driver.make_a_follow_b(receiver_actor_uri, sender_actor_uri)

    log : WebServerLog = driver.transaction( lambda:
        iut.make_actor_create_object( 'Note', 'Test Note')
    )
    assert(log.inbox_delta.size() == 1, 'Expecting one difference in the inbox')
    received_object = log.inbox_delta[0];

    fetched_object = driver.fetch_object(received_object['id'])
    assert(compare_objects(received_object, fetched_object)==0)