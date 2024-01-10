"""
"""

from feditest import register_test
from feditest.iut.activitypub import ActivityPubFederationIUT

@register_test
def follow(
        to_be_leader_iut:   ActivityPubFederationIUT,
        to_be_follower_iut: ActivityPubFederationIUT)
-> None:
    """
    Have an account on one IUT follow another account on another IUT.
    Make sure the follower or following collections are correct on both
    sides.
    """
    leader_actor_uri   = to_be_leader_iut.obtain_actor_uri();
    follower_actor_uri = to_be_follower_iut.obtain_actor_uri();

    leader_existing_followers = to_be_leader_iut.get_followers(leader_actor_uri)
    assert(follower_actor_uri not in leader_existing_followers)

    folllower_existing_following = to_be_follower_iut.get_following(following_actor_uri)
    assert(leader_actor_uri not in folllower_existing_following)

    to_be_follower_iut.make_a_follow_b(to_be_follower_uri, leader_actor_uri)

    leader_new_followers = to_be_leader_iut.get_followers(leader_actor_uri)
    assert(follower_actor_uri in leader_new_followers)

    follower_new_following = to_be_follower_iut.get_following(following_actor_uri)
    assert(leader_actor_uri in follower_new_following)

