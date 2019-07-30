from unittest.mock import patch

import pytest


@pytest.mark.dependency(name="instances_blueprint_loaded")
def test_transaction_blueprint_is_loaded(transaction_service_client):
    assert "instances_blueprint" in transaction_service_client.application.blueprints


class TestCreateRPCInstanceEndpoint:
    @pytest.mark.parametrize(
        "parameters, expected_status",
        argvalues=[
            (
                {
                    "privkey": b"12345678909876543211234567890098",
                    "gas_price_strategy": "super-fast",
                },
                "400",
            ),
            ({"chain_url": "https://test.net", "gas_price_strategy": "super-fast"}, "400"),
            (
                {"chain_url": "https://test.net", "privkey": b"12345678909876543211234567890098"},
                "200",
            ),
            (
                {
                    "chain_url": "https://test.net",
                    "privkey": b"12345678909876543211234567890098",
                    "gas_price_strategy": "super-fast",
                },
                "200",
            ),
        ],
        ids=[
            "missing 'chain_url' is not ok",
            "missing 'privkey'is not ok",
            "missing 'gas_price_strategy' is ok",
            "No missing paramters is ok",
        ],
    )
    def testcreate_rpc_instance_requires_parameters_specified_in_schema(
        self, parameters, expected_status, transaction_service_client
    ):
        # Patch the config dict to avoid actually calling the web3 backend.
        params_as_tuple = tuple(
            parameters[k]
            for k in ("chain_url", "privkey", "gas_price_strategy")
            if k in parameters
        )
        if not len(params_as_tuple) == 3:
            params_as_tuple = (*params_as_tuple, "fast")

        transaction_service_client.application.config["rpc-client"] = {
            params_as_tuple: (object(), "dummy")
        }

        resp = transaction_service_client.post("/rpc/client", data=parameters)
        assert expected_status in resp.status

    @patch("scenario_player.services.rpc.blueprints.instances.new_instance_schema")
    def test_create_rpc_instance_calls_validate_and_deserialize_of_its_schema(
        self,
        mock_schema,
        transaction_service_client,
        default_create_rpc_instance_request_parameters,
        deserialized_create_rpc_instance_request_parameters,
    ):
        """The :meth:`scenario_player.services.rpc.blueprints.TransactionSendRequest.validate_and_deserialize`
        must be called when processing a request.

        Since the parameters are passed as a :class:`werkzeug.datastructures.ImmutableMultiDict`, which cannot
        be compared to other instances created with identical parameters. Hence, we must
        iterate over the keys of our expected dict and compare manually.
        """
        mock_schema.configure_mock(
            **{
                "validate_and_deserialize.return_value": deserialized_create_rpc_instance_request_parameters,
                "dumps.return_value": "ok",
            }
        )
        transaction_service_client.post(
            f"/rpc/client", data=default_create_rpc_instance_request_parameters
        )

        mock_schema.validate_and_deserialize.assert_called_once()
        args, kwargs = mock_schema.validate_and_deserialize.call_args
        params_as_multi_dict, *_ = args
        for key, value in params_as_multi_dict.items():
            assert key in default_create_rpc_instance_request_parameters
            assert str(default_create_rpc_instance_request_parameters[key]) == value

    @patch("scenario_player.services.rpc.blueprints.instances.new_instance_schema")
    def test_create_rpc_instance_calls_dumps_of_its_schema(
        self,
        mock_schema,
        transaction_service_client,
        deserialized_create_rpc_instance_request_parameters,
        default_create_rpc_instance_request_parameters,
        rpc_client_id,
    ):
        """The :meth:`scenario_player.services.rpc.blueprints.TransactionSendRequest.dump`
        must be called when processing a request and its result returned by the function.
        """
        mock_schema.configure_mock(
            **{
                "validate_and_deserialize.return_value": deserialized_create_rpc_instance_request_parameters,
                "dumps.return_value": "ok",
            }
        )

        r = transaction_service_client.post(
            f"/rpc/client", data=default_create_rpc_instance_request_parameters
        )
        assert "200" in r.status
        mock_schema.dumps.assert_called_once_with({"client_id": rpc_client_id})
