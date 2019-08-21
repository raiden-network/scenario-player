from unittest.mock import patch, Mock

from scenario_player.services.rpc.app import (
    admin_blueprint,
    instances_blueprint,
    metrics_blueprint,
    serve,
    tokens_blueprint,
    transactions_blueprint,
)
from scenario_player.services.rpc.utils import RPCRegistry

dummy_app = object()


@patch("scenario_player.services.rpc.app.waitress.serve")
@patch("scenario_player.services.rpc.app.flask.Flask", autospec=True)
def test_rpc_app_constructor(mock_app, mock_serve):
    parsed = Mock(port=5100, host="127.0.0.1")
    app = serve(parsed)
    blueprints = [
        admin_blueprint,
        instances_blueprint,
        metrics_blueprint,
        tokens_blueprint,
        transactions_blueprint,
    ]
    for bp in blueprints:
        mock_app.register_blueprint.assert_any_call(bp)

    assert isinstance(app.config.get("rpc-client"), RPCRegistry)

    mock_serve.assert_called_once_with(mock_app, host=parsed.host, port=parsed.port)