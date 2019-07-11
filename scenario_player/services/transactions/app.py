from raiden.network.rpc.client import JSONRPCClient
from scenario_player.services.common.factories import construct_flask_app
from scenario_player.services.transactions.blueprints import (
    transactions_blueprint, tokens_blueprint
)

from scenario_player.hooks.impl import HOOK_IMPL


@HOOK_IMPL
def register_blueprints():
    """Register a list of blueprints with :mode:`raiden-scenario-player`."""
    return [transactions_blueprint, tokens_blueprint]


def construct_transaction_service(test_config=None, **JSONRPCClien_kwargs):
    app = construct_flask_app(db_name="transactions_service", test_config=test_config)
    app.config['rpc-client'] = JSONRPCClient(**JSONRPCClien_kwargs)
    return app
