from unittest import mock
from flask import Response
import pytest


from scenario_player.services.common.blueprints.admin import admin_blueprint, shutdown_server
from scenario_player.services.common.factories import construct_flask_app


@pytest.fixture
def client():
    app = construct_flask_app(admin_blueprint)
    app.config['TESTING'] = True
    client = app.test_client()

    return client


@mock.patch('scenario_player.services.common.blueprints.admin.shutdown_server', return_value=Response(status=200))
def test_shutdown_endpoint_returns_200_when_used_with_werkzeug_server(mock_shutdown, client):
    response = client.post('/shutdown')

    assert response.status_code == 200
    assert mock_shutdown.called
    assert mock_shutdown.call_count == 1


@mock.patch('scenario_player.services.common.blueprints.admin.request')
class TestShutdownServerFunc:

    def test_raises_runtime_error_if_no_werkzeug_shutdown_func_avaialable_in_app_environ(self, mock_flask_request):
        """Our shutdown endpoint only works properly if it's a :mod:`werkzeug`-based server.

        Assert that if this is not the case, we raise a :exc:`RunTimeError`.
        """
        mock_flask_request.environ = {}

        with pytest.raises(RuntimeError, match="Not running with the Werkzeug Server"):
            shutdown_server()

    def test_executes_shutdown_sequence_if_werkzeug_shutdown_func_available_in_app_environ(self, mock_flask_request):
        """If the server this function is used on is a :mod:`werkzeug`-ased server, make sure we're calling the
        shutdown function available from the app environment."""
        mock_flask_request.environ = {"werkzeug.server.shutdown": mock.Mock()}

        shutdown_server()

        assert mock_flask_request.environ["werkzeug.server.shutdown"].called
        assert mock_flask_request.environ["werkzeug.server.shutdown"].call_count == 1
