"""Unit tests for user creation, deletion and their Kafka events."""

import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from orders.commands import write_user


@pytest.fixture
def user_dependencies(monkeypatch):
    session = MagicMock()
    producer_factory = MagicMock()
    monkeypatch.setattr(write_user, "get_sqlalchemy_session", lambda: session)
    monkeypatch.setattr(write_user, "UserEventProducer", producer_factory)
    return session, producer_factory


@pytest.mark.parametrize("user_type_id", [1, 2, 3])
def test_add_user_stores_type_and_publishes_event(user_dependencies, user_type_id):
    session, producer_factory = user_dependencies

    def flush():
        session.add.call_args.args[0].id = 42

    session.flush.side_effect = flush
    session.commit.side_effect = lambda: producer_factory.assert_not_called()

    assert write_user.add_user("Joé Test", "joe@example.com", user_type_id) == 42

    user = session.add.call_args.args[0]
    assert user.user_type_id == user_type_id
    session.commit.assert_called_once_with()
    send = producer_factory.return_value.get_instance.return_value.send
    send.assert_called_once()
    assert send.call_args.args == ("user-events",)
    event = send.call_args.kwargs["value"]
    assert event["event"] == "UserCreated"
    assert event["id"] == 42
    assert event["name"] == "Joé Test"
    assert event["email"] == "joe@example.com"
    assert event["user_type_id"] == user_type_id
    assert datetime.datetime.fromisoformat(event["datetime"])
    session.rollback.assert_not_called()
    session.close.assert_called_once_with()


@pytest.mark.parametrize("user_type_id", [None, 0, 4, "2", True, 2.0])
def test_add_user_rejects_invalid_type(user_dependencies, user_type_id):
    session, producer_factory = user_dependencies

    with pytest.raises(ValueError, match="user_type_id"):
        write_user.add_user("Joé Test", "joe@example.com", user_type_id)

    session.add.assert_not_called()
    session.commit.assert_not_called()
    producer_factory.assert_not_called()


@pytest.mark.parametrize("user_type_id", [1, 2, 3])
def test_delete_user_publishes_event_after_commit(user_dependencies, user_type_id):
    session, producer_factory = user_dependencies
    user = SimpleNamespace(
        id=42, name="Joé Test", email="joe@example.com", user_type_id=user_type_id
    )
    session.query.return_value.filter.return_value.first.return_value = user

    def commit():
        producer_factory.assert_not_called()
        # Simulate the user data becoming unavailable after deletion.
        user.name = None
        user.email = None
        user.user_type_id = None

    session.commit.side_effect = commit

    assert write_user.delete_user(42) == 1

    session.delete.assert_called_once_with(user)
    session.commit.assert_called_once_with()
    producer_factory.assert_called_once_with()
    send = producer_factory.return_value.get_instance.return_value.send
    send.assert_called_once()
    assert send.call_args.args == ("user-events",)
    event = send.call_args.kwargs["value"]
    assert event["event"] == "UserDeleted"
    assert event["id"] == 42
    assert event["name"] == "Joé Test"
    assert event["email"] == "joe@example.com"
    assert event["user_type_id"] == user_type_id
    assert datetime.datetime.fromisoformat(event["datetime"])
    session.rollback.assert_not_called()
    session.close.assert_called_once_with()


def test_delete_missing_user_does_not_publish_event(user_dependencies):
    session, producer_factory = user_dependencies
    session.query.return_value.filter.return_value.first.return_value = None

    assert write_user.delete_user(42) == 0

    session.delete.assert_not_called()
    session.commit.assert_not_called()
    producer_factory.assert_not_called()
    session.close.assert_called_once_with()


def test_delete_user_commit_failure_does_not_publish_event(user_dependencies):
    session, producer_factory = user_dependencies
    session.commit.side_effect = RuntimeError("Commit failed")

    with pytest.raises(RuntimeError, match="Commit failed"):
        write_user.delete_user(42)

    producer_factory.assert_not_called()
    session.rollback.assert_called_once_with()
    session.close.assert_called_once_with()
