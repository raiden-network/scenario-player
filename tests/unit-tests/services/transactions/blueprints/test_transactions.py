from unittest.mock import patch, MagicMock

import pytest



@pytest.mark.dependency(name="transaction_blueprint_loaded")
def test_transaction_blueprint_is_loaded(transaction_service_client):
    assert "transactions_view" in transaction_service_client.application.blueprints


@pytest.mark.dependency(depends=["transaction_blueprint_loaded"])
@patch("scenario_player.services.transactions.blueprints.transactions.get_rpc_client", return_value=MagicMock(**{"send_transaction.return_value": b"my_tx_hash"}))
class TestNewTransactionEndpoint:
    """Test Schema validation/serialization, business logic for POST requests to /transactions."""

    @pytest.mark.parametrize(
        'parameters, expected_status',
        argvalues=[
            ({"value": 123.0, "to": 'someaddress', "startgas": 2.0, "privkey": "1z2x3c4v5b6n7m8,9.0pkjhgfdswert2", "gas_price_strategy": "fast"}, '400'),
            ({"value": 123.0, "to": 'someaddress', "startgas": 2.0, "gas_price_strategy": "fast", "chain_url": "http://test.net"}, '400'),
            ({"to": 'someaddress', "startgas": 2.0, "privkey": "1z2x3c4v5b6n7m8,9.0pkjhgfdswert2", "chain_url": "http://test.net", "gas_price_strategy": "fast"}, '400'),
            ({"value": 123.0, "startgas": 2.0, "privkey": "1z2x3c4v5b6n7m8,9.0pkjhgfdswert2", "chain_url": "http://test.net", "gas_price_strategy": "fast"}, '400'),
            ({"value": 123.0, "to": 'someaddress', "privkey": "1z2x3c4v5b6n7m8,9.0pkjhgfdswert2", "chain_url": "http://test.net", "gas_price_strategy": "fast"}, '400'),
            ({"value": 'wholesome', "to": 'someaddress', "startgas": 2.0, "privkey": "1z2x3c4v5b6n7m8,9.0pkjhgfdswert2", "chain_url": "http://test.net", "gas_price_strategy": "fast"}, '400'),
            ({"value": 123.0, "to": 'someaddress', "startgas": 'hello', "privkey": "1z2x3c4v5b6n7m8,9.0pkjhgfdswert2", "chain_url": "http://test.net", "gas_price_strategy": "fast"}, '400'),
            ({"value": 123.0, "to": 'someaddress', "startgas": 'hello', "privkey": "1z2x3c4v5b6n7m8,9.0pkjhgfdswert2", "chain_url": 1, "gas_price_strategy": "fast"}, '400'),
            ({"value": 123.0, "to": 'someaddress', "startgas": 'hello', "privkey": 1, "chain_url": "http://test.net", "gas_price_strategy": "fast"}, '400'),
            ({"value": 123.0, "to": 'someaddress', "startgas": 'hello', "privkey": "1z2x3c4v5b6n7m8,9.0pkjhgfdswert2", "chain_url": "http://test.net", "gas_price_strategy": 1}, '400'),
            ({"value": 123.0, "to": 'someaddress', "startgas": 2.0, "privkey": "1z2x3c4v5b6n7m8,9.0pkjhgfdswert2", "chain_url": "http://test.net", "gas_price_strategy": "fast"}, '200'),
            ({"value": 123.0, "to": 'someaddress', "startgas": 2.0, "privkey": "1z2x3c4v5b6n7m8,9.0pkjhgfdswert2", "chain_url": "http://test.net"}, '200'),
        ],
        ids=[
            "Missing 'chain_url'",
            "Missing 'privkey'",
            "Missing 'value'",
            "Missing 'to'",
            "Missing 'startgas'",
            "None missing - 'value' type incorrect",
            "None missing - 'startgas' type incorrect",
            "None missing - 'chain_url' type incorrect",
            "None missing - 'privkey' type incorrect",
            "None missing - 'gas_price_strategy' type incorrect",
            "None missing - correct types",
            "Missing 'gas_price_strategy'",
        ]
    )
    def test_endpoint_requires_parameter_and_expects_types(
            self, _, parameters, expected_status, transaction_service_client
    ):
        """The transactions service's `POST /transactions` endpoint requires a set of parameters with specific types.

        These are as follows:

            - `chain_url` - The url for configuring a Web3 instance, if this is the first
                transaction sent via the given `run_id`.
            - `privkey` - the private key required to send the transaction via a
                :class:`raiden.network.rpc.client.JSONRPCClient` instance.
            - `gas_price_strategy` - the strategy to set when instantiaing the
                :class:`raiden.network.rpc.client.JSONRPCClient` instance.
            - `to` - a transaction hash, sent as a  `utf-8` encoded :class:`str`.
            - `startgas` - the starting gas to use, as either :class:`int` or :class:`float`.
            - `amount` - the amount to send with the transaction, as either :class:`int` or :class:`float`.

        FIXME: Update the parameters once #96 is implemented.
         See here for more details:
            https://github.com/raiden-network/scenario-player/issues/96

        If either one or more is missing, or has an incorrect type, we expect to
        see a `400 Bad Request` response from the service.
        """
        resp = transaction_service_client.post('/transactions', data=parameters)

        assert expected_status in resp.status

    @patch('scenario_player.services.transactions.blueprints.transactions.transaction_send_schema')
    def test_new_transaction_calls_validate_and_deserialize_of_its_schema(
            self, mock_schema, _, transaction_service_client, default_send_tx_request_parameters, deserialized_send_tx_request_parameters
    ):
        """The :meth:`scenario_player.services.transactions.blueprints.TransactionSendRequest.validate_and_deserialize`
        must be called when processing a request.

        Since the parameters are passed as a :class:`werkzeug.datastructures.ImmutableMultiDict`, which cannot
        be compared to other instances created with identical parameters. Hence, we must
        iterate over the keys of our expected dict and compare manually.
        """
        mock_schema.configure_mock(
            **{
                "validate_and_deserialize.return_value": deserialized_send_tx_request_parameters,
                "dumps.return_value": "ok",
            }
        )
        transaction_service_client.post('/transactions', data=default_send_tx_request_parameters)

        mock_schema.validate_and_deserialize.assert_called_once()
        args, kwargs = mock_schema.validate_and_deserialize.call_args
        params_as_multi_dict, *_ = args
        for key, value in params_as_multi_dict.items():
            assert key in params_as_multi_dict
            assert params_as_multi_dict[key] == value

    @patch('scenario_player.services.transactions.blueprints.transactions.transaction_send_schema')
    def test_new_transaction_calls_dumps_of_its_schema(
            self,
            mock_schema, _,
            transaction_service_client,
            deserialized_send_tx_request_parameters,
            default_send_tx_request_parameters
    ):
        """The :meth:`scenario_player.services.transactions.blueprints.TransactionSendRequest.dump`
        must be called when processing a request and its result returned by the function.
        """
        mock_schema.configure_mock(
            **{
                "validate_and_deserialize.return_value": deserialized_send_tx_request_parameters,
                "dumps.return_value": "ok",
            }
        )
        expected_tx_hash = b'my_tx_hash'

        r = transaction_service_client.post('/transactions', data=default_send_tx_request_parameters)
        assert "200" in r.status
        mock_schema.dumps.assert_called_once_with({"tx_hash": expected_tx_hash})

    @patch('scenario_player.services.transactions.blueprints.transactions.TransactionSendRequest')
    def test_new_transaction_calls_get_rpc_client_function(self, mock_schema, mock_get_rpc_client, transaction_service_client, default_send_tx_request_parameters, deserialized_send_tx_request_parameters):
        """When sending a POST request, ensure that the endpoint calls the :func:`get_rpc_client` function."""
        mock_schema.configure_mock(
            **{
                "validate_and_deserialize.return_value": deserialized_send_tx_request_parameters,
                "dumps.return_value": "ok",
            }
        )

        transaction_service_client.post('/transactions', data=default_send_tx_request_parameters)
        mock_get_rpc_client.assert_called_once_with(
            deserialized_send_tx_request_parameters["chain_url"],
            deserialized_send_tx_request_parameters["privkey"],
            deserialized_send_tx_request_parameters["gas_price_strategy"],
        )



