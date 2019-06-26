from raiden.network.rpc.client import JSONRPCClient
from scenario_player.services.common.factories import construct_flask_app, attach_blueprints
from scenario_player.services.transactions.blueprints import (
    transactions_blueprint, tokens_blueprint
)


def attach_transaction_service(app, **JSONRPCClient_kwargs):
    attach_blueprints(app, transactions_blueprint, tokens_blueprint)
    app.config['rpc-client'] = JSONRPCClient(**JSONRPCClient_kwargs)
    return app


def construct_transaction_service(test_config=None, **JSONRPCClien_kwargs):
    app = construct_flask_app(tokens_blueprint, transactions_blueprint, db_name="transactions_service", test_config=test_config)
    attach_transaction_service(app, **JSONRPCClien_kwargs)
    return app