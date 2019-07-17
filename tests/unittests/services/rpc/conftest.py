from unittest import mock

import pytest

from scenario_player.services.utils.factories import construct_flask_app
from scenario_player.services.rpc.utils import generate_hash_key, RPCRegistry


@pytest.fixture
def default_create_rpc_instance_request_parameters():
    return {
        "chain_url": "https://test.net",
        "privkey": "my-private-key",
        "gas_price_strategy": "super-fast",
    }


@pytest.fixture
def deserialized_create_rpc_instance_request_parameters(
        default_create_rpc_instance_request_parameters
):
    deserialized = dict(default_create_rpc_instance_request_parameters)
    deserialized["privkey"] = deserialized["privkey"].encode("UTF-8")
    return deserialized


@pytest.fixture
def default_send_tx_request_parameters():
    """Default required request parameters for a POST request to /transactions."""
    parameters = {
        "to": 'someaddress',
        "value": 123.0,
        "startgas": 2.0,
    }
    return parameters


@pytest.fixture
def deserialized_send_tx_request_parameters(default_send_tx_request_parameters):
    deserialized = dict(default_send_tx_request_parameters)
    deserialized["to"] = deserialized["to"].encode("UTF-8")
    return deserialized


@pytest.fixture
def rpc_client_id(deserialized_create_rpc_instance_request_parameters):
    params = deserialized_create_rpc_instance_request_parameters
    return generate_hash_key(
        params["chain_url"],
        params["privkey"]
    )


@pytest.fixture
def transaction_service_app(rpc_client_id):
    app = construct_flask_app()
    app.config['TESTING'] = True
    app.config['rpc-client'] = RPCRegistry()
    app.config['rpc-client'].dict = {
        rpc_client_id: mock.Mock(**{"send_transaction.return_value": b"my_tx_hash"})
    }
    return app


@pytest.fixture
def transaction_service_client(transaction_service_app):
    return transaction_service_app.test_client()
