"""
See annotated ActivityPub specification, test 4.1/1
"""

from feditest import step
from feditest.protocols.activitypub import ActivityPubNode
from feditest.utils import http_https_uri_validate

@step
def actor_objects_must_have_an_inbox(
        iut:    ActivityPubNode,
        driver: ActivityPubNode
) -> None:
    actor_uri : str = iut.obtain_actor_uri();

    actor_result = driver.perform_get_actor_from(actor_uri)

    assert('inbox' in actor_result.data)
    assert(http_https_uri_validate(actor_result.data['inbox']))

    inbox_result = driver.perform_get_collection_from(actor_result.data['inbox'])
    assert(inbox_result)
