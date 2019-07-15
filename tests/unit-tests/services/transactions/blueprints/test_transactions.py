from unittest.mock import patch

import pytest

from raiden.network.rpc import client
from scenario_player.services.utils.factories import construct_flask_app


@pytest.fixture
def transaction_service_app():
    with patch.object(client, "JSONRPCClient", autospec=True):
        app = construct_flask_app()
        app.config['TESTING'] = True
        app.config['rpc-client'] = client.JSONRPCClient(web3='web3_instance', privkey=b"my_private_key")
        app.config['rpc-client'].send_transaction.return_value = b"result"

        yield app


@pytest.fixture
def transaction_service_client(transaction_service_app):
    return transaction_service_app.test_client()


@pytest.mark.dependency(name="transaction_blueprint_loaded")
def test_transaction_blueprint_is_loaded(transaction_service_client):
    assert "transactions_view" in transaction_service_client.application.blueprints


@pytest.mark.dependency(depends=["transaction_blueprint_loaded"])
class TestNewTransactionEndpoint:

    @pytest.mark.parametrize(
        'parameters, expected_status',
        argvalues=[
            ({"to": 'someaddress', "startgas": 2.0}, '400'),
            ({"value": 123.0, "startgas": 2.0}, '400'),
            ({"value": 123.0, "to": 'someaddress'}, '400'),
            ({"value": 123.0, "to": 'someaddress', "startgas": 2.0}, '200'),
            ({"value": 'wholesome', "to": 'someaddress', "startgas": 2.0}, '400'),
            ({"value": 123.0, "to": 'someaddress', "startgas": 'hello'}, '400'),
        ],
        ids=[
            "Missing 'value'",
            "Missing 'to'",
            "Missing 'startgas'",
            "None missing - correct types",
            "None missing - 'value' type incorrect",
            "None missing - 'startgas' type incorrect",
        ]
    )
    def test_endpoint_requires_parameter_and_expects_types(
            self, parameters, expected_status, transaction_service_client
    ):
        """The transactions service's `POST /transactions` endpoint requires a set of parameters with specific types.

        These are as follows:

            - `to` - a transaction hash, sent as a  `utf-8` encoded :class:`str`.
            - `startgas` - the starting gas to use, as either :class:`int` or :class:`float`.
            - `amount` - the amount to send with the transaction, as either :class:`int` or :class:`float`.

        If either one or more is missing, or has an incorrect type, we expect to
        see a `400 Bad Request` response from the service.
        """
        resp = transaction_service_client.post('/transactions', data=parameters)

        assert expected_status in resp.status

    @patch('scenario_player.services.transactions.blueprints.transactions.transaction_send_schema')
    def test_new_transaction_calls_validate_and_deserialize_of_its_schema(
            self, mock_schema, transaction_service_client
    ):
        """The :meth:`scenario_player.services.transactions.blueprints.TransactionSendRequest.validate_and_deserialize`
        must be called when processing a request.

        Since the parameters are passed as a :class:`werkzeug.datastructures.ImmutableMultiDict`, which cannot
        be compared to other instances created with identical parameters. Hence, we must
        iterate over the keys of our expected dict and compare manually.
        """
        parameters ={"value": 123.0, "to": 'someaddress', "startgas": 2.0}
        deserialized_parameters = {"value": 123.0, "to": b'someaddress', "startgas": 2.0}
        mock_schema.configure_mock(
            **{
                "validate_and_deserialize.return_value": deserialized_parameters,
                "dumps.return_value": "ok",
            }
        )
        transaction_service_client.post('/transactions', data=parameters)

        mock_schema.validate_and_deserialize.assert_called_once()
        args, kwargs = mock_schema.validate_and_deserialize.call_args
        params_as_multi_dict, *_ = args
        for key, value in parameters.items():
            assert key in params_as_multi_dict
            assert parameters[key] == value

    @patch('scenario_player.services.transactions.blueprints.transactions.transaction_send_schema')
    def test_new_transaction_calls_dumps_of_its_schema(self, mock_schema, transaction_service_client):
        """The :meth:`scenario_player.services.transactions.blueprints.TransactionSendRequest.dump`
        must be called when processing a request and its result returned by the function.
        """
        parameters = {"value": 123.0, "to": 'someaddress', "startgas": 2.0}
        mock_schema.configure_mock(
            **{
                "validate_and_deserialize.return_value": parameters,
                "dumps.return_value": "ok",
            }
        )
        expected_tx_hash = b'my_tx_hash'
        transaction_service_client.application.config['rpc-client'].send_transaction.return_value = expected_tx_hash
        parameters = {"value": 123.0, "to": 'someaddress', "startgas": 2.0}

        r = transaction_service_client.post('/transactions', data=parameters)
        assert "200" in r.status
        mock_schema.dumps.assert_called_once_with({"tx_hash": expected_tx_hash})

    @patch('scenario_player.services.transactions.blueprints.transactions.TransactionSendRequest')
    def test_new_transaction_calls_the_services_jsonrpc_client_with_the_requests_params(
            self, mock_schema, transaction_service_client
    ):
        """The method :meth:`JSONRPCClient.send_transaction` must be called with the parameters of the request
        and its result passed to :meth:`scenario_player.services.transactions.blueprints.TransactionSendRequest.dump`.
        """
        parameters = {"value": 123.0, "to": 'someaddress', "startgas": 2.0}
        deserialized_parameters = {"value": 123.0, "to": b'someaddress', "startgas": 2.0}
        mock_schema.configure_mock(
            **{
                "validate_and_deserialize.return_value": deserialized_parameters,
                "dumps.return_value": "ok",
            }
        )

        transaction_service_client.post('/transactions', data=parameters)
        transaction_service_client.application.config['rpc-client'].send_transaction.assert_called_once_with(**deserialized_parameters)

    def test_new_transaction_aborts_with_500_if_no_rpc_client_key_exists_in_app_config(
            self, transaction_service_client
    ):
        """A `500 Internal Server Error` is expected, if :func:`new_transaction` cannot find a
        :class:`JSONRPCClient` instance.

        Specifically, if no `'rpc-client'` key exists in the :attr:`flask.Flask.config` dictionary
        """
        parameters = {"value": 123.0, "to": 'someaddress', "startgas": 2.0}
        transaction_service_client.application.config.pop('rpc-client')

        resp = transaction_service_client.post('/transactions', data=parameters)
        assert '500' in resp.status
        assert b"No JSONRPCClient instance available on service!" in resp.data

    def test_new_transaction_aborts_with_500_if_rpc_client_key_value_is_not_a_valid_instance_of_rpc_client(
            self, transaction_service_client
    ):
        """A `500 Internal Server Error` is expected, if :func:`new_transaction` cannot find a
        :class:`JSONRPCClient` instance.

        Specifically, if :var:`flask.Flask.config['rpc-client']` is not an instance of :class:`JSONRPCClient`.
        """
        parameters = {"value": 123.0, "to": 'someaddress', "startgas": 2.0}
        transaction_service_client.application.config['rpc-client'] = "This is not a JSONRPCClient instance."

        resp = transaction_service_client.post('/transactions', data=parameters)
        assert '500' in resp.status
        assert b"No JSONRPCClient instance available on service!" in resp.data
