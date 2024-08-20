# SPDX-FileCopyrightText: 2023-2024 Johannes Ernst
# SPDX-FileCopyrightText: 2023-2024 Steve Bate
#
# SPDX-License-Identifier: MIT

import json
import os
import re
from datetime import datetime

import feditest
import pytest

pytest.skip(
    "Mastodon tests are disabled until they are fixed.", 
    allow_module_level=True,
)

@pytest.fixture(scope="module")
def mmnode_class():
    """ Keep these isolated to this module """
    feditest.all_node_drivers = {}
    feditest._loading_node_drivers = True

    from feditest.nodedrivers.mastodon.manual import MastodonManualNode  # noqa

    feditest._loading_node_drivers = False

    return MastodonManualNode


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


@pytest.fixture(scope="module")
def node(mmnode_class):
    cwd = os.path.dirname(__file__)
    try:
        with open(os.path.join(cwd, "mastodon_parameters.json")) as fp:
            parameters = json.load(fp)
            parameters["app"] = "?"
            return mmnode_class("client", parameters, object())
    except FileNotFoundError:
        pytest.skip("No Mastodon test configuration")


@pytest.fixture(autouse=True, scope="module")
def session_setup(node):
    node.delete_follows()
    node.delete_statuses()


@pytest.fixture(scope="module")
def note_uri(node):
    note_uri = node.make_create_note(None, f"testing make_create_note {datetime.now()}")
    node.wait_for_object_in_inbox(None, note_uri)
    return note_uri


# make_create_node is implied by other tests


def test_announce_note(node, note_uri: str):
    announce_uri = node.make_announce_object(None, note_uri)
    print(announce_uri)


def test_reply_note(node, note_uri: str):
    reply_uri = node.make_reply(None, note_uri, f"test_reply_note {datetime.now()}")
    print(reply_uri)


def test_follow_local(node):
    node.follow("primary_actor", "secondary_actor")


def test_follow_remote(node):
    if "external_actor" in node.actors_by_role:
        node.follow("primary_actor", "external_actor")
    else:
        pytest.skip("No external actor is configured")

def test_server_version(node):
    assert re.match(r'\d+\.\d+\.\d+', node.server_version), "Invalid version"