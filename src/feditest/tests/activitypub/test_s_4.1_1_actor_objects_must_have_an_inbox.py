"""
"""

from feditest import register_test
from feditest.iut.activitypub import ActivityPubFederationIUT

@register_test
def actor_objects_must_have_an_inbox(
        iut:    ActivityPubFederationIUT,
        driver: ActivityPubFederationIUT
) -> None:
    actor_uri : str = iut.obtain_actor_uri();

    actor_result = driver.perform_get_actor_from(actor_uri)

    assert('inbox' in actor_result.data)
    assert_absolute_http_https_uri(actor_result.data['inbox'])

    inbox_result = driver.perform_get_collection_from(actor_result.data['inbox'])
    assert(inbox_result)
