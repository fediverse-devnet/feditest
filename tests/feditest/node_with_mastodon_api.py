"""
Tests for our implementation of the NodeWithMastodonAPI implementatin
"""

from datetime import datetime

from feditest import step, test
from feditest.nodedrivers.mastodon import NodeWithMastodonAPI


@test
class CreateNoteTest:
    """
    Tests that we can create a Note through the Mastodon API.
    """
    def __init__(self,
        server: NodeWithMastodonAPI
    ) -> None:
        self.server = server
        self.actor_uri = None
        self.note_uri = None


    @step
    def provision_actor(self):
        self.actor_uri = self.server.obtain_actor_document_uri()


    @step
    def start_reset_all(self):
        self._reset_all()


    @step
    def create_note(self):
        self.note_uri = self.server.make_create_note(self.actor_uri, f"testing make_create_note {datetime.now()}")


    @step
    def wait_for_note_in_inbox(self):
        self.server.wait_for_object_in_inbox(self.actor_uri, self.note_uri)


    @step
    def end_reset_all(self):
        self._reset_all()


    def _reset_all(self):
        """
        Clean up data. This is intended to be usable with a non-brand-new instance.
        """
        self.server.delete_all_followers_of(self.actor_uri)
        self.server.delete_all_statuses_by(self.actor_uri)

