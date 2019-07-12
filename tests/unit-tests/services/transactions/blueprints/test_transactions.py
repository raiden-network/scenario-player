from unittest.mock import patch
import pytest
from raiden.network.rpc import client
from scenario_player.services.utils.factories import construct_flask_app

import logging


@pytest.fixture
def transaction_service_app():
    with patch.object(client, "JSONRPCClient", autospec=True):
        app = construct_flask_app()
        app.config['TESTING'] = True
        app.config['rpc-client'] = client.JSONRPCClient(web3='web3_instance', privkey=b"my_private_key")
        yield app


@pytest.fixture
def transaction_service_client(transaction_service_app):
    client = transaction_service_app.test_client()

    return client


@pytest.mark.dependency(name="transaction_blueprint_loaded")
def test_transaction_blueprint_is_loaded(transaction_service_client):
    assert "transactions_view" in transaction_service_client.application.blueprints


@pytest.mark.dependency(depends=["transaction_blueprint_loaded"])
class TestNewTransactionEndpoint:

    @pytest.mark.parametrize(
        'parameters, expected_status',
        argvalues=[
            ({"to": 'someaddress', "startgas": 2}, '400'),
            ({"value": 123, "startgas": 2}, '400'),
            ({"value": 123, "to": 'someaddress'}, '400'),
            ({"value": 123, "to": 'someaddress', "startgas": 2}, '200'),
            ({"value": 'wholesome', "to": 'someaddress', "startgas": 2}, '400'),
            ({"value": 123, "to": 55, "startgas": 2}, '400'),
            ({"value": 123, "to": 'someaddress', "startgas": 'hello'}, '400'),
        ],
        ids=[
            "Missing 'value'",
            "Missing 'to_address'",
            "Missing 'startgas'",
            "None missing - correct types",
            "None missing - 'value' type incorrect",
            "None missing - 'to_address' type incorrect",
            "None missing - 'startgas' type incorrect",
        ]
    )
    def test_endpoint_requires_parameter_and_expects_types(
            self, parameters, expected_status, transaction_service_client
    ):
        """The transactions service's `POST /transactions` endpoint requires a set of parameters with specific types.

        These are as follows:

            - `to_address` - a transaction hash, sent as a  `utf-8` encoded :class:`str`.
            - `startgas` - the starting gas to use, as either :class:`int` or :class:`float`.
            - `amount` - the amount to send with the transaction, as either :class:`int` or :class:`float`.

        If either one or more is missing, or has an incorrect type, we expect to
        see a `400 Bad Request` response from the service.
        """
        transaction_service_client.application.config['rpc-client'].send_transaction.return_value = b"tx_hash"
        resp = transaction_service_client.post('/transactions', data=parameters)

        assert expected_status in resp.status

    @patch('scenario_player.services.transactions.blueprints.transactions.TransactionSendRequest', autospec=True)
    def test_new_transaction_calls_load_of_its_validator_schema(
            self, mock_validator, transaction_service_client
    ):
        """The :meth:`scenario_player.services.transactions.blueprints.TransactionSendRequest.validate_and_deserialize`
        must be called when processing a request.
        """
        parameters = {"value": 123, "to_address": 'someaddress', "startgas": 2}
        mock_validator.load.return_value = parameters
        transaction_service_client.post('/transactions', data=parameters)
        mock_validator.load.assert_called_once_with(parameters)

    @patch('scenario_player.services.transactions.blueprints.transactions.TransactionSendRequest', autospec=True)
    def test_new_transaction_calls_dump_of_its_serializer_schema(self, mock_serializer, transaction_service_client):
        """The :meth:`scenario_player.services.transactions.blueprints.TransactionSendRequest.dump`
        must be called when processing a request and its result returned by the function.
        """
        expected_tx_hash = b'my_tx_hash'
        transaction_service_client.application.config['rpc-client'].send_transaction.return_value = expected_tx_hash
        parameters = {"value": 123, "to_address": 'someaddress', "startgas": 2}
        transaction_service_client.post('/transactions', data=parameters)
        mock_serializer.dump.assert_called_once_with(expected_tx_hash)

    @patch('scenario_player.services.transactions.blueprints.transactions.TransactionSendRequest', autospec=True)
    def test_new_transaction_calls_the_services_jsonrpc_client_with_the_requests_params(
            self, mock_validator, transaction_service_client
    ):
        """The method :meth:`JSONRPCClient.send_transaction` must be called with the parameters of the request
        and its result passed to :meth:`scenario_player.services.transactions.blueprints.TransactionSendRequest.dump`.
        """
        parameters = {"value": 123, "to_address": 'someaddress', "startgas": 2}
        mock_validator.validate_and_deserialize.return_value = parameters
        transaction_service_client.post('/transactions', data=parameters)
        transaction_service_client.application.config['rpc-client'].send_transaction.assert_called_once_with(parameters)

    def test_new_transaction_aborts_with_500_if_no_rpc_client_key_exists_in_app_config(
            self, transaction_service_client
    ):
        """A `500 Internal Server Error` is expected, if :func:`new_transaction` cannot find a
        :class:`JSONRPCClient` instance.

        Specifically, if no `'rpc-client'` key exists in the :attr:`flask.Flask.config` dictionary
        """
        parameters = {"value": 123, "to_address": 'someaddress', "startgas": 2}
        transaction_service_client.application.config.pop('rpc-client')
        resp = transaction_service_client.post('/transactions', data=parameters)
        assert '500' in resp.status
        assert "No JSONRPCClient instance available on service!" in resp.data

    def test_new_transaction_aborts_with_500_if_rpc_client_key_value_is_not_a_valid_instance_of_rpc_client(
            self, transaction_service_client
    ):
        """A `500 Internal Server Error` is expected, if :func:`new_transaction` cannot find a
        :class:`JSONRPCClient` instance.

        Specifically, if :var:`flask.Flask.config['rpc-client']` is not an instance of :class:`JSONRPCClient`.
        """
        parameters = {"value": 123, "to_address": 'someaddress', "startgas": 2}
        transaction_service_client.application.config['rpc-client'] = "This is not a JSONRPCClient instance."
        resp = transaction_service_client.post('/transactions', data=parameters)
        assert '500' in resp.status
        assert "No JSONRPCClient instance available on service!" in resp.data
