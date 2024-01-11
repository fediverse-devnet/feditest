"""
"""

from feditest import register_test
from feditest.protocols.fediverse import FediverseNode

@register_test
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
    assert(follower_actor_uri not in leader_existing_followers)

    follower_existing_following = to_be_follower_node.get_following(follower_actor_uri)
    assert(leader_actor_uri not in follower_existing_following)

    to_be_follower_node.make_a_follow_b(follower_actor_uri, leader_actor_uri)

    leader_new_followers = to_be_leader_node.get_followers(leader_actor_uri)
    assert(follower_actor_uri in leader_new_followers)

    follower_new_following = to_be_follower_node.get_following(follower_actor_uri)
    assert(leader_actor_uri in follower_new_following)

