"""
"""

from feditest import register_test
from feditest.iut.activitypub import ActivityPubIUT

@register_test
def test_01_valid_actor_document(iut: ActivityPubIUT) -> None:
    actor_doc_uri = iut.obtain_actor_document_URI()
    actor_doc_json = fetch(actor_doc_uri) # fixme
    validate(actor_doc_json)
