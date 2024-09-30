"""
Tests that two nodes that implement the Mastodon API can follow each other.
"""

from datetime import datetime

from feditest import step, test
from feditest.nodedrivers.mastodon import NodeWithMastodonAPI

import time

@test
class FollowTest:
    def __init__(self,
        leader_node: NodeWithMastodonAPI,
        follower_node: NodeWithMastodonAPI
    ) -> None:
        self.leader_node = leader_node
        self.leader_actor_uri = None
        self.leader_node.set_auto_accept_follow(True)

        self.follower_node = follower_node
        self.follower_actor_uri = None

        self.leader_note_uri = None


    @step
    def provision_actors(self):
        self.leader_actor_uri = self.leader_node.obtain_actor_document_uri()
        assert self.leader_actor_uri

        self.follower_actor_uri = self.follower_node.obtain_actor_document_uri()
        assert self.follower_actor_uri


    # @step
    # def start_reset_all(self):
    #     self._reset_all()


    @step
    def follow(self):
        self.follower_node.make_follow(self.follower_actor_uri, self.leader_actor_uri)


    @step
    def wait_until_actor_is_followed_by_actor(self):
        # self.leader_node.wait_until_actor_is_followed_by_actor(self.leader_actor_uri, self.follower_actor_uri)
        time.sleep(5)


    @step
    def wait_until_actor_is_following_actor(self):
        # self.follower_node.wait_until_actor_is_following_actor(self.follower_actor_uri, self.leader_actor_uri)
        time.sleep(5)


    @step
    def leader_creates_note(self):
        self.leader_note_uri = self.leader_node.make_create_note(self.leader_actor_uri, f"testing leader_creates_note {datetime.now()}")
        assert self.leader_note_uri


    @step
    def wait_until_note_received(self):
        self.follower_node.wait_until_actor_has_received_note(self.follower_actor_uri, self.leader_note_uri)


    # @step
    # def end_reset_all(self):
    #     self._reset_all()


    def _reset_all(self):
        """
        Clean up data. This is here so the test is usable with non-brand-new instances.
        """
        self.leader_node.delete_all_followers_of(self.leader_actor_uri)
        self.leader_node.delete_all_following_of(self.leader_actor_uri)
        self.leader_node.delete_all_statuses_by(self.leader_actor_uri)

        self.follower_node.delete_all_followers_of(self.follower_actor_uri)
        self.follower_node.delete_all_following_of(self.follower_actor_uri)
        self.follower_node.delete_all_statuses_by(self.follower_actor_uri)

