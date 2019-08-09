import logging
from unittest.mock import patch

from scenario_player.services.common.app import serve_spaas_stack

dummy_app = object()


@patch("scenario_player.services.common.app.construct_flask_app", return_value=dummy_app)
@patch("scenario_player.services.common.app.waitress.serve")
class TestServerSPaaSStack:
    def test_calls_waitress_serve_with_args(self, mock_serve, _, tmp_path):
        serve_spaas_stack(tmp_path.joinpath("tetst.log"), "127.0.0.666", 1000)
        mock_serve.assert_called_once_with(dummy_app, host="127.0.0.666", port=1000)

    @patch("scenario_player.services.common.app.logging.basicConfig", autospec=True)
    @patch("scenario_player.services.common.app.structlog.getLogger", autospec=True)
    def test_configures_logging(self, mock_structlog, mock_logging, _, __, tmp_path):
        logfile = tmp_path.joinpath("test.log")
        serve_spaas_stack(logfile, "127.0.0.1", 5000)
        mock_structlog.assert_called_once()
        mock_logging.assert_called_once_with(filename=logfile, filemode="a+", level=logging.DEBUG)
