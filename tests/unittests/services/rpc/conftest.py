import base64
from unittest import mock

import pytest

from scenario_player.constants import GAS_STRATEGIES
from scenario_player.services.rpc.utils import RPCRegistry, generate_hash_key
from scenario_player.services.utils.factories import construct_flask_app


@pytest.fixture
def tx_hash():
    with open("/dev/urandom", "rb") as f:
        return f.read(8)


@pytest.fixture
def serialized_tx_hash(tx_hash):
    return base64.encodebytes(tx_hash).decode("ascii")


@pytest.fixture
def deserialized_privkey():
    with open("/dev/urandom", "rb") as f:
        return f.read(8)


@pytest.fixture
def serialized_privkey(deserialized_privkey):
    return base64.encodebytes(deserialized_privkey).decode("ascii")


@pytest.fixture
def deserialized_address():
    with open("/dev/urandom", "rb") as f:
        return f.read(8)


@pytest.fixture
def serialized_address(deserialized_address):
    return base64.encodebytes(deserialized_address).decode("ascii")


@pytest.fixture
def default_create_rpc_instance_request_parameters(serialized_privkey):
    return {
        "chain_url": "https://test.net",
        "privkey": serialized_privkey,
        "gas_price_strategy": "fast",
    }


@pytest.fixture
def deserialized_create_rpc_instance_request_parameters(
    default_create_rpc_instance_request_parameters, deserialized_privkey
):
    deserialized = dict(default_create_rpc_instance_request_parameters)
    deserialized["privkey"] = deserialized_privkey
    return deserialized


@pytest.fixture
def default_send_tx_request_parameters(rpc_client_id, serialized_address):
    """Default required request parameters for a POST request to /transactions."""
    parameters = {"client_id": rpc_client_id, "to": "the_address", "value": 123, "startgas": 2}
    return parameters


@pytest.fixture
def deserialized_send_tx_request_parameters(
    default_send_tx_request_parameters, rpc_service_app, deserialized_address
):
    deserialized = dict(default_send_tx_request_parameters)
    deserialized["client"] = rpc_service_app.config["rpc-client"][
        default_send_tx_request_parameters["client_id"]
    ]
    return deserialized


@pytest.fixture
def default_send_tx_func_parameters(deserialized_send_tx_request_parameters):
    args = dict(deserialized_send_tx_request_parameters)
    args.pop("client_id", None), args.pop("client", None)
    return args


@pytest.fixture
def rpc_client_id(deserialized_create_rpc_instance_request_parameters):
    params = deserialized_create_rpc_instance_request_parameters
    return generate_hash_key(params["chain_url"], params["privkey"], GAS_STRATEGIES["FAST"])


@pytest.fixture
def rpc_service_app(rpc_client_id, tx_hash):
    app = construct_flask_app()
    app.config["TESTING"] = True
    app.config["rpc-client"] = RPCRegistry()
    app.config["rpc-client"].dict = {
        rpc_client_id: mock.Mock(
            client_id=rpc_client_id, **{"send_transaction.return_value": tx_hash}
        )
    }
    return app


@pytest.fixture
def transaction_service_client(rpc_service_app):
    return rpc_service_app.test_client()
