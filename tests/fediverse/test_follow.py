"""
"""

from hamcrest import assert_that, is_not, has_key
from feditest import step
from feditest.protocols.fediverse import FediverseNode

@step
def follow(
        to_be_leader_node:   FediverseNode,
        to_be_follower_node: FediverseNode
) -> None:
    """
    Have an account on one node follow another account on another node.
    Make sure the follower or following collections are correct on both
    sides.
    """
    leader_actor_uri   = to_be_leader_node.obtain_actor_document_uri();
    follower_actor_uri = to_be_follower_node.obtain_actor_document_uri();

    leader_existing_followers = to_be_leader_node.get_followers(leader_actor_uri)
    assert_that(leader_existing_followers, is_not(has_key(follower_actor_uri)))

    follower_existing_following = to_be_follower_node.get_following(follower_actor_uri)
    assert_that(follower_existing_following, is_not(has_key(leader_actor_uri)))

    to_be_follower_node.make_a_follow_b(follower_actor_uri, leader_actor_uri)

    leader_new_followers = to_be_leader_node.get_followers(leader_actor_uri)
    assert_that(leader_new_followers, has_key((follower_actor_uri)))

    follower_new_following = to_be_follower_node.get_following(follower_actor_uri)
    assert_that(follower_new_following, has_key(leader_actor_uri))
