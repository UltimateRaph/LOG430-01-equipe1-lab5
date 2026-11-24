"""Tests for the user type accepted by POST /users."""

from unittest.mock import MagicMock

import pytest
from orders.controllers import user_controller
from store_manager import app


@pytest.mark.parametrize("user_type_id", [1, 2, 3])
def test_create_user_passes_type_to_command(monkeypatch, user_type_id):
    add_user = MagicMock(return_value=42)
    monkeypatch.setattr(user_controller, "add_user", add_user)

    with app.test_client() as client:
        response = client.post('/users', json={
            'name': 'Test User',
            'email': 'test@example.com',
            'user_type_id': user_type_id,
        })

    assert response.status_code == 201
    assert response.get_json() == {'user_id': 42}
    add_user.assert_called_once_with('Test User', 'test@example.com', user_type_id)


@pytest.mark.parametrize("payload", [
    {'name': 'Test User', 'email': 'test@example.com'},
    {'name': 'Test User', 'email': 'test@example.com', 'user_type_id': 99},
    {'name': 'Test User', 'email': 'test@example.com', 'user_type_id': '2'},
    {'name': 'Test User', 'email': 'test@example.com', 'user_type_id': True},
])
def test_create_user_rejects_missing_or_invalid_type(payload):
    with app.test_client() as client:
        response = client.post('/users', json=payload)

    assert response.status_code == 400
    assert 'user_type_id' in response.get_json()['error']
