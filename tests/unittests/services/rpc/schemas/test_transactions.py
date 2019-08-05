import pytest
from werkzeug.exceptions import BadRequest

from scenario_player.services.rpc.blueprints.transactions import TransactionSendRequest


class TestTransactionSendRequestValidator:
    def test_validator_accepts_correct_input(
        self,
        default_send_tx_request_parameters,
        deserialized_send_tx_request_parameters,
        rpc_service_app,
    ):
        with rpc_service_app.app_context():
            validator = TransactionSendRequest()
            assert (
                validator.validate_and_deserialize(default_send_tx_request_parameters)
                == deserialized_send_tx_request_parameters
            )

    def test_validator_raises_validation_error_on_missing_args(self, serialized_address):
        validator = TransactionSendRequest()
        parameters = {"to": serialized_address, "value": 123}
        with pytest.raises(BadRequest):
            validator.validate_and_deserialize(parameters)

    def test_validator_raises_validation_error_on_invalid_arg_type(
        self, default_send_tx_request_parameters, rpc_service_app
    ):
        with rpc_service_app.app_context():

            validator = TransactionSendRequest()
            default_send_tx_request_parameters["value"] = "larry"
            with pytest.raises(BadRequest):
                validator.validate_and_deserialize(default_send_tx_request_parameters)

    def test_serializer_constructs_correct_output(self, tx_hash, serialized_tx_hash):
        serializer = TransactionSendRequest()
        given = {"tx_hash": tx_hash}
        expected_output = {"tx_hash": serialized_tx_hash}
        actual = serializer.dump(given)
        assert actual == expected_output
