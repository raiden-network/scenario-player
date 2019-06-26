import pytest

from werkzeug.exceptions import BadRequest

from scenario_player.services.transactions.blueprints.transactions import TransactionSendSchema


class TestTransactionSendRequestValidator:

    def test_validator_accepts_correct_input(self):
        validator = TransactionSendSchema()
        parameters = {'to': 'some_hash', 'value': 123, 'start_gas': 1.5}
        assert validator.validate_and_serialize(parameters) == parameters

    def test_validator_raises_validation_error_on_missing_args(self):
        validator = TransactionSendSchema()
        parameters = {'to': 'some_hash', 'value': 123}
        with pytest.raises(BadRequest):
            validator.validate_and_serialize(parameters)

    def test_validator_raises_validation_error_on_invalid_arg_type(self):
        validator = TransactionSendSchema()
        parameters = {'to': 1421431, 'value': 123, 'start_gas': 1.5}
        with pytest.raises(BadRequest):
            validator.validate_and_serialize(parameters)

    def test_serializer_constructs_correct_output(self):
        serializer = TransactionSendSchema()
        tx_hash = 'my_tx_hash'
        given = {'tx_hash': tx_hash}
        expected_output = {'tx_hash': tx_hash}
        actual = serializer.dump(given).data
        assert actual == expected_output
