import pytest

from werkzeug.exceptions import BadRequest

from scenario_player.services.transactions.blueprints.transactions import TransactionSendRequest


class TestTransactionSendRequestValidator:

    def test_validator_accepts_correct_input(self):
        validator = TransactionSendRequest()
        parameters = {'to': 'some_hash', 'value': 123, 'startgas': 1.5}
        expected_output = {'to': b'some_hash', 'value': 123, 'startgas': 1.5}
        assert validator.validate_and_deserialize(parameters) == expected_output

    def test_validator_raises_validation_error_on_missing_args(self):
        validator = TransactionSendRequest()
        parameters = {'to': 'some_hash', 'value': 123}
        with pytest.raises(BadRequest):
            validator.validate_and_deserialize(parameters)

    def test_validator_raises_validation_error_on_invalid_arg_type(self):
        validator = TransactionSendRequest()
        parameters = {'to': 1421431, 'value': 123, 'startgas': 1.5}
        with pytest.raises(BadRequest):
            validator.validate_and_deserialize(parameters)

    def test_serializer_constructs_correct_output(self):
        serializer = TransactionSendRequest()
        tx_hash = b'my_tx_hash'
        given = {'tx_hash': tx_hash}
        expected_output = {'tx_hash': tx_hash.decode('utf-8')}
        actual = serializer.dump(given).data
        assert actual == expected_output
