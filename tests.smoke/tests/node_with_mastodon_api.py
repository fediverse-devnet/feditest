"""
Tests for our implementation of the NodeWithMastodonAPI.
This tests produces regular Python assertion errors, not feditest assertion errors, because
problems here are problems in our NodeDriver, not Fediverse interop problems.
"""

from datetime import datetime

from feditest import poll_until, step, test
from feditest.nodedrivers.mastodon import NodeWithMastodonAPI

# @test
# def app_version(
#         server: NodeWithMastodonAPI
#     ) -> None:
#         # FIXME: need to implement property mastodon_api_app_version
#         # This should access Mastodon without an authenticated user and we don't currently have code for how to do that
#         assert re.fullmatch(r'\d+\.\d+\.\d+', server.mastodon_api_app_version), "Invalid version"


@test
class CreateNoteTest:
    """
    Tests that we can create a Note through the Mastodon API.
    """
    def __init__(self,
        server: NodeWithMastodonAPI
    ) -> None:
        self.server = server
        self.actor_acct_uri = None
        self.note_uri = None


    @step
    def provision_actor(self):
        self.actor_acct_uri = self.server.obtain_actor_acct_uri()
        assert self.actor_acct_uri


#    @step
#    def start_reset_all(self):
#        self._reset_all()


    @step
    def create_note(self):
        self.note_uri = self.server.make_create_note(self.actor_acct_uri, f"testing make_create_note {datetime.now()}")
        assert self.note_uri


    @step
    def wait_for_note_in_inbox(self):
        poll_until(lambda: self.server.actor_has_received_object(self.actor_acct_uri, self.note_uri))


#    @step
#    def end_reset_all(self):
#        self._reset_all()


    def _reset_all(self):
        """
        Clean up data. This is here so the test is usable with non-brand-new instances.
        """
        self.server.delete_all_followers_of(self.actor_acct_uri)
        self.server.delete_all_statuses_by(self.actor_acct_uri)

