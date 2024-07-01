import os
import signal
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

import feditest

# Workaround for global flags
feditest._loading_node_drivers = True

import pytest
from feditest.nodedrivers.grpc.client import GrpcNodeClient, GrpcNodeClientDriver
from feditest.nodedrivers.grpc.server import ExampleNodeServer


@pytest.fixture(scope="session")
def grpc_server():
    # Start the subprocess
    process = subprocess.Popen(["python", "src/feditest/nodedrivers/grpc/server.py"])
    time.sleep(2)
    print("ExampleNodeServer subprocess started")
    yield
    os.kill(process.pid, signal.SIGTERM)
    process.wait()
    print("ExampleNodeServer subprocess terminated")


@pytest.fixture(scope="session")
def node_client(grpc_server):
    driver = GrpcNodeClientDriver("grpc_test")
    node = driver._provision_node("client", {"server_endpoint": "localhost:50051"})
    yield node
    node.close()


def test_obtain_actor_document_uri(node_client: GrpcNodeClient):
    actor_uri = node_client.obtain_actor_document_uri()
    assert actor_uri == "https://server.test/actor/carol"


def test_obtain_followers_collection_uri(node_client: GrpcNodeClient):
    uri = node_client.obtain_followers_collection_uri()
    assert uri == "https://server.test/actor/carol/followers"


def test_obtain_following_collection_uri(node_client: GrpcNodeClient):
    uri = node_client.obtain_following_collection_uri()
    assert uri == "https://server.test/actor/carol/following"


def test_create_note(node_client: GrpcNodeClient):
    uri = node_client.make_create_note(
        "https://server.test/bob",
        "Let's get root beer",
    )
    assert uri == "https://server.test/activities/Create/1"


def test_wait_for_object_in_inbox_succeeded(node_client: GrpcNodeClient):
    uri = node_client.wait_for_object_in_inbox(
        "https://server.test/bob",
        "https://server.test/note/1",
    )
    assert uri == "https://server.test/note/1"


def test_wait_for_object_in_inbox_failed(node_client: GrpcNodeClient):
    with pytest.raises(AssertionError):
        node_client.wait_for_object_in_inbox(
            "https://server.test/bob",
            "https://server.test/note/2",
        )


def test_make_announce_object(node_client: GrpcNodeClient):
    activity_uri = node_client.make_announce_object(
        "https://server.test/bob",
        "https://server.test/note/1",
    )
    assert activity_uri == "https://server.test/announce"


def test_make_reply(node_client: GrpcNodeClient):
    activity_uri = node_client.make_reply(
        "https://server.test/bob",
        "https://server.test/note/1",
        "Root Beer?! Je veux bien!",
    )
    assert activity_uri == "https://server.test/reply"


def test_make_a_follow_b(node_client: GrpcNodeClient):
    is_accepted = node_client.make_a_follow_b(
        "https://server.test/bob", "https://server.test/carol", None
    )
    assert is_accepted


def test_assert_member__success(node_client: GrpcNodeClient):
    node_client.assert_member_of_collection_at(
        "https://server.test/carol",
        "https://server.test/collection",
    )
    # No exception


def test_assert_not_member__success(node_client: GrpcNodeClient):
    node_client.assert_not_member_of_collection_at(
        "https://server.test/bob",
        "https://server.test/collection",
    )
    # No exception


def test_assert_not_member__failed(node_client: GrpcNodeClient):
    with pytest.raises(AssertionError):
        node_client.assert_not_member_of_collection_at(
            "https://server.test/carol",
            "https://server.test/collection",
        )


def test_assert_member__failed(node_client: GrpcNodeClient):
    with pytest.raises(AssertionError):
        node_client.assert_member_of_collection_at(
            "https://server.test/bob",
            "https://server.test/collection",
        )
