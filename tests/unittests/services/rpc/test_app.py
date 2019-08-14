from unittest.mock import patch

from scenario_player.services.rpc.app import (
    admin_blueprint,
    instances_blueprint,
    metrics_blueprint,
    rpc_app,
    tokens_blueprint,
    transactions_blueprint,
)
from scenario_player.services.rpc.utils import RPCRegistry

dummy_app = object()


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
