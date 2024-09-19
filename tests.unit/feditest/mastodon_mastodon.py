"""
Tests that two instances of Mastodon can follow each other.
"""

from datetime import datetime
# import re

from feditest import step, test
from feditest.nodedrivers.mastodon import NodeWithMastodonAPI

@test
class FollowTest:
    def __init__(self,
        leader_node: NodeWithMastodonAPI,
        follower_node: NodeWithMastodonAPI
    ) -> None:
        self.leader_node = leader_node
        self.leader_actor_uri = None

        self.follower_node = follower_node
        self.follower_actor_uri = None

        self.leader_note_uri = None


    @step
    def provision_actors(self):
        self.leader_actor_uri = self.leader_node.obtain_actor_document_uri()
        assert self.leader_actor_uri

        self.follower_actor_uri = self.follower_node.obtain_actor_document_uri()
        assert self.follower_actor_uri


    @step
    def start_reset_all(self):
        self._reset_all()


    @step
    def follow(self):
        self.follower_node.make_a_follow_b(self.follower_actor_uri, self.leader_actor_uri, self.leader_node)


    @step
    def leader_creates_note(self):
        self.leader_note_uri = self.leader_node.make_create_note(self.leader_actor_uri, f"testing leader_creates_note {datetime.now()}")
        assert self.leader_note_uri


    @step
    def wait_for_note_in_leader_inbox(self):
        self.leader_node.wait_for_object_in_inbox(self.leader_actor_uri, self.leader_note_uri)


    @step
    def wait_for_note_in_follower_inbox(self):
        self.follower_node.wait_for_object_in_inbox(self.follower_actor_uri, self.leader_note_uri)


    @step
    def end_reset_all(self):
        self._reset_all()


    def _reset_all(self):
        """
        Clean up data. This is intended to be usable with non-brand-new instances.
        """
        self.leader_node.delete_all_followers_of(self.leader_actor_uri)
        self.leader_node.delete_all_following_of(self.leader_actor_uri)
        self.leader_node.delete_all_statuses_by(self.leader_actor_uri)

        self.follower_node.delete_all_followers_of(self.follower_actor_uri)
        self.follower_node.delete_all_following_of(self.follower_actor_uri)
        self.follower_node.delete_all_statuses_by(self.follower_actor_uri)

