import pytest

from werkzeug.exceptions import BadRequest

from scenario_player.services.transactions.blueprints.transactions import TransactionSendRequest


class TestTransactionSendRequestValidator:

    def test_validator_accepts_correct_input(self, default_request_parameters, deserialized_request_parameters):
        validator = TransactionSendRequest()
        assert validator.validate_and_deserialize(default_request_parameters) == deserialized_request_parameters

    def test_validator_raises_validation_error_on_missing_args(self):
        validator = TransactionSendRequest()
        parameters = {'to': 'some_hash', 'value': 123}
        with pytest.raises(BadRequest):
            validator.validate_and_deserialize(parameters)

    def test_validator_raises_validation_error_on_invalid_arg_type(self, default_request_parameters):
        validator = TransactionSendRequest()
        default_request_parameters["url"] = 55
        with pytest.raises(BadRequest):
            validator.validate_and_deserialize(default_request_parameters)

    def test_serializer_constructs_correct_output(self):
        serializer = TransactionSendRequest()
        tx_hash = b'my_tx_hash'
        given = {'tx_hash': tx_hash}
        expected_output = {'tx_hash': tx_hash.decode('utf-8')}
        actual = serializer.dump(given)
        assert actual == expected_output
