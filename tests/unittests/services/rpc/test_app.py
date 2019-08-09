import logging
from unittest.mock import patch

from scenario_player.services.rpc.app import (
    admin_blueprint,
    instances_blueprint,
    metrics_blueprint,
    rpc_app,
    serve_rpc,
    tokens_blueprint,
    transactions_blueprint,
)
from scenario_player.services.rpc.utils import RPCRegistry

dummy_app = object()


@patch("scenario_player.services.rpc.app.rpc_app", return_value=dummy_app)
@patch("scenario_player.services.rpc.app.waitress.serve")
class TestServeRPC:
    def test_calls_waitress_serve_with_args(self, mock_serve, _, tmp_path):
        serve_rpc(tmp_path.joinpath("tetst.log"), "127.0.0.666", 1000)
        mock_serve.assert_called_once_with(dummy_app, host="127.0.0.666", port=1000)

    @patch("scenario_player.services.rpc.app.logging.basicConfig", autospec=True)
    @patch("scenario_player.services.rpc.app.structlog.getLogger", autospec=True)
    def test_configures_logging(self, mock_structlog, mock_logging, _, __, tmp_path):
        logfile = tmp_path.joinpath("test.log")
        serve_rpc(logfile, "127.0.0.1", 5000)
        mock_structlog.assert_called_once()
        mock_logging.assert_called_once_with(filename=logfile, filemode="a+", level=logging.DEBUG)


@patch("scenario_player.services.rpc.app.flask.Flask.register_blueprint")
def test_rpc_app_constructor(mock_register_bp):
    app = rpc_app()
    blueprints = [
        admin_blueprint,
        instances_blueprint,
        metrics_blueprint,
        tokens_blueprint,
        transactions_blueprint,
    ]
    for bp in blueprints:
        mock_register_bp.assert_any_call(bp)

    assert isinstance(app.config.get("rpc-client"), RPCRegistry)
