import json
import os
from datetime import datetime

import pytest

# Needed to override some of the static behaviors for test support
os.environ["ALLOW_EXTERNAL_NODE_DRIVERS"] = "1"
from feditest.nodedrivers.mastodon.api import MastodonNode  # noqa

# To run these tests, you must create a file mastodon_parameters.json
# in this test directory with parameters like the following.
#
# Example test config
# {
#     "hostname": "...",
#     "actors": {
#         "default_role": "primary_actor",
#         "roles": {
#             "primary_actor": {
#                 "access_token": "TOKEN",
#                 "uri": "https://MASTODON_HOSTNAME/users/tester"
#             },
#             "secondary_actor": {
#                 "uri": "https://MASTODON_HOSTNAME/users/tester2"
#             },
#             "disabled_external_actor": {
#                 "uri": "https://MASTODON_HOSTNAME/users/steve"
#             }
#         }
#     }
# }


@pytest.fixture(scope="session")
def node():
    cwd = os.path.dirname(__file__)
    with open(os.path.join(cwd, "mastodon_parameters.json")) as fp:
        parameters = json.load(fp)
        return MastodonNode("client", parameters, None)


@pytest.fixture(autouse=True, scope="session")
def session_setup(node: MastodonNode):
    node.delete_follows()
    node.delete_statuses()


@pytest.fixture(scope="session")
def note_uri(node: MastodonNode):
    note_uri = node.make_create_note(None, f"testing make_create_note {datetime.now()}")
    node.wait_for_object_in_inbox(None, note_uri)
    return note_uri


# make_create_node is implied by other tests


def test_announce_note(node: MastodonNode, note_uri: str):
    announce_uri = node.make_announce_object(None, note_uri)
    print(announce_uri)


def test_reply_note(node: MastodonNode, note_uri: str):
    reply_uri = node.make_reply(None, note_uri, f"test_reply_note {datetime.now()}")
    print(reply_uri)


def test_follow_local(node: MastodonNode):
    node.follow("primary_actor", "secondary_actor")


def test_follow_remote(node: MastodonNode):
    if "external_actor" in node.actors_by_role:
        node.follow("primary_actor", "external_actor")
    else:
        pytest.skip("No external actor is configured")
