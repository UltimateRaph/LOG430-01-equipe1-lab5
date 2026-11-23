"""Vérifie la gestion de transaction nécessaire à la saga de stock."""
from unittest.mock import Mock, patch

import pytest
from flask import Flask

from stocks.controllers.stock_controller import update_stock


def test_update_stock_commits_and_closes_session():
    session = Mock()
    payload = {"items": [{"product_id": 1, "quantity": 2}], "operation": "-"}
    with Flask(__name__).test_request_context(json=payload), \
            patch("stocks.controllers.stock_controller.get_sqlalchemy_session", return_value=session), \
            patch("stocks.controllers.stock_controller.update_stock_mysql") as update:
        response, status = update_stock(Mock(get_json=Mock(return_value=payload)))

        assert status == 201
        assert response.get_json() == {"result": "OK"}
        update.assert_called_once_with(session, payload["items"], "-")
        session.commit.assert_called_once()
        session.rollback.assert_not_called()
        session.close.assert_called_once()


@pytest.mark.parametrize("failing_step", ["update_stock_mysql", "commit"])
def test_update_stock_rolls_back_and_closes_session(failing_step):
    session = Mock()
    error = RuntimeError("Transaction impossible")
    with Flask(__name__).test_request_context(), \
            patch("stocks.controllers.stock_controller.get_sqlalchemy_session", return_value=session), \
            patch("stocks.controllers.stock_controller.update_stock_mysql") as update:
        if failing_step == "update_stock_mysql":
            update.side_effect = error
        else:
            session.commit.side_effect = error

        response, status = update_stock(Mock(get_json=Mock(return_value={})))

        assert status == 500
        assert response.get_json() == {"error": str(error)}
        session.rollback.assert_called_once()
        session.close.assert_called_once()


def test_update_stock_handles_session_creation_failure():
    with Flask(__name__).test_request_context(), \
            patch("stocks.controllers.stock_controller.get_sqlalchemy_session",
                  side_effect=RuntimeError("Connexion impossible")):
        response, status = update_stock(Mock(get_json=Mock(return_value={})))

        assert status == 500
        assert response.get_json() == {"error": "Connexion impossible"}
