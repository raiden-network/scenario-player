from unittest.mock import patch
import pytest

from scenario_player.services.transactions.app import construct_transaction_service
from scenario_player.services.transactions.blueprints.transactions import new_transaction


@pytest.fixture
def transaction_service_app():
    with patch('scenario_player.services.transactions.app.JSONRPCClient', autospec=True):
        app = construct_transaction_service()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def transaction_service_client(transaction_service_app):
    client = transaction_service_app.test_client()

    return client


class TestNewTransactionEndpoint:
    @pytest.mark.parametrize(
        'parameters, expected_status',
        argvalues=[
            ({"to_address": 'someaddress', "start_gas": 2}, 400),
            ({"value": 123, "start_gas": 2}, 400),
            ({"value": 123, "to_address": 'someaddress'}, 400),
            ({"value": 123, "to_address": 'someaddress', "start_gas": 2}, 200),
            ({"value": 'wholesome', "to_address": 'someaddress', "start_gas": 2}, 400),
            ({"value": 123, "to_address": 55, "start_gas": 2}, 400),
            ({"value": 123, "to_address": 'someaddress', "start_gas": 'hello'}, 400),
        ],
        ids=[
            "Missing 'value'",
            "Missing 'to_address'",
            "Missing 'start_gas'",
            "None missing - correct types"
            "None missing - 'value' type incorrect"
            "None missing - 'to_address' type incorrect"
            "None missing - 'start_gas' type incorrect"
        ]
    )
    def test_endpoint_requires_parameter_and_expects_types(
            self, parameters, expected_status, transaction_service_client
    ):
        """The transactions service's `POST /transactions` endpoint should requires a set of parameters with specific types..

        These are as follows:

            - `to_address` - a transaction hash, sent as a  `utf-8` encoded :class:`str`.
            - `start_gas` - the starting gas to use, as either :class:`int` or :class:`float`.
            - `amount` - the amount to send with the transaction, as either :class:`int` or :class:`float`.

        If either one or more is missing, or has an incorrect type, we expect to
        see a `400 Bad Request` response from the service.
        """
        resp = transaction_service_client.post('/transactions', data=parameters)
        assert resp.status == expected_status

    @patch('scenario_player.services.transactions.blueprints.TransactionSendRequest')
    def test_new_transaction_calls_validate_and_serialize_of_its_validator_schema(
            self, mock_validator, transaction_service_app
    ):
        """The :meth:`scenario_player.services.transactions.blueprints.TransactionSendRequest.validate_and_serialize`
        must be called when processing a request.
        """
        parameters = {"value": 123, "to_address": 'someaddress', "start_gas": 2}
        with transaction_service_app.app_context(
                '/transactions', data=parameters):
            new_transaction()
        mock_validator.validate_and_serialize.assert_called_once_with(parameters)

    @patch('scenario_player.services.transactions.blueprints.TransactionSendResponse')
    def test_new_transaction_calls_dump_of_its_serializer_schema(self, mock_serializer, transaction_service_app):
        """The :meth:`scenario_player.services.transactions.blueprints.TransactionSendResponse.dump`
        must be called when processing a request and its reulst returned by the function.
        """
        expected_tx_hash = b'my_tx_hash'
        transaction_service_app.config['rpc-client'].send_transaction.return_value = expected_tx_hash
        parameters = {"value": 123, "to_address": 'someaddress', "start_gas": 2}
        with transaction_service_app.app_context(
                '/transactions', data=parameters):
            new_transaction()
        mock_serializer.validate_and_serialize.assert_called_once_with(expected_tx_hash)

    @patch('scenario_player.services.transactions.blueprints.TransactionSendRequest')
    def test_new_transaction_calls_the_services_jsonrpc_client_with_the_requests_params(self, mock_validator, transaction_service_app):
        """The method :meth:`JSONRPCClient.send_transaction` must be called with the parameters of the request
        and its result passed to :meth:`scenario_player.services.transactions.blueprints.TransactionSendResponse.dump`.
        """
        parameters = {"value": 123, "to_address": 'someaddress', "start_gas": 2}
        mock_validator.return_value = parameters
        with transaction_service_app.app_context(
            '/transactions', data=parameters):
            new_transaction()
        transaction_service_app.config['rpc-client'].send_transaction.assert_called_once_with(parameters)

    def test_new_transaction_aborts_with_500_if_no_rpc_client_key_exists_in_app_config(
            self, transaction_service_client
    ):
        """A `500 Internal Server Error` is expected, if :func:`new_transaction` cannot find a
        :class:`JSONRPCClient` instance.

        Specifically, if no `'rpc-client'` key exists in the :attr:`flask.Flask.config` dictionary
        """
        parameters = {"value": 123, "to_address": 'someaddress', "start_gas": 2}
        transaction_service_client.app.config.pop('rpc-client')
        resp = transaction_service_client,post('/transactions', data=parameters)
        assert resp.status == 500
        assert "No JSONRPCClient instance available on service!" in resp.data

    def test_new_transaction_aborts_with_500_if_rpc_client_key_value_is_not_a_valid_instance_of_rpc_client(
            self, transaction_service_app
    ):
        """A `500 Internal Server Error` is expected, if :func:`new_transaction` cannot find a
        :class:`JSONRPCClient` instance.

        Specifically, if :var:`flask.Flask.config['rpc-client']` is not an instance of :class:`JSONRPCClient`.
        """
        parameters = {"value": 123, "to_address": 'someaddress', "start_gas": 2}
        transaction_service_client.app.config['rpc-client'] = "This is not a JSONRPCClient instance."
        resp = transaction_service_client,post('/transactions', data=parameters)
        assert resp.status == 500
        assert "No JSONRPCClient instance available on service!" in resp.data
