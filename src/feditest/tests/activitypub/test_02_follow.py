"""
"""

from feditest import register_test
from feditest.iut.activitypub import ActivityPubIUT

@register_test
def follow(to_be_leader_iut: ActivityPubIUT, to_be_follower_iut: ActivityPubIUT) -> None:
    """
    Have an account on one IUT follow another account on another IUT.
    Make sure the follower or following collections are correct on both
    sides.
    """
    leader_actor_doc = to_be_leader_iut.create_actor_document_URI()
    follower_actor_doc = to_be_follower_iut.create_actor_document_URI()
    leader_id = leader_actor_doc['id']
    follower_id = follower_actor_doc['id']

    existing_followers = to_be_leader_iut.get_followers()
    assert(follower_id not in existing_followers)
    existing_following = to_be_follower_iut.get_following()
    assert(leader_id not in existing_following)

    to_be_follower_iut.initiate_follow( leader_actor_doc )

    new_followers = to_be_leader_iut.get_followers()
    assert(follower_id in new_followers)
    new_following = to_be_follower_iut.get_followers()
    assert(leader_id in new_following)
