from unittest.mock import patch

import pytest


@pytest.mark.dependency(name="instances_blueprint_loaded")
def test_transaction_blueprint_is_loaded(transaction_service_client):
    assert "instances_blueprint" in transaction_service_client.application.blueprints


class TestCreateRPCInstanceEndpoint:
    @patch("scenario_player.services.rpc.blueprints.instances.new_instance_schema")
    def test_create_rpc_instance_calls_validate_and_deserialize_of_its_schema(
        self,
        mock_schema,
        transaction_service_client,
        default_create_rpc_instance_request_parameters,
        deserialized_create_rpc_instance_request_parameters,
    ):
        """The :meth:`scenario_player.services.rpc.blueprints.SendTransactionSchema.validate_and_deserialize`
        must be called when processing a request.

        Since the parameters are passed as a :class:`werkzeug.datastructures.ImmutableMultiDict`, which cannot
        be compared to other instances created with identical parameters. Hence, we must
        iterate over the keys of our expected dict and compare manually.
        """
        mock_schema.configure_mock(
            **{
                "validate_and_deserialize.return_value": deserialized_create_rpc_instance_request_parameters,
                "jsonify.return_value": "ok",
            }
        )
        transaction_service_client.post(
            f"/rpc/client", json=default_create_rpc_instance_request_parameters
        )

        mock_schema.validate_and_deserialize.assert_called_once()
        args, kwargs = mock_schema.validate_and_deserialize.call_args
        params_as_multi_dict, *_ = args
        for key, value in params_as_multi_dict.items():
            assert key in default_create_rpc_instance_request_parameters
            assert str(default_create_rpc_instance_request_parameters[key]) == value

    @patch("scenario_player.services.rpc.blueprints.instances.jsonify", return_value="ok")
    @patch("scenario_player.services.rpc.blueprints.instances.new_instance_schema")
    def test_create_rpc_instance_calls_flask_jsonify(
        self,
        mock_schema,
        mock_jsonify,
        transaction_service_client,
        deserialized_create_rpc_instance_request_parameters,
        default_create_rpc_instance_request_parameters,
        rpc_client_id,
    ):
        """The :meth:`scenario_player.services.rpc.blueprints.SendTransactionSchema.dump`
        must be called when processing a request and its result returned by the function.
        """
        mock_schema.configure_mock(
            **{
                "validate_and_deserialize.return_value": deserialized_create_rpc_instance_request_parameters
            }
        )

        r = transaction_service_client.post(
            f"/rpc/client", data=default_create_rpc_instance_request_parameters
        )
        assert "200" in r.status
        mock_jsonify.assert_called_once_with({"client_id": rpc_client_id})
