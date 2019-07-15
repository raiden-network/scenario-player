import pytest

from scenario_player.services.utils.factories import construct_flask_app


@pytest.fixture
def transaction_service_app():
    app = construct_flask_app()
    app.config['TESTING'] = True
    app.config['rpc-client'] = {}
    return app


@pytest.fixture
def transaction_service_client(transaction_service_app):
    return transaction_service_app.test_client()


@pytest.fixture
def default_send_tx_request_parameters():
    """Default required request parameters for a POST request to /transactions.

    FIXME: Update the parameters once #96 is implemented.
     See here for more details:
        https://github.com/raiden-network/scenario-player/issues/96

    """
    parameters = {
        "chain_url": "http://test.net",
        "privkey": "1z2x3c4v5b6n7m8,9.0pkjhgfdswert2",
        "gas_price_strategy": "fast",
        "to": 'someaddress',
        "value": 123.0,
        "startgas": 2.0,
    }
    return parameters


@pytest.fixture
def deserialized_send_tx_request_parameters(default_send_tx_request_parameters):
    deserialized = dict(default_send_tx_request_parameters)
    deserialized["to"] = deserialized["to"].encode("UTF-8")
    deserialized["privkey"] = deserialized["privkey"].encode("UTF-8")
    return deserialized
