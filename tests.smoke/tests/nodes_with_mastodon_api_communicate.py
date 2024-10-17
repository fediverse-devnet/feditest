"""
Tests that two nodes that implement the Mastodon API can follow each other.
"""

from datetime import datetime
import time

from feditest import poll_until, step, test
from feditest.nodedrivers.mastodon import NodeWithMastodonAPI


@test
class FollowTest:
    def __init__(self,
        leader_node: NodeWithMastodonAPI,
        follower_node: NodeWithMastodonAPI
    ) -> None:
        self.leader_node = leader_node
        self.leader_actor_acct_uri = None

        self.follower_node = follower_node
        self.follower_actor_acct_uri = None

        self.leader_note_uri = None


    @step
    def provision_actors(self):
        self.leader_actor_acct_uri = self.leader_node.obtain_actor_acct_uri()
        assert self.leader_actor_acct_uri
        self.leader_node.set_auto_accept_follow(self.leader_actor_acct_uri, True)

        self.follower_actor_acct_uri = self.follower_node.obtain_actor_acct_uri()
        assert self.follower_actor_acct_uri


    # @step
    # def start_reset_all(self):
    #     self._reset_all()


    @step
    def follow(self):
        self.follower_node.make_follow(self.follower_actor_acct_uri, self.leader_actor_acct_uri)


    @step
    def wait_until_actor_is_followed_by_actor(self):
        time.sleep(1) # Sometimes there seems to be a race condition in Mastodon, or something like that.
                      # If we proceed too quickly, the API returns 422 "User already exists" or such
                      # in response to a search, which makes no sense.
        poll_until(lambda: self.leader_node.actor_is_followed_by_actor(self.leader_actor_acct_uri, self.follower_actor_acct_uri))


    @step
    def wait_until_actor_is_following_actor(self):
        poll_until(lambda: self.follower_node.actor_is_following_actor(self.follower_actor_acct_uri, self.leader_actor_acct_uri))


    @step
    def leader_creates_note(self):
        self.leader_note_uri = self.leader_node.make_create_note(self.leader_actor_acct_uri, f"testing leader_creates_note {datetime.now()}")
        assert self.leader_note_uri


    @step
    def wait_until_note_received(self):
        poll_until(lambda: self.follower_node.actor_has_received_object(self.follower_actor_acct_uri, self.leader_note_uri))


    # @step
    # def end_reset_all(self):
    #     self._reset_all()


    def _reset_all(self):
        """
        Clean up data. This is here so the test is usable with non-brand-new instances.
        """
        self.leader_node.delete_all_followers_of(self.leader_actor_acct_uri)
        self.leader_node.delete_all_following_of(self.leader_actor_acct_uri)
        self.leader_node.delete_all_statuses_by(self.leader_actor_acct_uri)

        self.follower_node.delete_all_followers_of(self.follower_actor_acct_uri)
        self.follower_node.delete_all_following_of(self.follower_actor_acct_uri)
        self.follower_node.delete_all_statuses_by(self.follower_actor_acct_uri)

